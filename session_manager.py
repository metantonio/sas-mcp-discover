"""
Session Manager - Persistent Conversation History for SAS Agent.

Stores chat conversations in JSON files within the user's sessions directory.
Preserves:
- UI chat display history (speaker, tags, timestamps)
- LLM Agent conversation context (system prompt, user messages, assistant replies, tool calls)
- PII Vault state (ensuring pseudonym-to-original mappings persist across sessions)
"""

import os
import sys
import json
import uuid
import datetime
from typing import List, Dict, Any, Optional

HOME = os.path.join(os.path.expandvars("%APPDATA%"), "SASAgent")


def get_base_dir() -> str:
    """Return base directory of script or frozen executable."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_sessions_dir() -> str:
    """Return sessions directory, creating it if necessary."""
    # Preferred: local folder next to script/exe if writable, otherwise in APPDATA
    preferred = os.path.join(get_base_dir(), "sessions")
    try:
        os.makedirs(preferred, exist_ok=True)
        # Test writability
        test_file = os.path.join(preferred, ".test_write")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return preferred
    except Exception:
        fallback = os.path.join(HOME, "sessions")
        os.makedirs(fallback, exist_ok=True)
        return fallback


class SessionManager:
    def __init__(self):
        self.sessions_dir = get_sessions_dir()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all saved sessions, sorted by updated_at descending.
        Returns list of metadata dicts.
        """
        results = []
        if not os.path.exists(self.sessions_dir):
            return results

        for fname in os.listdir(self.sessions_dir):
            if fname.endswith(".json") and not fname.startswith("."):
                path = os.path.join(self.sessions_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    msg_count = len(data.get("messages", []))
                    results.append({
                        "id": data.get("id", os.path.splitext(fname)[0]),
                        "title": data.get("title", "Conversación sin título"),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "provider": data.get("provider", "openai"),
                        "model": data.get("model", ""),
                        "message_count": msg_count,
                    })
                except Exception:
                    continue

        results.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return results

    def create_session(self, title: str = "Nueva Conversación", provider: str = "openai", model: str = "") -> Dict[str, Any]:
        """Create and persist a new session."""
        now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sess_id = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        session_data = {
            "id": sess_id,
            "title": title,
            "created_at": now_iso,
            "updated_at": now_iso,
            "provider": provider,
            "model": model,
            "messages": [],       # Display messages in the UI
            "llm_history": [],    # Internal LLM agent messages
            "pii_vault": {},      # Serialized PIIVault state
        }
        self.save_session(session_data)
        return session_data

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data by ID."""
        path = os.path.join(self.sessions_dir, f"{session_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}", file=sys.stderr)
            return None

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """Save session data to disk."""
        sess_id = session_data.get("id")
        if not sess_id:
            return False

        session_data["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = os.path.join(self.sessions_dir, f"{sess_id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving session {sess_id}: {e}", file=sys.stderr)
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file."""
        path = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception:
                return False
        return False

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Rename an existing session."""
        session = self.load_session(session_id)
        if session:
            session["title"] = new_title.strip() or "Conversación sin título"
            return self.save_session(session)
        return False
