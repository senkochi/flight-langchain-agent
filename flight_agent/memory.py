from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ConventionRecord(BaseModel):
    """
    Structured representation of a persistent convention or preference.
    Persists across sessions independent of conversation history.
    """
    key: str = Field(..., description="Unique convention key (e.g. preferred_airline)")
    value: Any = Field(..., description="Value or rule associated with the convention")
    description: Optional[str] = Field(default=None, description="Detailed description or rationale")
    category: str = Field(default="project_convention", description="Classification category")
    version: int = Field(default=1, description="Version number incremented on each update")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_session: Optional[str] = Field(default=None, description="Session ID where convention was established/updated")

class PersistentMemoryStore:
    """
    Persistent Memory Store outside conversational message history (Slide 14-16).
    
    Addresses Slide 15 Design Questions:
    1. Storage: JSON file with atomic write semantics (human-readable, audit-friendly, durable).
    2. Write mechanism: Supported via both Agent Tool calls and Harness API.
    3. Load mechanism: Pre-loaded and injected into Context at session startup.
    4. Conflict resolution: Strict versioning and overwrite semantics ensuring only latest active conventions enter context.
    5. Verification: Provides format_for_context() to inspect the exact injected context string.
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            scratch_dir = os.path.join(base_dir, ".scratch")
            os.makedirs(scratch_dir, exist_ok=True)
            storage_path = os.path.join(scratch_dir, "persistent_memory.json")
        self.storage_path = storage_path
        self._ensure_storage_file()

    def _ensure_storage_file(self) -> None:
        dir_name = os.path.dirname(self.storage_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self.storage_path):
            self._write_records({})

    def _read_records(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_records(self, data: Dict[str, Dict[str, Any]]) -> None:
        tmp_path = f"{self.storage_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.storage_path)

    def save_convention(
        self,
        key: str,
        value: Any,
        description: Optional[str] = None,
        category: str = "project_convention",
        session_id: Optional[str] = None,
    ) -> ConventionRecord:
        """
        Saves or updates a project convention. If convention exists, increments version
        and updates timestamp.
        """
        records = self._read_records()
        now = datetime.now(timezone.utc).isoformat()
        
        if key in records:
            existing = records[key]
            version = existing.get("version", 1) + 1
            created_at = existing.get("created_at", now)
        else:
            version = 1
            created_at = now

        record = ConventionRecord(
            key=key,
            value=value,
            description=description,
            category=category,
            version=version,
            created_at=created_at,
            updated_at=now,
            source_session=session_id,
        )
        records[key] = record.model_dump()
        self._write_records(records)
        return record

    def get_convention(self, key: str) -> Optional[ConventionRecord]:
        records = self._read_records()
        if key in records:
            return ConventionRecord(**records[key])
        return None

    def list_conventions(self) -> List[ConventionRecord]:
        records = self._read_records()
        return [ConventionRecord(**v) for v in records.values()]

    def delete_convention(self, key: str) -> bool:
        records = self._read_records()
        if key in records:
            del records[key]
            self._write_records(records)
            return True
        return False

    def clear(self) -> None:
        self._write_records({})

    def format_for_context(self) -> str:
        """
        Formats active persistent conventions for injection into the Agent's Context window (Slide 14 & 15).
        """
        conventions = self.list_conventions()
        if not conventions:
            return ""

        lines = [
            "============================================================",
            "[PERSISTENT PROJECT MEMORY & CONVENTIONS - INJECTED CONTEXT]",
            "The following conventions are active across sessions and MUST be strictly obeyed:",
        ]
        for c in conventions:
            desc_part = f" (Description: {c.description})" if c.description else ""
            lines.append(f"  • {c.key}: {c.value}{desc_part} [Version: v{c.version}]")
        lines.append("============================================================")
        return "\n".join(lines)

    def export_to_markdown(self) -> str:
        """Exports current memory state to formatted Markdown table."""
        conventions = self.list_conventions()
        if not conventions:
            return "_Persistent memory is currently empty._\n"

        md = ["| Key | Value | Description | Category | Version | Updated At | Session |",
              "| :--- | :--- | :--- | :--- | :---: | :--- | :--- |"]
        for c in conventions:
            md.append(f"| `{c.key}` | **{c.value}** | {c.description or ''} | {c.category} | v{c.version} | {c.updated_at[:19]} | {c.source_session or 'N/A'} |")
        return "\n".join(md) + "\n"
