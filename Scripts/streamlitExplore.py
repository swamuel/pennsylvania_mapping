"""PA Congressional races: map, candidates, and precinct vote shares.

Run:  streamlit run district_map_app.py
Reads the dev DuckDB read-only; close dbt/DBeaver/loaders first if it
complains about a lock.
"""
import json

import duckdb
import math
import pydeck as pdk
import streamlit as st

DB_PATH = r"D:\ProjectWork\SpatialDataRepository\db\dev\spatial_store.duckdb"
RESULTS = "stg_pa__congressional_district_results"
RETURNS = "stg_pa__election_returns"

st.set_page_config(page_title="PA Congressional Races", layout="wide")
st.title("PA Congressional races")

with st.expander("How to read this app", expanded=False):
    st.markdown("""
**What is a race?**
One U.S. House district in one election year. Pick a year with the slider and a
district from the dropdown, and everything below the map switches to that race.

**Where the data comes from**
- *Votes:* PA Department of State precinct-level election returns (general
  elections in presidential years, 1992-2024).
- *Boundaries:* the congressional-district-boundaries project (Jeffrey B. Lewis
  and collaborators), one shapefile per Congress, filtered to Pennsylvania.
- Each election uses the district map that was in force for it. An election in
  year Y chooses the Congress that starts the next January, so 1996 uses the
  105th Congress map and 2024 uses the 119th. The 1992 election uses the same
  map as the 104th, which was already in place.

**The map**
- *Winner (party):* blue = Democratic winner, red = Republican winner,
  gray = anyone else, or a candidate listed under both parties.
- *Democratic / Republican / Independent share:* each district is shaded light to
  dark by that group's share of the vote. The scale runs from the lowest to the
  highest district in the selected year, so compare shading within a year, not
  between years.
- *Blended:* one color per district, mixing blue (Democratic), red (Republican)
  and green (other) in proportion to their vote shares. A near-even race looks
  purple. The "Exaggerate differences" slider pushes close races apart.
- The selected district has a yellow outline. Hover over any district to see
  its winner and the Democratic / Republican / other split.

**Candidates table**
Every candidate in the selected race, their party code, votes, and share of all
votes cast in that race. Shares include write-ins, so they can differ slightly
from the state's certified percentages. "Party" is the code from the state
file; a candidate listed under two parties shows both (for example DEM/REP).

**Where the votes came from**
- *Precinct:* the smallest unit the state reports. Each row is one precinct
  (county, municipality, and precinct code).
- *Share:* that precinct's portion of the district's total vote. All shares in a
  race add up to 100%.
- *Leader:* the candidate with the most votes in that precinct.
- The chart shows the largest precincts by share. The table lists all of them
  and can be filtered by county.

**Things to keep in mind**
- Only presidential-year general elections are loaded, so midterms and special
  elections are not shown.
- "Other" includes minor parties, independents, write-ins, and candidates on
  both party lines. Shares for Democratic and Republican only count candidates
  listed under that party alone.
- Precincts are not drawn on the map, because the data has precinct codes but
  not precinct boundaries. Precinct codes can also change between elections,
  so the same code in two years may not be the same place.
- District boundaries are simplified so the map loads quickly, so edges are
  approximate.
""")

@st.cache_resource
def get_con():
    con = duckdb.connect(DB_PATH, read_only=True)
    con.execute("LOAD spatial")
    return con


