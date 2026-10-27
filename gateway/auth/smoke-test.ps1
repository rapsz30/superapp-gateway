# Smoke test autentikasi gateway. Mencetak PASS/FAIL per kasus, tidak pernah mencetak token.
# Jalankan dari root repo: powershell -File gateway\auth\smoke-test.ps1
$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:8080'
$script:fail = 0
$ts = [DateTimeOffset]::Now.ToUnixTimeSeconds()

function Report($name, $ok, $info) {
    if ($ok) { "PASS  $name  ($info)" } else { "FAIL  $name  ($info)"; $script:fail++ }
}

# Kirim request lewat curl.exe. Mengembalikan code, headers, body.
function Req([string]$Method, [string]$Path, [string]$Token = '', [string]$Json = $null, [string[]]$Extra = @(), [string]$File = $null) {
    $args2 = @('-s', '-i', '-X', $Method, "$base$Path", '--path-as-is')
    if ($Token) { $args2 += @('-H', "Authorization: Bearer $Token") }
    if ($Json) {
        $f = Join-Path $env:TEMP "smoke_body.json"
        Set-Content -Path $f -Value $Json -Encoding ascii -NoNewline
        $args2 += @('-H', 'Content-Type: application/json', '--data-binary', "@$f")
    }
    if ($File) { $args2 += @('-F', "file_pdf=@$File") }
    $args2 += $Extra
    $raw = (& curl.exe @args2) -join "`n"
    $parts = $raw -split "`n`n", 2
    # Pisahkan blok header terakhir (abaikan 100 Continue)
    while ($parts.Count -eq 2 -and $parts[0] -match '^HTTP/1\.[01] 100') { $parts = $parts[1] -split "`n`n", 2 }
    $head = $parts[0]
    $body = if ($parts.Count -gt 1) { $parts[1] } else { '' }
    $code = if ($head -match '^HTTP/\S+ (\d{3})') { [int]$Matches[1] } else { 0 }
    [pscustomobject]@{ Code = $code; Head = $head; Body = $body }
}

# Buat token di dalam container verifier (secret dari environment container, tidak dicetak).
function NewToken([string]$Role, [int]$ExpOffset, [string]$OtherSecret = '') {
    $code = @"
import os, time, jwt
now = int(time.time())
p = {'sub': 'uji-smoke-$ts', 'roles': ['$Role'], 'iat': now, 'exp': now + ($ExpOffset), 'iss': 'smoke'}
print(jwt.encode(p, '$OtherSecret' or os.environ['JWT_SECRET'], algorithm=os.environ.get('JWT_ALGORITHM', 'HS256')))
"@
    ($code | docker compose exec -T auth-verifier python - 2>$null | Select-Object -Last 1).Trim()
}

function JsonDetail($r) { try { ($r.Body | ConvertFrom-Json).detail } catch { '' } }

# --- Persiapan akun uji ---
$email = "uji-auth-$ts@example.com"
$nim = (Get-Random -Minimum 10000000 -Maximum 99999999).ToString()
$reg = @{ email = $email; password = 'Uji12345!'; full_name = 'Uji Auth'; nim = $nim; faculty = 'Fakultas Teknologi Industri'; study_program = 'Informatika' } | ConvertTo-Json -Compress

"== 1. Publik tanpa token"
$r = Req GET '/healthz'; Report 'GET /healthz' ($r.Code -eq 200) $r.Code
$r = Req GET '/api/micro-cred/health'; Report 'GET /api/micro-cred/health' ($r.Code -eq 200) $r.Code
$r = Req POST '/api/micro-cred/auth/register' -Json $reg; Report 'POST register' ($r.Code -eq 201) $r.Code
$r = Req POST '/api/micro-cred/auth/login' -Json (@{ email = $email; password = 'Uji12345!' } | ConvertTo-Json -Compress)
Report 'POST login' ($r.Code -eq 200) $r.Code
$student = try { ($r.Body | ConvertFrom-Json).tokens.access_token } catch { '' }
if (-not $student) { 'FAIL  token student tidak didapat, berhenti'; exit 1 }

"== 2. Tanpa token -> 401 JSON dari gateway"
$gjson = '{"interests":"sistem deteksi kantuk untuk pengemudi menggunakan computer vision dan machine learning"}'
foreach ($t in @(
        @('GET', '/api/micro-cred/tracks', $null),
        @('GET', '/api/micro-cred/auth/me', $null),
        @('GET', '/api/judul-recommender/', $null),
        @('POST', '/api/judul-recommender/get-recommendations', $gjson),
        @('POST', '/api/matkul-recommender/rekomendasi', '{}'))) {
    $r = Req $t[0] $t[1] -Json $t[2]
    Report "$($t[0]) $($t[1]) tanpa token" ($r.Code -eq 401 -and (JsonDetail $r) -eq 'Token tidak ada atau tidak valid') "$($r.Code) $(JsonDetail $r)"
}

"== 3. Token diubah satu karakter -> 401"
$last = $student[-1]; $swap = if ($last -eq 'A') { 'B' } else { 'A' }
$tampered = $student.Substring(0, $student.Length - 1) + $swap
$r = Req GET '/api/micro-cred/auth/me' -Token $tampered; Report 'token diubah' ($r.Code -eq 401) $r.Code

"== 4. Token kedaluwarsa -> 401"
$expired = NewToken 'student' -60
$r = Req GET '/api/micro-cred/auth/me' -Token $expired; Report 'token kedaluwarsa' ($r.Code -eq 401) $r.Code

