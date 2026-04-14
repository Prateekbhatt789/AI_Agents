import math
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── WorldPop Configuration ────────────────────────────
WORLDPOP_URL  = "https://api.worldpop.org/v1/services/stats"
WORLDPOP_YEAR = 2020
MAX_RETRIES   = 3
RETRY_DELAY   = 2

# ── Catchment distances per facility ─────────────────
CATCHMENT_KM = {
    "hospitals":     2.0,
    "schools":       1.0,
    "pharmacies":    0.5,
    "restaurants":   0.3,
    "fuel_stations": 3.0,
    "bus_stops":     0.5,
}

# ── Rules for each facility type ─────────────────────
FACILITY_RULES = {
    "hospitals":     { "needs": ["bus_stops"],           "avoid": [],                "min_pop": 500,  "min_dist": 2.0 },
    "schools":       { "needs": ["bus_stops"],           "avoid": [], "min_pop": 200,  "min_dist": 1.0 },
    "pharmacies":    { "needs": ["hospitals"],           "avoid": [],                "min_pop": 100,  "min_dist": 0.5 },
    "restaurants":   { "needs": ["bus_stops"],           "avoid": [],                "min_pop": 50,   "min_dist": 0.2 },
    "fuel_stations": { "needs": [],                      "avoid": [],                "min_pop": 100,  "min_dist": 3.0 },
}


# ─────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float,
              lat2: float, lon2: float) -> float:
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(lat1)) *
            math.cos(math.radians(lat2)) *
            math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def build_circle_geojson(lat: float, lon: float,
                          radius_km: float) -> str:
    points = []
    for angle in range(0, 360, 10):
        rad   = math.radians(angle)
        d_lat = (radius_km / 111.0) * math.cos(rad)
        d_lon = (radius_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(rad)
        points.append([lon + d_lon, lat + d_lat])

    points.append(points[0])

    return json.dumps({
        "type":        "Polygon",
        "coordinates": [points]
    })


# ─────────────────────────────────────────────────────
# WORLDPOP POPULATION FUNCTION
# ─────────────────────────────────────────────────────

def get_population_worldpop(lat: float, lon: float,
                             radius_km: float) -> int:
    geojson = build_circle_geojson(lat, lon, radius_km)

    payload = {
        "dataset":  "wpgpas",
        "year":     WORLDPOP_YEAR,
        "geojson":  geojson,
        "runasync": "false",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                WORLDPOP_URL,
                data    = payload,
                timeout = 30,
            )

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", RETRY_DELAY * attempt))
                time.sleep(wait)
                continue

            if response.status_code != 200:
                time.sleep(RETRY_DELAY * attempt)
                continue

            data      = response.json()
            has_error = data.get("error", False)

            if has_error:
                print(f"🔴 WorldPop API error: {data.get('message', 'unknown error')}")
                time.sleep(RETRY_DELAY * attempt)
                continue

            status   = data.get("status", "")
            api_data = data.get("data", {})

            if isinstance(api_data, dict) and "agesexpyramid" in api_data:
                age_data   = api_data["agesexpyramid"]
                population = int(sum(g["male"] + g["female"] for g in age_data))
                return population

            if isinstance(api_data, list) and api_data:
                population = int(api_data[0].get("total_population", 0))
                if population > 0:
                    return population

            if status not in ("finished", "ok", "success", ""):
                time.sleep(RETRY_DELAY * attempt)
                continue

            print(f"🔴 WorldPop unexpected response: {str(data)[:200]}")
            time.sleep(RETRY_DELAY * attempt)
            continue

        except requests.exceptions.Timeout:
            time.sleep(RETRY_DELAY * attempt)

        except requests.exceptions.ConnectionError:
            time.sleep(RETRY_DELAY * attempt)

        except Exception as e:
            print(f"🔴 WorldPop request failed: {type(e).__name__}: {e}")
            return 0

    return 0


def estimate_population(cell: dict) -> int:
    if cell.get("population", 0) > 0:
        return cell["population"]
    buildings = len(cell["pois"].get("buildings", []))
    return buildings * 20


# ─────────────────────────────────────────────────────
# PARALLEL WORLDPOP — THREAD BASED
# ─────────────────────────────────────────────────────

def fetch_all_cells_parallel(cells: list) -> list:
    results = [0] * len(cells)

    def fetch_one(index: int, cell: dict):
        pop = get_population_worldpop(
            cell["center_lat"],
            cell["center_lon"],
            cell.get("cell_radius_km", 0.6)
        )
        return index, pop

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_one, i, cell): i
            for i, cell in enumerate(cells)
        }
        for future in as_completed(futures):
            try:
                index, pop     = future.result()
                results[index] = pop
            except Exception as e:
                print(f"🔴 WorldPop thread failed: {e}")

    print(f"✅ WorldPop complete — {len(cells)} cells fetched")
    return results


