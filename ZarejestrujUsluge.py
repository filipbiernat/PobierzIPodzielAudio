"""
Rejestruje / wyrejestrowuje usługę PodzielAudio w Harmonogramie Zadań Windows.

Użycie:
    python ZarejestrujUsluge.py --install     Rejestruje zadanie (autostart przy logowaniu)
    python ZarejestrujUsluge.py --uninstall   Usuwa zadanie
    python ZarejestrujUsluge.py --status       Sprawdza status zadania
"""

import argparse
import os
import subprocess
import sys
import shutil

TASK_NAME = "PodzielAudio_Usluga"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_SCRIPT = os.path.join(SCRIPT_DIR, "Usluga.py")


def find_pythonw():
    """Znajduje ścieżkę do pythonw.exe (uruchamianie bez okna konsoli)."""
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if os.path.isfile(pythonw):
        return pythonw
    # Fallback: szukaj w PATH
    found = shutil.which("pythonw")
    if found:
        return found
    # Ostateczny fallback: użyj python.exe
    print("⚠  Nie znaleziono pythonw.exe — użyję python.exe (będzie widoczne okno konsoli)")
    return sys.executable


def install():
    """Rejestruje zadanie w Task Scheduler."""
    pythonw = find_pythonw()

    # Najpierw usuń istniejące zadanie (jeśli jest)
    uninstall(quiet=True)

    # schtasks /create ...
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{pythonw}" "{SERVICE_SCRIPT}"',
        "/sc", "onlogon",       # Uruchom przy logowaniu
        "/ru", "",              # Uruchom w kontekście zalogowanego użytkownika
        "/f",                   # Nadpisz istniejące
    ]

    print(f"Rejestruje zadanie: {TASK_NAME}")
    print(f"   Python:  {pythonw}")
    print(f"   Skrypt:  {SERVICE_SCRIPT}")

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode == 0:
        print(f"Sukces: Zadanie '{TASK_NAME}' zarejestrowane pomyslnie!")
        print("   Usluga uruchomi sie automatycznie przy nastepnym logowaniu.")
        print(f"\n   Aby uruchomic teraz:  schtasks /run /tn \"{TASK_NAME}\"")
    else:
        print(f"Blad rejestracji:")
        print(result.stderr or result.stdout)
        sys.exit(1)


def uninstall(quiet=False):
    """Usuwa zadanie z Task Scheduler."""
    cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode == 0:
        if not quiet:
            print(f"Sukces: Zadanie '{TASK_NAME}' usuniete.")
    else:
        if not quiet:
            if "nie mozna odnalezc" in result.stderr.lower() or "cannot find" in result.stderr.lower():
                print(f"Info: Zadanie '{TASK_NAME}' nie istnieje.")
            else:
                print(f"Blad usuwania:")
                print(result.stderr or result.stdout)


def status():
    """Sprawdza status zadania."""
    cmd = ["schtasks", "/query", "/tn", TASK_NAME, "/v", "/fo", "list"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode == 0:
        print(f"Status zadania '{TASK_NAME}':\n")
        # Wyciągnij kluczowe informacje
        for line in result.stdout.splitlines():
            line = line.strip()
            if any(key in line for key in ["Status", "Nazwa zadania", "Task Name",
                                            "Nastepne uruchomienie", "Next Run",
                                            "Ostatnie uruchomienie", "Last Run",
                                            "Ostatni wynik", "Last Result",
                                            "Akcja", "Task To Run"]):
                print(f"   {line}")
    else:
        if "nie mozna odnalezc" in result.stderr.lower() or "cannot find" in result.stderr.lower():
            print(f"Info: Zadanie '{TASK_NAME}' nie jest zarejestrowane.")
        else:
            print(f"Blad sprawdzania statusu:")
            print(result.stderr or result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Zarządzanie usługą PodzielAudio w Task Scheduler")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true", help="Zarejestruj zadanie (autostart)")
    group.add_argument("--uninstall", action="store_true", help="Usuń zadanie")
    group.add_argument("--status", action="store_true", help="Sprawdź status zadania")

    args = parser.parse_args()

    if args.install:
        install()
    elif args.uninstall:
        uninstall()
    elif args.status:
        status()


if __name__ == "__main__":
    main()
