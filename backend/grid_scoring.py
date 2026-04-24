import os
import math
from db.database import get_db_conn, release_db_conn

DB_SCHEMA  = os.getenv("DB_SCHEMA", "data")

# ─────────────────────────────────────────────────────────────────
# ✏️  CHANGE THESE TWO VALUES FOR EACH RUN
#     Run 1 → START_GRID_ID = 1,      END_GRID_ID = 25000
# ─────────────────────────────────────────────────────────────────
START_GRID_ID = 1
END_GRID_ID   = 20000

BATCH_SIZE    = 500


# ─────────────────────────────────────────────────────────────────
# FACILITY RULES
# poi_table:	Which table to look at
# needs:    	What should be nearby
# avoid	:       What should NOT be nearby
# min_pop:      Minimum population
# min_dist_km: 	Competition distance
# weight:   	Importance in final score
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


# ─────────────────────────────────────────────────────────────────
# 6.1.1.2 HAVERSINE
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
# 4.1 SPATIAL INDEX
# groups POIs (points) into latitude buckets (bins) so you don’t have to scan all points every time.
# ─────────────────────────────────────────────────────────────────
BIN_SIZE_DEG = 0.05

def build_spatial_index(pois: list[dict]) -> dict[int, list[dict]]:
    index: dict[int, list[dict]] = {}
    for p in pois:
        bin_key = int(p["lat"] / BIN_SIZE_DEG)
        index.setdefault(bin_key, []).append(p)
    return index

# ─────────────────────────────────────────────────────────────────
# 6.1.1.1 query_spatial index
# ─────────────────────────────────────────────────────────────────
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
# 6.1.1 DISTANCE-DECAYED SUM
# ─────────────────────────────────────────────────────────────────
def decay_sum(cell_lat:  float,
              cell_lon:  float,
              index:     dict[int, list[dict]],
              radius_km: float = PROXIMITY_RADIUS_KM,
              max_val:   float = 5.0) -> float:
    candidates = query_spatial_index(index, cell_lat, radius_km)
    total      = 0.0
    for p in candidates:
        d = haversine(cell_lat, cell_lon, p["lat"], p["lon"])
        if d < radius_km:
            total += 1.0 / (d + 0.1)
    return min(total, max_val)


# ─────────────────────────────────────────────────────────────────
# 4. LOAD ALL POIs + BUILD SPATIAL INDEXES
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
# 6.1 BUILD DECAY CACHE FOR ONE CELL
# ─────────────────────────────────────────────────────────────────
def build_decay_cache(cell_lat:   float,
                      cell_lon:   float,
                      poi_indexes: dict[str, dict]) -> dict[str, float]:
    cache = {}
    for table in ALL_POI_TABLES:
        cache[table] = decay_sum(
            cell_lat, cell_lon,
            poi_indexes.get(table, {}),
            radius_km = PROXIMITY_RADIUS_KM,
            max_val   = 99999.0,   
        )
    return cache


# ─────────────────────────────────────────────────────────────────
# 6.2 SCORE ONE CELL FOR ONE CATEGORY  (uses decay cache)
# ─────────────────────────────────────────────────────────────────
def score_cell_for_category(cell:        dict,
                             rules:      dict,
                             poi_data:   dict[str, list[dict]],
                             poi_indexes: dict[str, dict],
                             pop_max:    float,
                             decay_cache: dict[str, float]) -> float:
    lat = cell["center_lat"]
    lon = cell["center_lon"]
    pop = cell["population"]

    score = 0.0

    # ── Factor 1: Competition ────────────────────────────────────
    # Cannot use decay cache here — competition uses a different
    # radius per category (min_dist_km) and applies tiered
    # penalties, so we still use spatial index directly.
    # This is fast because query_spatial_index filters by lat bin
    # before haversine, so only a small candidate set is checked.
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

    # ── Factor 3: Required nearby facilities (from cache) ────────
    for need_table in rules["needs"]:
        score += min(decay_cache.get(need_table, 0.0), 3.0)

    # ── Factor 4: Avoid penalty ──────────────────────────────────
    # Uses 1.0 km fixed radius — still needs spatial index directly
    for avoid_table in rules["avoid"]:
        candidates = query_spatial_index(
            poi_indexes.get(avoid_table, {}), lat, 1.0)
        for p in candidates:
            d = haversine(lat, lon, p["lat"], p["lon"])
            if d < 1.0:
                score -= 2.0

    # ── Factor 5: Accessibility (from cache) ─────────────────────
    score += min(decay_cache.get("transport", 0.0), 3.0)
    score += min(decay_cache.get("infra_str",  0.0), 2.0)

    # ── Factor 6: Diversity / urbanisation bonus (from cache) ────
    diversity = 0.0
    for div_table in DIVERSITY_TABLES:
        diversity += min(decay_cache.get(div_table, 0.0), 1.0)
    score += min(diversity, 3.0)

    return round(score, 4)


