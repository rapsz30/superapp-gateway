#!/usr/bin/env bash
# Smoke test CI untuk superapp-gateway (Bash, LF, memakai curl & jq).
# Tidak pernah mencetak token atau secret ke stdout/stderr, dan tidak memanggil LLM.

set -uo pipefail

# Fallback ke python bila biner jq belum terpasang di Git Bash lokal (di runner CI ubuntu-latest jq sudah tersedia)
if ! command -v jq >/dev/null 2>&1; then
  jq() {
    python - "$@" << 'PY'
import json, sys
args = sys.argv[1:]
if "-n" in args:
    out = {}
    i = 0
    while i < len(args):
        if args[i] == "--arg" and i + 2 < len(args):
            out[args[i + 1]] = args[i + 2]
            i += 3
        else:
            i += 1
    print(json.dumps(out))
elif "-r" in args:
    idx = args.index("-r")
    expr = args[idx + 1].split("//")[0].strip().lstrip(".")
    fpath = args[idx + 2]
    try:
        with open(fpath, "r", encoding="utf-8") as fh:
            cur = json.load(fh)
        for part in expr.split("."):
            if part:
                cur = cur.get(part) if isinstance(cur, dict) else None
        print(cur if isinstance(cur, str) else "")
    except Exception:
        print("")
PY
  }
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"
FAIL_COUNT=0
TMP_DIR=".smoke-tmp-$$"
mkdir -p "$TMP_DIR"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

