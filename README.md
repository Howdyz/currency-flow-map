# Currency Flow Map

An interactive map of where America's money moved: the adjusted gross income
that households carried with them when they moved between states and counties,
from the [IRS SOI migration data](https://www.irs.gov/statistics/soi-tax-stats-migration-data),
plus each county's biggest industry from the Census Bureau's
[County Business Patterns](https://www.census.gov/programs-surveys/cbp.html).

- Color states by net flow, money in, money out, net gain per household that
  stayed, or who's moving (newcomers' income per person minus leavers')
- Year slider and ▶ play through every IRS year from 2011–12 to 2022–23, on
  a color scale held fixed across years
- Click a state to see its biggest routes out (orange) and in (green), then
  click one of its counties for that county's own routes and #1 industry
  (county detail covers 2020–21 to 2022–23)
- **#1 industry** color style: every county by the sector with the most
  private-sector jobs (Census County Business Patterns)
- **Table** ranks every state, route, and the selected state's counties
- **Share** copies a link that reopens the exact view, e.g.
  `#county=48201&color=ind` or `#state=FL&year=1920`
- Drag to pan, scroll or pinch to zoom, space bar blinks the heat layer

## Layout

Everything the site serves is static, under `public/`:

- `index.html` — the page (D3 and TopoJSON load from cdnjs)
- `data/us-topo.json` — state and county shapes, already projected (Albers USA)
- `data/years.json` — which years exist at each level
- `data/states-YYZZ.json` — one IRS year (`2223` = 2022→2023 filings):
  - `tot`: `[state FIPS, income in $M, income out $M, people in, people out]`
  - `flows`: `[from FIPS, to FIPS, people, income $M]`, each state's six
    biggest routes in and out
  - `stay`: tax households that didn't move, per state FIPS
- `data/counties/YYZZ/SS.json` — one state's counties for one year:
  - `c`: `[county FIPS, income in $K, income out $K, people in, people out, households that stayed]`
    (in and out include moves within the state)
  - `r`: `[from FIPS, to FIPS, people, income $K]`, each county's eight
    biggest routes in and out
  - `n`: county names by FIPS
- `data/industry.json` — per county `[private-sector jobs, sector, jobs, sector, jobs, sector, jobs]`
  for its three biggest sectors

The county shapes predate two boundary changes: Alaska's Chugach and Copper
River are folded back into Valdez-Cordova, and Connecticut (which reports by
planning region since 2022) gets approximate points for its nine regions.

## Updating the data

The **Update data** GitHub workflow runs on the 3rd of every month (or by hand
from the Actions tab). It downloads the IRS and Census files with
`scripts/fetch_sources.sh`, rebuilds `public/data` with
`scripts/build_data.py`, and commits only if something changed, so a new IRS
year or Census release shows up on the site within a month of publication.
It also keeps the raw files, gzipped, on the `irs-raw` branch. To rebuild
locally from those:

```bash
git fetch origin irs-raw:refs/remotes/origin/irs-raw
mkdir -p raw && git archive origin/irs-raw | tar -x -C raw
python3 scripts/build_data.py raw
```

Or download fresh with `scripts/fetch_sources.sh raw` first.

## Running locally

```bash
cd public
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Hosting

Deployed as a Render static site: no build step, publish directory `public`.
Every push to `main` redeploys.
