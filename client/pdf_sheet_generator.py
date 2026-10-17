"""Modulo per la generazione della Scheda Personaggio D&D 5e ufficiale in formato PDF.
Sovrappone graficamente i dati del personaggio sul template ufficiale italiano (dnd_blankcharactersheet_it.pdf)
utilizzando ReportLab e PyPDF.
"""

import io
import os
import re
from typing import Any, Dict, List, Optional

try:
    from reportlab.lib.colors import Color, black
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from pypdf import PdfReader, PdfWriter
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


# Mappa per le competenze standard dei tiri salvezza in D&D 5e per classe
CLASS_SAVE_PROFS = {
    "barbarian": ["FOR", "COS"], "barbaro": ["FOR", "COS"],
    "bard": ["DES", "CAR"], "bardo": ["DES", "CAR"],
    "cleric": ["SAG", "CAR"], "chierico": ["SAG", "CAR"],
    "druid": ["INT", "SAG"], "druido": ["INT", "SAG"],
    "fighter": ["FOR", "COS"], "guerriero": ["FOR", "COS"],
    "monk": ["FOR", "DES"], "monaco": ["FOR", "DES"],
    "paladin": ["SAG", "CAR"], "paladino": ["SAG", "CAR"],
    "ranger": ["FOR", "DES"],
    "rogue": ["DES", "INT"], "ladro": ["DES", "INT"],
    "sorcerer": ["COS", "CAR"], "stregone": ["COS", "CAR"],
    "warlock": ["SAG", "CAR"],
    "wizard": ["INT", "SAG"], "mago": ["INT", "SAG"],
}

# Mappa per la caratteristica di incantatore primaria della classe
CLASS_SPELLCASTING_ABILITY = {
    "wizard": "INT", "mago": "INT",
    "cleric": "SAG", "chierico": "SAG",
    "druid": "SAG", "druido": "SAG",
    "bard": "CAR", "bardo": "CAR",
    "sorcerer": "CAR", "stregone": "CAR",
    "warlock": "CAR",
    "paladin": "CAR", "paladino": "CAR",
    "ranger": "SAG",
    "monk": "SAG", "monaco": "SAG",
}

# Mappa abilità -> caratteristica chiave
SKILL_ABILITY_MAP = {
    "Acrobazia": "DES",
    "Addestrare Animali": "SAG",
    "Arcano": "INT",
    "Atletica": "FOR",
    "Furtività": "DES",
    "Indagare": "INT",
    "Inganno": "CAR",
    "Intimidire": "CAR",
    "Intrattenere": "CAR",
    "Intuizione": "SAG",
    "Medicina": "SAG",
    "Natura": "INT",
    "Percezione": "SAG",
    "Persuasione": "CAR",
    "Prestidigitazione": "DES",
    "Rapidità di Mano": "DES",
    "Religione": "INT",
    "Sopravvivenza": "SAG",
    "Storia": "INT",
}


