"""
Pomocnicze funkcje do lokalizowania narzędzi zewnętrznych (ffmpeg, deno)
używanych przez yt-dlp, niezależnie od zmiennych środowiskowych PATH.

Dlaczego to jest potrzebne:
  Usługa Windows uruchamiana jako LocalSystem nie dziedziczy PATH użytkownika.
  os.path.expanduser("~") zwraca C:\\Windows\\System32\\config\\systemprofile
  zamiast C:\\Users\\<nazwa>. Dlatego szukamy narzędzi przez glob we wszystkich
  profilach użytkowników i przekazujemy lokalizację bezpośrednio do yt-dlp.
"""

import glob
import os
import shutil


def _glob_users(subpath_with_filename: str) -> str | None:
    """
    Szuka pliku w profilach wszystkich użytkowników (C:\\Users\\*\\...).
    Zwraca pierwszą znalezioną ścieżkę lub None.
    """
    pattern = os.path.join(r"C:\Users\*", subpath_with_filename)
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def find_ffmpeg_dir() -> str | None:
    """
    Zwraca katalog zawierający ffmpeg.exe i ffprobe.exe, lub None gdy nie znaleziono.
    Kolejność prób:
      1. PATH (działa przy ręcznym uruchomieniu)
      2. Profil użytkownika — ffmpegio / ffmpeg-downloader (pip install ffmpegio)
      3. Profil użytkownika — scoop
      4. Standardowe katalogi systemowe
    """
    # 1. PATH
    found = shutil.which("ffmpeg")
    if found:
        return os.path.dirname(found)

    # 2-3. Profil użytkownika (glob)
    user_subpaths = [
        r"AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin\ffmpeg.exe",
        r"scoop\apps\ffmpeg\current\bin\ffmpeg.exe",
        r"AppData\Local\Programs\ffmpeg\bin\ffmpeg.exe",
    ]
    for subpath in user_subpaths:
        hit = _glob_users(subpath)
        if hit and os.path.isfile(hit):
            return os.path.dirname(hit)

    # 4. Standardowe ścieżki systemowe
    system_candidates = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
    ]
    for candidate in system_candidates:
        if os.path.isfile(os.path.join(candidate, "ffmpeg.exe")):
            return candidate

    return None


def find_deno_exe() -> str | None:
    """
    Zwraca pełną ścieżkę do deno.exe, lub None gdy nie znaleziono.
    Kolejność prób:
      1. PATH
      2. Profil użytkownika — ~/.deno/bin (standardowa instalacja Deno)
      3. Scoop
      4. Standardowe ścieżki systemowe
    """
    # 1. PATH
    found = shutil.which("deno")
    if found:
        return found

    # 2-3. Profil użytkownika (glob)
    user_subpaths = [
        r".deno\bin\deno.exe",
        r"scoop\apps\deno\current\deno.exe",
        r"AppData\Local\Programs\deno\deno.exe",
    ]
    for subpath in user_subpaths:
        hit = _glob_users(subpath)
        if hit and os.path.isfile(hit):
            return hit

    # 4. Standardowe ścieżki systemowe
    system_candidates = [
        r"C:\Program Files\deno\deno.exe",
        os.path.join(
            os.environ.get("PROGRAMFILES", r"C:\Program Files"), "deno", "deno.exe"
        ),
    ]
    for candidate in system_candidates:
        if os.path.isfile(candidate):
            return candidate

    return None


def extra_ytdlp_flags(need_ffmpeg: bool = True, need_deno: bool = True) -> list[str]:
    """
    Zwraca listę dodatkowych flag dla yt-dlp zapewniających dostęp do ffmpeg i deno,
    niezależnie od zmiennych środowiskowych (działa w kontekście usługi Windows).

    Przykład użycia:
        cmd = ["yt-dlp", *extra_ytdlp_flags(), "-x", "--audio-format", "mp3", ...]

    :param need_ffmpeg: Czy dodać --ffmpeg-location (potrzebne do konwersji audio)
    :param need_deno:   Czy dodać --js-runtimes deno (potrzebne do ekstrakcji YouTube JS)
    :return: Lista flag do wstawienia na początku komendy yt-dlp
    """
    flags = []

    if need_ffmpeg:
        ffmpeg_dir = find_ffmpeg_dir()
        if ffmpeg_dir:
            flags += ["--ffmpeg-location", ffmpeg_dir]
            print(f"ffmpeg znaleziony: {ffmpeg_dir}")
        else:
            print("⚠️  ffmpeg nie znaleziony — konwersja do MP3 może się nie powieść!")

    if need_deno:
        deno_exe = find_deno_exe()
        if deno_exe:
            flags += ["--js-runtimes", f"deno:{deno_exe}"]
            print(f"deno znaleziony: {deno_exe}")
        # Brak deno = yt-dlp wyświetli warning, ale pobierze (część formatów może nie być dostępna)

    return flags
