param([Parameter(Mandatory = $true)][string]$CsvPath)
while ($true) {
    $ts = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    $lines = @(docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" 2>$null)
    foreach ($l in $lines) {
        if ($l) {
            "$ts,$l" | Add-Content -Path $CsvPath -Encoding utf8
        }
    }
    Start-Sleep -Seconds 2
}

