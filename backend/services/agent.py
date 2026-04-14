import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from services.pinecone_store import search_pois, make_namespace
from services.grid_analyzer import (
    create_grid,
    assign_pois_to_grid,
    analyze_full_grid,
    grid_to_text,
    get_top3_cells,      # ✅ new import
    haversine
)
from dotenv import load_dotenv

load_dotenv()

# ── Purpose → category keyword map ───────────────────
PURPOSE_MAP = {
    "hospital":   "hospitals",    "clinic":      "hospitals",
    "school":     "schools",      "college":     "schools",
    "pharmacy":   "pharmacies",   "medicine":    "pharmacies",
    "restaurant": "restaurants",  "food":        "restaurants",
    "fuel":       "fuel_stations","petrol":      "fuel_stations",
    "gas":        "fuel_stations","station":     "fuel_stations",
    "bus":        "bus_stops",    "stop":        "bus_stops",
    "transport":  "bus_stops",    "transit":     "bus_stops",
}

# ── Rank labels and icons ─────────────────────────────
RANK_LABELS = {
    1: "Best location",
    2: "2nd best location",
    3: "3rd best location",
}


# ────────────────────────────────────────────────────
# SESSION
# ────────────────────────────────────────────────────

def create_session() -> dict:
    """Returns a fresh empty session for a new user."""
    return {
        "location":       None,
        "summary":        {},
        "radius":         None,
        "lat":            None,
        "lon":            None,
        "poi_data":       None,
        "grid_cache":     None,
        "analysis_cache": {},
    }


def set_session(session: dict,
                location: str,
                summary: dict,
                radius_km: float,
                lat: float     = None,
                lon: float     = None,
                poi_data: dict = None):
    """
    Populates session dict with location data.
    All state stored in passed-in dict —
    nothing written to module-level variables.
    """
    session["location"]       = location
    session["summary"]        = summary
    session["radius"]         = radius_km
    session["grid_cache"]     = None
    session["analysis_cache"] = {}

    if lat      is not None: session["lat"]      = lat
    if lon      is not None: session["lon"]      = lon
    if poi_data is not None: session["poi_data"] = poi_data

    if lat is not None and lon is not None and poi_data:
        _build_grid_cache(session)
    else:
        print("⚠️ Grid cache skipped — missing lat/lon/poi_data")


# ── Grid Cache ────────────────────────────────────────

def _build_grid_cache(session: dict):
    try:
        required = ["lat", "lon", "poi_data", "radius"]
        missing  = [k for k in required if session.get(k) is None]
        if missing:
            print(f"⚠️ Grid cache skipped — missing keys: {missing}")
            return

        cells = create_grid(
            center_lat = session["lat"],
            center_lon = session["lon"],
            radius_km  = session["radius"],
            grid_size  = 5
        )

        if not cells:
            print("⚠️ No valid grid cells found")
            return

        cells = assign_pois_to_grid(cells, session["poi_data"])
        session["grid_cache"] = {
            "cells":    cells,
            "poi_data": session["poi_data"]
        }
        print(f"✅ Grid cache built with {len(cells)} cells")

    except Exception as e:
        print(f"🔴 Grid cache error: {e}")
        import traceback
        traceback.print_exc()
        session["grid_cache"] = None


# ── Context Builders ──────────────────────────────────

def _get_poi_counts(session: dict) -> str:
    if not session.get("summary"):
        return "No location analyzed yet."
    s = session["summary"]
    return (
        f"    Location        : {session.get('location')} "
        f"({session.get('radius')}km radius)\n"
        f"    Human Hospitals : {s.get('human_hospitals', 0)}\n"
        f"    Vet Hospitals   : {s.get('vet_hospitals', 0)}\n"
        f"    Bus Stops       : {s.get('bus_stops', 0)}\n"
        f"    Fuel Stations   : {s.get('fuel_stations', 0)}\n"
        f"    Schools         : {s.get('schools', 0)}\n"
        f"    Restaurants     : {s.get('restaurants', 0)}\n"
        f"    Pharmacies      : {s.get('pharmacies', 0)}\n"
        f"    Buildings       : {s.get('buildings', 0)}"
    )


def _search_nearby(query: str, session: dict) -> str:
    """
    Passes namespace explicitly — safe for concurrent users.
    """
    # ✅ Vulnerability fix — sanitize query before passing to search
    safe_query = query[:200].strip()
    namespace  = make_namespace(session.get("location", "default"))
    results    = search_pois(safe_query, namespace=namespace)
    if not results:
        return "No relevant places found."
    return "\n".join(
        f"- {r['category'].replace('_', ' ')}: {r['name']}"
        for r in results
    )


def _get_suitability(session: dict) -> str:
    if not session.get("summary"):
        return "No location analyzed yet."
    s     = session["summary"]
    notes = []
    if s.get("human_hospitals", 0) > 3: notes.append("Good healthcare access")
    if s.get("schools", 0) > 3:         notes.append("Good education infrastructure")
    if s.get("bus_stops", 0) > 10:      notes.append("Excellent public transport")
    if s.get("restaurants", 0) > 10:    notes.append("Active commercial area")
    if not notes:                        notes.append("Limited amenities in this area")
    return "\n".join(f"• {n}" for n in notes)


