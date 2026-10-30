<#
.SYNOPSIS
  Orkestrator pengujian kinerja dan beban gateway SuperApp menggunakan grafana/k6 (Docker).

.DESCRIPTION
  Menjalankan skenario S1 sampai S6 secara berurutan (dan S7 hanya bila -IncludeLlm diaktifkan).
  Setiap skenario diawali warm-up 10 detik yang tidak dihitung, dan diulang sebanyak -Repeats kali (default 3).
  Selama tiap skenario, mencatat docker stats --no-stream tiap 2 detik ke CSV di gateway/tests/perf/out/.
  Menghentikan seluruh pengujian bila stack tidak healthy atau error rate > 20% selama >= 15 detik.
  Token dan data pribadi tidak pernah dicetak atau disimpan di file keluaran.

.PARAMETER Repeats
  Jumlah ulangan per skenario (default 3).
.PARAMETER IncludeLlm
  Jalankan skenario S7 yang memanggil LLM berbayar (default false).
.PARAMETER OnlyScenario
  Opsional: filter nama skenario tertentu (default kosong = jalankan semua).
#>
param(
    [int]$Repeats = 3,
    [switch]$IncludeLlm = $false,
    [string]$OnlyScenario = '',
    [switch]$Resume = $false
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$inv = [Globalization.CultureInfo]::InvariantCulture

$perfDir = $PSScriptRoot
$outDir = Join-Path $perfDir 'out'
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

# Pastikan file biner uji untuk S5 tersedia di out/ (14 MB dan 17 MB, bukan PDF)
$file14 = Join-Path $outDir 'dummy-14mb.bin'
$file17 = Join-Path $outDir 'dummy-17mb.bin'

function Ensure-DummyFile([string]$Path, [long]$SizeBytes) {
    if ((Test-Path $Path) -and ((Get-Item $Path).Length -eq $SizeBytes)) {
        return
    }
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
    try {
        $header = [System.Text.Encoding]::ASCII.GetBytes('NOT_A_PDF_BINARY_PAYLOAD_FOR_PERF_TEST_')
        $fs.Write($header, 0, $header.Length)
        $fs.SetLength($SizeBytes)
    }
    finally {
        $fs.Close()
    }
}

Ensure-DummyFile -Path $file14 -SizeBytes (14 * 1024 * 1024)
Ensure-DummyFile -Path $file17 -SizeBytes (17 * 1024 * 1024)

# Periksa kesehatan seluruh container di project superapp
function Test-StackHealthy {
    $lines = @(docker ps --filter "label=com.docker.compose.project=superapp" --format "{{.Names}}|{{.Status}}" 2>$null)
    if ($lines.Count -lt 9) {
        return [pscustomobject]@{ Ok = $false; Reason = "Jumlah container aktif kurang dari 9 (ditemukan $($lines.Count))" }
    }
    foreach ($line in $lines) {
        $parts = $line.Split('|')
        $name = $parts[0]
        $st = $parts[1]
        if ($st -match 'unhealthy|starting|Exited|Dead|Restarting') {
            return [pscustomobject]@{ Ok = $false; Reason = "Container $name berstatus tidak sehat: $st" }
        }
    }
    return [pscustomobject]@{ Ok = $true; Reason = 'Semua container healthy' }
}

# Hitung median dari array angka
function Get-Median([double[]]$Values) {
    if (-not $Values -or $Values.Count -eq 0) { return 0.0 }
    $sorted = @($Values | Sort-Object)
    $n = $sorted.Count
    if ($n % 2 -eq 1) {
        return [double]$sorted[[int](($n - 1) / 2)]
    }
    return ([double]$sorted[$n / 2 - 1] + [double]$sorted[$n / 2]) / 2.0
}

# Urai ukuran memori docker stats (mis. "45.2MiB" atau "1.2GiB") menjadi MiB
function ConvertTo-MiB([string]$MemStr) {
    if (-not $MemStr) { return 0.0 }
    $used = ($MemStr -split '/')[0].Trim()
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

# Urai file CSV docker stats untuk mendapatkan puncak CPU (%) dan puncak Memori (MiB) per container
function Get-PeakContainerStats([string]$CsvPath) {
    $peaks = [ordered]@{}
    if (-not (Test-Path $CsvPath)) { return $peaks }
    $rows = Import-Csv -Path $CsvPath -ErrorAction SilentlyContinue
    foreach ($r in $rows) {
        $c = $r.container
        if (-not $c) { continue }
        $cpuStr = ($r.cpu_perc -replace '%', '').Trim()
        $cpu = 0.0
        [void][double]::TryParse($cpuStr, [Globalization.NumberStyles]::Float, $inv, [ref]$cpu)
        $memMib = ConvertTo-MiB $r.mem_usage
        if (-not $peaks.Contains($c)) {
            $peaks[$c] = [ordered]@{ peak_cpu_pct = $cpu; peak_mem_mib = [math]::Round($memMib, 1) }
        }
        else {
            if ($cpu -gt $peaks[$c].peak_cpu_pct) { $peaks[$c].peak_cpu_pct = $cpu }
            if ($memMib -gt $peaks[$c].peak_mem_mib) { $peaks[$c].peak_mem_mib = [math]::Round($memMib, 1) }
        }
    }
    return $peaks
}

# Hitung baris log akses /tracks di microcred-api (untuk verifikasi S3)
function Get-MicrocredAccessCounts {
    $prevErr = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $logs = @(docker logs superapp-microcred-api-1 2>&1 | ForEach-Object { "$_" })
    $ErrorActionPreference = $prevErr
    $tracksLines = @($logs | Where-Object { $_ -match '/tracks' }).Count
    $nonHealthLines = @($logs | Where-Object { $_ -notmatch 'health_probe|/health' }).Count
    return [pscustomobject]@{
        TracksLines    = $tracksLines
        NonHealthLines = $nonHealthLines
        TotalLines     = $logs.Count
    }
}

# Ambil nilai metrik dari objek JSON summary-export k6 dengan aman
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

# Daftar skenario yang akan dijalankan.
# S2 (uji titik jenuh hingga 800 req/s) ditempatkan setelah S1 dan S3-S6 agar saat S2
# melampaui batas galat 20% selama 15 detik dan memicu penghentian keras, data S1 dan S3-S6 sudah lengkap.
$scenarios = @(
    @{ Name = 's1a-healthz-100rps';       Group = 'S1'; Script = 's1-overhead.js';   Env = @('TARGET=a', 'RATE=100'); DurationSec = 30 },
    @{ Name = 's1b-gw-tracks-100rps';     Group = 'S1'; Script = 's1-overhead.js';   Env = @('TARGET=b', 'RATE=100'); DurationSec = 30 },
    @{ Name = 's1c-direct-tracks-100rps'; Group = 'S1'; Script = 's1-overhead.js';   Env = @('TARGET=c', 'RATE=100'); DurationSec = 30 },

    @{ Name = 's3-unauth-200rps';         Group = 'S3'; Script = 's3-unauth.js';     Env = @('RATE=200'); DurationSec = 30; CheckMicrocredLog = $true },
    @{ Name = 's3-unauth-800rps';         Group = 'S3'; Script = 's3-unauth.js';     Env = @('RATE=800'); DurationSec = 30; CheckMicrocredLog = $true },

    @{ Name = 's4-login-1vu';             Group = 'S4'; Script = 's4-login.js';      Env = @('VUS=1');  DurationSec = 20 },
    @{ Name = 's4-login-3vu';             Group = 'S4'; Script = 's4-login.js';      Env = @('VUS=3');  DurationSec = 20 },
    @{ Name = 's4-login-5vu';             Group = 'S4'; Script = 's4-login.js';      Env = @('VUS=5');  DurationSec = 20 },
    @{ Name = 's4-login-10vu';            Group = 'S4'; Script = 's4-login.js';      Env = @('VUS=10'); DurationSec = 20 },

    @{ Name = 's5-upload14m-1vu';         Group = 'S5'; Script = 's5-upload.js';     Env = @('MODE=14m', 'VUS=1');    DurationSec = 20 },
    @{ Name = 's5-upload14m-3vu';         Group = 'S5'; Script = 's5-upload.js';     Env = @('MODE=14m', 'VUS=3');    DurationSec = 20 },
    @{ Name = 's5-upload14m-5vu';         Group = 'S5'; Script = 's5-upload.js';     Env = @('MODE=14m', 'VUS=5');    DurationSec = 20 },
    @{ Name = 's5-upload17m-20rps';       Group = 'S5'; Script = 's5-upload.js';     Env = @('MODE=17m', 'RATE=20');  DurationSec = 30 },

    @{ Name = 's6-judul-50rps';           Group = 'S6'; Script = 's6-judul.js';      Env = @('RATE=50');  DurationSec = 30 },
    @{ Name = 's6-judul-200rps';          Group = 'S6'; Script = 's6-judul.js';      Env = @('RATE=200'); DurationSec = 30 },

    @{ Name = 's2-tracks-50rps';          Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=50',  'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
    @{ Name = 's2-tracks-100rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=100', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
    @{ Name = 's2-tracks-200rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=200', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
    @{ Name = 's2-tracks-400rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=400', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
    @{ Name = 's2-tracks-800rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=800', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 }
)

if ($IncludeLlm) {
    $scenarios += @(
        @{ Name = 's7a-judul-llm-1vu';     Group = 'S7'; Script = 's7-judul-llm.js';     Env = @('VUS=1'); DurationSec = 72; IsLlm = $true },
        @{ Name = 's7a-judul-llm-2vu';     Group = 'S7'; Script = 's7-judul-llm.js';     Env = @('VUS=2'); DurationSec = 72; IsLlm = $true },
        @{ Name = 's7a-judul-llm-3vu';     Group = 'S7'; Script = 's7-judul-llm.js';     Env = @('VUS=3'); DurationSec = 72; IsLlm = $true },
        @{ Name = 's7b-microcred-llm-1vu'; Group = 'S7'; Script = 's7-microcred-llm.js'; Env = @('VUS=1'); DurationSec = 60; IsLlm = $true },
        @{ Name = 's7b-microcred-llm-2vu'; Group = 'S7'; Script = 's7-microcred-llm.js'; Env = @('VUS=2'); DurationSec = 60; IsLlm = $true },
        @{ Name = 's7b-microcred-llm-3vu'; Group = 'S7'; Script = 's7-microcred-llm.js'; Env = @('VUS=3'); DurationSec = 60; IsLlm = $true }
    )
}

if ($OnlyScenario) {
    $scenarios = @($scenarios | Where-Object { $_.Name -like "*$OnlyScenario*" -or $_.Group -eq $OnlyScenario })
}

$initHealth = Test-StackHealthy
if (-not $initHealth.Ok) {
    Write-Error "ABORT: Stack tidak healthy sebelum pengujian dimulai: $($initHealth.Reason)"
    exit 1
}
Write-Host "Stack healthy. Memulai pengujian kinerja dengan Repeats=$Repeats, IncludeLlm=$IncludeLlm..."

$summaryOutPath = Join-Path $outDir 'summary-medians.json'
$existingMap = [ordered]@{}
if (($OnlyScenario -or $Resume) -and (Test-Path $summaryOutPath)) {
    $prevList = @(Get-Content $summaryOutPath -Raw | ConvertFrom-Json)
    foreach ($item in $prevList) {
        if ($item -and $item.scenario) {
            $existingMap[$item.scenario] = $item
        }
    }
}

$statsScript = Join-Path $perfDir 'collect-stats.ps1'

foreach ($sc in $scenarios) {
    $scName = $sc.Name
    if ($Resume -and $existingMap.Contains($scName) -and $existingMap[$scName].repeats -ge $Repeats -and -not $existingMap[$scName].aborted) {
        Write-Host "Melewati $scName (sudah selesai $($existingMap[$scName].repeats) ulangan)."
        continue
    }
    $statsCsv = Join-Path $outDir "stats-$scName.csv"
    "timestamp_utc,container,cpu_perc,mem_usage,mem_perc" | Set-Content -Path $statsCsv -Encoding utf8

    Write-Host "`n=== Skenario: $scName ($Repeats ulangan) ==="

    # Jalankan pencatat docker stats tiap 2 detik di proses latar belakang (kutip path yang mengandung spasi)
    $argStr = "-NoProfile -WindowStyle Hidden -File `"$statsScript`" -CsvPath `"$statsCsv`""
    $statsProc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argStr -PassThru

    $runMetrics = New-Object System.Collections.Generic.List[object]
    $abortedMsg = ''

    try {
        for ($r = 1; $r -le $Repeats; $r++) {
            $healthBefore = Test-StackHealthy
            if (-not $healthBefore.Ok) {
                $abortedMsg = "ABORT: Stack tidak healthy sebelum $scName ulangan ${r}: $($healthBefore.Reason)"
                break
            }

            $logBefore = $null
            if ($sc.CheckMicrocredLog) {
                $logBefore = Get-MicrocredAccessCounts
            }

            $runTag = "$scName-r$r"
            $jsonRel = "/scripts/out/$runTag.json"
            $jsonHost = Join-Path $outDir "$runTag.json"
            if (Test-Path $jsonHost) { Remove-Item $jsonHost -Force }

            # Tiap skenario diawali warm-up 10 detik yang tidak dihitung pada awal skenario (r=1)
            $warmupSec = if ($r -eq 1) { 10 } else { 0 }

            $dockerArgs = @(
                'run', '--rm',
                '--network', 'superapp_default',
                '-v', "${perfDir}:/scripts",
                '-e', 'BASE=http://nginx',
                '-e', "WARMUP_SEC=$warmupSec"
            )
            foreach ($e in $sc.Env) {
                $dockerArgs += @('-e', $e)
            }
            $dockerArgs += @(
                'grafana/k6', 'run',
                '--quiet',
                '--summary-export', $jsonRel,
                "/scripts/$($sc.Script)"
            )

            $ErrorActionPreference = 'Continue'
            $k6Out = & docker @dockerArgs 2>&1
            $k6Exit = $LASTEXITCODE
            $ErrorActionPreference = 'Stop'

            $logDeltaTracks = 0
            $logDeltaNonHealth = 0
            if ($sc.CheckMicrocredLog -and $null -ne $logBefore) {
                $logAfter = Get-MicrocredAccessCounts
                $logDeltaTracks = $logAfter.TracksLines - $logBefore.TracksLines
                $logDeltaNonHealth = $logAfter.NonHealthLines - $logBefore.NonHealthLines
            }

            if (-not (Test-Path $jsonHost)) {
                $abortedMsg = "ABORT: File hasil k6 tidak terbentuk untuk $runTag (exit=$k6Exit). Output: $($k6Out -join ' ')"
                break
            }

            $summary = Get-Content $jsonHost -Raw | ConvertFrom-Json
            # Hapus setup_data agar token dan email tidak pernah tersimpan di file JSON
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
            $reqs = Get-K6MetricValue $m 'main_reqs' 'count'
            $errRate = Get-K6MetricValue $m 'main_failed' 'value'
            if ($errRate -eq 0) { $errRate = Get-K6MetricValue $m 'main_failed' 'rate' }
            $dropped = Get-K6MetricValue $m 'dropped_iterations' 'count'
            $vusMax = Get-K6MetricValue $m 'vus_max' 'value'
            if ($vusMax -eq 0) { $vusMax = Get-K6MetricValue $m 'vus_max' 'max' }
            $insuffVus = [bool](($k6Out -join "`n") -match 'Insufficient VUs')
            $timeouts = Get-K6MetricValue $m 'main_timeouts' 'count'
            $s200 = Get-K6MetricValue $m 'main_status_200' 'count'
            $s400 = Get-K6MetricValue $m 'main_status_400' 'count'
            $s401 = Get-K6MetricValue $m 'main_status_401' 'count'
            $s413 = Get-K6MetricValue $m 'main_status_413' 'count'
            $s503 = Get-K6MetricValue $m 'main_status_503' 'count'
            $s5xx = Get-K6MetricValue $m 'main_status_5xx' 'count'
            $json413 = Get-K6MetricValue $m 'main_json_413' 'count'

            $durSec = [double]$sc.DurationSec
            $rps = if ($durSec -gt 0) { $reqs / $durSec } else { 0.0 }

            Write-Host ("  [r{0}] reqs={1} rps={2:N1} p50={3:N2}ms p95={4:N2}ms p99={5:N2}ms err={6:N2}% dropped={7} vus_max={8} insuff_vus={9} 503={10} timeout={11}" -f $r, $reqs, $rps, $p50, $p95, $p99, ($errRate * 100.0), $dropped, $vusMax, $insuffVus, $s503, $timeouts)

            $runMetrics.Add([pscustomobject]@{
                repeat                   = $r
                reqs                     = $reqs
                rps                      = $rps
                p50_ms                   = $p50
                p95_ms                   = $p95
                p99_ms                   = $p99
                avg_ms                   = $avg
                err_rate_pct             = $errRate * 100.0
                dropped_iterations       = $dropped
                vus_max                  = $vusMax
                insufficient_vus_warning = $insuffVus
                timeouts                 = $timeouts
                status_200               = $s200
                status_400               = $s400
                status_401               = $s401
                status_413               = $s413
                status_503               = $s503
                status_5xx               = $s5xx
                json_413                 = $json413
                log_delta_tracks         = $logDeltaTracks
                log_delta_non_health     = $logDeltaNonHealth
            })

            # Jeda singkat 2 detik agar antrean koneksi backend reda sebelum ulangan berikutnya
            Start-Sleep -Seconds 2

            $healthAfter = Test-StackHealthy
            if (-not $healthAfter.Ok) {
                $abortedMsg = "ABORT: Stack menjadi tidak healthy setelah ${runTag}: $($healthAfter.Reason)"
                break
            }

            if ($k6Exit -eq 99 -or $errRate -gt 0.20) {
                $abortedMsg = ("ABORT: Error rate melampaui batas 20% ({0:N2}%) selama >=15 detik pada {1} (exit={2}). Pengujian dihentikan sesuai aturan keras." -f ($errRate * 100.0), $runTag, $k6Exit)
                break
            }
        }
    }
    finally {
        if ($statsProc -and -not $statsProc.HasExited) {
            Stop-Process -Id $statsProc.Id -Force -ErrorAction SilentlyContinue
        }
    }

    $peaks = Get-PeakContainerStats -CsvPath $statsCsv

    if ($runMetrics.Count -gt 0) {
        $medObj = [ordered]@{
            scenario             = $scName
            group                = $sc.Group
            repeats              = $runMetrics.Count
            aborted              = [bool]($abortedMsg -ne '')
            abort_reason         = $abortedMsg
            p50_ms               = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.p50_ms })), 2)
            p95_ms               = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.p95_ms })), 2)
            p99_ms               = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.p99_ms })), 2)
            avg_ms               = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.avg_ms })), 2)
            reqs                 = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.reqs })), 0)
            throughput_rps       = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.rps })), 2)
            error_rate_pct           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.err_rate_pct })), 2)
            dropped_iterations       = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.dropped_iterations })), 0)
            vus_max                  = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.vus_max })), 0)
            insufficient_vus_warning = [bool](($runMetrics | Where-Object { $_.insufficient_vus_warning }).Count -gt 0)
            timeouts                 = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.timeouts })), 0)
            status_200           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_200 })), 0)
            status_400           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_400 })), 0)
            status_401           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_401 })), 0)
            status_413           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_413 })), 0)
            status_503           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_503 })), 0)
            status_5xx           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_5xx })), 0)
            json_413             = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.json_413 })), 0)
            log_delta_tracks     = ($runMetrics | Measure-Object -Property log_delta_tracks -Sum).Sum
            log_delta_non_health = ($runMetrics | Measure-Object -Property log_delta_non_health -Sum).Sum
            container_peaks      = $peaks
            runs                 = $runMetrics
        }
        $existingMap[$scName] = [pscustomobject]$medObj
        ($existingMap.Values | ConvertTo-Json -Depth 8) | Set-Content -Path $summaryOutPath -Encoding utf8
    }

    if ($abortedMsg) {
        Write-Warning $abortedMsg
        break
    }
}

Write-Host "`n=== Ringkasan Median ==="
$existingMap.Values | Select-Object scenario, repeats, throughput_rps, p50_ms, p95_ms, p99_ms, error_rate_pct, dropped_iterations, aborted | Format-Table -AutoSize | Out-String -Width 160 | Write-Host
Write-Host "Selesai. Ringkasan disimpan di gateway/tests/perf/out/summary-medians.json"
