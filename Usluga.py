"""
Usługa HTTP działająca w tle.
Nasłuchuje na localhost:8765 i uruchamia odpowiednie skrypty
na żądanie skryptu Tampermonkey z YouTube.

Uruchomienie:  python Usluga.py
               pythonw Usluga.py   (bez okna konsoli)
"""

import logging
import os
import subprocess
import sys
import threading
import uuid
from collections import deque
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Konfiguracja ──────────────────────────────────────────────────────────────

PORT = 8765
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)  # Wymuszenie katalogu roboczego (ważne dla Task Scheduler)

# Mapowanie akcji na skrypty
ACTIONS = {
    "pobierz_audio": "PobierzAudio.py",
    "pobierz_i_podziel_audio": "PobierzIPodzielAudio.py",
    "pobierz_napisy": "PobierzNapisy.py",
    "pobierz_audio_gdrive": "PobierzAudioIGoogleDrive.py",
}

# ── Rejestr zadań (buforowane logi dla pollingu) ───────────────────────────────

# task_id -> { status, lines: deque, started_at, finished_at }
_tasks: dict[str, dict] = {}
_tasks_lock = threading.Lock()

MAX_LINES = 500   # Maksymalna liczba linii logów w pamięci na zadanie
MAX_TASKS = 50    # Maksymalna liczba pamiętanych zadań (najstarsze usuwane)


def _task_new(task_id: str, script_name: str, url: str):
    with _tasks_lock:
        _tasks[task_id] = {
            "task_id": task_id,
            "script": script_name,
            "url": url,
            "status": "running",
            "lines": deque(maxlen=MAX_LINES),
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
        }
        # Usuń najstarsze zadanie jeśli przekroczono limit
        if len(_tasks) > MAX_TASKS:
            oldest = next(iter(_tasks))
            del _tasks[oldest]


def _task_append(task_id: str, line: str):
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id]["lines"].append(line)


def _task_finish(task_id: str, success: bool):
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id]["status"] = "done" if success else "error"
            _tasks[task_id]["finished_at"] = datetime.now().isoformat()


def _task_snapshot(task_id: str):
    """Zwraca kopię stanu zadania bezpieczną do serializacji JSON."""
    with _tasks_lock:
        t = _tasks.get(task_id)
        if t is None:
            return None
        return {
            "task_id": t["task_id"],
            "script": t["script"],
            "url": t["url"],
            "status": t["status"],
            "lines": list(t["lines"]),
            "started_at": t["started_at"],
            "finished_at": t["finished_at"],
        }


# ── Logowanie ─────────────────────────────────────────────────────────────────

log_path = os.path.join(SCRIPT_DIR, "Usluga.log")

log = logging.getLogger("Usluga")
log.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s")

_fh = logging.FileHandler(log_path, encoding="utf-8")
_fh.setFormatter(_fmt)
log.addHandler(_fh)

# Windows cp1252 nie obsługuje emoji — wymuszamy UTF-8 na strumieniu (tylko jeśli stdout istnieje)
if sys.stdout is not None and hasattr(sys.stdout, "fileno"):
    try:
        _sh = logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
            if sys.platform == "win32"
            else sys.stdout
        )
        _sh.setFormatter(_fmt)
        log.addHandler(_sh)
    except Exception:
        # Ignorujemy błędy strumienia konsoli pod pythonw
        pass

# ── Flask ─────────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)  # Pozwala na żądania z youtube.com


