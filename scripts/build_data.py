"""Build the site's data files from the raw IRS and Census downloads.

scripts/fetch_sources.sh downloads the raw files; the "Update data" workflow
also keeps them, gzipped, on the irs-raw branch. To rebuild from those:

    git fetch origin irs-raw:refs/remotes/origin/irs-raw
    mkdir -p raw && git archive origin/irs-raw | tar -x -C raw
    python3 scripts/build_data.py raw

Writes, under public/data/:
    states-YYZZ.json       one per IRS year (e.g. 2223 = 2022 -> 2023 filings)
    counties/YYZZ/SS.json  one per state per year with county files
    industry.json          each county's biggest industries (County Business Patterns)
    jobs.json              latest quarter's jobs and weekly wages, with yearly change (BLS QCEW)
    years.json             which years exist at each level
"""

import csv
import glob
import gzip
import io
import json
import os
import re
import sys

OUT = os.path.join(os.path.dirname(__file__), "..", "public", "data")
STATE_ROUTES = 6    # biggest routes kept per state, each direction
COUNTY_ROUTES = 8   # biggest routes kept per county, each direction

# Alaska's Valdez-Cordova split into Chugach (063) and Copper River (066) in
# 2019; the map still has the old borough, so fold them back into it.
REMAP = {2063: 2261, 2066: 2261}
RENAME = {2261: "Valdez-Cordova Census Area",
          # the IRS cuts Connecticut's planning region names short
          9110: "Capitol Planning Region", 9120: "Greater Bridgeport Planning Region",
          9130: "Lower Connecticut River Valley Planning Region", 9140: "Naugatuck Valley Planning Region",
          9150: "Northeastern Connecticut Planning Region", 9160: "Northwest Hills Planning Region",
          9170: "South Central Connecticut Planning Region", 9180: "Southeastern Connecticut Planning Region",
          9190: "Western Connecticut Planning Region"}

# County Business Patterns 2-digit sectors, with short labels for the map
SECTORS = {
    "11": "Farming, forestry & fishing", "21": "Mining, oil & gas", "22": "Utilities",
    "23": "Construction", "31": "Manufacturing", "42": "Wholesale trade", "44": "Retail",
    "48": "Transportation & warehousing", "51": "Information", "52": "Finance & insurance",
    "53": "Real estate", "54": "Professional services", "55": "Company management",
    "56": "Admin & support services", "61": "Education", "62": "Health care & social assistance",
    "71": "Arts & recreation", "72": "Hotels & restaurants", "81": "Other services",
    "99": "Unclassified",
}


def read_csv(path):
    raw = gzip.open(path).read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    rows = list(csv.DictReader(io.StringIO(text)))
    # column names vary in case between years (AGI vs agi)
    return [{k.strip().lower(): (v or "").strip() for k, v in r.items()} for r in rows]


def num(v):
    return int(float(v)) if v not in ("", "d", "D") else -1


def year_of(path, prefix):
    return re.match(prefix + r"(\d{4})\.csv\.gz$", os.path.basename(path)).group(1)


def build_states(raw, year):
    inflow = read_csv(os.path.join(raw, f"stateinflow{year}.csv.gz"))
    outflow = read_csv(os.path.join(raw, f"stateoutflow{year}.csv.gz"))
    tot, stay, ins, outs = {}, {}, {}, {}
    for r in inflow:
        d, o = num(r["y2_statefips"]), num(r["y1_statefips"])
        n1, n2, agi = num(r["n1"]), num(r["n2"]), num(r["agi"])
        if o == 97 and "same state" not in r["y1_state_name"].lower():   # 97 also tags within-state moves
            tot.setdefault(d, {})["in"] = (agi, n2)
        elif o == d:
            stay[d] = n1
        elif o <= 56 and n2 >= 0:
            ins.setdefault(d, []).append((o, d, n2, agi))
    for r in outflow:
        o, d = num(r["y1_statefips"]), num(r["y2_statefips"])
        n2, agi = num(r["n2"]), num(r["agi"])
        if d == 97 and "same state" not in r["y2_state_name"].lower():
            tot.setdefault(o, {})["out"] = (agi, n2)
        elif d <= 56 and d != o and n2 >= 0:
            outs.setdefault(o, []).append((o, d, n2, agi))
    flows = {}
    for group in (outs, ins):
        for routes in group.values():
            for o, d, n2, agi in sorted(routes, key=lambda x: -x[3])[:STATE_ROUTES]:
                flows[(o, d)] = [o, d, n2, round(agi / 1000)]
    states = sorted(s for s in tot if s <= 56)
    return {
        "tot": [[s, round(tot[s]["in"][0] / 1000), round(tot[s]["out"][0] / 1000), tot[s]["in"][1], tot[s]["out"][1]] for s in states],
        "flows": [flows[k] for k in sorted(flows)],
        "stay": {str(s): stay[s] for s in states},
    }


