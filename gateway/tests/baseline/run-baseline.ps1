<#
.SYNOPSIS
  Orkestrator pengujian Baseline ("Standalone" vs NoAuth NGINX vs Full Gateway), Evaluasi Fase B, dan Generator Tabel (-Report).

.DESCRIPTION
  - Fase A (-Phase A): Mengukur tiga jalur akses (direct, noauth, gateway) untuk ketiga layanan
    (Micro-cred, Judul, Matkul) dari container grafana/k6 di jaringan superapp_default tanpa memanggil LLM.
  - Fase B (-Phase B): Evaluasi alur rekomendasi Matkul (B0-B2), pasangan langsung vs gateway Judul (B3),
    dan uji ulang Micro-cred (B4: 1 probe + 5 siklus utama = 6 siklus). Hanya dijalankan bila -Phase B diberikan.
  - Mode Laporan (-Report): Membaca out/phase-a-summary.json dan menghasilkan docs/baseline-comparison-tables.md
    tanpa menimpa docs/baseline-comparison-results.md. Sel yang belum diukur ditulis "tidak diukur".
  - Token, secret, isi berkas fixtures, dan data pribadi TIDAK PERNAH dicetak ke konsol maupun file.

.PARAMETER Phase
  Fase yang dijalankan: 'A' (default, tanpa LLM) atau 'B' (memanggil LLM).
.PARAMETER Repeats
  Jumlah ulangan per kondisi pada Fase A (default 3).
.PARAMETER OnlyCondition
  Opsional: filter ID kondisi tertentu pada Fase A (mis. 'M1-20rps' atau 'K2').
.PARAMETER Resume
  Opsional: lanjutkan kondisi Fase A yang belum selesai dari out/phase-a-summary.json.
.PARAMETER Report
  Hasilkan docs/baseline-comparison-tables.md dari out/phase-a-summary.json tanpa menjalankan beban uji.
#>
param(
    [ValidateSet('A', 'B')]
    [string]$Phase = 'A',
    [int]$Repeats = 3,
    [string]$OnlyCondition = '',
    [switch]$Resume = $false,
    [switch]$Report = $false
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$inv = [Globalization.CultureInfo]::InvariantCulture
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$baseDir = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $baseDir '..\..\..')).Path
Set-Location $repoRoot

$outDir = Join-Path $baseDir 'out'
$fixturesDir = Join-Path $baseDir 'fixtures'
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
if (-not (Test-Path $fixturesDir)) {
    New-Item -ItemType Directory -Path $fixturesDir -Force | Out-Null
}

# ===========================================================================
# Fungsi Utilitas Statistik, Penanganan Output Native, & Sanitasi
# ===========================================================================
function ConvertTo-TrimmedString($RawOutput) {
    if ($null -eq $RawOutput) { return '' }
    $joined = (@($RawOutput) -join "`n")
    if ([string]::IsNullOrWhiteSpace($joined)) { return '' }
    return $joined.Trim()
}

function ConvertFrom-JsonSafe([string]$JsonText, [string]$Context = 'JSON') {
    if ([string]::IsNullOrWhiteSpace($JsonText)) {
        throw "Output JSON kosong pada $Context."
    }
    try {
        return ($JsonText | ConvertFrom-Json)
    }
    catch {
        throw "Gagal mengurai JSON pada ${Context}: $($_.Exception.Message)"
    }
}

function Get-Median([double[]]$Values) {
    if (-not $Values -or $Values.Count -eq 0) { return 0.0 }
    $sorted = @($Values | Sort-Object)
    $n = $sorted.Count
    if ($n % 2 -eq 1) {
        return [double]$sorted[[int](($n - 1) / 2)]
    }
    return ([double]$sorted[$n / 2 - 1] + [double]$sorted[$n / 2]) / 2.0
}

function Get-Min([double[]]$Values) {
    if (-not $Values -or $Values.Count -eq 0) { return 0.0 }
    return [double](($Values | Measure-Object -Minimum).Minimum)
}

function Get-Max([double[]]$Values) {
    if (-not $Values -or $Values.Count -eq 0) { return 0.0 }
    return [double](($Values | Measure-Object -Maximum).Maximum)
}

function Test-RangesOverlap([double]$MinA, [double]$MaxA, [double]$MinB, [double]$MaxB) {
    return ([math]::Max($MinA, $MinB) -le [math]::Min($MaxA, $MaxB))
}

function Mask-SensitiveText([string]$Text) {
    if (-not $Text) { return '' }
    $t = $Text -replace '[\w\.\-+]+@[\w\.\-]+', '<email>'
    $t = $t -replace 'eyJ[\w\-\.]+', '<token>'
    $t = $t -replace 'Bearer\s+\S+', 'Bearer <token>'
    if ($t.Length -gt 240) { $t = $t.Substring(0, 240) + '...' }
    return $t
}

function ConvertTo-MiB([string]$MemStr) {
    if (-not $MemStr) { return 0.0 }
    $used = ConvertTo-TrimmedString (($MemStr -split '/')[0])
    if ($used -match '^([\d\.]+)\s*GiB$') {
        return [double]::Parse($Matches[1], $inv) * 1024.0
    }
    if ($used -match '^([\d\.]+)\s*MiB$') {
        return [double]::Parse($Matches[1], $inv)
    }
    if ($used -match '^([\d\.]+)\s*KiB$') {
        return [double]::Parse($Matches[1], $inv) / 1024.0
    }
    if ($used -match '^([\d\.]+)\s*B$') {
        return [double]::Parse($Matches[1], $inv) / (1024.0 * 1024.0)
    }
    return 0.0
}

# Hitung MEDIAN CPU (%), MEDIAN Memori (MiB), dan MEDIAN interval sampel aktual pada jendela fase ukur [StartMs, EndMs]
function Get-MeasureWindowMedianStats([string]$CsvPath, [long]$StartMs, [long]$EndMs) {
    $containers = [ordered]@{}
    if (-not (Test-Path $CsvPath)) {
        return [pscustomobject]@{
            Containers              = $containers
            SampleIntervalMedianSec = $null
            SampleIntervalMedianMs  = $null
            SampleBatches           = 0
        }
    }
    $rows = @(Import-Csv -Path $CsvPath -ErrorAction SilentlyContinue)
    $filtered = @($rows | Where-Object {
        $ts = 0L
        [long]::TryParse($_.timestamp_ms, [ref]$ts) -and $ts -ge $StartMs -and $ts -le $EndMs
    })
    if ($filtered.Count -eq 0) {
        $filtered = $rows
    }

    $uniqueTs = @($filtered | ForEach-Object {
        $ts = 0L
        if ([long]::TryParse($_.timestamp_ms, [ref]$ts)) { $ts }
    } | Select-Object -Unique | Sort-Object)

    $intervalMsList = New-Object System.Collections.Generic.List[double]
    for ($i = 1; $i -lt $uniqueTs.Count; $i++) {
        $diffMs = [double]($uniqueTs[$i] - $uniqueTs[$i - 1])
        if ($diffMs -gt 0) {
            $intervalMsList.Add($diffMs)
        }
    }
    $medIntMs = if ($intervalMsList.Count -gt 0) { [math]::Round((Get-Median ([double[]]$intervalMsList)), 0) } else { $null }
    $medIntSec = if ($null -ne $medIntMs) { [math]::Round(($medIntMs / 1000.0), 2) } else { $null }

    $byContainer = @{}
    foreach ($r in $filtered) {
        $c = $r.container
        if (-not $c) { continue }
        $cpuStr = ConvertTo-TrimmedString ($r.cpu_perc -replace '%', '')
        $cpu = 0.0
        [void][double]::TryParse($cpuStr, [Globalization.NumberStyles]::Float, $inv, [ref]$cpu)
        $memMib = ConvertTo-MiB $r.mem_usage
        if (-not $byContainer.ContainsKey($c)) {
            $byContainer[$c] = @{
                cpus = New-Object System.Collections.Generic.List[double]
                mems = New-Object System.Collections.Generic.List[double]
            }
        }
        $byContainer[$c].cpus.Add($cpu)
        $byContainer[$c].mems.Add($memMib)
    }
    foreach ($c in ($byContainer.Keys | Sort-Object)) {
        $medCpu = [math]::Round((Get-Median ([double[]]$byContainer[$c].cpus)), 2)
        $medMem = [math]::Round((Get-Median ([double[]]$byContainer[$c].mems)), 1)
        $containers[$c] = [ordered]@{
            median_cpu_pct = $medCpu
            median_mem_mib = $medMem
            samples        = $byContainer[$c].cpus.Count
        }
    }
    return [pscustomobject]@{
        Containers              = $containers
        SampleIntervalMedianSec = $medIntSec
        SampleIntervalMedianMs  = $medIntMs
        SampleBatches           = $uniqueTs.Count
    }
}

# Periksa kesehatan seluruh 9 container utama superapp
function Test-StackHealthy {
    $lines = @(docker ps --filter "label=com.docker.compose.project=superapp" --format "{{.Names}}|{{.Status}}" 2>$null)
    if ($lines.Count -lt 9) {
        return [pscustomobject]@{ Ok = $false; Reason = "Jumlah container aktif superapp kurang dari 9 (ditemukan $($lines.Count))" }
    }
    foreach ($line in $lines) {
        $parts = $line.Split('|')
        $name = $parts[0]
        $st = $parts[1]
        if ($st -match 'unhealthy|starting|Exited|Dead|Restarting') {
            return [pscustomobject]@{ Ok = $false; Reason = "Container $name berstatus tidak sehat: $st" }
        }
    }
    return [pscustomobject]@{ Ok = $true; Reason = 'Semua 9 container superapp healthy' }
}

