#!/bin/bash
# Smoke test for import-local.sh: build a tiny synthetic EFA backup zip, run
# the importer through it, and check the JSON output.
# Synthetic data only -- no real club/member data.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/.." && pwd)"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

club="$tmp/src/data/BelvoirRC"
mkdir -p "$club"

cat > "$club/boats.efa2boats" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<efa2boats><data>
  <record>
    <Id>11111111-1111-1111-1111-111111111111</Id>
    <Name>Test Boat</Name>
    <TypeSeats>1</TypeSeats>
    <TypeRigging>X</TypeRigging>
    <TypeCoxing>N</TypeCoxing>
    <LastVariant>1</LastVariant>
  </record>
</data></efa2boats>
XML

cat > "$club/persons.efa2persons" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<efa2persons><data>
  <record>
    <Id>22222222-2222-2222-2222-222222222222</Id>
    <FirstName>Test</FirstName>
    <LastName>Rower</LastName>
    <Gender>MALE</Gender>
  </record>
</data></efa2persons>
XML

cat > "$club/destinations.efa2destinations" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<efa2destinations><data>
  <record>
    <Id>33333333-3333-3333-3333-333333333333</Id>
    <Name>Test Lake</Name>
    <Distance>10 km</Distance>
  </record>
</data></efa2destinations>
XML

cat > "$club/2024.efa2logbook" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<efa2logbook><data>
  <record>
    <Date>15.06.2024</Date>
    <BoatId>11111111-1111-1111-1111-111111111111</BoatId>
    <BoatVariant>1</BoatVariant>
    <Crew1Id>22222222-2222-2222-2222-222222222222</Crew1Id>
    <DestinationId>33333333-3333-3333-3333-333333333333</DestinationId>
    <Distance>10 km</Distance>
  </record>
</data></efa2logbook>
XML

fromdir="$tmp/backups"
mkdir -p "$fromdir"
python3 - "$tmp/src" "$fromdir/efaBackup_20240615_000000.zip" <<'PY'
import sys, zipfile, os
src, zippath = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(src):
        for f in files:
            full = os.path.join(root, f)
            z.write(full, os.path.relpath(full, src))
PY

out="$tmp/out"
EFA_BACKUPS="$fromdir" EFA_OUTDIR="$out" "$repo/import-local.sh"

for f in boats persons destinations logbooks; do
  [[ -s "$out/$f.json" ]]    || { echo "FAIL: $f.json missing/empty" >&2; exit 1; }
  [[ -s "$out/$f.json.gz" ]] || { echo "FAIL: $f.json.gz missing/empty" >&2; exit 1; }
done

python3 - "$out" <<'PY'
import json, sys, pathlib
out = pathlib.Path(sys.argv[1])
boats = json.loads((out/"boats.json").read_text())
persons = json.loads((out/"persons.json").read_text())
dests = json.loads((out/"destinations.json").read_text())
logs = json.loads((out/"logbooks.json").read_text())
assert len(boats) == 1, boats
assert len(persons) == 1, persons
assert len(dests) == 1, dests
assert len(logs) == 1, logs
e = logs[0]
assert e["boat"] == "11111111-1111-1111-1111-111111111111-v1", e
assert e["crew"] == ["22222222-2222-2222-2222-222222222222"], e
assert e["dest"] == "33333333-3333-3333-3333-333333333333", e
assert e["dist"] == 10, e
print("OK: import-local.sh produced valid JSON")
PY
