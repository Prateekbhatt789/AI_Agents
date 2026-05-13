import uuid
import threading
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.agent import ask_agent, set_session, create_session
from services.pinecone_store import store_pois, make_namespace, namespace_exists  # ✅ added namespace_exists

router = APIRouter()

_sessions      : dict[str, dict] = {}
_sessions_lock : threading.Lock  = threading.Lock()


def _get_session(session_id: str) -> dict | None:
    with _sessions_lock:
        return _sessions.get(session_id)


def _put_session(session_id: str, session: dict):
    with _sessions_lock:
        _sessions[session_id] = session


class AnalyzeRequest(BaseModel):
    location:  str
    lat:       float
    lon:       float
    radius_km: float
    poi_data:  dict


class ChatRequest(BaseModel):
    message: str


@router.get("/status")
async def status(x_session_id: str = Header(default=None)):
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


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        namespace      = make_namespace(request.location, request.radius_km)  
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
        session["namespace"] = namespace

        _put_session(session_id, session)

        if already_exists:
            print(f" Cache hit — reusing '{namespace}'")
            return {
                "status":         "ready",
                "session_id":     session_id,
                "vectors_stored": 0,
                "cached":         True
            }

        print(f" Cache miss — storing '{namespace}'")
        count = store_pois(request.poi_data, namespace,request.location)

        return {
            "status":         "ready",
            "session_id":     session_id,
            "vectors_stored": count,
            "cached":         False
        }

    except Exception as e:  
        print(f" /analyze error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code = 500,
            content     = {
                "status": "error",
                "detail": f"{type(e).__name__}: {str(e)}"
            }
        )


@router.post("/chat")
async def chat(request: ChatRequest,
               x_session_id: str = Header(default=None)):
    if not request.message.strip():
        return {
            "response":    "Please enter a question.",
            "suggestions": None
        }

    if not x_session_id:
        return JSONResponse(
            status_code = 400,
            content     = {
                "response":    "Missing X-Session-Id header. Call /analyze first.",
                "suggestions": None
            }
        )

    session = _get_session(x_session_id)
    if not session:
        return JSONResponse(
            status_code = 404,
            content     = {
                "response":    "Session not found or expired. Please call /analyze again.",
                "suggestions": None
            }
        )

    try:
        result      = ask_agent(request.message, session)
        # print("Result of llm is :", result)
        suggestions = result.get("suggestions")

        print(f" suggestions count: {len(suggestions) if suggestions else 0}")
        if suggestions:
            for s in suggestions:
                print(f"   Rank {s['rank']}: {s['lat']:.4f}, {s['lon']:.4f} — {s['label']}")

        return {
            "response":    result["response"],
            "suggestions": suggestions
        }

    except Exception as e:
        print(f" /chat error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code = 500,
            content     = {
                "response":    f"Something went wrong: {type(e).__name__}. Please try again.",
                "suggestions": None
            }
        )







