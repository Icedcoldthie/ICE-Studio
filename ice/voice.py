from __future__ import annotations

import platform
import queue
import subprocess
import threading
from typing import Any


class VoiceEngine:
    """Optional local Windows TTS using built-in System.Speech."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.queue: queue.Queue[str] = queue.Queue(maxsize=20)
        self.running = True
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def update_config(self, config: dict[str, Any]) -> None:
        self.config = config

    def speak(self, text: str) -> None:
        if not self.config.get("voice_enabled", False):
            return
        if platform.system().lower() != "windows":
            return
        try:
            self.queue.put_nowait(text)
        except queue.Full:
            pass

    def stop(self) -> None:
        self.running = False

    def _worker(self) -> None:
        while self.running:
            text = self.queue.get()
            try:
                self._speak_windows(text)
            except Exception:
                pass
            finally:
                self.queue.task_done()

    def _speak_windows(self, text: str) -> None:
        voice_name = str(self.config.get("voice_name", "")).replace("'", "''")
        rate = int(self.config.get("voice_rate", 0))
        volume = int(self.config.get("voice_volume", 100))
        safe_text = text.replace("'", "''")
        select_voice = f"$s.SelectVoice('{voice_name}');" if voice_name else ""
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$s.Rate={max(-10, min(10, rate))};"
            f"$s.Volume={max(0, min(100, volume))};"
            f"{select_voice}"
            f"$s.Speak('{safe_text}');"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