# ─────────────────────────────────────────────────────
# GRID CREATION
# ─────────────────────────────────────────────────────

def create_grid(center_lat: float, center_lon: float,
                radius_km: float, grid_size: int = 5) -> list:
    lat_deg        = radius_km / 111.0
    lon_deg        = radius_km / (111.0 * math.cos(math.radians(center_lat)))
    cell_lat       = (2 * lat_deg) / grid_size
    cell_lon       = (2 * lon_deg) / grid_size
    cell_radius_km = (radius_km * 2 / grid_size) / 2
    start_lat      = center_lat + lat_deg
    start_lon      = center_lon - lon_deg
    valid_cells    = []

    for row in range(grid_size):
        for col in range(grid_size):
            north = start_lat - (row * cell_lat)
            south = north - cell_lat
            west  = start_lon + (col * cell_lon)
            east  = west + cell_lon

            cell_center_lat = (north + south) / 2
            cell_center_lon = (west  + east)  / 2
            cell_name       = f"{chr(65 + row)}{col + 1}"

            dist = haversine(
                center_lat,      center_lon,
                cell_center_lat, cell_center_lon
            )

            if dist > radius_km:
                continue

            valid_cells.append({
                "name":             cell_name,
                "row":              row,
                "col":              col,
                "north":            north,
                "south":            south,
                "west":             west,
                "east":             east,
                "center_lat":       cell_center_lat,
                "center_lon":       cell_center_lon,
                "dist_from_center": round(dist, 2),
                "cell_radius_km":   cell_radius_km,
                "pois":             {}
            })

    return valid_cells


# ─────────────────────────────────────────────────────
# POI ASSIGNMENT
# ─────────────────────────────────────────────────────

def assign_pois_to_grid(cells: list, poi_data: dict) -> list:
    for cell in cells:
        cell["pois"] = {
            "hospitals":     [],
            "bus_stops":     [],
            "fuel_stations": [],
            "schools":       [],
            "restaurants":   [],
            "pharmacies":    [],
            "buildings":     []
        }

    for category, items in poi_data.items():
        if category == "summary" or not isinstance(items, list):
            continue
        for poi in items:
            for cell in cells:
                if (cell["south"] <= poi["lat"] <= cell["north"] and
                    cell["west"]  <= poi["lon"] <= cell["east"]):
                    if category in cell["pois"]:
                        cell["pois"][category].append(poi["name"])
                    break

    populations = fetch_all_cells_parallel(cells)

    for i, cell in enumerate(cells):
        raw_pop = populations[i]
        if raw_pop > 0:
            cell["population"] = raw_pop
        else:
            buildings          = len(cell["pois"].get("buildings", []))
            cell["population"] = buildings * 20

    return cells


# ─────────────────────────────────────────────────────
# CELL SCORING
# ─────────────────────────────────────────────────────

