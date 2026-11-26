#!/usr/bin/env bash
# Deploy superapp ke VPS: kemas commit -> unggah -> cadangkan basis data -> build -> nyalakan -> periksa -> rollback.
# Dijalankan dari Git Bash di laptop. Konfigurasi di deploy/deploy.env (lihat deploy.env.example).
#
#   ./deploy/deploy-vps.sh kemas    hanya membuat dan memeriksa arsip (tidak menyentuh server)
#   ./deploy/deploy-vps.sh siapkan  pertama kali: unggah kode dan buat berkas .env kosong di server untuk diisi
#   ./deploy/deploy-vps.sh          deploy
#
# Hanya isi COMMIT terakhir yang dikirim. Berkas .env dan sertifikat tidak pernah dikirim dari laptop; keduanya
# disimpan di server pada $REMOTE_DIR/env dan disalin ke setiap rilis.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-deploy}"
case "$MODE" in kemas|siapkan|deploy) ;; *) echo "Pakai: $0 [kemas|siapkan|deploy]"; exit 1 ;; esac

cd "$ROOT"
if [[ -f deploy/deploy.env ]]; then
  # shellcheck disable=SC1091
  source <(tr -d '\r' < deploy/deploy.env)
elif [[ "$MODE" != "kemas" ]]; then
  echo "deploy/deploy.env belum ada. Salin dari deploy/deploy.env.example lalu isi."; exit 1