def _run_script(task_id: str, script_name: str, youtube_url: str):
    """Uruchamia skrypt w osobnym procesie, zbierając logi na bieżąco."""
    script_path = os.path.join(SCRIPT_DIR, script_name)

    def emit(line: str):
        """Dodaje linię do buforów: zadania i pliku logów."""
        _task_append(task_id, line)
        log.info("[%s] %s", task_id[:8], line)

    if not os.path.isfile(script_path):
        emit(f"❌ Skrypt nie istnieje: {script_path}")
        _task_finish(task_id, False)
        return

    emit(f"▶  Uruchamiam {script_name}")
    emit(f"🌐 URL: {youtube_url}")

    try:
        python_exe = sys.executable
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        # URL przekazywany jako argument — eliminuje race condition na schowku
        # przy równoległym uruchamianiu wielu skryptów.
        # Schowek kopiowany dodatkowo dla wygody (podgląd URL w systemie).
        try:
            import pyperclip
            pyperclip.copy(youtube_url)
            emit("📋 URL skopiowany do schowka (+ przekazany jako argument)")
        except Exception as exc:
            emit(f"⚠️  Nie udało się skopiować do schowka: {exc}")

        # CREATE_NO_WINDOW: gdy usługa Windows nie ma konsoli, bez tej flagi
        # Windows tworzy nowe okno konsoli dla procesu potomnego — stdout
        # trafia do tej konsoli zamiast do PIPE, więc Tampermonkey nic nie widzi.
        _no_window = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        process = subprocess.Popen(
            [python_exe, script_path, youtube_url],  # URL jako argv[1]
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # Łącz stderr ze stdout
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=_no_window,
        )

        # Czytaj logi na bieżąco — linia po linii
        collected_lines = []
        for line in process.stdout:
            stripped = line.rstrip("\n\r")
            emit(stripped)
            collected_lines.append(stripped)

        process.wait()
        success = process.returncode == 0

        if success:
            emit(f"✅ Zakończono pomyślnie (kod: {process.returncode})")
        else:
            emit(f"❌ Zakończono z błędem (kod: {process.returncode})")

        _task_finish(task_id, success)

        # ── Auto-aktualizacja yt-dlp ─────────────────────────────────────────
        # Wykryj warning yt-dlp o starości wersji i zaktualizuj po zakończeniu
        ytdlp_outdated = any(
            "older than" in line and "yt-dlp" in line.lower()
            for line in collected_lines
        )
        if ytdlp_outdated:
            emit("━" * 50)
            emit("🔄 Wykryto starą wersję yt-dlp — uruchamiam automatyczną aktualizację...")
            try:
                update_proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", "-U", "yt-dlp[default]"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    creationflags=_no_window,
                )
                for upd_line in update_proc.stdout:
                    emit(f"  {upd_line.rstrip()}")
                update_proc.wait()
                if update_proc.returncode == 0:
                    emit("✅ yt-dlp zaktualizowany pomyślnie!")
                else:
                    emit(f"⚠️  Aktualizacja zakończona kodem {update_proc.returncode}")
            except Exception as upd_exc:
                emit(f"⚠️  Błąd aktualizacji yt-dlp: {upd_exc}")

    except Exception as exc:
        emit(f"💥 Wyjątek: {exc}")
        _task_finish(task_id, False)


@app.route("/health", methods=["GET"])
def health():
    """Healthcheck — sprawdzenie czy usługa działa."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "available_actions": list(ACTIONS.keys()),
    })


@app.route("/run", methods=["POST"])
def run_action():
    """Uruchamia wybrany skrypt i zwraca task_id do śledzenia postępu."""
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    url = data.get("url", "")

    if action not in ACTIONS:
        return jsonify({
            "error": f"Nieznana akcja: '{action}'",
            "available_actions": list(ACTIONS.keys()),
        }), 400

    if not url:
        return jsonify({"error": "Brak pola 'url'"}), 400

    script_name = ACTIONS[action]
    task_id = str(uuid.uuid4())

    log.info("📨  Odebrano żądanie: action=%s  url=%s  task_id=%s", action, url, task_id)

    _task_new(task_id, script_name, url)

    thread = threading.Thread(
        target=_run_script,
        args=(task_id, script_name, url),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "status": "started",
        "task_id": task_id,
        "action": action,
        "script": script_name,
        "url": url,
    })


@app.route("/status/<task_id>", methods=["GET"])
def task_status(task_id: str):
    """Zwraca aktualny stan zadania i zebrane logi (do pollingu)."""
    # Opcjonalny parametr 'from' — klient może prosić tylko o nowe linie
    from_index = request.args.get("from", 0, type=int)

    snapshot = _task_snapshot(task_id)
    if snapshot is None:
        return jsonify({"error": "Nie znaleziono zadania"}), 404

    all_lines = snapshot["lines"]
    new_lines = all_lines[from_index:]

    return jsonify({
        "task_id": snapshot["task_id"],
        "script": snapshot["script"],
        "status": snapshot["status"],
        "started_at": snapshot["started_at"],
        "finished_at": snapshot["finished_at"],
        "total_lines": len(all_lines),
        "lines": new_lines,
    })


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("🚀  Usługa startuje na http://localhost:%d", PORT)
    log.info("📂  Katalog skryptów: %s", SCRIPT_DIR)
    log.info("📋  Dostępne akcje: %s", list(ACTIONS.keys()))

    # use_reloader=False — ważne przy uruchomieniu jako usługa/task scheduler
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
