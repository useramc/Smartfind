"""Text -> vector. Uses sentence-transformers if available, else an offline hashing fallback."""
import os, re, zlib
import numpy as np

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
BACKEND = os.getenv("EMBED_BACKEND", "sentence-transformers")
HASH_DIM = 384
_model = None
_mode = None


def _load():
    global _model, _mode
    if _mode:
        return
    if BACKEND != "hash":
        try:
            from sentence_transformers import SentenceTransformer
            _model, _mode = SentenceTransformer(MODEL_NAME), "st"
            return
        except Exception as e:
            print(f"[embeddings] sentence-transformers unavailable ({e}); using hash fallback")
    _mode = "hash"


def mode() -> str:
    _load()
    return _mode


def dim() -> int:
    _load()
    return _model.get_sentence_embedding_dimension() if _mode == "st" else HASH_DIM


def _hash_vec(text: str) -> np.ndarray:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    grams = toks + [a + "_" + b for a, b in zip(toks, toks[1:])]
    v = np.zeros(HASH_DIM, dtype=np.float32)
    for g in grams:
        h = zlib.crc32(g.encode())
        v[h % HASH_DIM] += 1.0 if (h >> 16) & 1 else -1.0
    n = np.linalg.norm(v)
    return v / n if n else v


def embed(texts: list[str]) -> list[list[float]]:
    _load()
    if _mode == "st":
        return _model.encode(texts, normalize_embeddings=True, batch_size=64).tolist()
    return [_hash_vec(t).tolist() for t in texts]
