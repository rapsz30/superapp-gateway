#!/usr/bin/env bash
# Hapus superapp versi lama di server (dipasang 22 Nov: ~/projects/superapp-gateway, port 8082,
# domain api-superapp-gateway.ahlanapp.cloud). Dijalankan DI SERVER dengan sudo:
#
#   sudo bash hapus-versi-lama.sh lihat       tampilkan apa saja yang ada (tidak mengubah apa pun)
#   sudo bash hapus-versi-lama.sh cadangkan   simpan salinan berkas, volume, situs NGINX, dan basis data
#   sudo bash hapus-versi-lama.sh hapus       hentikan dan hapus (minta ketik HAPUS; wajib sudah dicadangkan,
#                                             kecuali ditambah --tanpa-cadangan)
#
# Hanya menyentuh milik superapp. Aplikasi lain di server tidak disentuh. Basis data di Postgres server
# TIDAK dihapus otomatis; perintahnya dicetak untuk dijalankan sendiri.
set -euo pipefail

MODE="${1:-lihat}"
OWNER="${SUDO_USER:-daffa}"
RUMAH="/home/$OWNER"
ROOT="$RUMAH/projects/superapp-gateway"
SETUP="$RUMAH/ahlan-superapp-setup"
PROYEK="superapp"
SITUS="api-superapp-gateway"
DOMAIN="api-superapp-gateway.ahlanapp.cloud"
CADANGAN="$RUMAH/cadangan-superapp-lama"

[[ "$(id -u)" == 0 ]] || { echo "Jalankan dengan sudo."; exit 1; }
case "$MODE" in lihat|cadangkan|hapus) ;; *) echo "Pakai: sudo bash $0 [lihat|cadangkan|hapus]"; exit 1 ;; esac

kontainer() { docker ps -a --filter "label=com.docker.compose.project=$PROYEK" "$@"; }
volume() { docker volume ls -q --filter "label=com.docker.compose.project=$PROYEK"; }
# Nama basis data Postgres server yang dipakai micro-credential (tanpa pengguna dan sandi).
basisdata() {
  local f="$ROOT/services/microcred/.env"
  [[ -f "$f" ]] || return 0
  grep -E '^DATABASE_URL=' "$f" | head -1 | tr -d "\"'\r" | sed -E 's#^.*@[^/]+/([^?]+).*$#\1#' | grep -E '^[A-Za-z0-9_-]+$' || true
}
# Pastikan kontainer proyek ini memang berasal dari folder versi lama.
periksa_asal() {
  local lain
  lain="$(kontainer --format '{{.Label "com.docker.compose.project.working_dir"}}' | sort -u | grep -v "^$ROOT\$" || true)"
  if [[ -n "$lain" ]]; then
    echo "DIBATALKAN: ada kontainer proyek '$PROYEK' dari folder lain: $lain"; exit 1
  fi
}

DB="$(basisdata)"