def score_cell(cell: dict, category: str,
               all_pois: dict, all_cells: list = None) -> dict:
    rules = FACILITY_RULES.get(category, {
        "needs": [], "avoid": [], "min_pop": 100, "min_dist": 1.0
    })

    score = 0
    notes = []

    # ── Factor 1: Competition ─────────────────────────
    existing       = len(cell["pois"].get(category, []))
    adjacent_count = 0

    if all_cells:
        for other in all_cells:
            if other["name"] == cell["name"]:
                continue
            if (abs(other["row"] - cell["row"]) <= 1 and
                    abs(other["col"] - cell["col"]) <= 1):
                adjacent_count += len(other["pois"].get(category, []))

    if existing == 0 and adjacent_count == 0:
        score += 5
        notes.append(f"✅ Zero {category} here or nearby — perfect gap")
    elif existing == 0 and adjacent_count <= 2:
        score += 4
        notes.append(f"🟢 No {category} here, {adjacent_count} nearby — low risk")
    elif existing == 0 and adjacent_count <= 5:
        score += 2
        notes.append(f"🟡 No {category} here but {adjacent_count} nearby")
    elif existing == 0:
        score += 1
        notes.append(f"🟠 No {category} here but {adjacent_count} in surrounding zones")
    elif existing == 1:
        score += 2
        notes.append(f"🟡 Only 1 existing — low competition")
    else:
        score -= existing
        notes.append(f"🔴 {existing} already exist — saturated")

    # ── Factor 2: Population ──────────────────────────
    population = estimate_population(cell)

    if all_cells:
        all_pops  = [estimate_population(c) for c in all_cells]
        max_pop   = max(all_pops) if all_pops else 1
        min_pop   = min(all_pops) if all_pops else 0
        pop_range = max_pop - min_pop or 1
        relative  = (population - min_pop) / pop_range

        if population < rules["min_pop"]:
            score += 0
            notes.append(f"🔴 Population too low (~{population:,})")
        elif relative >= 0.75:
            score += 4
            notes.append(f"✅ Highest population zone (~{population:,})")
        elif relative >= 0.50:
            score += 3
            notes.append(f"✅ Good population (~{population:,})")
        elif relative >= 0.25:
            score += 2
            notes.append(f"🟡 Moderate population (~{population:,})")
        else:
            score += 1
            notes.append(f"🟠 Below-average population (~{population:,})")
    else:
        if population >= rules["min_pop"]:
            score += 3
            notes.append(f"✅ Good population (~{population:,} residents)")
        else:
            notes.append(f"⚠️ Low population (~{population:,} residents)")

    # ── Factor 3: Required nearby facilities ──────────
    for needed in rules["needs"]:
        count = len(cell["pois"].get(needed, []))
        if count >= 3:
            score += 3
            notes.append(f"✅ Good {needed} nearby ({count})")
        elif count > 0:
            score += 1
            notes.append(f"🟡 Limited {needed} ({count})")
        else:
            score -= 2
            notes.append(f"❌ No {needed} nearby")

    # ── Factor 4: Facilities to avoid ─────────────────
    for avoid in rules["avoid"]:
        count = len(cell["pois"].get(avoid, []))
        if count > 0:
            score -= 2
            notes.append(f"⚠️ {avoid} nearby — not ideal")

    # ── Factor 5: Distance from nearest competitor ────
    min_dist  = rules["min_dist"]
    all_items = all_pois.get(category, [])

    if all_items:
        nearest = min(
            haversine(
                cell["center_lat"], cell["center_lon"],
                p["lat"], p["lon"]
            )
            for p in all_items
        )

        if nearest >= min_dist * 3:
            score += 5
            notes.append(f"✅ {nearest:.1f}km from nearest — excellent gap")
        elif nearest >= min_dist * 2:
            score += 4
            notes.append(f"✅ {nearest:.1f}km from nearest — very good gap")
        elif nearest >= min_dist:
            score += 2
            notes.append(f"🟡 {nearest:.1f}km from nearest — acceptable gap")
        elif nearest >= min_dist * 0.5:
            score -= 1
            notes.append(f"🟠 {nearest:.1f}km — below minimum gap ({min_dist}km)")
        else:
            score -= 3
            notes.append(f"🔴 Only {nearest:.1f}km — far too close")
    else:
        score += 5
        notes.append("✅ No competitors in entire area!")

    return {
        "name":       cell["name"],
        "score":      score,
        "notes":      notes,
        "center_lat": cell["center_lat"],
        "center_lon": cell["center_lon"],
        "north":      cell["north"],
        "south":      cell["south"],
        "west":       cell["west"],
        "east":       cell["east"],
        "population": population,
        "existing":   existing,
    }


# ─────────────────────────────────────────────────────
# FULL GRID ANALYSIS
# ─────────────────────────────────────────────────────

