# common/file_utils.py
"""
Utility per la gestione sicura e atomica dei file su disco.
Previene la corruzione dei file JSON in caso di arresti anomali o crash.
"""
import os
import sys
import json
import shutil
import tempfile


def get_base_dir() -> str:
    """
    Restituisce la directory radice dell'applicazione o del bundle PyInstaller.
    Utilizzata per caricare asset statici, compendi e template inclusi nella release.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_writable_dir() -> str:
    """
    Restituisce la directory scrivibile in cui salvare dati persistenti utente
    (file di configurazione, cartella client_data, personaggi e campagne salvate).
    In modalità standalone (.exe) coincide con la cartella che ospita l'eseguibile.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



def atomic_save_json(filepath, data, indent=4, ensure_ascii=False, create_backup: bool = False):
    """
    Salva i dati in formato JSON in modo atomico.
    Scrive prima su un file temporaneo nella stessa directory e poi esegue
    la sostituzione atomica (os.replace) per garantire che il file di destinazione
    non rimanga mai vuoto o parzialmente scritto in caso di errori.
    Se create_backup=True ed esiste un file precedente, preserva `<filepath>.bak`.
    """
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)

    tf = tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8")
    tmp_path = tf.name
    try:
        json.dump(data, tf, indent=indent, ensure_ascii=ensure_ascii)
        tf.flush()
        tf.close()
        if create_backup and os.path.exists(filepath):
            try:
                shutil.copy2(filepath, f"{filepath}.bak")
            except OSError:
                pass
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            tf.close()
        except Exception:
            pass
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def load_json(filepath, default=None):
    """
    Carica i dati da un file JSON con encoding UTF-8.
    Se il file primario è corrotto e esiste `<filepath>.bak`, tenta il ripristino dal backup.
    Se entrambi mancano o sono illeggibili, restituisce `default`.
    """
    bak_path = f"{filepath}.bak"
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError) as e:
            print(f"[file_utils] Errore caricamento '{filepath}': {e}")
            if os.path.exists(bak_path):
                try:
                    with open(bak_path, "r", encoding="utf-8") as bf:
                        recovered = json.load(bf)
                    print(f"[file_utils] Recupero automatico riuscito dal backup '{bak_path}'.")
                    return recovered
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError) as be:
                    print(f"[file_utils] Errore recupero backup '{bak_path}': {be}")
            return default
    if os.path.exists(bak_path):
        try:
            with open(bak_path, "r", encoding="utf-8") as bf:
                recovered = json.load(bf)
            print(f"[file_utils] File primario assente, ripristinato da backup '{bak_path}'.")
            return recovered
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError) as be:
            print(f"[file_utils] Errore recupero backup '{bak_path}': {be}")
    return default


# Alias per compatibilità
safe_write_json = atomic_save_json