# Tunggu sampai total CPU seluruh container < 5% pada 2 sampel beruntun (maks 60 detik), lalu jeda 15 detik
function Wait-ContainersCalm([int]$MaxWaitSec = 60, [int]$PostCalmSleepSec = 15) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $consecUnder5 = 0
    $lastTotalCpu = 999.0
    while ($sw.Elapsed.TotalSeconds -lt $MaxWaitSec) {
        $lines = @(docker stats --no-stream --format "{{.CPUPerc}}" 2>$null)
        $sumCpu = 0.0
        foreach ($l in $lines) {
            $s = ConvertTo-TrimmedString ($l -replace '%', '')
            $v = 0.0
            if ([double]::TryParse($s, [Globalization.NumberStyles]::Float, $inv, [ref]$v)) {
                $sumCpu += $v
            }
        }
        $lastTotalCpu = [math]::Round($sumCpu, 2)
        if ($lines.Count -gt 0 -and $sumCpu -lt 5.0) {
            $consecUnder5++
            if ($consecUnder5 -ge 2) {
                Start-Sleep -Seconds $PostCalmSleepSec
                return [pscustomobject]@{
                    Calm         = $true
                    WaitedSec    = [math]::Round($sw.Elapsed.TotalSeconds, 1)
                    LastTotalCpu = $lastTotalCpu
                }
            }
        }
        else {
            $consecUnder5 = 0
        }
        Start-Sleep -Seconds 2
    }
    Start-Sleep -Seconds $PostCalmSleepSec
    return [pscustomobject]@{
        Calm         = $false
        WaitedSec    = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        LastTotalCpu = $lastTotalCpu
    }
}

# Pembuat berkas PDF minimal yang valid secara programatik (tanpa pustaka eksternal)
function New-MinimalValidPdf([string]$FilePath, [string]$TextContent = 'Panduan Akademik Kurikulum Uji Baseline SuperApp 2026') {
    $escaped = $TextContent.Replace('\', '\\').Replace('(', '\(').Replace(')', '\)')
    $streamBody = "BT /F1 12 Tf 72 720 Td ($escaped) Tj ET"
    $streamBytes = [System.Text.Encoding]::ASCII.GetBytes($streamBody)

    $header = "%PDF-1.4`n"
    $obj1 = "1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n"
    $obj2 = "2 0 obj`n<< /Type /Pages /Kids [3 0 R] /Count 1 >>`nendobj`n"
    $obj3 = "3 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>`nendobj`n"
    $obj4 = "4 0 obj`n<< /Length $($streamBytes.Length) >>`nstream`n$streamBody`nendstream`nendobj`n"
    $obj5 = "5 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`nendobj`n"

    $offsets = @()
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append($header)

    foreach ($o in @($obj1, $obj2, $obj3, $obj4, $obj5)) {
        $offsets += [System.Text.Encoding]::ASCII.GetByteCount($sb.ToString())
        [void]$sb.Append($o)
    }

    $xrefOffset = [System.Text.Encoding]::ASCII.GetByteCount($sb.ToString())
    [void]$sb.Append("xref`n0 6`n0000000000 65535 f `n")
    foreach ($off in $offsets) {
        [void]$sb.Append(("{0:D10} 00000 n `n" -f $off))
    }
    [void]$sb.Append("trailer`n<< /Size 6 /Root 1 0 R >>`nstartxref`n$xrefOffset`n%%EOF`n")

    [System.IO.File]::WriteAllBytes($FilePath, [System.Text.Encoding]::ASCII.GetBytes($sb.ToString()))
}

# Pembuat konfigurasi nginx-noauth.conf dari gateway/nginx/nginx.conf dengan regex toleran spasi dan validasi perubahan
function Ensure-NginxNoAuthConfig {
    $srcConf = Join-Path $repoRoot 'gateway\nginx\nginx.conf'
    $dstConf = Join-Path $baseDir 'nginx-noauth.conf'
    if (-not (Test-Path $srcConf)) {
        throw "Ensure-NginxNoAuthConfig gagal: berkas sumber $srcConf tidak ditemukan."
    }
    $raw = [System.IO.File]::ReadAllText($srcConf, $utf8NoBom)
    $pattern = '(?m)^(\s*)auth_request\s+/_auth\s*;'
    if ($raw -notmatch $pattern) {
        throw "Ensure-NginxNoAuthConfig gagal: baris 'auth_request /_auth;' tidak ditemukan di $srcConf."
    }
    $modified = [regex]::Replace($raw, $pattern, '$1auth_request off;')
    if ($modified -eq $raw) {
        throw "Ensure-NginxNoAuthConfig gagal: hasil penggantian sama dengan berkas sumber ($srcConf)."
    }
    [System.IO.File]::WriteAllText($dstConf, $modified, $utf8NoBom)
    return $dstConf
}

function Get-AuthVerifierLogLineCount {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $lines = @(docker logs superapp-auth-verifier-1 2>&1)
    $ErrorActionPreference = $prev
    return $lines.Count
}

function Get-ContainerLogLineCount([string]$ContainerName) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $lines = @(docker logs $ContainerName 2>&1)
    $ErrorActionPreference = $prev
    return $lines.Count
}

# ===========================================================================
# Manajemen Akun Uji & Token JWT (Tanpa Pernah Mencetak Token)
# ===========================================================================
$script:AuthState = @{
    Email      = ''
    Password   = 'UjiBaseline123!'
    Token      = ''
    ExpiresIn  = 3600
    IssuedAtMs = 0L
}

function Initialize-TestAccount([string]$GatewayHostUrl = 'http://127.0.0.1:8080') {
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $nim = (Get-Random -Minimum 10000000 -Maximum 99999999).ToString()
    $email = "uji-base-$ts@example.com"
    $script:AuthState.Email = $email

    $regBody = @{
        email         = $email
        password      = $script:AuthState.Password
        full_name     = 'Mahasiswa Uji Baseline'
        nim           = $nim
        faculty       = 'Fakultas Teknologi Industri'
        study_program = 'Informatika'
    } | ConvertTo-Json -Compress

    $tmpReg = Join-Path $env:TEMP "baseline_reg_$ts.json"
    [System.IO.File]::WriteAllText($tmpReg, $regBody, $utf8NoBom)
    try {
        $regRaw = & curl.exe -s -o NUL -w "%{http_code}" -X POST "$GatewayHostUrl/api/micro-cred/auth/register" -H "Content-Type: application/json" --data-binary "@$tmpReg"
        $regCode = ConvertTo-TrimmedString $regRaw
        if ($regCode -ne '201' -and $regCode -ne '409') {
            throw "Registrasi akun uji gagal dengan kode HTTP '$regCode'"
        }
    }
    finally {
        Remove-Item $tmpReg -Force -ErrorAction SilentlyContinue
    }

    Update-TestToken -GatewayHostUrl $GatewayHostUrl
}

function Update-TestToken([string]$GatewayHostUrl = 'http://127.0.0.1:8080') {
    $nowMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $elapsedSec = ($nowMs - $script:AuthState.IssuedAtMs) / 1000.0
    if ($script:AuthState.Token -and $elapsedSec -lt [math]::Max($script:AuthState.ExpiresIn - 120, 30)) {
        return
    }
    $loginBody = @{
        email    = $script:AuthState.Email
        password = $script:AuthState.Password
    } | ConvertTo-Json -Compress

    $tmpLogin = Join-Path $env:TEMP "baseline_login_$nowMs.json"
    [System.IO.File]::WriteAllText($tmpLogin, $loginBody, $utf8NoBom)
    try {
        $raw = & curl.exe -s -X POST "$GatewayHostUrl/api/micro-cred/auth/login" -H "Content-Type: application/json" --data-binary "@$tmpLogin"
        $rawStr = ConvertTo-TrimmedString $raw
        $parsed = ConvertFrom-JsonSafe -JsonText $rawStr -Context 'Login akun uji'
        if (-not $parsed -or -not $parsed.tokens -or -not $parsed.tokens.access_token) {
            throw "Login akun uji tidak mengembalikan access_token"
        }
        $script:AuthState.Token = [string]$parsed.tokens.access_token
        $script:AuthState.ExpiresIn = if ($parsed.tokens.expires_in) { [int]$parsed.tokens.expires_in } else { 3600 }
        $script:AuthState.IssuedAtMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    }
    finally {
        Remove-Item $tmpLogin -Force -ErrorAction SilentlyContinue
    }
}

function Get-K6MetricValue($MetricsObj, [string]$MetricName, [string]$PropName, [double]$DefaultVal = 0.0) {
    if ($null -eq $MetricsObj) { return $DefaultVal }
    $mProp = $MetricsObj.PSObject.Properties[$MetricName]
    if (-not $mProp -or $null -eq $mProp.Value) { return $DefaultVal }
    $valObj = $mProp.Value
    if ($valObj.PSObject.Properties['values'] -and $null -ne $valObj.values) {
        $valObj = $valObj.values
    }
    $p = $valObj.PSObject.Properties[$PropName]
    if (-not $p -or $null -eq $p.Value) { return $DefaultVal }
    return [double]$p.Value
}

