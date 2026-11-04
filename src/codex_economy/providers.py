"""Replaceable ranking contracts; local ranking never needs network or downloaded weights."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Protocol
from .security import redact


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

        if not candidates:
            return []
        # Corpus-fit statistical model, no neural semantics claimed.
        texts = [(r["path"] + "\n" + r["source"])[:32000] for r in candidates[:500]]
        v = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=30000)
        try:
            matrix = v.fit_transform(texts)
        except ValueError:
            return candidates
        scores = (matrix @ v.transform([query]).T).toarray().ravel()
        return [
            {**r, "rerank_score": float(scores[i])}
            for i, r in sorted(enumerate(candidates[:500]), key=lambda ir: float(scores[ir[0]]), reverse=True)
        ]


class Jev:
    endpoint = "https://api.typesafe.ai/v1/systemone"

    def __init__(self, store, timeout=15):
        self.s = store
        self.timeout = timeout

    def ask(self, state, questions, allowed=False):
        if not allowed:
            return {"mode": "local-fallback", "error": "external_context_denied"}
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            return {"mode": "local-fallback", "error": "credential_unavailable"}
        payload = {"model": "jev-latest", "state": state, "questions": questions}
        data = json.dumps(payload).encode()
        if len(data) > 64000 or not 1 <= len(questions) <= 32:
            raise ValueError("Jev input limit: 64000 bytes / 32 questions")
        started = time.monotonic()
        result = {}
        try:
            req = urllib.request.Request(
                self.endpoint,
                data,
                {"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError("Response too large")
            result = json.loads(raw)
            answers = result["answers"]
            for q, spec in questions.items():
                answer = answers[q]
                typ = spec["type"]
                if answer["type"] != typ:
                    raise ValueError("Type mismatch")
                if typ == "noul" and not 0 <= answer["noul"] <= 1:
                    raise ValueError("Invalid probability")
                if typ == "score" and not 0 <= answer["score"] <= len(spec["criteria"]) - 1:
                    raise ValueError("Invalid score")
                if typ == "choice" and answer["choice"] not in spec["criteria"]:
                    raise ValueError("Invalid choice")
                if typ in ("score", "choice") and (
                    not 0 <= answer["confidence"] <= 1 or not all(0 <= v <= 1 for v in answer["probabilities"].values())
                ):
                    raise ValueError("Invalid distribution")
            result["mode"] = "jev"
        except urllib.error.HTTPError as e:
            result = {
                "mode": "local-fallback",
                "error": {401: "authentication", 403: "authorization", 429: "rate_limit"}.get(
                    e.code, "http_" + str(e.code)
                ),
            }
        except TimeoutError:
            result = {"mode": "local-fallback", "error": "timeout"}
        except urllib.error.URLError:
            result = {"mode": "local-fallback", "error": "network"}
        except (ValueError, KeyError, TypeError):
            result = {"mode": "local-fallback", "error": "invalid_response"}
        result["latency_seconds"] = time.monotonic() - started
        result["provider"] = "typesafe"
        result["requested_model"] = "jev-latest"
        result["input_bytes"] = len(data)
        result["cost"] = None  # No extrapolation without billing data.
        with self.s.db:
            self.s.db.execute(
                "INSERT INTO events(created,kind,payload) VALUES(?,?,?)", (time.time(), "auxiliary", json.dumps(result))
            )
        return result

    def rank(self, project, query, rows):
        if len(rows) <= 3:
            return rows, {"mode": "bypass", "reason": "small_candidate_set"}
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
            "instructions": "Does the supplied state show a repeated investigation with no changed evidence?",
        }
        result = self.ask({"task": query, "candidates": candidates}, questions, project["policy"]["external"])
        if result["mode"] == "jev":
            # Advisory ordering only; no uncalibrated accept/stop threshold.
            order = sorted(range(len(candidates)), key=lambda i: result["answers"][str(i)]["score"], reverse=True)
            rows = [rows[i] for i in order] + rows[len(candidates) :]
        return rows, result
