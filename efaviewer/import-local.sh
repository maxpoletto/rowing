#!/bin/bash
# import-local.sh -- regenerate the viewer's JSON from the newest EFA backup
# already present on this host. The boathouse PC scp's nightly efaBackup_*.zip
# into $EFA_BACKUPS; the VM cron runs this. For the developer remote-pull
# workflow, use import.sh instead.
#
# Overridable (defaults suit the VM):
#   EFA_BACKUPS  dir holding efaBackup_*.zip   (default /home/efa/backups)
#   EFA_OUTDIR   JSON output dir               (default <script-dir>/app/data)
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backups="${EFA_BACKUPS:-/home/efa/backups}"
outdir="${EFA_OUTDIR:-$here/app/data}"
club=BelvoirRC

name="$(ls "$backups" 2>/dev/null | grep -E 'efaBackup.*zip' | tail -1 || true)"
[[ -n "$name" ]] || { echo "import-local.sh: no efaBackup_*.zip in $backups" >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

unzip -q "$backups/$name" -d "$tmp"
data="$tmp/data/$club"

mkdir -p "$outdir"
python3 "$here/bin/efa_importer.py" --max-distance 500 \
  --boats "$data/boats.efa2boats" \
  --persons "$data/persons.efa2persons" \
  --destinations "$data/destinations.efa2destinations" \
  --logbooks "$data/20*.efa2logbook" \
  --output "$outdir"
gunzip -kf "$outdir"/*.gz
