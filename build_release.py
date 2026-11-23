# build_release.py
"""
Script di build multipiattaforma (Windows e Linux) per generare la release
standalone di D&D OmniCompanion.

Usa PyInstaller per compilare l'applicazione in un eseguibile nativo:
- Su Windows: dist/DndOmniCompanion/DndOmniCompanion.exe + archivio ZIP (.zip)
- Su Linux: dist/DndOmniCompanion/DndOmniCompanion + launcher run.sh + archivio tar.gz (.tar.gz) e .zip
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

VERSION = os.environ.get("RELEASE_VERSION", "v0.6.0-alpha")
APP_NAME = "DndOmniCompanion"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform.startswith("darwin")

REQUIRED_DATA_DIRS = [
    ("srd_data", "srd_data"),
    ("maps", "maps"),
]
OPTIONAL_DATA_FILES = [
    ("dnd_blankcharactersheet_it.pdf", "."),
]
REQUIRED_DOCS = [
    "README.md",
    "README_IT.md",
]
BUNDLE_DOCS = [
    "README.md",
    "README_IT.md",
    "LICENSE",
]
HIDDEN_IMPORTS = [
    "PIL", "PIL.Image", "PIL.ImageTk",
    "ttkbootstrap",
    "sounddevice", "soundfile",
    "cffi", "reportlab", "pypdf",
    "tkinter", "tkinter.ttk",
    "sqlite3", "json", "threading", "queue", "socket",
    "common.i18n", "common.theme", "common.file_utils",
    "common.spell_effects_engine", "common.subclass_and_race_rules",
    "components.ui_components", "components.command_palette",
    "client.client", "client.network_handlers", "client.reaction_prompts_mixin",
    "client.sheet_panels.combat_panel", "client.sheet_panels.spells_panel", "client.sheet_panels.vitals_panel",
    "server.server", "server.dm_gui", "server.dm_campaign_session_mixin", "server.dm_automation_panel",
]


def validate_build_inputs(base_dir: str = BASE_DIR, version: str = VERSION) -> list[str]:
    """Verifica prerequisiti di packaging (entrypoint, asset, docs IT/EN, moduli interni) senza scrivere file."""
    errors: list[str] = []
    if not str(version or "").strip():
        errors.append("RELEASE_VERSION is empty.")

    entry = os.path.join(base_dir, "main.py")
    if not os.path.isfile(entry):
        errors.append(f"Missing entrypoint: {entry}")

    for src, _dst in REQUIRED_DATA_DIRS:
        p = os.path.join(base_dir, src)
        if not os.path.isdir(p):
            errors.append(f"Missing required data directory: {p}")

    for doc in REQUIRED_DOCS:
        p = os.path.join(base_dir, doc)
        if not os.path.isfile(p):
            errors.append(f"Missing required documentation file: {p}")

    inserted_path = False
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
        inserted_path = True
    try:
        for mod in HIDDEN_IMPORTS:
            if mod.startswith(("common.", "components.", "client.", "server.")):
                try:
                    spec = importlib.util.find_spec(mod)
                except Exception as exc:
                    spec = None
                    errors.append(f"Error resolving internal module {mod}: {exc}")
                if spec is None:
                    errors.append(f"Unresolvable internal hidden import: {mod}")
    finally:
        if inserted_path and base_dir in sys.path:
            sys.path.remove(base_dir)

    return errors


def run_pyinstaller():
    errors = validate_build_inputs()
    if errors:
        for err in errors:
            print(f"[ERRORE] {err}")
        sys.exit(1)

    os_name = "Windows" if IS_WINDOWS else ("Linux" if IS_LINUX else "macOS")
    print(f"=== Creazione Build Eseguibile {APP_NAME} ({VERSION}) su {os_name} ===")
    
    dist_dir = os.path.join(BASE_DIR, "dist")
    build_dir = os.path.join(BASE_DIR, "build")
    
    # Pulizia preventiva
    for p in [dist_dir, build_dir]:
        if os.path.exists(p):
            print(f"Pulizia cartella: {p}")
            shutil.rmtree(p, ignore_errors=True)
            
    # Dati pubblici/core da includere (source, dest).
    # NOTE: manuals/, audio_library/ e campagne private non vengono incluse per evitare
    # la redistribuzione accidentale di PDF protetti da copyright o audio/campagne personali dell'utente.
    datas = [
        ("srd_data", "srd_data"),
        ("maps", "maps"),
    ]
    # Separatore di PyInstaller: ';' su Windows, ':' su Linux/macOS
    path_sep = ";" if IS_WINDOWS else ":"
    data_args = []
    for src, dst in datas:
        src_path = os.path.join(BASE_DIR, src)
        if os.path.exists(src_path):
            data_args.extend(["--add-data", f"{src_path}{path_sep}{dst}"])
        else:
            print(f"Avviso: Cartella sorgente non trovata: {src_path}")
    for src, dst in OPTIONAL_DATA_FILES:
        src_path = os.path.join(BASE_DIR, src)
        if os.path.isfile(src_path):
            data_args.extend(["--add-data", f"{src_path}{path_sep}{dst}"])
            
    hidden_args = []
    for h in HIDDEN_IMPORTS:
        hidden_args.extend(["--hidden-import", h])
        
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", APP_NAME,
        *data_args,
        *hidden_args,
        os.path.join(BASE_DIR, "main.py")
    ]
    
    print("\nEsecuzione comando PyInstaller...")
    print(" ".join(cmd[:10]) + " ...")
    
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print(f"\n[ERRORE] PyInstaller fallito con exit code {result.returncode}")
        sys.exit(result.returncode)
        
    print("\n[OK] Compilazione PyInstaller completata!")
    
    app_dist_dir = os.path.join(dist_dir, APP_NAME)
    client_data_dist = os.path.join(app_dist_dir, "client_data")
    os.makedirs(client_data_dist, exist_ok=True)
    
    # Copia le impostazioni predefinite se esistono
    src_settings = os.path.join(BASE_DIR, "client_data", "settings.json")
    if os.path.exists(src_settings):
        shutil.copy2(src_settings, os.path.join(client_data_dist, "settings.json"))
        
    # Copia README bilingue & Documentazione essenziale
    for doc in BUNDLE_DOCS:
        src_doc = os.path.join(BASE_DIR, doc)
        if os.path.exists(src_doc):
            shutil.copy2(src_doc, app_dist_dir)

    # Crea cartelle template pulite per l'utente finale (senza file privati o protetti da copyright)
    user_template_dirs = [
        ("manuals", "Posiziona qui i tuoi manuali o regole personalizzate (PDF, Markdown)."),
        ("campaigns", "Cartella per le campagne utente. Le campagne salvate verranno collocate qui."),
        ("audio_library", "Cartella per le tracce audio e playlist del Dungeon Master.")
    ]
    for udir, readme_text in user_template_dirs:
        target_dir = os.path.join(app_dist_dir, udir)
        os.makedirs(target_dir, exist_ok=True)
        readme_file = os.path.join(target_dir, "README.txt")
        if not os.path.exists(readme_file):
            with open(readme_file, "w", encoding="utf-8") as f:
                f.write(f"{readme_text}\n")
            
    if IS_LINUX:
        # Crea script launcher run.sh con permessi di esecuzione
        run_sh_path = os.path.join(app_dist_dir, "run.sh")
        with open(run_sh_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "#!/usr/bin/env bash\n"
                "# Launcher per D&D OmniCompanion su Linux\n"
                "set -e\n"
                "SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
                "chmod +x \"$SCRIPT_DIR/DndOmniCompanion\"\n"
                "exec \"$SCRIPT_DIR/DndOmniCompanion\" \"$@\"\n"
            )
        try:
            os.chmod(run_sh_path, 0o755)
            bin_path = os.path.join(app_dist_dir, APP_NAME)
            if os.path.exists(bin_path):
                os.chmod(bin_path, 0o755)
        except Exception:
            pass

        # Genera archivio tar.gz
        tar_filename = f"{APP_NAME}-{VERSION}-linux-x64.tar.gz"
        tar_path = os.path.join(dist_dir, tar_filename)
        print(f"\nCreazione pacchetto compresso: {tar_path}")
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(app_dist_dir, arcname=APP_NAME)
            
        tar_size_mb = os.path.getsize(tar_path) / (1024 * 1024)
        print("\n========================================================")
        print("RELEASE LINUX GENERATA CON SUCCESSO:")
        print(f"  Cartella: {app_dist_dir}")
        print(f"  Binario: {os.path.join(app_dist_dir, APP_NAME)}")
        print(f"  Archivio TAR.GZ: {tar_path} ({tar_size_mb:.2f} MB)")
        print("========================================================")
    elif IS_MACOS:
        zip_filename = f"{APP_NAME}-{VERSION}-macos.zip"
        zip_path = os.path.join(dist_dir, zip_filename)
        print(f"\nCreazione pacchetto compresso macOS: {zip_path}")
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(app_dist_dir):
                for file in files:
                    file_full = os.path.join(root, file)
                    rel_path = os.path.relpath(file_full, dist_dir)
                    zf.write(file_full, rel_path)
                    
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print("\n========================================================")
        print("RELEASE MACOS GENERATA CON SUCCESSO:")
        print(f"  Cartella: {app_dist_dir}")
        print(f"  Binario: {os.path.join(app_dist_dir, APP_NAME)}")
        print(f"  Archivio ZIP: {zip_path} ({zip_size_mb:.2f} MB)")
        print("========================================================")
    else:
        # Genera archivio ZIP per Windows
        zip_filename = f"{APP_NAME}-{VERSION}-win64.zip"
        zip_path = os.path.join(dist_dir, zip_filename)
        print(f"\nCreazione pacchetto compresso Windows: {zip_path}")
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(app_dist_dir):
                for file in files:
                    file_full = os.path.join(root, file)
                    rel_path = os.path.relpath(file_full, dist_dir)
                    zf.write(file_full, rel_path)
                    
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print("\n========================================================")
        print("RELEASE WINDOWS GENERATA CON SUCCESSO:")
        print(f"  Cartella: {app_dist_dir}")
        print(f"  Eseguibile: {os.path.join(app_dist_dir, f'{APP_NAME}.exe')}")
        print(f"  Archivio ZIP: {zip_path} ({zip_size_mb:.2f} MB)")
        print("========================================================")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=f"{APP_NAME} release builder")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate entrypoints, data directories, docs, and internal hidden imports without writing files.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        errors = validate_build_inputs()
        print(
            f"[DRY-RUN] app={APP_NAME} version={VERSION} "
            f"dirs={len(REQUIRED_DATA_DIRS)} docs={len(REQUIRED_DOCS)} hidden_imports={len(HIDDEN_IMPORTS)}"
        )
        if errors:
            for err in errors:
                print(f"[DRY-RUN ERROR] {err}")
            print("DRY_RUN_STATUS=FAIL")
            return 1
        print("DRY_RUN_STATUS=OK")
        return 0
    run_pyinstaller()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
