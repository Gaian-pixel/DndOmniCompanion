# common/audio_player.py
"""
Riproduzione locale di tracce audio (MP3, OGG, WAV, FLAC) usando soundfile + sounddevice.

- Canale "music": una sola traccia alla volta (avviarne una nuova ferma la precedente), loop opzionale.
- Canale "sfx": effetti sonori one-shot, possono sovrapporsi.

La traccia viene letta dal disco a blocchi (streaming), quindi anche file lunghi non occupano RAM.
Se non c'è un dispositivo audio disponibile, i metodi falliscono silenziosamente restituendo False.
"""
import threading

try:
    import numpy as np
    import soundfile as sf
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except Exception as _e:  # librerie mancanti
    print(f"[Audio] Riproduzione non disponibile: {_e}")
    AUDIO_AVAILABLE = False

SUPPORTED_EXTENSIONS = (".mp3", ".ogg", ".wav", ".flac")


def get_audio_info(path):
    """Restituisce (durata_secondi, samplerate, canali) oppure solleva un'eccezione se il file non è valido."""
    info = sf.info(path)
    return info.duration, info.samplerate, info.channels


class _Track:
    def __init__(self, path, loop, volume, channel_volume_getter):
        self.loop = loop
        self.volume = max(0.0, min(1.0, float(volume)))
        self._channel_volume = channel_volume_getter
        self._lock = threading.Lock()
        self.finished = False
        self.file = sf.SoundFile(path)
        self.out_channels = min(self.file.channels, 2)
        self.stream = sd.OutputStream(
            samplerate=self.file.samplerate,
            channels=self.out_channels,
            dtype="float32",
            blocksize=4096,
            latency="high",
            callback=self._callback,
            finished_callback=self._on_finished,
        )

    def start(self):
        self.stream.start()

    def _read(self, frames):
        data = self.file.read(frames, dtype="float32", always_2d=True)
        if self.loop and len(data) < frames:
            parts = [data]
            got = len(data)
            while got < frames:
                self.file.seek(0)
                more = self.file.read(frames - got, dtype="float32", always_2d=True)
                if len(more) == 0:
                    break
                parts.append(more)
                got += len(more)
            data = np.concatenate(parts)
        return data[:, :self.out_channels]

    def _callback(self, outdata, frames, time_info, status):
        with self._lock:
            if self.finished:
                outdata.fill(0)
                raise sd.CallbackStop
            try:
                data = self._read(frames)
            except Exception:
                outdata.fill(0)
                raise sd.CallbackStop
        n = len(data)
        gain = self.volume * self._channel_volume()
        outdata[:n] = data * gain
        if n < frames:
            outdata[n:] = 0
            raise sd.CallbackStop

    def _on_finished(self):
        self.finished = True

    def stop(self):
        with self._lock:
            self.finished = True
        try:
            self.stream.abort(ignore_errors=True)
            self.stream.close(ignore_errors=True)
        except Exception:
            pass
        try:
            self.file.close()
        except Exception:
            pass


class AudioManager:
    def __init__(self):
        self.music_volume = 0.8
        self.sfx_volume = 1.0
        self._music = None
        self._music_name = None
        self._sfx = []
        self._lock = threading.Lock()

    @property
    def available(self):
        return AUDIO_AVAILABLE

    @property
    def current_music_name(self):
        if self._music and not self._music.finished:
            return self._music_name
        return None

    def play(self, path, channel="music", loop=False, volume=1.0, name=None):
        """Avvia la riproduzione di un file. Restituisce True se è partita."""
        if not AUDIO_AVAILABLE:
            return False
        try:
            if channel == "music":
                track = _Track(path, loop, volume, lambda: self.music_volume)
                with self._lock:
                    old = self._music
                    self._music = track
                    self._music_name = name
                if old:
                    old.stop()
            else:
                track = _Track(path, False, volume, lambda: self.sfx_volume)
                with self._lock:
                    finished = [t for t in self._sfx if t.finished]
                    self._sfx = [t for t in self._sfx if not t.finished]
                    self._sfx.append(track)
                for t in finished:
                    t.stop()
            track.start()
            return True
        except Exception as e:
            print(f"[Audio] Impossibile riprodurre '{path}': {e}")
            return False

    def stop(self, channel="all"):
        with self._lock:
            to_stop = []
            if channel in ("music", "all") and self._music:
                to_stop.append(self._music)
                self._music = None
                self._music_name = None
            if channel in ("sfx", "all"):
                to_stop.extend(self._sfx)
                self._sfx = []
        for t in to_stop:
            t.stop()

    def get_volume(self, channel="music"):
        return self.music_volume if channel == "music" else self.sfx_volume

    def set_volume(self, channel, value):
        value = max(0.0, min(1.0, float(value)))
        if channel == "music":
            self.music_volume = value
        else:
            self.sfx_volume = value

    def shutdown(self):
        self.stop("all")

