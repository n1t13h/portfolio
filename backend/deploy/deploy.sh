#!/usr/bin/env bash
# Runs on YOUR laptop. Copies the backend to the shared CraftClash EC2 box and runs
# server-setup.sh there.
#   usage: deploy/deploy.sh                       (from backend/)
#   env:   SSH_KEY=~/.ssh/craftclash-ec2.pem      (optional, if the key isn't in your ssh-agent/config)
#
# The instance itself (size, firewall, Elastic IP) is managed by Terraform in
# ~/code/craftclash/infra/terraform. Don't manage it from here.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
HOST=${HOST:-15.252.177.189}
DOMAIN=${DOMAIN:-api.ntshptl.in}
TARGET=ubuntu@$HOST
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -n "${SSH_KEY:-}" ] && SSH_OPTS+=(-i "$SSH_KEY")

echo "==> Deploying to $TARGET as https://$DOMAIN"

# api is proxied by Cloudflare (orange cloud), so it resolves to Cloudflare, not to $HOST.
if [ -z "$(dig +short A "$DOMAIN" | tail -1)" ]; then
  echo "    warning: $DOMAIN does not resolve. Add it in Cloudflare (proxied) -> $HOST."
fi

echo "==> Copying files"
ssh "${SSH_OPTS[@]}" "$TARGET" 'sudo install -d -m 755 /opt/portfolio /opt/portfolio/backend'
# .env is a symlink to /etc/portfolio/backend.env on the server; --delete must leave it alone.
# -rlpt, not -a: without -o/-g the files are owned by the receiving side (root), so the app user
# can run the code but not change it. (macOS's openrsync has no --chown.)
rsync -rlptz --delete -e "ssh ${SSH_OPTS[*]}" --rsync-path="sudo rsync" \
  --filter 'P /.env' --filter 'P /.venv/' \
  --exclude '__pycache__/' \
  --include '/app/***' --include '/alembic/***' --include '/deploy/***' --include '/seed/***' \
  --include '/alembic.ini' --include '/pyproject.toml' --include '/uv.lock' --include '/.env.example' \
  --include '/README.md' \
  --exclude '*' \
  "$ROOT/" "$TARGET:/opt/portfolio/backend/"

echo "==> Running setup on the server"
ssh "${SSH_OPTS[@]}" "$TARGET" "sudo bash /opt/portfolio/backend/deploy/server-setup.sh '$DOMAIN'"

echo
echo "Done. Admin path prefix:"
echo "  ssh ${SSH_OPTS[*]} $TARGET sudo grep ADMIN_PATH_PREFIX /etc/portfolio/backend.env"
