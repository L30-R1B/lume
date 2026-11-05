"""Typed optional auxiliary inference, bounded concurrency and labeled deterministic fallback."""

import fcntl
import json
import math
import os
import time
import urllib.error
import urllib.request
from typing import Protocol
from .security import redact, digest


class Reranker(Protocol):
    def rank(self, query: str, candidates: list[dict]) -> list[dict]: ...


class Embedder(Protocol):
    def encode(self, texts: list[str]): ...


class Locator(Protocol):
    def locate(self, query: str, candidates: list[dict]) -> list[dict]: ...


class LocalReranker:
    model = "tfidf-char-wb-3-5-v1"

    def rank(self, query, candidates):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from threadpoolctl import threadpool_limits

        if not candidates:
            return []
        candidates = candidates[:500]
        texts = [(r["path"] + "\n" + r["source"])[:32000] for r in candidates]
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=30000)
        with threadpool_limits(limits=1):
            try:
                matrix = vectorizer.fit_transform(texts)
            except ValueError:
                return candidates
            scores = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
        return [
            {**r, "rerank_score": float(scores[i])}
            for i, r in sorted(enumerate(candidates), key=lambda ir: float(scores[ir[0]]), reverse=True)
        ]


class LSAEmbedder:
    """Offline statistical semantic projection fitted to the current candidate corpus."""

    model = "tfidf-lsa-64-v1"

    def encode(self, texts):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        if not 1 <= len(texts) <= 500:
            raise ValueError("LSA requires 1–500 bounded texts")
        matrix = TfidfVectorizer(max_features=10000).fit_transform(t[:32000] for t in texts)
        dimensions = min(64, matrix.shape[1] - 1)
        return (
            TruncatedSVD(n_components=dimensions, random_state=42).fit_transform(matrix)
            if dimensions >= 1
            else matrix.toarray()
        )


def probability(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def validate_questions(questions):
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 32:
        raise ValueError("Jev requires 1–32 questions")
    for question in questions.values():
        if (
            not isinstance(question, dict)
            or question.get("type") not in ("choice", "score", "noul")
            or not question.get("instructions")
        ):
            raise ValueError("Invalid typed Jev question")
        kind = question["type"]
        if kind == "choice" and (
            not isinstance(question.get("criteria"), dict) or not 2 <= len(question["criteria"]) <= 32
        ):
            raise ValueError("Choice requires 2–32 options")
        if kind == "score" and (
            not isinstance(question.get("criteria"), list) or not 2 <= len(question["criteria"]) <= 16
        ):
            raise ValueError("Score requires 2–16 levels")


def validate_answers(result, questions):
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict) or not result.get("model"):
        raise ValueError("Invalid Jev response envelope")
    for name, spec in questions.items():
        answer = result["answers"][name]
        kind = spec["type"]
        if answer.get("type") != kind:
            raise ValueError("Response type mismatch")
        if kind == "noul":
            if not probability(answer.get("noul")):
                raise ValueError("Invalid Noul probability")
        else:
            probs = answer.get("probabilities", {})
            expected = set(spec["criteria"]) if kind == "choice" else set(map(str, range(len(spec["criteria"]))))
            if (
                set(probs) != expected
                or not all(probability(v) for v in probs.values())
                or abs(sum(probs.values()) - 1) > 0.025
                or not probability(answer.get("confidence"))
            ):
                raise ValueError("Invalid Jev probability distribution")
            if kind == "choice" and answer.get("choice") not in expected:
                raise ValueError("Invalid choice")
            if kind == "score" and (
                not isinstance(answer.get("score"), (int, float))
                or not math.isfinite(answer["score"])
                or not 0 <= answer["score"] <= len(spec["criteria"]) - 1
            ):
                raise ValueError("Invalid score")
    return result


