# Currency Flow Map

An interactive map of where America's money moved: the adjusted gross income
that households carried with them when they moved between states, from the
[IRS SOI migration data, 2022–2023](https://www.irs.gov/statistics/soi-tax-stats-migration-data-2022-2023).

- Color states by net flow, money in, money out, net gain per household that
  stayed, or who's moving (newcomers' income per person minus leavers')
- Click a state to see its biggest routes out (orange) and in (green)
- **Table** ranks every state and route; click a column to sort
- **Share** copies a link that reopens the exact view (state, color style,
  layers), e.g. `#state=FL&color=gap`
- Drag to pan, scroll or pinch to zoom, space bar blinks the heat layer

## Layout

Everything is static, under `public/`:

- `index.html` — the page (D3 and TopoJSON load from cdnjs)
- `data/us-topo.json` — state and county shapes, already projected (Albers USA)
- `data/states-2223.json` — one year of state-to-state figures:
  - `tot`: `[state FIPS, income in $M, income out $M, people in, people out]`
  - `flows`: `[from FIPS, to FIPS, people, income $M]`, each state's six
    biggest routes in and out
  - `stay`: tax households that didn't move, per state FIPS

## Running locally

```bash
cd public
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Hosting

Deployed as a Render static site: no build step, publish directory `public`.
Every push to `main` redeploys.
