#!/usr/bin/env bash
# Download the raw source files into a directory (default: raw/), gzipped,
# for scripts/build_data.py:
#   - IRS SOI state-to-state migration, every year from 2011-12 on
#   - IRS SOI county-to-county migration, 2020-21 on
#   - Census County Business Patterns, the newest year, 2-digit sectors only
set -u
out=${1:-raw}
mkdir -p "$out" && cd "$out"
ua="currency-flow-map data update (https://github.com/Howdyz/currency-flow-map)"
get() { curl -fsSL --retry 3 -A "$ua" -o "$1" "$2" && echo "ok $1" || { rm -f "$1"; echo "missing $1"; return 1; }; }

now=$(date -u +%y)
for ((y = 11; y <= now; y++)); do
  yy=$(printf "%02d%02d" $y $((y + 1)))
  get stateinflow$yy.csv https://www.irs.gov/pub/irs-soi/stateinflow$yy.csv
  get stateoutflow$yy.csv https://www.irs.gov/pub/irs-soi/stateoutflow$yy.csv
  if ((y >= 20)); then
    get countyinflow$yy.csv https://www.irs.gov/pub/irs-soi/countyinflow$yy.csv
    get countyoutflow$yy.csv https://www.irs.gov/pub/irs-soi/countyoutflow$yy.csv
  fi
done

for ((y = now; y >= now - 4; y--)); do
  yy=$(printf "%02d" $y)
  if get cbp.zip https://www2.census.gov/programs-surveys/cbp/datasets/20$yy/cbp${yy}co.zip; then
    unzip -o -q cbp.zip && rm cbp.zip
    { head -1 cbp${yy}co.txt; grep -E '^[^,]*,[^,]*,"?([0-9]{2}----|------)"?,' cbp${yy}co.txt; } > cbp${yy}co.csv
    rm cbp${yy}co.txt
    break
  fi
done

gzip -9f *.csv
ls -la
