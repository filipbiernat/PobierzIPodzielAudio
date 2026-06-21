"""
Pobiera ścieżkę audio z YouTube i przenosi plik do folderu Google Drive.
"""

import os
import shutil
import sys
import PobierzAudio

DESTINATION_DIR = r"C:\Filip\GoogleDrive"


def main():
    # 1. Pobranie pliku audio do domyślnego katalogu roboczego
    print("Pobieranie pliku audio...")
    audio_file_path = PobierzAudio.handle_clipboard_and_dialog()

    if not audio_file_path:
        print("Nie udalo sie pobrac pliku audio.")
        sys.exit(1)

    print(f"Pobrano plik: {audio_file_path}")

    # 2. Weryfikacja, że plik faktycznie istnieje
    if not os.path.isfile(audio_file_path):
        print(f"Blad: plik nie istnieje pod sciezka: {audio_file_path}")
        print(f"Zawartość katalogu {os.getcwd()}:")
        for f in os.listdir("."):
            if f.endswith(".mp3"):
                print(f"  [mp3] {f}")
        sys.exit(1)

    # 3. Tworzenie folderu docelowego, jeśli nie istnieje
    if not os.path.exists(DESTINATION_DIR):
        try:
            os.makedirs(DESTINATION_DIR, exist_ok=True)
            print(f"Utworzono katalog docelowy: {DESTINATION_DIR}")
        except Exception as e:
            print(f"Nie mozna utworzyc katalogu docelowego {DESTINATION_DIR}: {e}")
            sys.exit(1)

    # 4. Przeniesienie pliku do Google Drive
    file_name = os.path.basename(audio_file_path)
    dest_path = os.path.join(DESTINATION_DIR, file_name)

    print(f"Przenoszenie: {audio_file_path}")
    print(f"         --> {dest_path}")
    try:
        shutil.move(audio_file_path, dest_path)
        print(f"Plik przeniesiony pomyslnie do Google Drive!")
    except Exception as e:
        print(f"Blad podczas przenoszenia pliku: {e}")
        print(f"  Zrodlo istnieje: {os.path.isfile(audio_file_path)}")
        print(f"  Cel istnieje:    {os.path.isdir(DESTINATION_DIR)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
