import os
import math
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from difflib import get_close_matches
from services.pinecone_store import search_pois, make_namespace
from services.grid_scorer import (
    score_grids_for_category,
    build_spatial_index,
    FACILITY_RULES,
    ALL_POI_TABLES,
  query_spatial_index
    
)
from dotenv import load_dotenv

load_dotenv()

# ── Purpose → category keyword map ───────────────────
PURPOSE_MAP = {
    "hospital":   "hospitals",    "clinic":      "hospitals",
    "school":     "schools",      "college":     "schools",
    "pharmacy":   "hospitals",    "medicine":    "hospitals",
    "restaurant": "restaurants",  "food":        "restaurants",
   
}

# ── Maps agent category names → grid_scorer FACILITY_RULES keys ──
CATEGORY_TO_RULE = {
    "hospitals":   "hospitals",
    "schools":     "schools",
    "restaurants": "restaurants",
    "businesses":  "businesses",
    "finance":     "finance",
    "recreation":  "recreation",
    "shops":       "shops",
    "tourism":     "tourism",
    "building":   "building",   
    "infrastructure": "infra_str",
    "religious": "religious",   
    
}


# ────────────────────────────────────────────────────
# SESSION
# ────────────────────────────────────────────────────

def create_session() -> dict:
    return {
        "location": None,
        "summary":  {},
        "radius":   None,
        "lat":      None,
        "lon":      None,
        "poi_data": None,
    }


def set_session(session, location, summary, radius_km,
                lat=None, lon=None, poi_data=None):
    session["location"] = location
    session["summary"]  = summary
    session["radius"]   = radius_km

    if lat:      session["lat"]      = lat
    if lon:      session["lon"]      = lon
    if poi_data: session["poi_data"] = poi_data


# ────────────────────────────────────────────────────
# CONTEXT HELPERS
# ────────────────────────────────────────────────────
def _get_poi_counts(session: dict) -> str:
    s = session.get("summary", {})
    pois = session.get("poi_data", {}).get("pois", {})

    def count(key):
        return len(pois.get(key, []))

    return (
        f"Location: {session.get('location')} ({session.get('radius')}km)\n"
        f"Buildings: {s.get('Building', 0)}\n"
        f"Businesses: {s.get('Business', 0)}\n"
        f"Finance: {s.get('Finance', 0)}\n"
        f"Food: {s.get('Food', 0)}\n"
        f"Hospitals: {count('Health Care')}\n"
        f"Schools: {count('Education')}\n"
        f"Shops: {count('Shops')}\n"
        f"Tourism: {count('Tourism')}\n"
        f"Religious: {count('Religious')}\n"
    )


