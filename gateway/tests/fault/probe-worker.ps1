<#
.SYNOPSIS
  Worker latar belakang untuk menjalankan satu probe (P1..P6) setiap 500 ms.
  Token diterima lewat environment variable FAULT_PROBE_TOKEN agar tidak muncul di baris perintah proses.
#>
param(
    [Parameter(Mandatory = $true)][string]$ProbeName,
    [Parameter(Mandatory = $true)][string]$Gateway,
    [Parameter(Mandatory = $true)][string]$OutCsv,
    [Parameter(Mandatory = $true)][string]$StopFlagFile,
    [Parameter(Mandatory = $true)][string]$SmallFile,
    [Parameter(Mandatory = $true)][string]$LoginJsonFile
)

$ErrorActionPreference = 'Continue'
$inv = [Globalization.CultureInfo]::InvariantCulture
$token = $env:FAULT_PROBE_TOKEN

function Sanitize-Detail([string]$Body) {
    if (-not $Body) { return '' }
    $clean = $Body -replace '[\r\n]+', ' ' -replace '"', "'" -replace ',', ';'
    $clean = $clean -replace 'eyJ[A-Za-z0-9_\-\.]+', '<token>'
    $clean = $clean -replace '[\w\.\-+]+@[\w\.\-]+', '<email>'
    if ($clean.Length -gt 120) { $clean = $clean.Substring(0, 120) }
    return $clean.Trim()
}

while (-not (Test-Path $StopFlagFile)) {
    $tsMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $sw = [Diagnostics.Stopwatch]::StartNew()

    $curlArgs = @('-s', '-m', '10', '-w', "`n%{http_code} %{time_total}")
    switch ($ProbeName) {
        'P1' {
            $curlArgs += @('-X', 'GET', "$Gateway/healthz")
        }
        'P2' {
            $curlArgs += @('-X', 'GET', "$Gateway/api/micro-cred/tracks", '-H', "Authorization: Bearer $token")
        }
        'P3' {
            $curlArgs += @('-X', 'GET', "$Gateway/api/judul-recommender/", '-H', "Authorization: Bearer $token")
        }
        'P4' {
            $curlArgs += @('-X', 'POST', "$Gateway/api/matkul-recommender/panduan/extract-upload", '-H', "Authorization: Bearer $token", '-F', "file_pdf=@$SmallFile;type=application/octet-stream")
        }
        'P5' {
            $curlArgs += @('-X', 'GET', "$Gateway/api/micro-cred/health")
        }
        'P6' {
            $curlArgs += @('-X', 'POST', "$Gateway/api/micro-cred/auth/login", '-H', 'Content-Type: application/json', '--data-binary', "@$LoginJsonFile")
        }
    }

    $raw = (& curl.exe @curlArgs 2>$null) -join "`n"
    $sw.Stop()

    $idx = $raw.LastIndexOf("`n")
    $body = if ($idx -ge 0) { $raw.Substring(0, $idx).Trim() } else { '' }
    $tail = if ($idx -ge 0) { $raw.Substring($idx + 1).Trim() } else { $raw.Trim() }
    $parts = $tail -split '\s+'

    $codeStr = '000'
    $timeSec = [math]::Round($sw.Elapsed.TotalSeconds, 4)
    if ($parts.Count -ge 2 -and $parts[0] -match '^\d{3}$') {
        $codeStr = $parts[0]
        $parsedTime = 0.0
        if ([double]::TryParse($parts[1], [Globalization.NumberStyles]::Float, $inv, [ref]$parsedTime)) {
            $timeSec = [math]::Round($parsedTime, 4)
        }
    }
    $codeInt = [int]$codeStr

    $isOk = 0
    $detail = ''
    switch ($ProbeName) {
        'P1' {
            $isOk = if ($codeInt -eq 200) { 1 } else { 0 }
            if (-not $isOk) { $detail = Sanitize-Detail $body }
        }
        'P2' {
            $isOk = if ($codeInt -eq 200) { 1 } else { 0 }
            if (-not $isOk) { $detail = Sanitize-Detail $body }
        }
        'P3' {
            $isOk = if ($codeInt -eq 200) { 1 } else { 0 }
            if (-not $isOk) { $detail = Sanitize-Detail $body }
        }
        'P4' {
            # Normalnya 400 dari aplikasi Matkul karena bukan PDF
            $isOk = if ($codeInt -eq 400) { 1 } else { 0 }
            if (-not $isOk) { $detail = Sanitize-Detail $body }
        }
        'P5' {
            if ($codeInt -eq 200) {
                try {
                    $j = $body | ConvertFrom-Json
                    if ($j -and $j.status -eq 'ok') {
                        $isOk = 1
                        $detail = 'status=ok'
                    }
                    else {
                        $isOk = 0
                        $pg = if ($j.datastores -and $j.datastores.postgres) { $j.datastores.postgres.status } else { '?' }
                        $rd = if ($j.datastores -and $j.datastores.redis) { $j.datastores.redis.status } else { '?' }
                        $detail = "status=$($j.status);pg=$pg;redis=$rd"
                    }
                }
                catch {
                    $isOk = 0
                    $detail = Sanitize-Detail $body
                }
            }
            else {
                $isOk = 0
                $detail = Sanitize-Detail $body
            }
        }
        'P6' {
            # Login dengan email tidak ada: normalnya 401 saat DB hidup
            $isOk = if ($codeInt -eq 401) { 1 } else { 0 }
            if (-not $isOk) { $detail = Sanitize-Detail $body }
        }
    }

    $line = ('{0},{1},{2},{3},{4},"{5}"' -f $tsMs, $ProbeName, $codeStr, $timeSec.ToString($inv), $isOk, $detail)
    Add-Content -Path $OutCsv -Value $line -Encoding utf8

    $remainMs = 500 - [int]$sw.ElapsedMilliseconds
    if ($remainMs -gt 20 -and -not (Test-Path $StopFlagFile)) {
        Start-Sleep -Milliseconds $remainMs
    }
}

