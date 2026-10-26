# build_release.py
"""
Script di build multipiattaforma (Windows e Linux) per generare la release
standalone di D&D OmniCompanion.

Usa PyInstaller per compilare l'applicazione in un eseguibile nativo:
- Su Windows: dist/DndOmniCompanion/DndOmniCompanion.exe + archivio ZIP (.zip)
- Su Linux: dist/DndOmniCompanion/DndOmniCompanion + launcher run.sh + archivio tar.gz (.tar.gz) e .zip
"""

import os
import sys
import shutil
import zipfile
import tarfile
import subprocess

VERSION = os.environ.get("RELEASE_VERSION", "v0.1.0-alpha")
APP_NAME = "DndOmniCompanion"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform.startswith("darwin")


def run_pyinstaller():
    os_name = "Windows" if IS_WINDOWS else ("Linux" if IS_LINUX else "macOS")
    print(f"=== Creazione Build Eseguibile {APP_NAME} ({VERSION}) su {os_name} ===")
    
    dist_dir = os.path.join(BASE_DIR, "dist")
    build_dir = os.path.join(BASE_DIR, "build")
    
    # Pulizia preventiva
    for p in [dist_dir, build_dir]:
        if os.path.exists(p):
            print(f"Pulizia cartella: {p}")
            shutil.rmtree(p, ignore_errors=True)
            
    # Dati da includere (source, dest)
    datas = [
        ("srd_data", "srd_data"),
        ("manuals", "manuals"),
        ("campaigns", "campaigns"),
        ("audio_library", "audio_library"),
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
            
    hidden_imports = [
        "PIL", "PIL.Image", "PIL.ImageTk",
        "sounddevice", "soundfile",
        "cffi", "reportlab", "pypdf",
        "tkinter", "tkinter.ttk",
        "sqlite3", "json", "threading", "queue", "socket",
        "common.i18n", "common.theme", "common.file_utils",
        "client.client", "server.server", "server.dm_gui"
    ]
    
    hidden_args = []
    for h in hidden_imports:
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
        
    # Copia README & Documentazione essenziale
    for doc in ["README.md", "LICENSE"]:
        src_doc = os.path.join(BASE_DIR, doc)
        if os.path.exists(src_doc):
            shutil.copy2(src_doc, app_dist_dir)
            
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
        print(f"\n========================================================")
        print(f"RELEASE LINUX GENERATA CON SUCCESSO:")
        print(f"  Cartella: {app_dist_dir}")
        print(f"  Binario: {os.path.join(app_dist_dir, APP_NAME)}")
        print(f"  Archivio TAR.GZ: {tar_path} ({tar_size_mb:.2f} MB)")
        print(f"========================================================")
    else:
        # Genera archivio ZIP per Windows
        zip_filename = f"{APP_NAME}-{VERSION}-win64.zip"
        zip_path = os.path.join(dist_dir, zip_filename)
        print(f"\nCreazione pacchetto compresso: {zip_path}")
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(app_dist_dir):
                for file in files:
                    file_full = os.path.join(root, file)
                    rel_path = os.path.relpath(file_full, dist_dir)
                    zf.write(file_full, rel_path)
                    
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"\n========================================================")
        print(f"RELEASE WINDOWS GENERATA CON SUCCESSO:")
        print(f"  Cartella: {app_dist_dir}")
        print(f"  Eseguibile: {os.path.join(app_dist_dir, f'{APP_NAME}.exe')}")
        print(f"  Archivio ZIP: {zip_path} ({zip_size_mb:.2f} MB)")
        print(f"========================================================")


if __name__ == "__main__":
    run_pyinstaller()
