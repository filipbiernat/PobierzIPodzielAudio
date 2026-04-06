import re
import os
import sys
import tkinter as tk
from tkinter import filedialog


def strip_inline_tags(text):
    """Usuwa znaczniki czasu i <c></c> z tekstu napisu."""
    # Usuń znaczniki czasu: <00:00:00.000>
    text = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d+>', '', text)
    # Usuń tagi karaoke: <c> i </c>
    text = re.sub(r'</?c>', '', text)
    return text.strip()


def vtt_na_txt(vtt_path):
    with open(vtt_path, encoding='utf-8') as f:
        lines = f.readlines()

    text_lines = []
    for line in lines:
        line = line.strip()

        # Pomiń nagłówki i metadane
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue

        # Pomiń linie ze znacznikami czasu (np. 00:00:00.000 --> 00:00:05.000 ...)
        if re.match(r'^\d{2}:\d{2}:\d{2}\.\d+ -->', line):
            continue

        # Pomiń puste linie
        if not line:
            continue

        cleaned = strip_inline_tags(line)

        # Pomiń linie puste po oczyszczeniu
        if not cleaned:
            continue

        text_lines.append(cleaned)

    # Usuń kolejne duplikaty (rolling captions powtarzają poprzednią linię)
    deduplicated = []
    for line in text_lines:
        if not deduplicated or line != deduplicated[-1]:
            deduplicated.append(line)

    # Złącz w jeden ciągły tekst
    full_text = ' '.join(deduplicated)

    # Opcjonalne: dodaj nową linię po końcu zdania dla lepszej czytelności
    full_text = re.sub(r'([.?!])\s+([A-ZŁŚŹĆĄĘÓŃ])', r'\1\n\2', full_text)

    txt_path = os.path.splitext(vtt_path)[0] + '.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(full_text)

    print(f'Zapisano: {txt_path}')
    return txt_path


def wybierz_plik():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title='Wybierz plik VTT',
        filetypes=[('Pliki napisów VTT', '*.vtt'), ('Wszystkie pliki', '*.*')]
    )
    root.destroy()
    return path


if __name__ == '__main__':
    if len(sys.argv) > 1:
        vtt_file = sys.argv[1]
    else:
        vtt_file = wybierz_plik()

    if not vtt_file:
        print('Nie wybrano pliku.')
        sys.exit(1)

    if not os.path.isfile(vtt_file):
        print(f'Plik nie istnieje: {vtt_file}')
        sys.exit(1)

    vtt_na_txt(vtt_file)
