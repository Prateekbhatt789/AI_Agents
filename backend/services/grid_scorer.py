import os
import math

DB_SCHEMA = os.getenv("DB_SCHEMA", "data")

# ─────────────────────────────────────────────────────────────────
# FACILITY RULES
# ─────────────────────────────────────────────────────────────────
FACILITY_RULES = {
    "hospitals": {
        "poi_table":   "health_care",
        "needs":       ["transport", "finance"],
        "avoid":       [],
        "min_pop":     30,
        "min_dist_km": 2.0,
        "weight":      1.5,
    },
    "schools": {
        "poi_table":   "education",
        "needs":       ["transport", "recreation"],
        "avoid":       ["infra_str"],
        "min_pop":     50,
        "min_dist_km": 1.0,
        "weight":      1.3,
    },
    "restaurants": {
        "poi_table":   "food",
        "needs":       ["transport", "business"],
        "avoid":       [],
        "min_pop":     20,
        "min_dist_km": 0.3,
        "weight":      1.0,
    },
    "businesses": {
        "poi_table":   "business",
        "needs":       ["transport", "finance"],
        "avoid":       [],
        "min_pop":     100,
        "min_dist_km": 0.5,
        "weight":      1.2,
    },
    "finance": {
        "poi_table":   "finance",
        "needs":       ["business", "transport"],
        "avoid":       [],
        "min_pop":     150,
        "min_dist_km": 0.5,
        "weight":      1.1,
    },
    "recreation": {
        "poi_table":   "recreation",
        "needs":       ["transport"],
        "avoid":       [],
        "min_pop":     500,
        "min_dist_km": 1.0,
        "weight":      1.0,
    },
    "shops": {
        "poi_table":   "shops",
        "needs":       ["transport", "business"],
        "avoid":       [],
        "min_pop":     100,
        "min_dist_km": 0.4,
        "weight":      1.0,
    },
    "tourism": {
        "poi_table":   "tourism",
        "needs":       ["transport", "recreation"],
        "avoid":       [],
        "min_pop":     100,
        "min_dist_km": 1.0,
        "weight":      0.9,
    },
    "infra_str": {
        "poi_table":   "infra_str",
        "needs":       ["transport", "business"],
        "avoid":       ["recreation"],
        "min_pop":     100,
        "min_dist_km": 1.5,
        "weight":      1.1,
    },
}

ALL_POI_TABLES = [
    "health_care", "education", "transport", "food",
    "shops", "business", "tourism", "religious",
    "landuse", "infra_str", "finance", "recreation", "building",
]

DIVERSITY_TABLES    = ["building", "landuse", "infra_str", "religious"]
PROXIMITY_RADIUS_KM = 3.0
BIN_SIZE_DEG        = 0.05


# ─────────────────────────────────────────────────────────────────
# HAVERSINE
# ─────────────────────────────────────────────────────────────────
def haversine(lat1: float, lon1: float,
              lat2: float, lon2: float) -> float:
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


# ─────────────────────────────────────────────────────────────────
# SPATIAL INDEX
# ─────────────────────────────────────────────────────────────────
def build_spatial_index(pois: list[dict]) -> dict[int, list[dict]]:
    index: dict[int, list[dict]] = {}
    for p in pois:
        bin_key = int(p["lat"] / BIN_SIZE_DEG)
        index.setdefault(bin_key, []).append(p)
    return index


def query_spatial_index(index:     dict[int, list[dict]],
                        cell_lat:  float,
                        radius_km: float) -> list[dict]:
    lat_deg    = radius_km / 111.0
    bin_min    = int((cell_lat - lat_deg) / BIN_SIZE_DEG)
    bin_max    = int((cell_lat + lat_deg) / BIN_SIZE_DEG)
    candidates = []
    for b in range(bin_min, bin_max + 1):
        if b in index:
            candidates.extend(index[b])
    return candidates


# ─────────────────────────────────────────────────────────────────
# DISTANCE-DECAYED SUM  (no cap — raw value for percentile use)
# ─────────────────────────────────────────────────────────────────
def decay_sum(cell_lat:  float,
              cell_lon:  float,
              index:     dict[int, list[dict]],
              radius_km: float = PROXIMITY_RADIUS_KM) -> float:
    candidates = query_spatial_index(index, cell_lat, radius_km)
    total      = 0.0
    for p in candidates:
        d = haversine(cell_lat, cell_lon, p["lat"], p["lon"])
        if d < radius_km:
            total += 1.0 / (d + 0.1)
    return total


# ─────────────────────────────────────────────────────────────────
# PERCENTILE HELPERS
# ─────────────────────────────────────────────────────────────────
def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx         = (pct / 100.0) * (len(sorted_vals) - 1)
    lo          = int(idx)
    hi          = min(lo + 1, len(sorted_vals) - 1)
    frac        = idx - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def percentile_score(value: float,
                     p25:   float,
                     p50:   float,
                     p75:   float) -> float:
    """
    Returns 0.0–3.0 based on where value falls
    relative to area percentiles — self-adjusts to local density.
    """
    if value >= p75:
        return 3.0
    elif value >= p50:
        return 2.0
    elif value >= p25:
        return 1.0
    else:
        return 0.0


