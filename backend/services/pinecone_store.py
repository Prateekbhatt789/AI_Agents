import os
import re
import time
import threading
import unicodedata
import hashlib

from dotenv import load_dotenv

load_dotenv()

# ────────────────────────────────────────────────────
# NOTHING runs at import time.
# Pinecone client, index, and model are all initialized
# lazily on first use. This lets FastAPI start instantly.
# ────────────────────────────────────────────────────

_pc           = None
_pc_lock      = threading.Lock()

_embedder     = None
_model_lock   = threading.Lock()

_index_ready  = False
_index_lock   = threading.Lock()

INDEX_NAME    = os.getenv("PINECONE_INDEX_NAME", "gis-agent")


# ── Pinecone client — lazy ────────────────────────────

def _get_pc():
    """
    Returns Pinecone client, creating it on first call only.
    Not created at import time so server starts instantly.
    """
    global _pc
    if _pc is not None:
        return _pc
    with _pc_lock:
        if _pc is None:
            from pinecone import Pinecone
            _pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return _pc


# ── Embedder model — lazy ─────────────────────────────

def get_embedder():
    """
    Returns SentenceTransformer model, loading it on first call.
    Not loaded at import time — model download would block startup.
    Thread-safe: only one thread loads the model even under concurrency.
    """
    global _embedder
    if _embedder is not None:
        return _embedder
    with _model_lock:
        if _embedder is None:
            from sentence_transformers import SentenceTransformer
            print("🟡 Loading sentence-transformers model...")
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ sentence-transformers model ready")
    return _embedder


# ── Index setup — lazy, once ──────────────────────────

def ensure_index():
    """
    Creates Pinecone index if it doesn't exist.
    Runs only once per server lifetime — guarded by lock
    so concurrent requests don't race to create the index.
    """
    global _index_ready
    if _index_ready:
        return
    with _index_lock:
        if _index_ready:
            return
        try:
            from pinecone import ServerlessSpec
            pc       = _get_pc()
            existing = [i.name for i in pc.list_indexes().indexes]
            if INDEX_NAME not in existing:
                print(f"🟡 Creating Pinecone index '{INDEX_NAME}'")
                pc.create_index(
                    name      = INDEX_NAME,
                    dimension = 384,
                    metric    = "cosine",
                    spec      = ServerlessSpec(cloud="aws", region="us-east-1")
                )
                print(f"✅ Index '{INDEX_NAME}' created")
            else:
                print(f"✅ Index '{INDEX_NAME}' ready")
            _index_ready = True
        except Exception as e:
            print(f"🔴 ensure_index failed: {e}")
            raise


# ────────────────────────────────────────────────────
# NAMESPACE HELPERS
# ────────────────────────────────────────────────────

def make_namespace(location_name: str) -> str:
    """
    Converts location name to a safe Pinecone namespace.
    Example: "Éamon de Valera Marg" → "eamon_de_valera_marg"
    """
    clean = unicodedata.normalize("NFKD", location_name)
    clean = clean.encode("ascii", "ignore").decode("ascii")
    clean = clean.lower().replace(" ", "_")
    clean = re.sub(r"[^a-z0-9_-]", "", clean)
    return clean[:40]


def namespace_exists(namespace: str) -> bool:
    """
    Checks if a namespace already has vectors.
    Uses describe_index_stats() — reliable unlike zero-vector querying.
    """
    try:
        ensure_index()
        index = _get_pc().Index(INDEX_NAME)
        stats = index.describe_index_stats()
        return namespace in (stats.namespaces or {})
    except Exception as e:
        print(f"🔴 namespace_exists failed: {e}")
        return False


# ────────────────────────────────────────────────────
# VECTOR ID
# ────────────────────────────────────────────────────

def make_vector_id(text: str, namespace: str, index: int) -> str:
    base = f"{namespace}_{index}_{text}"
    return hashlib.md5(base.encode()).hexdigest()


# ────────────────────────────────────────────────────
# STORE POIS
# ────────────────────────────────────────────────────

