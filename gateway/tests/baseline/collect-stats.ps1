param([Parameter(Mandatory = $true)][string]$CsvPath)
while ($true) {
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $lines = @(docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" 2>$null)
    foreach ($l in $lines) {
        if ($l) {
            "$ts,$l" | Add-Content -Path $CsvPath -Encoding utf8
        }
    }
}
