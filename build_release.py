# build_release.py
"""
Script di build per generare la release standalone di D&D OmniCompanion.
Usa PyInstaller per compilare l'applicazione in un eseguibile Windows (.exe)
e genera l'archivio ZIP pronto per la distribuzione:
dist/DndOmniCompanion-v0.1.0-alpha-win64.zip
"""

import os
import sys
import shutil
import zipfile
import subprocess

VERSION = "v0.1.0-alpha"
APP_NAME = "DndOmniCompanion"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_pyinstaller():
    print(f"=== Creazione Build Eseguibile {APP_NAME} ({VERSION}) ===")
    
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
    
    data_args = []
    for src, dst in datas:
        src_path = os.path.join(BASE_DIR, src)
        if os.path.exists(src_path):
            # In Windows il separatore di PyInstaller è ';'
            data_args.extend(["--add-data", f"{src_path};{dst}"])
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
    
    # Assicurati che client_data e cartelle necessarie esistano nella dist
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
            
    # Crea archivio ZIP distribuibile
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
    print(f"RELEASE GENERATA CON SUCCESSO:")
    print(f"  Cartella: {app_dist_dir}")
    print(f"  Eseguibile: {os.path.join(app_dist_dir, f'{APP_NAME}.exe')}")
    print(f"  Archivio ZIP: {zip_path} ({zip_size_mb:.2f} MB)")
    print(f"========================================================")


if __name__ == "__main__":
    run_pyinstaller()