"== 4b. Token ditandatangani dengan secret lain -> 401"
$foreign = NewToken 'student' 600 'secret-lain-yang-tidak-sama-dengan-gateway-1234567890'
$r = Req GET '/api/micro-cred/auth/me' -Token $foreign; Report 'token secret lain' ($r.Code -eq 401) $r.Code

"== 5. Token student sah"
$r = Req GET '/api/micro-cred/auth/me' -Token $student; Report 'GET /auth/me' ($r.Code -eq 200) $r.Code
$r = Req GET '/api/micro-cred/tracks' -Token $student; Report 'GET /tracks' ($r.Code -eq 200) $r.Code
$r = Req POST '/api/judul-recommender/get-recommendations' -Token $student -Json $gjson
Report 'POST get-recommendations' ($r.Code -in 200, 500) $r.Code
$notpdf = Join-Path $env:TEMP 'smoke_notpdf.bin'; Set-Content -Path $notpdf -Value 'bukan pdf' -Encoding ascii
$r = Req POST '/api/matkul-recommender/panduan/extract-upload' -Token $student -File $notpdf
Report 'POST extract-upload bukan PDF' ($r.Code -eq 400) $r.Code

"== 6. Student menulis tracks -> 403 dari gateway"
$r = Req POST '/api/micro-cred/tracks' -Token $student -Json '{}'
Report 'POST /tracks (student)' ($r.Code -eq 403 -and (JsonDetail $r) -eq 'Akses ditolak') "$($r.Code) $(JsonDetail $r)"

"== 6b. Percobaan melewati kebijakan (student)"
foreach ($p in '/api/micro-cred/tracks?x=1', '/api/micro-cred/%74racks', '/api/micro-cred//tracks', '/api/micro-cred/tracks/') {
    $r = Req POST $p -Token $student -Json '{}'
    Report "POST $p" ($r.Code -eq 403 -and (JsonDetail $r) -eq 'Akses ditolak') "$($r.Code)"
}

"== 7. Admin menulis tracks -> bukan 401/403 dari gateway"
$admin = NewToken 'admin' 600
$r = Req POST '/api/micro-cred/tracks' -Token $admin -Json '{}'
Report 'POST /tracks (admin)' ($r.Code -notin 401, 403, 502, 503) $r.Code

"== 8. Batas upload dengan token student"
$f14 = Join-Path $env:TEMP 'smoke14.bin'; $f17 = Join-Path $env:TEMP 'smoke17.bin'
Remove-Item $f14, $f17 -ErrorAction SilentlyContinue
fsutil file createnew $f14 14680064 | Out-Null; fsutil file createnew $f17 17825792 | Out-Null
$r = Req POST '/api/matkul-recommender/panduan/extract-upload' -Token $student -File $f14; Report 'upload 14 MB' ($r.Code -ne 413 -and $r.Code -lt 500) $r.Code
$r = Req POST '/api/matkul-recommender/panduan/extract-upload' -Token $student -File $f17
Report 'upload 17 MB' ($r.Code -eq 413 -and (JsonDetail $r) -eq 'Ukuran file melebihi batas') "$($r.Code)"
Remove-Item $f14, $f17, $notpdf -ErrorAction SilentlyContinue

"== 9. CORS"
$o = 'http://127.0.0.1:5500'
$r = Req OPTIONS '/api/judul-recommender/get-recommendations' -Extra @('-H', "Origin: $o", '-H', 'Access-Control-Request-Method: POST', '-H', 'Access-Control-Request-Headers: authorization,content-type')
Report 'preflight origin diizinkan' ($r.Code -eq 204 -and $r.Head -match "(?im)^Access-Control-Allow-Origin: $([regex]::Escape($o))\s*$" -and $r.Head -match '(?im)^Access-Control-Allow-Headers:.*Authorization') $r.Code
$r = Req OPTIONS '/api/judul-recommender/get-recommendations' -Extra @('-H', 'Origin: http://evil.example', '-H', 'Access-Control-Request-Method: POST')
Report 'preflight origin asing' ($r.Code -eq 204 -and $r.Head -notmatch '(?im)^Access-Control-Allow-Origin:') $r.Code
$r = Req GET '/api/judul-recommender/' -Extra @('-H', "Origin: $o")
Report '401 memuat header CORS' ($r.Code -eq 401 -and $r.Head -match "(?im)^Access-Control-Allow-Origin: $([regex]::Escape($o))\s*$") $r.Code

"== 10. Pemalsuan header X-User-*"
$r = Req POST '/api/micro-cred/tracks' -Token $student -Json '{}' -Extra @('-H', 'X-User-Id: 999', '-H', 'X-User-Roles: admin')
Report 'student + header admin palsu tetap 403' ($r.Code -eq 403) $r.Code

"== 11. Verifier mati (fail closed)"
docker compose stop auth-verifier 2>&1 | Out-Null
$r = Req GET '/api/judul-recommender/' -Token $student
Report 'rute terproteksi -> 503' ($r.Code -eq 503 -and (JsonDetail $r) -eq 'Layanan autentikasi tidak tersedia') "$($r.Code) $(JsonDetail $r)"
$r = Req GET '/api/micro-cred/health'; Report 'health publik tetap 200' ($r.Code -eq 200) $r.Code
docker compose start auth-verifier 2>&1 | Out-Null
Start-Sleep 15
docker compose restart nginx 2>&1 | Out-Null
Start-Sleep 12
$r = Req GET '/api/micro-cred/auth/me' -Token $student; Report 'pulih setelah start verifier + restart nginx' ($r.Code -eq 200) $r.Code
docker compose ps --format '{{.Service}} {{.Status}}'

"== Ringkasan: $script:fail FAIL"
exit $script:fail