# ── Suggestion Point For One Cell ────────────────────

def _get_suggestion_for_cell(cell: dict,
                              poi_data: dict,
                              category: str,
                              session: dict,
                              rank: int = 1) -> dict:
    """
    Finds most precise gap point inside a cell.
    Samples 25 points and picks the one furthest
    from all existing facilities.
    rank = 1, 2, or 3 — determines label.
    """
    existing_pois = poi_data.get(category, [])
    label_prefix  = RANK_LABELS.get(rank, f"Option {rank}")

    center_lat = session["lat"]
    center_lon = session["lon"]
    radius_km  = session["radius"]

    if not existing_pois:
        return {
            "rank":  rank,
            "lat":   cell["center_lat"],
            "lon":   cell["center_lon"],
            "label": f"{label_prefix} — no existing {category} nearby",
            "notes": cell.get("notes", []),
            "score": cell.get("score", 0),
        }

    north    = cell["north"]
    south    = cell["south"]
    west     = cell["west"]
    east     = cell["east"]

    best_point    = None
    best_min_dist = -1
    lat_step      = (north - south) / 6
    lon_step      = (east  - west)  / 6

    for i in range(1, 6):
        for j in range(1, 6):
            sample_lat = south + (i * lat_step)
            sample_lon = west  + (j * lon_step)

            # Skip points outside the main radius circle
            if haversine(center_lat, center_lon,
                         sample_lat, sample_lon) > radius_km:
                continue

            min_dist = min(
                haversine(sample_lat, sample_lon,
                          p["lat"], p["lon"])
                for p in existing_pois
            )

            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_point    = (sample_lat, sample_lon)

    # Fallback to cell center if no valid point found
    if best_point is None:
        best_point    = (cell["center_lat"], cell["center_lon"])
        best_min_dist = 0.0
        print(f"⚠️ Rank {rank} fallback to cell center")

    # Final safety check — must be inside radius
    if haversine(center_lat, center_lon,
                 best_point[0], best_point[1]) > radius_km:
        best_point = (cell["center_lat"], cell["center_lon"])
        print(f"⚠️ Rank {rank} point outside radius — using cell center")

    return {
        "rank":  rank,
        "lat":   best_point[0],
        "lon":   best_point[1],
        "label": f"{label_prefix} — {best_min_dist:.1f}km from nearest {category[:-1]}",
        "notes": cell.get("notes", []),
        "score": cell.get("score", 0),
    }


# ── Top 3 Suggestions ─────────────────────────────────

def _get_top3_suggestions(analysis: dict,
                           poi_data: dict,
                           category: str,
                           session: dict) -> list:
    """
    Builds suggestion pins for top 3 cells.
    Returns list of 3 dicts with rank, lat, lon, label, notes.
    """
    top3_cells  = get_top3_cells(analysis)
    suggestions = []

    for i, cell in enumerate(top3_cells):
        suggestion = _get_suggestion_for_cell(
            cell     = cell,
            poi_data = poi_data,
            category = category,
            session  = session,
            rank     = i + 1
        )
        suggestions.append(suggestion)
        print(f"📍 Rank {i+1}: {suggestion['lat']:.4f}, "
              f"{suggestion['lon']:.4f} — {suggestion['label']}")

    return suggestions


# ── Grid Context ──────────────────────────────────────

