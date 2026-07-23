from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import deque

import websocket

class StreamerBotClient:
    def __init__(self, config: dict, brain):
        self.config = config
        self.brain = brain
        self.ws = None
        self.thread = None
        self.running = False
        self.connected = False
        self.last_reply = 0.0
        self.reply_times = deque(maxlen=50)
        self.processing = threading.Lock()

    def update_config(self, config: dict):
        self.config = config

    def status(self) -> bool:
        return self.connected

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.connected = False
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def restart(self):
        self.stop()
        time.sleep(0.5)
        self.start()

    def _run_loop(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.config.get("streamerbot_ws", "ws://127.0.0.1:8080/"),
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception:
                self.connected = False
            if self.running:
                time.sleep(5)

    def _on_open(self, ws):
        self.connected = True
        request = {
            "request": "Subscribe",
            "id": str(uuid.uuid4()),
            "events": {"Twitch": ["ChatMessage"]},
        }
        ws.send(json.dumps(request))

    def _on_close(self, ws, code, message):
        self.connected = False

    def _on_error(self, ws, error):
        self.connected = False

    def _extract(self, payload: dict):
        data = payload.get("data", {}) or {}
        user = data.get("user")
        if isinstance(user, dict):
            username = user.get("display") or user.get("name") or user.get("login")
        else:
            username = data.get("displayName") or data.get("userName") or user

        message = data.get("message")
        if isinstance(message, dict):
            message = message.get("message") or message.get("text")
        message = message or data.get("text") or data.get("rawInput")
        return str(username or "").strip(), str(message or "").strip()

    def _should_reply(self, username: str, message: str) -> bool:
        if not username or not message:
            return False
        bot_name = self.config.get("bot_username", "").lower()
        if bot_name and username.lower() == bot_name:
            return False
        if self.config.get("ignore_commands", True) and message.startswith(("!", "/", ".")):
            return False

        mode = self.config.get("reply_mode", "smart")
        lower = message.lower()
        directly = "ice" in lower

        if mode == "all":
            return True
        if directly:
            return True

        now = time.time()
        cooldown = float(self.config.get("cooldown_seconds", 8))
        if now - self.last_reply < cooldown:
            return False

        while self.reply_times and now - self.reply_times[0] > 60:
            self.reply_times.popleft()
        if len(self.reply_times) >= int(self.config.get("max_messages_per_minute", 8)):
            return False

        greeting_or_question = (
            message.endswith("?")
            or any(x in lower for x in ["hallo", "hoi", "hey", "hoe gaat", "hello", "hi "])
        )
        chance = 0.85 if greeting_or_question else float(self.config.get("reply_chance", 0.35))
        return random.random() < chance

    def _on_message(self, ws, raw_message):
        try:
            payload = json.loads(raw_message)
        except Exception:
            return

        event = payload.get("event", {}) or {}
        if str(event.get("source", "")).lower() != "twitch":
            return
        if str(event.get("type", "")).lower() != "chatmessage":
            return

        username, message = self._extract(payload)
        if not self._should_reply(username, message):
            return

        threading.Thread(
            target=self._process,
            args=(username, message),
            daemon=True,
        ).start()

    def _process(self, username: str, message: str):
        if not self.processing.acquire(blocking=False):
            return
        try:
            result = self.brain.respond(username, message, source="twitch")
            for chunk in self.brain.split_for_twitch(result["answer"]):
                self._send_chat(chunk)
                time.sleep(1.2)
            now = time.time()
            self.last_reply = now
            self.reply_times.append(now)
        finally:
            self.processing.release()

    def _send_chat(self, text: str):
        if not self.ws:
            return
        request = {
            "request": "DoAction",
            "id": str(uuid.uuid4()),
            "action": {
                "name": self.config.get("streamerbot_action", "ICE - Send Chat")
            },
            "args": {"ice_message": text},
        }
        self.ws.send(json.dumps(request))
