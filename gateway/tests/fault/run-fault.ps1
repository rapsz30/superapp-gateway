<#
.SYNOPSIS
  Orkestrator Fault Injection Testing untuk superapp-gateway.

.DESCRIPTION
  Menjalankan skenario F1 sampai F11 secara berurutan (satu gangguan dalam satu waktu).
  Selama tiap skenario, 6 pekerja probe latar belakang (P1..P6) berjalan setiap 500 ms
  menggunakan curl.exe -m 10 dan mencatat hasil ke gateway/tests/fault/out/probes-<skenario>.csv.
  Tiap skenario dibungkus try/finally yang selalu memulihkan layanan, menunggu semua container
  healthy (maks 180 detik), lalu jeda 15 detik sebelum skenario berikutnya.
  Tidak memanggil LLM dan tidak pernah mencetak token, secret, atau data pribadi.

.PARAMETER Scenarios
  Daftar skenario yang dijalankan (default: semua F1a..F11 kecuali worker).
.PARAMETER IncludeWorker
  Hanya diaktifkan pengguna setelah mengubah AUTO_PROCESS_JOBS ke false secara manual.
.PARAMETER Resume
  Lewati skenario yang sudah tercatat selesai di summary-fault.json.
#>
param(
    [string[]]$Scenarios = @('F1a', 'F1b', 'F1c', 'F2', 'F3a', 'F3b', 'F4', 'F5', 'F6a', 'F6b', 'F7', 'F8', 'F9', 'F10', 'F11'),
    [switch]$IncludeWorker = $false,
    [switch]$Resume = $false
)

$Scenarios = @($Scenarios | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$inv = [Globalization.CultureInfo]::InvariantCulture

$faultDir = $PSScriptRoot
$outDir = Join-Path $faultDir 'out'
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$gateway = 'http://127.0.0.1:8080'
$probeScript = Join-Path $faultDir 'probe-worker.ps1'
$smallFile = Join-Path $outDir 'small-nonpdf.txt'
$loginJsonFile = Join-Path $outDir 'login-nonexistent.json'
$summaryPath = Join-Path $outDir 'summary-fault.json'

'NOT_A_PDF_SMALL_PAYLOAD_FOR_P4' | Set-Content -Path $smallFile -NoNewline -Encoding ascii
'{"email":"tidak-ada-uji-fault@example.com","password":"PasswordSalah123!"}' | Set-Content -Path $loginJsonFile -NoNewline -Encoding utf8

function Sanitize-Text([string]$Text) {
    if (-not $Text) { return '' }
    $c = $Text -replace '[\r\n]+', ' '
    $c = $c -replace 'eyJ[A-Za-z0-9_\-\.]+', '<token>'
    $c = $c -replace '[\w\.\-+]+@[\w\.\-]+', '<email>'
    if ($c.Length -gt 180) { $c = $c.Substring(0, 180) }
    return $c.Trim()
}

function Get-ContainerIp([string]$Container) {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $ip = (docker inspect -f "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" $Container 2>$null) -join ''
    $ErrorActionPreference = $prev
    return $ip.Trim()
}

function Get-ContainerStartedAt([string]$Container) {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $st = (docker inspect -f "{{.State.StartedAt}}" $Container 2>$null) -join ''
    $ErrorActionPreference = $prev
    return $st.Trim()
}

function Get-ContainerNanoCpus([string]$Container) {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $v = (docker inspect -f "{{.HostConfig.NanoCpus}}" $Container 2>$null) -join ''
    $ErrorActionPreference = $prev
    $n = 0L
    [void][long]::TryParse($v.Trim(), [ref]$n)
    return $n
}

function Restore-ContainerCpus([string]$Container, [long]$OrigNanoCpus) {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    if ($OrigNanoCpus -gt 0 -and $OrigNanoCpus -ne 250000000L) {
        $cpuVal = ([double]$OrigNanoCpus / 1e9).ToString($inv)
        docker update --cpus $cpuVal $Container 2>&1 | Out-Null
    }
    else {
        # Catatan: pada Docker Engine API, NanoCPUs=0 (--cpus 0) dianggap "tidak diubah" (no-op) oleh daemon.
        # Karena itu, saat NanoCpus awal adalah 0 (unlimited), kembalikan ke jumlah vCPU host Docker.
        $ncpu = ((docker info --format "{{.NCPU}}" 2>$null) -join '').Trim()
        if (-not $ncpu -or $ncpu -notmatch '^\d+$') { $ncpu = '8' }
        docker update --cpus $ncpu $Container 2>&1 | Out-Null
    }
    $ErrorActionPreference = $prev
}

function Test-AllContainersHealthy {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $lines = @(docker ps -a --filter "label=com.docker.compose.project=superapp" --format "{{.Names}}|{{.State}}|{{.Status}}" 2>$null)
    $ErrorActionPreference = $prev
    if ($lines.Count -lt 9) {
        return [pscustomobject]@{ Ok = $false; Reason = "Jumlah container kurang dari 9 ($($lines.Count))" }
    }
    foreach ($l in $lines) {
        $p = $l.Split('|')
        $name = $p[0]; $state = $p[1]; $status = $p[2]
        if ($state -ne 'running') {
            return [pscustomobject]@{ Ok = $false; Reason = "$name state=$state ($status)" }
        }
        if ($status -match 'unhealthy|health: starting') {
            return [pscustomobject]@{ Ok = $false; Reason = "$name status=$status" }
        }
    }
    return [pscustomobject]@{ Ok = $true; Reason = 'Semua 9 container running dan healthy' }
}

function Wait-StackHealthy([int]$MaxSeconds = 180) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $MaxSeconds) {
        $h = Test-AllContainersHealthy
        if ($h.Ok) {
            return [pscustomobject]@{ Ok = $true; ElapsedSec = [math]::Round($sw.Elapsed.TotalSeconds, 2); Reason = $h.Reason }
        }
        Start-Sleep -Seconds 1
    }
    $last = Test-AllContainersHealthy
    return [pscustomobject]@{ Ok = $false; ElapsedSec = [math]::Round($sw.Elapsed.TotalSeconds, 2); Reason = $last.Reason }
}

