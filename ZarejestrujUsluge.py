"""
Rejestruje / wyrejestrowuje usługę PodzielAudio w Windows SCM.
Używa WinSW (Windows Service Wrapper) — github.com/winsw/winsw.

Użycie (wymaga uprawnień administratora):
    python ZarejestrujUsluge.py --install     Instaluje i uruchamia usługę
    python ZarejestrujUsluge.py --uninstall   Zatrzymuje i usuwa usługę
    python ZarejestrujUsluge.py --status      Sprawdza status usługi
    python ZarejestrujUsluge.py --start       Uruchamia usługę
    python ZarejestrujUsluge.py --stop        Zatrzymuje usługę
"""

import argparse
import ctypes
import io
import os
import shutil
import subprocess
import sys
import time
import urllib.request

# ── Wymuszenie UTF-8 na stdout/stderr ─────────────────────────────────────────

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Konfiguracja ──────────────────────────────────────────────────────────────

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
SERVICE_SCRIPT  = os.path.join(SCRIPT_DIR, "Usluga.py")

# WinSW — plik exe i xml muszą mieć tę samą nazwę bazową
WINSW_EXE       = os.path.join(SCRIPT_DIR, "PodzielAudio-service.exe")
WINSW_XML       = os.path.join(SCRIPT_DIR, "PodzielAudio-service.xml")
WINSW_LOG_DIR   = os.path.join(SCRIPT_DIR, "winsw-logs")

# WinSW v2.12.0 — ostatni stabilny release (winsw/winsw)
WINSW_DOWNLOAD  = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
WINSW_SHA256    = None  # Opcjonalna weryfikacja (pominięta dla prostoty)

SERVICE_ID      = "PodzielAudioUsluga"
SERVICE_NAME    = "PodzielAudio — Usługa HTTP"
SERVICE_DESC    = "Lokalna usługa HTTP na porcie 8765 dla skryptu Tampermonkey/YouTube."

# Stare zadania Task Scheduler do usunięcia przy instalacji
OLD_TASKS       = ["PodzielAudio_Usluga", "PodzielAudio_Watchdog"]


# ── Uprawnienia administratora ────────────────────────────────────────────────