def store_pois(poi_data: dict, location_name: str) -> int:
    ensure_index()

    namespace = make_namespace(location_name)
    index     = _get_pc().Index(INDEX_NAME)
    texts     = []
    metas     = []

    for category, items in poi_data.items():
        if category == "summary" or not isinstance(items, list):
            continue
        for item in items[:30]:
            text = (
                f"{category.replace('_', ' ')} "
                f"named {item['name']} "
                f"at {item['lat']:.4f}, {item['lon']:.4f} "
                f"in {location_name}"
            )
            texts.append(text)
            metas.append({
                "text":     text,
                "category": category,
                "name":     item["name"],
                "lat":      item["lat"],
                "lon":      item["lon"],
                "location": location_name
            })

    if not texts:
        return 0

    embeddings = get_embedder().encode(
        texts,
        batch_size        = 32,
        show_progress_bar = False
    )

    vectors = [
        {
            "id":       make_vector_id(texts[i], namespace, i),
            "values":   embeddings[i].tolist(),
            "metadata": metas[i]
        }
        for i in range(len(texts))
    ]

    for batch_start in range(0, len(vectors), 100):
        batch   = vectors[batch_start:batch_start + 100]
        success = False

        for attempt in range(3):
            try:
                index.upsert(vectors=batch, namespace=namespace)
                success = True
                break
            except Exception as e:
                print(f"🔴 Upsert batch {batch_start} failed "
                      f"(attempt {attempt+1}/3): {e}")
                time.sleep(2 * (attempt + 1))

        if not success:
            print(f"🔴 Batch {batch_start} permanently failed — skipping")

    return len(vectors)


# ────────────────────────────────────────────────────
# SEARCH
# ────────────────────────────────────────────────────

def search_pois(query: str, namespace: str, top_k: int = 8) -> list:
    ensure_index()

    index     = _get_pc().Index(INDEX_NAME)
    embedding = get_embedder().encode(query).tolist()

    try:
        results = index.query(
            vector           = embedding,
            top_k            = top_k,
            include_metadata = True,
            namespace        = namespace
        )
    except Exception as e:
        print(f"🔴 search_pois failed: {e}")
        return []

    return [
        {
            "text":     m.metadata["text"],
            "category": m.metadata["category"],
            "name":     m.metadata["name"],
            "score":    m.score
        }
        for m in results.matches
    ]










# import os
# import re
# import time
# import threading
# import unicodedata
# import hashlib

# from pinecone import Pinecone, ServerlessSpec
# from sentence_transformers import SentenceTransformer
# from dotenv import load_dotenv

# load_dotenv()

# pc         = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
# INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "gis-agent")

# # ────────────────────────────────────────────────────
# # MODEL — lazy load, thread-safe
# # ────────────────────────────────────────────────────

# _embedder    = None
# _model_ready = threading.Event()


# def _preload_model():
#     global _embedder
#     print("🟡 Loading sentence-transformers model...")
#     _embedder = SentenceTransformer("all-MiniLM-L6-v2")
#     _model_ready.set()
#     print("✅ sentence-transformers model ready")


# threading.Thread(target=_preload_model, daemon=True).start()


# def get_embedder() -> SentenceTransformer:
#     if not _model_ready.is_set():
#         print("⏳ Waiting for model to load...")
#         _model_ready.wait()
#     return _embedder


# # ────────────────────────────────────────────────────
# # INDEX SETUP — once at startup, protected by a Lock
# # ────────────────────────────────────────────────────

# _index_ready = False
# _index_lock  = threading.Lock()   # ✅ prevents simultaneous index creation


# def ensure_index():
#     """
#     Creates Pinecone index if it doesn't exist.
#     Lock ensures only ONE thread runs this at a time.
#     Without the lock, two simultaneous requests both see
#     _index_ready=False and both attempt to create the index.
#     """
#     global _index_ready

#     # Fast path — no lock needed once ready
#     if _index_ready:
#         return

#     with _index_lock:
#         # Re-check inside lock — another thread may have
#         # completed index creation while this one was waiting
#         if _index_ready:
#             return

#         try:
#             existing = [i.name for i in pc.list_indexes().indexes]

#             if INDEX_NAME not in existing:
#                 print(f"🟡 Creating Pinecone index '{INDEX_NAME}'")
#                 pc.create_index(
#                     name      = INDEX_NAME,
#                     dimension = 384,
#                     metric    = "cosine",
#                     spec      = ServerlessSpec(cloud="aws", region="us-east-1")
#                 )
#                 print(f"✅ Index '{INDEX_NAME}' created")
#             else:
#                 print(f"✅ Index '{INDEX_NAME}' ready")

#             _index_ready = True

#         except Exception as e:
#             print(f"🔴 ensure_index failed: {e}")
#             raise


