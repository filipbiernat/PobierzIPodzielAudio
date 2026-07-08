import subprocess
import sys
import tkinter as tk
import pyperclip  # Do obsługi schowka
import re
import os
import glob
import NarzedziaYtdlp  # Lokalizowanie deno niezależnie od PATH

def create_input_dialog(title, label_text, default_value, button_text):
    """
    Tworzy okno dialogowe do wprowadzania danych przez użytkownika.
    :param title: Tytuł okna
    :param label_text: Tekst etykiety
    :param default_value: Wartość domyślna w polu tekstowym
    :param button_text: Tekst na przycisku
    """
    def on_submit():
        global user_input
        user_input = entry.get()
        root.destroy()

    # Tworzenie głównego okna
    root = tk.Tk()
    root.title(title)
    root.geometry("600x150")
    root.wm_attributes('-topmost', 1)  # Okno na wierzchu
    root.focus_force()                 # Wymuszenie focusu
    # Etykieta z instrukcją
    label = tk.Label(root, text=label_text, font=("Arial", 12))
    label.pack(pady=10)
    # Pole tekstowe z domyślną wartością
    entry = tk.Entry(root, width=70, font=("Arial", 12))
    entry.insert(0, default_value)
    entry.pack(pady=5)
    # Przycisk zatwierdzający
    submit_button = tk.Button(root, text=button_text, command=on_submit, font=("Arial", 12))
    submit_button.pack(pady=10)
    # Uruchomienie pętli zdarzeń
    root.mainloop()

def download_audio(youtube_url, title=None):
    try:
        if title:
            # Tytuł przekazany z zewnątrz (np. z Tampermonkey) — pomijamy dialog
            video_title = title
            print(f"Tytuł przekazany jako argument: \"{video_title}\"")
        else:
            cmd_get_title = [
                "yt-dlp",
                "--get-title",
                youtube_url
            ]
            video_title = subprocess.check_output(cmd_get_title, encoding="utf-8", errors="replace").strip()

            create_input_dialog("Nazwa pliku z napisami", "Podaj nazwę pliku:", video_title, "Zapisz")
            video_title = user_input

        output_filename_without_extension = video_title.replace("/", " ").strip()

        cmd_download_subs = [
            "yt-dlp",
            *NarzedziaYtdlp.extra_ytdlp_flags(need_ffmpeg=False, need_deno=True),
            "--ignore-errors",
            "--retries", "10",
            "--write-auto-subs",
            "--sub-langs", "pl",
            "--sub-format", "vtt",
            "--skip-download",
            "-o", output_filename_without_extension + ".%(ext)s",
            youtube_url
        ]
        
        result = subprocess.run(cmd_download_subs,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        if result.stdout:
            print(result.stdout, end="", flush=True)
        if result.returncode != 0:
            print(f"yt-dlp zakończył z kodem błędu: {result.returncode}")
        
        # Sprawdź czy napisy istnieją
        subs_filename = f"{output_filename_without_extension}.pl.vtt"
        if not os.path.exists(subs_filename):
            # yt-dlp może nieznacznie zmienić nazwę pliku – szukaj przez glob
            matches = glob.glob("*.pl.vtt")
            if matches:
                subs_filename = max(matches, key=os.path.getmtime)
            else:
                subs_filename = None

        if subs_filename and os.path.exists(subs_filename):
            absolute_path = os.path.abspath(subs_filename)
            print(f"Napisy automatyczne zapisane jako: {absolute_path}")
            return absolute_path
        else:
            print("Nie udało się pobrać napisów. Możliwe przyczyny:")
            print("- Film nie ma automatycznych napisów")
            print("- YouTube zablokował pobieranie (spróbuj ponownie za kilka godzin)")
            print("- Błąd tymczasowy (sprawdź połączenie internetowe)")
            print("Pełny log błędu był wypisany powyżej.")
            return None
            
    except Exception as e:
        print(f"Krytyczny błąd: {str(e)}")
        return None

def get_youtube_url():
    """
    Tworzy okno dialogowe do wprowadzenia linku YouTube przez użytkownika.
    :return: Ścieżka do pobranego pliku z napisami
    """
    create_input_dialog("Pobieranie napisów z YouTube", "Podaj adres URL filmu na YouTube:", "https://", "Pobierz")
    if user_input.startswith("https://"):
        return download_audio(user_input)
    else:
        print("Nie podano prawidłowego adresu URL.")
        return None

def handle_clipboard_and_dialog():
    """
    Funkcja przetwarzająca URL i wywołująca okno dialogowe.
    Priorytet źródła URL:
      1. sys.argv[1] — przekazany przez Usługę (bezpieczne równoległe uruchamianie)
      2. Schowek        — fallback przy ręcznym uruchomieniu
      3. Okno dialogowe — gdy brak URL w obu źródłach
    Priorytet źródła tytułu:
      1. sys.argv[2] — przekazany przez Usługę (podany przez Tampermonkey)
      2. Okno dialogowe — gdy brak tytułu (interaktywne pytanie)
    Zwraca ścieżkę nowego pliku z napisami.
    :return: Ścieżka do pobranego pliku z napisami
    """
    youtube_pattern = re.compile(r"^https?://(www\.)?(youtube\.com|youtu\.be)/.*")

    # Tytuł opcjonalnie z argv[2] (przekazany przez Tampermonkey przez Usługę)
    title = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else None

    # 1. URL jako argument wiersza poleceń (przekazany przez Usluga.py)
    if len(sys.argv) > 1 and youtube_pattern.match(sys.argv[1]):
        print(f"URL przekazany jako argument: {sys.argv[1]}")
        return download_audio(sys.argv[1], title=title)

    # 2. Schowek (ręczne uruchomienie)
    clipboard_content = pyperclip.paste().strip()
    if youtube_pattern.match(clipboard_content):
        print(f"Znaleziono link w schowku: {clipboard_content}")
        return download_audio(clipboard_content, title=title)

    # 3. Okno dialogowe
    return get_youtube_url()

if __name__ == "__main__":
    handle_clipboard_and_dialog()