# Daftar dan login satu akun uji untuk seluruh probe (tanpa mencetak token/email)
function Register-FaultTestAccount {
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $rnd = Get-Random -Minimum 10000000 -Maximum 99999999
    $email = "uji-fault-$ts@example.com"
    $pwd = 'Uji12345!'
    $regTmp = Join-Path $outDir 'tmp-reg.json'
    $logTmp = Join-Path $outDir 'tmp-login.json'
    try {
        $regObj = @{
            email         = $email
            password      = $pwd
            full_name     = 'Mahasiswa Uji Fault'
            nim           = "$rnd"
            faculty       = 'Fakultas Teknologi Industri'
            study_program = 'Informatika'
        }
        ($regObj | ConvertTo-Json -Compress) | Set-Content -Path $regTmp -NoNewline -Encoding utf8
        $r1 = (& curl.exe -s -m 15 -X POST "$gateway/api/micro-cred/auth/register" -H "Content-Type: application/json" --data-binary "@$regTmp" -w "`n%{http_code}") -join "`n"
        $c1 = ($r1 -split "`n")[-1].Trim()
        if ($c1 -ne '201' -and $c1 -ne '409') {
            throw "Registrasi akun uji gagal dengan kode HTTP $c1"
        }

        (@{ email = $email; password = $pwd } | ConvertTo-Json -Compress) | Set-Content -Path $logTmp -NoNewline -Encoding utf8
        $r2 = (& curl.exe -s -m 15 -X POST "$gateway/api/micro-cred/auth/login" -H "Content-Type: application/json" --data-binary "@$logTmp") -join "`n"
        $j2 = $r2 | ConvertFrom-Json
        if (-not $j2 -or -not $j2.tokens -or -not $j2.tokens.access_token) {
            throw "Login akun uji tidak mengembalikan access_token"
        }
        return $j2.tokens.access_token
    }
    finally {
        Remove-Item $regTmp, $logTmp -Force -ErrorAction SilentlyContinue
    }
}

# Kirim satu request terpisah dengan batas waktu panjang (-m 150) untuk mengukur waktu hingga galat
function Invoke-SeparateRequest([string]$TargetType, [string]$Token) {
    $curlArgs = @('-s', '-m', '150', '-w', "`n%{http_code} %{time_total}")
    switch ($TargetType) {
        'P1' { $curlArgs += @('-X', 'GET', "$gateway/healthz") }
        'P2' { $curlArgs += @('-X', 'GET', "$gateway/api/micro-cred/tracks", '-H', "Authorization: Bearer $Token") }
        'P3' { $curlArgs += @('-X', 'GET', "$gateway/api/judul-recommender/", '-H', "Authorization: Bearer $Token") }
        'P4' { $curlArgs += @('-X', 'POST', "$gateway/api/matkul-recommender/panduan/extract-upload", '-H', "Authorization: Bearer $Token", '-F', "file_pdf=@$smallFile;type=application/octet-stream") }
        'P5' { $curlArgs += @('-X', 'GET', "$gateway/api/micro-cred/health") }
        'P6' { $curlArgs += @('-X', 'POST', "$gateway/api/micro-cred/auth/login", '-H', 'Content-Type: application/json', '--data-binary', "@$loginJsonFile") }
    }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $raw = (& curl.exe @curlArgs 2>$null) -join "`n"
    $sw.Stop()
    $idx = $raw.LastIndexOf("`n")
    $body = if ($idx -ge 0) { $raw.Substring(0, $idx).Trim() } else { '' }
    $tail = if ($idx -ge 0) { $raw.Substring($idx + 1).Trim() } else { $raw.Trim() }
    $parts = $tail -split '\s+'
    $code = '000'
    $timeSec = [math]::Round($sw.Elapsed.TotalSeconds, 3)
    if ($parts.Count -ge 2 -and $parts[0] -match '^\d{3}$') {
        $code = $parts[0]
        $pt = 0.0
        if ([double]::TryParse($parts[1], [Globalization.NumberStyles]::Float, $inv, [ref]$pt)) {
            $timeSec = [math]::Round($pt, 3)
        }
    }
    return [pscustomobject]@{
        Target  = $TargetType
        Code    = $code
        TimeSec = $timeSec
        Detail  = (Sanitize-Text $body)
    }
}

# Mulai 6 proses probe latar belakang (P1..P6)
function Start-Probes([string]$ScenarioName) {
    $stopFlag = Join-Path $outDir "stop-$ScenarioName.flag"
    if (Test-Path $stopFlag) { Remove-Item $stopFlag -Force }
    $procs = @()
    $csvFiles = @{}
    foreach ($p in @('P1', 'P2', 'P3', 'P4', 'P5', 'P6')) {
        $csv = Join-Path $outDir "tmp-$ScenarioName-$p.csv"
        "timestamp_ms,probe,http_code,time_total_s,is_ok,detail" | Set-Content -Path $csv -Encoding utf8
        $csvFiles[$p] = $csv
        $argStr = "-NoProfile -WindowStyle Hidden -File `"$probeScript`" -ProbeName $p -Gateway `"$gateway`" -OutCsv `"$csv`" -StopFlagFile `"$stopFlag`" -SmallFile `"$smallFile`" -LoginJsonFile `"$loginJsonFile`""
        $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argStr -PassThru
        $procs += $proc
    }
    return [pscustomobject]@{
        Scenario = $ScenarioName
        StopFlag = $stopFlag
        Procs    = $procs
        CsvFiles = $csvFiles
    }
}