# # ────────────────────────────────────────────────────
# # NAMESPACE HELPERS
# # ────────────────────────────────────────────────────

# def make_namespace(location_name: str) -> str:
#     """
#     Converts location name to a safe Pinecone namespace.
#     Example: "Éamon de Valera Marg" → "eamon_de_valera_marg"
#     """
#     clean = unicodedata.normalize("NFKD", location_name)
#     clean = clean.encode("ascii", "ignore").decode("ascii")
#     clean = clean.lower().replace(" ", "_")
#     clean = re.sub(r"[^a-z0-9_-]", "", clean)
#     return clean[:40]


# def namespace_exists(namespace: str) -> bool:
#     """
#     Checks if a namespace has vectors using describe_index_stats().
#     Reliable — unlike zero-vector querying which has undefined
#     cosine similarity behavior.
#     """
#     try:
#         ensure_index()
#         index  = pc.Index(INDEX_NAME)
#         stats  = index.describe_index_stats()
#         return namespace in (stats.namespaces or {})

#     except Exception as e:
#         print(f"🔴 namespace_exists check failed: {e}")
#         return False


# # ────────────────────────────────────────────────────
# # VECTOR ID GENERATION
# # ────────────────────────────────────────────────────

# def make_vector_id(text: str, namespace: str, index: int) -> str:
#     base = f"{namespace}_{index}_{text}"
#     return hashlib.md5(base.encode()).hexdigest()


# # ────────────────────────────────────────────────────
# # STORE POIS — stateless, safe for concurrent users
# # ────────────────────────────────────────────────────

# def store_pois(poi_data: dict, location_name: str) -> int:
#     """
#     All inputs are passed as arguments — no globals read or written.
#     Safe for any number of concurrent users.
#     """
#     ensure_index()

#     namespace = make_namespace(location_name)
#     index     = pc.Index(INDEX_NAME)
#     texts     = []
#     metas     = []

#     for category, items in poi_data.items():
#         if category == "summary" or not isinstance(items, list):
#             continue

#         for item in items[:30]:
#             text = (
#                 f"{category.replace('_', ' ')} "
#                 f"named {item['name']} "
#                 f"at {item['lat']:.4f}, {item['lon']:.4f} "
#                 f"in {location_name}"
#             )
#             texts.append(text)
#             metas.append({
#                 "text":     text,
#                 "category": category,
#                 "name":     item["name"],
#                 "lat":      item["lat"],
#                 "lon":      item["lon"],
#                 "location": location_name
#             })

#     if not texts:
#         return 0

#     embeddings = get_embedder().encode(
#         texts,
#         batch_size        = 32,
#         show_progress_bar = False
#     )

#     vectors = [
#         {
#             "id":       make_vector_id(texts[i], namespace, i),
#             "values":   embeddings[i].tolist(),
#             "metadata": metas[i]
#         }
#         for i in range(len(texts))
#     ]

#     for batch_start in range(0, len(vectors), 100):
#         batch   = vectors[batch_start:batch_start + 100]
#         success = False

#         for attempt in range(3):
#             try:
#                 index.upsert(vectors=batch, namespace=namespace)
#                 success = True
#                 break
#             except Exception as e:
#                 print(f"🔴 Upsert batch {batch_start} failed "
#                       f"(attempt {attempt+1}/3): {e}")
#                 time.sleep(2 * (attempt + 1))

#         if not success:
#             print(f"🔴 Batch {batch_start} permanently failed — skipping")

#     return len(vectors)


# # ────────────────────────────────────────────────────
# # SEARCH — stateless, safe for concurrent users
# # ────────────────────────────────────────────────────

# def search_pois(query: str, namespace: str, top_k: int = 8) -> list:
#     """
#     namespace passed explicitly per request — no global state.
#     Each user's request carries its own namespace derived from
#     their analyzed location, so concurrent users never interfere.
#     """
#     ensure_index()

#     index     = pc.Index(INDEX_NAME)
#     embedding = get_embedder().encode(query).tolist()

#     try:
#         results = index.query(
#             vector           = embedding,
#             top_k            = top_k,
#             include_metadata = True,
#             namespace        = namespace
#         )
#     except Exception as e:
#         print(f"🔴 search_pois failed: {e}")
#         return []

#     return [
#         {
#             "text":     m.metadata["text"],
#             "category": m.metadata["category"],
#             "name":     m.metadata["name"],
#             "score":    m.score
#         }
#         for m in results.matches
#     ]





