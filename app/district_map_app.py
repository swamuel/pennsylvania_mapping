"""PA Congressional races: map, candidates, and precinct vote shares.

Run:  streamlit run app/district_map_app.py
Reads only the Parquet files in app/app_data (made by export_app_data.py),
so it needs no database and no spatial extension.
"""
import json
import math
from pathlib import Path

import duckdb
import pydeck as pdk
import streamlit as st

DATA = Path(__file__).parent / "app_data"
F_RESULTS = (DATA / "district_results.parquet").as_posix()
F_DSHAPES = (DATA / "district_shapes.parquet").as_posix()
F_PRESULTS = (DATA / "precinct_results.parquet").as_posix()
F_PSHAPES = (DATA / "precinct_shapes.parquet").as_posix()

st.set_page_config(page_title="PA Congressional Races", layout="wide")
st.title("PA Congressional races")

if not (DATA / "district_results.parquet").exists():
    st.error("No data found in app/app_data. Run export_app_data.py first.")
    st.stop()


@st.cache_resource
def get_con():
    return duckdb.connect()   # in-memory; queries read the Parquet files directly


@st.cache_data
def get_years():
    rows = get_con().execute(
        f"SELECT DISTINCT election_year FROM read_parquet('{F_RESULTS}') ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


@st.cache_data
def get_districts(year: int):
    """One row per district: winner, party shares, simplified GeoJSON."""
    return get_con().execute(f"""
        SELECT r.district,
               max_by(r.candidate_first_name || ' ' || r.candidate_last_name, r.votes) AS winner,
               max_by(r.parties, r.votes)                                           AS winner_parties,
               round(100.0 * max(r.votes) / sum(r.votes), 1)                        AS win_pct,
               round(100.0 * sum(CASE WHEN r.parties ILIKE '%DEM%'
                                       AND r.parties NOT ILIKE '%REP%'
                                      THEN r.votes ELSE 0 END) / sum(r.votes), 1)   AS dem_pct,
               round(100.0 * sum(CASE WHEN r.parties ILIKE '%REP%'
                                       AND r.parties NOT ILIKE '%DEM%'
                                      THEN r.votes ELSE 0 END) / sum(r.votes), 1)   AS rep_pct,
               round(100.0 * sum(CASE WHEN (r.parties ILIKE '%DEM%') = (r.parties ILIKE '%REP%')
                                      THEN r.votes ELSE 0 END) / sum(r.votes), 1)   AS other_pct,
               any_value(s.gj)                                                      AS gj
        FROM read_parquet('{F_RESULTS}') r
        JOIN read_parquet('{F_DSHAPES}') s
          ON s.election_year = r.election_year AND s.district = r.district
        WHERE r.election_year = ?
        GROUP BY r.district
        ORDER BY r.district
    """, [year]).fetchall()


@st.cache_data
def get_candidates(year: int, district: int):
    return get_con().execute(f"""
        SELECT candidate_first_name || ' ' || candidate_last_name AS candidate,
               parties                                            AS party,
               votes,
               round(100.0 * votes / sum(votes) OVER (), 2)       AS pct
        FROM read_parquet('{F_RESULTS}')
        WHERE election_year = ? AND district = ?
        ORDER BY votes DESC
    """, [year, district]).df()


@st.cache_data
def get_precincts(year: int, district: int):
    """Each precinct's share of the district's total congressional vote."""
    return get_con().execute(f"""
        WITH by_precinct AS (
            SELECT county_name, municipality_name, precinct_code,
                   sum(vote_total) AS votes,
                   arg_max(candidate_last_name, vote_total) AS precinct_leader
            FROM read_parquet('{F_PRESULTS}')
            WHERE election_year = ? AND district = ?
            GROUP BY county_name, municipality_name, precinct_code
        )
        SELECT county_name AS county, municipality_name AS municipality,
               precinct_code AS precinct, votes,
               round(100.0 * votes / sum(votes) OVER (), 3) AS pct_of_district,
               precinct_leader AS leader
        FROM by_precinct
        ORDER BY votes DESC
    """, [year, district]).df()


@st.cache_data
def get_precinct_map(year: int, district: int):
    """Precincts in one race: vote shares, leader, geometry."""
    return get_con().execute(f"""
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
            FROM read_parquet('{F_PRESULTS}')
            WHERE election_year = ? AND district = ? AND geoid IS NOT NULL
            GROUP BY geoid
        )
        SELECT r.geoid, p.name, p.county_name, r.votes,
               r.dem_pct, r.rep_pct, r.other_pct, r.leader, r.leader_party,
               p.gj, p.lon, p.lat
        FROM r JOIN read_parquet('{F_PSHAPES}') p ON p.geoid = r.geoid
    """, [year, district]).fetchall()


@st.cache_data
def get_precinct_coverage(year: int, district: int):
    return get_con().execute(f"""
        SELECT sum(vote_total), sum(vote_total) FILTER (WHERE geoid IS NOT NULL)
        FROM read_parquet('{F_PRESULTS}')
        WHERE election_year = ? AND district = ?
    """, [year, district]).fetchone()


# ---- colors -----------------------------------------------------------
RAMPS = {
    "Democratic share": ((222, 235, 247), (8, 81, 156)),
    "Republican share": ((254, 224, 210), (165, 15, 21)),
    "Independent / other share": ((229, 245, 224), (0, 109, 44)),
}
METRIC_INDEX = {"Democratic share": 5, "Republican share": 6,
                "Independent / other share": 7}
PREC_IDX = {"Democratic share": 4, "Republican share": 5,
            "Independent / other share": 6}
BLENDED = "Blended (weighted by vote share)"
PARTY_RGB = {"dem": (40, 90, 200), "rep": (210, 50, 50), "other": (130, 130, 130)}


def winner_color(parties, alpha):
    p = (parties or "").upper()
    if "DEM" in p and "REP" not in p:
        return [*PARTY_RGB["dem"], alpha]
    if "REP" in p and "DEM" not in p:
        return [*PARTY_RGB["rep"], alpha]
    return [*PARTY_RGB["other"], alpha]


def ramp_color(value, vmin, vmax, light, dark, alpha):
    t = 0.0 if vmax == vmin else (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    return [int(light[i] + (dark[i] - light[i]) * t) for i in range(3)] + [alpha]


def blend_color(dem, rep, other, contrast, alpha):
    """Mix party colors in proportion to vote share. Higher contrast makes the
    leading party count for more (share ** contrast), so close races stay muted."""
    w = {k: max(v, 0.0) ** contrast for k, v in
         (("dem", dem), ("rep", rep), ("other", other))}
    total = sum(w.values()) or 1.0
    return [int(sum(PARTY_RGB[k][i] * w[k] for k in w) / total) for i in range(3)] + [alpha]


def shade(shade_by, parties, dem, rep, other, ramp_val, lo, hi, contrast, alpha):
    if shade_by == "Winner (party)":
        return winner_color(parties, alpha)
    if shade_by == BLENDED:
        return blend_color(dem, rep, other, contrast, alpha)
    light, dark = RAMPS[shade_by]
    return ramp_color(ramp_val, lo, hi, light, dark, alpha)


# ---- sidebar ----------------------------------------------------------
years = get_years()
year = st.sidebar.select_slider("Election year", options=years, value=years[-1])
districts_data = get_districts(year)
district = st.sidebar.selectbox("District (race)", [int(r[0]) for r in districts_data])

shade_by = st.sidebar.radio(
    "Shade by", ["Winner (party)", BLENDED] + list(RAMPS.keys()),
    help="How each area is colored on the maps.")
contrast = 1.0
if shade_by == BLENDED:
    contrast = st.sidebar.slider(
        "Contrast", 1.0, 4.0, 2.0, 0.5,
        help="Higher values let the leading party dominate the color.")
lo = hi = 0.0
if shade_by in RAMPS:
    vals = [float(r[METRIC_INDEX[shade_by]]) for r in districts_data]
    lo, hi = min(vals), max(vals)
    st.sidebar.caption(f"{shade_by}: {lo:.1f}% (light) to {hi:.1f}% (dark), "
                       f"scaled to the districts in {year}.")

# ---- district map -----------------------------------------------------
features = []
for r in districts_data:
    d, winner, win_parties, win_pct, dem, rep, other, gj = r
    d = int(d)
    selected = d == district
    ramp_val = float(r[METRIC_INDEX[shade_by]]) if shade_by in RAMPS else 0.0
    color = shade(shade_by, win_parties, float(dem), float(rep), float(other),
                  ramp_val, lo, hi, contrast, 235 if selected else 190)
    features.append({
        "type": "Feature", "geometry": json.loads(gj),
        "properties": {
            "district": d, "winner": winner, "parties": win_parties,
            "win_pct": float(win_pct), "dem": float(dem), "rep": float(rep),
            "other": float(other), "color": color,
            "line": [255, 255, 0] if selected else [255, 255, 255],
            "width": 800 if selected else 50,
        },
    })

st.pydeck_chart(pdk.Deck(
    layers=[pdk.Layer(
        "GeoJsonLayer", {"type": "FeatureCollection", "features": features},
        pickable=True, stroked=True, filled=True,
        get_fill_color="properties.color", get_line_color="properties.line",
        get_line_width="properties.width",
        line_width_min_pixels=1, line_width_max_pixels=4)],
    initial_view_state=pdk.ViewState(latitude=41.0, longitude=-77.6, zoom=6.2),
    map_style="light",
    tooltip={"html": "<b>District {district}</b><br/>"
                     "{winner} ({parties}) - {win_pct}%<br/>"
                     "D {dem}% / R {rep}% / other {other}%"},
))
st.caption("The selected district is outlined in yellow. Blue = Democratic, "
           "red = Republican, gray = other or cross-filed.")


# ---- precinct map -----------------------------------------------------
def render_precinct_map(year, district):
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
        v = [float(r[PREC_IDX[shade_by]] or 0) for r in rows]
        plo, phi = min(v), max(v)
    else:
        plo = phi = 0.0

    feats = []
    for r in rows:
        geoid, name, county, votes, dem, rep, other, leader, leader_party, gj, lon, lat = r
        dem, rep, other = float(dem or 0), float(rep or 0), float(other or 0)
        rv = float(r[PREC_IDX[shade_by]] or 0) if shade_by in PREC_IDX else 0.0
        feats.append({
            "type": "Feature", "geometry": json.loads(gj),
            "properties": {"name": name, "county": county, "votes": int(votes),
                           "dem": dem, "rep": rep, "other": other, "leader": leader,
                           "color": shade(shade_by, leader_party, dem, rep, other,
                                          rv, plo, phi, contrast, 200)},
        })
    lons, lats = [r[10] for r in rows], [r[11] for r in rows]
    span = max(max(lons) - min(lons), max(lats) - min(lats), 0.01)
    zoom = max(5.0, min(12.0, math.log2(562 / (1.3 * span))))
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": feats},
                          pickable=True, stroked=True, filled=True,
                          get_fill_color="properties.color",
                          get_line_color=[255, 255, 255], line_width_min_pixels=1)],
        initial_view_state=pdk.ViewState(latitude=sum(lats) / len(lats),
                                         longitude=sum(lons) / len(lons), zoom=zoom),
        map_style="light",
        tooltip={"html": "<b>{name}</b> ({county})<br/>{votes} votes - led by {leader}<br/>"
                         "D {dem}% / R {rep}% / other {other}%"},
    ))