if [[ "$MODE" == "lihat" ]]; then
  echo "== kontainer proyek '$PROYEK'"
  kontainer --format '{{.Names}} | {{.Status}} | {{.Label "com.docker.compose.project.working_dir"}}'
  echo "== volume"; volume
  echo "== folder"; du -sh "$ROOT" "$SETUP" 2>/dev/null || true
  echo "== situs NGINX"; ls -l /etc/nginx/sites-enabled/$SITUS /etc/nginx/sites-available/$SITUS 2>/dev/null || true
  echo "== sertifikat"; command -v certbot >/dev/null && certbot certificates --cert-name "$DOMAIN" 2>/dev/null | grep -E "Certificate Name|Domains|Expiry" || true
  echo "== basis data micro-credential di Postgres server: ${DB:-tidak diketahui}"
  command -v psql >/dev/null && sudo -u postgres psql -Atc "select datname || ' | ' || pg_size_pretty(pg_database_size(datname)) from pg_database where not datistemplate order by 1" || true
  echo "== permintaan ke domain ini 7 hari terakhir (apakah masih dipakai?)"
  grep -h "$DOMAIN" /var/log/nginx/*.log 2>/dev/null | tail -3 || echo "(log NGINX tidak memisahkan domain; cek access.log)"
  tail -n 2000 /var/log/nginx/access.log 2>/dev/null | grep -cE '"(GET|POST|PUT|DELETE|PATCH) /api/' | sed 's/^/baris \/api\/ pada access.log terakhir: /' || true
  exit 0
fi

periksa_asal

if [[ "$MODE" == "cadangkan" ]]; then
  cap="$(date +%Y%m%d-%H%M%S)"; T="$CADANGAN/$cap"
  mkdir -p "$T"; chmod 700 "$CADANGAN" "$T"
  [[ -d "$ROOT" ]] && tar -czf "$T/projects-superapp-gateway.tar.gz" -C "$RUMAH/projects" superapp-gateway
  [[ -d "$SETUP" ]] && tar -czf "$T/ahlan-superapp-setup.tar.gz" -C "$RUMAH" ahlan-superapp-setup
  [[ -f /etc/nginx/sites-available/$SITUS ]] && cp /etc/nginx/sites-available/$SITUS "$T/nginx-$SITUS.conf"
  for v in $(volume); do
    echo "    volume $v"
    docker run --rm -v "$v:/data:ro" -v "$T:/out" alpine:3.20 tar -czf "/out/volume-$v.tar.gz" -C /data .
  done
  if [[ -n "$DB" ]] && command -v pg_dump >/dev/null; then
    echo "    basis data $DB"
    sudo -u postgres pg_dump "$DB" | gzip > "$T/db-$DB.sql.gz"
    gzip -t "$T/db-$DB.sql.gz"
  else
    echo "!! basis data tidak dicadangkan (nama tidak diketahui atau pg_dump tidak ada)"
  fi
  chown -R "$OWNER:$OWNER" "$CADANGAN"; chmod -R go-rwx "$CADANGAN"
  touch "$T/LENGKAP"
  echo; ls -lh "$T"; echo "Cadangan selesai: $T"
  exit 0
fi

# ------------------------------------------------------------------ hapus
if [[ "${2:-}" == "--tanpa-cadangan" ]]; then
  echo "PERHATIAN: tanpa cadangan. Volume dan folder yang dihapus tidak dapat dipulihkan."
else
  ls "$CADANGAN"/*/LENGKAP >/dev/null 2>&1 || { echo "Belum ada cadangan lengkap. Jalankan 'cadangkan' dulu, atau tambahkan --tanpa-cadangan."; exit 1; }
fi
echo "Yang akan DIHAPUS:"
echo "  - kontainer:"; kontainer --format '      {{.Names}}'
echo "  - volume:"; volume | sed 's/^/      /'
echo "  - folder: $ROOT dan $SETUP"
echo "  - situs NGINX $SITUS dan sertifikat $DOMAIN"
echo "Yang TIDAK dihapus: basis data Postgres '${DB:-?}' dan aplikasi lain."
read -r -p "Ketik HAPUS untuk melanjutkan: " jawab
[[ "$jawab" == "HAPUS" ]] || { echo "Dibatalkan."; exit 1; }

ids="$(kontainer -q)"; [[ -n "$ids" ]] && docker rm -f $ids >/dev/null
vols="$(volume)"; [[ -n "$vols" ]] && docker volume rm $vols >/dev/null
docker network ls -q --filter "label=com.docker.compose.project=$PROYEK" | xargs -r docker network rm >/dev/null
echo "    kontainer, volume, dan jaringan dihapus"

if [[ -e /etc/nginx/sites-enabled/$SITUS ]]; then
  rm -f /etc/nginx/sites-enabled/$SITUS
  if nginx -t; then
    systemctl reload nginx; rm -f /etc/nginx/sites-available/$SITUS; echo "    situs NGINX dihapus"
  else
    ln -s /etc/nginx/sites-available/$SITUS /etc/nginx/sites-enabled/$SITUS
    echo "!! nginx -t gagal; situs dikembalikan. Periksa konfigurasi NGINX."; exit 1
  fi
fi
command -v certbot >/dev/null && certbot delete --non-interactive --cert-name "$DOMAIN" || echo "!! sertifikat tidak terhapus (boleh diabaikan)"
rm -rf "$ROOT" "$SETUP"
echo "    folder dihapus"
echo
echo "Selesai. Bila basis data lama memang tidak diperlukan lagi:"
[[ -n "$DB" ]] && echo "    sudo -u postgres dropdb \"$DB\""
echo "Hapus juga catatan DNS $DOMAIN bila tidak dipakai lagi."
