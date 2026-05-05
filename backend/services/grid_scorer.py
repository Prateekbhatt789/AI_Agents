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
        "min_pop":     70,
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
        "min_pop":     30,
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
    "religious": {
        "poi_table":   "religious",
        "needs":       ["transport"],
        "avoid":       ["infra_str", "business"],
        "min_pop":     50,
        "min_dist_km": 1.0,
        "weight":      1.0,
    },
}

ALL_POI_TABLES = [
    "health_care", "education", "transport", "food",
    "shops", "business", "tourism", "religious",
    "landuse", "infra_str", "finance", "recreation", "building",
]


DIVERSITY_TABLES    = ["building", "landuse", "religious"]
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
def build_spatial_index(pois: list[dict]) -> dict[tuple, list[dict]]:
    index: dict[tuple, list[dict]] = {}
    for p in pois:
        # FIX 2: Guard against missing or invalid lat/lon in POI data
        # Without this, int(None / 0.05) raises TypeError at runtime
        try:
            lat_bin = int(float(p["lat"]) / BIN_SIZE_DEG)
            lon_bin = int(float(p["lon"]) / BIN_SIZE_DEG)
        except (KeyError, TypeError, ValueError):
            continue
        bin_key = (lat_bin, lon_bin)
        index.setdefault(bin_key, []).append(p)
    return index


def query_spatial_index(index:     dict[tuple, list[dict]],
                        cell_lat:  float,
                        cell_lon:  float,
                        radius_km: float) -> list[dict]:
   
    if not index:
        return []

    lat_deg = radius_km / 111.0
    # Clamp lat to avoid cos(90°) = 0 → division by zero near poles
    clamped_lat = max(-89.9, min(89.9, cell_lat))
    lon_deg     = radius_km / (111.0 * math.cos(math.radians(clamped_lat)))

    lat_bin_min = int((cell_lat - lat_deg) / BIN_SIZE_DEG)
    lat_bin_max = int((cell_lat + lat_deg) / BIN_SIZE_DEG)
    lon_bin_min = int((cell_lon - lon_deg) / BIN_SIZE_DEG)
    lon_bin_max = int((cell_lon + lon_deg) / BIN_SIZE_DEG)

    candidates = []
    for lat_b in range(lat_bin_min, lat_bin_max + 1):
        for lon_b in range(lon_bin_min, lon_bin_max + 1):
            bin_key = (lat_b, lon_b)
            if bin_key in index:
                candidates.extend(index[bin_key])
    return candidates


# ─────────────────────────────────────────────────────────────────
# DISTANCE-DECAYED SUM
# ─────────────────────────────────────────────────────────────────
def decay_sum(cell_lat:  float,
              cell_lon:  float,
              index:     dict[tuple, list[dict]],
              radius_km: float = PROXIMITY_RADIUS_KM) -> float:
    candidates = query_spatial_index(index, cell_lat, cell_lon, radius_km)
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
    Returns 0.0–3.0 smoothly based on where value falls
    relative to area percentiles — self-adjusts to local density.
    """
    if p75 > p50 and value >= p75:
        # Above p75: scale 3.0 → 4.0 with diminishing returns cap at 3.5
        extra = (value - p75) / (p75 - p50 + 1e-9)
        return min(3.0 + extra * 0.5, 3.5)
    elif p75 > p50 and value >= p50:
        return 2.0 + (value - p50) / (p75 - p50) * 1.0
    elif p50 > p25 and value >= p25:
        return 1.0 + (value - p25) / (p50 - p25) * 1.0
    elif value > 0:
        # Below p25 but not zero — give small partial credit
        baseline = p25 if p25 > 0 else 1.0
        return min(value / baseline, 1.0) * 0.5
    else:
        return 0.0


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
            radius_km=PROXIMITY_RADIUS_KM,
        )
    return cache


# ─────────────────────────────────────────────────────────────────
# PRECOMPUTE AREA PERCENTILES ACROSS ALL GRIDS
# ─────────────────────────────────────────────────────────────────
def compute_area_percentiles(decay_caches: list[dict[str, float]]) -> dict[str, dict]:
    """
decay_caches = [
  {"transport": 5, "shops": 2},
  {"transport": 10, "shops": 3},
  {"transport": 20, "shops": 6},
  {"transport": 30, "shops": 8},]
  
vals = [5, 10, 20, 30] for transport
  
