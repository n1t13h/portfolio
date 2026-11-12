#!/usr/bin/env bash
# Runs ON the server, as root, from /opt/portfolio/backend/deploy. Called by deploy/deploy.sh.
# Safe to run again: every step checks what is already there.
#   usage: server-setup.sh <domain>
#
# The box is shared with CraftClash (~/code/craftclash owns the instance, Caddy and the main
# Caddyfile). This script only touches portfolio-owned paths: the `portfolio` user, /opt/portfolio,
# /var/lib/portfolio, /etc/portfolio, /etc/caddy/sites/portfolio.caddy and portfolio-* units.
# It never restarts Caddy (a reload keeps live CraftClash connections) and never runs apt.
set -euo pipefail

DOMAIN=${1:?usage: server-setup.sh <domain>}
APP=/opt/portfolio/backend
DATA=/var/lib/portfolio
ENV_FILE=/etc/portfolio/backend.env
DB=$DATA/portfolio.db
PORT=8100

log() { printf '\n==> %s\n' "$*"; }

for bin in caddy uv sqlite3 curl openssl; do
  command -v "$bin" >/dev/null || { echo "missing $bin: run the craftclash deploy first" >&2; exit 1; }
done
grep -q '^import /etc/caddy/sites/\*\.caddy' /etc/caddy/Caddyfile \
  || { echo "/etc/caddy/Caddyfile does not import sites/*.caddy: run the craftclash deploy first" >&2; exit 1; }

# ---------- user and directories ----------
id portfolio >/dev/null 2>&1 || useradd --system --home "$DATA" --shell /usr/sbin/nologin portfolio
install -d -m 750 -o portfolio -g portfolio "$DATA" "$DATA/backups"
install -d -m 755 /etc/portfolio

# ---------- Python + dependencies ----------
log "Python dependencies"
# Our own Python under /opt/portfolio (root-owned, world-readable), not CraftClash's copy.
export UV_PYTHON_INSTALL_DIR=/opt/portfolio/python UV_CACHE_DIR=/var/cache/uv
(cd "$APP" && uv sync --frozen --no-dev --python 3.12 --quiet)

# ---------- secrets: generated once, never overwritten ----------
if [ ! -f "$ENV_FILE" ]; then
  log "Creating $ENV_FILE (fill in R2, Unsplash and Telegram keys there)"
  umask 077
  sed -e "s|^DATABASE_URL=.*|DATABASE_URL=sqlite:///${DB}|" \
      -e "s|^ADMIN_PATH_PREFIX=.*|ADMIN_PATH_PREFIX=$(openssl rand -hex 24)|" \
      -e "s|^SESSION_SECRET=.*|SESSION_SECRET=$(openssl rand -hex 32)|" \
      "$APP/.env.example" >"$ENV_FILE"
  umask 022
fi
# Owned by the app user so `sudo -u portfolio python -m app.cli ...` can read it; the service
# itself sees /etc read-only (ProtectSystem=strict).
chown portfolio:portfolio "$ENV_FILE"
chmod 600 "$ENV_FILE"
ln -sfn "$ENV_FILE" "$APP/.env" # the CLI reads .env from the working directory

# ---------- Caddy site ----------
log "Caddy site"
SITE=/etc/caddy/sites/portfolio.caddy
[ -f "$SITE" ] && cp -p "$SITE" "$SITE.prev"
sed "s/^api\.ntshptl\.in {/${DOMAIN} {/" "$APP/deploy/portfolio.caddy" >"$SITE"
# A broken site file would also break CraftClash's next reload, so put the old one back on failure.
if ! caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null; then
  if [ -f "$SITE.prev" ]; then mv "$SITE.prev" "$SITE"; else rm -f "$SITE"; fi
  echo "portfolio.caddy is invalid; kept the previous site file" >&2
  exit 1
fi
rm -f "$SITE.prev"

# ---------- systemd units ----------
log "systemd units"
for u in portfolio-api.service \
         portfolio-sync.service portfolio-sync.timer \
         portfolio-backup.service portfolio-backup.timer \
         portfolio-notify.service portfolio-notify.timer; do
  install -m 644 "$APP/deploy/$u" "/etc/systemd/system/$u"
done
systemctl daemon-reload

# ---------- backup before replacing the running version ----------
if [ -f "$DB" ]; then
  log "Pre-deploy backup"
  sudo -u portfolio sqlite3 "$DB" ".backup $DATA/backups/predeploy-$(date +%F-%H%M).db"
  # keep the 5 newest
  ls -1t "$DATA"/backups/predeploy-*.db 2>/dev/null | tail -n +6 | xargs -r rm -f
fi

# ---------- (re)start ----------
log "Starting services"
setting() { sed -n "s/^$1=//p" "$ENV_FILE"; }
# A timer whose service has no credentials yet would only fail every run, so it waits for them.
timer() { # timer <name> <required setting>
  if [ -n "$(setting "$2")" ]; then
    systemctl enable --now "portfolio-$1.timer" >/dev/null 2>&1
  else
    systemctl disable --now "portfolio-$1.timer" >/dev/null 2>&1 || true
    echo "    portfolio-$1.timer off until $2 is set in $ENV_FILE"
  fi
}
timer sync UNSPLASH_ACCESS_KEY
timer backup R2_ACCESS_KEY
timer notify TELEGRAM_BOT_TOKEN

systemctl enable portfolio-api >/dev/null 2>&1
systemctl restart portfolio-api
systemctl reload caddy

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    log "API is healthy: https://${DOMAIN}/health"
    exit 0
  fi
  sleep 1
done
echo "API did not become healthy; see: journalctl -u portfolio-api -n 50" >&2
exit 1
