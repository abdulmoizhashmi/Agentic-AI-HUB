import json
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone

class SessionStore:
    """Small JSON checkpoint store for local development."""
    def __init__(self, path: Path):
        self.path, self.lock = path, RLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("{}", encoding="utf-8")

    def _read(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not read session store at {self.path}") from exc

    def _write(self, data):
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_session(self, sid):
        with self.lock:
            return self._read().get(sid, {"messages": [], "memory": {}, "pending_review": None})

    def append_turn(self, sid, user, assistant, agent, metadata=None):
        with self.lock:
            data = self._read()
            s = data.setdefault(sid, {"messages": [], "memory": {}, "pending_review": None})
            now = datetime.now(timezone.utc).isoformat()
            s["messages"] += [
                {"role": "user", "content": user, "at": now},
                {"role": "assistant", "content": assistant, "at": now, "agent": agent, "metadata": metadata or {}}
            ]
            s["messages"] = s["messages"][-60:]
            s["memory"]["last_agent"] = agent
            s["memory"]["turn_count"] = s["memory"].get("turn_count", 0) + 1
            s["memory"]["last_user_intent"] = user[:240]
            self._write(data)
            return s

    def set_pending_review(self, sid, review):
        with self.lock:
            data = self._read()
            s = data.setdefault(sid, {"messages": [], "memory": {}, "pending_review": None})
            s["pending_review"] = review
            self._write(data)

    def pending_reviews(self):
        with self.lock:
            data = self._read()
            return {"items": [{"session_id": sid, **s["pending_review"]}
                              for sid, s in data.items() if s.get("pending_review")]}

    def clear_session(self, sid):
        with self.lock:
            data = self._read()
            data.pop(sid, None)
            self._write(data)
