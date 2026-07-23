from __future__ import annotations

import json
import re
from typing import Any
import requests

class IceBrain:
    def __init__(self, config: dict, memory, knowledge, games):
        self.config = config
        self.memory = memory
        self.knowledge = knowledge
        self.games = games
        self.event_callback = None

    def update_config(self, config: dict):
        self.config = config

    def set_event_callback(self, callback):
        self.event_callback = callback

    def check_ollama(self) -> bool:
        try:
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            return response.ok
        except Exception:
            return False

    def detect_language(self, text: str) -> str:
        lower = text.lower()
        dutch_markers = [" de ", " het ", " een ", " hoe ", " wat ", " waarom ", " mijn ", " jouw ", " ratten"]
        english_markers = [" the ", " how ", " what ", " why ", " my ", " your ", " game "]
        dutch = sum(marker in f" {lower} " for marker in dutch_markers)
        english = sum(marker in f" {lower} " for marker in english_markers)
        return "en" if english > dutch else "nl"

    def _is_game_question(self, message: str) -> bool:
        lower = message.lower()
        markers = [
            "steam", "game", "spel", "dlc", "releasedatum", "release date",
            "multiplayer", "singleplayer", "co-op", "coop", "ontwikkelaar",
            "developer", "uitgever", "publisher"
        ]
        return any(x in lower for x in markers)

    def _build_system_prompt(self, language: str) -> str:
        p = self.config.get("personality", {})
        style = self.config.get("response_style", "auto")
        return f'''
Je bent ICE: Intelligent Cohost Engine, de digitale cohost van Twitch-streamer IcedColdThie.

Taal:
- Antwoord in het Nederlands als de kijker Nederlands schrijft.
- Antwoord in het Engels als de kijker Engels schrijft.
- Gedetecteerde voorkeur: {language}.

Gedrag:
- Reageer natuurlijk als een echte cohost.
- Wees vriendelijk, spontaan en behulpzaam.
- Humor: {p.get("humor", 70)}/100.
- Sarcasme: {p.get("sarcasm", 35)}/100, nooit gemeen.
- Energie: {p.get("energy", 65)}/100.
- Vriendelijkheid: {p.get("friendly", 85)}/100.
- Antwoordstijl: {style}.
- Er is geen vaste maximale antwoordlengte.
- Kies zelf hoeveel uitleg nodig is.
- Korte sociale berichten mogen kort zijn.
- Inhoudelijke vragen mogen uitgebreid worden beantwoord.
- Gebruik geen markdown-tabellen in Twitch-antwoorden.
- Verzin geen feiten.
- Maak duidelijk wanneer informatie onzeker is.
- Gebruik aangeleverde kennis als belangrijkste bron.
- Medische vragen over mensen of dieren: geef algemene informatie en adviseer een deskundige bij alarmsignalen.
- Schrijf alleen ICE zijn antwoord, zonder analyse of denkstappen.
'''

    def _build_context(self, username: str, message: str) -> tuple[str, list[str]]:
        local_context, local_sources = self.knowledge.context_for(message, limit=6)
        game_context = ""
        game_sources = []
        if self._is_game_question(message):
            game_context, game_sources = self.games.context_for(message)

        recent = self.memory.recent_context(10)
        recent_lines = []
        for row in recent:
            recent_lines.append(
                f"{row['username']}: {row['message']}\nICE: {row['answer']}"
            )

        sections = [
            f"Nieuw bericht van {username}:\n{message}",
        ]
        if local_context:
            sections.append("Lokale kennisbank:\n" + local_context)
        if game_context:
            sections.append("Game-informatie uit Steam:\n" + game_context)
        if recent_lines:
            sections.append("Recente gesprekken:\n" + "\n\n".join(recent_lines))

        return "\n\n".join(sections), list(dict.fromkeys(local_sources + game_sources))

    def _clean_answer(self, answer: str) -> str:
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S | re.I)
        answer = answer.replace("<think>", "").replace("</think>", "")
        return answer.strip()

    def respond(self, username: str, message: str, source: str = "twitch") -> dict[str, Any]:
        self.memory.remember_viewer(username)
        language = self.detect_language(message)
        context, sources = self._build_context(username, message)

        payload = {
            "model": self.config.get("ollama_model", "qwen3:4b"),
            "messages": [
                {"role": "system", "content": self._build_system_prompt(language)},
                {"role": "user", "content": context},
            ],
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.75,
                "repeat_penalty": 1.1,
                "num_predict": -1,
            },
        }

        try:
            response = requests.post(
                self.config.get("ollama_url", "http://127.0.0.1:11434/api/chat"),
                json=payload,
                timeout=180,
            )
            response.raise_for_status()
            answer = self._clean_answer(
                response.json().get("message", {}).get("content", "")
            )
        except Exception as exc:
            answer = (
                "Ik kan mijn lokale AI-brein nu niet bereiken. "
                f"Controleer of Ollama draait. Technische melding: {exc}"
            )

        interaction_id = self.memory.save_interaction(
            username=username,
            message=message,
            answer=answer,
            source=source,
            detected_language=language,
            knowledge_used=", ".join(sources),
        )

        if self.event_callback:
            try:
                self.event_callback(answer)
            except Exception:
                pass

        return {
            "id": interaction_id,
            "username": username,
            "message": message,
            "answer": answer,
            "language": language,
            "sources": sources,
        }

    def split_for_twitch(self, text: str, limit: int = 430) -> list[str]:
        if not self.config.get("split_long_twitch_messages", True):
            return [text]
        text = text.strip()
        if len(text) <= limit:
            return [text]

        chunks = []
        remaining = text
        while len(remaining) > limit:
            split_at = max(
                remaining.rfind(". ", 0, limit),
                remaining.rfind("? ", 0, limit),
                remaining.rfind("! ", 0, limit),
                remaining.rfind(" ", 0, limit),
            )
            if split_at < limit // 2:
                split_at = limit
            chunk = remaining[:split_at + 1].strip()
            chunks.append(chunk)
            remaining = remaining[split_at + 1:].strip()
        if remaining:
            chunks.append(remaining)
        return chunks
