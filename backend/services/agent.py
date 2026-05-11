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
    SUBCATEGORY_RULES,
  query_spatial_index
    
)
from dotenv import load_dotenv

load_dotenv()

# ── ADD CATEGORY_SYNONYMS INSTEAD ──

CATEGORY_SYNONYMS: dict[str, list[str]] = {
    "hospitals":      ["Dispensary", "Nursing Home", "Diagnostic Centre", "Ambulance",
                       "Clinic", "Poly Clinic", "24 Hours Chemist", "Veterinary Clinic","Hospital","Blood Bank"],
    
    "education":      ["University Study Centre", "institute", "college", "Vocational Institute",
                       "Pre School","Hostel","Library","school","Computer Education","university"],
    
    "finance":        ["Financial Service","Insurance Service","atm", "bank"],
    
    "recreation":     ["park", "Cultural Centre", "Locality", "Residential Area", "Playground","Gymnasium", 
                       "Banquet Hall", "Pool", "Club", "Lake", "Cinema Hall", "Sport Club", "Stadium","Water Park"],
    
    "restaurants":    ["Tea Stall", "Fast Food", "Bakery", "Bar", "Juice Bar",
                       "Ice Cream Parlour", "Restaurant", "Soda Shop","Dairy"],
    
    "religious":      ["temple", "Gurdwara", "Mosque","Mausoleum","Religious Society", "Prayer Hall","Church"],
    
    "shops":          ["Jewellery Shop", "Vegetable Shop", "Ration Shop", "Courier", "Commercial Complex", "Gift Shop", "Music Shop", "Cyber Cafe",
                       "Mobile Shop","Sport Shop","Chemist Shop","Photo Lab","Multiplex","Footwear Shop","Book Shop","Super Market","Tailor Shop","White Goods Shop","Apparel Shop","Business","Laundry",
                       "Hyper Market","Shopping Centre","LPG Shop","Auto Dealer","Handloom Shop","Boutique","Showroom","Computer Shop","Wine Shop","Professional Service","Stationery Shop","Beauty Parlour","Confectionery Shop",
                       "Local Shopping Centre","Furniture Shop"],
    
    "tourism":        ["Art Gallery", "Travel Service", "Statue", "Zoo", "Tourist Information",
                       "Historical Place", "Guest House","Museum","Hotel"],
    
    "businesses":     ["Airlines Office", "industry", "Real Estate","Company"],
    
    "infrastructure": ["Bridge","CNG Station","Telegraph Office","petrol pump","Fire Station","Auditorium","Graveyard","Post Office","Flyover",
                       "PTO","Gas Station","Government Office","Court","BTS Tower","Telephone Office","PCR","Overhead Water Tank","Crematorium",
                       "Public Utility","Telephone Exchange","Jail","Parking Place","GPO","police station", ],
    
    "building":       ["IT Park", "Embassy", "Apartment", "Society", "Industrial Complex","Landmark",
                       "Mall","Building","Bungalow","Organisation","Office"],
    
    "transport":       ["Road Junction","Rapid Metro Station","Bus Terminal","Taxi Stand","Airport","Bus Stand","Metro Station","Railway Station"
                        "Railway Reservation"]
}

