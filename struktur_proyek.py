
from pathlib import Path

# Root folder = lokasi script Python ini berada
ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = "struktur_proyek.txt"

IGNORE_DIRS = {
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "out",
    "vendor",
    "target",
    "site-packages",
    "bower_components",
    ".turbo",
}

IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
}

IGNORE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".obj",
    ".dll",
    ".exe",
    ".so",
    ".dylib",
    ".log",
}


def buat_struktur(folder, prefix="", hasil=None):
    if hasil is None:
        hasil = []

    try:
        items = sorted(
            folder.iterdir(),
            key=lambda p: (p.is_file(), p.name.lower())
        )
    except PermissionError:
        return hasil

    items = [
        item for item in items
        if not (
            item.is_dir()
            and item.name.lower() in IGNORE_DIRS
        )
        and not (
            item.is_file()
            and (
                item.name == OUTPUT_FILE
                or item.name in IGNORE_FILES
                or item.suffix.lower() in IGNORE_EXTENSIONS
            )
        )
    ]

    for i, item in enumerate(items):
        last = i == len(items) - 1
        connector = "└── " if last else "├── "
        hasil.append(f"{prefix}{connector}{item.name}")

        if item.is_dir():
            new_prefix = prefix + ("    " if last else "│   ")
            buat_struktur(item, new_prefix, hasil)

    return hasil


def main():
    hasil = [
        f"STRUKTUR PROYEK: {ROOT.name}",
        f"Lokasi: {ROOT}",
        "=" * 70,
        "",
        f"{ROOT.name}/",
    ]

    buat_struktur(ROOT, hasil=hasil)

    output = ROOT / OUTPUT_FILE
    output.write_text(
        "\n".join(hasil) + "\n",
        encoding="utf-8"
    )

    print(f"Berhasil membuat: {output}")


if __name__ == "__main__":
    main()
