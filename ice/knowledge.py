from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

class KnowledgeBase:
    def __init__(self, folder: Path):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)
        self.file = self.folder / "knowledge.json"
        self.lock = Lock()
        if not self.file.exists():
            self.file.write_text("[]", encoding="utf-8")
        self.items = self._load()

    def _load(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self):
        self.file.write_text(
            json.dumps(self.items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_entry(self, title: str, category: str, content: str, source: str = "manual"):
        with self.lock:
            item = {
                "id": max([x.get("id", 0) for x in self.items] + [0]) + 1,
                "title": title.strip(),
                "category": category.strip(),
                "content": content.strip(),
                "source": source.strip(),
            }
            self.items.append(item)
            self._save()
            return item

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        query = (query or "").strip().lower()
        if not query:
            return self.items[-limit:][::-1]

        words = [w for w in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", query) if len(w) > 2]
        ranked = []
        for item in self.items:
            haystack = " ".join([
                item.get("title", ""),
                item.get("category", ""),
                item.get("content", ""),
                item.get("source", ""),
            ]).lower()
            score = sum(haystack.count(word) for word in words)
            if query in haystack:
                score += 5
            if score > 0:
                ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:limit]]

    def context_for(self, query: str, limit: int = 5) -> tuple[str, list[str]]:
        items = self.search(query, limit)
        if not items:
            return "", []
        blocks = []
        sources = []
        for item in items:
            blocks.append(
                f"[{item['category']}] {item['title']}\n{item['content']}"
            )
            sources.append(item.get("source", "local"))
        return "\n\n".join(blocks), sources