report() {
  local name="$1"
  local ok="$2"
  local info="$3"
  if [ "$ok" = "1" ]; then
    printf "PASS  %s  (%s)\n" "$name" "$info"
  else
    printf "FAIL  %s  (%s)\n" "$name" "$info"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

echo "== 1. Health check publik (/healthz dan /api/micro-cred/health, tunggu maks 120s) =="
DEADLINE=$((SECONDS + 120))
HZ_CODE="000"
MC_CODE="000"
while [ $SECONDS -lt $DEADLINE ]; do
  HZ_CODE="$(curl -s -m 5 -o "$TMP_DIR/hz.json" -w "%{http_code}" "$BASE_URL/healthz" 2>/dev/null)" || HZ_CODE="000"
  MC_CODE="$(curl -s -m 5 -o "$TMP_DIR/mc.json" -w "%{http_code}" "$BASE_URL/api/micro-cred/health" 2>/dev/null)" || MC_CODE="000"
  if [ "$HZ_CODE" = "200" ] && [ "$MC_CODE" = "200" ]; then
    break
  fi
  sleep 2
done
[ "$HZ_CODE" = "200" ] && report "GET /healthz -> 200" 1 "$HZ_CODE" || report "GET /healthz -> 200" 0 "$HZ_CODE"
[ "$MC_CODE" = "200" ] && report "GET /api/micro-cred/health -> 200" 1 "$MC_CODE" || report "GET /api/micro-cred/health -> 200" 0 "$MC_CODE"

echo "== 2. Registrasi akun acak (201) dan login (200) =="
TS="$(date +%s)"
RND_NIM="$(awk 'BEGIN{srand(); printf "%08d", int(10000000 + rand()*89999999)}')"
EMAIL="uji-ci-${TS}-${RND_NIM}@example.com"
PASSWORD="UjiCiPassword123!"

jq -n \
  --arg email "$EMAIL" \
  --arg password "$PASSWORD" \
  --arg full_name "Mahasiswa Uji CI" \
  --arg nim "$RND_NIM" \
  --arg faculty "Fakultas Teknologi Industri" \
  --arg study_program "Informatika" \
  '{email:$email, password:$password, full_name:$full_name, nim:$nim, faculty:$faculty, study_program:$study_program}' \
  > "$TMP_DIR/register.json"

REG_CODE="$(curl -s -m 15 -o "$TMP_DIR/reg_resp.json" -w "%{http_code}" \
  -X POST "$BASE_URL/api/micro-cred/auth/register" \
  -H "Content-Type: application/json" \
  --data-binary "@$TMP_DIR/register.json" 2>/dev/null)" || REG_CODE="000"
[ "$REG_CODE" = "201" ] && report "POST /api/micro-cred/auth/register -> 201" 1 "$REG_CODE" || report "POST /api/micro-cred/auth/register -> 201" 0 "$REG_CODE"

jq -n --arg email "$EMAIL" --arg password "$PASSWORD" '{email:$email, password:$password}' > "$TMP_DIR/login.json"
LOGIN_CODE="$(curl -s -m 15 -o "$TMP_DIR/login_resp.json" -w "%{http_code}" \
  -X POST "$BASE_URL/api/micro-cred/auth/login" \
  -H "Content-Type: application/json" \
  --data-binary "@$TMP_DIR/login.json" 2>/dev/null)" || LOGIN_CODE="000"
STUDENT_TOKEN="$(jq -r '.tokens.access_token // empty' "$TMP_DIR/login_resp.json" 2>/dev/null | tr -d '\r\n' || true)"

if [ "$LOGIN_CODE" = "200" ] && [ -n "$STUDENT_TOKEN" ]; then
  report "POST /api/micro-cred/auth/login -> 200 + access_token" 1 "$LOGIN_CODE"
else
  report "POST /api/micro-cred/auth/login -> 200 + access_token" 0 "$LOGIN_CODE"
  echo "FAIL  Token student tidak diperoleh, menghentikan smoke test."
  exit 1
fi

echo "== 3. Akses rute terproteksi tanpa token -> 401 =="
C_NOAUTH_1="$(curl -s -m 10 -o "$TMP_DIR/na1.json" -w "%{http_code}" "$BASE_URL/api/micro-cred/tracks" 2>/dev/null)" || C_NOAUTH_1="000"
[ "$C_NOAUTH_1" = "401" ] && report "GET /api/micro-cred/tracks tanpa token -> 401" 1 "$C_NOAUTH_1" || report "GET /api/micro-cred/tracks tanpa token -> 401" 0 "$C_NOAUTH_1"

C_NOAUTH_2="$(curl -s -m 10 -o "$TMP_DIR/na2.json" -w "%{http_code}" "$BASE_URL/api/judul-recommender/" 2>/dev/null)" || C_NOAUTH_2="000"
[ "$C_NOAUTH_2" = "401" ] && report "GET /api/judul-recommender/ tanpa token -> 401" 1 "$C_NOAUTH_2" || report "GET /api/judul-recommender/ tanpa token -> 401" 0 "$C_NOAUTH_2"

C_NOAUTH_3="$(curl -s -m 10 -o "$TMP_DIR/na3.json" -w "%{http_code}" \
  -X POST "$BASE_URL/api/matkul-recommender/rekomendasi" \
  -H "Content-Type: application/json" -d '{}' 2>/dev/null)" || C_NOAUTH_3="000"
[ "$C_NOAUTH_3" = "401" ] && report "POST /api/matkul-recommender/rekomendasi tanpa token -> 401" 1 "$C_NOAUTH_3" || report "POST /api/matkul-recommender/rekomendasi tanpa token -> 401" 0 "$C_NOAUTH_3"

echo "== 4. Akses rute dengan token student sah =="
C_STU_1="$(curl -s -m 10 -o "$TMP_DIR/st1.json" -w "%{http_code}" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  "$BASE_URL/api/micro-cred/tracks" 2>/dev/null)" || C_STU_1="000"
[ "$C_STU_1" = "200" ] && report "GET /api/micro-cred/tracks (student) -> 200" 1 "$C_STU_1" || report "GET /api/micro-cred/tracks (student) -> 200" 0 "$C_STU_1"

C_STU_2="$(curl -s -m 10 -o "$TMP_DIR/st2.json" -w "%{http_code}" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  "$BASE_URL/api/judul-recommender/" 2>/dev/null)" || C_STU_2="000"
[ "$C_STU_2" = "200" ] && report "GET /api/judul-recommender/ (student) -> 200" 1 "$C_STU_2" || report "GET /api/judul-recommender/ (student) -> 200" 0 "$C_STU_2"

printf "bukan-file-pdf" > "$TMP_DIR/notpdf.bin"
C_STU_3="$(curl -s -m 15 -o "$TMP_DIR/st3.json" -w "%{http_code}" \
  -X POST "$BASE_URL/api/matkul-recommender/panduan/extract-upload" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -F "file_pdf=@$TMP_DIR/notpdf.bin" 2>/dev/null)" || C_STU_3="000"
[ "$C_STU_3" = "400" ] && report "POST /api/matkul-recommender/panduan/extract-upload non-PDF -> 400" 1 "$C_STU_3" || report "POST /api/matkul-recommender/panduan/extract-upload non-PDF -> 400" 0 "$C_STU_3"

echo "== 5. Token student menulis ke /api/micro-cred/tracks -> 403 =="
C_RBAC="$(curl -s -m 10 -o "$TMP_DIR/rbac.json" -w "%{http_code}" \
  -X POST "$BASE_URL/api/micro-cred/tracks" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" -d '{}' 2>/dev/null)" || C_RBAC="000"
RBAC_DETAIL="$(jq -r '.detail // empty' "$TMP_DIR/rbac.json" 2>/dev/null | tr -d '\r\n' || true)"
if [ "$C_RBAC" = "403" ] && [ "$RBAC_DETAIL" = "Akses ditolak" ]; then
  report "POST /api/micro-cred/tracks (student) -> 403 JSON" 1 "$C_RBAC $RBAC_DETAIL"
else
  report "POST /api/micro-cred/tracks (student) -> 403 JSON" 0 "$C_RBAC $RBAC_DETAIL"
