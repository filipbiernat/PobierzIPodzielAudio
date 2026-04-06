#!/usr/bin/env python3
"""Usuwa z bieżącego folderu pliki nieśledzone przez git."""

import subprocess
import os


def get_untracked_files():
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        capture_output=True, check=True
    )
    # -z rozdziela NULL-bajtami, omija problem z cudzysłowami i escape'ami
    files = result.stdout.split(b'\x00')
    return [f.decode('utf-8') for f in files if f]


def main():
    untracked = get_untracked_files()

    if not untracked:
        print("Brak plików nieśledzonych przez git.")
        return

    print("Pliki do usunięcia:")
    for f in untracked:
        print(f"  {f}")

    answer = input("\nCzy usunąć te pliki? [t/N] ").strip().lower()
    if answer != "t":
        print("Anulowano.")
        return

    for f in untracked:
        os.remove(f)
        print(f"Usunięto: {f}")

    print("Gotowe.")


if __name__ == "__main__":
    main()