# ── Maps agent category names → grid_scorer FACILITY_RULES keys ──
CATEGORY_TO_RULE = {
    "hospitals":   "hospitals",
    "education":    "education",
    "restaurants": "restaurants",
    "businesses":  "businesses",
    "finance":     "finance",
    "recreation":  "recreation",
    "shops":       "shops",
    "tourism":     "tourism",
    "building":   "building",   
    "infrastructure": "infra_str",
    "religious": "religious",  
    "transport":"transport" 
    
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



def _get_suitability(session: dict) -> str:
    s     = session.get("summary", {})
    notes = []

    if s.get("Building",  0) > 50: notes.append("High infrastructure density")
    if s.get("Business",  0) > 40: notes.append("Strong commercial presence")
    if s.get("Finance",   0) > 50: notes.append("Good financial ecosystem")
    if s.get("Food",      0) > 50: notes.append("Active food and lifestyle zone")

    return "\n".join(f"• {n}" for n in notes) if notes else "Limited amenities"


def _get_category_pois(category: str, session: dict, keyword: str = None) -> str:
    poi_data = session.get("poi_data", {})
    pois     = poi_data.get("pois", {})

    category_key_map = {
        "hospitals":      "Health Care",
        "education":      "Education",
        "restaurants":    "Food",
        "businesses":     "Business",
        "finance":        "Finance",
        "recreation":     "Recreation",
        "shops":          "Shops",
        "tourism":        "Tourism",
        "religious":      "Religious",
        "infrastructure": "Infrastructure",
        "building":       "Building",
    }

    key   = category_key_map.get(category)
    items = pois.get(key, []) if key else []

    if keyword:
        keyword = keyword.lower().strip()
        items = [
            p for p in items
            if (p.get("sub_category") or "").lower().strip() == keyword
        ]

    print(f"Total POIs found: {len(items)}")

    if not items:
        return f"__NONE_FOUND__:{keyword or category}"

    lines = []
    for i, p in enumerate(items, 1):  # ✅ NO LIMIT
        name = p.get("name", "Unnamed")
        lat  = p.get("lat", "")
        lon  = p.get("lon", "")
        lines.append(f"{i}. {name} ({lat}, {lon})")

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

def calculate_catchment_population(
    suggested_lat:  float,
    suggested_lon:  float,
    all_grids:      list[dict],
    poi_indexes:    dict,
    poi_table:      str,
    radius_km:      float,
    category:       str = None,
) -> tuple[int, float]:

    print(f"category is: '{poi_table}' and sub category is '{category}'")

    # ─────────────────────────────────────────────────────────────
    # Step 1: Find nearest EXISTING same-type facility within radius
    # ─────────────────────────────────────────────────────────────
    nearest_existing_dist = None
    nearest_existing_poi  = None

    comp_index = poi_indexes.get(poi_table, {})

    candidates = query_spatial_index(
        comp_index,
        suggested_lat,
        suggested_lon,
        radius_km=radius_km
    )

    # ── Filter same subtype only ─────────────────────────────────
    filtered_candidates = candidates

    if category:

        category_lower = category.lower().strip()

        filtered_candidates = [
            p for p in candidates
            if (
                category_lower in (
                    (p.get("sub_category") or "").lower()
                )
                or
                category_lower in (
                    (p.get("name") or "").lower()
                )
            )
        ]

    # ── Use filtered if available, else fall back to all candidates
    search_pool = (
        filtered_candidates
        if filtered_candidates
        else candidates
    )

    for p in search_pool:

        p_lat = p.get("lat")
        p_lon = p.get("lon")

        if p_lat is None or p_lon is None:
            continue

        d = haversine(
            suggested_lat,
            suggested_lon,
            p_lat,
            p_lon
        )

        if (
            nearest_existing_dist is None
            or d < nearest_existing_dist
        ):
            nearest_existing_dist = d
            nearest_existing_poi  = p

    # ─────────────────────────────────────────────────────────────
    # Step 2: Determine catchment radius
    # If nearest existing found → use that distance
    # If nothing found within radius → use full selected radius
    # ─────────────────────────────────────────────────────────────
    if nearest_existing_dist is not None:
        catchment_radius = nearest_existing_dist
    else:
        catchment_radius = radius_km

    # ─────────────────────────────────────────────────────────────
    # Step 3: Count all grids within catchment radius
    # All grids inside = potential customers, no ownership check
    # ─────────────────────────────────────────────────────────────
    total_population = 0
    grids_inside     = 0
    grids_skipped    = 0

    for g in all_grids:

        grid_lat = g.get("center_lat") or g.get("lat")
        grid_lon = g.get("center_lon") or g.get("lon")
        grid_pop = g.get("population", 0)

        if grid_lat is None or grid_lon is None:
            grids_skipped += 1
            continue

        dist_to_suggested = haversine(
            suggested_lat,
            suggested_lon,
            grid_lat,
            grid_lon
        )

        if dist_to_suggested <= catchment_radius:
            total_population += grid_pop
            grids_inside     += 1

    # ─────────────────────────────────────────────────────────────
    # Debug logs
    # ─────────────────────────────────────────────────────────────
    print(
        f"[catchment] "
        f"lat={suggested_lat:.4f} "
        f"lon={suggested_lon:.4f} | "
        f"filtered_candidates={len(filtered_candidates)} | "
        f"nearest_existing={nearest_existing_dist} | "
        f"catchment_radius={catchment_radius} | "
        f"grids_inside={grids_inside} | "
        f"grids_skipped={grids_skipped} | "
        f"total_pop={total_population}"
    )

    return total_population, round(catchment_radius, 3)

def get_top3_from_db(grids:      list,
                     radius_km:  float,
                     category:   str  = None,
                     poi_data:   dict = None,
                     poi_filter: list = None,
                     rules:      dict = None,
                     session:    dict = None) -> list:

    if not grids:
        return []

    # ── Session center coords ─────────────────────────────────────
    center_lat = session.get("lat") if session else None
    center_lon = session.get("lon") if session else None

    # ── Normalize grid keys + inject area center ──────────────────
    normalized_grids = []

    for g in grids:
        normalized_grids.append({
            **g,
            "center_lat":      g.get("center_lat", g.get("lat")),
            "center_lon":      g.get("center_lon", g.get("lon")),
            "lat":             g.get("lat", g.get("center_lat")),
            "lon":             g.get("lon", g.get("center_lon")),
            "area_center_lat": center_lat,
            "area_center_lon": center_lon,
            "area_radius_km":  radius_km,
        })

    grids = normalized_grids

    # ── Score grids ───────────────────────────────────────────────
    poi_indexes = {}

    if category and poi_data:

        poi_data_normalized = _normalize_poi_keys(poi_data)

        poi_indexes = {
            k: build_spatial_index(v)
            for k, v in poi_data_normalized.items()
            if isinstance(v, list) and v
        }

        grids = score_grids_for_category(
            grids,
            poi_data_normalized,
            poi_indexes,
            category,
            poi_filter=poi_filter,
            rules=rules,
        )

        sort_key = "normalized_score"

    else:
        sort_key = "score"

    # ── Sort by score descending ──────────────────────────────────
    sorted_grids = sorted(
        grids,
        key=lambda x: x.get(sort_key, 0),
        reverse=True
    )

    # ── Simple greedy selection — best score wins, just maintain spacing ──
    spacing_km = rules.get("min_dist_km", 0.5) * 0.4 if rules else 0.5
    min_km     = max(0.3, min(spacing_km, radius_km * 0.2))

    selected = []

    for g in sorted_grids:

        if not selected:
            selected.append(g)
            continue

        too_close = any(
            haversine(
                g["lat"],
                g["lon"],
                s["lat"],
                s["lon"]
            ) < min_km
            for s in selected
        )

        if not too_close:
            selected.append(g)

        if len(selected) == 3:
            break

    # ── Fallback: if spacing too strict and less than 3 found, relax it ──
    if len(selected) < 3:

        relaxed_min_km = min_km * 0.5

        for g in sorted_grids:

            if g not in selected:

                too_close = any(
                    haversine(
                        g["lat"],
                        g["lon"],
                        s["lat"],
                        s["lon"]
                    ) < relaxed_min_km
                    for s in selected
                )

                if not too_close:
                    selected.append(g)

            if len(selected) == 3:
                break

    # ── get poi_table from rules for catchment population ─────────
    poi_table = rules.get("poi_table") if rules else None

    # ── Build result ──────────────────────────────────────────────
    result = []

    for i, g in enumerate(selected):

        if poi_table and poi_indexes:

            catchment_pop, radius_used = calculate_catchment_population(
                suggested_lat=g["lat"],
                suggested_lon=g["lon"],
                all_grids=normalized_grids,
                poi_indexes=poi_indexes,
                poi_table=poi_table,
                radius_km=radius_km,
                category=category,
            )

        else:
            catchment_pop = g.get("population", 0)

        result.append({
            "rank":       i + 1,
            "lat":        g["lat"],
            "lon":        g["lon"],
            "score":      g.get("normalized_score", 0),
            "population": catchment_pop,
            "label": (
                f"Score: {g.get('normalized_score', 0):.2f}, "
                f"Population: {catchment_pop}"
            ),
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


def _detect_category(question: str, llm) -> tuple[str | None, str | None]:
    """Returns (broad_category, specific_keyword)"""
    q_lower = question.lower()

    # ── 1. Fast path: scan CATEGORY_SYNONYMS directly ───────────────────────
    for category, synonyms in CATEGORY_SYNONYMS.items():
        for synonym in synonyms:
            if synonym.lower() in q_lower:
                return category, synonym   # ← returns matched keyword directly

    # ── 2. LLM fallback: category ONLY ──────────────────────────────────────
    try:
        prompt = f"""
You are a facility classifier for a GIS application.
Return STRICT JSON only — no explanation, no markdown:
{{"category": "<one_of_below_or_null>"}}

Valid categories: {', '.join(CATEGORY_SYNONYMS.keys())}

Rules:
- Pick the single best matching category for the question.
- If nothing matches, return null.

Question: "{question}"
"""
        raw    = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        raw    = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        cat    = parsed.get("category", "")

        if not cat or cat.lower() in ("null", "none", ""):
            return None, None

        mapped_cat = map_to_valid_category(cat)
        if not mapped_cat:
            return None, None

        # ── 3. Extract keyword from question using detected category ─────────
        keyword = next(
            (syn for syn in CATEGORY_SYNONYMS.get(mapped_cat, [])
             if syn in q_lower),
            None
        )

        print(f"LLM detected → category: {mapped_cat}, keyword: {keyword}")
        return mapped_cat, keyword

    except Exception:
        return None, None
    


LISTING_WORDS = ["list", "show", "all", "display", "what are", "give me",
                  "how many", "count", "which", "enumerate", "name",
                 "are there", "any", "do we have", "nearby", "available"]

LOCATION_WORDS = ["where", "best", "suggest", "recommend", "location",
                  "spot", "find", "ideal",  "open"]

def _detect_intent(question: str) -> str:
    q = question.lower()

    # LISTING takes priority — most explicit
    if any(w in q for w in LISTING_WORDS):
        return "LISTING"

    # LOCATION second
    if any(w in q for w in LOCATION_WORDS):
        return "LOCATION"

    return "ANALYSIS"


def _resolve_rule(category: str, keyword: str | None) -> tuple[str, dict, list | None]:
    if keyword:
        keyword_lower = keyword.lower()
        if keyword_lower in SUBCATEGORY_RULES:
            rules = SUBCATEGORY_RULES[keyword_lower]
            print(f"[RULE] SUBCATEGORY matched → '{keyword_lower}' | poi_filter:{rules} | poi_filter: {rules.get('poi_filter')} | min_dist_km: {rules.get('min_dist_km')}")
            return keyword_lower, rules, rules.get("poi_filter")
        else:
            print(f"[RULE] SUBCATEGORY miss → keyword='{keyword_lower}' not in SUBCATEGORY_RULES")

    rule_key = CATEGORY_TO_RULE.get(category, category)
    rules    = FACILITY_RULES.get(rule_key)
    if not rules:
        print(f"[RULE] No rules found for '{rule_key}'")
        return rule_key, {}, None    
    print(f"[RULE] FACILITY fallback → category='{category}' mapped to '{rule_key}'")
    return rule_key, rules, None


# ────────────────────────────────────────────────────
# MAIN AGENT
# ───────────────────────────────────────────────────

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

    # ── Intent detection ──────────────────────────────
    # LISTING takes priority — most explicit intent
    intent = _detect_intent(question)

    # ── Category detection ────────────────────────────
    matched_category, matched_keyword = _detect_category(question, llm)

    print(f"Intent={intent} | Category={matched_category} | Keyword={matched_keyword}")

    # ── Dynamic scoring + top 3 (only for LOCATION) ───
    suggestions = []
    grids       = []

    if intent == "LOCATION" and matched_category and session.get("poi_data"):
        grids    = session["poi_data"].get("grids", [])
        poi_data = session["poi_data"].get("pois",  {})
        
         # ── Resolve to subcategory rule if keyword matched ────────
        rule_key, rules, poi_filter = _resolve_rule(matched_category, matched_keyword)

        scored_grids = get_top3_from_db(
            grids     = grids,
            radius_km = session["radius"],
            category  = rule_key,
            poi_data  = poi_data,
            poi_filter = poi_filter,
            rules      = rules,
            session    = session, # ← pass resolved rules directly
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

    # ── POI list for LISTING intent ───────────────────

    if intent == "LISTING" and matched_category:
        raw = _get_category_pois(matched_category, session, keyword=matched_keyword)
        
         # ✅ DEBUG PRINTS (move here)
        print("==== DEBUG LISTING ====")
        print("Category:", matched_category)
        print("Keyword :", matched_keyword)
        print("Raw POIs:\n", raw)


        if raw.startswith("__NONE_FOUND__:"):
            queried_type = raw.split(":", 1)[1]
            return {
                "response":    f"There are no {queried_type} recorded in the "
                               f"selected area. Try expanding the radius or ask "
                               f"about a different facility type.",
                "suggestions": None,
                "grids":       []
            }

        return {
            "response": f"Here are all the {matched_keyword or matched_category} in this area:\n\n{raw}",
            "suggestions": None,
            "grids": []
        }
        


    # DEBUG — remove after confirming

    # ── Memory ────────────────────────────────────────
    previous_q = session.get("last_question", "None")

    # ── System prompt ─────────────────────────────────
    system_prompt = f"""
You are an expert Location Intelligence Consultant specializing in site selection and urban analysis.

## AREA DATA
{poi_counts}

## AREA SUITABILITY
{suitability}

## USER CONTEXT
Previous question: {previous_q}

"""



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
- Available facilities nearby (ONLY mention from AREA DATA above)
- Population coverage
- Why it is suitable for the requested facility type

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
    