@st.cache_data
def get_years():
    rows = get_con().execute(
        f"SELECT DISTINCT election_year FROM {RESULTS} ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


@st.cache_data
def get_districts(year: int):
    """One row per district: winner, party shares, simplified GeoJSON."""
    return get_con().execute(f"""
        SELECT district,
               max_by(candidate_first_name || ' ' || candidate_last_name, votes) AS winner,
               max_by(parties, votes)                                           AS winner_parties,
               round(100.0 * max(votes) / sum(votes), 1)                        AS win_pct,
               round(100.0 * sum(CASE WHEN parties ILIKE '%DEM%'
                                       AND parties NOT ILIKE '%REP%'
                                      THEN votes ELSE 0 END) / sum(votes), 1)   AS dem_pct,
               round(100.0 * sum(CASE WHEN parties ILIKE '%REP%'
                                       AND parties NOT ILIKE '%DEM%'
                                      THEN votes ELSE 0 END) / sum(votes), 1)   AS rep_pct,
               round(100.0 * sum(CASE WHEN (parties ILIKE '%DEM%') = (parties ILIKE '%REP%')
                                      THEN votes ELSE 0 END) / sum(votes), 1)   AS other_pct,
               ST_AsGeoJSON(ST_Simplify(any_value(geom), 0.001))                AS gj
        FROM {RESULTS}
        WHERE election_year = ?
        GROUP BY district
        ORDER BY district
    """, [year]).fetchall()


@st.cache_data
def get_candidates(year: int, district: int):
    """Every candidate in one race, with vote share (no geometry needed)."""
    return get_con().execute(f"""
        SELECT candidate_first_name || ' ' || candidate_last_name AS candidate,
               parties                                            AS party,
               votes,
               round(100.0 * votes / sum(votes) OVER (), 2)       AS pct
        FROM {RESULTS}
        WHERE election_year = ? AND district = ?
        ORDER BY votes DESC
    """, [year, district]).df()


@st.cache_data
def get_precincts(year: int, district: int):
    """Each precinct's share of the district's total congressional vote."""
    return get_con().execute(f"""
        WITH by_precinct AS (
            SELECT county_name,
                   municipality_name,
                   precinct_code,
                   sum(vote_total) AS votes,
                   arg_max(candidate_last_name, vote_total) AS precinct_leader
            FROM {RETURNS}
            WHERE candidate_office_code = 'USC'
              AND election_year = ?
              AND us_congressional_district = ?
            GROUP BY county_name, municipality_name, precinct_code
        )
        SELECT county_name                                   AS county,
               municipality_name                             AS municipality,
               precinct_code                                 AS precinct,
               votes,
               round(100.0 * votes / sum(votes) OVER (), 3)  AS pct_of_district,
               precinct_leader                               AS leader
        FROM by_precinct
        ORDER BY votes DESC
    """, [year, district]).df()


# ---- colors -----------------------------------------------------------
# (light end, dark end) of each party's ramp
RAMPS = {
    "Democratic share": ((222, 235, 247), (8, 81, 156)),
    "Republican share": ((254, 224, 210), (165, 15, 21)),
    "Independent / other share": ((229, 245, 224), (0, 109, 44)),
}
METRIC_INDEX = {   # position in each district row
    "Democratic share": 5,
    "Republican share": 6,
    "Independent / other share": 7,
}


def winner_color(parties: str, alpha: int):
    p = (parties or "").upper()
    if "DEM" in p and "REP" not in p:
        return [40, 90, 200, alpha]
    if "REP" in p and "DEM" not in p:
        return [210, 50, 50, alpha]
    return [130, 130, 130, alpha]


def ramp_color(value, vmin, vmax, light, dark, alpha):
    t = 0.0 if vmax == vmin else (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    return [int(light[i] + (dark[i] - light[i]) * t) for i in range(3)] + [alpha]
BLEND = {"dem": (30, 80, 210), "rep": (210, 40, 40), "other": (40, 160, 70)}


def blend_color(dem, rep, other, contrast, alpha):
    """Mix the party colors, weighted by vote share (contrast > 1 exaggerates)."""
    w = {"dem": max(dem, 0) ** contrast,
         "rep": max(rep, 0) ** contrast,
         "other": max(other, 0) ** contrast}
    total = sum(w.values()) or 1.0
    return [int(sum(BLEND[k][i] * w[k] for k in w) / total) for i in range(3)] + [alpha]

PREC_IDX = {"Democratic share": 4, "Republican share": 5, "Independent / other share": 6}


@st.cache_data
def get_precinct_map(year: int, district: int):
    """Precincts in one race: vote shares, leader, simplified geometry."""
    return get_con().execute("""
        WITH r AS (
            SELECT geoid,
                   sum(vote_total) AS votes,
                   round(100.0 * sum(CASE WHEN coalesce(candidate_party_code, '') ILIKE '%DEM%'
                                           AND coalesce(candidate_party_code, '') NOT ILIKE '%REP%'
                                          THEN vote_total ELSE 0 END)
                         / nullif(sum(vote_total), 0), 1) AS dem_pct,
                   round(100.0 * sum(CASE WHEN coalesce(candidate_party_code, '') ILIKE '%REP%'
                                           AND coalesce(candidate_party_code, '') NOT ILIKE '%DEM%'
                                          THEN vote_total ELSE 0 END)
                         / nullif(sum(vote_total), 0), 1) AS rep_pct,
                   round(100.0 * sum(CASE WHEN (coalesce(candidate_party_code, '') ILIKE '%DEM%')
                                              = (coalesce(candidate_party_code, '') ILIKE '%REP%')
                                          THEN vote_total ELSE 0 END)
                         / nullif(sum(vote_total), 0), 1) AS other_pct,
                   max_by(candidate_last_name, vote_total) AS leader,
                   max_by(candidate_party_code, vote_total) AS leader_party
            FROM stg_pa__precinct_results
            WHERE candidate_office_code = 'USC'
              AND election_year = ?
              AND us_congressional_district = ?
              AND geoid IS NOT NULL
            GROUP BY geoid
        )
        SELECT r.geoid, p.name, p.county_name, r.votes,
               r.dem_pct, r.rep_pct, r.other_pct, r.leader, r.leader_party,
               ST_AsGeoJSON(ST_Simplify(p.geom, 0.0003)) AS gj,
               ST_X(ST_Centroid(p.geom)) AS lon,
               ST_Y(ST_Centroid(p.geom)) AS lat
        FROM r
        JOIN stg_pa__precincts_geom p ON p.geoid = r.geoid
    """, [year, district]).fetchall()


@st.cache_data
def get_precinct_coverage(year: int, district: int):
    """(total votes, votes that map to a 2021 precinct) for one race."""
    return get_con().execute("""
        SELECT sum(vote_total),
               sum(vote_total) FILTER (WHERE geoid IS NOT NULL)
        FROM stg_pa__precinct_results
        WHERE candidate_office_code = 'USC'
          AND election_year = ? AND us_congressional_district = ?
    """, [year, district]).fetchone()


def render_precinct_map(year, district, shade_by, blended_label, contrast):
    st.subheader(f"Precinct map: {year}, District {district}")
    rows = get_precinct_map(year, district)
    total_v, mapped_v = get_precinct_coverage(year, district)

    if not rows or not total_v:
        st.info("No precincts in this race could be mapped to a 2021 precinct boundary.")
        return

    pct = 100.0 * (mapped_v or 0) / total_v
    note = "" if year >= 2020 else (" Older elections are drawn on 2021 precinct "
                                    "boundaries, so shapes are approximate.")
    st.caption(f"{pct:.1f}% of this race's votes map to a 2021 precinct; the rest "
               f"are not drawn.{note}")

    if shade_by in PREC_IDX:
        vals = [float(r[PREC_IDX[shade_by]] or 0) for r in rows]
        lo, hi = min(vals), max(vals)

    features = []
    for r in rows:
        (geoid, name, county, votes, dem, rep, other, leader, leader_party,
         gj, lon, lat) = r
        dem, rep, other = float(dem or 0), float(rep or 0), float(other or 0)
        if shade_by == "Winner (party)":
            color = winner_color(leader_party, 200)
        elif shade_by == blended_label:
            color = blend_color(dem, rep, other, contrast, 200)
        else:
            light, dark = RAMPS[shade_by]
            color = ramp_color(float(r[PREC_IDX[shade_by]] or 0), lo, hi, light, dark, 200)
        features.append({
            "type": "Feature",
            "geometry": json.loads(gj),
            "properties": {
                "name": name, "county": county, "votes": int(votes),
                "dem": dem, "rep": rep, "other": other, "leader": leader,
                "color": color,
            },
        })

    lons = [r[10] for r in rows]
    lats = [r[11] for r in rows]
    span = max(max(lons) - min(lons), max(lats) - min(lats), 0.01)
    zoom = max(5.0, min(12.0, math.log2(562 / (1.3 * span))))
    view = pdk.ViewState(latitude=sum(lats) / len(lats),
                         longitude=sum(lons) / len(lons), zoom=zoom)

    layer = pdk.Layer(
        "GeoJsonLayer",
        {"type": "FeatureCollection", "features": features},
        pickable=True, stroked=True, filled=True,
        get_fill_color="properties.color",
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
    )
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view, map_style="light",
        tooltip={"html": "<b>{name}</b> ({county})<br/>{votes} votes - led by {leader}<br/>"
                         "D {dem}% / R {rep}% / other {other}%"},
    ))