# ─────────────────────────────────────────────────────────────────
# 6. SCORE A BATCH OF CELLS
# ─────────────────────────────────────────────────────────────────
def score_batch(grids:       list[dict],
                poi_data:    dict[str, list[dict]],
                poi_indexes: dict[str, dict],
                pop_max:     float) -> list[tuple[float, int]]:
    results = []
    for cell in grids:
        lat = cell["center_lat"]
        lon = cell["center_lon"]

        # Build decay cache once for this cell — reused across
        # all 9 categories instead of recomputing every time
        decay_cache = build_decay_cache(lat, lon, poi_indexes)

        weighted_sum = 0.0
        total_weight = 0.0

        for category, rules in FACILITY_RULES.items():
            cat_score     = score_cell_for_category(
                                cell, rules, poi_data,
                                poi_indexes, pop_max,
                                decay_cache)
            weighted_sum += cat_score * rules["weight"]
            total_weight += rules["weight"]

        combined = weighted_sum / total_weight if total_weight else 0.0
        results.append((round(combined, 4), cell["id"]))

    return results


# ─────────────────────────────────────────────────────────────────
# 1. ENSURE raw_score COLUMN EXISTS
# ─────────────────────────────────────────────────────────────────
def ensure_columns(cur) -> None:
    cur.execute(f"""
        ALTER TABLE {DB_SCHEMA}.grids
        ADD COLUMN IF NOT EXISTS raw_score DOUBLE PRECISION;
    """)


# ─────────────────────────────────────────────────────────────────
# 2. FETCH pop_max GLOBALLY
# Must be the same value across all range scripts so population
# scoring is consistent — every script queries the full table.
# ─────────────────────────────────────────────────────────────────
def fetch_pop_max(cur) -> float:
    cur.execute(f"""
        SELECT MAX(COALESCE(population_per_grid, 0))
        FROM {DB_SCHEMA}.grids;
    """)
    return float(cur.fetchone()[0] or 1.0)


# ─────────────────────────────────────────────────────────────────
# 3. FETCH COUNT OF GRIDS IN THIS RANGE
# ─────────────────────────────────────────────────────────────────
def fetch_range_count(cur, start_id: int, end_id: int) -> int:
    cur.execute(f"""
        SELECT COUNT(*)
        FROM {DB_SCHEMA}.grids
        WHERE id >= %s AND id <= %s;
    """, (start_id, end_id))
    return int(cur.fetchone()[0])


# ─────────────────────────────────────────────────────────────────
# 5. FETCH ONE BATCH WITHIN RANGE  (keyset pagination)
# Skips already scored rows so the script is safely resumable —
# if it crashes mid-run, just rerun and it picks up where it left off.
# ─────────────────────────────────────────────────────────────────
def fetch_grid_page(cur,
                    after_id: int,
                    end_id:   int,
                    limit:    int) -> list[dict]:
    cur.execute(f"""
        SELECT
            id,
            ST_Y(centroid::geometry)         AS center_lat,
            ST_X(centroid::geometry)         AS center_lon,
            COALESCE(population_per_grid, 0) AS population
        FROM {DB_SCHEMA}.grids
        WHERE id    >  %s
          AND id    <= %s
          AND raw_score IS NULL
        ORDER BY id
        LIMIT %s;
    """, (after_id, end_id, limit))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ─────────────────────────────────────────────────────────────────