def _search_nearby(query: str, session: dict) -> str:
    namespace = make_namespace(session.get("location", "default"),session.get("radius") )
    results   = search_pois(query[:200], namespace=namespace)

    if not results:
        return "No relevant places found."

    seen  = set()
    lines = []

    for r in results:
        key = (r["name"], r["category"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {r['category']}: {r['name']}")
        if len(lines) >= 8:
            break

    return "\n".join(lines)


def _get_suitability(session: dict) -> str:
    s     = session.get("summary", {})
    notes = []

    if s.get("Building",  0) > 50: notes.append("High infrastructure density")
    if s.get("Business",  0) > 40: notes.append("Strong commercial presence")
    if s.get("Finance",   0) > 50: notes.append("Good financial ecosystem")
    if s.get("Food",      0) > 50: notes.append("Active food and lifestyle zone")

    return "\n".join(f"• {n}" for n in notes) if notes else "Limited amenities"

def _get_category_pois(category: str, session: dict) -> str:
    """Extract actual POI names from session for a given category."""
    poi_data = session.get("poi_data", {})
    pois     = poi_data.get("pois", {})

    # map agent category → poi_data key
    category_key_map = {
        "hospitals":   "Health Care",
        "schools":     "Education",
        "restaurants": "Food",
        "businesses":  "Business",
        "finance":     "Finance",
        "recreation":  "Recreation",
        "shops":       "Shops",
        "tourism":     "Tourism",
        "religious":   "Religious",
    }

    key   = category_key_map.get(category)
    items = pois.get(key, []) if key else []

    if not items:
        return f"No {category} found in this area."

    lines = []
    for p in items[:20]:  # limit to 20
        name = p.get("name", "Unnamed")
        lat  = p.get("lat", "")
        lon  = p.get("lon", "")
        lines.append(f"- {name} ({lat}, {lon})")

    return "\n".join(lines)

# ────────────────────────────────────────────────────
# HAVERSINE
# ────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    R                       = 6371
    lat1, lon1, lat2, lon2  = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat                    = lat2 - lat1
    dlon                    = lon2 - lon1
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


# ────────────────────────────────────────────────────
# RUNTIME CATEGORY SCORING
# ────────────────────────────────────────────────────

def _normalize_poi_keys(poi_data: dict) -> dict:
    key_map = {
        "Health Care":    "health_care",
        "Education":      "education",
        "Transport":      "transport",
        "Food":           "food",
        "Shops":          "shops",
        "Business":       "business",
        "Tourism":        "tourism",
        "Religious":      "religious",
        "Infrastructure": "infra_str",
        "Finance":        "finance",
        "Recreation":     "recreation",
        "Building":       "building",
    }
    return {key_map.get(k, k.lower()): v for k, v in poi_data.items()}


# ────────────────────────────────────────────────────
# population for suggested location
# ───────────────────────────────────────────────────
def calculate_catchment_population(suggested_lat:  float,
                                   suggested_lon:  float,
                                   all_grids:      list[dict],
                                   poi_indexes:    dict,
                                   poi_table:      str,
                                   radius_km:      float,
                                   other_selected: list[dict]) -> tuple[int, float]:
    """
    1. Finds nearest existing facility from poi_indexes
    2. Finds nearest other suggested location
    3. Uses MINIMUM of both as catchment radius
    4. Sums population of all grids within that radius
    """

    # ── Step 1: nearest existing facility ────────────────────────
    nearest_existing = None
# poi_table = "health_care" (for hospitals)
# poi_indexes = {
#     "health_care": {(572, 1544): [Hospital_A, Hospital_B]},
#     "education":   {(572, 1546): [School_A]},
# }
# comp_index = {(572, 1544): [Hospital_A, Hospital_B]}
    comp_index = poi_indexes.get(poi_table, {})
    candidates = query_spatial_index(
                     comp_index,
                     suggested_lat,
                     suggested_lon,
                     radius_km = radius_km
                 )

    for p in candidates:
        d = haversine(suggested_lat, suggested_lon, p["lat"], p["lon"])
        if nearest_existing is None or d < nearest_existing:
            nearest_existing = d

    # print(f"      nearest existing facility: "
    #       f"{round(nearest_existing, 3) if nearest_existing else 'None'}km")

    # ── Step 2: nearest other suggested location ──────────────────
    nearest_suggested = None

    for s in other_selected:
        d = haversine(suggested_lat, suggested_lon, s["lat"], s["lon"])
        if nearest_suggested is None or d < nearest_suggested:
            nearest_suggested = d

    # print(f"      nearest suggested location: "
    #       f"{round(nearest_suggested, 3) if nearest_suggested else 'None'}km")

    # ── Step 3: pick minimum of both ─────────────────────────────
    candidates_dist = [d for d in [nearest_existing, nearest_suggested]
                       if d is not None]

    # nearest_suggested is ALWAYS available so this will never be empty
    catchment_radius = min(candidates_dist)

    # guard against 0 only
    if catchment_radius <= 0:
        catchment_radius = nearest_suggested   # ← use suggested as guard

    # print(f"      catchment_radius: {round(catchment_radius, 3)}km")

    # ── Step 4: sum all grid populations within catchment radius ──
    total_population = 0
    for g in all_grids:
        grid_lat = g.get("lat", g.get("center_lat"))
        grid_lon = g.get("lon", g.get("center_lon"))
        grid_pop = g.get("population", 0)

        if grid_lat is None or grid_lon is None:
            continue

        d = haversine(suggested_lat, suggested_lon, grid_lat, grid_lon)
        if d <= catchment_radius:
            total_population += grid_pop

    return total_population, round(catchment_radius, 3)


def get_top3_from_db(grids: list, radius_km: float,
                     category: str = None,
                     poi_data: dict = None) -> list:
    
    if not grids:
        return []

    # ← normalize keys RIGHT HERE before anything else
    normalized_grids = []
    for g in grids:
        normalized_grids.append({
            **g,
            "center_lat": g.get("center_lat", g.get("lat")),
            "center_lon": g.get("center_lon", g.get("lon")),
            "lat":        g.get("lat", g.get("center_lat")),
            "lon":        g.get("lon", g.get("center_lon")),
        })
    grids = normalized_grids

    # Score dynamically if category + poi_data provided
    poi_indexes = {}  # ← hoisted out so accessible later


# poi_indexes looks like:
# {
#     "health_care": {
#         (572, 1544): [Hospital_A, Hospital_B],
#         (573, 1545): [Hospital_C],
#     }

    if category and poi_data:
        poi_data_normalized = _normalize_poi_keys(poi_data)
        poi_indexes = {
            k: build_spatial_index(v)
            for k, v in poi_data_normalized.items()
            if isinstance(v, list) and v
        }
        rule_category = CATEGORY_TO_RULE.get(category, category)
        grids    = score_grids_for_category(grids, poi_data_normalized, poi_indexes, rule_category)
        sort_key = "normalized_score"
    else:
        sort_key = "score"

    min_km       = max(0.5, radius_km * 0.4)
    sorted_grids = sorted(grids, key=lambda x: x.get(sort_key, 0), reverse=True)

    selected = []
    for g in sorted_grids:
        if not selected:
            selected.append(g)
            continue
        too_close = any(
            haversine(g["lat"], g["lon"], s["lat"], s["lon"]) < min_km
            for s in selected
        )
        if not too_close:
            selected.append(g)
        if len(selected) == 3:
            break

    # ── get poi_table from rules for catchment population ────────
    rule_category = CATEGORY_TO_RULE.get(category, category) if category else None
    rules         = FACILITY_RULES.get(rule_category, {})     if rule_category else {}
    poi_table     = rules.get("poi_table")

    result = []
    for i, g in enumerate(selected):

        # ── other selected locations except current one ───────────
        other_selected = [s for s in selected if s != g]

        # ── catchment population calculation ─────────────────────
        if poi_table and poi_indexes:
            catchment_pop, radius_used = calculate_catchment_population(
                suggested_lat  = g["lat"],
                suggested_lon  = g["lon"],
                all_grids      = normalized_grids, 
                poi_indexes    = poi_indexes,
                poi_table      = poi_table,
                radius_km      = radius_km,
                other_selected = other_selected,    # ← other suggested locations
            )
            # print(f"   Rank {i+1} → catchment radius: {radius_used}km, "
            #       f"population: {catchment_pop}")
        else:
            catchment_pop = g.get("population", 0)  # ← fallback to single grid
        # ─────────────────────────────────────────────────────────

        result.append({
            "rank":       i + 1,
            "lat":        g["lat"],
            "lon":        g["lon"],
            "score":      g.get("normalized_score", 0),
            "population": catchment_pop,
            "label":      f"Score: {g.get('normalized_score', 0):.2f}, "
                          f"Population: {catchment_pop}",
        })

    return result


# ────────────────────────────────────────────────────
# CATEGORY DETECTION
# ────────────────────────────────────────────────────


VALID_CATEGORIES = list(CATEGORY_TO_RULE.keys())

def map_to_valid_category(cat: str) -> str | None:
    if not cat:
        return None

    cat = cat.lower().strip()

    # direct match
    if cat in VALID_CATEGORIES:
        return cat

    # fuzzy match
    match = get_close_matches(cat, VALID_CATEGORIES, n=1, cutoff=0.5)
    if match:
    
        return match[0]

    return None



def _detect_category(question: str, llm) -> str | None:
    q_lower = question.lower()

    # ── 1. Keyword match (fast path) ──
    for keyword, cat in PURPOSE_MAP.items():
        if keyword in q_lower:
            return cat

    # ── 2. LLM fallback ──
    try:
        prompt = f"""
You are a facility classifier. Only classify if the question clearly refers to a real, recognizable facility type.

Return STRICT JSON:
{{"category": "<one_of_below_or_null>"}}

Valid categories ONLY:
hospitals, schools, restaurants, businesses, finance, recreation, shops, tourism, religious, infrastructure, building

Rules:
- If the question contains a real facility type → return that category
- If the word is gibberish, made-up, or unrecognizable → return null
- If you are not confident → return null

Question: "{question}"
"""
        raw    = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        raw    = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        cat = parsed.get("category")

        # ── NEW: reject null/none responses from LLM ──
        if not cat or cat.lower() in ("null", "none", ""):
            return None

        print("LLM raw output is:", cat)
        return map_to_valid_category(cat)

    except Exception:
        return None

# ────────────────────────────────────────────────────
# MAIN AGENT
# ────────────────────────────────────────────────────

def ask_agent(question: str, session: dict) -> dict:

    question = question[:500].strip()
    if not question:
        return {"response": "Ask a valid question", "suggestions": None}

    llm = ChatGroq(
        model       = "llama-3.3-70b-versatile",
        api_key     = os.getenv("GROQ_API_KEY"),
        temperature = 0.2,
    )

    q_lower = question.lower()

    location_words = ["where", "best", "suggest", "recommend", "location", "spot"]
    intent = "LOCATION" if any(w in q_lower for w in location_words) else "ANALYSIS"

    # ── Category detection ────────────────────────────
    matched_category = _detect_category(question, llm) if intent == "LOCATION" else None

    # ── For ANALYSIS intent, also try to detect category for context ──
    if intent == "ANALYSIS":
        matched_category = _detect_category(question, llm)

    print(f"Intent={intent} | Category={matched_category}")

    # ── Dynamic scoring + top 3 ───────────────────────
    suggestions = []
    grids       = []

    if intent == "LOCATION" and matched_category and session.get("poi_data"):
        grids    = session["poi_data"].get("grids", [])
        poi_data = session["poi_data"].get("pois",  {})

        scored_grids = get_top3_from_db(
            grids     = grids,
            radius_km = session["radius"],
            category  = matched_category,
            poi_data  = poi_data,
        )

        if not scored_grids:
            return {
                "response":    (
                    f"Sorry, I don't have rules for '{matched_category}' yet. "
                    f"Try: hospitals, schools, restaurants, businesses, finance, "
                    f"recreation, shops, tourism, religious."
                ),
                "suggestions": None,
                "grids":       []
            }

        suggestions = scored_grids

    elif intent == "LOCATION" and not matched_category:
        return {
            "response":    "Please specify what type of place you're looking for "
                           "(e.g., hospital, school, restaurant).",
            "suggestions": None,
            "grids":       []
        }

    # ── Context building ──────────────────────────────
    poi_counts  = _get_poi_counts(session)
    suitability = _get_suitability(session)

    use_semantic = any(w in q_lower for w in
                       ["near", "nearby", "around", "find", "search"])
    nearby = _search_nearby(question, session) if use_semantic else \
             "Context derived from structured database."

    # ── Actual POI list for listing questions ─────────
    listing_words = ["list", "show", "all", "display", "what are", "give me"]
    wants_listing = any(w in q_lower for w in listing_words)
    poi_list_text = (
        _get_category_pois(matched_category, session)
        if wants_listing and matched_category
        else ""
    )

    # ── Memory (lightweight context) ───────────────────
    previous_q = session.get("last_question", "None")

    system_prompt = f"""
You are an expert Location Intelligence Consultant specializing in site selection and urban analysis.

IMPORTANT: Only use the data provided below. Do NOT mention any places outside this dataset.

## AREA DATA
{poi_counts}

## NEARBY INSIGHTS
{nearby}

## AREA SUITABILITY
{suitability}

## USER CONTEXT
Previous question: {previous_q}

"""

    if poi_list_text:
        system_prompt += f"\n## {matched_category.upper()} IN THIS AREA\n{poi_list_text}\n"

    if suggestions:
        system_prompt += "\n## TOP 3 RECOMMENDED LOCATIONS\n"
        for s in suggestions:
            system_prompt += (
                f"Rank {s['rank']} → {s['lat']:.5f}, {s['lon']:.5f} "
                f"(Population: {s['population']})\n"
            )

        system_prompt += """
## RESPONSE INSTRUCTIONS (VERY IMPORTANT)

- Start with a short summary (1–2 lines)
- Then explain each location clearly

Use this format:

<brief insight>

Location 1 (mention direction like North/East etc.)
- Nearby advantages
- Population coverage
- Why it is suitable

Location 2
- Same structure

Location 3
- Same structure

Guidelines:
- Keep response professional but conversational
- Use bullet points for clarity
- Highlight important insights using CAPITAL WORDS instead of bold
- Do NOT mention technical terms like "score", "grid", or backend logic
- Make response visually clean and easy to read
"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ])

    # ── Save last question (memory) ───────────────────
    session["last_question"] = question

    return {
        "response":    response.content,
        "suggestions": suggestions,
        "grids":       grids
    }