fi
SSH_HOST="${SSH_HOST:-}"; REMOTE_DIR="${REMOTE_DIR:-superapp}"; PROXY="${PROXY:-ada}"
DOMAIN="${DOMAIN:-localhost}"; GATEWAY_PORT="${GATEWAY_PORT:-8080}"; FRONTEND_PORT="${FRONTEND_PORT:-3200}"
# Nilai ini disisipkan ke perintah di server, jadi bentuknya dibatasi.
[[ "$REMOTE_DIR" =~ ^[A-Za-z0-9_./-]+$ ]] || { echo "REMOTE_DIR tidak sah"; exit 1; }
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || { echo "DOMAIN tidak sah"; exit 1; }
[[ "$GATEWAY_PORT$FRONTEND_PORT" =~ ^[0-9]+$ ]] || { echo "Port harus angka"; exit 1; }
[[ "$PROXY" == "ada" || "$PROXY" == "caddy" ]] || { echo "PROXY harus 'ada' atau 'caddy'"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> [1] Kemas commit"
REV="$(git rev-parse --short HEAD)"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "    PERINGATAN: ada perubahan belum di-commit; TIDAK ikut dikirim."
fi
ARSIP="$TMP/superapp-$REV.tar.gz"
# Akhiran baris LF, apa pun pengaturan git di Windows.
git -c core.autocrlf=false -c core.eol=lf archive --format=tar.gz -o "$ARSIP" HEAD
echo "    commit $REV  $(du -h "$ARSIP" | cut -f1)"
for wajib in docker-compose.prod.yml frontend/Dockerfile deploy/Caddyfile; do
  tar -tzf "$ARSIP" | grep -qx "$wajib" || { echo "DIBATALKAN: $wajib belum ada di commit."; exit 1; }
done

echo "==> [2] Cek berkas sensitif di dalam arsip"
if tar -tzf "$ARSIP" | grep -E '(^|/)(\.env(\.local|\.production)?|deploy\.env|id_(rsa|ed25519|ecdsa))$|\.(pem|key|p12)$|(^|/)node_modules/'; then
  echo "DIBATALKAN: berkas sensitif ada di arsip."; exit 1
fi
echo "    bersih"
[[ "$MODE" == "kemas" ]] && { echo "Selesai (tidak ada yang dikirim)."; exit 0; }
[[ -n "$SSH_HOST" && "$SSH_HOST" != "nama-alias-ssh" ]] || { echo "Isi SSH_HOST di deploy/deploy.env"; exit 1; }

echo "==> [3] Unggah ke $SSH_HOST"
ssh "$SSH_HOST" "mkdir -p '$REMOTE_DIR/releases/$REV' '$REMOTE_DIR/env' '$REMOTE_DIR/backup'"
scp -q "$ARSIP" "$SSH_HOST:$REMOTE_DIR/releases/$REV.tar.gz"

echo "==> [4] Jalankan di server"
# shellcheck disable=SC2087
ssh "$SSH_HOST" bash -s -- "$MODE" "$REMOTE_DIR" "$REV" "$PROXY" "$DOMAIN" "$GATEWAY_PORT" "$FRONTEND_PORT" <<'REMOTE'
set -euo pipefail
MODE="$1"; BASE="$(cd "$2" && pwd)"; REV="$3"; PROXY="$4"
export DOMAIN="$5" GATEWAY_PORT="$6" FRONTEND_PORT="$7"
REL="$BASE/releases/$REV"
tar -xzf "$BASE/releases/$REV.tar.gz" -C "$REL"
rm -f "$BASE/releases/$REV.tar.gz"

ENV_FILES="services/identity/.env services/matkul/.env.local services/microcred/.env services/judul/.env alurkerja-connector/.env"

if [[ "$MODE" == "siapkan" ]]; then
  for f in $ENV_FILES; do
    tujuan="$BASE/env/$f"
    mkdir -p "$(dirname "$tujuan")"
    if [[ ! -f "$tujuan" ]]; then
      cp "$REL/$(dirname "$f")/.env.example" "$tujuan"; chmod 600 "$tujuan"; echo "    dibuat: $tujuan"
    else
      echo "    sudah ada, tidak diubah: $tujuan"
    fi
  done
  echo
  echo "Isi berkas di $BASE/env (secret baru, jangan salin dari laptop), lalu jalankan deploy."
  exit 0
fi

command -v docker >/dev/null || { echo "Docker belum terpasang di server."; exit 1; }
for f in $ENV_FILES; do
  [[ -f "$BASE/env/$f" ]] || { echo "Belum ada $BASE/env/$f. Jalankan 'siapkan' dulu."; exit 1; }
  cp "$BASE/env/$f" "$REL/$f"
done
mkdir -p "$REL/alurkerja-connector/certs"
if [[ -f "$BASE/env/rootCA.pem" ]]; then
  cp "$BASE/env/rootCA.pem" "$REL/alurkerja-connector/certs/rootCA.pem"
else
  : > "$REL/alurkerja-connector/certs/rootCA.pem"   # berkas kosong: Docker tidak membuatnya sebagai folder
fi
chmod 644 "$REL/alurkerja-connector/certs/rootCA.pem"

nilai() { grep -E "^$2=" "$BASE/env/$1" | head -1 | cut -d= -f2- | tr -d "\"'\r"; }
masalah=0
for pasangan in "services/identity/.env JWT_SECRET" "services/identity/.env INTERNAL_TOKEN" \
  "services/identity/.env POSTGRES_PASSWORD" "services/matkul/.env.local POSTGRES_PASSWORD" \
  "services/matkul/.env.local MATKUL_SERVICE_TOKEN" "services/microcred/.env JWT_SECRET" \
  "services/microcred/.env POSTGRES_PASSWORD" "services/judul/.env GROQ_API_KEY"; do
  read -r f k <<<"$pasangan"
  v="$(nilai "$f" "$k" || true)"
  if [[ -z "$v" || "$v" == *ganti* || "$v" == *replace* || "$v" == *change* ]]; then
    echo "    belum diisi dengan benar: $f -> $k"; masalah=1
  fi
done
if [[ "$(nilai services/identity/.env JWT_SECRET)" == "$(nilai services/microcred/.env JWT_SECRET)" ]]; then
  echo "    JWT_SECRET micro-credential harus BERBEDA dari identity (pendaftarannya terbuka)."; masalah=1
fi
[[ "$masalah" == 0 ]] || { echo "DIBATALKAN: perbaiki berkas .env di server."; exit 1; }

PROFIL=(); [[ "$PROXY" == "caddy" ]] && PROFIL=(--profile https)
compose() { docker compose -f docker-compose.yml -f docker-compose.prod.yml "${PROFIL[@]}" "$@"; }
LAMA=""; [[ -L "$BASE/current" ]] && LAMA="$(readlink -f "$BASE/current")"

cd "$REL"
compose config -q

if [[ -n "$LAMA" ]]; then
  echo "    cadangkan basis data"
  cap="$(date +%Y%m%d-%H%M%S)"
  for svc in identity-db matkul-db db; do
    (cd "$LAMA" && compose exec -T "$svc" sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"') | gzip > "$BASE/backup/$cap-$svc.sql.gz" \
      || { echo "DIBATALKAN: pencadangan $svc gagal."; exit 1; }
  done
  chmod 600 "$BASE"/backup/*.gz
fi

echo "    build (versi lama masih melayani)"
compose build

sehat() {
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:$GATEWAY_PORT/healthz" >/dev/null \
      && curl -fsS "http://127.0.0.1:$GATEWAY_PORT/api/identity/health" >/dev/null \
      && curl -fsS -o /dev/null "http://127.0.0.1:$FRONTEND_PORT/login" \
      && curl -fsS "http://127.0.0.1:$FRONTEND_PORT/api/identity/health" >/dev/null; then
      return 0
    fi
    sleep 4
  done
  return 1
}

nyalakan() {
  compose up -d --remove-orphans || return 1
  # NGINX menyimpan alamat layanan saat menyala; dibuat ulang agar mengikuti kontainer baru.
  compose up -d --force-recreate --no-deps nginx || return 1
}

echo "    nyalakan"
if nyalakan && sehat; then
  ln -sfn "$REL" "$BASE/current"
  echo "    sehat; rilis aktif: $REV"
  # Sisakan 3 rilis terbaru.
  ls -1dt "$BASE"/releases/*/ | tail -n +4 | xargs -r rm -rf
else
  echo "!! pemeriksaan gagal"
  compose ps || true
  compose logs --tail 40 identity-api nginx frontend || true
  if [[ -n "$LAMA" && "$LAMA" != "$REL" ]]; then
    echo "!! rollback ke $(basename "$LAMA") (perubahan skema basis data TIDAK dibatalkan; cadangan ada di $BASE/backup)"
    cd "$LAMA" && compose build && nyalakan && sehat && echo "    rollback sehat" || echo "!! rollback juga gagal, periksa server"
  fi
  exit 1
fi
REMOTE
echo; echo "Selesai ($MODE, commit $REV)."
