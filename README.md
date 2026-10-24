# Currency Flow Map

An interactive map of where America's money moved: the adjusted gross income
that households carried with them when they moved between states, from the
[IRS SOI migration data, 2022–2023](https://www.irs.gov/statistics/soi-tax-stats-migration-data-2022-2023).

- Color states by net flow, money in, money out, or net gain per household that stayed
- Click a state to see its biggest routes out (orange) and in (green)
- Drag to pan, scroll or pinch to zoom, space bar blinks the heat layer

## Layout

The whole site is one self-contained page, `public/index.html`. The state and
county shapes and the migration figures are embedded in it; D3 and
TopoJSON load from cdnjs.

## Running locally

```bash
cd public
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Hosting

Deployed as a Render static site: no build step, publish directory `public`.
Every push to `main` redeploys.
