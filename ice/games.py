from __future__ import annotations

from typing import Any
import requests

class GameDatabase:
    SEARCH_URL = "https://store.steampowered.com/api/storesearch/"

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        try:
            response = requests.get(
                self.SEARCH_URL,
                params={"term": query, "l": "dutch", "cc": "NL"},
                timeout=12,
                headers={"User-Agent": "ICE-Studio/1.0"},
            )
            response.raise_for_status()
            data = response.json()
            items = []
            for item in data.get("items", [])[:limit]:
                items.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "price": (item.get("price") or {}).get("final_formatted", ""),
                    "image": item.get("tiny_image", ""),
                    "platforms": item.get("platforms", {}),
                    "source": "Steam Store",
                })
            return items
        except Exception as exc:
            return [{
                "name": query,
                "error": f"Steam niet bereikbaar: {exc}",
                "source": "Steam Store",
            }]

    def context_for(self, query: str) -> tuple[str, list[str]]:
        items = self.search(query, limit=5)
        valid = [x for x in items if not x.get("error")]
        if not valid:
            return "", []
        lines = []
        for item in valid:
            platforms = ", ".join(
                name for name, enabled in item.get("platforms", {}).items() if enabled
            )
            lines.append(
                f"{item.get('name')} | prijs: {item.get('price') or 'onbekend'} | "
                f"platformen: {platforms or 'onbekend'} | Steam app-id: {item.get('id')}"
            )
        return "\n".join(lines), ["Steam Store"]