# ---- the race ---------------------------------------------------------
st.header(f"{year} - District {district}")
cands = get_candidates(year, district)
left, right = st.columns([3, 2])
with left:
    st.subheader("Candidates")
    st.dataframe(cands, width="stretch", hide_index=True, column_config={
        "votes": st.column_config.NumberColumn("Votes", format="%d"),
        "pct": st.column_config.NumberColumn("Share", format="%.2f%%")})
with right:
    st.subheader("Vote share")
    st.bar_chart(cands.set_index("candidate")["pct"])

render_precinct_map(year, district)

st.subheader("Where the votes came from")
prec = get_precincts(year, district)
st.caption(f"{len(prec):,} precincts. 'Share' is each precinct's portion of the "
           "district's total vote. 'Leader' is the candidate with the most votes there.")
top_n = st.slider("Show top precincts in chart", 5, 50, 20)
chart = prec.head(top_n).copy()
chart["label"] = (chart["county"].fillna("?") + " - " + chart["municipality"].fillna("?")
                  + " " + chart["precinct"].astype(str))
st.bar_chart(chart.set_index("label")["pct_of_district"])
picked = st.multiselect("Filter table by county", sorted(prec["county"].dropna().unique()))
table = prec[prec["county"].isin(picked)] if picked else prec
st.dataframe(table, width="stretch", hide_index=True, column_config={
    "votes": st.column_config.NumberColumn("Votes", format="%d"),
    "pct_of_district": st.column_config.NumberColumn("Share", format="%.3f%%")})

with st.expander("How to read this app / data sources"):
    st.markdown("""
**Shading.** *Winner* colors by the winning candidate's party. *Blended* mixes
blue, red and gray in proportion to each side's vote share. The party ramps
shade by one party's share, scaled to the districts shown.

**Cross-filed candidates** (listed on both party ballots, e.g. DEM/REP) count as
"other" in the shares.

**Precinct map.** Election returns are matched to 2021 precinct boundaries by
code first, then by a unique-name fallback. Older elections use today's
boundaries, so shapes are approximate, and unmatched precincts are not drawn.

**Sources.** Election returns: Pennsylvania Department of State bulk results.
Congressional boundaries: Jeffrey B. Lewis, Brandon DeVine, Lincoln Pitcher, and
Kenneth C. Martis (2013), *Digital Boundary Definitions of United States
Congressional Districts, 1789-2012*, https://cdmaps.polisci.ucla.edu (MIT license).
Precinct boundaries: PA Legislative Reapportionment Commission, 2021 data release.
Work in progress; not an official source.
""")