# ===========================================================================
# FASE A: Pembanding Akses Langsung (Direct vs NoAuth NGINX vs Gateway Penuh)
# ===========================================================================
function Invoke-PhaseA {
    Write-Host "=== FASE A: Pembanding Akses Langsung (Tanpa LLM) ==="

    # A0. Pemeriksaan prasyarat
    $health = Test-StackHealthy
    if (-not $health.Ok) {
        throw "ABORT A0: Stack tidak healthy: $($health.Reason)"
    }
    Write-Host "[A0] $($health.Reason)"

    $k6Images = @(docker images -q grafana/k6 2>$null)
    if ($k6Images.Count -eq 0) {
        throw "ABORT A0: Image grafana/k6 belum tersedia di lokal."
    }

    # Siapkan nginx-noauth.conf dan berkas payload kecil K1 & K2
    $noAuthConfPath = Ensure-NginxNoAuthConfig
    $smallTxtPath = Join-Path $outDir 'small-nonpdf.txt'
    [System.IO.File]::WriteAllText($smallTxtPath, "BUKAN_PDF_UJI_BASELINE_MATKUL_EXTRACT_UPLOAD`n", $utf8NoBom)

    $smallPdfPath = Join-Path $outDir 'minimal-valid.pdf'
    New-MinimalValidPdf -FilePath $smallPdfPath

    # Buat 1 akun uji untuk seluruh Fase A
    Initialize-TestAccount -GatewayHostUrl 'http://127.0.0.1:8080'
    Write-Host "[A2] Akun uji berhasil dibuat dan token siap di memori (tidak dicetak)."

    # Jalankan container sementara superapp-nginx-noauth di jaringan superapp_default (tanpa port host)
    $noAuthContainer = 'superapp-nginx-noauth'
    $prevErr = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    docker rm -f $noAuthContainer 2>&1 | Out-Null
    $ErrorActionPreference = $prevErr

    $statsScript = Join-Path $baseDir 'collect-stats.ps1'

    try {
        Write-Host "[A1] Menjalankan container uji sementara $noAuthContainer..."
        docker run -d --name $noAuthContainer --network superapp_default -v "${noAuthConfPath}:/etc/nginx/nginx.conf:ro" nginx:1.27-alpine | Out-Null
        Start-Sleep -Seconds 2

        # (3b) Probe noauth dibungkus try/catch, kirim kode Python lewat stdin, berhenti bila status != 200 atau log auth-verifier bertambah
        $verBeforeProbe = Get-AuthVerifierLogLineCount
        $probeNoAuthCode = ''
        $verProbeDelta = 0
        try {
            $probePy = @"
import urllib.request
with urllib.request.urlopen('http://superapp-nginx-noauth/api/judul-recommender/', timeout=10) as resp:
    print(resp.status)
"@
            $probeRaw = $probePy | & docker compose exec -T microcred-api python - 2>$null
            $probeNoAuthCode = ConvertTo-TrimmedString $probeRaw
            if (-not $probeNoAuthCode) {
                throw "Output probe noauth kosong dari container microcred-api."
            }
            $verAfterProbe = Get-AuthVerifierLogLineCount
            $verProbeDelta = $verAfterProbe - $verBeforeProbe
            if ($probeNoAuthCode -ne '200') {
                throw "Status HTTP probe noauth bukan 200 (diterima: '$probeNoAuthCode')."
            }
            if ($verProbeDelta -gt 0) {
                throw "Log auth-verifier bertambah $verProbeDelta baris selama probe noauth."
            }
        }
        catch {
            throw "ABORT A1 (Validasi Probe NoAuth Gagal): $($_.Exception.Message)"
        }
        Write-Host "[A1] Probe superapp-nginx-noauth tanpa token LOLOS -> HTTP $probeNoAuthCode (delta log auth-verifier = $verProbeDelta)"

        # (2) Verifikasi pra-syarat K2: kirim kode Python lewat stdin ke "docker compose exec -T microcred-api python -"
        $pdfB64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($smallPdfPath))
        $k2VerifyPy = @"
import urllib.request, json, base64
pdf_bytes = base64.b64decode('$pdfB64')
boundary = '----BaselineK2Boundary'
body = (
    f'--{boundary}\r\n'
    'Content-Disposition: form-data; name="file_pdf"; filename="minimal-valid.pdf"\r\n'
    'Content-Type: application/pdf\r\n\r\n'
).encode('ascii') + pdf_bytes + f'\r\n--{boundary}--\r\n'.encode('ascii')
req = urllib.request.Request(
    'http://matkul:3000/api/panduan/extract-upload',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    method='POST'
)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print(json.dumps({'status': resp.status, 'ok': data.get('ok'), 'extracted_chars': data.get('extracted_chars', 0)}))
"@
        $k2Raw = $k2VerifyPy | & docker compose exec -T microcred-api python - 2>$null
        $k2VerifyOut = ConvertTo-TrimmedString $k2Raw
        if (-not $k2VerifyOut) {
            throw "ABORT A3-K2: Verifikasi PDF minimal langsung ke matkul:3000 menghasilkan output kosong."
        }
        $k2VerifyObj = ConvertFrom-JsonSafe -JsonText $k2VerifyOut -Context 'Verifikasi K2 matkul:3000'
        $k2Enabled = ($k2VerifyObj.status -eq 200 -and [int]$k2VerifyObj.extracted_chars -gt 0)
        Write-Host "[A3-K2] Verifikasi PDF minimal langsung ke matkul:3000 -> status=$($k2VerifyObj.status), extracted_chars=$($k2VerifyObj.extracted_chars), K2 diaktifkan=$k2Enabled"

        $conditions = @(
            @{ Id = 'M1-20rps';  Cond = 'M1'; Service = 'Micro-cred'; Endpoint = 'GET /tracks';                                      Rate = 20;  Expected = 200 },
            @{ Id = 'M1-50rps';  Cond = 'M1'; Service = 'Micro-cred'; Endpoint = 'GET /tracks';                                      Rate = 50;  Expected = 200 },
            @{ Id = 'M1-100rps'; Cond = 'M1'; Service = 'Micro-cred'; Endpoint = 'GET /tracks';                                      Rate = 100; Expected = 200 },
            @{ Id = 'M2-20rps';  Cond = 'M2'; Service = 'Micro-cred'; Endpoint = 'GET /auth/me';                                     Rate = 20;  Expected = 200 },
            @{ Id = 'M2-50rps';  Cond = 'M2'; Service = 'Micro-cred'; Endpoint = 'GET /auth/me';                                     Rate = 50;  Expected = 200 },
            @{ Id = 'J1-50rps';  Cond = 'J1'; Service = 'Judul';      Endpoint = 'GET /';                                            Rate = 50;  Expected = 200 },
            @{ Id = 'J1-200rps'; Cond = 'J1'; Service = 'Judul';      Endpoint = 'GET /';                                            Rate = 200; Expected = 200 },
            @{ Id = 'K1-20rps';  Cond = 'K1'; Service = 'Matkul';     Endpoint = 'POST /api/panduan/extract-upload (non-PDF -> 400)'; Rate = 20; Expected = 400 },
            @{ Id = 'K1-50rps';  Cond = 'K1'; Service = 'Matkul';     Endpoint = 'POST /api/panduan/extract-upload (non-PDF -> 400)'; Rate = 50; Expected = 400 }
        )
        if ($k2Enabled) {
            $conditions += @(
                @{ Id = 'K2-5rps';  Cond = 'K2'; Service = 'Matkul'; Endpoint = 'POST /api/panduan/extract-upload (PDF valid -> 200)'; Rate = 5;  Expected = 200 },
                @{ Id = 'K2-10rps'; Cond = 'K2'; Service = 'Matkul'; Endpoint = 'POST /api/panduan/extract-upload (PDF valid -> 200)'; Rate = 10; Expected = 200 }
            )
        }

        if ($OnlyCondition) {
            $conditions = @($conditions | Where-Object { $_.Id -like "*$OnlyCondition*" -or $_.Cond -eq $OnlyCondition })
        }

        $summaryJsonPath = Join-Path $outDir 'phase-a-summary.json'
        $summaryMap = [ordered]@{}
        if (($Resume -or $OnlyCondition) -and (Test-Path $summaryJsonPath)) {
            $loadedRaw = Get-Content $summaryJsonPath -Raw
            if (-not [string]::IsNullOrWhiteSpace($loadedRaw)) {
                $loaded = ConvertFrom-JsonSafe -JsonText $loadedRaw -Context $summaryJsonPath
                if ($loaded -and $loaded.conditions) {
                    foreach ($item in $loaded.conditions) {
                        $summaryMap[$item.id] = $item
                    }
                }
            }
        }

        $saturatedGroups = @{}
        $basePaths = @('direct', 'noauth', 'gateway')

        foreach ($c in $conditions) {
            $cid = $c.Id
            $cGroup = $c.Cond

            if ($Resume -and $summaryMap.Contains($cid) -and -not $summaryMap[$cid].skipped) {
                Write-Host "`nMelewati $cid (sudah ada di phase-a-summary.json)."
                if ($summaryMap[$cid].saturated) {
                    $saturatedGroups[$cGroup] = $true
                }
                continue
            }

            if ($saturatedGroups.ContainsKey($cGroup)) {
                Write-Warning "Melewati $cid karena laju lebih rendah pada kelompok $cGroup sudah ditandai JENUH."
                $summaryMap[$cid] = [ordered]@{
                    id          = $cid
                    cond        = $cGroup
                    service     = $c.Service
                    endpoint    = $c.Endpoint
                    rate_rps    = $c.Rate
                    skipped     = $true
                    skip_reason = "Dilewati karena kondisi laju lebih rendah pada $cGroup sudah jenuh (error rate > 20% selama >= 15 detik)."
                }
                continue
            }

            Write-Host "`n============================================================"
            Write-Host "Kondisi: $cid ($($c.Service) | $($c.Endpoint) @ $($c.Rate) req/s, $Repeats ulangan)"
            Write-Host "============================================================"

            $runsByPath = @{
                direct  = New-Object System.Collections.Generic.List[object]
                noauth  = New-Object System.Collections.Generic.List[object]
                gateway = New-Object System.Collections.Generic.List[object]
            }
            $conditionSaturated = $false
            $saturationReason = ''
            $notCalmEvents = New-Object System.Collections.Generic.List[string]
            $noAuthVerifierHitEvents = New-Object System.Collections.Generic.List[string]

            for ($r = 1; $r -le $Repeats; $r++) {
                $rotatedPaths = @(
                    $basePaths[($r - 1 + 0) % 3],
                    $basePaths[($r - 1 + 1) % 3],
                    $basePaths[($r - 1 + 2) % 3]
                )
                Write-Host ("  [Ulangan {0}/{1}] Urutan jalur: {2}" -f $r, $Repeats, ($rotatedPaths -join ' -> '))

                foreach ($pathMode in $rotatedPaths) {
                    $calmInfo = Wait-ContainersCalm -MaxWaitSec 60 -PostCalmSleepSec 15
                    if (-not $calmInfo.Calm) {
                        $msg = "${cid}-${pathMode}-r${r} (total CPU terakhir $($calmInfo.LastTotalCpu)% setelah $($calmInfo.WaitedSec)s)"
                        Write-Warning "  [TIDAK TENANG] $msg"
                        $notCalmEvents.Add($msg)
                    }

                    $hBefore = Test-StackHealthy
                    if (-not $hBefore.Ok) {
                        throw "ABORT: Stack tidak healthy sebelum ${cid} (${pathMode}, r=${r}): $($hBefore.Reason)"
                    }

                    Update-TestToken -GatewayHostUrl 'http://127.0.0.1:8080'

                    $runTag = "$cid-$pathMode-r$r"
                    $jsonRel = "/scripts/out/$runTag.json"
                    $jsonHost = Join-Path $outDir "$runTag.json"
                    $statsCsv = Join-Path $outDir "stats-$runTag.csv"
                    if (Test-Path $jsonHost) { Remove-Item $jsonHost -Force }
                    "timestamp_ms,container,cpu_perc,mem_usage,mem_perc" | Set-Content -Path $statsCsv -Encoding utf8

                    $verLinesBefore = Get-AuthVerifierLogLineCount
                    $noAuthLogsBefore = Get-ContainerLogLineCount -ContainerName $noAuthContainer

                    $argStr = "-NoProfile -WindowStyle Hidden -File `"$statsScript`" -CsvPath `"$statsCsv`""
                    $statsProc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argStr -PassThru

                    $runStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                    $measureStartMs = $runStartMs + 10000L
                    $k6Exit = 0
                    $k6Out = @()

                    try {
                        $dockerArgs = @(
                            'run', '--rm',
                            '--network', 'superapp_default',
                            '-v', "${baseDir}:/scripts",
                            '-e', "COND=$($c.Cond)",
                            '-e', "PATH_MODE=$pathMode",
                            '-e', "RATE=$($c.Rate)",
                            '-e', 'WARMUP_SEC=10',
                            '-e', 'MEASURE_SEC=30',
                            '-e', "TOKEN=$($script:AuthState.Token)",
                            'grafana/k6', 'run',
                            '--quiet',
                            '--summary-export', $jsonRel,
                            '/scripts/baseline-k6.js'
                        )
                        $prevErr = $ErrorActionPreference
                        $ErrorActionPreference = 'Continue'
                        $k6Out = & docker @dockerArgs 2>&1
                        $k6Exit = $LASTEXITCODE
                        $ErrorActionPreference = $prevErr
                    }
                    finally {
                        $measureEndMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                        if ($statsProc -and -not $statsProc.HasExited) {
                            Stop-Process -Id $statsProc.Id -Force -ErrorAction SilentlyContinue
                        }
                    }

                    $verLinesAfter = Get-AuthVerifierLogLineCount
                    $noAuthLogsAfter = Get-ContainerLogLineCount -ContainerName $noAuthContainer
                    $verLogDelta = $verLinesAfter - $verLinesBefore
                    $noAuthLogDelta = $noAuthLogsAfter - $noAuthLogsBefore

                    # (3c) Bila jalur noauth mencatat verifier_log_delta > 0, tandai sebagai noauth_verifier_hits dan laporkan
                    $noAuthHit = ($pathMode -eq 'noauth' -and $verLogDelta -gt 0)
                    if ($noAuthHit) {
                        $hitMsg = "${runTag}: verifier_log_delta=$verLogDelta"
                        Write-Warning "  [NOAUTH_VERIFIER_HITS] Jalur noauth mencatat penambahan log auth-verifier ($hitMsg)!"
                        $noAuthVerifierHitEvents.Add($hitMsg)
                    }

                    if (-not (Test-Path $jsonHost)) {
                        throw "ABORT: File ringkasan k6 tidak terbentuk untuk $runTag (exit=$k6Exit)."
                    }

                    $summaryRaw = Get-Content $jsonHost -Raw
                    $summary = ConvertFrom-JsonSafe -JsonText $summaryRaw -Context "Ringkasan k6 $runTag"
                    if ($summary.PSObject.Properties['setup_data']) {
                        $summary.PSObject.Properties.Remove('setup_data')
                        ($summary | ConvertTo-Json -Depth 8) | Set-Content -Path $jsonHost -Encoding utf8
                    }

                    $m = $summary.metrics
                    $p50 = Get-K6MetricValue $m 'main_duration' 'p(50)'
                    if ($p50 -eq 0) { $p50 = Get-K6MetricValue $m 'main_duration' 'med' }
                    $p95 = Get-K6MetricValue $m 'main_duration' 'p(95)'
                    $p99 = Get-K6MetricValue $m 'main_duration' 'p(99)'
                    $avg = Get-K6MetricValue $m 'main_duration' 'avg'
                    $minLat = Get-K6MetricValue $m 'main_duration' 'min'
                    $maxLat = Get-K6MetricValue $m 'main_duration' 'max'
                    $reqs = Get-K6MetricValue $m 'main_reqs' 'count'
                    $errRate = Get-K6MetricValue $m 'main_failed' 'value'
                    if ($errRate -eq 0) { $errRate = Get-K6MetricValue $m 'main_failed' 'rate' }
                    $dropped = Get-K6MetricValue $m 'dropped_iterations' 'count'
                    $timeouts = Get-K6MetricValue $m 'main_timeouts' 'count'
                    $s200 = Get-K6MetricValue $m 'main_status_200' 'count'
                    $s400 = Get-K6MetricValue $m 'main_status_400' 'count'
                    $s401 = Get-K6MetricValue $m 'main_status_401' 'count'
                    $s503 = Get-K6MetricValue $m 'main_status_503' 'count'
                    $s5xx = Get-K6MetricValue $m 'main_status_5xx' 'count'
                    $extOk = Get-K6MetricValue $m 'main_extracted_ok' 'count'

                    $rps = [math]::Round(($reqs / 30.0), 2)
                    $statsResult = Get-MeasureWindowMedianStats -CsvPath $statsCsv -StartMs $measureStartMs -EndMs $measureEndMs

                    Write-Host ("    [{0,-7}] reqs={1,4} rps={2,6:N2} p50={3,6:N2}ms p95={4,7:N2}ms p99={5,7:N2}ms avg={6,6:N2}ms err={7,5:N2}% drop={8} calm={9} dt_stats={10}s" -f $pathMode, $reqs, $rps, $p50, $p95, $p99, $avg, ($errRate * 100.0), $dropped, $calmInfo.Calm, $statsResult.SampleIntervalMedianSec)

                    $runsByPath[$pathMode].Add([pscustomobject]@{
                        repeat                     = $r
                        path_mode                  = $pathMode
                        calm_before                = $calmInfo.Calm
                        calm_wait_sec              = $calmInfo.WaitedSec
                        calm_last_total_cpu_pct    = $calmInfo.LastTotalCpu
                        reqs                       = $reqs
                        rps                        = $rps
                        p50_ms                     = [math]::Round($p50, 2)
                        p95_ms                     = [math]::Round($p95, 2)
                        p99_ms                     = [math]::Round($p99, 2)
                        avg_ms                     = [math]::Round($avg, 2)
                        min_ms                     = [math]::Round($minLat, 2)
                        max_ms                     = [math]::Round($maxLat, 2)
                        err_rate_pct               = [math]::Round(($errRate * 100.0), 2)
                        dropped_iterations         = $dropped
                        timeouts                   = $timeouts
                        status_200                 = $s200
                        status_400                 = $s400
                        status_401                 = $s401
                        status_503                 = $s503
                        status_5xx                 = $s5xx
                        extracted_ok               = $extOk
                        verifier_log_delta         = $verLogDelta
                        noauth_verifier_hits       = $noAuthHit
                        noauth_nginx_log_delta     = $noAuthLogDelta
                        sample_interval_median_sec = $statsResult.SampleIntervalMedianSec
                        sample_interval_median_ms  = $statsResult.SampleIntervalMedianMs
                        container_medians          = $statsResult.Containers
                    })

                    $hAfter = Test-StackHealthy
                    if (-not $hAfter.Ok) {
                        throw "ABORT: Stack menjadi tidak healthy setelah ${runTag}: $($hAfter.Reason)"
                    }

                    if ($k6Exit -eq 99 -or $errRate -gt 0.20) {
                        $conditionSaturated = $true
                        $saturationReason = ("Kondisi {0} pada jalur {1} (ulangan {2}) melampaui error rate 20% ({3:N2}%, exit={4}). Ditandai JENUH." -f $cid, $pathMode, $r, ($errRate * 100.0), $k6Exit)
                        Write-Warning "  [JENUH] $saturationReason"
                        $saturatedGroups[$cGroup] = $true
                        break
                    }
                }

                if ($conditionSaturated) {
                    break
                }
            }

            # Agregasi metrik per jalur
            $pathSummaries = [ordered]@{}
            foreach ($pm in $basePaths) {
                $list = $runsByPath[$pm]
                if ($list.Count -eq 0) { continue }
                $p50Arr = [double[]]($list | ForEach-Object { [double]$_.p50_ms })
                $p95Arr = [double[]]($list | ForEach-Object { [double]$_.p95_ms })
                $p99Arr = [double[]]($list | ForEach-Object { [double]$_.p99_ms })
                $avgArr = [double[]]($list | ForEach-Object { [double]$_.avg_ms })
                $rpsArr = [double[]]($list | ForEach-Object { [double]$_.rps })
                $errArr = [double[]]($list | ForEach-Object { [double]$_.err_rate_pct })
                $drpArr = [double[]]($list | ForEach-Object { [double]$_.dropped_iterations })
                $intSecArr = [double[]]($list | Where-Object { $null -ne $_.sample_interval_median_sec } | ForEach-Object { [double]$_.sample_interval_median_sec })

                $cNames = @()
                foreach ($runItem in $list) {
                    if ($runItem.container_medians) {
                        $cNames += @($runItem.container_medians.Keys)
                    }
                }
                $cNames = @($cNames | Select-Object -Unique | Sort-Object)
                $aggContainers = [ordered]@{}
                foreach ($cn in $cNames) {
                    $cpus = [double[]]($list | Where-Object { $_.container_medians.Contains($cn) } | ForEach-Object { [double]$_.container_medians[$cn].median_cpu_pct })
                    $mems = [double[]]($list | Where-Object { $_.container_medians.Contains($cn) } | ForEach-Object { [double]$_.container_medians[$cn].median_mem_mib })
                    $aggContainers[$cn] = [ordered]@{
                        median_cpu_pct = [math]::Round((Get-Median $cpus), 2)
                        median_mem_mib = [math]::Round((Get-Median $mems), 1)
                    }
                }

                $verHitsSum = ($list | Measure-Object -Property verifier_log_delta -Sum).Sum
                $pathSummaries[$pm] = [ordered]@{
                    repeats                    = $list.Count
                    p50_median_ms              = [math]::Round((Get-Median $p50Arr), 2)
                    p50_min_ms                 = [math]::Round((Get-Min $p50Arr), 2)
                    p50_max_ms                 = [math]::Round((Get-Max $p50Arr), 2)
                    p95_median_ms              = [math]::Round((Get-Median $p95Arr), 2)
                    p95_min_ms                 = [math]::Round((Get-Min $p95Arr), 2)
                    p95_max_ms                 = [math]::Round((Get-Max $p95Arr), 2)
                    p99_median_ms              = [math]::Round((Get-Median $p99Arr), 2)
                    avg_median_ms              = [math]::Round((Get-Median $avgArr), 2)
                    throughput_median_rps      = [math]::Round((Get-Median $rpsArr), 2)
                    error_rate_median_pct      = [math]::Round((Get-Median $errArr), 2)
                    dropped_median             = [math]::Round((Get-Median $drpArr), 0)
                    verifier_log_delta_sum     = $verHitsSum
                    noauth_verifier_hits       = [bool]($pm -eq 'noauth' -and $verHitsSum -gt 0)
                    noauth_log_delta_sum       = ($list | Measure-Object -Property noauth_nginx_log_delta -Sum).Sum
                    sample_interval_median_sec = if ($intSecArr.Count -gt 0) { [math]::Round((Get-Median $intSecArr), 2) } else { $null }
                    container_medians          = $aggContainers
                    runs                       = $list
                }
            }

            # Hitung selisih antar jalur
            $diffs = [ordered]@{}
            if ($pathSummaries.Contains('direct') -and $pathSummaries.Contains('noauth') -and $pathSummaries.Contains('gateway')) {
                $d = $pathSummaries['direct']
                $n = $pathSummaries['noauth']
                $g = $pathSummaries['gateway']

                $proxyP50Runs = @()
                $authP50Runs = @()
                $totalP50Runs = @()
                $proxyP95Runs = @()
                $authP95Runs = @()
                $totalP95Runs = @()

                $minCount = [math]::Min($d.repeats, [math]::Min($n.repeats, $g.repeats))
                for ($idx = 0; $idx -lt $minCount; $idx++) {
                    $proxyP50Runs += [math]::Round(($n.runs[$idx].p50_ms - $d.runs[$idx].p50_ms), 2)
                    $authP50Runs  += [math]::Round(($g.runs[$idx].p50_ms - $n.runs[$idx].p50_ms), 2)
                    $totalP50Runs += [math]::Round(($g.runs[$idx].p50_ms - $d.runs[$idx].p50_ms), 2)

                    $proxyP95Runs += [math]::Round(($n.runs[$idx].p95_ms - $d.runs[$idx].p95_ms), 2)
                    $authP95Runs  += [math]::Round(($g.runs[$idx].p95_ms - $n.runs[$idx].p95_ms), 2)
                    $totalP95Runs += [math]::Round(($g.runs[$idx].p95_ms - $d.runs[$idx].p95_ms), 2)
                }

                $ovProxy = Test-RangesOverlap $d.p50_min_ms $d.p50_max_ms $n.p50_min_ms $n.p50_max_ms
                $ovAuth  = Test-RangesOverlap $n.p50_min_ms $n.p50_max_ms $g.p50_min_ms $g.p50_max_ms
                $ovTotal = Test-RangesOverlap $d.p50_min_ms $d.p50_max_ms $g.p50_min_ms $g.p50_max_ms

                $diffs = [ordered]@{
                    proxy_noauth_minus_direct = [ordered]@{
                        p50_diff_median_ms = [math]::Round(($n.p50_median_ms - $d.p50_median_ms), 2)
                        p50_diff_min_ms    = [math]::Round((Get-Min ([double[]]$proxyP50Runs)), 2)
                        p50_diff_max_ms    = [math]::Round((Get-Max ([double[]]$proxyP50Runs)), 2)
                        p95_diff_median_ms = [math]::Round(($n.p95_median_ms - $d.p95_median_ms), 2)
                        p95_diff_min_ms    = [math]::Round((Get-Min ([double[]]$proxyP95Runs)), 2)
                        p95_diff_max_ms    = [math]::Round((Get-Max ([double[]]$proxyP95Runs)), 2)
                        p50_ranges_overlap = $ovProxy
                        interpretation     = if ($ovProxy) { 'tidak dapat dibedakan pada pengukuran ini' } else { 'rentang p50 tidak tumpang tindih' }
                    }
                    auth_gateway_minus_noauth = [ordered]@{
                        p50_diff_median_ms = [math]::Round(($g.p50_median_ms - $n.p50_median_ms), 2)
                        p50_diff_min_ms    = [math]::Round((Get-Min ([double[]]$authP50Runs)), 2)
                        p50_diff_max_ms    = [math]::Round((Get-Max ([double[]]$authP50Runs)), 2)
                        p95_diff_median_ms = [math]::Round(($g.p95_median_ms - $n.p95_median_ms), 2)
                        p95_diff_min_ms    = [math]::Round((Get-Min ([double[]]$authP95Runs)), 2)
                        p95_diff_max_ms    = [math]::Round((Get-Max ([double[]]$authP95Runs)), 2)
                        p50_ranges_overlap = $ovAuth
                        interpretation     = if ($ovAuth) { 'tidak dapat dibedakan pada pengukuran ini' } else { 'rentang p50 tidak tumpang tindih' }
                    }
                    total_gateway_minus_direct = [ordered]@{
                        p50_diff_median_ms = [math]::Round(($g.p50_median_ms - $d.p50_median_ms), 2)
                        p50_diff_min_ms    = [math]::Round((Get-Min ([double[]]$totalP50Runs)), 2)
                        p50_diff_max_ms    = [math]::Round((Get-Max ([double[]]$totalP50Runs)), 2)
                        p95_diff_median_ms = [math]::Round(($g.p95_median_ms - $d.p95_median_ms), 2)
                        p95_diff_min_ms    = [math]::Round((Get-Min ([double[]]$totalP95Runs)), 2)
                        p95_diff_max_ms    = [math]::Round((Get-Max ([double[]]$totalP95Runs)), 2)
                        p50_ranges_overlap = $ovTotal
                        interpretation     = if ($ovTotal) { 'tidak dapat dibedakan pada pengukuran ini' } else { 'rentang p50 tidak tumpang tindih' }
                    }
                }
            }

            $summaryMap[$cid] = [ordered]@{
                id                   = $cid
                cond                 = $cGroup
                service              = $c.Service
                endpoint             = $c.Endpoint
                rate_rps             = $c.Rate
                expected_status      = $c.Expected
                skipped              = $false
                saturated            = $conditionSaturated
                saturation_reason    = $saturationReason
                not_calm_events      = @($notCalmEvents)
                noauth_verifier_hits = [bool]($noAuthVerifierHitEvents.Count -gt 0)
                noauth_hit_events    = @($noAuthVerifierHitEvents)
                paths                = $pathSummaries
                differences          = $diffs
            }

            $outPayload = [ordered]@{
                generated_utc       = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
                phase               = 'A'
                repeats             = $Repeats
                noauth_probe_status = $probeNoAuthCode
                noauth_probe_delta  = $verProbeDelta
                k2_verify           = $k2VerifyObj
                conditions          = @($summaryMap.Values)
            }
            ($outPayload | ConvertTo-Json -Depth 10) | Set-Content -Path $summaryJsonPath -Encoding utf8
        }

        Write-Host "`nFase A selesai. Hasil disimpan di $summaryJsonPath"
    }
    finally {
        Write-Host "`n[Cleanup] Menghapus container uji sementara $noAuthContainer..."
        $prevErr = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        docker rm -f $noAuthContainer 2>&1 | Out-Null
        $ErrorActionPreference = $prevErr
    }
}

