<#
.SYNOPSIS
  Uji alur nyata (end-to-end) lewat gateway dan pengukuran waktu respons.

.DESCRIPTION
  Alur A: Micro-cred (register, login, start, submit, polling status, result).
  Alur B: Judul (get-recommendations).
  Alur C: overhead gateway (health langsung vs lewat gateway, selisih rt - urt dari log nginx).
  Memanggil layanan LLM berbayar dalam jumlah kecil. Tidak memanggil email-summary atau webhook.
  Token tidak pernah dicetak. Alur C butuh stack mode debug (port 8000) dan perintah docker.

.PARAMETER Cycles
  Jumlah siklus per alur A dan B (default 5, disarankan maksimal 5).
.PARAMETER OutJson
  Opsional: simpan hasil mentah (tanpa token) ke file JSON.

.EXAMPLE
  powershell -File gateway\tests\e2e-flow.ps1 -Cycles 5
#>
param(
    [int]$Cycles = 5,
    [string]$Gateway = 'http://127.0.0.1:8080',
    [string]$MicroCredDirect = 'http://127.0.0.1:8000',
    [int]$PollTimeoutSec = 120,
    [string]$OutJson = ''
)

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$inv = [Globalization.CultureInfo]::InvariantCulture
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repoRoot
$tmp = Join-Path $env:TEMP 'e2e_body.json'
$startUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$utf8 = New-Object Text.UTF8Encoding $false
$results = [ordered]@{ started_utc = $startUtc; cycles = $Cycles }
$failures = New-Object System.Collections.Generic.List[string]

# ---------- helper ----------
function Req([string]$Method, [string]$Url, [string]$Token = '', $Body = $null) {
    $a = @('-s', '-X', $Method, $Url, '-w', "`n%{http_code} %{time_total}")
    if ($Token) { $a += @('-H', "Authorization: Bearer $Token") }
    if ($null -ne $Body) {
        [IO.File]::WriteAllText($tmp, ($Body | ConvertTo-Json -Depth 8 -Compress), $utf8)
        $a += @('-H', 'Content-Type: application/json', '--data-binary', "@$tmp")
    }
    $raw = (& curl.exe @a) -join "`n"
    $i = $raw.LastIndexOf("`n")
    $tail = $raw.Substring($i + 1).Trim().Split(' ')
    $code = 0; $time = 0.0
    if ($tail.Count -ge 2) { $code = [int]$tail[0]; $time = [double]::Parse($tail[1], $inv) }
    [pscustomobject]@{ Code = $code; Time = $time; Body = $(if ($i -gt 0) { $raw.Substring(0, $i) } else { '' }) }
}

function ParseJson($r) { try { $r.Body | ConvertFrom-Json } catch { $null } }

function Median([double[]]$v) {
    if (-not $v -or $v.Count -eq 0) { return $null }
    $s = $v | Sort-Object
    $n = $s.Count
    if ($n % 2 -eq 1) { [double]$s[[int](($n - 1) / 2)] } else { ([double]$s[$n / 2 - 1] + [double]$s[$n / 2]) / 2 }
}

function Stats([double[]]$v) {
    if (-not $v -or $v.Count -eq 0) { return 'tidak ada data' }
    $m = ($v | Measure-Object -Minimum -Maximum)
    'n={0} min={1:N2} median={2:N2} maks={3:N2}' -f $v.Count, $m.Minimum, (Median $v), $m.Maximum
}

# Samarkan email dan token sebelum teks log apa pun ditampilkan
function Mask([string]$t) {
    $t = $t -replace '[\w\.\-+]+@[\w\.\-]+', '<email>'
    $t = $t -replace 'eyJ[\w\-\.]+', '<token>'
    $t = $t -replace 'Bearer\s+\S+', 'Bearer <token>'
    if ($t.Length -gt 200) { $t = $t.Substring(0, 200) + '...' }
    $t
}

function NewAccountToken([string]$Tag) {
    $ts = [DateTimeOffset]::Now.ToUnixTimeMilliseconds()
    $email = "uji-e2e-$Tag-$ts@example.com"
    $reg = @{ email = $email; password = 'Uji12345!'; full_name = 'Uji E2E'; nim = (Get-Random -Minimum 10000000 -Maximum 99999999).ToString(); faculty = 'Fakultas Teknologi Industri'; study_program = 'Informatika' }
    $r1 = Req POST "$Gateway/api/micro-cred/auth/register" '' $reg
    $r2 = Req POST "$Gateway/api/micro-cred/auth/login" '' @{ email = $email; password = 'Uji12345!' }
    $tok = ''
    $j = ParseJson $r2
    if ($j -and $j.tokens) { $tok = $j.tokens.access_token }
    [pscustomobject]@{ Token = $tok; RegCode = $r1.Code; LoginCode = $r2.Code }
}

