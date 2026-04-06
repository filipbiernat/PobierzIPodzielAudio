import subprocess

import tkinter as tk

import pyperclip  # Do obsługi schowka

import re

import os

import glob

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

def download_audio(youtube_url):
    try:
        cmd_get_title = [
            "yt-dlp",
            "--get-title",
            youtube_url
        ]
        video_title = subprocess.check_output(cmd_get_title, encoding="utf-8", errors="replace").strip()
        
        create_input_dialog("Nazwa pliku z napisami", "Podaj nazwę pliku:", video_title, "Zapisz")
        output_filename_without_extension = user_input.replace("/", " ").strip()

        cmd_download_subs = [
            "yt-dlp",
            "--ignore-errors",
            "--retries", "10",
            "--write-auto-subs",
            "--sub-langs", "pl",
            "--sub-format", "vtt",
            "--skip-download",
            "-o", output_filename_without_extension + ".%(ext)s",
            youtube_url
        ]
        
        result = subprocess.run(cmd_download_subs, capture_output=True, text=True, encoding="utf-8", errors="replace")
        
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
            print("Pełny log błędu:\n", result.stderr)
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
    Funkcja przetwarzająca zawartość schowka lub wywołująca okno dialogowe do wprowadzenia URL.
    Zwraca ścieżkę nowego pliku z napisami.
    :return: Ścieżka do pobranego pliku z napisami
    """
    # Sprawdzenie zawartości schowka
    clipboard_content = pyperclip.paste().strip()
    youtube_pattern = re.compile(r"^https?://(www\.)?(youtube\.com|youtu\.be)/.*")
    # Jeśli w schowku znajduje się link do YouTube, użyj go, w przeciwnym razie wywołaj okno dialogowe
    if youtube_pattern.match(clipboard_content):
        print(f"Znaleziono link w schowku: {clipboard_content}")
        return download_audio(clipboard_content)
    else:
        return get_youtube_url()

if __name__ == "__main__":
    handle_clipboard_and_dialog()