def _get_grid_context(question: str,
                      session: dict,
                      category: str = None) -> tuple:
    """
    Returns (grid_text, suggestions_list) from cached grid.
    suggestions_list contains top 3 ranked suggestions.
    """
    cache = session.get("grid_cache")
    if not cache:
        print("⚠️ No grid cache available")
        return None, None

    try:
        cells    = cache["cells"]
        poi_data = cache["poi_data"]

        # Per-category analysis cache
        analysis_cache = session.get("analysis_cache", {})
        if category and category in analysis_cache:
            analysis = analysis_cache[category]
            print(f"✅ Using cached analysis for: {category}")
        else:
            analysis = analyze_full_grid(
                cells      = cells,
                poi_data   = poi_data,
                purpose    = question,
                center_lat = session["lat"],
                center_lon = session["lon"],
                radius_km  = session["radius"]
            )
            if category:
                session.setdefault("analysis_cache", {})[category] = analysis

        grid_text   = grid_to_text(analysis)
        category    = analysis["category"]

        # ✅ Get top 3 suggestions instead of just 1
        suggestions = _get_top3_suggestions(
            analysis = analysis,
            poi_data = poi_data,
            category = category,
            session  = session
        )

        return grid_text, suggestions

    except Exception as e:
        print(f"🔴 Grid context error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


# ── Main Agent Entry Point ────────────────────────────

def ask_agent(question: str, session: dict) -> dict:
    """
    session passed in per-request — never read from global state.
    Returns response text + list of top 3 suggestions.
    """

    # ✅ Vulnerability fix — limit question length
    question = question[:500].strip()
    if not question:
        return {
            "response":    "Please ask a question.",
            "suggestions": None
        }

    llm = ChatGroq(
        model       = "llama-3.3-70b-versatile",
        api_key     = os.getenv("GROQ_API_KEY"),
        temperature = 0.2
    )

    # ─────────────────────────────────────────────
    # STEP 1: INTENT + CATEGORY DETECTION
    # ─────────────────────────────────────────────
    q_lower          = question.lower()
    matched_category = None

    for keyword, cat in PURPOSE_MAP.items():
        if keyword in q_lower:
            matched_category = cat
            break

    location_words = [
        "where", "suggest", "recommend", "best place",
        "open", "start", "location", "site", "spot"
    ]
    intent = "LOCATION" if any(w in q_lower for w in location_words) else "ANALYSIS"

    # LLM fallback only when keyword matching finds nothing
    if not matched_category:
        try:
            intent_prompt = f"""
Classify the user question into intent and category.

Intent options:
- LOCATION → user wants best place suggestion
- ANALYSIS → user wants evaluation only

Category options:
- hospitals
- schools
- pharmacies
- restaurants
- fuel_stations
- bus_stops
- NONE (if no facility type mentioned)

Rules:
- Transport/connectivity → bus_stops
- If unclear → NONE

Return ONLY valid JSON with no extra text:
{{"intent": "LOCATION or ANALYSIS", "category": "category name or NONE"}}

Question: "{question}"
"""
            # ✅ Vulnerability fix — validate LLM JSON output safely
            raw = llm.invoke([
                HumanMessage(content=intent_prompt)
            ]).content.strip()

            # Strip markdown code fences if present
            raw = raw.replace("```json", "").replace("```", "").strip()

            parsed           = json.loads(raw)
            llm_intent       = parsed.get("intent", "")
            llm_category     = parsed.get("category", "")

            # Validate values are expected strings
            if llm_intent in ("LOCATION", "ANALYSIS"):
                intent = llm_intent

            if llm_category and llm_category != "NONE":
                valid_categories = {
                    "hospitals", "schools", "pharmacies",
                    "restaurants", "fuel_stations", "bus_stops",
                    "vet_hospitals"
                }
                if llm_category in valid_categories:
                    matched_category = llm_category

        except json.JSONDecodeError:
            print("⚠️ LLM returned invalid JSON — using keyword defaults")
        except Exception as e:
            print(f"⚠️ Intent detection error: {e}")
            intent           = "ANALYSIS"
            matched_category = None

    print(f"Intent={intent} | Category={matched_category}")

    # ─────────────────────────────────────────────
    # STEP 2: GRID ANALYSIS (ONLY IF NEEDED)
    # ─────────────────────────────────────────────
    suggestions = None
    grid_text   = ""

    if intent == "LOCATION" and matched_category:
        try:
            grid_text, suggestions = _get_grid_context(
                question, session, matched_category
            )
        except Exception as e:
            print(f"🔴 Grid analysis error: {e}")

    # ─────────────────────────────────────────────
    # STEP 3: CONTEXT BUILDING
    # ─────────────────────────────────────────────
    poi_counts  = _get_poi_counts(session)
    nearby      = _search_nearby(question, session)
    suitability = _get_suitability(session)

    system_prompt = f"""You are an expert GIS location analyst helping users
find the best locations to open new facilities based on real spatial data.

## AREA SUMMARY
{poi_counts}

## NEARBY PLACES
{nearby}

## AREA SUITABILITY
{suitability}
"""

    if grid_text:
        system_prompt += f"\n## GRID ANALYSIS\n{grid_text}\n"

    if suggestions and len(suggestions) >= 1:
        # Build location block for all 3 suggestions
        rank_icons   = {1: "🥇", 2: "🥈", 3: "🥉"}
        location_lines = []
        for s in suggestions:
            location_lines.append(
                f"{rank_icons.get(s['rank'], '📍')} "
                f"Rank {s['rank']}: {s['lat']:.5f}, {s['lon']:.5f} "
                f"— {s['label']}"
            )

        system_prompt += f"""
## TOP 3 RECOMMENDED LOCATIONS
{chr(10).join(location_lines)}

## RESPONSE INSTRUCTIONS
- Describe ALL 3 recommended locations
- For each mention general direction (north/south/east/west)
- Give actual population numbers from grid data
- Explain WHY each location is ranked the way it is
- Do NOT mention zone names like A1 B2
- Do NOT mention grid scores or normalized numbers
- Keep response natural and conversational
- End your response with:
  🥇 Best:   {suggestions[0]['lat']:.4f}, {suggestions[0]['lon']:.4f}
  🥈 2nd:    {suggestions[1]['lat']:.4f}, {suggestions[1]['lon']:.4f}
  🥉 3rd:    {suggestions[2]['lat']:.4f}, {suggestions[2]['lon']:.4f}
"""

    # ─────────────────────────────────────────────
    # STEP 4: FINAL RESPONSE
    # ─────────────────────────────────────────────
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ])

    return {
        "response":    response.content,
        "suggestions": suggestions   # ✅ list of 3, not single
    }