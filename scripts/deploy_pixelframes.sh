#!/bin/sh
# Build the PixelFrames conference site and mirror it to the FTP host.
#
#   FTP_PASS='...' ./scripts/deploy_pixelframes.sh
#
# The password is read from the environment and never stored in this repo.
# FTP_HOST defaults to the hostname rather than the 172.21.66.7 shown in the
# hosting panel — that is a private-range address and will not route from
# outside the host's own network. Override any of these if the panel differs.
#
# ponytail: build + lftp mirror, no state file, no manifest. Swap the mirror for
# rsync over ssh if SSH access ever gets enabled on this account.
set -eu

: "${FTP_PASS:?set FTP_PASS (e.g. FTP_PASS='...' $0)}"
FTP_HOST="${FTP_HOST:-pixelframe2027.unidcom-iade.pt}"
FTP_USER="${FTP_USER:-Senses2021pro_user}"
FTP_DIR="${FTP_DIR:-/}"

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC="$ROOT/pixelframes"

command -v hugo >/dev/null || { echo "hugo not found" >&2; exit 1; }
command -v lftp >/dev/null || { echo "lftp not found (brew install lftp)" >&2; exit 1; }

hugo --source "$SRC" --minify --gc --cleanDestinationDir

# Refuse to mirror an empty build rather than --delete the live site away.
[ -f "$SRC/public/index.html" ] || { echo "build produced no index.html" >&2; exit 1; }

echo "Mirroring $SRC/public/ -> $FTP_USER@$FTP_HOST:$FTP_DIR"
lftp -u "$FTP_USER,$FTP_PASS" "$FTP_HOST" -e "
  set ssl:verify-certificate no;
  mirror --reverse --delete --verbose --exclude-glob .git* '$SRC/public/' '$FTP_DIR';
  bye
"
echo "Done: https://$FTP_HOST/"