# ─────────────────────────────────────────────────────────────────
# LOAD ALL POIs + BUILD SPATIAL INDEXES  (used by DB scoring script)
# ─────────────────────────────────────────────────────────────────
def load_all_pois(cur) -> tuple[dict[str, list[dict]],
                                dict[str, dict[int, list[dict]]]]:
    poi_data:    dict[str, list[dict]]            = {}
    poi_indexes: dict[str, dict[int, list[dict]]] = {}

    for table in ALL_POI_TABLES:
        cur.execute(f"""
            SELECT lat, lon
            FROM {DB_SCHEMA}.{table}
            WHERE lat IS NOT NULL AND lon IS NOT NULL;
        """)
        rows = cur.fetchall()
        pois = [{"lat": float(r[0]), "lon": float(r[1])} for r in rows]

        poi_data[table]    = pois
        poi_indexes[table] = build_spatial_index(pois)
        print(f"   {len(pois):>7,} POIs  ← {table}")

    return poi_data, poi_indexes


# ─────────────────────────────────────────────────────────────────
# BUILD DECAY CACHE FOR ONE CELL
# ─────────────────────────────────────────────────────────────────
def build_decay_cache(cell_lat:    float,
                      cell_lon:    float,
                      poi_indexes: dict[str, dict]) -> dict[str, float]:
    cache = {}
    for table in ALL_POI_TABLES:
        cache[table] = decay_sum(
            cell_lat, cell_lon,
            poi_indexes.get(table, {}),
            radius_km = PROXIMITY_RADIUS_KM,
        )
    return cache


# ─────────────────────────────────────────────────────────────────
# PRECOMPUTE AREA PERCENTILES ACROSS ALL GRIDS
# Call once before scoring — reused for every grid in the batch
# ─────────────────────────────────────────────────────────────────
def compute_area_percentiles(decay_caches: list[dict[str, float]]) -> dict[str, dict]:
    """
    decay_caches : list of decay_cache dicts, one per grid.
    Returns      : { table_name: { p25, p50, p75 } }
    """
    area_pct = {}
    for table in ALL_POI_TABLES:
        vals = [dc.get(table, 0.0) for dc in decay_caches]
        area_pct[table] = {
            "p25": percentile(vals, 25),
            "p50": percentile(vals, 50),
            "p75": percentile(vals, 75),
        }
    return area_pct


# ─────────────────────────────────────────────────────────────────
# NORMALIZE SCORES 0 → 100 ACROSS A LIST
# ─────────────────────────────────────────────────────────────────
def normalize_scores(scored_grids: list[dict],
                     score_key:    str = "dynamic_score") -> list[dict]:
    values  = [g[score_key] for g in scored_grids]
    min_val = min(values)
    max_val = max(values)
    rng     = max_val - min_val

    for g in scored_grids:
        g["normalized_score"] = (
            50.0 if rng == 0
            else round((g[score_key] - min_val) / rng * 100, 2)
        )

    return scored_grids


# ─────────────────────────────────────────────────────────────────
# SCORE ONE CELL FOR ONE CATEGORY  (percentile-relative)
# ─────────────────────────────────────────────────────────────────
def score_cell_for_category(cell:        dict,
                             rules:       dict,
                             poi_data:    dict[str, list[dict]],
                             poi_indexes: dict[str, dict],
                             pop_max:     float,
                             decay_cache: dict[str, float],
                             area_pct:    dict[str, dict] = None) -> float:
    lat = cell["center_lat"]
    lon = cell["center_lon"]
    pop = cell["population"]

    score = 0.0

    # ── Factor 1: Competition ────────────────────────────────────
    competitors     = poi_data.get(rules["poi_table"], [])
    min_dist_km     = rules["min_dist_km"]
    comp_penalty    = 0.0
    comp_index      = poi_indexes.get(rules["poi_table"], {})
    comp_candidates = query_spatial_index(comp_index, lat, min_dist_km * 2)

    for p in comp_candidates:
        d = haversine(lat, lon, p["lat"], p["lon"])
        if d < min_dist_km * 0.5:
            comp_penalty -= 4.0
        elif d < min_dist_km:
            comp_penalty -= 2.0
        elif d < min_dist_km * 2:
            comp_penalty -= 0.5

    if not competitors:
        comp_penalty += 5.0

    score += max(comp_penalty, -10.0)

    # ── Factor 2: Population ─────────────────────────────────────
    pop_ratio = pop / pop_max if pop_max > 0 else 0.0

    if pop < rules["min_pop"]:
        pop_score = 0.0
    elif pop_ratio >= 0.75:
        pop_score = 4.0
    elif pop_ratio >= 0.50:
        pop_score = 3.0
    elif pop_ratio >= 0.25:
        pop_score = 2.0
    else:
        pop_score = 1.0

    score += pop_score

    # ── Factor 3: Required nearby facilities (percentile-relative) ─
    for need_table in rules["needs"]:
        if area_pct and need_table in area_pct:
            p = area_pct[need_table]
            score += percentile_score(
                decay_cache.get(need_table, 0.0),
                p["p25"], p["p50"], p["p75"]
            )
        else:
            score += min(decay_cache.get(need_table, 0.0), 3.0)

    # ── Factor 4: Avoid penalty ──────────────────────────────────
    for avoid_table in rules["avoid"]:
        candidates = query_spatial_index(
            poi_indexes.get(avoid_table, {}), lat, 1.0)
        for p in candidates:
            d = haversine(lat, lon, p["lat"], p["lon"])
            if d < 1.0:
                score -= 2.0

    # ── Factor 5: Accessibility (percentile-relative) ────────────
    if area_pct:
        tp = area_pct.get("transport", {})
        score += percentile_score(
            decay_cache.get("transport", 0.0),
            tp.get("p25", 0), tp.get("p50", 0), tp.get("p75", 0)
        )
        ip = area_pct.get("infra_str", {})
        score += percentile_score(
            decay_cache.get("infra_str", 0.0),
            ip.get("p25", 0), ip.get("p50", 0), ip.get("p75", 0)
        ) * 0.67
    else:
        score += min(decay_cache.get("transport", 0.0), 3.0)
        score += min(decay_cache.get("infra_str",  0.0), 2.0)

    # ── Factor 6: Diversity / urbanisation (percentile-relative) ─
    diversity = 0.0
    for div_table in DIVERSITY_TABLES:
        if area_pct and div_table in area_pct:
            dp = area_pct[div_table]
            diversity += percentile_score(
                decay_cache.get(div_table, 0.0),
                dp["p25"], dp["p50"], dp["p75"]
            )
        else:
            diversity += min(decay_cache.get(div_table, 0.0), 1.0)

    score += min(diversity, 3.0)

    return score


