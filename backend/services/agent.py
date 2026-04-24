import os
import math
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from services.pinecone_store import search_pois, make_namespace
from services.grid_scorer import (
    score_grids_for_category,
    build_spatial_index,
    FACILITY_RULES,
    ALL_POI_TABLES,
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
    "gym":        "business",   "fitness":    "business",
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
    "bus_stops":   "infra_str",   # fallback — closest rule
    "fuel_stations": "infra_str",
    "pharmacies":  "hospitals", 
    "GYM":"businesses"# fallback — closest rule
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
    return (
        f"Location: {session.get('location')} ({session.get('radius')}km)\n"
        f"Buildings: {s.get('Building', 0)}\n"
        f"Businesses: {s.get('Business', 0)}\n"
        f"Finance: {s.get('Finance', 0)}\n"
        f"Food: {s.get('Food', 0)}"
    )


def _search_nearby(query: str, session: dict) -> str:
    namespace = make_namespace(session.get("location", "default"))
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



def get_top3_from_db(grids: list, radius_km: float,
                     category: str = None,
                     poi_data: dict = None) -> list:
    
    
    if not grids:
        return []

    # Score dynamically if category + poi_data provided
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

    min_km       = max(0.3, radius_km * 0.25)
    sorted_grids = sorted(grids, key=lambda x: x.get(sort_key, 0), reverse=True)
    print(f"min_km={min_km}, total grids={len(grids)}, score range: {sorted_grids[-1].get('dynamic_score')} - {sorted_grids[0].get('dynamic_score')}")

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

    return [
        {
            "rank":             i + 1,
            "lat":              g["lat"],
            "lon":              g["lon"],
            "score":            g.get("normalized_score" ,0),
            "population":       g.get("population", 0),
            "label":            f"Score: {g.get('normalized_score', 0):.2f}, "
                            f"Population: {g.get('population', 0)}",
        }
        for i, g in enumerate(selected)
    ]


# ────────────────────────────────────────────────────
# CATEGORY DETECTION
# ────────────────────────────────────────────────────

def _detect_category(question: str, llm) -> str | None:
    q_lower = question.lower()

    for keyword, cat in PURPOSE_MAP.items():
        if keyword in q_lower:
            return cat

    # LLM fallback
    try:
        prompt = f"""
Classify the facility type from this question.
Return ONLY valid JSON, no extra text:
{{"category": "hospitals|schools|pharmacies|restaurants|fuel_stations|bus_stops|businesses|finance|recreation|shops|tourism|NONE"}}

Question: "{question}"
"""
        raw    = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        raw    = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        cat    = parsed.get("category", "NONE")

        valid = set(PURPOSE_MAP.values()) | {
            "businesses", "finance", "recreation", "shops", "tourism"
        }
        return cat if cat in valid else None

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

    location_words = ["where", "best", "suggest", "recommend",
                      "open", "start", "location", "site", "spot"]
    intent = "LOCATION" if any(w in q_lower for w in location_words) else "ANALYSIS"

    # ── Category detection ────────────────────────────
    matched_category = _detect_category(question, llm) if intent == "LOCATION" else None

    print(f"Intent={intent} | Category={matched_category}")

    # ── Dynamic scoring + top 3 ───────────────────────
    suggestions = []

    if intent == "LOCATION" and session.get("poi_data"):
        grids    = session["poi_data"].get("grids", [])
        poi_data = session["poi_data"].get("pois",  {})

        suggestions = get_top3_from_db(
            grids     = grids,
            radius_km = session["radius"],
            category  = matched_category,
            poi_data  = poi_data,
        )

    # ── Context building ──────────────────────────────
    poi_counts  = _get_poi_counts(session)
    suitability = _get_suitability(session)

    use_semantic = any(w in q_lower for w in
                       ["near", "nearby", "around", "find", "search"])
    nearby = _search_nearby(question, session) if use_semantic else \
             "Context derived from structured database."

    system_prompt = f"""
You are a GIS expert analyzing real estate and facility placement.

## AREA DATA
{poi_counts}

## NEARBY
{nearby}

## SUITABILITY
{suitability}
"""

    if suggestions:
        system_prompt += "\n## TOP 3 RECOMMENDED LOCATIONS\n"
        for s in suggestions:
            system_prompt += (
                f"Rank {s['rank']} → {s['lat']:.5f}, {s['lon']:.5f} "
                f"(Score: {s['score']:.2f}, Population: {s['population']})\n"
            )
        system_prompt += """
## RESPONSE INSTRUCTIONS
- Describe all 3 locations with general direction (north/south/east/west)
- Mention population figures
- Explain why each location suits the requested facility type
- Do NOT mention scores or technical grid names
- Keep response natural and conversational
"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ])

    return {
        "response":    response.content,
        "suggestions": suggestions,
    }










# import os
# import math
# from langchain_groq import ChatGroq
# from langchain_core.messages import HumanMessage, SystemMessage
# from services.pinecone_store import search_pois, make_namespace
# from dotenv import load_dotenv

# load_dotenv()

# # ── Purpose → category keyword map ───────────────────
# PURPOSE_MAP = {
#     "hospital":   "hospitals",    "clinic":      "hospitals",
#     "school":     "schools",      "college":     "schools",
#     "pharmacy":   "pharmacies",   "medicine":    "pharmacies",
#     "restaurant": "restaurants",  "food":        "restaurants",
#     "fuel":       "fuel_stations","petrol":      "fuel_stations",
#     "gas":        "fuel_stations","station":     "fuel_stations",
#     "bus":        "bus_stops",    "stop":        "bus_stops",
#     "transport":  "bus_stops",    "transit":     "bus_stops",
# }

# # ────────────────────────────────────────────────────
# # SESSION
# # ────────────────────────────────────────────────────

# def create_session() -> dict:
#     return {
#         "location": None,
#         "summary": {},
#         "radius": None,
#         "lat": None,
#         "lon": None,
#         "poi_data": None,
#     }


# def set_session(session, location, summary, radius_km, lat=None, lon=None, poi_data=None):
#     session["location"] = location
#     session["summary"] = summary
#     session["radius"] = radius_km

#     if lat: session["lat"] = lat
#     if lon: session["lon"] = lon
#     if poi_data: session["poi_data"] = poi_data


# # ────────────────────────────────────────────────────
# # CONTEXT HELPERS
# # ────────────────────────────────────────────────────


# def _get_poi_counts(session: dict) -> str:
#     s = session.get("summary", {})

#     return (
#         f"Location: {session.get('location')} ({session.get('radius')}km)\n"
#         f"Buildings: {s.get('Building', 0)}\n"
#         f"Businesses: {s.get('Business', 0)}\n"
#         f"Finance: {s.get('Finance', 0)}\n"
#         f"Food: {s.get('Food', 0)}"
#     )


# #  IMPROVED: controlled Pinecone usage (no duplicates)
# def _search_nearby(query: str, session: dict) -> str:
#     namespace = make_namespace(session.get("location", "default"))
#     results = search_pois(query[:200], namespace=namespace)

#     if not results:
#         return "No relevant places found."

#     seen = set()
#     lines = []

#     for r in results:
#         key = (r["name"], r["category"])
#         if key in seen:
#             continue
#         seen.add(key)

#         lines.append(f"- {r['category']}: {r['name']}")

#         if len(lines) >= 8:
#             break

#     return "\n".join(lines)


# #  FIXED: aligned with your summary keys
# def _get_suitability(session: dict) -> str:
#     s = session.get("summary", {})
#     notes = []

#     if s.get("Building", 0) > 50:
#         notes.append("High infrastructure density")
#     if s.get("Business", 0) > 40:
#         notes.append("Strong commercial presence")
#     if s.get("Finance", 0) > 50:
#         notes.append("Good financial ecosystem")
#     if s.get("Food", 0) > 50:
#         notes.append("Active food and lifestyle zone")

#     return "\n".join(f"• {n}" for n in notes) if notes else "Limited amenities"


# # ────────────────────────────────────────────────────
# # TOP 3 GRID LOGIC (FIXED)
# # ────────────────────────────────────────────────────
# def haversine(lat1, lon1, lat2, lon2):
#     R = 6371  # Earth radius in km

#     lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

#     dlat = lat2 - lat1
#     dlon = lon2 - lon1

#     a = (
#         math.sin(dlat / 2) ** 2 +
#         math.cos(lat1) * math.cos(lat2) *
#         math.sin(dlon / 2) ** 2
#     )

#     c = 2 * math.asin(math.sqrt(a))

#     return R * c


# def get_top3_from_db(grids, radius_km):
#     if not grids:
#         return []

#     min_km = max(0.3, radius_km * 0.25)

#     sorted_grids = sorted(grids, key=lambda x: x["score"], reverse=True)

#     selected = []

#     for g in sorted_grids:
#         if not selected:
#             selected.append(g)
#             continue

#         too_close = False
#         for s in selected:
#             if haversine(g["lat"], g["lon"], s["lat"], s["lon"]) < min_km:
#                 too_close = True
#                 break

#         if not too_close:
#             selected.append(g)

#         if len(selected) == 3:
#             break

#     return [
#         {
#             "rank": i + 1,
#             "lat": g["lat"],
#             "lon": g["lon"],
#             "score": g["score"],
#             "population": g["population"],
#             "label": f"Score: {g['score']}, Population: {g['population']}"
#         }
#         for i, g in enumerate(selected)
#     ]

# # ────────────────────────────────────────────────────
# # MAIN AGENT
# # ────────────────────────────────────────────────────

# def ask_agent(question: str, session: dict) -> dict:

#     question = question[:500].strip()
#     if not question:
#         return {"response": "Ask a valid question", "suggestions": None}

#     llm = ChatGroq(
#         model="llama-3.3-70b-versatile",
#         api_key=os.getenv("GROQ_API_KEY"),
#         temperature=0.2
#     )

#     q_lower = question.lower()

#     # ── intent detection
#     intent = "LOCATION" if any(w in q_lower for w in ["where", "best", "suggest"]) else "ANALYSIS"

#     # ───────────────────────────────
#     # ✅ FIXED: correct grids extraction
#     # ───────────────────────────────
#     suggestions = []

#     if intent == "LOCATION" and session.get("poi_data"):
#         grids = session["poi_data"].get("grids", [])
#         suggestions = get_top3_from_db(grids, session["radius"])

#     # ───────────────────────────────
#     # CONTEXT
#     # ───────────────────────────────
#     poi_counts = _get_poi_counts(session)
#     suitability = _get_suitability(session)

#     # ✅ smart Pinecone usage (only when needed)
#     use_semantic = any(w in q_lower for w in ["near", "nearby", "around", "find", "search"])

#     if use_semantic:
#         nearby = _search_nearby(question, session)
#     else:
#         nearby = "Context derived from structured database."

#     system_prompt = f"""
# You are a GIS expert analyzing real estate and facility placement.

# ## AREA DATA
# {poi_counts}

# ## NEARBY
# {nearby}

# ## SUITABILITY
# {suitability}
# """

#     # ── ADD TOP 3 LOCATIONS
#     if suggestions:
#         system_prompt += "\n## TOP 3 LOCATIONS\n"
#         for s in suggestions:
#             system_prompt += (
#                 f"Rank {s['rank']} → {s['lat']}, {s['lon']} "
#                 f"(Score: {s['score']}, Pop: {s['population']})\n"
#             )

#     # ───────────────────────────────
#     # LLM CALL
#     # ───────────────────────────────
#     response = llm.invoke([
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=question)
#     ])

#     return {
#         "response": response.content,
#         "suggestions": suggestions
#     }