# ---------- jawaban otomatis dari bentuk soal ----------
function EssayAnswer([string]$prompt) {
    if ($prompt -match 'PUT vs PATCH') {
        return 'PUT mengganti seluruh representasi resource sehingga klien harus mengirim semua field, dan bersifat idempoten. PATCH hanya mengubah sebagian field sehingga payload lebih kecil dan cocok untuk perubahan parsial. Contoh PUT /users/12 dengan body {"name":"Budi Santoso","role":"student","status":"active"}, sedangkan PATCH /users/12 cukup mengirim {"status":"inactive"}.'
    }
    if ($prompt -match 'POST /login') {
        return 'Validasi input dulu (email dan password wajib, panjang dibatasi) dan balas 400 bila tidak valid. Cari user berdasarkan email lalu verifikasi password dengan bcrypt compare; bila user tidak ada atau password salah balas 401 dengan pesan yang sama agar tidak membocorkan informasi. Bila benar, buat JWT dengan claim sub dan exp (misalnya 1 jam) yang ditandatangani secret dari environment lalu kembalikan 200. Error tak terduga ditangkap dan dibalas 500 tanpa detail internal.'
    }
    if ($prompt -match '(?i)rate limit') {
        return 'Gunakan algoritma token bucket dengan counter di Redis agar konsisten di semua instance, kunci per API key atau IP. Bucket memberi kapasitas burst dan laju isi ulang tetap, dan operasi dibuat atomik lewat Lua script. Saat limit tercapai kembalikan 429 dengan header Retry-After dan X-RateLimit-Remaining serta pesan JSON yang jelas. Tentukan perilaku fail-open atau fail-closed bila Redis tidak tersedia dan catat metrik penolakan.'
    }
    'Saya akan menjelaskan konsepnya secara bertahap, lalu memberi contoh implementasi singkat. Pendekatan ini memperhatikan keamanan, kinerja, dan kemudahan perawatan. Hasilnya diuji dengan beberapa kasus normal dan kasus batas.'
}

function BuildAnswer($q) {
    $p = @{ question_id = $q.id }
    switch ($q.question_type) {
        'essay' { $p.answer_text = EssayAnswer $q.prompt }
        'theoretical' {
            $ids = @($q.options | ForEach-Object { $_.id })
            $pick = Get-Random -InputObject $ids
            $p.selected_option = $pick
            $p.selected_option_id = $pick
        }
        default {
            $caps = @($q.metadata.captures)
            $opts = @($q.options | Where-Object { $_ })
            $acc = @($q.metadata.accepted_values)
            if ($caps -contains 'project_count') {
                $ctx = @($acc | Select-Object -First 2)
                $p.project_count = 3
                $p.selected_options = $ctx
                $p.project_contexts = $ctx
            }
            elseif ($opts.Count -eq 0) {
                $vals = @($acc | Get-Random -Count 3)
                $p.selected_options = $vals
                $p.answer_text = ($vals -join ', ')
            }
            else {
                $p.selected_option = (Get-Random -InputObject @($opts | ForEach-Object { $_.id }))
            }
        }
    }
    $p
}