# ===========================================================================
# FASE B: Evaluasi Alur Rekomendasi Matkul & Uji Ulang Micro-cred (Memanggil LLM)
# ===========================================================================
function Invoke-PhaseB {
    Write-Host "=== FASE B: Evaluasi Alur Rekomendasi & Pasangan Langsung vs Gateway (Memanggil LLM) ==="

    # B0. Pemeriksaan awal
    $khsPdf = Join-Path $fixturesDir 'khs-sample.pdf'
    $panduanPdf = Join-Path $fixturesDir 'panduan-sample.pdf'
    if (-not (Test-Path $khsPdf) -or -not (Test-Path $panduanPdf)) {
        throw "ABORT B0: Berkas fixtures/khs-sample.pdf dan/atau fixtures/panduan-sample.pdf belum tersedia. Letakkan kedua berkas sesuai gateway/tests/baseline/fixtures/README.md."
    }

    $health = Test-StackHealthy
    if (-not $health.Ok) {
        throw "ABORT B0: Stack tidak healthy: $($health.Reason)"
    }

    # Cek kesehatan PocketBase dari jaringan Docker via stdin
    $pbPy = @"
import urllib.request
with urllib.request.urlopen('http://pocketbase:8090/api/health', timeout=10) as resp:
    print(resp.status)
"@
    $pbRaw = $pbPy | & docker compose exec -T microcred-api python - 2>$null
    $pbHealth = ConvertTo-TrimmedString $pbRaw
    if ($pbHealth -ne '200') {
        throw "ABORT B0: PocketBase tidak sehat (GET http://pocketbase:8090/api/health -> '$pbHealth')"
    }
    Write-Host "[B0] PocketBase healthy (HTTP 200)."

    Initialize-TestAccount -GatewayHostUrl 'http://127.0.0.1:8080'

    function Test-LlmQuotaError([int]$HttpCode, [string]$BodyText) {
        if ($HttpCode -eq 429) { return $true }
        if ($BodyText -match '(?i)insufficient_quota|no credits|rate_limit_exceeded|billing_hard_limit') { return $true }
        return $false
    }

    # B1. Alur Matkul lewat gateway (5 siklus)
    Write-Host "`n[B1] Menjalankan 5 siklus alur Matkul lewat gateway..."
    $b1Rows = New-Object System.Collections.Generic.List[object]
    $savedRekPayload = $null

    for ($c = 1; $c -le 5; $c++) {
        Update-TestToken -GatewayHostUrl 'http://127.0.0.1:8080'
        $tok = $script:AuthState.Token
        $cycleSw = [Diagnostics.Stopwatch]::StartNew()

        # Langkah 1: POST /api/matkul-recommender/khs/upload
        $sw1 = [Diagnostics.Stopwatch]::StartNew()
        $raw1 = ConvertTo-TrimmedString (& curl.exe -s -w "`n%{http_code}" -X POST "http://127.0.0.1:8080/api/matkul-recommender/khs/upload" -H "Authorization: Bearer $tok" -F "file=@$khsPdf;type=application/pdf")
        $sw1.Stop()
        $idx1 = $raw1.LastIndexOf("`n")
        $code1 = if ($idx1 -ge 0) { [int](ConvertTo-TrimmedString $raw1.Substring($idx1 + 1)) } else { 0 }
        $body1 = if ($idx1 -gt 0) { $raw1.Substring(0, $idx1) } else { '' }

        if (Test-LlmQuotaError -HttpCode $code1 -BodyText $body1) {
            throw "ABORT B0/B1: Panggilan LLM pada khs/upload siklus $c mengembalikan kuota habis / 429 (HTTP $code1). Dihentikan tanpa retry."
        }
        if ($code1 -ne 200) {
            throw "ABORT B1: khs/upload siklus $c gagal dengan HTTP $code1"
        }
        $json1 = ConvertFrom-JsonSafe -JsonText $body1 -Context "khs/upload siklus $c"

        # Langkah 2: POST /api/matkul-recommender/panduan/extract-upload
        $sw2 = [Diagnostics.Stopwatch]::StartNew()
        $raw2 = ConvertTo-TrimmedString (& curl.exe -s -w "`n%{http_code}" -X POST "http://127.0.0.1:8080/api/matkul-recommender/panduan/extract-upload" -H "Authorization: Bearer $tok" -F "file_pdf=@$panduanPdf;type=application/pdf")
        $sw2.Stop()
        $idx2 = $raw2.LastIndexOf("`n")
        $code2 = if ($idx2 -ge 0) { [int](ConvertTo-TrimmedString $raw2.Substring($idx2 + 1)) } else { 0 }
        $body2 = if ($idx2 -gt 0) { $raw2.Substring(0, $idx2) } else { '' }
        if ($code2 -ne 200) {
            throw "ABORT B1: panduan/extract-upload siklus $c gagal dengan HTTP $code2"
        }
        $json2 = ConvertFrom-JsonSafe -JsonText $body2 -Context "panduan/extract-upload siklus $c"

        # Langkah 3: POST /api/matkul-recommender/rekomendasi
        $rekReqObj = [ordered]@{
            khs          = $json1.preview
            panduan_text = [string]$json2.text
        }
        $rekReqStr = $rekReqObj | ConvertTo-Json -Depth 10 -Compress
        if ($null -eq $savedRekPayload) {
            $savedRekPayload = $rekReqStr
        }

        $tmpRek = Join-Path $env:TEMP "baseline_b1_rek_$c.json"
        [System.IO.File]::WriteAllText($tmpRek, $rekReqStr, $utf8NoBom)
        $code3 = 0
        $body3 = ''
        $sw3 = [Diagnostics.Stopwatch]::StartNew()
        try {
            $raw3 = ConvertTo-TrimmedString (& curl.exe -s -w "`n%{http_code}" -X POST "http://127.0.0.1:8080/api/matkul-recommender/rekomendasi" -H "Authorization: Bearer $tok" -H "Content-Type: application/json" --data-binary "@$tmpRek")
            $sw3.Stop()
            $idx3 = $raw3.LastIndexOf("`n")
            $code3 = if ($idx3 -ge 0) { [int](ConvertTo-TrimmedString $raw3.Substring($idx3 + 1)) } else { 0 }
            $body3 = if ($idx3 -gt 0) { $raw3.Substring(0, $idx3) } else { '' }
        }
        finally {
            Remove-Item $tmpRek -Force -ErrorAction SilentlyContinue
        }

        $cycleSw.Stop()
        if (Test-LlmQuotaError -HttpCode $code3 -BodyText $body3) {
            throw "ABORT B1: Panggilan LLM pada /rekomendasi siklus $c mengembalikan kuota habis / 429 (HTTP $code3). Dihentikan tanpa retry."
        }

        $json3 = ConvertFrom-JsonSafe -JsonText $body3 -Context "rekomendasi siklus $c"
        $hasKeys = (
            $null -ne $json3 -and
            $null -ne $json3.PSObject.Properties['semester_target'] -and
            $null -ne $json3.PSObject.Properties['ringkasan'] -and
            $null -ne $json3.PSObject.Properties['evaluasi_nilai'] -and
            $null -ne $json3.PSObject.Properties['rekomendasi_semester_depan']
        )
        $rekList = @($json3.rekomendasi_semester_depan)
        $itemsValid = ($rekList.Count -gt 0)
        foreach ($it in $rekList) {
            if ([string]::IsNullOrWhiteSpace([string]$it.kode) -or [string]::IsNullOrWhiteSpace([string]$it.nama)) {
                $itemsValid = $false
            }
        }
        $techPass = ($code1 -eq 200 -and $code2 -eq 200 -and $code3 -eq 200 -and $hasKeys -and $itemsValid)

        $b1Rows.Add([pscustomobject]@{
            cycle             = $c
            khs_upload_code   = $code1
            khs_upload_sec    = [math]::Round($sw1.Elapsed.TotalSeconds, 2)
            panduan_code      = $code2
            panduan_sec       = [math]::Round($sw2.Elapsed.TotalSeconds, 2)
            rekomendasi_code  = $code3
            rekomendasi_sec   = [math]::Round($sw3.Elapsed.TotalSeconds, 2)
            total_cycle_sec   = [math]::Round($cycleSw.Elapsed.TotalSeconds, 2)
            semester_target   = $json3.semester_target
            rekomendasi_count = $rekList.Count
            evaluasi_count    = @($json3.evaluasi_nilai).Count
            technical_pass    = $techPass
        })
        Write-Host ("  [B1 Siklus {0}] khs={1} ({2}s) panduan={3} ({4}s) rek={5} ({6}s) total={7}s items={8} pass={9}" -f $c, $code1, [math]::Round($sw1.Elapsed.TotalSeconds, 2), $code2, [math]::Round($sw2.Elapsed.TotalSeconds, 2), $code3, [math]::Round($sw3.Elapsed.TotalSeconds, 2), [math]::Round($cycleSw.Elapsed.TotalSeconds, 2), $rekList.Count, $techPass)
    }

    # B2. Pasangan langsung vs gateway pada /api/rekomendasi Matkul (5 pasang, jeda >= 10 detik)
    Write-Host "`n[B2] Menjalankan 5 pasang langsung vs gateway pada /api/rekomendasi Matkul..."
    $b2Pairs = New-Object System.Collections.Generic.List[object]
    $b2PayloadB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($savedRekPayload))

    for ($p = 1; $p -le 5; $p++) {
        Update-TestToken -GatewayHostUrl 'http://127.0.0.1:8080'
        $tok = $script:AuthState.Token
        $order = if ($p % 2 -eq 1) { @('direct', 'gateway') } else { @('gateway', 'direct') }
        $pairRes = @{}

        foreach ($mode in $order) {
            $targetUrl = if ($mode -eq 'direct') { 'http://matkul:3000/api/rekomendasi' } else { 'http://nginx/api/matkul-recommender/rekomendasi' }
            $pyB2 = @"
import urllib.request, time, json, base64
body = base64.b64decode('$b2PayloadB64')
req = urllib.request.Request(
    '$targetUrl',
    data=body,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer $tok'},
    method='POST'
)
t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        dt = time.perf_counter() - t0
        data = json.loads(r.read().decode('utf-8'))
        print(json.dumps({'code': r.status, 'sec': round(dt, 3), 'count': len(data.get('rekomendasi_semester_depan', []))}))
except Exception as e:
    dt = time.perf_counter() - t0
    code = getattr(e, 'code', 0)
    print(json.dumps({'code': code, 'sec': round(dt, 3), 'error': str(e)[:120]}))
"@
            $rawB2 = $pyB2 | & docker compose exec -T microcred-api python - 2>$null
            $outStr = ConvertTo-TrimmedString $rawB2
            $pairRes[$mode] = ConvertFrom-JsonSafe -JsonText $outStr -Context "B2 pasang $p ($mode)"
            Start-Sleep -Seconds 10
        }

        $dSec = [double]$pairRes['direct'].sec
        $gSec = [double]$pairRes['gateway'].sec
        $b2Pairs.Add([pscustomobject]@{
            pair            = $p
            order           = ($order -join ' -> ')
            direct_code     = $pairRes['direct'].code
            direct_sec      = $dSec
            gateway_code    = $pairRes['gateway'].code
            gateway_sec     = $gSec
            diff_gw_minus_d = [math]::Round(($gSec - $dSec), 3)
        })
    }

    # B3. Pasangan langsung vs gateway pada Judul get-recommendations (10 pasang, jeda >= 12 detik)
    Write-Host "`n[B3] Menjalankan 10 pasang langsung vs gateway pada Judul get-recommendations..."
    $b3Pairs = New-Object System.Collections.Generic.List[object]
    $consecFail = 0
    for ($p = 1; $p -le 10; $p++) {
        Update-TestToken -GatewayHostUrl 'http://127.0.0.1:8080'
        $tok = $script:AuthState.Token
        $order = if ($p % 2 -eq 1) { @('direct', 'gateway') } else { @('gateway', 'direct') }
        $pairRes = @{}

        foreach ($mode in $order) {
            $targetUrl = if ($mode -eq 'direct') { 'http://judul-api:8001/get-recommendations' } else { 'http://nginx/api/judul-recommender/get-recommendations' }
            $pyB3 = @"
import urllib.request, time, json
body = json.dumps({'interests': 'sistem deteksi kantuk untuk pengemudi menggunakan computer vision dan machine learning'}).encode('utf-8')
req = urllib.request.Request(
    '$targetUrl',
    data=body,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer $tok'},
    method='POST'
)
t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        dt = time.perf_counter() - t0
        data = json.loads(r.read().decode('utf-8'))
        recs = data.get('rekomendasi', [])
        refs = [len(x.get('referensi', [])) for x in recs]
        print(json.dumps({'code': r.status, 'sec': round(dt, 3), 'recs': len(recs), 'refs': refs}))
except Exception as e:
    dt = time.perf_counter() - t0
    code = getattr(e, 'code', 0)
    print(json.dumps({'code': code, 'sec': round(dt, 3), 'recs': 0, 'refs': [], 'error': str(e)[:120]}))
"@
            $rawB3 = $pyB3 | & docker compose exec -T microcred-api python - 2>$null
            $outStr = ConvertTo-TrimmedString $rawB3
            $resObj = ConvertFrom-JsonSafe -JsonText $outStr -Context "B3 pasang $p ($mode)"
            $pairRes[$mode] = $resObj
            if ($resObj.code -ne 200) {
                $consecFail++
                if ($consecFail -ge 3) {
                    throw "ABORT B3: Tiga kegagalan beruntun terdeteksi pada Judul get-recommendations."
                }
            }
            else {
                $consecFail = 0
            }
            Start-Sleep -Seconds 12
        }

        $b3Pairs.Add([pscustomobject]@{
            pair            = $p
            order           = ($order -join ' -> ')
            direct_code     = $pairRes['direct'].code
            direct_sec      = [double]$pairRes['direct'].sec
            direct_recs     = $pairRes['direct'].recs
            direct_refs     = ($pairRes['direct'].refs -join ',')
            gateway_code    = $pairRes['gateway'].code
            gateway_sec     = [double]$pairRes['gateway'].sec
            gateway_recs    = $pairRes['gateway'].recs
            gateway_refs    = ($pairRes['gateway'].refs -join ',')
            diff_gw_minus_d = [math]::Round(([double]$pairRes['gateway'].sec - [double]$pairRes['direct'].sec), 3)
        })
    }

    # B4. Uji ulang alur Micro-cred via gateway/tests/e2e-flow.ps1 (1 probe + 5 siklus utama = 6 siklus)
    Write-Host "`n[B4] Menjalankan uji ulang alur Micro-cred (1 siklus probe + 5 siklus utama = 6 siklus)..."
    $e2eScript = Join-Path $repoRoot 'gateway\tests\e2e-flow.ps1'
    $e2eSource = Get-Content $e2eScript -Raw
    if ($e2eSource -match 'docs[\\/]+e2e-results\.md') {
        throw "ABORT B4: Skrip e2e-flow.ps1 terdeteksi menulis ke docs/e2e-results.md!"
    }

    $b4ProbeJson = Join-Path $outDir 'b4-probe-1cycle.json'
    $b4StartUtc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    & powershell.exe -NoProfile -File $e2eScript -Cycles 1 -OutJson $b4ProbeJson

    $apiLogsAfter1 = @(docker compose logs --no-log-prefix --since $b4StartUtc microcred-api microcred-worker 2>$null)
    $creditIssues = @($apiLogsAfter1 | Where-Object { $_ -match '(?i)gpt_rate_limited|no credits|insufficient_quota|essay_scoring_failed' })
    if ($creditIssues.Count -gt 0) {
        throw "ABORT B4: Siklus probe pertama Micro-cred mendeteksi kendala kredit/skoring di log ($($creditIssues.Count) baris). Dihentikan sesuai aturan B4."
    }

    $b4FullJson = Join-Path $outDir 'b4-e2e-5cycles.json'
    & powershell.exe -NoProfile -File $e2eScript -Cycles 5 -OutJson $b4FullJson

    # (6) Hitung event log sejak $b4StartUtc (mencakup 6 siklus: 1 probe + 5 siklus utama)
    $b4AllLogs = @(docker compose logs --no-log-prefix --since $b4StartUtc microcred-api microcred-worker 2>$null)
    $b4LogEvents = [ordered]@{
        essay_scoring_failed        = @($b4AllLogs | Where-Object { $_ -match 'essay_scoring_failed' }).Count
        essay_scoring_fallback_used = @($b4AllLogs | Where-Object { $_ -match 'essay_scoring_fallback_used' }).Count
        rag_no_matches              = @($b4AllLogs | Where-Object { $_ -match 'rag_no_matches' }).Count
        rag_fallback_activated      = @($b4AllLogs | Where-Object { $_ -match 'rag_fallback_activated' }).Count
        gpt_rate_limited            = @($b4AllLogs | Where-Object { $_ -match 'gpt_rate_limited' }).Count
    }

    $phaseBOut = Join-Path $outDir 'phase-b-summary.json'
    ([ordered]@{
        generated_utc           = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
        phase                   = 'B'
        pocketbase_records_note = 'tidak diukur oleh skrip, diverifikasi manual'
        b1_matkul               = $b1Rows
        b2_matkul               = $b2Pairs
        b3_judul                = $b3Pairs
        b4_cycles_note          = 'B4 menjalankan total 6 siklus (1 siklus probe + 5 siklus utama)'
        b4_started_utc          = $b4StartUtc
        b4_log_events           = $b4LogEvents
        b4_json_path            = $b4FullJson
    } | ConvertTo-Json -Depth 10) | Set-Content -Path $phaseBOut -Encoding utf8
    Write-Host "`nFase B selesai. Hasil disimpan di $phaseBOut"
}

