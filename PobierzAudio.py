import subprocess
import sys
import tkinter as tk
import pyperclip  # Do obsługi schowka
import re
import os

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

def download_audio(youtube_url):
    """
    Pobiera ścieżkę audio z podanego linku YouTube i zwraca ścieżkę do pobranego pliku.
    :param youtube_url: URL filmu na YouTube
    :return: Ścieżka do pobranego pliku MP3
    """
    try:
        # Pobranie tytułu filmu
        cmd_get_title = [
            "yt-dlp",
            "--get-title",
            youtube_url
        ]
        video_title = subprocess.check_output(cmd_get_title).decode("utf-8").strip()
        
        # Zapytanie użytkownika o nazwę pliku
        create_input_dialog("Nazwa pliku audio", "Podaj nazwę pliku:", video_title, "Zapisz")

        # Zastąp znaki niedozwolone w nazwach plików Windows
        illegal_chars = r'\/:*?"<>|'
        output_filename_without_extension = user_input
        for ch in illegal_chars:
            output_filename_without_extension = output_filename_without_extension.replace(ch, "#")
        output_filename_without_extension = output_filename_without_extension.strip()
        output_filename = f"{output_filename_without_extension}.mp3"
        
        print(f"Pobieranie ścieżki audio z filmu: \"{video_title}\" do pliku: \"{output_filename}\"")
        
        # Pobranie ścieżki audio i zapis jako MP3
        cmd_download_audio = [
            "yt-dlp",
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "--no-continue",          # Nie wznawiaj poprzedniego pobierania (.part)
            "-o", output_filename,
            youtube_url
        ]
        subprocess.run(cmd_download_audio)
        
        # Weryfikacja: czy plik naprawdę istnieje?
        absolute_path = os.path.abspath(output_filename)
        if not os.path.isfile(absolute_path):
            # yt-dlp mógł nieznacznie zmienić nazwę — szukamy najnowszego .mp3
            import glob
            candidates = glob.glob("*.mp3")
            if candidates:
                absolute_path = os.path.abspath(max(candidates, key=os.path.getmtime))
                print(f"Znaleziono plik pod zmienioną nazwą: {absolute_path}")
            else:
                print("Nie znaleziono żadnego pliku .mp3 w katalogu roboczym!")
                return None
        
        print(f"Sciezka audio zapisana jako: {absolute_path}")
        return absolute_path

    except Exception as e:
        print(f"Wystąpił błąd: {e}")
        return None

def get_youtube_url():
    """
    Tworzy okno dialogowe do wprowadzenia linku YouTube przez użytkownika.
    :return: Ścieżka do pobranego pliku MP3
    """
    create_input_dialog("Pobieranie audio z YouTube", "Podaj adres URL filmu na YouTube:", "https://", "Pobierz")
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
    Zwraca ścieżkę nowego pliku audio.
    :return: Ścieżka do pobranego pliku MP3
    """
    youtube_pattern = re.compile(r"^https?://(www\.)?(youtube\.com|youtu\.be)/.*")

    # 1. URL jako argument wiersza poleceń (przekazany przez Usluga.py)
    if len(sys.argv) > 1 and youtube_pattern.match(sys.argv[1]):
        print(f"URL przekazany jako argument: {sys.argv[1]}")
        return download_audio(sys.argv[1])

    # 2. Schowek (ręczne uruchomienie)
    clipboard_content = pyperclip.paste().strip()
    if youtube_pattern.match(clipboard_content):
        print(f"Znaleziono link w schowku: {clipboard_content}")
        return download_audio(clipboard_content)

    # 3. Okno dialogowe
    return get_youtube_url()

if __name__ == "__main__":
    handle_clipboard_and_dialog()

#pip install -U "yt-dlp[default]"