# WRITE ONE BATCH — retries on failure, skips if all retries fail
# Commits after every batch so connection never idles long enough
# to time out, and already-written batches survive a crash.
# ─────────────────────────────────────────────────────────────────
def write_raw_batch(cur, conn,
                    scored:    list[tuple[float, int]],
                    batch_num: int,
                    retries:   int = 3) -> bool:
    for attempt in range(1, retries + 1):
        try:
            cur.executemany(f"""
                UPDATE {DB_SCHEMA}.grids
                SET raw_score = %s
                WHERE id = %s;
            """, scored)
            conn.commit()
            return True

        except Exception as e:
            print(f"   ⚠️  Batch {batch_num} attempt {attempt} failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

            if attempt == retries:
                print(f"   🔴 Batch {batch_num} permanently failed — "
                      f"skipping, continuing with next batch.")
                return False

    return False


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def calculate_grid_scores() -> None:

    print(f"🚀 Starting scoring for grid id {START_GRID_ID} → {END_GRID_ID}\n")

    conn = get_db_conn()
    try:
        cur = conn.cursor()

        # ── Ensure raw_score column exists ───────────────────────
        ensure_columns(cur)
        conn.commit()

        # ── Global pop_max ────────────────────────────────────────
        pop_max = fetch_pop_max(cur)
        print(f"Global pop_max : {pop_max:,.0f}")

        # ── Count grids in this range ─────────────────────────────
        range_total = fetch_range_count(cur, START_GRID_ID, END_GRID_ID)
        print(f" Grids in range : {range_total:,}  "
              f"(id {START_GRID_ID} → {END_GRID_ID})\n")

        if range_total == 0:
            print(" No grids found in this range — nothing to score.")
            return

        # ── Load all POIs once into RAM ───────────────────────────
        print(" Loading POIs + building spatial indexes …")
        poi_data, poi_indexes = load_all_pois(cur)
        print()

        # ─────────────────────────────────────────────────────────
        # SCORING LOOP
        # fetch BATCH_SIZE grids → score → write raw_score → commit
        #
        # fetch_grid_page filters WHERE raw_score IS NULL so:
        #   • already scored rows are automatically skipped
        #   • safe to rerun if script crashes mid-way
        #   • after_id still moves forward correctly via keyset
        # ─────────────────────────────────────────────────────────
        print(f"⚙️  Scoring in batches of {BATCH_SIZE:,} …\n")

        after_id     = START_GRID_ID - 1
        processed    = 0
        total_failed = 0
        batch_num    = 0

        while True:
            grids = fetch_grid_page(cur, after_id, END_GRID_ID, BATCH_SIZE)
            if not grids:
                break

            batch_num += 1
            scored     = score_batch(grids, poi_data, poi_indexes, pop_max)
            ok         = write_raw_batch(cur, conn, scored, batch_num)

            after_id   = grids[-1]["id"]
            processed += len(grids)

            if ok:
                print(f"   ✅ Batch {batch_num:>3} | "
                      f"ids {grids[0]['id']:>8} – {grids[-1]['id']:>8} | "
                      f"{processed:>6} / {range_total:,} done")
            else:
                total_failed += len(grids)
                print(f"   ⚠️  Batch {batch_num:>3} | SKIPPED | "
                      f"{total_failed:,} rows lost so far")

        # ── Summary ───────────────────────────────────────────────
        total_written = processed - total_failed
        print(f"\n{'─' * 55}")
        print(f"  Range    : {START_GRID_ID} → {END_GRID_ID}")
        print(f"  Written  : {total_written:,}")
        print(f"  Skipped  : {total_failed:,}")
        print(f"{'─' * 55}")
        print(f"\n✅ Done. Run remaining range scripts, then run")
        print(f"   the normalisation SQL query in the database.")

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"🔴 Fatal error: {e}")
        raise

    finally:
        release_db_conn(conn)


if __name__ == "__main__":
    calculate_grid_scores()