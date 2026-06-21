import sys
import PobierzAudio
import PodzielAudio

# 1. Pobranie pliku audio
print("🔹 Pobieranie pliku audio...")
audio_file_path = PobierzAudio.handle_clipboard_and_dialog()

if not audio_file_path:
    print("Nie udalo sie pobrac pliku audio. Zamykanie skryptu.")
    sys.exit(1)

print(f"✅ Pobrano plik: {audio_file_path}")

# 2. Podzielenie pliku audio
print("🔹 Dzielenie pliku audio...")
PodzielAudio.przetworz_plik(audio_file_path)

print("🎉 Proces zakończony!")