def is_admin() -> bool:
    """Zwraca True jeśli proces ma uprawnienia administratora."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def require_admin():
    """Jeśli brak uprawnień, restartuje skrypt z UAC (runas) i kończy bieżący proces."""
    if is_admin():
        return
    print("🔐 Wymagane uprawnienia administratora — proszę potwierdzić UAC...")
    script = os.path.abspath(__file__)
    args   = " ".join(f'"{a}"' for a in sys.argv[1:])
    # ShellExecuteW z "runas" — wywołuje okno UAC
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas",
        sys.executable,
        f'"{script}" {args}',
        None, 1,   # SW_SHOWNORMAL
    )
    if ret <= 32:
        print(f"❌ Nie udało się uruchomić jako administrator (kod: {ret}).")
        sys.exit(1)
    sys.exit(0)


# ── WinSW: pobieranie i generowanie XML ───────────────────────────────────────

def find_python() -> str:
    """Zwraca ścieżkę do pythonw.exe (bez okna konsoli) lub python.exe."""
    python_dir = os.path.dirname(sys.executable)
    pythonw    = os.path.join(python_dir, "pythonw.exe")
    if os.path.isfile(pythonw):
        return pythonw
    found = shutil.which("pythonw")
    if found:
        return found
    print("⚠  Nie znaleziono pythonw.exe — użyję python.exe")
    return sys.executable


def download_winsw():
    """Pobiera WinSW.exe jeśli nie istnieje."""
    if os.path.isfile(WINSW_EXE):
        print(f"✅ WinSW już istnieje: {WINSW_EXE}")
        return

    print(f"⬇  Pobieranie WinSW z {WINSW_DOWNLOAD} ...")
    try:
        urllib.request.urlretrieve(WINSW_DOWNLOAD, WINSW_EXE)
        size_kb = os.path.getsize(WINSW_EXE) // 1024
        print(f"✅ WinSW pobrany ({size_kb} KB) → {WINSW_EXE}")
    except Exception as exc:
        print(f"❌ Błąd pobierania WinSW: {exc}")
        print(f"   Pobierz ręcznie z: {WINSW_DOWNLOAD}")
        print(f"   i zapisz jako:     {WINSW_EXE}")
        sys.exit(1)


def write_xml(python_exe: str):
    """Generuje plik konfiguracyjny WinSW XML."""
    os.makedirs(WINSW_LOG_DIR, exist_ok=True)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<service>

  <!-- Identyfikator usługi w Windows SCM -->
  <id>{SERVICE_ID}</id>
  <name>{SERVICE_NAME}</name>
  <description>{SERVICE_DESC}</description>

  <!-- Executable: pythonw.exe (bez okna konsoli) -->
  <executable>{python_exe}</executable>
  <arguments>"{SERVICE_SCRIPT}"</arguments>
  <workingdirectory>{SCRIPT_DIR}</workingdirectory>

  <!-- Uruchamiaj automatycznie przy starcie systemu -->
  <startmode>Automatic</startmode>

  <!-- Zmienne środowiskowe -->
  <env name="PYTHONIOENCODING" value="utf-8" />
  <env name="PYTHONUTF8"       value="1"     />

  <!-- Restart po awarii: 3 próby (5s / 15s / 30s), potem odczekaj 1 minutę -->
  <onfailure action="restart" delay="5  sec" />
  <onfailure action="restart" delay="15 sec" />
  <onfailure action="restart" delay="30 sec" />
  <resetfailure>1 min</resetfailure>

  <!-- Logowanie stdout/stderr przez WinSW (rotacja po 10 MB, 5 plików) -->
  <logpath>{WINSW_LOG_DIR}</logpath>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>5</keepFiles>
  </log>

</service>
"""
    with open(WINSW_XML, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"✅ Wygenerowano konfigurację: {WINSW_XML}")


def run_winsw(*args, check: bool = True) -> subprocess.CompletedProcess:
    """Uruchamia WinSW z podanymi argumentami."""
    cmd = [WINSW_EXE, *args]
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        check=False,
    )


