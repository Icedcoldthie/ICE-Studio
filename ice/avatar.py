from __future__ import annotations

import re
import threading
import time
from typing import Any


class AvatarController:
    """Thread-safe state shared by ICE and the OBS browser avatar."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.lock = threading.Lock()
        self.revision = 0
        self.state: dict[str, Any] = {
            "revision": 0,
            "text": "",
            "speaker": "ICE",
            "emotion": "neutral",
            "outfit": config.get("avatar_outfit", "farmer"),
            "visible": True,
            "speaking": False,
            "speaking_until": 0.0,
        }

    def update_config(self, config: dict[str, Any]) -> None:
        self.config = config
        with self.lock:
            self.state["outfit"] = config.get("avatar_outfit", "farmer")

    def detect_emotion(self, text: str) -> str:
        value = text.lower()
        rules = [
            ("thinking", ["even denken", "ik denk", "hmm", "let me think"]),
            ("surprised", ["wow", "serieus", "wat?!", "no way", "ongelooflijk"]),
            ("laughing", ["haha", "hahaha", "😂", "grappig", "lol"]),
            ("excited", ["geweldig", "top!", "lekker!", "yes!", "awesome", "fantastisch"]),
            ("concerned", ["voorzichtig", "dierenarts", "gevaar", "zorgelijk", "pas op"]),
            ("annoyed", ["niet slim", "kom op", "alweer", "serieus sander"]),
            ("happy", ["graag", "leuk", "welkom", "goed bezig", "mooi"]),
        ]
        for emotion, needles in rules:
            if any(needle in value for needle in needles):
                return emotion
        return "neutral"

    def publish_response(self, text: str, speaker: str = "ICE", emotion: str | None = None) -> dict[str, Any]:
        text = re.sub(r"\s+", " ", text).strip()
        emotion = emotion or self.detect_emotion(text)
        # Reading time is used only for animation; it is not an answer-length cap.
        duration = min(max(len(text) / 15.0, 2.0), 45.0)
        with self.lock:
            self.revision += 1
            self.state.update({
                "revision": self.revision,
                "text": text,
                "speaker": speaker,
                "emotion": emotion,
                "outfit": self.config.get("avatar_outfit", "farmer"),
                "visible": bool(self.config.get("avatar_visible", True)),
                "speaking": True,
                "speaking_until": time.time() + duration,
            })
            return dict(self.state)

    def set_emotion(self, emotion: str) -> dict[str, Any]:
        allowed = {"neutral", "happy", "laughing", "surprised", "thinking", "excited", "concerned", "annoyed"}
        if emotion not in allowed:
            emotion = "neutral"
        with self.lock:
            self.revision += 1
            self.state.update({"revision": self.revision, "emotion": emotion})
            return dict(self.state)

    def set_outfit(self, outfit: str) -> dict[str, Any]:
        with self.lock:
            self.revision += 1
            self.state.update({"revision": self.revision, "outfit": outfit})
            return dict(self.state)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            result = dict(self.state)
        if result.get("speaking") and time.time() >= float(result.get("speaking_until", 0)):
            with self.lock:
                self.state["speaking"] = False
                result = dict(self.state)
        return result
