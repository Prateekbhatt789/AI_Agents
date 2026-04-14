import uuid
import threading
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.agent import ask_agent, set_session, create_session
from services.pinecone_store import store_pois, namespace_exists, make_namespace

router = APIRouter()

# ────────────────────────────────────────────────────
# SESSION STORE — per-user, keyed by session_id
# ────────────────────────────────────────────────────

_sessions      : dict[str, dict] = {}
_sessions_lock : threading.Lock  = threading.Lock()


def _get_session(session_id: str) -> dict | None:
    with _sessions_lock:
        return _sessions.get(session_id)


def _put_session(session_id: str, session: dict):
    with _sessions_lock:
        _sessions[session_id] = session


# ────────────────────────────────────────────────────
# REQUEST MODELS
# ────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    location:  str
    lat:       float
    lon:       float
    radius_km: float
    poi_data:  dict


class ChatRequest(BaseModel):
    message: str


# ────────────────────────────────────────────────────
# STATUS
# ────────────────────────────────────────────────────

@router.get("/status")
async def status(x_session_id: str = Header(default=None)):
    """
    Returns session status for the given session_id header.
    """
    if not x_session_id:
        return {"status": "ok", "location_loaded": False}

    session = _get_session(x_session_id)
    if not session:
        return {"status": "ok", "location_loaded": False}

    return {
        "status":          "ok",
        "location_loaded": bool(session.get("location")),
        "location":        session.get("location"),
        "radius_km":       session.get("radius"),
        "grid_cached":     session.get("grid_cache") is not None,
    }


# ────────────────────────────────────────────────────
# ANALYZE
# ────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Creates a fresh session, populates it, returns session_id.
    Client must send X-Session-Id header on all /chat requests.
    """
    try:
        namespace      = make_namespace(request.location)
        already_exists = namespace_exists(namespace)

        session    = create_session()
        session_id = str(uuid.uuid4())

        set_session(
            session,
            request.location,
            request.poi_data.get("summary", {}),
            request.radius_km,
            lat      = request.lat,
            lon      = request.lon,
            poi_data = request.poi_data
        )

        _put_session(session_id, session)

        if already_exists:
            return {
                "status":         "ready",
                "session_id":     session_id,
                "vectors_stored": 0,
                "cached":         True
            }

        print(f"🟡 Cache miss — storing '{request.location}'")
        count = store_pois(request.poi_data, request.location)

        return {
            "status":         "ready",
            "session_id":     session_id,
            "vectors_stored": count,
            "cached":         False
        }

    except Exception as e:
        print(f"🔴 /analyze error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code = 500,
            content     = {
                "status": "error",
                "detail": f"{type(e).__name__}: {str(e)}"
            }
        )


# ────────────────────────────────────────────────────
# CHAT
# ────────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest,
               x_session_id: str = Header(default=None)):
    """
    Requires X-Session-Id header from /analyze.
    Returns response + top 3 suggestions list.
    """
    if not request.message.strip():
        return {
            "response":    "Please enter a question.",
            "suggestions": None    # ✅ changed from suggestion
        }

    if not x_session_id:
        return JSONResponse(
            status_code = 400,
            content     = {
                "response":    "Missing X-Session-Id header. Call /analyze first.",
                "suggestions": None    # ✅ changed from suggestion
            }
        )

    session = _get_session(x_session_id)
    if not session:
        return JSONResponse(
            status_code = 404,
            content     = {
                "response":    "Session not found or expired. Please call /analyze again.",
                "suggestions": None    # ✅ changed from suggestion
            }
        )

    try:
        result = ask_agent(request.message, session)

        # ✅ Log suggestions for debugging
        suggestions = result.get("suggestions")
        print(f"🔍 DEBUG suggestions count: "
              f"{len(suggestions) if suggestions else 0}")
        if suggestions:
            for s in suggestions:
                print(f"   Rank {s['rank']}: "
                      f"{s['lat']:.4f}, {s['lon']:.4f} "
                      f"— {s['label']}")

        return {
            "response":    result["response"],
            "suggestions": suggestions    # ✅ list of 3, not single dict
        }

    except Exception as e:
        print(f"🔴 /chat error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code = 500,
            content     = {
                "response":    f"Something went wrong: {type(e).__name__}. Please try again.",
                "suggestions": None    # ✅ changed from suggestion
            }
        )