# ---- sidebar: pick a race ---------------------------------------------
years = get_years()
year = st.sidebar.select_slider("Election year", options=years, value=years[-1])

districts_data = get_districts(year)
district = st.sidebar.selectbox("District (race)", [int(r[0]) for r in districts_data])

BLENDED = "Blended (weighted by vote share)"

shade_by = st.sidebar.radio(
    "Shade by",
    ["Winner (party)", BLENDED] + list(RAMPS.keys()),
)

contrast = 1.0
if shade_by == BLENDED:
    contrast = st.sidebar.slider("Exaggerate differences", 1.0, 4.0, 1.0, 0.5)
    st.sidebar.caption("Blue = Democratic, red = Republican, green = other. "
                       "Mixed districts blend toward purple.")
elif shade_by in RAMPS:
    idx = METRIC_INDEX[shade_by]
    values = [float(r[idx]) for r in districts_data]
    vmin, vmax = min(values), max(values)
    st.sidebar.caption(f"{shade_by}: {vmin:.1f}% (light) to {vmax:.1f}% (dark), "
                       f"scaled to the districts in {year}.")
# ---- map --------------------------------------------------------------
features = []
for r in districts_data:
    d, winner, win_parties, win_pct, dem, rep, other, gj = r
    d = int(d)
    selected = d == district
    alpha = 235 if selected else 190
    if shade_by == "Winner (party)":
        color = winner_color(win_parties, alpha)
    elif shade_by == BLENDED:
        color = blend_color(float(dem), float(rep), float(other), contrast, alpha)
    else:
        light, dark = RAMPS[shade_by]
        color = ramp_color(float(r[METRIC_INDEX[shade_by]]), vmin, vmax, light, dark, alpha)
    features.append({
        "type": "Feature",
        "geometry": json.loads(gj),
        "properties": {
            "district": d,
            "winner": winner,
            "parties": win_parties,
            "win_pct": float(win_pct),
            "dem": float(dem),
            "rep": float(rep),
            "other": float(other),
            "color": color,
            "line": [255, 255, 0] if selected else [255, 255, 255],
            "width": 800 if selected else 50,
        },
    })