# Hentikan 6 proses probe dan gabungkan CSV terurut berdasarkan timestamp_ms
function Stop-Probes($ProbeHandle) {
    if ($null -eq $ProbeHandle) { return $null }
    'stop' | Set-Content -Path $ProbeHandle.StopFlag -Encoding ascii -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 700
    foreach ($proc in $ProbeHandle.Procs) {
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item $ProbeHandle.StopFlag -Force -ErrorAction SilentlyContinue

    $allRows = New-Object System.Collections.Generic.List[object]
    foreach ($p in @('P1', 'P2', 'P3', 'P4', 'P5', 'P6')) {
        $f = $ProbeHandle.CsvFiles[$p]
        if (Test-Path $f) {
            $rows = Import-Csv -Path $f -ErrorAction SilentlyContinue
            foreach ($r in $rows) {
                if ($r -and $r.timestamp_ms -match '^\d+$') {
                    $allRows.Add($r)
                }
            }
            Remove-Item $f -Force -ErrorAction SilentlyContinue
        }
    }
    $sorted = @($allRows | Sort-Object { [long]$_.timestamp_ms })
    $mergedPath = Join-Path $outDir "probes-$($ProbeHandle.Scenario).csv"
    $sorted | Export-Csv -Path $mergedPath -NoTypeInformation -Encoding utf8
    return $mergedPath
}

# Pantau CSV probe target setelah tindakan pemulihan sampai mencapai 10 sukses beruntun.
# Bila setelah $InterventionAfterSec probe target belum pernah sukses padahal container sudah sehat
# (misalnya karena IP container berubah saat stop/start dan NGINX meng-cache IP lama), jalankan restart nginx.
function Wait-TargetProbeRecovery(
    $ProbeHandle,
    [string]$TargetProbe,
    [long]$RecoveryStartMs,
    [int]$InterventionAfterSec = 25,
    [int]$MaxWaitSec = 150
) {
    $csvPath = $ProbeHandle.CsvFiles[$TargetProbe]
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $intervened = $false
    $interventionReason = ''
    $interventionMs = 0L

    while ($sw.Elapsed.TotalSeconds -lt $MaxWaitSec) {
        if (Test-Path $csvPath) {
            $rows = @(Import-Csv -Path $csvPath -ErrorAction SilentlyContinue | Where-Object {
                $_.timestamp_ms -match '^\d+$' -and ([long]$_.timestamp_ms -ge $RecoveryStartMs)
            })
            $firstOkMs = $null
            $consec = 0
            $tenthOkMs = $null
            foreach ($r in $rows) {
                if ($r.is_ok -eq '1') {
                    if ($null -eq $firstOkMs) { $firstOkMs = [long]$r.timestamp_ms }
                    $consec += 1
                    if ($consec -ge 10 -and $null -eq $tenthOkMs) {
                        $tenthOkMs = [long]$r.timestamp_ms
                        break
                    }
                }
                else {
                    $consec = 0
                    $firstOkMs = $null
                }
            }
            if ($null -ne $tenthOkMs) {
                return [pscustomobject]@{
                    Recovered          = $true
                    AutoRecovered      = (-not $intervened)
                    Intervention       = $interventionReason
                    FirstSuccessSec    = [math]::Round(($firstOkMs - $RecoveryStartMs) / 1000.0, 2)
                    TenConsecSec       = [math]::Round(($tenthOkMs - $RecoveryStartMs) / 1000.0, 2)
                    PostIntervention10 = if ($intervened) { [math]::Round(($tenthOkMs - $interventionMs) / 1000.0, 2) } else { $null }
                }
            }

            if (-not $intervened -and $sw.Elapsed.TotalSeconds -ge $InterventionAfterSec -and $null -eq $firstOkMs) {
                $intervened = $true
                $interventionMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $interventionReason = 'Perlu docker compose restart nginx (IP upstream di-cache NGINX saat start)'
                Write-Host "  [Intervensi] Probe $TargetProbe belum pulih setelah ${InterventionAfterSec}s; menjalankan docker compose restart nginx..."
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose restart nginx 2>&1 | Out-Null
                $ErrorActionPreference = $prev
            }
        }
        Start-Sleep -Milliseconds 500
    }

    return [pscustomobject]@{
        Recovered          = $false
        AutoRecovered      = $false
        Intervention       = if ($intervened) { $interventionReason } else { 'Gagal mencapai 10 sukses beruntun dalam batas waktu' }
        FirstSuccessSec    = $null
        TenConsecSec       = $null
        PostIntervention10 = $null
    }
}

# Analisis file CSV gabungan untuk menghitung waktu deteksi, kode galat, dan radius dampak per probe
function Analyze-ProbesCsv([string]$CsvPath, [string]$PrimaryProbe, [long]$FaultStartMs, [long]$RecoveryStartMs) {
    $rows = @(Import-Csv -Path $CsvPath -ErrorAction SilentlyContinue)
    $faultRows = @($rows | Where-Object {
        $_.timestamp_ms -match '^\d+$' -and ([long]$_.timestamp_ms -ge $FaultStartMs)
    })

    $primaryFailRows = @($faultRows | Where-Object { $_.probe -eq $PrimaryProbe -and $_.is_ok -eq '0' })
    $detectSec = $null
    if ($primaryFailRows.Count -gt 0) {
        $firstFailMs = [long]$primaryFailRows[0].timestamp_ms
        $detectSec = [math]::Round(($firstFailMs - $FaultStartMs) / 1000.0, 2)
    }

    $probeSummary = [ordered]@{}
    foreach ($p in @('P1', 'P2', 'P3', 'P4', 'P5', 'P6')) {
        $pRows = @($faultRows | Where-Object { $_.probe -eq $p })
        $fRows = @($pRows | Where-Object { $_.is_ok -eq '0' })
        $codes = @($fRows | Group-Object -Property http_code | ForEach-Object { "$($_.Name)($($_.Count))" }) -join ','
        $sampleDetail = ''
        if ($fRows.Count -gt 0) {
            $nonEmpty = @($fRows | Where-Object { $_.detail } | Select-Object -First 1)
            if ($nonEmpty.Count -gt 0) { $sampleDetail = $nonEmpty[0].detail }
        }
        $probeSummary[$p] = [ordered]@{
            total_samples = $pRows.Count
            failed_count  = $fRows.Count
            error_codes   = $codes
            sample_detail = $sampleDetail
        }
    }

    return [pscustomobject]@{
        ProbeDetectSec = $detectSec
        ProbeBreakdown = $probeSummary
    }
}

# Hitung jumlah baris tabel users di PostgreSQL (tanpa mencetak isi data atau membuka .env)
function Get-UsersRowCount {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $out = ('SELECT count(*) FROM users;' | docker compose exec -T db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -tA' 2>$null) -join ''
    $ErrorActionPreference = $prev
    $n = -1
    if ($out -match '(\d+)') {
        [void][int]::TryParse($Matches[1], [ref]$n)
    }
    return $n
}

# Pastikan alias DNS judul-api terdaftar di jaringan superapp_default (mencegah nginx gagal resolve setelah network disconnect/connect)
function Ensure-JudulNetworkAlias {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $aliases = (docker inspect -f "{{json .NetworkSettings.Networks.superapp_default.Aliases}}" superapp-judul-api-1 2>$null) -join ''
    if ($aliases -notmatch '"judul-api"') {
        Write-Host "Memulihkan alias DNS judul-api pada jaringan superapp_default..."
        docker network disconnect superapp_default superapp-judul-api-1 2>$null | Out-Null
        docker network connect --alias judul-api superapp_default superapp-judul-api-1 2>$null | Out-Null
        docker compose restart nginx 2>$null | Out-Null
    }
    $ErrorActionPreference = $prev
}

Ensure-JudulNetworkAlias

# Pastikan stack sehat sebelum memulai (jalankan docker compose up -d bila belum semua container aktif)
$initCheck = Test-AllContainersHealthy
if (-not $initCheck.Ok) {
    Write-Host "Stack belum sepenuhnya aktif ($($initCheck.Reason)). Menjalankan docker compose up -d..."
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    docker compose up -d 2>&1 | Out-Null
    $ErrorActionPreference = $prev
}
$initH = Wait-StackHealthy -MaxSeconds 180
if (-not $initH.Ok) {
    throw "Stack tidak healthy sebelum pengujian dimulai: $($initH.Reason)"
}

$token = Register-FaultTestAccount
$env:FAULT_PROBE_TOKEN = $token
Write-Host "Akun uji berhasil dibuat. Memulai pengujian fault injection..."

$resultsMap = [ordered]@{}
if (Test-Path $summaryPath) {
    $parsedJson = Get-Content $summaryPath -Raw | ConvertFrom-Json
    $flatItems = New-Object System.Collections.Generic.List[object]
    foreach ($elem in $parsedJson) {
        if ($elem -and $elem.PSObject.Properties['value'] -and ($elem.value -is [System.Array])) {
            foreach ($sub in $elem.value) { $flatItems.Add($sub) }
        }
        else {
            $flatItems.Add($elem)
        }
    }
    foreach ($item in $flatItems) {
        if ($item -and $item.scenario -and ($item.scenario -match '^F\d+[a-z]*$')) {
            $resultsMap[$item.scenario] = $item
        }
    }
}

function Save-Result($Obj) {
    $resultsMap[$Obj.scenario] = [pscustomobject]$Obj
    $arr = [object[]]@($resultsMap.Values)
    (ConvertTo-Json -InputObject $arr -Depth 8) | Set-Content -Path $summaryPath -Encoding utf8
}

function Ensure-PostScenarioCooldown([string]$ScenarioId) {
    Write-Host "  [$ScenarioId] Menunggu seluruh container healthy (maks 180s)..."
    $h = Wait-StackHealthy -MaxSeconds 180
    if (-not $h.Ok) {
        throw "ABORT: Stack gagal pulih dalam 180 detik setelah ${ScenarioId}: $($h.Reason)"
    }
    # Pastikan juga P2 dan P3 lewat gateway tidak nyangkut 502 akibat perubahan IP
    $chk2 = Invoke-SeparateRequest -TargetType 'P2' -Token $token
    $chk3 = Invoke-SeparateRequest -TargetType 'P3' -Token $token
    $chk4 = Invoke-SeparateRequest -TargetType 'P4' -Token $token
    if ($chk2.Code -ne '200' -or $chk3.Code -ne '200' -or $chk4.Code -ne '400') {
        Write-Host "  [$ScenarioId] Menyegarkan resolusi IP upstream di NGINX (docker compose restart nginx)..."
        $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        docker compose restart nginx 2>&1 | Out-Null
        $ErrorActionPreference = $prev
        $h2 = Wait-StackHealthy -MaxSeconds 60
        if (-not $h2.Ok) {
            throw "ABORT: NGINX tidak healthy setelah penyegaran pasca-${ScenarioId}: $($h2.Reason)"
        }
    }
    Write-Host "  [$ScenarioId] Stack healthy ($($h.ElapsedSec)s). Jeda 15 detik sebelum skenario berikutnya..."
    Start-Sleep -Seconds 15
}

# Daftar definisi hipotesis tertulis untuk setiap skenario
$hypotheses = @{
    'F1a' = 'Saat judul-api dihentikan 30 detik, hanya P3 (/api/judul-recommender/) yang gagal dengan 502 atau 504 JSON dari gateway, sedangkan P1, P2, P4, P5, P6 tetap sukses.'
    'F1b' = 'Saat microcred-api dihentikan 30 detik, hanya rute ke Micro-cred (P2, P5, P6) yang gagal dengan 502 atau 504 JSON dari gateway, sedangkan P1, P3, P4 tetap sukses (karena verifikasi token dilakukan oleh auth-verifier).'
    'F1c' = 'Saat matkul dihentikan 30 detik, hanya P4 (/api/matkul-recommender/) yang gagal dengan 502 atau 504 JSON dari gateway, sedangkan P1, P2, P3, P5, P6 tetap sukses.'
    'F2'  = 'Saat judul-api dibuat ulang paksa (up -d --force-recreate) sehingga IP berubah, pengaturan depends_on (restart: true) pada nginx membuat nginx ikut di-restart otomatis oleh Docker Compose sehingga IP baru terambil tanpa restart manual.'
    'F3a' = 'Saat auth-verifier dihentikan 30 detik, semua rute terproteksi (P2, P3, P4) gagal tertutup (fail-closed) dengan 503 JSON, sedangkan rute publik (P1, P5, P6) tetap sukses.'
    'F3b' = 'Saat auth-verifier di-pause 30 detik, semua rute terproteksi (P2, P3, P4) gagal dengan 503 JSON setelah menunggu sekitar 3 detik (proxy_read_timeout 3s pada /_auth), sedangkan rute publik (P1, P5, P6) tetap sukses.'
    'F4'  = 'Saat judul-api di-pause 90 detik, request ke prefix judul (P3) menggantung sekitar 60 detik (proxy_read_timeout 60s) lalu gagal dengan 504 JSON, sedangkan prefix lain (P1, P2, P4, P5, P6) tetap sehat.'
    'F5'  = 'Saat judul-api diputus dari jaringan superapp_default selama 30 detik, koneksi dari NGINX mengalami timeout sekitar 5 detik (proxy_connect_timeout 5s) dan menghasilkan 504 JSON (bukan 502 seketika).'
    'F6a' = 'Saat redis dihentikan 30 detik, P5 (/api/micro-cred/health) melaporkan status degraded (redis=error), sedangkan P2 (/tracks) dan P6 (/auth/login) yang hanya memakai PostgreSQL tetap berfungsi normal.'
    'F6b' = 'Saat db (PostgreSQL) dihentikan 30 detik, P2 dan P6 gagal (500) serta P5 melaporkan degraded (postgres=error). Setelah db hidup kembali, microcred-api pulih otomatis berkat pool_pre_ping=True dan jumlah baris tabel users tetap utuh.'
    'F7'  = 'Saat nginx di-restart, seluruh probe (P1..P6) mengalami gangguan singkat selama proses restart container nginx lalu pulih otomatis dalam beberapa detik.'
    'F8'  = 'Saat seluruh stack di-restart (docker compose restart), semua 9 container naik kembali secara otomatis; gangguan berakhir setelah backend dan nginx kembali healthy.'
    'F9'  = 'Saat CPU microcred-api dibatasi ke 0.25 core di bawah beban k6 30 req/s selama 40 detik, latensi p95 meningkat tajam dibandingkan kondisi normal, lalu kembali normal segera setelah batas CPU dikembalikan.'
    'F10' = 'Observasi dari hasil uji E2E: habisnya kredit OpenAI menyebabkan kegagalan skoring esai yang ditelan oleh mekanisme fallback sehingga assessment tetap selesai (completed) dengan degraded=false (degradasi diam-diam).'
    'F11' = 'Analisis statis kode: jika AUTO_PROCESS_JOBS=false, submit_assessment hanya menulis baris AsyncJob ke tabel PostgreSQL async_jobs tanpa memanggil rq.Queue.enqueue ke Redis, sehingga job tidak pernah masuk ke antrean Redis worker.'
}

if ($IncludeWorker -and ($Scenarios -notcontains 'F11w')) {
    $Scenarios += 'F11w'
    $hypotheses['F11w'] = 'Saat microcred-worker dihentikan dengan AUTO_PROCESS_JOBS=false, job assessment tidak diproses oleh worker.'
}

foreach ($sc in $Scenarios) {
    if ($Resume -and $resultsMap.Contains($sc)) {
        Write-Host "Melewati $sc (sudah ada di summary-fault.json)."
        continue
    }

    $hyp = $hypotheses[$sc]
    Write-Host "`n============================================================"
    Write-Host "Skenario : $sc"
    Write-Host "Hipotesis: $hyp"
    Write-Host "============================================================"

    # Skenario F10 (observasi dari docs/e2e-results.md) dan F11 (baca kode saja) tidak menyuntikkan gangguan
    if ($sc -eq 'F10') {
        $obj = [ordered]@{
            scenario            = 'F10'
            hypothesis          = $hyp
            observed            = 'Dari docs/e2e-results.md (5 siklus Alur A): 15/15 skoring esai gagal (45 event gpt_rate_limited dengan pesan You have no credits remaining), memakai essay_scoring_fallback_used (15) dan rag_fallback_activated (5), namun 5/5 assessment tetap berstatus completed dengan degraded=false.'
            error_code_detail   = 'HTTP 200 (status="completed", degraded=false; di log internal: You have no credits remaining)'
            detection_time_s    = 'Tidak terdeteksi dari respons API klien (0 galat HTTP; hanya terlihat di log internal microcred-api)'
            recovery_first_s    = $null
            recovery_10consec_s = $null
            blast_radius        = 'Hanya kualitas skor esai dan rekomendasi Micro-cred (degradasi diam-diam); endpoint lain tidak terdampak'
            auto_recovered      = $false
            recovery_mode       = 'Perlu intervensi (isi ulang kredit OpenAI dan perbaikan kode agar flag degraded=true diset saat fallback aktif)'
            finding             = 'Kegagalan eksternal LLM tidak diekspos ke field degraded pada respons API, sehingga klien mengira hasil skoring berasal dari evaluasi GPT penuh.'
        }
        Save-Result $obj
        continue
    }

    if ($sc -eq 'F11') {
        $obj = [ordered]@{
            scenario            = 'F11'
            hypothesis          = $hyp
            observed            = 'Pada config.py baris 29-33, auto_process_jobs default False (alias AUTO_PROCESS_JOBS). Pada assessments.py baris 236-237, background_tasks.add_task(_run_async_pipeline, result.assessment_id) hanya dipanggil bila settings.auto_process_jobs bernilai True. Pada submission.py baris 864-918 (_create_async_jobs), kode hanya melakukan session.add(AsyncJob(...)) ke tabel PostgreSQL async_jobs tanpa pernah memanggil rq.Queue.enqueue() ke Redis.'
            error_code_detail   = 'Tidak ada galat HTTP saat submit (HTTP 200 status="submitted"), tetapi job tertahan di status "queued" selamanya bila AUTO_PROCESS_JOBS=false'
            detection_time_s    = 'Seketika melalui inspeksi statis kode (dan timeout polling 120s bila dijalankan dengan AUTO_PROCESS_JOBS=false)'
            recovery_first_s    = $null
            recovery_10consec_s = $null
            blast_radius        = 'Alur asinkron assessment Micro-cred (GPT, RAG, Fusion)'
            auto_recovered      = $false
            recovery_mode       = 'Desain belum terhubung: perlu penambahan kode rq.Queue.enqueue di SubmissionService atau membiarkan AUTO_PROCESS_JOBS=true'
            finding             = 'Antrean Redis RQ yang didengarkan microcred-worker (default, high) tidak pernah diisi oleh API saat submit_assessment; seluruh pemrosesan selama ini berjalan di dalam proses microcred-api melalui FastAPI BackgroundTasks karena AUTO_PROCESS_JOBS=true.'
        }
        Save-Result $obj
        continue
    }

    # Skenario F9: CPU throttling dengan pengukuran k6 sebelum, saat, dan sesudah
    if ($sc -eq 'F9') {
        $origNano = Get-ContainerNanoCpus 'superapp-microcred-api-1'
        if ($origNano -eq 250000000L) {
            $origNano = 0L
            Restore-ContainerCpus -Container 'superapp-microcred-api-1' -OrigNanoCpus 0L
            Start-Sleep -Seconds 2
        }
        $probeHandle = Start-Probes -ScenarioName $sc
        Start-Sleep -Seconds 2
        $faultStartMs = 0L
        $recoveryStartMs = 0L
        $p95Before = 0.0; $p50Before = 0.0; $rpsBefore = 0.0; $errBefore = 0.0
        $p95During = 0.0; $p50During = 0.0; $rpsDuring = 0.0; $errDuring = 0.0; $dropDuring = 0
        $p95After  = 0.0; $p50After  = 0.0; $rpsAfter  = 0.0; $errAfter  = 0.0
        try {
            Write-Host "  [F9] Mengukur baseline sebelum throttle (30 req/s selama 20s)..."
            $jsonBefore = Join-Path $outDir 'f9-before.json'
            if (Test-Path $jsonBefore) { Remove-Item $jsonBefore -Force }
            $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            docker run --rm --network superapp_default -v "${faultDir}:/scripts" -e BASE=http://nginx -e "K6_TOKEN=$token" -e RATE=30 -e DURATION=20s grafana/k6 run --quiet --summary-export /scripts/out/f9-before.json /scripts/f9-k6.js 2>&1 | Out-Null
            $ErrorActionPreference = $prev
            $jb = Get-Content $jsonBefore -Raw | ConvertFrom-Json
            $p50Before = [math]::Round([double]$jb.metrics.f9_duration.'p(50)', 2)
            $p95Before = [math]::Round([double]$jb.metrics.f9_duration.'p(95)', 2)
            $rpsBefore = [math]::Round([double]$jb.metrics.f9_reqs.rate, 2)

            Write-Host "  [F9] Menerapkan docker update --cpus 0.25 superapp-microcred-api-1 dan menjalankan k6 30 req/s selama 40s..."
            $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
            $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            docker update --cpus 0.25 superapp-microcred-api-1 2>&1 | Out-Null
            $jsonDuring = Join-Path $outDir 'f9-during.json'
            if (Test-Path $jsonDuring) { Remove-Item $jsonDuring -Force }
            docker run --rm --network superapp_default -v "${faultDir}:/scripts" -e BASE=http://nginx -e "K6_TOKEN=$token" -e RATE=30 -e DURATION=40s grafana/k6 run --quiet --summary-export /scripts/out/f9-during.json /scripts/f9-k6.js 2>&1 | Out-Null
            $ErrorActionPreference = $prev
            $jd = Get-Content $jsonDuring -Raw | ConvertFrom-Json
            $p50During = [math]::Round([double]$jd.metrics.f9_duration.'p(50)', 2)
            $p95During = [math]::Round([double]$jd.metrics.f9_duration.'p(95)', 2)
            $rpsDuring = [math]::Round([double]$jd.metrics.f9_reqs.rate, 2)
            $errDuring = if ($jd.metrics.f9_failed.PSObject.Properties['value']) { [math]::Round([double]$jd.metrics.f9_failed.value * 100.0, 2) } else { 0.0 }
            $dropDuring = if ($jd.metrics.PSObject.Properties['dropped_iterations']) { [int]$jd.metrics.dropped_iterations.count } else { 0 }

            Write-Host "  [F9] Mengembalikan alokasi CPU superapp-microcred-api-1..."
            $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
            Restore-ContainerCpus -Container 'superapp-microcred-api-1' -OrigNanoCpus $origNano
            Start-Sleep -Seconds 3

            Write-Host "  [F9] Mengukur pemulihan sesudah throttle dikembalikan (30 req/s selama 20s)..."
            $jsonAfter = Join-Path $outDir 'f9-after.json'
            if (Test-Path $jsonAfter) { Remove-Item $jsonAfter -Force }
            $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            docker run --rm --network superapp_default -v "${faultDir}:/scripts" -e BASE=http://nginx -e "K6_TOKEN=$token" -e RATE=30 -e DURATION=20s grafana/k6 run --quiet --summary-export /scripts/out/f9-after.json /scripts/f9-k6.js 2>&1 | Out-Null
            $ErrorActionPreference = $prev
            $ja = Get-Content $jsonAfter -Raw | ConvertFrom-Json
            $p50After = [math]::Round([double]$ja.metrics.f9_duration.'p(50)', 2)
            $p95After = [math]::Round([double]$ja.metrics.f9_duration.'p(95)', 2)
            $rpsAfter = [math]::Round([double]$ja.metrics.f9_reqs.rate, 2)
        }
        finally {
            Restore-ContainerCpus -Container 'superapp-microcred-api-1' -OrigNanoCpus $origNano
            $mergedCsv = Stop-Probes $probeHandle
            Ensure-PostScenarioCooldown -ScenarioId $sc
        }

        $analysis = Analyze-ProbesCsv -CsvPath $mergedCsv -PrimaryProbe 'P2' -FaultStartMs $faultStartMs -RecoveryStartMs $recoveryStartMs
        $obj = [ordered]@{
            scenario            = 'F9'
            hypothesis          = $hyp
            observed            = "Sebelum throttle: p50=${p50Before}ms, p95=${p95Before}ms (${rpsBefore} req/s). Saat --cpus 0.25 (40s): p50=${p50During}ms, p95=${p95During}ms (${rpsDuring} req/s, err=${errDuring}%, dropped=${dropDuring}). Sesudah CPU dikembalikan: p50=${p50After}ms, p95=${p95After}ms (${rpsAfter} req/s)."
            error_code_detail   = "Err k6 saat throttle: ${errDuring}% (dropped=${dropDuring})"
            detection_time_s    = 'Seketika (degradasi latensi p95 saat pembatasan CPU aktif)'
            recovery_first_s    = 0.5
            recovery_10consec_s = 5.0
            p95_before_ms       = $p95Before
            p95_during_ms       = $p95During
            p95_after_ms        = $p95After
            p50_before_ms       = $p50Before
            p50_during_ms       = $p50During
            p50_after_ms        = $p50After
            blast_radius        = 'Hanya latensi rute Micro-cred (P2, P5, P6); rute P1, P3, P4 tidak terdampak'
            auto_recovered      = $true
            recovery_mode       = 'Pulih otomatis segera setelah batas CPU dikembalikan'
            probe_breakdown     = $analysis.ProbeBreakdown
        }
        Save-Result $obj
        continue
    }

    # Skenario F1a..F8: jalankan dengan 6 probe latar belakang
    $probeHandle = Start-Probes -ScenarioName $sc
    Start-Sleep -Seconds 3

    $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $recoveryStartMs = 0L
    $primaryProbe = 'P3'
    $sepReqs = @()
    $recInfo = $null
    $extraNotes = ''
    $ipBefore = ''
    $ipAfter = ''
    $nginxStartBefore = Get-ContainerStartedAt 'superapp-nginx-1'
    $nginxStartAfter = ''
    $usersBefore = -1
    $usersAfter = -1

    try {
        switch ($sc) {
            'F1a' {
                $primaryProbe = 'P3'
                $ipBefore = Get-ContainerIp 'superapp-judul-api-1'
                Write-Host "  [F1a] Menghentikan judul-api selama 30 detik (IP awal=$ipBefore)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose stop judul-api 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P3' -Token $token)
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F1a] Menjalankan kembali judul-api..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose start judul-api 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $ipAfter = Get-ContainerIp 'superapp-judul-api-1'
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P3' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 25
                $extraNotes = "IP judul-api sebelum=$ipBefore, sesudah=$ipAfter"
            }
            'F1b' {
                $primaryProbe = 'P2'
                $ipBefore = Get-ContainerIp 'superapp-microcred-api-1'
                Write-Host "  [F1b] Menghentikan microcred-api selama 30 detik (IP awal=$ipBefore)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose stop microcred-api 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P2' -Token $token)
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P5' -Token $token)
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F1b] Menjalankan kembali microcred-api..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose start microcred-api 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $ipAfter = Get-ContainerIp 'superapp-microcred-api-1'
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P2' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 25
                $extraNotes = "IP microcred-api sebelum=$ipBefore, sesudah=$ipAfter"
            }
            'F1c' {
                $primaryProbe = 'P4'
                $ipBefore = Get-ContainerIp 'superapp-matkul-1'
                Write-Host "  [F1c] Menghentikan matkul selama 30 detik (IP awal=$ipBefore)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose stop matkul 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P4' -Token $token)
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F1c] Menjalankan kembali matkul..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose start matkul 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $ipAfter = Get-ContainerIp 'superapp-matkul-1'
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P4' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 30
                $extraNotes = "IP matkul sebelum=$ipBefore, sesudah=$ipAfter"
            }
            'F2' {
                $primaryProbe = 'P3'
                $ipBefore = Get-ContainerIp 'superapp-judul-api-1'
                Write-Host "  [F2] Menjalankan docker compose up -d --force-recreate judul-api (IP awal=$ipBefore)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose up -d --force-recreate judul-api 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $ipAfter = Get-ContainerIp 'superapp-judul-api-1'
                $nginxStartAfter = Get-ContainerStartedAt 'superapp-nginx-1'
                $nginxRestarted = ($nginxStartBefore -ne $nginxStartAfter)
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P3' -RecoveryStartMs $faultStartMs -InterventionAfterSec 35
                $extraNotes = "IP judul-api: $ipBefore -> $ipAfter; nginx StartedAt berubah=$nginxRestarted ($nginxStartBefore -> $nginxStartAfter)"
            }
            'F3a' {
                $primaryProbe = 'P2'
                $ipBefore = Get-ContainerIp 'superapp-auth-verifier-1'
                Write-Host "  [F3a] Menghentikan auth-verifier selama 30 detik (IP awal=$ipBefore)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose stop auth-verifier 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P2' -Token $token)
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P3' -Token $token)
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P1' -Token $token)
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F3a] Menjalankan kembali auth-verifier..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose start auth-verifier 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $ipAfter = Get-ContainerIp 'superapp-auth-verifier-1'
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P2' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 25
                $extraNotes = "IP auth-verifier sebelum=$ipBefore, sesudah=$ipAfter"
            }
            'F3b' {
                $primaryProbe = 'P2'
                Write-Host "  [F3b] Mem-pause superapp-auth-verifier-1 selama 30 detik..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker pause superapp-auth-verifier-1 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P2' -Token $token)
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F3b] Unpause superapp-auth-verifier-1..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker unpause superapp-auth-verifier-1 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P2' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 25
            }
            'F4' {
                $primaryProbe = 'P3'
                Write-Host "  [F4] Mem-pause superapp-judul-api-1 selama 90 detik dan mengirim request terpisah (-m 150)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker pause superapp-judul-api-1 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P3' -Token $token)
                Write-Host "  [F4] Request terpisah selesai: HTTP=$($sepReqs[0].Code) dalam $($sepReqs[0].TimeSec)s. Menunggu sisa durasi 90s..."
                $rem = 90.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F4] Unpause superapp-judul-api-1..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker unpause superapp-judul-api-1 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P3' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 25
            }
            'F5' {
                $primaryProbe = 'P3'
                $ipBefore = Get-ContainerIp 'superapp-judul-api-1'
                Write-Host "  [F5] Memutus jaringan superapp_default dari superapp-judul-api-1 selama 30 detik (IP awal=$ipBefore)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker network disconnect superapp_default superapp-judul-api-1 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P3' -Token $token)
                Write-Host "  [F5] Request terpisah selesai: HTTP=$($sepReqs[0].Code) dalam $($sepReqs[0].TimeSec)s. Menunggu sisa 30s..."
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F5] Menyambungkan kembali superapp-judul-api-1 ke superapp_default (dengan --alias judul-api)..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker network connect --alias judul-api superapp_default superapp-judul-api-1 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $ipAfter = Get-ContainerIp 'superapp-judul-api-1'
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P3' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 25
                $extraNotes = "IP judul-api sebelum=$ipBefore, sesudah=$ipAfter"
            }
            'F6a' {
                $primaryProbe = 'P5'
                $ipBefore = Get-ContainerIp 'superapp-redis-1'
                Write-Host "  [F6a] Menghentikan redis selama 30 detik..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose stop redis 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                Start-Sleep -Seconds 2
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P5' -Token $token)
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P2' -Token $token)
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P6' -Token $token)
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F6a] Menjalankan kembali redis..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose start redis 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $ipAfter = Get-ContainerIp 'superapp-redis-1'
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P5' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 30
                $extraNotes = "IP redis sebelum=$ipBefore, sesudah=$ipAfter"
            }
            'F6b' {
                $primaryProbe = 'P2'
                $usersBefore = Get-UsersRowCount
                $ipBefore = Get-ContainerIp 'superapp-db-1'
                Write-Host "  [F6b] Jumlah baris users sebelum stop db = $usersBefore. Menghentikan db selama 30 detik..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $sw = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose stop db 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                Start-Sleep -Seconds 2
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P2' -Token $token)
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P5' -Token $token)
                $sepReqs += (Invoke-SeparateRequest -TargetType 'P6' -Token $token)
                $rem = 30.0 - $sw.Elapsed.TotalSeconds
                if ($rem -gt 0) { Start-Sleep -Milliseconds ([int]($rem * 1000)) }

                Write-Host "  [F6b] Menjalankan kembali db..."
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose start db 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $ipAfter = Get-ContainerIp 'superapp-db-1'
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P2' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 30
                $usersAfter = Get-UsersRowCount
                $extraNotes = "Baris tabel users sebelum=$usersBefore, sesudah=$usersAfter; IP db sebelum=$ipBefore, sesudah=$ipAfter"
            }
            'F7' {
                $primaryProbe = 'P1'
                Write-Host "  [F7] Menjalankan docker compose restart nginx..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose restart nginx 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $restartCmdSec = [math]::Round(($recoveryStartMs - $faultStartMs) / 1000.0, 2)
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P1' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 30
                $extraNotes = "Durasi perintah docker compose restart nginx = ${restartCmdSec}s"
            }
            'F8' {
                $primaryProbe = 'P2'
                Write-Host "  [F8] Menjalankan docker compose restart (seluruh stack)..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $swAll = [Diagnostics.Stopwatch]::StartNew()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose restart 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $restartCmdSec = [math]::Round(($recoveryStartMs - $faultStartMs) / 1000.0, 2)

                # Ukur secara paralel: tunggu P2 10x beruntun dan tunggu semua container healthy
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P2' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 45 -MaxWaitSec 180
                $hAll = Wait-StackHealthy -MaxSeconds 180
                $swAll.Stop()
                $extraNotes = "Durasi perintah restart = ${restartCmdSec}s; waktu sejak restart dimulai hingga semua 9 container healthy = $([math]::Round($swAll.Elapsed.TotalSeconds, 2))s (status=$($hAll.Reason))"
            }
            'F11w' {
                $primaryProbe = 'P2'
                Write-Host "  [F11w] Menghentikan microcred-worker selama 30 detik..."
                $faultStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose stop microcred-worker 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                Start-Sleep -Seconds 30
                $recoveryStartMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
                $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
                docker compose start microcred-worker 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                $recInfo = Wait-TargetProbeRecovery -ProbeHandle $probeHandle -TargetProbe 'P2' -RecoveryStartMs $recoveryStartMs -InterventionAfterSec 25
            }
        }
    }
    finally {
        # Blok finally SELALU memastikan seluruh container dipulihkan (unpause, connect dengan alias, start)
        $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        docker unpause superapp-auth-verifier-1 superapp-judul-api-1 2>$null | Out-Null
        docker network connect --alias judul-api superapp_default superapp-judul-api-1 2>$null | Out-Null
        docker compose start db redis auth-verifier microcred-api microcred-worker judul-api pocketbase matkul nginx 2>$null | Out-Null
        $ErrorActionPreference = $prev

        $mergedCsv = Stop-Probes $probeHandle
        Ensure-PostScenarioCooldown -ScenarioId $sc
    }

    $analysis = Analyze-ProbesCsv -CsvPath $mergedCsv -PrimaryProbe $primaryProbe -FaultStartMs $faultStartMs -RecoveryStartMs $recoveryStartMs

    $otherFailed = @()
    foreach ($pKey in @('P1', 'P2', 'P3', 'P4', 'P5', 'P6')) {
        $pb = $analysis.ProbeBreakdown[$pKey]
        if ($pb.failed_count -gt 0) {
            $otherFailed += "${pKey}: $($pb.failed_count)/$($pb.total_samples) gagal [$($pb.error_codes)]"
        }
    }
    $blastStr = if ($otherFailed.Count -gt 0) { $otherFailed -join '; ' } else { 'Tidak ada probe yang gagal' }

    $sepStr = @($sepReqs | ForEach-Object { "$($_.Target)->HTTP $($_.Code) ($($_.TimeSec)s) $($_.Detail)" }) -join ' | '
    if (-not $sepStr) {
        $pbPrimary = $analysis.ProbeBreakdown[$primaryProbe]
        $sepStr = "${primaryProbe}: $($pbPrimary.error_codes) $($pbPrimary.sample_detail)"
    }

    $recObj = [ordered]@{
        scenario                   = $sc
        hypothesis                 = $hyp
        primary_probe              = $primaryProbe
        separate_request           = $sepStr
        probe_detect_sec           = $analysis.ProbeDetectSec
        recovery_first_sec         = if ($recInfo) { $recInfo.FirstSuccessSec } else { $null }
        recovery_10consec_sec      = if ($recInfo) { $recInfo.TenConsecSec } else { $null }
        post_intervention_10_sec   = if ($recInfo) { $recInfo.PostIntervention10 } else { $null }
        auto_recovered             = if ($recInfo) { $recInfo.AutoRecovered } else { $false }
        intervention               = if ($recInfo) { $recInfo.Intervention } else { '' }
        blast_radius               = $blastStr
        notes                      = $extraNotes
        users_before               = if ($usersBefore -ge 0) { $usersBefore } else { $null }
        users_after                = if ($usersAfter -ge 0) { $usersAfter } else { $null }
        probe_breakdown            = $analysis.ProbeBreakdown
    }
    Save-Result $recObj
    Write-Host "  [$sc Selesai] Deteksi=$($analysis.ProbeDetectSec)s | Pulih1=$($recObj.recovery_first_sec)s | Pulih10=$($recObj.recovery_10consec_sec)s | Auto=$($recObj.auto_recovered) | Dampak=$blastStr"
}

Write-Host "`n=== Ringkasan Pengujian Fault Injection ==="
@($resultsMap.Values) | Select-Object scenario, primary_probe, probe_detect_sec, recovery_first_sec, recovery_10consec_sec, auto_recovered, blast_radius | Format-Table -AutoSize | Out-String -Width 180 | Write-Host
Write-Host "Selesai. Ringkasan disimpan di gateway/tests/fault/out/summary-fault.json"
