# Pobierz i Podziel Audio (YouTube Tools)

Zestaw skryptów w Pythonie oraz skrypt użytkownika Tampermonkey umożliwiający wygodne pobieranie ścieżki dźwiękowej z filmów na YouTube, dzielenie plików audio na 5-minutowe fragmenty z zapowiedziami głosowymi (TTS) oraz pobieranie i konwersję napisów bezpośrednio z poziomu przeglądarki.

---

## 🛠️ Opis skryptów

1. **`Usluga.py`**  
   Lokalna usługa w tle (serwer Flask na `http://localhost:8765`), która przyjmuje żądania od skryptu w przeglądarce, zapisuje linki w schowku systemowym i uruchamia odpowiednie skrypty przetwarzające.

2. **`PodzielAudio.user.js`**  
   Skrypt użytkownika dla wtyczki Tampermonkey. Dodaje przycisk **🎵 Pobierz** z menu rozwijanym pod odtwarzaczem YouTube, pozwalając na wywołanie lokalnej usługi za pomocą jednego kliknięcia.

3. **`PobierzAudio.py`**  
   Pobiera ścieżkę dźwiękową z filmu YouTube i zapisuje ją w formacie MP3 przy użyciu `yt-dlp`.

4. **`PobierzIPodzielAudio.py`**  
   Automatyzuje cały proces: pobiera audio (`PobierzAudio.py`), a następnie dzieli plik na 5-minutowe segmenty (`PodzielAudio.py`).

5. **`PobierzAudioIGoogleDrive.py`**  
   Pobiera ścieżkę dźwiękową z YouTube, a następnie automatycznie przenosi (wytnij-wklej) pobrany plik MP3 do katalogu docelowego `C:\Filip\GoogleDrive`.

6. **`PodzielAudio.py`**  
   Dzieli plik MP3 na 5-minutowe segmenty. Na początku każdego segmentu generowana jest zapowiedź głosowa w języku polskim za pomocą biblioteki `gTTS` (np. *"Nazwa pliku - segment pierwszy z pięciu"*), ułatwiając słuchanie na urządzeniach bez ekranu.

6. **`PobierzNapisy.py`**  
   Pobiera automatycznie wygenerowane napisy (`.vtt`) w języku polskim dla wybranego filmu.

7. **`KonwertujVttDoTxt.py`**  
   Konwertuje pliki napisów z formatu `.vtt` do czystego tekstu `.txt`, usuwając powtarzające się linie (rolling captions), tagi HTML/karaoke i formatując tekst w czytelne zdania.

8. **`UsunNiesledzone.py`**  
   Pomocniczy skrypt usuwający z folderu roboczego wszystkie pliki nieśledzone przez system kontroli wersji Git.

9. **`ZarejestrujUsluge.py`**  
   Skrypt rejestrujący/wyrejestrowujący usługę `Usluga.py` w Harmonogramie Zadań Windows (Task Scheduler).

---

## 🚀 Instalacja i konfiguracja

### 1. Wymagania wstępne
Upewnij się, że masz zainstalowany program **Python 3** dodany do zmiennej środowiskowej PATH oraz pobrane narzędzie **`yt-dlp`** (i opcjonalnie `ffmpeg` potrzebny do konwersji audio).

Zainstaluj wymagane biblioteki Pythona:
```bash
pip install -U "yt-dlp[default]" pydub gTTS pyperclip flask flask-cors
```

### 2. Instalacja skryptu Tampermonkey
1. Zainstaluj rozszerzenie **Tampermonkey** w swojej przeglądarce.
2. Otwórz panel sterowania Tampermonkey i kliknij **Dodaj nowy skrypt**.
3. Wklej zawartość pliku [`PodzielAudio.user.js`](file:///c:/Filip/SW/PodzielAudio/PodzielAudio.user.js) i zapisz go (`Ctrl + S`).

### 3. Autouruchamianie usługi przy logowaniu
Aby usługa automatycznie startowała w tle (bez widocznego okna konsoli) przy każdym logowaniu do systemu Windows:

1. Otwórz terminal (jako administrator, jeśli Harmonogram Zadań tego wymaga) w tym folderze.
2. Uruchom skrypt instalacyjny:
   ```bash
   python ZarejestrujUsluge.py --install
   ```

W celu usunięcia usługi z Harmonogramu Zadań uruchom:
```bash
python ZarejestrujUsluge.py --uninstall
```

Możesz też sprawdzić status zadania:
```bash
python ZarejestrujUsluge.py --status
```

---

## 📖 Sposób użycia

1. Upewnij się, że usługa działa (jeśli nie zrestartowałeś systemu po instalacji zadania, możesz ją uruchomić komendą `schtasks /run /tn "PodzielAudio_Usluga"` lub ręcznie poprzez `python Usluga.py`).
2. Wejdź na dowolny film na YouTube.

### Jak wygląda i gdzie jest przycisk?

Przycisk pojawia się **bezpośrednio pod odtwarzaczem wideo**, obok innych systemowych przycisków YouTube (takich jak *Subskrybuj*, *Udostępnij*, *Klip* itp.).

* **Wygląd**: Czerwony, zaokrąglony przycisk z napisem **`🎵 Pobierz`**.
* **Menu rozwijane**: Po prawej stronie przycisku znajduje się strzałka **`▾`**, która otwiera menu z opcjami:
  * `📥 Pobierz Audio` — pobiera plik MP3
  * `📥🔪 Pobierz i Podziel Audio` — pobiera MP3 i tnie na 5-minutowe segmenty z zapowiedziami głosowymi
  * `📝 Pobierz Napisy` — pobiera napisy VTT do pliku
  * `🤖📁 Pobierz i wyślij na GDrive` — pobiera plik MP3 i przenosi go bezpośrednio do folderu `C:\Filip\GoogleDrive`
* **Wskaźnik statusu (Online/Offline)**:
  * Jeśli lokalna usługa w tle działa, przycisk jest **czerwony**.
  * Jeśli usługa jest wyłączona, przycisk staje się **szary**, a na dole ekranu pojawi się komunikat ostrzegawczy o braku połączenia z lokalnym serwerem.

3. Pod odtwarzaczem zobaczysz czerwony przycisk **🎵 Pobierz** oraz strzałkę menu.
4. Kliknij przycisk główny, aby pobrać samo audio, lub rozwiń menu i wybierz odpowiednią akcję.
5. Skrypt wywoła okno dialogowe Pythona (Tkinter) na pulpicie z zapytaniem o nazwę zapisu, a następnie uruchomi pobieranie/konwersję.
