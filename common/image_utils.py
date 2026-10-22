# common/image_utils.py
"""
Utility per il caricamento, ottimizzazione, ritaglio circolare e conversione
in formato base64 delle immagini dei token/avatar per personaggi, PNG e mostri.
Garantisce token leggeri e compatibili con la visualizzazione su mappa esagonale (HexMapCanvas).
"""

import io
import os
import base64
from typing import Optional, Tuple
from PIL import Image, ImageTk, ImageDraw, ImageOps
from tkinter import filedialog, messagebox


def process_avatar_image(source, max_size: Tuple[int, int] = (128, 128)) -> str:
    """
    Carica un'immagine da percorso file, bytes o oggetto PIL.Image,
    applica l'orientamento EXIF corretto, ritaglia centralmente a quadrato 1:1,
    la ridimensiona a max_size e restituisce la stringa base64 PNG ottimizzata.
    """
    if not source:
        return ""

    img = None
    try:
        if isinstance(source, str):
            if not os.path.exists(source):
                return ""
            img = Image.open(source)
        elif isinstance(source, (bytes, bytearray)):
            img = Image.open(io.BytesIO(source))
        elif isinstance(source, Image.Image):
            img = source.copy()
        else:
            return ""

        # Correzione automatica orientamento EXIF (foto smartphone/fotocamera)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        img = img.convert("RGBA")

        # Ritaglio centrale al quadrato perfetto (1:1)
        w, h = img.size
        min_dim = min(w, h)
        if min_dim <= 0:
            return ""

        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))

        # Ridimensionamento ad alta qualità
        img = img.resize(max_size, Image.Resampling.LANCZOS)

        # Salvataggio in buffer memoria PNG compresso
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[image_utils] Errore elaborazione immagine avatar: {e}")
        return ""


def avatar_b64_to_tk_image(avatar_b64: str, size: int = 64, circular: bool = True) -> Optional[ImageTk.PhotoImage]:
    """
    Converte una stringa avatar_b64 in un oggetto PhotoImage Tkinter
    ridimensionato e opzionalmente ritagliato a cerchio.
    Restituisce None in caso di errore o ambiente headless senza display Tk.
    """
    if not avatar_b64 or not isinstance(avatar_b64, str):
        return None

    try:
        raw_bytes = base64.b64decode(avatar_b64)
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        target_size = max(16, size)
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

        if circular:
            mask = Image.new("L", (target_size, target_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, target_size, target_size), fill=255)
            circular_img = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
            circular_img.paste(img, (0, 0), mask=mask)
            img = circular_img

        return ImageTk.PhotoImage(img)
    except Exception:
        # Silenzioso se Tk non è inizializzato (es. nei test headless)
        return None


def open_avatar_file_dialog(parent=None) -> Tuple[str, str]:
    """
    Apre una finestra di dialogo per selezionare un'immagine dal disco.
    Restituisce (avatar_b64, filepath). Se l'utente annulla, restituisce ("", "").
    """
    try:
        file_path = filedialog.askopenfilename(
            title="Seleziona Immagine del Personaggio / Token Mappa",
            filetypes=[
                ("File Immagine", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                ("PNG (*.png)", "*.png"),
                ("JPEG (*.jpg, *.jpeg)", "*.jpg *.jpeg"),
                ("WebP (*.webp)", "*.webp"),
                ("Tutti i file", "*.*")
            ],
            parent=parent
        )
        if not file_path:
            return "", ""

        b64 = process_avatar_image(file_path)
        if not b64:
            messagebox.showwarning(
                "Immagine non valida",
                "Impossibile elaborare il file selezionato. Assicurati che sia un'immagine valida (PNG, JPEG, WebP, BMP).",
                parent=parent
            )
            return "", ""

        return b64, file_path
    except Exception as e:
        print(f"[image_utils] Errore apertura file dialog: {e}")
        return "", ""


def render_avatar_on_canvas(canvas, avatar_b64: str, display_name: str = "", size: int = 64,
                            border_color: str = "#D4AF37", bg_color: str = "#181A20",
                            tag: str = "avatar_token"):
    """
    Disegna l'avatar circolare o un placeholder fantasy con le iniziali sulla Canvas data.
    Salva il riferimento dell'immagine PhotoImage su canvas._avatar_img per evitarne il garbage collection.
    """
    try:
        canvas.delete(tag)
        w = size
        h = size
        cx, cy = w / 2, h / 2

        tk_img = avatar_b64_to_tk_image(avatar_b64, size=size, circular=True) if avatar_b64 else None
        if tk_img:
            canvas._avatar_img = tk_img
            canvas.create_image(cx, cy, image=tk_img, anchor="center", tags=tag)
            # Bordo dorato / stilizzato
            canvas.create_oval(1.5, 1.5, w - 1.5, h - 1.5, outline=border_color, width=2, fill="", tags=tag)
        else:
            canvas._avatar_img = None
            # Sfondo circolare scuro
            canvas.create_oval(1.5, 1.5, w - 1.5, h - 1.5, fill=bg_color, outline=border_color, width=2, tags=tag)
            initials = display_name[:2].upper() if display_name and display_name.strip() else "👤"
            font_size = max(8, int(size * 0.28))
            canvas.create_text(cx, cy, text=initials, fill="#FFFFFF", font=("Segoe UI", font_size, "bold"), tags=tag)
    except Exception as e:
        print(f"[image_utils] Errore render avatar su canvas: {e}")

