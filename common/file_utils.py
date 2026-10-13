# common/file_utils.py
"""
Utility per la gestione sicura e atomica dei file su disco.
Previene la corruzione dei file JSON in caso di arresti anomali o crash.
"""
import os
import json
import tempfile


def atomic_save_json(filepath, data, indent=4, ensure_ascii=False):
    """
    Salva i dati in formato JSON in modo atomico.
    Scrive prima su un file temporaneo nella stessa directory e poi esegue
    la sostituzione atomica (os.replace) per garantire che il file di destinazione
    non rimanga mai vuoto o parzialmente scritto in caso di errori.
    """
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)

    tf = tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8")
    tmp_path = tf.name
    try:
        json.dump(data, tf, indent=indent, ensure_ascii=ensure_ascii)
        tf.flush()
        tf.close()
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
    Se il file non esiste o è corrotto, restituisce `default`.
    """
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[file_utils] Errore caricamento '{filepath}': {e}")
        return default


# Alias per compatibilità
safe_write_json = atomic_save_json