# ===========================================================================
# MODE REPORT (-Report): Hasilkan docs/baseline-comparison-tables.md dari out/phase-a-summary.json
# ===========================================================================
function Invoke-GenerateBaselineTables {
    $summaryJsonPath = Join-Path $outDir 'phase-a-summary.json'
    $tablesMdPath = Join-Path $repoRoot 'docs\baseline-comparison-tables.md'

    $expectedSpecs = @(
        @{ Id = 'M1-20rps';  Service = 'Micro-cred'; Endpoint = 'GET /tracks';                                      Rate = 20  },
        @{ Id = 'M1-50rps';  Service = 'Micro-cred'; Endpoint = 'GET /tracks';                                      Rate = 50  },
        @{ Id = 'M1-100rps'; Service = 'Micro-cred'; Endpoint = 'GET /tracks';                                      Rate = 100 },
        @{ Id = 'M2-20rps';  Service = 'Micro-cred'; Endpoint = 'GET /auth/me';                                     Rate = 20  },
        @{ Id = 'M2-50rps';  Service = 'Micro-cred'; Endpoint = 'GET /auth/me';                                     Rate = 50  },
        @{ Id = 'J1-50rps';  Service = 'Judul';      Endpoint = 'GET /';                                            Rate = 50  },
        @{ Id = 'J1-200rps'; Service = 'Judul';      Endpoint = 'GET /';                                            Rate = 200 },
        @{ Id = 'K1-20rps';  Service = 'Matkul';     Endpoint = 'POST /api/panduan/extract-upload (non-PDF -> 400)'; Rate = 20  },
        @{ Id = 'K1-50rps';  Service = 'Matkul';     Endpoint = 'POST /api/panduan/extract-upload (non-PDF -> 400)'; Rate = 50  },
        @{ Id = 'K2-5rps';   Service = 'Matkul';     Endpoint = 'POST /api/panduan/extract-upload (PDF valid -> 200)'; Rate = 5 },
        @{ Id = 'K2-10rps';  Service = 'Matkul';     Endpoint = 'POST /api/panduan/extract-upload (PDF valid -> 200)'; Rate = 10 }
    )

    $condMap = @{}
    $genUtc = 'tidak diukur'
    $repCount = 'tidak diukur'

    if (-not (Test-Path $summaryJsonPath)) {
        Write-Warning "[Mode Report] Berkas $summaryJsonPath belum tersedia. Menghasilkan $tablesMdPath dengan nilai 'tidak diukur'."
    }
    else {
        $raw = Get-Content $summaryJsonPath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            Write-Warning "[Mode Report] Berkas $summaryJsonPath kosong. Menghasilkan $tablesMdPath dengan nilai 'tidak diukur'."
        }
        else {
            $parsed = ConvertFrom-JsonSafe -JsonText $raw -Context $summaryJsonPath
            if ($parsed.generated_utc) { $genUtc = [string]$parsed.generated_utc }
            if ($parsed.repeats) { $repCount = [string]$parsed.repeats }
            foreach ($c in @($parsed.conditions)) {
                if ($c -and $c.id) {
                    $condMap[[string]$c.id] = $c
                }
            }
            if ($condMap.Count -lt $expectedSpecs.Count) {
                Write-Warning "[Mode Report] Data di $summaryJsonPath belum lengkap ($($condMap.Count)/$($expectedSpecs.Count) kondisi). Kondisi yang belum ada ditulis 'tidak diukur'."
            }
        }
    }

    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine('# Tabel Hasil Pengujian Baseline Fase A (`docs/baseline-comparison-tables.md`)')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("Dihasilkan oleh: ``powershell -File gateway/tests/baseline/run-baseline.ps1 -Report``  ")
    [void]$sb.AppendLine("Sumber data: ``gateway/tests/baseline/out/phase-a-summary.json`` (Waktu sumber: ``$genUtc``, Ulangan target: ``$repCount``)  ")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('> [!NOTE]')
    [void]$sb.AppendLine('> Sel tanpa data pengukuran aktual ditulis **`tidak diukur`** (tidak diestimasi dan tidak diisi nol).')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('---')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## 1. Tabel Tiga Jalur per Kondisi (`direct`, `noauth`, `gateway`)')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('| Kondisi | Layanan | Endpoint | Laju Target (req/s) | Jalur | p50 Median [Min–Maks] (ms) | p95 Median [Min–Maks] (ms) | p99 Median (ms) | Rata-rata (ms) | Throughput (req/s) | Kegagalan (%) | Dropped Iterations | Interval Stats Median (s) |')
    [void]$sb.AppendLine('|---|---|---|---:|---|---|---|---|---|---|---|---|---|')

    foreach ($spec in $expectedSpecs) {
        $cid = $spec.Id
        $cObj = if ($condMap.ContainsKey($cid)) { $condMap[$cid] } else { $null }
        foreach ($pm in @('direct', 'noauth', 'gateway')) {
            $pObj = $null
            if ($cObj -and -not $cObj.skipped -and $cObj.paths -and $cObj.paths.PSObject.Properties[$pm]) {
                $pObj = $cObj.paths.PSObject.Properties[$pm].Value
            }
            if ($null -eq $pObj) {
                [void]$sb.AppendLine("| **$cid** | $($spec.Service) | ``$($spec.Endpoint)`` | $($spec.Rate) | ``$pm`` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |")
            }
            else {
                $p50Cell = ('{0:N2} [{1:N2}–{2:N2}]' -f [double]$pObj.p50_median_ms, [double]$pObj.p50_min_ms, [double]$pObj.p50_max_ms)
                $p95Cell = ('{0:N2} [{1:N2}–{2:N2}]' -f [double]$pObj.p95_median_ms, [double]$pObj.p95_min_ms, [double]$pObj.p95_max_ms)
                $p99Cell = ('{0:N2}' -f [double]$pObj.p99_median_ms)
                $avgCell = ('{0:N2}' -f [double]$pObj.avg_median_ms)
                $rpsCell = ('{0:N2}' -f [double]$pObj.throughput_median_rps)
                $errCell = ('{0:N2}%' -f [double]$pObj.error_rate_median_pct)
                $drpCell = ('{0}' -f $pObj.dropped_median)
                $intCell = if ($null -ne $pObj.sample_interval_median_sec) { ('{0:N2}' -f [double]$pObj.sample_interval_median_sec) } else { 'tidak diukur' }
                [void]$sb.AppendLine("| **$cid** | $($spec.Service) | ``$($spec.Endpoint)`` | $($spec.Rate) | ``$pm`` | $p50Cell | $p95Cell | $p99Cell | $avgCell | $rpsCell | $errCell | $drpCell | $intCell |")
            }
        }
    }

    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('---')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## 2. Tabel Selisih Antar Jalur ($\Delta_{\text{proxy}}$, $\Delta_{\text{auth}}$, $\Delta_{\text{total}}$) dan Tafsir')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('| Kondisi | $\Delta_{\text{proxy}}$ p50 [Min–Maks] (ms) | $\Delta_{\text{auth}}$ p50 [Min–Maks] (ms) | $\Delta_{\text{total}}$ p50 [Min–Maks] (ms) | $\Delta_{\text{proxy}}$ p95 [Min–Maks] (ms) | $\Delta_{\text{auth}}$ p95 [Min–Maks] (ms) | $\Delta_{\text{total}}$ p95 [Min–Maks] (ms) | Tafsir $\Delta_{\text{proxy}}$ | Tafsir $\Delta_{\text{auth}}$ | Tafsir $\Delta_{\text{total}}$ |')
    [void]$sb.AppendLine('|---|---|---|---|---|---|---|---|---|---|')

    foreach ($spec in $expectedSpecs) {
        $cid = $spec.Id
        $cObj = if ($condMap.ContainsKey($cid)) { $condMap[$cid] } else { $null }
        $dObj = if ($cObj -and $cObj.differences) { $cObj.differences } else { $null }
        if ($null -eq $dObj -or -not $dObj.PSObject.Properties['proxy_noauth_minus_direct']) {
            [void]$sb.AppendLine("| **$cid** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |")
        }
        else {
            $dp = $dObj.proxy_noauth_minus_direct
            $da = $dObj.auth_gateway_minus_noauth
            $dt = $dObj.total_gateway_minus_direct

            $dp50 = ('{0:N2} [{1:N2}..{2:N2}]' -f [double]$dp.p50_diff_median_ms, [double]$dp.p50_diff_min_ms, [double]$dp.p50_diff_max_ms)
            $da50 = ('{0:N2} [{1:N2}..{2:N2}]' -f [double]$da.p50_diff_median_ms, [double]$da.p50_diff_min_ms, [double]$da.p50_diff_max_ms)
            $dt50 = ('{0:N2} [{1:N2}..{2:N2}]' -f [double]$dt.p50_diff_median_ms, [double]$dt.p50_diff_min_ms, [double]$dt.p50_diff_max_ms)

            $dp95 = ('{0:N2} [{1:N2}..{2:N2}]' -f [double]$dp.p95_diff_median_ms, [double]$dp.p95_diff_min_ms, [double]$dp.p95_diff_max_ms)
            $da95 = ('{0:N2} [{1:N2}..{2:N2}]' -f [double]$da.p95_diff_median_ms, [double]$da.p95_diff_min_ms, [double]$da.p95_diff_max_ms)
            $dt95 = ('{0:N2} [{1:N2}..{2:N2}]' -f [double]$dt.p95_diff_median_ms, [double]$dt.p95_diff_min_ms, [double]$dt.p95_diff_max_ms)

            [void]$sb.AppendLine("| **$cid** | $dp50 | $da50 | $dt50 | $dp95 | $da95 | $dt95 | $($dp.interpretation) | $($da.interpretation) | $($dt.interpretation) |")
        }
    }

    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('---')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## 3. Tabel Median CPU (`%`) dan Memori (`MiB`) per Container pada Fase Ukur')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('| Kondisi | Jalur | `nginx` | `superapp-nginx-noauth` | `auth-verifier` | `microcred-api` | `db` | `judul-api` | `matkul` | `pocketbase` | `redis` |')
    [void]$sb.AppendLine('|---|---|---|---|---|---|---|---|---|---|---|')

    $containerCols = @(
        'superapp-nginx-1',
        'superapp-nginx-noauth',
        'superapp-auth-verifier-1',
        'superapp-microcred-api-1',
        'superapp-db-1',
        'superapp-judul-api-1',
        'superapp-matkul-1',
        'superapp-pocketbase-1',
        'superapp-redis-1'
    )

    foreach ($spec in $expectedSpecs) {
        $cid = $spec.Id
        $cObj = if ($condMap.ContainsKey($cid)) { $condMap[$cid] } else { $null }
        foreach ($pm in @('direct', 'noauth', 'gateway')) {
            $pObj = $null
            if ($cObj -and -not $cObj.skipped -and $cObj.paths -and $cObj.paths.PSObject.Properties[$pm]) {
                $pObj = $cObj.paths.PSObject.Properties[$pm].Value
            }
            $cells = @()
            foreach ($cn in $containerCols) {
                if ($null -ne $pObj -and $pObj.container_medians -and $pObj.container_medians.PSObject.Properties[$cn]) {
                    $cm = $pObj.container_medians.PSObject.Properties[$cn].Value
                    $cells += ('{0:N2}% / {1:N1} MiB' -f [double]$cm.median_cpu_pct, [double]$cm.median_mem_mib)
                }
                else {
                    $cells += 'tidak diukur'
                }
            }
            [void]$sb.AppendLine("| **$cid** | ``$pm`` | $($cells -join ' | ') |")
        }
    }

    [System.IO.File]::WriteAllText($tablesMdPath, $sb.ToString(), $utf8NoBom)
    Write-Host "[Mode Report] Tabel perbandingan berhasil ditulis ke $tablesMdPath"
}

if ($Report) {
    Invoke-GenerateBaselineTables
}
elseif ($Phase -eq 'A') {
    Invoke-PhaseA
}
else {
    Invoke-PhaseB
}
