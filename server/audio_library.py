# server/audio_library.py
"""
Libreria delle tracce audio caricate dal DM.
I file vengono copiati in `audio_library/` con nome = hash SHA1 del contenuto,
così i client possono mettere in cache le tracce e scaricarle una sola volta.
"""
import os
import json
import shutil
import hashlib

from common.audio_player import SUPPORTED_EXTENSIONS, get_audio_info

LIB_DIR = "audio_library"
INDEX_FILE = os.path.join(LIB_DIR, "library.json")
MAX_FILE_SIZE = 60 * 1024 * 1024   # 60 MB
CHUNK_SIZE = 256 * 1024            # byte per blocco di trasferimento
MUSIC_THRESHOLD_SECONDS = 30       # oltre questa durata la traccia è considerata "Musica"


def _sha1_of_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class AudioLibrary:
    def __init__(self):
        os.makedirs(LIB_DIR, exist_ok=True)
        self.tracks = []
        self._load()

    # --- persistenza ---
    def _load(self):
        from common.file_utils import load_json
        data = load_json(INDEX_FILE, default=[])
        if isinstance(data, list):
            self.tracks = [t for t in data if isinstance(t, dict) and os.path.exists(self._file_for(t))]
        else:
            self.tracks = []

    def _save(self):
        from common.file_utils import atomic_save_json
        atomic_save_json(INDEX_FILE, self.tracks, indent=2, ensure_ascii=False)

    def _file_for(self, track):
        return os.path.join(LIB_DIR, f"{track['id']}{track['ext']}")

    # --- API ---
    def get(self, track_id):
        return next((t for t in self.tracks if t["id"] == track_id), None)

    def get_path(self, track_id):
        t = self.get(track_id)
        return self._file_for(t) if t else None

    def import_file(self, src_path):
        """Importa un file audio. Restituisce la traccia (dict). Solleva ValueError se non valido."""
        ext = os.path.splitext(src_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato non supportato ({ext}). Usa: {', '.join(SUPPORTED_EXTENSIONS)}")
        size = os.path.getsize(src_path)
        if size > MAX_FILE_SIZE:
            raise ValueError(f"File troppo grande ({size // (1024*1024)} MB, massimo {MAX_FILE_SIZE // (1024*1024)} MB).")
        try:
            duration, _, _ = get_audio_info(src_path)
        except Exception as e:
            raise ValueError(f"File audio non leggibile: {e}")

        track_id = _sha1_of_file(src_path)
        existing = self.get(track_id)
        if existing:
            return existing

        dest = os.path.join(LIB_DIR, f"{track_id}{ext}")
        if not os.path.exists(dest):
            shutil.copyfile(src_path, dest)

        track = {
            "id": track_id,
            "name": os.path.splitext(os.path.basename(src_path))[0],
            "ext": ext,
            "size": size,
            "duration": round(duration, 1),
            "category": "Musica" if duration > MUSIC_THRESHOLD_SECONDS else "Effetto",
        }
        self.tracks.append(track)
        self._save()
        return track

    def remove(self, track_id):
        t = self.get(track_id)
        if not t:
            return
        self.tracks.remove(t)
        try:
            os.remove(self._file_for(t))
        except OSError:
            pass
        self._save()

    def rename(self, track_id, new_name):
        t = self.get(track_id)
        if t and new_name:
            t["name"] = new_name
            self._save()

    def toggle_category(self, track_id):
        t = self.get(track_id)
        if t:
            t["category"] = "Effetto" if t["category"] == "Musica" else "Musica"
            self._save()

    def iter_chunks(self, track_id):
        """Genera (indice, totale, bytes) per il trasferimento ai client."""
        path = self.get_path(track_id)
        if not path:
            return
        size = os.path.getsize(path)
        total = max(1, (size + CHUNK_SIZE - 1) // CHUNK_SIZE)
        with open(path, "rb") as f:
            for i in range(total):
                yield i, total, f.read(CHUNK_SIZE)