Returns:
   area_pct = {
  "transport": { "p25": 8.75, "p50": 15, "p75": 22.5 },
  "shops":     { "p25": ...,  "p50": ..., "p75": ... }
}
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
    if not scored_grids:
        return []

    values  = [g[score_key] for g in scored_grids]
    min_val = min(values)
    max_val = max(values)
    rng     = max_val - min_val

    result = []
    for g in scored_grids:
        g_copy = g.copy()
        if rng == 0:
            # FIX 7: Single grid or all grids equal score
            # OLD: returned 50.0 — misleading, implies middle of range
            # NEW: if only 1 grid → 100.0 (it's the best by default)
            #      if multiple grids all equal → 50.0 (genuinely tied)
            g_copy["normalized_score"] = 100.0 if len(scored_grids) == 1 else 50.0
        else:
            g_copy["normalized_score"] = round(
                (g[score_key] - min_val) / rng * 100, 2
            )
        result.append(g_copy)

    return result


# ─────────────────────────────────────────────────────────────────
# SCORE ONE CELL FOR ONE CATEGORY  (percentile-relative)
# ─────────────────────────────────────────────────────────────────
def score_cell_for_category(cell:        dict,
                             rules:       dict,
                             poi_indexes: dict[str, dict],
                             pop_max:     float,
                             decay_cache: dict[str, float],
                             area_pct:    dict[str, dict] = None) -> float:

    lat = cell["center_lat"]
    lon = cell["center_lon"]
    pop = cell["population"]

    score = 0.0

    # ── Factor 1: Competition ────────────────────────────────────
    min_dist_km  = rules["min_dist_km"]
    comp_penalty = 0.0
    comp_index   = poi_indexes.get(rules["poi_table"], {})
    comp_candidates = query_spatial_index(comp_index, lat, lon, min_dist_km * 2)

    nearby = []
    for p in comp_candidates:
        d = haversine(lat, lon, p["lat"], p["lon"])
        if d < min_dist_km * 0.5:
            comp_penalty -= 4.0
            nearby.append(p)
        elif d < min_dist_km:
            comp_penalty -= 2.0
            nearby.append(p)
        elif d < min_dist_km * 2:
            comp_penalty -= 0.5
            nearby.append(p)

    if not nearby:
        comp_penalty += 5.0

    competitor_count = len(nearby)
    dynamic_floor    = min(-4.0 * competitor_count, -20.0)
    score           += max(comp_penalty, dynamic_floor)

    # ── Factor 2: Population ─────────────────────────────────────
    
    if pop < rules["min_pop"]:
        pop_score = 0.0
    else:
        pop_ratio = pop / pop_max if pop_max > 0 else 0.0
        if pop_ratio >= 0.75:
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
            pct = area_pct[need_table]
            score += percentile_score(
                decay_cache.get(need_table, 0.0),
                pct["p25"], pct["p50"], pct["p75"]
            )
        else:
            score += min(decay_cache.get(need_table, 0.0), 3.0)

    # ── Factor 4: Avoid penalty ──────────────────────────────────
    for avoid_table in rules["avoid"]:
        candidates = query_spatial_index(
            poi_indexes.get(avoid_table, {}), lat, lon, 1.0
        )
        for poi in candidates:
            d = haversine(lat, lon, poi["lat"], poi["lon"])
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

    # ── Factor 6: Diversity / urbanisation 
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
        # FIX 11: Log unknown category so caller knows why scores are 0
        print(f"  Unknown category '{category}' — valid: {list(FACILITY_RULES.keys())}")
        return []
        # return [dict(g, dynamic_score=0, normalized_score=0) for g in grids]

    rules = FACILITY_RULES[category]

    
    pop_max = max((g.get("population", 0) for g in grids), default=1)
    pop_max = pop_max if pop_max > 0 else 1

    # Step 1: decay caches
    decay_caches = [
        build_decay_cache(g["center_lat"], g["center_lon"], poi_indexes)
        for g in grids
    ]
    
    
#     decay_caches = [
#   {"transport": 5, "shops": 2},
#   {"transport": 10, "shops": 3},
#   {"transport": 20, "shops": 6},
#   {"transport": 30, "shops": 8},
# ]

    # Step 2: area percentiles
    area_pct = compute_area_percentiles(decay_caches)



    # Step 3: score — FIX 8 reflected here: removed poi_data from call
    scored = []
    for i, g in enumerate(grids):
        raw = score_cell_for_category(
            cell        = g,
            rules       = rules,
            poi_indexes = poi_indexes,
            pop_max     = pop_max,
            decay_cache = decay_caches[i],
            area_pct    = area_pct,
        )
        scored.append(dict(g, dynamic_score=round(raw, 4)))

    # Step 4: normalize
    scored = normalize_scores(scored, score_key="dynamic_score")


    return scored