def county(state, cty):
    code = num(state) * 1000 + num(cty)
    return REMAP.get(code, code)


def clean_name(name):
    return re.sub(r"\s+(Non-migrants|Total Migration.*)$", "", name)


def build_counties(raw, year):
    inflow = read_csv(os.path.join(raw, f"countyinflow{year}.csv.gz"))
    outflow = read_csv(os.path.join(raw, f"countyoutflow{year}.csv.gz"))
    tot, names, ins, outs = {}, {}, {}, {}

    def add(table, key, i, vals):
        row = table.setdefault(key, [0, 0, 0, 0, 0])
        for j, v in zip(i, vals):
            row[j] += max(v, 0)

    def route(group, owner, o, d, n2, agi):
        if o == d:   # Alaska's folded boroughs moving between each other
            return
        r = group.setdefault(owner, {}).setdefault((o, d), [0, 0])
        r[0] += n2
        r[1] += agi

    for r in inflow:
        d = county(r["y2_statefips"], r["y2_countyfips"])
        so, co = num(r["y1_statefips"]), num(r["y1_countyfips"])
        n1, n2, agi = num(r["n1"]), num(r["n2"]), num(r["agi"])
        if so == 97 and co == 0:
            add(tot, d, (0, 2), (agi, n2))          # income in, people in
        elif so <= 56:
            o = county(r["y1_statefips"], r["y1_countyfips"])
            if num(r["y2_statefips"]) * 1000 + num(r["y2_countyfips"]) == so * 1000 + co:
                add(tot, d, (4,), (n1,))            # households that didn't move
                names.setdefault(d, clean_name(r["y1_countyname"]))
            elif n2 >= 0:
                route(ins, d, o, d, n2, agi)
                names.setdefault(o, r["y1_countyname"])
    for r in outflow:
        o = county(r["y1_statefips"], r["y1_countyfips"])
        sd, cd = num(r["y2_statefips"]), num(r["y2_countyfips"])
        n2, agi = num(r["n2"]), num(r["agi"])
        if sd == 97 and cd == 0:
            add(tot, o, (1, 3), (agi, n2))          # income out, people out
        elif sd <= 56 and n2 >= 0:
            d = county(r["y2_statefips"], r["y2_countyfips"])
            if num(r["y1_statefips"]) * 1000 + num(r["y1_countyfips"]) != sd * 1000 + cd:
                route(outs, o, o, d, n2, agi)
                names.setdefault(d, r["y2_countyname"])

    by_state = {}
    for c in tot:
        by_state.setdefault(c // 1000, []).append(c)
    files = {}
    for s, counties in by_state.items():
        keep = {}
        for c in counties:
            for group in (outs, ins):
                top = sorted(group.get(c, {}).items(), key=lambda kv: -kv[1][1])[:COUNTY_ROUTES]
                for (o, d), (n2, agi) in top:
                    keep[(o, d)] = [o, d, n2, agi]
        used = set(counties) | {x for k in keep for x in k}
        files[s] = {
            # [county FIPS, income in $K, income out $K, people in, people out, households that stayed]
            "c": [[c] + tot[c] for c in sorted(counties)],
            # [from FIPS, to FIPS, people, income $K]
            "r": [keep[k] for k in sorted(keep)],
            "n": {str(c): RENAME.get(c, names.get(c)) for c in sorted(used) if c in names or c in RENAME},
        }
    return files


def build_industry(raw):
    paths = sorted(glob.glob(os.path.join(raw, "cbp*co.csv.gz")))
    if not paths:
        return None
    path = paths[-1]
    year = 2000 + int(re.search(r"cbp(\d\d)co", path).group(1))
    emp, total = {}, {}
    for r in read_csv(path):
        c = county(r["fipstate"], r["fipscty"])
        if c % 1000 == 999:   # "statewide" establishments with no county
            continue
        n = max(num(r["emp"]), 0)
        code = r["naics"].strip('"')
        if code == "------":
            total[c] = total.get(c, 0) + n
        elif code[:2] in SECTORS:
            emp.setdefault(c, {})
            emp[c][code[:2]] = emp[c].get(code[:2], 0) + n
    out = {}
    for c, sectors in emp.items():
        top = sorted(((e, s) for s, e in sectors.items() if e > 0), reverse=True)[:3]
        if top and total.get(c):
            out[str(c)] = [total[c]] + [x for e, s in top for x in (int(s), e)]
    return {"year": year, "sectors": SECTORS, "c": out}


def build_jobs(raw):
    """Latest BLS QCEW quarter: jobs and average weekly wage, all industries and owners."""
    paths = sorted(glob.glob(os.path.join(raw, "qcew*.csv.gz")))
    if not paths:
        return None
    m = re.search(r"qcew(\d{4})q(\d)", paths[-1])
    acc = {}
    for r in read_csv(paths[-1]):
        if r["own_code"] != "0" or r["agglvl_code"] not in ("10", "50", "70") or r["disclosure_code"].upper() == "N":   # N = withheld
            continue
        area = r["area_fips"]
        if area == "US000":
            key = ("us", 0)
        elif area.endswith("000"):
            key = ("s", int(area[:2]))
        elif area[:2].isdigit() and int(area[:2]) <= 56 and not area.endswith("999"):
            key = ("c", county(area[:2], area[2:]))
        else:
            continue
        months = [num(r[f"month{i}_emplvl"]) for i in (1, 2, 3)]
        changes = [num(r[f"oty_month{i}_emplvl_chg"]) for i in (1, 2, 3)]
        acc.setdefault(key, []).append((months, changes, num(r["total_qtrly_wages"]),
                                        num(r["oty_total_qtrly_wages_chg"]), r))

    def summarize(parts):
        if len(parts) == 1:
            months, changes, _, _, r = parts[0]
            emp, chg = months[2], changes[2]
            return [emp, round(100 * chg / (emp - chg), 1), num(r["avg_wkly_wage"]),
                    float(r["oty_avg_wkly_wage_pct_chg"] or 0)]
        # Alaska's two folded boroughs: recombine from totals the way BLS computes them
        emp = sum(p[0][2] for p in parts)
        chg = sum(p[1][2] for p in parts)
        avg = sum(sum(p[0]) for p in parts) / 3
        avg_before = avg - sum(sum(p[1]) for p in parts) / 3
        wages = sum(p[2] for p in parts)
        wages_before = wages - sum(p[3] for p in parts)
        wage, wage_before = wages / avg / 13, wages_before / avg_before / 13
        return [emp, round(100 * chg / (emp - chg), 1), round(wage), round(100 * (wage / wage_before - 1), 1)]

    out = {"period": f"{m.group(1)} Q{m.group(2)}", "us": None, "s": {}, "c": {}}
    for (level, code), parts in acc.items():
        if level == "us":
            out["us"] = summarize(parts)
        else:
            out[level][str(code)] = summarize(parts)
    return out


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))


def main(raw):
    state_years = sorted(year_of(p, "stateinflow") for p in glob.glob(os.path.join(raw, "stateinflow*.csv.gz")))
    county_years = sorted(year_of(p, "countyinflow") for p in glob.glob(os.path.join(raw, "countyinflow*.csv.gz")))
    for y in state_years:
        write(os.path.join(OUT, f"states-{y}.json"), build_states(raw, y))
        print("states", y)
    for y in county_years:
        for s, data in build_counties(raw, y).items():
            write(os.path.join(OUT, "counties", y, f"{s:02d}.json"), data)
        print("counties", y)
    industry = build_industry(raw)
    if industry:
        write(os.path.join(OUT, "industry.json"), industry)
        print("industry", industry["year"], len(industry["c"]), "counties")
    jobs = build_jobs(raw)
    if jobs:
        write(os.path.join(OUT, "jobs.json"), jobs)
        print("jobs", jobs["period"], len(jobs["c"]), "counties")
    write(os.path.join(OUT, "years.json"), {"states": state_years, "counties": county_years,
                                             "industry": industry and industry["year"],
                                             "jobs": jobs and jobs["period"]})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "raw")