# ================= Alur A: Micro-cred =================
"== Alur A: Micro-cred ($Cycles siklus)"
$rowsA = New-Object System.Collections.Generic.List[object]
for ($c = 1; $c -le $Cycles; $c++) {
    $row = [ordered]@{ cycle = $c; reg = 0; login = 0; start = 0; submit = 0; final_status = ''; status_code = 0; result = 0; seconds = $null; server_ms = $null; recs = 0; recs_with_reason = 0; has_summary = $false; note = '' }
    $acct = NewAccountToken "a$c"
    $row.reg = $acct.RegCode; $row.login = $acct.LoginCode
    if (-not $acct.Token) { $row.note = 'login gagal'; $failures.Add("A siklus ${c}: register=$($acct.RegCode) login=$($acct.LoginCode)"); $rowsA.Add([pscustomobject]$row); continue }
    $tok = $acct.Token

    $st = Req POST "$Gateway/api/micro-cred/assessments/start" $tok @{ role_slug = 'backend-engineer' }
    $row.start = $st.Code
    $sj = ParseJson $st
    if ($st.Code -ne 200 -or -not $sj -or -not $sj.questions) { $row.note = 'start gagal'; $failures.Add("A siklus ${c}: start=$($st.Code)"); $rowsA.Add([pscustomobject]$row); continue }

    $answers = @($sj.questions | ForEach-Object { BuildAnswer $_ })
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $sub = Req POST "$Gateway/api/micro-cred/assessments/$($sj.assessment_id)/submit" $tok @{ responses = $answers }
    $row.submit = $sub.Code
    if ($sub.Code -ge 300) {
        $row.note = 'submit gagal'; $failures.Add("A siklus ${c}: submit=$($sub.Code) $(Mask $sub.Body)")
        $rowsA.Add([pscustomobject]$row); continue
    }

    $final = ''; $last = $null
    while ($sw.Elapsed.TotalSeconds -lt $PollTimeoutSec) {
        $ps = Req GET "$Gateway/api/micro-cred/assessments/$($sj.assessment_id)/status" $tok
        $row.status_code = $ps.Code
        $last = ParseJson $ps
        if ($ps.Code -eq 200 -and $last -and $last.status -in 'completed', 'failed') { $final = $last.status; break }
        Start-Sleep -Seconds 2
    }
    $row.seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
    $row.final_status = if ($final) { $final } else { 'timeout' }
    if ($final -ne 'completed') {
        $jobErr = ''
        if ($last -and $last.jobs) { $jobErr = (($last.jobs | Where-Object { $_.error } | ForEach-Object { "$($_.job_type): $(Mask $_.error)" }) -join '; ') }
        $failures.Add("A siklus ${c}: status akhir=$($row.final_status) $jobErr")
    }

    $rs = Req GET "$Gateway/api/micro-cred/assessments/$($sj.assessment_id)/result" $tok
    $row.result = $rs.Code
    $rj = ParseJson $rs
    if ($rj) {
        $recs = @($rj.recommendations)
        $row.recs = $recs.Count
        $row.recs_with_reason = @($recs | Where-Object { $_.match_reason }).Count
        $row.has_summary = [bool]$rj.summary
        if ($null -ne $rj.processing_duration_ms) { $row.server_ms = [int]$rj.processing_duration_ms }
    }
    $rowsA.Add([pscustomobject]$row)
    "  siklus ${c}: submit=$($row.submit) status=$($row.final_status) waktu=$($row.seconds)s rekomendasi=$($row.recs)"
}
$rowsA | Format-Table cycle, reg, login, start, submit, final_status, seconds, server_ms, result, recs, recs_with_reason, has_summary, note -AutoSize | Out-String -Width 200
$timesA = @($rowsA | Where-Object { $_.final_status -eq 'completed' -and $null -ne $_.seconds } | ForEach-Object { [double]$_.seconds })
$srvA = @($rowsA | Where-Object { $_.final_status -eq 'completed' -and $null -ne $_.server_ms } | ForEach-Object { [double]$_.server_ms / 1000 })
"Waktu submit sampai selesai (detik, hanya siklus completed): $(Stats $timesA)"
"processing_duration_ms dari server (detik): $(Stats $srvA)"
$results.alur_a = @{ rows = $rowsA; stats_client_seconds = (Stats $timesA); stats_server_seconds = (Stats $srvA); completed = $timesA.Count }

# ================= Alur B: Judul =================
"`n== Alur B: Judul ($Cycles siklus)"
$acctB = NewAccountToken 'b'
$rowsB = New-Object System.Collections.Generic.List[object]
if (-not $acctB.Token) { 'FAIL  token untuk alur B tidak didapat'; $failures.Add('B: login gagal') }
else {
    for ($c = 1; $c -le $Cycles; $c++) {
        $r = Req POST "$Gateway/api/judul-recommender/get-recommendations" $acctB.Token @{ interests = 'sistem deteksi kantuk untuk pengemudi menggunakan computer vision dan machine learning' }
        $j = ParseJson $r
        $recN = 0; $refs = ''; $detail = ''
        if ($r.Code -eq 200 -and $j -and $j.rekomendasi) {
            $recN = @($j.rekomendasi).Count
            $refs = (@($j.rekomendasi | ForEach-Object { @($_.referensi).Count }) -join ',')
        }
        elseif ($j -and $j.detail) { $detail = Mask ([string]$j.detail) }
        if ($r.Code -ne 200) { $failures.Add("B siklus ${c}: http=$($r.Code) $detail") }
        $rowsB.Add([pscustomobject]@{ cycle = $c; code = $r.Code; seconds = [math]::Round($r.Time, 2); recs = $recN; refs_per_rec = $refs; detail = $detail })
        "  siklus ${c}: http=$($r.Code) waktu=$([math]::Round($r.Time,2))s rekomendasi=$recN"
    }
}
$rowsB | Format-Table -AutoSize | Out-String -Width 200
$okB = @($rowsB | Where-Object { $_.code -eq 200 })
$timesB = @($okB | ForEach-Object { [double]$_.seconds })
"Waktu (detik, hanya HTTP 200): $(Stats $timesB)"
"Tingkat sukses: $($okB.Count)/$($rowsB.Count)"
$results.alur_b = @{ rows = $rowsB; stats_seconds = (Stats $timesB); success = "$($okB.Count)/$($rowsB.Count)" }