def remove_old_tasks():
    """Usuwa stare zadania Task Scheduler (z poprzedniej wersji)."""
    for task in OLD_TASKS:
        result = subprocess.run(
            ["schtasks", "/delete", "/tn", task, "/f"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            print(f"🗑  Usunięto stare zadanie Task Scheduler: {task}")


# ── Komendy ───────────────────────────────────────────────────────────────────

def install():
    """Pobiera WinSW, generuje XML, instaluje i uruchamia usługę Windows."""
    python_exe = find_python()
    print(f"🐍 Python:   {python_exe}")
    print(f"📄 Skrypt:   {SERVICE_SCRIPT}\n")

    # 1. Pobierz WinSW jeśli brak
    download_winsw()

    # 2. Wygeneruj XML
    write_xml(python_exe)

    # 3. Usuń poprzednią instancję usługi (ignoruj błędy)
    print("\n🗑  Usuwam poprzednią instancję (jeśli istnieje)...")
    run_winsw("stop")
    time.sleep(1)
    run_winsw("uninstall")

    # 4. Usuń stare zadania Task Scheduler
    remove_old_tasks()

    # 5. Zainstaluj usługę
    print(f"\n📦 Instaluję usługę '{SERVICE_ID}'...")
    r = run_winsw("install")
    if r.returncode != 0:
        print(f"❌ Błąd instalacji:\n{r.stdout}\n{r.stderr}")
        sys.exit(1)
    print(f"✅ Usługa '{SERVICE_NAME}' zainstalowana!")

    # 6. Uruchom usługę
    print(f"\n🚀 Uruchamiam usługę...")
    r = run_winsw("start")
    if r.returncode != 0:
        print(f"❌ Błąd uruchomienia:\n{r.stdout}\n{r.stderr}")
        sys.exit(1)
    print(f"✅ Usługa uruchomiona!")

    # 7. Poczekaj chwilę i sprawdź status
    time.sleep(3)
    status(brief=True)

    print(f"\n💡 Zarządzaj usługą:")
    print(f"   services.msc    — GUI menedżer usług Windows")
    print(f"   sc query {SERVICE_ID}")
    print(f"   python ZarejestrujUsluge.py --status")


def uninstall():
    """Zatrzymuje i usuwa usługę Windows."""
    print(f"⏹  Zatrzymuję usługę '{SERVICE_ID}'...")
    run_winsw("stop")
    time.sleep(2)

    print(f"🗑  Usuwam usługę '{SERVICE_ID}'...")
    r = run_winsw("uninstall")
    if r.returncode != 0:
        err = (r.stdout + r.stderr).strip()
        if "does not exist" in err.lower() or "nie istnieje" in err.lower():
            print("ℹ️  Usługa już nie istnieje.")
        else:
            print(f"⚠  Kod powrotu: {r.returncode}\n{err}")
    else:
        print(f"✅ Usługa '{SERVICE_NAME}' usunięta.")

    remove_old_tasks()


def start():
    """Uruchamia usługę."""
    r = run_winsw("start")
    if r.returncode == 0:
        print(f"✅ Usługa '{SERVICE_ID}' uruchomiona.")
    else:
        print(f"❌ Błąd:\n{r.stdout}\n{r.stderr}")
        sys.exit(1)


def stop():
    """Zatrzymuje usługę."""
    r = run_winsw("stop")
    if r.returncode == 0:
        print(f"✅ Usługa '{SERVICE_ID}' zatrzymana.")
    else:
        print(f"❌ Błąd:\n{r.stdout}\n{r.stderr}")
        sys.exit(1)


def status(brief: bool = False):
    """Wyświetla status usługi przez sc query."""
    result = subprocess.run(
        ["sc", "query", SERVICE_ID],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    if result.returncode != 0:
        err = result.stderr or result.stdout
        if "1060" in err or "does not exist" in err.lower():
            print(f"ℹ️  Usługa '{SERVICE_ID}' nie jest zainstalowana.")
        else:
            print(f"Błąd sprawdzania statusu:\n{err}")
        return

    # Wyciągnij kluczowe linie
    print(f"\nStatus usługi '{SERVICE_NAME}':")
    for line in result.stdout.splitlines():
        line = line.strip()
        if any(k in line for k in ["STATE", "WIN32_EXIT", "SERVICE_NAME", "DISPLAY_NAME"]):
            print(f"   {line}")

    if not brief:
        # Sprawdź też port
        port_check = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        listening = [ln for ln in port_check.stdout.splitlines() if ":8765" in ln and "LISTENING" in ln]
        if listening:
            print(f"   PORT: 8765 LISTENING ✅")
        else:
            print(f"   PORT: 8765 — brak nasłuchu ⚠️")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Zarządzanie usługą PodzielAudio w Windows SCM (wymaga admina)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install",   action="store_true", help="Zainstaluj i uruchom usługę")
    group.add_argument("--uninstall", action="store_true", help="Zatrzymaj i usuń usługę")
    group.add_argument("--status",    action="store_true", help="Sprawdź status usługi")
    group.add_argument("--start",     action="store_true", help="Uruchom usługę")
    group.add_argument("--stop",      action="store_true", help="Zatrzymaj usługę")

    args = parser.parse_args()

    # Operacje modyfikujące wymagają admina
    if args.install or args.uninstall or args.start or args.stop:
        require_admin()

    if args.install:
        install()
    elif args.uninstall:
        uninstall()
    elif args.status:
        status()
    elif args.start:
        start()
    elif args.stop:
        stop()


if __name__ == "__main__":
    main()
