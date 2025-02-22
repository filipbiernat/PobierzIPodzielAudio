from pydub import AudioSegment
from gtts import gTTS
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Funkcje generujące liczebniki i opisy segmentów
def liczebnik_porządkowy(n):
    jednostki_porządkowe = ["pierwszy", "drugi", "trzeci", "czwarty", "piąty", 
                            "szósty", "siódmy", "ósmy", "dziewiąty"]
    nastki_porządkowe = ["jedenasty", "dwunasty", "trzynasty", "czternasty", 
                         "piętnasty", "szesnasty", "siedemnasty", "osiemnasty", "dziewiętnasty"]
    dziesiątki_porządkowe = ["dziesiąty", "dwudziesty", "trzydziesty", 
                             "czterdziesty", "pięćdziesiąty", "sześćdziesiąty", 
                             "siedemdziesiąty", "osiemdziesiąty", "dziewięćdziesiąty"]
    setki_porządkowe = ["setny", "dwusetny", "trzysetny", "czterysetny", 
                        "pięćsetny", "sześćsetny", "siedemsetny", "osiemsetny", "dziewięćsetny"]

    if n <= 9:
        return jednostki_porządkowe[n - 1]
    elif 10 < n < 20:
        return nastki_porządkowe[n - 11]
    elif n % 10 == 0 and n < 100:
        return dziesiątki_porządkowe[n // 10 - 1]
    elif n < 100:
        return dziesiątki_porządkowe[n // 10 - 1][:-1] + jednostki_porządkowe[n % 10 - 1]
    elif n % 100 == 0 and n < 1000:
        return setki_porządkowe[n // 100 - 1]
    else:
        return f"{n}-ty"

def liczebnik_glowny(n):
    jednostki_glowne = ["", "jednego", "dwóch", "trzech", "czterech", "pięciu", 
                        "sześciu", "siedmiu", "ośmiu", "dziewięciu"]
    nastki_glowne = ["jedenastu", "dwunastu", "trzynastu", "czternastu", 
                     "piętnastu", "szesnastu", "siedemnastu", "osiemnastu", "dziewiętnastu"]
    dziesiątki_glowne = ["dziesięciu", "dwudziestu", "trzydziestu", 
                         "czterdziestu", "pięćdziesięciu", "sześćdziesięciu", 
                         "siedemdziesięciu", "osiemdziesięciu", "dziewięćdziesięciu"]
    setki_glowne = ["stu", "dwustu", "trzystu", "czterystu", "pięciuset", 
                    "sześciuset", "siedmiuset", "osiemset", "dziewięćset"]

    if n <= 9:
        return jednostki_glowne[n]
    elif 10 < n < 20:
        return nastki_glowne[n - 11]
    elif n % 10 == 0 and n < 100:
        return dziesiątki_glowne[n // 10 - 1]
    elif n < 100:
        return f"{dziesiątki_glowne[n // 10 - 1]} {jednostki_glowne[n % 10]}".strip()
    elif n % 100 == 0 and n < 1000:
        return setki_glowne[n // 100 - 1]
    elif n < 1000:
        return f"{setki_glowne[n // 100 - 1]} {dziesiątki_glowne[(n % 100) // 10 - 1] if (n % 100) // 10 != 0 else ''} {jednostki_glowne[n % 10]}".strip()
    else:
        return str(n)

def opis_segmentu(numer, liczba_segmentow, nazwa_pliku):
    porzadkowy = liczebnik_porządkowy(numer)
    glowny = liczebnik_glowny(liczba_segmentow)
    return f"{nazwa_pliku} - segment {porzadkowy} z {glowny}"

# 1. Funkcja wyboru pliku
def wybierz_plik():
    root = Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    print("Wybierz plik MP3 do podzielenia...")
    file_path = askopenfilename(filetypes=[("Pliki MP3", "*.mp3")])
    root.destroy()
    return file_path

# 2. Nowa funkcja do przetwarzania pliku
def przetworz_plik(input_filename=None):
    # Jeśli nie podano ścieżki, otwieramy okno wyboru pliku
    if not input_filename:
        input_filename = wybierz_plik()
    
    if not input_filename:
        print("Nie wybrano pliku. Zakończono działanie skryptu.")
        exit()

    print(f"Wybrano plik: {input_filename}")

    # 3. Wczytaj plik MP3
    try:
        audio = AudioSegment.from_mp3(input_filename)
    except Exception as e:
        print(f"Błąd przy wczytywaniu pliku: {e}")
        exit()

    print("Plik został pomyślnie wczytany.")

    # 4. Przygotowanie katalogu wyjściowego
    base_name = os.path.splitext(os.path.basename(input_filename))[0]
    output_dir = os.path.join(os.path.dirname(input_filename), base_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Nowy folder na segmenty został utworzony: {output_dir}")

    # 5. Parametry segmentów
    segment_duration = 5 * 60 * 1000
    total_length = len(audio)
    total_segments = (total_length + segment_duration - 1) // segment_duration

    # 6. Tworzenie ciszy
    silence_1_sec = AudioSegment.silent(duration=1000)
    silence_2_sec = AudioSegment.silent(duration=2000)

    # 7. Podział i zapis segmentów
    for i in range(total_segments):
        start = i * segment_duration
        end = min(start + segment_duration, total_length)
        
        # Generowanie tytułu z uwzględnieniem nazwy pliku
        segment_title = opis_segmentu(i + 1, total_segments, base_name)
        
        # Debug: wypisanie tytułu, który ma być zamieniony na mowę
        print(f"\nGeneruję mowę dla tytułu: '{segment_title}'")
        
        # Tworzenie segmentu audio
        segment = audio[start:end]
        
        # Ścieżka do tymczasowego pliku w folderze docelowym
        temp_filename = os.path.join(output_dir, "temp_title.mp3")
        
        # Konwersja tytułu na mowę i zapis do pliku tymczasowego
        speech_generator = gTTS(text=segment_title, lang='pl')
        speech_generator.save(temp_filename)
        title_audio = AudioSegment.from_mp3(temp_filename)

        # Łączenie tytułu, ciszy i segmentu
        final_segment = title_audio + silence_1_sec + segment + silence_2_sec
        segment_filename = f"{base_name}_{i + 1:02}.mp3"
        segment_filepath = os.path.join(output_dir, segment_filename)
        
        print(f"Zapisuję segment jako {segment_filepath}...")
        try:
            final_segment.export(segment_filepath, format="mp3")
            print(f"Segment {i + 1} zapisany pomyślnie.")
        except Exception as e:
            print(f"Błąd przy zapisie segmentu {i + 1}: {e}")

        # Usunięcie tymczasowego pliku z tytułem
        os.remove(temp_filename)

    print("\nPlik został pomyślnie podzielony na segmenty 5-minutowe i zapisany w nowym folderze.")

# 3. Wywołanie w main
if __name__ == "__main__":
    przetworz_plik()