# ================= Alur C: overhead gateway =================
"`n== Alur C: overhead gateway"
$gw = @(); $dr = @()
for ($i = 1; $i -le 10; $i++) {
    $g = Req GET "$Gateway/api/micro-cred/health"; if ($g.Code -eq 200) { $gw += $g.Time }
    $d = Req GET "$MicroCredDirect/health"; if ($d.Code -eq 200) { $dr += $d.Time }
}
$mg = Median ([double[]]$gw); $md = Median ([double[]]$dr)
if ($null -ne $mg -and $null -ne $md) {
    'Health Micro-cred (10x): median lewat gateway = {0:N1} ms, langsung = {1:N1} ms, selisih = {2:N1} ms' -f ($mg * 1000), ($md * 1000), (($mg - $md) * 1000)
    $results.alur_c1 = @{ gateway_median_ms = [math]::Round($mg * 1000, 1); direct_median_ms = [math]::Round($md * 1000, 1); n_gateway = $gw.Count; n_direct = $dr.Count }
}
else { 'Health: data tidak lengkap (port debug 8000 tidak aktif?)'; $failures.Add("C1: sukses gateway=$($gw.Count) langsung=$($dr.Count)") }

# rt - urt dari log nginx (selisih memuat verifikasi auth_request dan overhead proxy)
$nginxLog = @(docker compose logs --no-log-prefix --since $startUtc nginx 2>$null)
$re = '"(?<m>[A-Z]+) (?<path>\S+) HTTP/[\d.]+" (?<st>\d{3}) rt=(?<rt>[\d.]+) urt=(?<urt>\S+) upstream='
$diffA = @(); $diffB = @()
foreach ($line in $nginxLog) {
    $m = [regex]::Match([string]$line, $re)
    if (-not $m.Success) { continue }
    $urt = $m.Groups['urt'].Value
    if ($urt -notmatch '^[\d.]+$') { continue }
    $diff = ([double]::Parse($m.Groups['rt'].Value, $inv) - [double]::Parse($urt, $inv)) * 1000
    $path = $m.Groups['path'].Value
    if ($path -like '/api/micro-cred/assessments*') { $diffA += $diff }
    elseif ($path -like '/api/judul-recommender/get-recommendations*') { $diffB += $diff }
}
function SD([double[]]$v) { if ($v.Count -eq 0) { 'tidak ada data' } else { 'n={0} median={1:N1} ms maks={2:N1} ms' -f $v.Count, (Median $v), ($v | Measure-Object -Maximum).Maximum } }
"rt - urt, request alur A (/assessments/*): $(SD ([double[]]$diffA))"
"rt - urt, request alur B (get-recommendations): $(SD ([double[]]$diffB))"
$results.alur_c2 = @{ a = (SD ([double[]]$diffA)); b = (SD ([double[]]$diffB)) }

# ---------- log worker ----------
"`n== Log microcred-worker sejak mulai"
$wlog = @(docker compose logs --no-log-prefix --since $startUtc microcred-worker 2>$null)
$nEssay = @($wlog | Where-Object { $_ -match 'score_essay' }).Count
$nReco = @($wlog | Where-Object { $_ -match 'generate_recommendations' }).Count
$errs = @($wlog | Where-Object { $_ -match '(?i)error|exception|traceback|failed' })
"baris dengan score_essay: $nEssay; generate_recommendations: $nReco; baris mengandung error/exception/failed: $($errs.Count)"
foreach ($l in @($wlog | Where-Object { $_ -match 'score_essay|generate_recommendations' } | Select-Object -First 4)) { "  contoh: $(Mask ([string]$l))" }
foreach ($l in @($errs | Select-Object -First 5)) { "  error: $(Mask ([string]$l))" }
$results.worker = @{ score_essay_lines = $nEssay; generate_recommendations_lines = $nReco; error_lines = $errs.Count }

# ---------- ringkasan ----------
"`n== Kegagalan ($($failures.Count))"
foreach ($f in $failures) { "  - $f" }
$results.failures = @($failures)
Remove-Item $tmp -ErrorAction SilentlyContinue
if ($OutJson) { ($results | ConvertTo-Json -Depth 8) | Set-Content -Path $OutJson -Encoding utf8; "hasil mentah disimpan ke file (tanpa token)." }

