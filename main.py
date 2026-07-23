from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import uvicorn

from ice.avatar import AvatarController
from ice.brain import IceBrain
from ice.memory import MemoryStore
from ice.knowledge import KnowledgeBase
from ice.games import GameDatabase
from ice.streamerbot import StreamerBotClient
from ice.voice import VoiceEngine

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


config = load_config()
memory = MemoryStore(BASE_DIR / "ice_memory.db")
knowledge = KnowledgeBase(BASE_DIR / "knowledge")
games = GameDatabase()
avatar = AvatarController(config)
voice = VoiceEngine(config)
brain = IceBrain(config, memory, knowledge, games)
streamerbot = StreamerBotClient(config, brain)


def publish_ice_response(text: str) -> None:
    avatar.publish_response(text)
    voice.speak(text)


brain.set_event_callback(publish_ice_response)

app = FastAPI(title="ICE Studio 1.1")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def startup_event():
    streamerbot.start()


@app.on_event("shutdown")
def shutdown_event():
    streamerbot.stop()
    voice.stop()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "config": config})


@app.get("/avatar", response_class=HTMLResponse)
def avatar_page(request: Request):
    return templates.TemplateResponse("avatar.html", {"request": request, "config": config})


@app.get("/api/status")
def api_status():
    return {
        "version": "1.1",
        "ollama": brain.check_ollama(),
        "streamerbot": streamerbot.status(),
        "model": config["ollama_model"],
        "outfit": config.get("avatar_outfit", "farmer"),
        "voice": config.get("voice_enabled", False),
        "avatar": config.get("avatar_visible", True),
        "stats": memory.get_stats(),
    }


@app.post("/api/chat")
def api_chat(username: str = Form(...), message: str = Form(...)):
    return brain.respond(username, message, source="dashboard")


@app.post("/api/feedback")
def api_feedback(interaction_id: int = Form(...), rating: str = Form(...), correction: str = Form("")):
    memory.save_feedback(interaction_id, rating, correction)
    if correction.strip():
        knowledge.add_entry(
            title=f"Correctie op antwoord {interaction_id}",
            category="approved_corrections",
            content=correction.strip(),
            source="dashboard_feedback",
        )
    return {"ok": True}


@app.get("/api/history")
def api_history(limit: int = 50):
    return {"items": memory.get_history(limit)}


@app.get("/api/knowledge")
def api_knowledge(query: str = ""):
    return {"items": knowledge.search(query, limit=50)}


@app.post("/api/knowledge")
def api_add_knowledge(title: str = Form(...), category: str = Form(...), content: str = Form(...), source: str = Form("manual")):
    return {"ok": True, "item": knowledge.add_entry(title, category, content, source)}


@app.get("/api/games/search")
def api_games_search(query: str):
    return {"items": games.search(query)}


@app.get("/api/avatar/state")
def api_avatar_state():
    return avatar.snapshot()


@app.post("/api/avatar/test")
def api_avatar_test(text: str = Form("Hallo! Ik ben ICE, je digitale cohost."), emotion: str = Form("neutral")):
    state = avatar.publish_response(text, emotion=emotion)
    voice.speak(text)
    return {"ok": True, "state": state}


@app.post("/api/avatar/emotion")
def api_avatar_emotion(emotion: str = Form(...)):
    return {"ok": True, "state": avatar.set_emotion(emotion)}


@app.post("/api/avatar/outfit")
def api_avatar_outfit(outfit: str = Form(...)):
    global config
    config["avatar_outfit"] = outfit
    save_config(config)
    avatar.update_config(config)
    return {"ok": True, "state": avatar.set_outfit(outfit)}


@app.post("/api/settings")
def api_settings(payload: dict):
    global config
    config.update(payload)
    save_config(config)
    brain.update_config(config)
    streamerbot.update_config(config)
    avatar.update_config(config)
    voice.update_config(config)
    return {"ok": True, "config": config}


@app.post("/api/streamerbot/reconnect")
def api_streamerbot_reconnect():
    streamerbot.restart()
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=False)