def get_default_template_path() -> Optional[str]:
    """Restituisce il percorso al template se presente localmente, altrimenti None."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        "dnd_blankcharactersheet_it.pdf",
        os.path.join(current_dir, "..", "dnd_blankcharactersheet_it.pdf"),
        os.path.join(current_dir, "dnd_blankcharactersheet_it.pdf"),
        os.path.abspath("dnd_blankcharactersheet_it.pdf"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None



def _draw_wrapped_lines(can: "canvas.Canvas", text: str, x: float, start_y: float,
                        max_width: float, line_height: float, max_lines: int = 10,
                        font_name: str = "Helvetica", font_size: float = 8.0) -> float:
    """Disegna testo multilinea con word-wrap, restituendo la coordinata Y successiva."""
    can.setFont(font_name, font_size)
    if not text:
        return start_y
    
    current_y = start_y
    lines_drawn = 0
    
    paragraphs = str(text).split("\n")
    for para in paragraphs:
        words = para.strip().split()
        if not words:
            current_y -= line_height * 0.7
            continue
        
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            w = can.stringWidth(test_line, font_name, font_size)
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    can.drawString(x, current_y, " ".join(current_line))
                    current_y -= line_height
                    lines_drawn += 1
                    if lines_drawn >= max_lines:
                        return current_y
                current_line = [word]
        
        if current_line:
            can.drawString(x, current_y, " ".join(current_line))
            current_y -= line_height
            lines_drawn += 1
            if lines_drawn >= max_lines:
                return current_y

    return current_y


def generate_character_pdf(character_data: Any, output_path: str, template_path: Optional[str] = None) -> str:
    """
    Compila la scheda personaggio D&D 5e e la salva come PDF all'indirizzo `output_path`.
    
    Args:
        character_data: Istanza di Character oppure dict con i campi del personaggio.
        output_path: Percorso del file PDF di destinazione.
        template_path: Percorso del template base (default: cerca dnd_blankcharactersheet_it.pdf).
        
    Returns:
        output_path in caso di successo.
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab non è installato. Esegui 'pip install reportlab' per generare le schede PDF.")
    if not PYPDF_AVAILABLE:
        raise ImportError("PyPDF non è installato. Esegui 'pip install pypdf' per generare le schede PDF.")

    if hasattr(character_data, "to_dict"):
        data = character_data.to_dict()
    elif isinstance(character_data, dict):
        data = character_data
    else:
        data = dict(character_data)

    if not template_path:
        template_path = get_default_template_path()
    if not template_path or not os.path.isfile(template_path):
        raise FileNotFoundError(
            "Modello PDF vuoto non trovato. Seleziona il file del template della scheda (es. dnd_blankcharactersheet_it.pdf)."
        )

    # Estrai e normalizza statistiche
    name = str(data.get("name", "Eroe")).strip()
    char_class = str(data.get("char_class", "")).strip()
    level = int(data.get("level", 1) or 1)
    background = str(data.get("background", "")).strip()
    player_name = str(data.get("player_name", "")).strip()
    race = str(data.get("race", "")).strip()
    alignment = str(data.get("alignment", "")).strip()
    exp = str(data.get("exp", 0))

    # Calcolo bonus competenza
    prof_bonus = int(data.get("proficiency_bonus", 0) or (2 + (level - 1) // 4))

    # Caratteristiche
    attrs = data.get("attributes", {})
    if not isinstance(attrs, dict):
        attrs = {}

    def get_attr_val(code: str) -> int:
        try:
            return int(attrs.get(code, 10))
        except (ValueError, TypeError):
            return 10

    scores = {c: get_attr_val(c) for c in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]}
    mods = {c: (scores[c] - 10) // 2 for c in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]}

    # Tiri Salvezza
    # Rileva competenze: se indicate esplicitamente o dedotte dalla classe
    save_profs = data.get("saving_throw_proficiencies", [])
    if not save_profs:
        class_key = char_class.lower()
        for k, v in CLASS_SAVE_PROFS.items():
            if k in class_key:
                save_profs = v
                break

    # Abilità
    skills_data = data.get("skills", {})
    if not isinstance(skills_data, dict):
        skills_data = {}

    # Disegna overlay ReportLab in memoria (3 pagine da 594 x 783 pt)
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(594, 783))

    # =========================================================================
    # PAGINA 0: Scheda Principale (Statistiche, Abilità, Combattimento, Equip.)
    # =========================================================================
    can.setFillColor(black)

    # 1. Header
    can.setFont("Helvetica-Bold", 13)
    can.drawString(55, 703, name[:28])

    can.setFont("Helvetica", 9)
    class_lvl_str = f"{char_class} {level}".strip() if char_class else str(level)
    can.drawString(265, 728, class_lvl_str[:22])
    can.drawString(377, 728, background[:18])
    can.drawString(474, 728, player_name[:18])

    can.drawString(265, 701, race[:22])
    can.drawString(377, 701, alignment[:18])
    can.drawString(474, 701, exp[:18])

    # 2. Caratteristiche (6 box a sinistra)
    # Nel template ufficiale 5e, il riquadro centrale grande ospita il Modificatore (+X)
    # e l'ovale inferiore ospita il Punteggio base (10..20). Altezza casella: ~71.5 pt.
    stat_boxes = [
        ("FOR", 620, 576),
        ("DES", 548.5, 504.5),
        ("COS", 477, 433),
        ("INT", 405.5, 361.5),
        ("SAG", 334, 290),
        ("CAR", 262.5, 218.5),
    ]
    for code, y_mod, y_score in stat_boxes:
        m = mods[code]
        m_str = f"+{m}" if m >= 0 else str(m)
        can.setFont("Helvetica-Bold", 15)
        can.drawCentredString(48, y_mod, m_str)
        can.setFont("Helvetica-Bold", 9)
        can.drawCentredString(48, y_score, str(scores[code]))

    # 3. Ispirazione e Competenza
    if data.get("has_inspiration", False):
        can.setFont("Helvetica-Bold", 12)
        can.drawCentredString(105, 646, "✔")

    can.setFont("Helvetica-Bold", 11)
    can.drawCentredString(101.5, 610, f"+{prof_bonus}")

    # 4. Tiri Salvezza (Saving Throws)
    save_rows = [
        ("FOR", 576.2),
        ("DES", 562.7),
        ("COS", 549.2),
        ("INT", 535.7),
        ("SAG", 522.2),
        ("CAR", 508.7),
    ]
    for code, y_pos in save_rows:
        is_prof = code in save_profs
        if is_prof:
            can.circle(88.5, y_pos + 2.5, 2.0, fill=1, stroke=0)
            st_bonus = mods[code] + prof_bonus
        else:
            st_bonus = mods[code]
        b_str = f"+{st_bonus}" if st_bonus >= 0 else str(st_bonus)
        can.setFont("Helvetica-Bold", 8)
        can.drawCentredString(107.5, y_pos, b_str)

    # 5. Abilità (Skills - 18)
    skill_rows = [
        ("Acrobazia", 460.9),
        ("Addestrare Animali", 447.4),
        ("Arcano", 433.9),
        ("Atletica", 420.4),
        ("Furtività", 406.9),
        ("Indagare", 393.4),
        ("Inganno", 379.9),
        ("Intimidire", 366.4),
        ("Intrattenere", 352.9),
        ("Intuizione", 339.4),
        ("Medicina", 325.9),
        ("Natura", 312.4),
        ("Percezione", 298.9),
        ("Persuasione", 285.4),
        ("Rapidità di Mano", 271.9),
        ("Religione", 258.4),
        ("Sopravvivenza", 244.9),
        ("Storia", 231.3),
    ]
    for skill_name, y_pos in skill_rows:
        prof_lvl = skills_data.get(skill_name, 0)
        if prof_lvl == 0 and skill_name == "Rapidità di Mano":
            prof_lvl = skills_data.get("Prestidigitazione", 0)

        stat_code = SKILL_ABILITY_MAP.get(skill_name, "DES")
        total_bonus = mods.get(stat_code, 0) + (int(prof_lvl) * prof_bonus)

        if prof_lvl == 1:
            can.circle(88.5, y_pos + 2.5, 2.0, fill=1, stroke=0)
        elif prof_lvl >= 2:
            can.circle(88.5, y_pos + 2.5, 2.0, fill=1, stroke=0)
            can.circle(88.5, y_pos + 2.5, 3.5, fill=0, stroke=1)

        b_str = f"+{total_bonus}" if total_bonus >= 0 else str(total_bonus)
        can.setFont("Helvetica-Bold", 8)
        can.drawCentredString(107.5, y_pos, b_str)

    # 6. Percezione Passiva (Saggezza Passiva)
    perc_prof = skills_data.get("Percezione", 0)
    passive_perc = 10 + mods.get("SAG", 0) + (int(perc_prof) * prof_bonus)
    can.setFont("Helvetica-Bold", 11)
    can.drawCentredString(48, 184, str(passive_perc))

    # 7. Altre Competenze e Linguaggi (box in basso a sinistra)
    prof_langs_text = []
    if data.get("languages"):
        langs = data["languages"] if isinstance(data["languages"], str) else ", ".join(data["languages"])
        prof_langs_text.append(f"Linguaggi: {langs}")
    if data.get("proficiencies"):
        profs = data["proficiencies"] if isinstance(data["proficiencies"], str) else ", ".join(data["proficiencies"])
        prof_langs_text.append(f"Competenze: {profs}")
    if data.get("travel_role") and data["travel_role"] != "Nessuna":
        prof_langs_text.append(f"Ruolo di Viaggio: {data['travel_role']}")
    if not prof_langs_text:
        prof_langs_text.append("Competenze standard armi e armature di classe.")

    _draw_wrapped_lines(can, "\n".join(prof_langs_text), 40, 142, 150, 9.5, max_lines=11, font_size=7.5)

    # 8. Valori di Combattimento (CA, Iniziativa, Velocità)
    ac = data.get("ac", 10 + mods.get("DES", 0))
    can.setFont("Helvetica-Bold", 14)
    can.drawCentredString(237, 632, str(ac))

    init_val = data.get("initiative", mods.get("DES", 0))
    init_str = f"+{init_val}" if init_val >= 0 else str(init_val)
    can.setFont("Helvetica-Bold", 13)
    can.drawCentredString(287, 632, init_str)

    speed_val = data.get("speed", 9)
    unit = data.get("speed_unit", "m")
    can.setFont("Helvetica-Bold", 10)
    can.drawCentredString(348, 632, f"{speed_val} {unit}".strip())

    # 9. Punti Ferita (HP Max, Attuali, Temporanei)
    hp_max = data.get("hp_max", 10)
    hp_cur = data.get("hp_current", hp_max)
    temp_hp = data.get("temp_hp", 0)

    can.setFont("Helvetica-Bold", 9)
    can.drawCentredString(315, 582, str(hp_max))

    can.setFont("Helvetica-Bold", 15)
    can.drawCentredString(295, 554, str(hp_cur))

    if temp_hp:
        can.setFont("Helvetica-Bold", 12)
        can.drawCentredString(295, 500, str(temp_hp))

    # 10. Dadi Vita e Tiri Salvezza contro Morte
    hd_tot = data.get("hit_dice_total", level)
    hd_cur = data.get("hit_dice_current", hd_tot)
    hd_type = str(data.get("hit_dice_type", "d8")).lower()

    can.setFont("Helvetica-Bold", 8)
    can.drawString(245, 462, str(hd_tot))
    can.setFont("Helvetica-Bold", 11)
    can.drawCentredString(250, 446, f"{hd_cur} {hd_type}")

    death_saves = data.get("death_saves", {})
    if isinstance(death_saves, dict):
        succ = int(death_saves.get("successes", 0))
        fail = int(death_saves.get("failures", 0))
        succ_xs = [345, 355, 365]
        fail_xs = [345, 355, 365]
        for idx in range(min(succ, 3)):
            can.circle(succ_xs[idx], 463.0, 2.3, fill=1, stroke=0)
        for idx in range(min(fail, 3)):
            can.circle(fail_xs[idx], 448.0, 2.3, fill=1, stroke=0)

    # 11. Attacchi & Incantesimi
    weapons = data.get("weapons", [])
    if isinstance(weapons, list):
        attack_rows_y = [385, 370, 355]
        for idx, w in enumerate(weapons[:3]):
            y_r = attack_rows_y[idx]
            w_name = str(w.get("name", "Arma"))[:14]
            w_bonus = w.get("bonus", mods.get("FOR", 0) + prof_bonus)
            b_str = f"+{w_bonus}" if w_bonus >= 0 else str(w_bonus)
            w_dice = str(w.get("damage_dice", "1d6"))
            w_type = str(w.get("damage_type", ""))
            dmg_str = f"{w_dice} {w_type}".strip()[:14]

            can.setFont("Helvetica-Bold", 8)
            can.drawString(216, y_r, w_name)
            can.setFont("Helvetica", 8)
            can.drawCentredString(298, y_r, b_str)
            can.drawString(322, y_r, dmg_str)

    # Note attacco aggiuntive (armi oltre le prime 3, resistenze, immunità)
    extra_atk_lines = []
    if len(weapons) > 3:
        for w in weapons[3:]:
            extra_atk_lines.append(f"• {w.get('name')}: +{w.get('bonus',0)} ({w.get('damage_dice')} {w.get('damage_type','')})")
    if data.get("damage_resistances"):
        res = ", ".join(data["damage_resistances"]) if isinstance(data["damage_resistances"], list) else str(data["damage_resistances"])
        extra_atk_lines.append(f"Resistenze: {res}")
    if data.get("damage_immunities"):
        imm = ", ".join(data["damage_immunities"]) if isinstance(data["damage_immunities"], list) else str(data["damage_immunities"])
        extra_atk_lines.append(f"Immunità: {imm}")

    if extra_atk_lines:
        _draw_wrapped_lines(can, "\n".join(extra_atk_lines), 216, 335, 160, 9.0, max_lines=9, font_size=7)

    # 12. Monete (MR, MA, ME, MO, MP)
    curr = data.get("currency", {})
    if isinstance(curr, dict):
        can.setFont("Helvetica-Bold", 8)
        can.drawCentredString(228, 179, str(curr.get("MR", 0)))
        can.drawCentredString(228, 153, str(curr.get("MA", 0)))
        can.drawCentredString(228, 127, str(curr.get("ME", 0)))
        can.drawCentredString(228, 101, str(curr.get("MO", 0)))
        can.drawCentredString(228, 75, str(curr.get("MP", 0)))

    # 13. Equipaggiamento / Inventario
    inv_items = []
    grid = data.get("inventory_grid", [])
    if isinstance(grid, list):
        for item in grid:
            if isinstance(item, dict) and item.get("name"):
                qty = item.get("qty", 1)
                wt = item.get("weight", 0)
                wt_str = f" ({wt} lb)" if wt else ""
                inv_items.append(f"• {item['name']} x{qty}{wt_str}")
    if not inv_items and data.get("inventory"):
        raw_inv = data["inventory"]
        if isinstance(raw_inv, list):
            for it in raw_inv:
                if isinstance(it, dict):
                    inv_items.append(f"• {it.get('name', 'Oggetto')} (x{it.get('qty', 1)})")
                else:
                    inv_items.append(f"• {it}")
        elif isinstance(raw_inv, str):
            inv_items.extend(raw_inv.split("\n"))

    if inv_items:
        _draw_wrapped_lines(can, "\n".join(inv_items), 256, 195, 118, 8.5, max_lines=18, font_size=7)

    # 14. Colonna destra (Tratti, Ideali, Legami, Difetti)
    traits = data.get("personality_traits", "") or data.get("traits", "")
    ideals = data.get("ideals", "")
    bonds = data.get("bonds", "")
    flaws = data.get("flaws", "")

    _draw_wrapped_lines(can, str(traits), 410, 630, 150, 9.0, max_lines=5, font_size=7.5)
    _draw_wrapped_lines(can, str(ideals), 410, 575, 150, 9.0, max_lines=4, font_size=7.5)
    _draw_wrapped_lines(can, str(bonds), 410, 520, 150, 9.0, max_lines=4, font_size=7.5)
    _draw_wrapped_lines(can, str(flaws), 410, 465, 150, 9.0, max_lines=4, font_size=7.5)

    # 15. Privilegi e Tratti (Features & Traits - Colonna destra inferiore)
    features_lines = []
    class_res = data.get("class_resources", {})
    if isinstance(class_res, dict):
        if class_res.get("rage_max", 0) > 0:
            features_lines.append(f"• Ira: {class_res.get('rage_current', 0)}/{class_res.get('rage_max', 0)}")
        if class_res.get("second_wind"):
            features_lines.append("• Secondo Fiato: Disponibile")
        if class_res.get("action_surge"):
            features_lines.append("• Azione Impetuosa: Disponibile")

    for cres in data.get("custom_resources", []):
        if isinstance(cres, dict) and cres.get("name"):
            features_lines.append(f"• {cres['name']}: {cres.get('current',0)}/{cres.get('max',0)} (Reset: {cres.get('reset_on', 'long')})")

    feats = data.get("features", "")
    if isinstance(feats, str) and feats.strip():
        features_lines.append(feats.strip())
    elif isinstance(feats, list):
        for f in feats:
            features_lines.append(f"• {f}")

    if features_lines:
        _draw_wrapped_lines(can, "\n".join(features_lines), 410, 405, 150, 9.0, max_lines=38, font_size=7)

    can.showPage()

    # =========================================================================
    # PAGINA 1: Dettagli Personaggio, Aspetto, Alleati e Storia
    # =========================================================================
    can.setFillColor(black)
    can.setFont("Helvetica-Bold", 13)
    can.drawString(55, 703, name[:28])

    can.setFont("Helvetica", 9)
    can.drawString(265, 728, str(data.get("age", ""))[:12])
    can.drawString(330, 728, str(data.get("height", ""))[:12])
    can.drawString(390, 728, str(data.get("weight", ""))[:12])

    can.drawString(265, 701, str(data.get("eyes", ""))[:12])
    can.drawString(330, 701, str(data.get("skin", ""))[:12])
    can.drawString(390, 701, str(data.get("hair", ""))[:12])

    # Aspetto Personaggio
    appearance = data.get("appearance", "")
    _draw_wrapped_lines(can, str(appearance), 45, 640, 160, 9.5, max_lines=18, font_size=7.5)

    # Alleati & Organizzazioni
    allies = data.get("allies", "")
    campaign_info = data.get("campaign", "")
    if campaign_info and campaign_info != "Nessuna Campagna":
        allies = f"Campagna: {campaign_info}\n" + str(allies)
    _draw_wrapped_lines(can, str(allies), 225, 640, 160, 9.5, max_lines=18, font_size=7.5)

    # Tratti e Privilegi Aggiuntivi
    add_traits = data.get("additional_traits", "") or data.get("notes", "")
    _draw_wrapped_lines(can, str(add_traits), 225, 420, 340, 9.5, max_lines=18, font_size=7.5)

    # Storia del Personaggio (Backstory)
    backstory = data.get("backstory", "") or data.get("journal_notes", "")
    _draw_wrapped_lines(can, str(backstory), 45, 420, 160, 9.5, max_lines=36, font_size=7.5)

    # Tesoro
    treasure = data.get("treasure", "")
    _draw_wrapped_lines(can, str(treasure), 225, 195, 340, 9.5, max_lines=14, font_size=7.5)

    can.showPage()

    # =========================================================================
    # PAGINA 2: Incantesimi (Spellcasting)
    # =========================================================================
    can.setFillColor(black)

    # 1. Header Incantatore
    spell_class = data.get("spellcasting_class", char_class)
    can.setFont("Helvetica-Bold", 10)
    can.drawString(55, 704, str(spell_class)[:24])

    spell_ability = data.get("spellcasting_ability")
    if not spell_ability:
        spell_ability = CLASS_SPELLCASTING_ABILITY.get(str(char_class).lower(), "INT")

    can.drawCentredString(285, 718, str(spell_ability))

    spell_mod = mods.get(spell_ability, 0)
    spell_dc = 8 + prof_bonus + spell_mod
    spell_atk = prof_bonus + spell_mod
    atk_str = f"+{spell_atk}" if spell_atk >= 0 else str(spell_atk)

    can.drawCentredString(385, 718, str(spell_dc))
    can.drawCentredString(485, 718, atk_str)

    # 2. Configurazione Colonne e Livelli Incantesimo
    level_sections = {
        0: {"x": 42, "prep_x": None, "y_start": 615, "max_items": 8, "has_slots": False},
        1: {"x": 56, "prep_x": 45, "y_start": 425, "max_items": 12, "has_slots": True, "slot_tot_x": 68, "slot_tot_y": 463, "slot_spd_x": 115, "slot_spd_y": 463},
        2: {"x": 56, "prep_x": 45, "y_start": 195, "max_items": 13, "has_slots": True, "slot_tot_x": 68, "slot_tot_y": 234, "slot_spd_x": 115, "slot_spd_y": 234},
        3: {"x": 244, "prep_x": 233, "y_start": 590, "max_items": 13, "has_slots": True, "slot_tot_x": 256, "slot_tot_y": 630, "slot_spd_x": 303, "slot_spd_y": 630},
        4: {"x": 244, "prep_x": 233, "y_start": 365, "max_items": 13, "has_slots": True, "slot_tot_x": 256, "slot_tot_y": 404, "slot_spd_x": 303, "slot_spd_y": 404},
        5: {"x": 244, "prep_x": 233, "y_start": 140, "max_items": 9, "has_slots": True, "slot_tot_x": 256, "slot_tot_y": 178, "slot_spd_x": 303, "slot_spd_y": 178},
        6: {"x": 432, "prep_x": 421, "y_start": 590, "max_items": 9, "has_slots": True, "slot_tot_x": 443, "slot_tot_y": 630, "slot_spd_x": 490, "slot_spd_y": 630},
        7: {"x": 432, "prep_x": 421, "y_start": 420, "max_items": 9, "has_slots": True, "slot_tot_x": 443, "slot_tot_y": 460, "slot_spd_x": 490, "slot_spd_y": 460},
        8: {"x": 432, "prep_x": 421, "y_start": 250, "max_items": 7, "has_slots": True, "slot_tot_x": 443, "slot_tot_y": 290, "slot_spd_x": 490, "slot_spd_y": 290},
        9: {"x": 432, "prep_x": 421, "y_start": 110, "max_items": 7, "has_slots": True, "slot_tot_x": 443, "slot_tot_y": 150, "slot_spd_x": 490, "slot_spd_y": 150},
    }

    # Raggruppa incantesimi per livello da spellbook
    spellbook = data.get("spellbook", [])
    spells_by_lvl: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(10)}
    if isinstance(spellbook, list):
        for sp in spellbook:
            if isinstance(sp, dict):
                try:
                    s_lvl = int(sp.get("level", 0))
                except (ValueError, TypeError):
                    s_lvl = 0
                if 0 <= s_lvl <= 9:
                    spells_by_lvl[s_lvl].append(sp)

    # Slot incantesimo (livelli 1-9)
    spell_slots = data.get("spell_slots", {})
    if not isinstance(spell_slots, dict):
        spell_slots = {}

    for lvl, sec in level_sections.items():
        # Slot totali e spesi
        if sec.get("has_slots"):
            slot_info = spell_slots.get(str(lvl), {})
            if isinstance(slot_info, dict):
                s_tot = slot_info.get("max", 0)
                s_cur = slot_info.get("current", s_tot)
                s_spent = max(0, s_tot - s_cur)
            elif isinstance(slot_info, (list, tuple)) and len(slot_info) >= 2:
                s_tot = slot_info[1]
                s_spent = slot_info[0]
            else:
                s_tot = 0
                s_spent = 0

            if s_tot > 0:
                can.setFont("Helvetica-Bold", 8)
                can.drawCentredString(sec["slot_tot_x"], sec["slot_tot_y"], str(s_tot))
                if s_spent > 0:
                    can.drawCentredString(sec["slot_spd_x"], sec["slot_spd_y"], str(s_spent))

        # Lista incantesimi del livello
        cur_y = sec["y_start"]
        sp_list = spells_by_lvl.get(lvl, [])
        for sp in sp_list[:sec["max_items"]]:
            sp_name = str(sp.get("name", "Incantesimo"))[:24]
            can.setFont("Helvetica", 7.5)
            # Cerchietto di preparazione se preparato
            if sec.get("prep_x") and sp.get("prepared", False):
                can.circle(sec["prep_x"], cur_y + 2.5, 2.0, fill=1, stroke=0)
            can.drawString(sec["x"], cur_y, sp_name)
            cur_y -= 11.5

    can.showPage()
    can.save()

    # =========================================================================
    # Merge overlay con il template ufficiale (PyPDF)
    # =========================================================================
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    template_reader = PdfReader(template_path)
    writer = PdfWriter()

    for idx, template_page in enumerate(template_reader.pages):
        added_page = writer.add_page(template_page)
        if idx < len(overlay_reader.pages):
            added_page.merge_page(overlay_reader.pages[idx])

    # Crea directory padre se non esiste
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    return output_path