layer = pdk.Layer(
    "GeoJsonLayer",
    {"type": "FeatureCollection", "features": features},
    pickable=True,
    stroked=True,
    filled=True,
    get_fill_color="properties.color",
    get_line_color="properties.line",
    get_line_width="properties.width",
    line_width_min_pixels=1,
    line_width_max_pixels=4,
)

view = pdk.ViewState(latitude=41.0, longitude=-77.6, zoom=6.2)
st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    map_style="light",
    tooltip={"html": "<b>District {district}</b><br/>"
                     "{winner} ({parties}) - {win_pct}%<br/>"
                     "D {dem}% / R {rep}% / other {other}%"},
))
st.caption("The selected district is outlined in yellow. In 'Winner' mode: "
           "blue = Democratic, red = Republican, gray = other or cross-filed.")

render_precinct_map(year, district, shade_by, BLENDED, contrast)

# ---- the race: every candidate ----------------------------------------
st.header(f"{year} - District {district}")
cands = get_candidates(year, district)

left, right = st.columns([3, 2])
with left:
    st.subheader("Candidates")
    st.dataframe(
        cands,
        use_container_width=True,
        hide_index=True,
        column_config={
            "votes": st.column_config.NumberColumn("Votes", format="%d"),
            "pct": st.column_config.NumberColumn("Share", format="%.2f%%"),
        },
    )
with right:
    st.subheader("Vote share")
    st.bar_chart(cands.set_index("candidate")["pct"])

# ---- precincts --------------------------------------------------------
st.subheader("Where the votes came from")
prec = get_precincts(year, district)
st.caption(f"{len(prec):,} precincts. 'Share' is each precinct's portion of the "
           "district's total vote. 'Leader' is the candidate with the most "
           "votes in that precinct.")

top_n = st.slider("Show top precincts in chart", 5, 50, 20)
chart = prec.head(top_n).copy()
chart["label"] = (chart["county"].fillna("?") + " - "
                  + chart["municipality"].fillna("?") + " "
                  + chart["precinct"].astype(str))
st.bar_chart(chart.set_index("label")["pct_of_district"])

counties = sorted(prec["county"].dropna().unique())
picked = st.multiselect("Filter table by county", counties)
table = prec[prec["county"].isin(picked)] if picked else prec
st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "votes": st.column_config.NumberColumn("Votes", format="%d"),
        "pct_of_district": st.column_config.NumberColumn("Share", format="%.3f%%"),
    },
)