fi

echo "== 6. Upload 17 MB -> 413 JSON dari NGINX =="
dd if=/dev/zero of="$TMP_DIR/file17mb.bin" bs=1M count=17 status=none
C_413="$(curl -s -m 30 -o "$TMP_DIR/err413.json" -w "%{http_code}" \
  -X POST "$BASE_URL/api/matkul-recommender/panduan/extract-upload" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -F "file_pdf=@$TMP_DIR/file17mb.bin" 2>/dev/null)" || C_413="000"
DETAIL_413="$(jq -r '.detail // empty' "$TMP_DIR/err413.json" 2>/dev/null | tr -d '\r\n' || true)"
if [ "$C_413" = "413" ] && [ "$DETAIL_413" = "Ukuran file melebihi batas" ]; then
  report "Upload 17 MB -> 413 JSON" 1 "$C_413 $DETAIL_413"
else
  report "Upload 17 MB -> 413 JSON" 0 "$C_413 $DETAIL_413"
fi

echo "== 7. Preflight CORS =="
ALLOWED_ORIGIN="http://127.0.0.1:5500"
C_CORS_OK="$(curl -s -m 10 -D "$TMP_DIR/cors_ok.hdr" -o "$TMP_DIR/null.out" -w "%{http_code}" \
  -X OPTIONS "$BASE_URL/api/judul-recommender/get-recommendations" \
  -H "Origin: $ALLOWED_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization, Content-Type" 2>/dev/null)" || C_CORS_OK="000"
if [ "$C_CORS_OK" = "204" ] && grep -qi "^Access-Control-Allow-Origin: ${ALLOWED_ORIGIN}" "$TMP_DIR/cors_ok.hdr"; then
  report "OPTIONS preflight origin diizinkan -> 204 + ACAO" 1 "$C_CORS_OK"
else
  report "OPTIONS preflight origin diizinkan -> 204 + ACAO" 0 "$C_CORS_OK"
fi

C_CORS_EVIL="$(curl -s -m 10 -D "$TMP_DIR/cors_evil.hdr" -o "$TMP_DIR/null.out" -w "%{http_code}" \
  -X OPTIONS "$BASE_URL/api/judul-recommender/get-recommendations" \
  -H "Origin: http://evil.example" \
  -H "Access-Control-Request-Method: POST" 2>/dev/null)" || C_CORS_EVIL="000"
if [ "$C_CORS_EVIL" = "204" ] && ! grep -qi "^Access-Control-Allow-Origin:" "$TMP_DIR/cors_evil.hdr"; then
  report "OPTIONS preflight origin asing -> 204 tanpa ACAO" 1 "$C_CORS_EVIL"
else
  report "OPTIONS preflight origin asing -> 204 tanpa ACAO" 0 "$C_CORS_EVIL"
fi

echo "== 8. Token ditandatangani dengan secret lain -> 401 =="
FOREIGN_TOKEN="$(docker compose exec -T auth-verifier python -c "import time, secrets, jwt; now=int(time.time()); print(jwt.encode({'sub':'ci-foreign-user','roles':['student'],'iat':now,'exp':now+600,'iss':'ci'}, secrets.token_hex(32), algorithm='HS256'))" 2>/dev/null | tr -d '\r\n' || true)"
if [ -n "$FOREIGN_TOKEN" ]; then
  C_FOREIGN="$(curl -s -m 10 -o "$TMP_DIR/foreign.json" -w "%{http_code}" \
    -H "Authorization: Bearer $FOREIGN_TOKEN" \
    "$BASE_URL/api/micro-cred/auth/me" 2>/dev/null)" || C_FOREIGN="000"
  [ "$C_FOREIGN" = "401" ] && report "Token dengan secret asing -> 401" 1 "$C_FOREIGN" || report "Token dengan secret asing -> 401" 0 "$C_FOREIGN"
else
  report "Token dengan secret asing -> 401" 0 "Gagal membuat token di container auth-verifier"
fi

echo "== 9. Percobaan melewati kebijakan (/api/micro-cred/%74racks) -> 403 =="
C_BYPASS="$(curl -s -m 10 --path-as-is -o "$TMP_DIR/bypass.json" -w "%{http_code}" \
  -X POST "$BASE_URL/api/micro-cred/%74racks" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" -d '{}' 2>/dev/null)" || C_BYPASS="000"
[ "$C_BYPASS" = "403" ] && report "POST /api/micro-cred/%74racks (--path-as-is) -> 403" 1 "$C_BYPASS" || report "POST /api/micro-cred/%74racks (--path-as-is) -> 403" 0 "$C_BYPASS"

echo "== Ringkasan: $FAIL_COUNT FAIL =="
if [ "$FAIL_COUNT" -ne 0 ]; then
  exit 1
fi
exit 0