def analyze_full_grid(cells: list, poi_data: dict,
                      purpose: str,
                      center_lat: float = None,
                      center_lon: float = None,
                      radius_km:  float = None) -> dict:
    purpose_map = {
        "hospital":   "hospitals",     "clinic":      "hospitals",
        "school":     "schools",       "college":     "schools",
        "pharmacy":   "pharmacies",    "medicine":    "pharmacies",
        "restaurant": "restaurants",   "food":        "restaurants",
        "fuel":       "fuel_stations", "petrol":      "fuel_stations",
        "vet":        "vet_hospitals", "veterinary":  "vet_hospitals",
    }

    category = "hospitals"
    for keyword, cat in purpose_map.items():
        if keyword in purpose.lower():
            category = cat
            break

    scored_cells = []
    for cell in cells:
        result = score_cell(cell, category, poi_data, all_cells=cells)
        scored_cells.append(result)

    scored_cells.sort(key=lambda x: x["score"], reverse=True)

    best  = scored_cells[0]
    worst = scored_cells[-1]

    max_score   = max(c["score"] for c in scored_cells)
    min_score   = min(c["score"] for c in scored_cells)
    score_range = max_score - min_score or 1

    for c in scored_cells:
        c["normalized"] = int(
            (c["score"] - min_score) / score_range * 100
        )

    print(f"🏆 Best: {best['name']} (score={best['score']}) | "
          f"⛔ Worst: {worst['name']} (score={worst['score']})")

    return {
        "category":   category,
        "best":       best,
        "worst":      worst,
        "all_cells":  scored_cells,
        "grid_cells": cells,
    }


# ─────────────────────────────────────────────────────
# TOP 3 CELLS  ✅ NEW FUNCTION
# ─────────────────────────────────────────────────────

def get_top3_cells(analysis: dict) -> list:
    """
    Returns top 3 scored cells from analysis.
    all_cells is already sorted best → worst
    so we just take first 3.

    Each cell contains:
    - rank (1, 2, 3)
    - label (best, second, third)
    - lat/lon for map pin
    - score, population, notes for popup
    """
    all_cells = analysis["all_cells"]

    # Take top 3 — or fewer if less than 3 cells exist
    top3       = all_cells[:3]
    rank_names = ["best", "second", "third"]
    result     = []

    for i, cell in enumerate(top3):
        result.append({
            "rank":       i + 1,
            "label":      rank_names[i],
            "name":       cell["name"],
            "center_lat": cell["center_lat"],
            "center_lon": cell["center_lon"],
            "score":      cell["score"],
            "population": cell["population"],
            "existing":   cell["existing"],
            "notes":      cell["notes"],
            "north":      cell.get("north"),
            "south":      cell.get("south"),
            "east":       cell.get("east"),
            "west":       cell.get("west"),
        })

    print(f"✅ Top 3 cells selected: "
          f"{[c['name'] for c in result]}")

    return result


# ─────────────────────────────────────────────────────
# TEXT FOR LLM
# ─────────────────────────────────────────────────────

def grid_to_text(analysis: dict) -> str:
    lines = []
    cat   = analysis["category"]
    best  = analysis["best"]
    worst = analysis["worst"]

    # Get top 3 for LLM context
    top3 = analysis["all_cells"][:3]

    lines.append(f"=== SPATIAL ANALYSIS FOR: {cat.upper()} ===\n")
    lines.append(f"Valid zones analyzed: {len(analysis['all_cells'])}")
    lines.append("(5x5 grid with outside-circle cells removed)\n")

    lines.append("Zone scores (higher = better opportunity):")
    for cell in analysis["all_cells"]:
        lines.append(
            f"  Zone {cell['name']:4} → "
            f"score={cell['score']:3} | "
            f"existing={cell['existing']} | "
            f"population~{cell['population']:,}"
        )

    # ✅ Show top 3 in LLM text
    rank_labels = ["🥇 BEST", "🥈 2ND BEST", "🥉 3RD BEST"]
    for i, cell in enumerate(top3):
        lines.append(f"\n{rank_labels[i]} ZONE: {cell['name']}")
        lines.append(f"   Coordinates: {cell['center_lat']:.4f}, "
                     f"{cell['center_lon']:.4f}")
        lines.append(f"   Score:       {cell['score']}")
        lines.append(f"   Population:  ~{cell['population']:,}")
        lines.append("   Reasons:")
        for note in cell["notes"]:
            lines.append(f"     {note}")

    lines.append(f"\n⛔ WORST ZONE: {worst['name']} "
                 f"(score: {worst['score']})")
    for note in worst["notes"][:2]:
        lines.append(f"     {note}")

    return "\n".join(lines)