# ─────────────────────────────────────────────────────────────────
# SCORE ALL GRIDS FOR ONE CATEGORY  (runtime — called from agent)
# ─────────────────────────────────────────────────────────────────
def score_grids_for_category(grids:       list[dict],
                              poi_data:    dict[str, list[dict]],
                              poi_indexes: dict[str, dict],
                              category:    str) -> list[dict]:
    """
    Full pipeline:
      1. Build decay cache per grid
      2. Compute area percentiles once across all grids
      3. Score each grid relative to those percentiles
      4. Normalize scores 0 → 100
    Returns grids with dynamic_score + normalized_score added.
    """
    if not grids:
        return []

    if category not in FACILITY_RULES:
        return [dict(g, dynamic_score=0, normalized_score=0) for g in grids]

    rules   = FACILITY_RULES[category]
    pop_max = max((g.get("population", 0) for g in grids), default=1) or 1

    # Step 1: decay caches
    decay_caches = [
        build_decay_cache(g["lat"], g["lon"], poi_indexes)
        for g in grids
    ]

    # Step 2: area percentiles
    area_pct = compute_area_percentiles(decay_caches)

    print(f"📊 Percentiles [{category}] transport → "
          f"p25={area_pct['transport']['p25']:.2f} "
          f"p50={area_pct['transport']['p50']:.2f} "
          f"p75={area_pct['transport']['p75']:.2f}")

    # Step 3: score
    scored = []
    for i, g in enumerate(grids):
        cell = {
            "center_lat": g["lat"],
            "center_lon": g["lon"],
            "population": g.get("population", 0),
        }
        raw = score_cell_for_category(
            cell        = cell,
            rules       = rules,
            poi_data    = poi_data,
            poi_indexes = poi_indexes,
            pop_max     = pop_max,
            decay_cache = decay_caches[i],
            area_pct    = area_pct,
        )
        scored.append(dict(g, dynamic_score=round(raw, 4)))

    # Step 4: normalize
    scored = normalize_scores(scored, score_key="dynamic_score")

    print(f"✅ {len(scored)} grids scored | "
          f"raw range: {min(g['dynamic_score'] for g in scored):.2f} – "
          f"{max(g['dynamic_score'] for g in scored):.2f} | "
          f"normalized: 0.0 – 100.0")

    return scored


# ─────────────────────────────────────────────────────────────────
# SCORE A BATCH OF CELLS  (used by DB scoring script only)
# ─────────────────────────────────────────────────────────────────
def score_batch(grids:       list[dict],
                poi_data:    dict[str, list[dict]],
                poi_indexes: dict[str, dict],
                pop_max:     float) -> list[tuple[float, int]]:

    decay_caches = [
        build_decay_cache(cell["center_lat"], cell["center_lon"], poi_indexes)
        for cell in grids
    ]
    area_pct = compute_area_percentiles(decay_caches)

    results = []
    for i, cell in enumerate(grids):
        weighted_sum = 0.0
        total_weight = 0.0

        for category, rules in FACILITY_RULES.items():
            cat_score     = score_cell_for_category(
                                cell, rules, poi_data,
                                poi_indexes, pop_max,
                                decay_caches[i],
                                area_pct = area_pct)
            weighted_sum += cat_score * rules["weight"]
            total_weight += rules["weight"]

        combined = weighted_sum / total_weight if total_weight else 0.0
        results.append((round(combined, 4), cell["id"]))

    return results