class Jev:
    endpoint = "https://api.typesafe.ai/v1/systemone"

    def __init__(self, store, timeout=15):
        self.s = store
        self.timeout = timeout

    def ask(self, state, questions, allowed=False):
        if not allowed:
            return {"mode": "local-fallback", "error": "external_context_denied", "requests": 0}
        from .config import load

        config = load(self.s)
        if os.environ.get("CE_JEV_MODE", config["auxiliary"]["mode"]) == "off":
            return {"mode": "off", "requests": 0}
        key = os.environ.get("TYPESAFE_API_KEY")
        secret_file = self.s.home / "typesafe.key"
        if not key and secret_file.is_file() and not secret_file.is_symlink():
            if secret_file.stat().st_mode & 0o077:
                raise ValueError("Secret file permissions must be 0600")
            key = secret_file.read_text().strip()
        if not key:
            return {"mode": "local-fallback", "error": "credential_unavailable", "requests": 0}
        if not config["auxiliary"]["allow_paid"] and os.environ.get("CE_JEV_ALLOW_PAID") != "1":
            return {"mode": "local-fallback", "error": "paid_inference_not_authorized", "requests": 0}
        validate_questions(questions)
        model = os.environ.get("CE_JEV_MODEL", config["auxiliary"]["model"])
        payload = {"model": model, "state": state, "questions": questions}
        data = json.dumps(payload).encode()
        if len(data) > 64000:
            raise ValueError("Jev input limit is 64000 bytes")
        cache_key = digest(data)
        validity = digest(json.dumps({"provider": "typesafe", "model": model, "contract": 2}))
        if model != "jev-latest":
            cached = self.s.cache_get("inference", cache_key, validity)
            if cached:
                result = {
                    **cached,
                    "mode": "jev-cache",
                    "requests": 0,
                    "usage": None,
                    "latency_seconds": 0,
                    "cache_hit": True,
                }
                self.s.event("auxiliary", result)
                return result
        slots = []
        acquired = None
        try:
            for i in range(2):
                fd = os.open(self.s.home / f".jev-slot-{i}", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
                slots.append(fd)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = fd
                    break
                except BlockingIOError:
                    continue
            if acquired is None:
                return {"mode": "local-fallback", "error": "concurrency_limit", "requests": 0}
            started = time.monotonic()
            try:
                request = urllib.request.Request(
                    self.endpoint,
                    data,
                    {"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ValueError("Response exceeds limit")
                result = validate_answers(json.loads(raw), questions)
                result["mode"] = "jev"
            except urllib.error.HTTPError as error:
                result = {
                    "mode": "local-fallback",
                    "error": {401: "authentication", 403: "authorization", 429: "rate_limit"}.get(
                        error.code, "http_" + str(error.code)
                    ),
                }
            except TimeoutError:
                result = {"mode": "local-fallback", "error": "timeout"}
            except urllib.error.URLError:
                result = {"mode": "local-fallback", "error": "network"}
            except (ValueError, KeyError, TypeError, AttributeError):
                result = {"mode": "local-fallback", "error": "invalid_response"}
            result.update(
                {
                    "latency_seconds": time.monotonic() - started,
                    "provider": "typesafe",
                    "requested_model": model,
                    "input_bytes": len(data),
                    "cost": None,
                    "requests": 1,
                    "decision_used": "ranking_only" if result["mode"] == "jev" else "none",
                    "cache_hit": False,
                }
            )
            self.s.event("auxiliary", result)
            if result["mode"] == "jev" and model != "jev-latest":
                self.s.cache_put("inference", cache_key, validity, result, ttl=3600)
            return result
        finally:
            for fd in slots:
                os.close(fd)

    def rank(self, project, query, rows):
        if len(rows) <= 3 or any(query == r.get("path") for r in rows):
            return rows, {"mode": "bypass", "reason": "exact_or_small_set", "requests": 0}
        candidates = [
            {"id": i, "path": r["path"], "source": redact(r["source"][:1400])} for i, r in enumerate(rows[:24])
        ]
        questions = {
            str(i): {
                "type": "score",
                "instructions": f"How relevant is candidate {i} to the task?",
                "criteria": ["Irrelevant", "Related", "Direct evidence"],
            }
            for i in range(len(candidates))
        }
        questions["action"] = {
            "type": "choice",
            "instructions": "Which next action type fits the evidence?",
            "criteria": {"read": "Read source", "test": "Run verification", "search": "Find missing evidence"},
        }
        questions["repeat"] = {
            "type": "noul",
            "instructions": "Does the state show repeated investigation without changed evidence?",
        }
        result = self.ask(
            {"task": query, "candidates": candidates, "investigation": project.get("_investigation", {})},
            questions,
            project["policy"]["external"],
        )
        if result["mode"] in ("jev", "jev-cache"):
            order = sorted(range(len(candidates)), key=lambda i: result["answers"][str(i)]["score"], reverse=True)
            rows = [rows[i] for i in order] + rows[len(candidates) :]
        return rows, result


def calibrate(rows):
    if not isinstance(rows, list) or len(rows) < 4 or any(r.get("split") != "calibration" for r in rows):
        raise ValueError("Use at least four labeled calibration records, separate from final evaluation")
    if any(not probability(r.get("probability")) or r.get("label") not in (0, 1) for r in rows):
        raise ValueError("Invalid labeled probability")
    if {r["label"] for r in rows} != {0, 1}:
        raise ValueError("Calibration needs both classes")
    choices = sorted({r["probability"] for r in rows})
    outcomes = []
    for threshold in choices:
        tp = sum(r["probability"] >= threshold and r["label"] == 1 for r in rows)
        fp = sum(r["probability"] >= threshold and r["label"] == 0 for r in rows)
        fn = sum(r["probability"] < threshold and r["label"] == 1 for r in rows)
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0
        outcomes.append((f1, threshold, tp, fp, fn))
    f1, threshold, tp, fp, fn = max(outcomes)
    return {
        "threshold": threshold,
        "objective": "maximum calibration F1",
        "f1": f1,
        "n": len(rows),
        "brier": sum((r["probability"] - r["label"]) ** 2 for r in rows) / len(rows),
        "dataset_hash": digest(json.dumps(rows, sort_keys=True)),
        "evaluation": False,
        "guarantee": False,
        "use": "advisory routing only; independent acceptance checks remain mandatory",
        "confusion": {"tp": tp, "fp": fp, "fn": fn},
    }
