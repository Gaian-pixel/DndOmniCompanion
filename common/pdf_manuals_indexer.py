# common/pdf_manuals_indexer.py
"""
Modulo di indicizzazione e gestione coerente dei manuali D&D 5e / 2024 in formato PDF.
Estrae sezioni, regole, classi, incantesimi, mostri e strumenti del DM memorizzandoli
in un indice strutturato JSON ultra-veloce (manuals/pdf_index_cache.json).
In questo modo l'applicazione non interroga il PDF grezzo da centinaia di MB,
ma accede in 30ms a voci coerenti integrate nel compendio e nelle meccaniche di gioco.
"""

import os
import re
import json
import time
import threading
from typing import List, Dict, Optional, Tuple, Callable

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

from common.file_utils import get_base_dir, get_writable_dir

BASE_DIR = get_base_dir()
_writable_pdf_dir = os.path.join(get_writable_dir(), "manuals_pdf")
PDF_DIR = _writable_pdf_dir if os.path.exists(_writable_pdf_dir) else os.path.join(BASE_DIR, "manuals_pdf")
_writable_cache = os.path.join(get_writable_dir(), "manuals", "pdf_index_cache.json")
CACHE_FILE = _writable_cache if os.path.exists(_writable_cache) else os.path.join(BASE_DIR, "manuals", "pdf_index_cache.json")

from common.srd_offline import extract_and_normalize_attributes, get_monster_offline

# Dizionario traduzioni / sinonimi italiano-inglese per ricerca istantanea
ITALIAN_TRANSLATIONS = {
    # Condizioni & Stati
    "blinded": ["accecato", "cecità"],
    "charmed": ["affascinato", "ammaliato"],
    "deafened": ["assordato"],
    "exhaustion": ["sfinimento", "esausto"],
    "frightened": ["spaventato", "paura"],
    "grappled": ["afferrato", "lotta"],
    "incapacitated": ["incapace di agire", "inabile"],
    "invisible": ["invisibile", "invisibilità"],
    "paralyzed": ["paralizzato", "paralisi"],
    "petrified": ["pietrificato", "pietrificazione"],
    "poisoned": ["avvelenato", "veleno"],
    "prone": ["prono", "a terra"],
    "restrained": ["trattenuto", "immobilizzato"],
    "stunned": ["stordito", "stordimento"],
    "unconscious": ["incosciente", "privo di sensi", "svenuto"],
    # Azioni di combattimento
    "attack": ["attacco", "attaccare"],
    "dash": ["scatto", "correre"],
    "disengage": ["disimpegno", "disimpegnarsi"],
    "dodge": ["schivata", "schivare"],
    "help": ["aiuto", "aiutare"],
    "hide": ["nascondersi", "furtività"],
    "ready": ["preparare", "azione preparata"],
    "search": ["cercare", "indagare"],
    # Classi
    "barbarian": ["barbaro", "ira"],
    "bard": ["bardo", "ispirazione"],
    "cleric": ["chierico"],
    "druid": ["druido", "forma selvatica"],
    "fighter": ["guerriero"],
    "monk": ["monaco", "ki"],
    "paladin": ["paladino", "punizione divina"],
    "ranger": ["ranger"],
    "rogue": ["ladro", "attacco furtivo"],
    "sorcerer": ["stregone"],
    "warlock": ["warlock", "patrono"],
    "wizard": ["mago", "grimorio"],
    "artificer": ["artefice", "infusioni"],
    # Regole & Meccaniche
    "resting": ["riposo", "riposo breve", "riposo lungo"],
    "short rest": ["riposo breve", "dadi vita"],
    "long rest": ["riposo lungo"],
    "cover": ["copertura", "riparo"],
    "falling": ["caduta", "danni da caduta"],
    "suffocation": ["soffocamento"],
    "burning": ["a fuoco", "bruciare"],
    "advantage": ["vantaggio"],
    "disadvantage": ["svantaggio"],
    "fireball": ["palla di fuoco"],
    "magic missile": ["dardo incantato"],
    "cure wounds": ["cura ferite"],
    "counterspell": ["controincantesimo"],
    "shield": ["scudo"],
    "haste": ["velocità"],
    "fly": ["volare"],
    "beholder": ["occhio tiranno", "beholder"],
    "goblin": ["goblin"],
    "dragon": ["drago"],
    "zombie": ["zombi", "non morto"],
    "skeleton": ["scheletro"],
    "lich": ["lich"],
    "orc": ["orco"],
    "troll": ["troll"],
}

# Correzioni OCR comuni per titoli dai PDF
OCR_FIXES = [
    (r'\b8([a-zA-Z])', r'B\1'),         # 8oss -> Boss, 8ear -> Bear
    (r'([a-zA-Z])1([a-zA-Z])', r'\1l\2'), # A11osaurus -> Allosaurus
    (r'([a-zA-Z])1\b', r'\1l'),          # Anima1 -> Animal
    (r'([a-zA-Z])2([a-zA-Z])', r'\1z\2'), # Li2ard -> Lizard
    (r'\b2([a-zA-Z])', r'Z\1'),          # 2ombie -> Zombie
    (r'\b0([a-zA-Z])', r'O\1'),          # 0gre -> Ogre
    (r'\bBnnorDER\b', 'Beholder'),
]

# Mostri iconici aggiuntivi del Monster Manual da garantire sempre
ADDITIONAL_MM_ENTRIES = [
    {"name": "Beholder", "page": 36, "ac": 18, "hp": 180, "cr": "13", "desc": "Aberration, Lawful Evil. The iconic many-eyed tyrant of the Underdark with lethal eye rays and Antimagic Cone."},
    {"name": "Gelatinous Cube", "page": 230, "ac": 6, "hp": 84, "cr": "2", "desc": "Large Ooze, Unaligned. Transparent dungeon cleaner that engulfs adventurers and dissolves organic matter."},
    {"name": "Mimic", "page": 210, "ac": 12, "hp": 58, "cr": "2", "desc": "Medium Monstrosity (Shapechanger), Neutral. Deceptive predator that disguises itself as chests, doors or furniture."},
    {"name": "Lich", "page": 196, "ac": 17, "hp": 135, "cr": "21", "desc": "Medium Undead (Wizard), Any Evil Alignment. Legendary undead spellcaster bound to a soul-storing phylactery."},
    {"name": "Mind Flayer", "page": 212, "ac": 15, "hp": 71, "cr": "7", "desc": "Medium Aberration, Lawful Evil. Psionic tyrant with tentacled maw that extracts and consumes brains."},
    {"name": "Displacer Beast", "page": 98, "ac": 13, "hp": 85, "cr": "3", "desc": "Large Monstrosity, Lawful Evil. Six-legged predator that bends light to appear several feet away from its true space."},
]


def clean_text(text: str) -> str:
    """Rimuove stranezze da estrazione PDF come a capo a metà parola o troppi spazi."""
    if not text:
        return ""
    text = re.sub(r'([A-Za-z])-[\r\n]+([A-Za-z])', r'\1\2', text)
    text = re.sub(r'[\r\n]+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def clean_ocr_name(name: str) -> str:
    """Corregge errori tipici di OCR come 8oss -> Boss, Li2ard -> Lizard, 2ombie -> Zombie."""
    for pattern, repl in OCR_FIXES:
        name = re.sub(pattern, repl, name)
    return name.strip()


def preserve_case_sub(pattern: str, replacement_lower: str, text: str) -> str:
    """Sostituisce il pattern preservando il casing originale (ALL CAPS, Title Case, o lowercase)."""
    def repl(m):
        orig = m.group(0)
        if orig.isupper():
            return replacement_lower.upper()
        if orig[0].isupper():
            return replacement_lower.capitalize()
        return replacement_lower
    return re.sub(pattern, repl, text, flags=re.I)


def format_clean_manual_text(text: str, title: str = "") -> str:
    """
    Riformatta il testo estratto dal PDF per renderlo altamente leggibile e strutturato:
    - Rimuove intestazioni di pagina (es. CHAPTER 3 | DM's TOOLBOX) e numeri isolati
    - Elimina testo spazzatura, riquadri arte o note corsive OCR illeggibili (Tasha / Xanathar)
    - Recupera lettere e drop-caps mancanti (es. AGIC IS EVERYWHERE -> Magic is everywhere)
    - Ripara tracking e kerning spezzati da InDesign (es. Ch Apter -> Chapter, supernat ural -> supernatural)
    - Ricostruisce tabelle spezzate multi-colonna (es. Tabelle incantesimi di TCoE e XGtE) in Markdown
    - Risolve parole unite da OCR (es. creaturesfor -> creatures for)
    - Converte paragrafi e linee spezzate in testo continuo e fluido
    - Trasforma i sottotitoli in maiuscolo in intestazioni Markdown (#### Sottotitolo)
    - Converte liste di tratti e abilità in elenchi puntati formattati (• **Nome**: Descrizione)
    """
    if not text:
        return ""

    # 0. Rimuovi caratteri invisibili, BOM e soft hyphens
    text = text.replace('\xad', '').replace('\u00ad', '').replace('\ufeff', '')

    # 1. Risolvi trattini a fine riga (parole spezzate)
    text = re.sub(r'([A-Za-z])-[\r\n]+([A-Za-z])', r'\1\2', text)

    # 2. Rimuovi artefatti orfani di drop-caps a inizio pagina (es. 'a ...')
    text = re.sub(r'(?im)^\s*[a-z]\s*[\.\s…]{2,}\s*$', '', text)
    text = re.sub(r'(?m)^\s*[a-zA-Z]\s*$', '', text)

    # 3. Rimuovi running headers e footers
    text = re.sub(r'(?i)chapter\s+\d+\s*[\|I]\s*[^\n]+', '', text)
    text = re.sub(r'(?i)part\s+\d+\s*[\|I]\s*[^\n]+', '', text)
    text = re.sub(r'(?i)appendix\s+[a-z]\s*[\|I]\s*[^\n]+', '', text)
    text = re.sub(r'(?m)^\s*\d{1,3}\s*$', '', text)

    # 4. Rimuovi note a margine in corsivo corrotte da OCR (frecce e note comiche di Tasha e Xanathar)
    text = re.sub(r'(?s)(?:I\s*\n\s*)?Well,\s*&?Ar.*?TA[^\n]*HA\b', '', text)
    text = re.sub(r'(?s)(?:^|\n)\s*I\s*\n\s*Well,.*?TA[^\n]*HA\b', '', text)
    text = re.sub(r'(?s)(?:^|\n)[^\n]*?(?:\\pell\\|&Ar|hAppe\?d|Bo1A).*?TA[^\n]*HA\b', '', text)
    text = re.sub(r'(?s)(?:^|\n)[^\n]*?(?:I\s+love\s+goldfish|beauty\s+is\s+in\s+the\s+eye|sylgar).*?XANATHAR\b', '', text)

    # 5. Ripristino lettere capitali mancanti nei capilettera decorativi
    drop_cap_fixes = [
        (r'\bAGIC\s+IS\s+EVERYWHERE\s+IN\s+D&D\.\s*MANY\b', 'Magic is everywhere in D&D. Many'),
        (r'\bAGIC\s+IS\s+EVERYWHERE\b', 'Magic is everywhere'),
        (r'\bDVENTURING\b', 'Adventuring'),
        (r'\bHARACTER\b', 'Character'),
        (r'\bOMBAT\b', 'Combat'),
        (r'\bPELLS\b', 'Spells'),
        (r'\bREATURES\b', 'Creatures'),
        (r'\bUNGEON\b', 'Dungeon'),
        (r'\bREASURE\b', 'Treasure'),
        (r'\bULES\b', 'Rules'),
        (r'\bLAYING\b', 'Playing'),
        (r'\bACKGROUNDS\b', 'Backgrounds'),
        (r'\bQUIPMENT\b', 'Equipment'),
    ]
    for p, r in drop_cap_fixes:
        text = re.sub(p, r, text)

    # 6. Riparazione tracking e kerning spezzati da InDesign
    kern_repls = [
        (r'\bCh\s+Apter\b', 'chapter'),
        (r'\bsupernat\s*ural\b', 'supernatural'),
        (r'\blik\s+e\b', 'like'),
        (r'\bpl\s+ay\b', 'play'),
        (r'\bspellcas\s*ters\b', 'spellcasters'),
        (r'\bBl\s+ade\b', 'blade'),
        (r'\bSliv\s+er\b', 'sliver'),
        (r'\bBur\s+st\b', 'burst'),
        (r'\bCaus\s+tic\b', 'caustic'),
        (r'\bEncha\s*ntment\b', 'enchantment'),
        (r'\b3r\s+d\b', '3rd'),
        (r'\bl\s+st\b', '1st'),
        (r'\bIn\s*tell\s*ect\b', 'intellect'),
        (r'\bSpi\s*rit\b', 'spirit'),
        (r'\bShr\s*oud\b', 'shroud'),
        (r'\bNe\s*croma\s*ncy\b', 'necromancy'),
        (r'\bSumm\s+on\b', 'summon'),
        (r'\bShado\s*wspawn\b', 'shadowspawn'),
        (r'\bUn\s+dead\b', 'undead'),
        (r'\bAberra\s*tion\b', 'aberration'),
        (r'\bConj\s*ur\s*ation\b', 'conjuration'),
        (r'\bOtherwo\s*rldly\b', 'otherworldly'),
        (r'\bGu\s+ise\b', 'guise'),
        (r'\bTransmut\s*ation\b', 'transmutation'),
        (r'\bDis\s+aster\b', 'disaster'),
        (r'\bArtifi\s*cer\b', 'artificer'),
        (r'\bArtific\s*er\b', 'artificer'),
        (r'\bSo\s*r\s*cerer\b', 'sorcerer'),
        (r'\bWa\s*rlock\b', 'warlock'),
        (r'\bBar\s+d\b', 'bard'),
        (r'\bPala\s*d\s*in\b', 'paladin'),
        (r'\bPa\s*ladin\b', 'paladin'),
        (r'\bRan\s*ger\b', 'ranger'),
        (r'\bRang\s*er\b', 'ranger'),
        (r'\bWizar\s+d\b', 'wizard'),
        (r'\bAbj\s*ur\s*ation\b', 'abjuration'),
        (r'\bPoti\s*on\s*s\s+o\s*f\b', 'potions of'),
        (r'\bPoti\s*on\b', 'potion'),
        (r'\bs\s*pecia\s*l\b', 'special'),
        (r'\bite\s*m\b', 'item'),
        (r'\bcraft\s*ing\b', 'crafting'),
        (r'\bsepa\s*rate\b', 'separate'),
        (r'\bm\s+agic\b', 'magic'),
        (r'\bcharacte\s*r\b', 'character'),
        (r'\bh\s+as\b', 'has'),
        (r'\bprofi\s*ciency\b', 'proficiency'),
        (r'\bk\s+it\b', 'kit'),
        (r'\bca\s+n\b', 'can'),
        (r'\bdoin\s*g\b', 'doing'),
        (r'\ba\s+re\b', 'are'),
        (r'\bs\s*umm\s*a\s*rized\b', 'summarized'),
        (r'\bHea\s*ling\b', 'healing'),
        (r'\bC\s*reation\b', 'creation'),
        (r'\bta\s*ble\b', 'table'),
    ]
    for p, rep in kern_repls:
        text = preserve_case_sub(p, rep, text)

    # Rimuovi intestazione di capitolo ridondante se già presente nel titolo dell'entry
    if title and re.match(r'(?i)^(?:ch(?:apter)?\.?\s*\d+)', title):
        text = re.sub(r'(?i)^\s*chapter\s+\d+\s*\n\s*[a-z\s\']+\n', '', text)

    # 7. Ricostruzione tabelle incantesimi multi-colonna (es. TCoE / XGtE)
    t_match = re.search(r'Level\s+Spell\s+School\s+Con[ce]\.?(.*?)(?:\n\s*(?:SPELLS|This section|\n\n))', text, re.DOTALL)
    rit_match = re.search(r'Ritual\s*\n((?:(?:Yes|No)\s*\n?)+)', text, re.IGNORECASE)
    cls_match = re.search(r'Class\s*\n(.*?)(?:CHAPTER|\Z)', text, re.DOTALL)

    if t_match and rit_match and cls_match:
        rows1 = [l.strip() for l in t_match.group(1).strip().splitlines() if l.strip()]
        rits = [l.strip() for l in rit_match.group(1).strip().splitlines() if l.strip()]
        classes = [l.strip() for l in cls_match.group(1).strip().splitlines() if l.strip() and not l.upper().startswith('CHAPTER')]

        if len(rows1) == len(rits) == len(classes):
            table_lines = [
                '| Livello | Incantesimo | Scuola | Conc. | Rituale | Classi |',
                '| :--- | :--- | :--- | :---: | :---: | :--- |'
            ]
            for r1, rit, cls in zip(rows1, rits, classes):
                cls_clean = re.sub(r'\s+,', ',', cls)
                cls_clean = re.sub(r',\s*', ', ', cls_clean)
                m_row = re.match(r'^(0|\d+[a-z]{2})\s+(.*?)\s+(Abjuration|Conjuration|Divination|Enchantment|Evocation|Illusion|Necromancy|Transmutation)\s+(Yes|No)$', r1, re.I)
                if m_row:
                    lvl, sp_name, school, conc = m_row.groups()
                    table_lines.append(f'| {lvl} | {sp_name} | {school} | {conc} | {rit} | {cls_clean} |')
                else:
                    table_lines.append(f'| {r1} | | | | {rit} | {cls_clean} |')
            md_table = '\n'.join(table_lines)

            # Sostituisci il blocco grezzo con la tabella Markdown
            text = text[:t_match.start()] + '\n\n' + md_table + '\n\n' + text[t_match.end():]
            text = re.sub(r'Ritual\s*\n(?:(?:Yes|No)\s*\n?)+', '', text, flags=re.I)
            text = re.sub(r'Class\s*\n(?:[^\n]+\n?)+?(?=(?:CHAPTER|\Z))', '', text, flags=re.I)

    # 8. Elimina rumore/arte prima del titolo principale se presente
    if title:
        pattern = re.compile(rf'(?i)^.*?\b({re.escape(title)})\b', re.DOTALL)
        m = pattern.search(text[:600])
        if m:
            text = text[m.start(1):]

    # 9. Correzioni specifiche di parole unite e artefatti OCR comuni
    replacements = [
        (r"(\w)'s(\w)", r"\1's \2"),
        (r"([a-z])just\b", r"\1 just"),
        (r"\bcreaturesfor\b", "creatures for"),
        (r"\bfollowingpieces\b", "following pieces"),
        (r"\bfora\b", "for a"),
        (r"\bofa\b", "of a"),
        (r"\binstead ofa\b", "instead of a"),
        (r"\bifa\b", "if a"),
        (r"\bIfa\b", "If a"),
        (r"\bifthe\b", "if the"),
        (r"\bgivea\b", "give a"),
        (r"\bwitha\b", "with a"),
        (r"\bmakea\b", "make a"),
        (r"\btoa\b", "to a"),
        (r"\bofits\b", "of its"),
        (r"\bablade\b", "a blade"),
        (r"\btelepathyor\b", "telepathy or"),
        (r"\bal of\b", "all of"),
        (r"\bhi\s*ing\b", "hiding"),
        (r"\bmonst saving\b", "monster's saving"),
        (r"\bSEN\b", "SENSES"),
        (r"\b80,\s*It\'s\b", "so. It's"),
        (r"\bcharacterswith\b", "characters with"),
        (r"\bdamagewith\b", "damage with"),
        (r"\boneto\b", "one to"),
        (r"\btwoor\b", "two or"),
        (r"\bOfthe\b", "Of the"),
        (r"\bofthe\b", "of the"),
        (r"\bintothe\b", "into the"),
        (r"\bfromthe\b", "from the"),
        (r"\btothe\b", "to the"),
        (r"\batthe\b", "at the"),
        (r"\bonthe\b", "on the"),
        (r"\bforthe\b", "for the"),
        (r"\bwiththe\b", "with the"),
        (r"\binall\b", "in all"),
        (r"\biswasted\b", "is wasted"),
        (r"[‘’'\"`]+([A-Z])", r"\1"),
    ]
    for p, r in replacements:
        text = re.sub(p, r, text)

    # 10. Formatta sottotitoli, elenchi, tabelle e paragrafi fluidi
    lines = [l.strip() for l in text.split('\n')]
    formatted_blocks = []
    current_para = []
    in_traits_list = False

    def flush_para():
        if current_para:
            p_text = " ".join(current_para).strip()
            p_text = re.sub(r'[ \t]+', ' ', p_text)
            if p_text:
                formatted_blocks.append(p_text)
            current_para.clear()

    def is_likely_heading(line_str, next_line_str=""):
        if len(line_str) < 3 or len(line_str) > 50:
            return False
        if line_str.endswith(('.', ':', ';', ',')):
            return False
        if '.' in line_str[:-1]:
            return False
        if next_line_str and next_line_str.strip() and next_line_str.strip()[0].islower():
            return False
        words = line_str.split()
        if len(words) > 6:
            return False
        if line_str.isupper() and any(c.isalpha() for c in line_str):
            return True
        upper_chars = sum(1 for c in line_str if c.isupper())
        lower_chars = sum(1 for c in line_str if c.islower())
        if upper_chars > lower_chars and upper_chars >= 4:
            return True
        return False

    for i, line in enumerate(lines):
        if not line:
            if current_para and (current_para[-1].endswith((',', '-', ';')) or current_para[-1].split()[-1].lower() in ['and', 'or', 'of', 'the', 'a', 'an', 'to', 'in', 'with', 'for']):
                continue
            flush_para()
            continue

        # Tabelle Markdown: mantieni compatte senza spaziature vuote tra le righe
        if line.startswith('|'):
            flush_para()
            if formatted_blocks and formatted_blocks[-1].splitlines()[-1].startswith('|'):
                formatted_blocks[-1] += '\n' + line
            else:
                formatted_blocks.append(line)
            continue

        next_line = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            if lines[j]:
                next_line = lines[j]
                break

        # Riconoscimento sottotitoli di sezione
        if is_likely_heading(line, next_line):
            words = line.split()
            if len(words) == 1 and line.title() in ["Large", "Medium", "Small", "Tiny", "Huge", "Gargantuan"]:
                current_para.append(line)
                continue

            flush_para()
            head_title = line.title()
            if title and (head_title.lower() == title.lower() or head_title.lower() in title.lower() or title.lower() in head_title.lower()):
                # Già presente nel titolo dell'entry, evita intestazione ridondante
                pass
            else:
                formatted_blocks.append(f"#### {head_title}")
            if "trait" in line.lower() or "option" in line.lower() or "hazard" in line.lower():
                in_traits_list = True
            else:
                in_traits_list = False
            continue

        # Riconoscimento tratti / elementi di lista (es. "Battle Ready. Descrizione...")
        if in_traits_list:
            trait_match = re.match(r'^([A-Z][a-zA-Z\s\-\'\,\(\)]{2,30})\.\s+(.*)', line)
            if trait_match and len(trait_match.group(1).split()) <= 4:
                flush_para()
                t_name = trait_match.group(1).strip().title()
                t_desc = trait_match.group(2).strip()
                if t_desc:
                    t_desc = t_desc[0].upper() + t_desc[1:]
                current_para.append(f"• **{t_name}**: {t_desc}")
                continue

        # Riga di testo ordinaria: continua il paragrafo corrente
        current_para.append(line)

    flush_para()
    return "\n\n".join(formatted_blocks)


def normalize_stat_number(val, is_cr: bool = False):
    """Normalizza numeri da scansioni OCR (es. 'l' -> 1, 'I' -> 1, ''l9s' -> 195, '112' -> '1/2')."""
    if not val:
        return "1" if is_cr else 10
    v = str(val).replace('l', '1').replace('I', '1').replace('s', '5').replace('S', '5').replace("'", "").strip()
    if is_cr:
        v_clean = re.sub(r'[^0-9\/]', '', v)
        if v_clean in ["112", "1/2"]:
            return "1/2"
        if v_clean in ["114", "1/4"]:
            return "1/4"
        if v_clean in ["118", "1/8"]:
            return "1/8"
        return v_clean if v_clean else "1"
    try:
        digits = re.sub(r'[^0-9]', '', v)
        return int(digits) if digits else 10
    except Exception:
        return 10


TYPE_RE = re.compile(r'(?i)(tiny|small|medium|large|huge|gargantuan|monstrosity|construct|dragon|fiend|beast|humanoid|undead|celestial|elemental|fey|giant|ooze|plant|5\s*m\s*a\s*l|la\s*rge)')


def slice_monster_on_page(page_text: str, monster_name: str) -> str:
    """
    Isola il blocco statistico del mostro specifico se una pagina contiene più mostri.
    Usa la firma AC + HP per rilevare tutti i blocchi mostro e calcola il miglior match semantico.
    """
    if not page_text:
        return ""
    page_lines = page_text.splitlines()
    ac_indices = []
    for i, line in enumerate(page_lines):
        if re.search(r'\bAC\s+[0-9lI]+', line, re.I):
            has_hp = any(re.search(r'\bHP\s*[\'\"`]?\s*[0-9lIsS]+', page_lines[k], re.I) for k in range(i+1, min(len(page_lines), i+3)))
            if has_hp:
                ac_indices.append(i)

    if len(ac_indices) <= 1:
        return page_text

    start_indices = []
    for idx, ac_idx in enumerate(ac_indices):
        s = ac_idx - 1
        for j in range(ac_idx - 1, max(-1, ac_idx - 4), -1):
            lj = page_lines[j].strip()
            if TYPE_RE.search(lj):
                s = j
                if j > 0 and len(page_lines[j-1].split()) <= 4 and not page_lines[j-1].endswith('.'):
                    s = j - 1
                break
        start_indices.append(s)

    slices = []
    for idx in range(len(ac_indices)):
        s_idx = start_indices[idx]
        if idx + 1 < len(ac_indices):
            e_idx = start_indices[idx + 1]
        else:
            e_idx = len(page_lines)
            for k in range(len(page_lines) - 1, ac_indices[idx], -1):
                lk = page_lines[k].strip()
                alpha_count = sum(1 for c in lk if c.isalpha())
                if re.search(r'(?i)^[a-z\s]+\s+\d{1,3}$', lk) or alpha_count <= 2 or re.match(r'^[^a-zA-Z0-9]+$', lk):
                    e_idx = k
                else:
                    break
        slices.append("\n".join(page_lines[s_idx:e_idx]))

    m_lower = monster_name.lower().strip()
    m_words = set(w for w in re.findall(r'[a-z]+', m_lower) if len(w) > 2)

    modifiers = ['regent', 'wyrmling', 'young', 'adult', 'ancient', 'warhorse', 'ogre',
                 'fanatic', 'leader', 'boss', 'giant', 'greater', 'lesser', 'chieftain',
                 'warrior', 'shaman', 'guard', 'captain', 'mage', 'soldier', 'knight',
                 'apprentice', 'noble', 'veteran', 'commoner', 'bandit']

    best_s = slices[0]
    best_sc = -999
    for s in slices:
        s_lower = s.lower()
        score = 0
        for w in m_words:
            if w in s_lower:
                score += 10
        for mod in modifiers:
            if mod in m_words and mod in s_lower:
                score += 25
            elif mod not in m_words and mod in s_lower:
                score -= 30
        if score > best_sc:
            best_sc = score
            best_s = s

    return best_s


def find_monster_lore_snippet(reader, bpage: int, mname: str) -> str:
    """Estrae la breve descrizione narrativa/lore del mostro cercandola tra le pagine adiacenti."""
    words = [w.lower() for w in mname.split() if len(w) > 3 and w.lower() not in ['dragon', 'adult', 'young', 'ancient', 'warrior', 'boss']]
    for offset in [2, 1, 3]:
        p = bpage + offset
        if p >= len(reader.pages):
            continue
        txt = reader.pages[p].extract_text() or ''
        txt = re.sub(r'([A-Za-z])-[\r\n]+([A-Za-z])', r'\1\2', txt)
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        for idx, line in enumerate(lines):
            l_lower = line.lower()
            if any(w in l_lower for w in words):
                start_p = idx
                while start_p > 0 and not lines[start_p-1].endswith(('.', '!', '?')) and not re.search(r'\b(AC|HP|CR)\b', lines[start_p-1]):
                    if any(lines[start_p-1].startswith(h) for h in ['Coc', 'Large', 'Small', 'Medium', 'Huge', 'Ancient', 'Adult', 'Young']):
                        break
                    start_p -= 1
                para = []
                for nxt in lines[start_p:start_p+6]:
                    if re.search(r'\b(AC\s+[0-9lI]|HP\s+[0-9lI]|CR\s+[0-9lI]|MOD SAVE|Actions|Traits|Large|Small|Medium|Huge)\b', nxt, re.I):
                        break
                    para.append(nxt)
                    if nxt.endswith(('.', '!', '?')):
                        break
                p_text = " ".join(para).strip()
                p_text = re.sub(r'^[A-Za-z\s]{3,25}\b(?=[A-Z][a-z])', '', p_text).strip()
                p_text = re.sub(r'\s+(?:Coppen|Your?\.?r?c|Medium|Large|Huge)[^\.]*$', '.', p_text)
                if len(p_text) > 40 and not any(k in p_text for k in ['AC ', 'HP ', 'Hit:']):
                    if words and all(w in p_text.lower() for w in words):
                        return p_text
    return ""


def format_clean_monster_stat_block(text: str, monster_name: str, lore: str = "") -> str:
    """
    Pulisce e riformatta lo stat block di un mostro dal Monster Manual:
    - Rimuove intestazioni correnti, marginali e artefatti OCR
    - Riordina le sezioni in un flusso standard continuo
    - Ricongiunge frasi spezzate tra le colonne
    - Struttura i tratti e le azioni in elenchi puntati chiari e leggibili
    """
    if not text:
        return ""

    text = re.sub(r'([A-Za-z])-[\r\n]+([A-Za-z])', r'\1\2', text)

    # Rimuovi noise e piè di pagina
    text = re.sub(r'(?i)coPPER\s+DRAGONS[^\n]*', '', text)
    text = re.sub(r'(?i)Aoulr\s+Coppen\s+Dnacoru[^\n]*', '', text)
    text = re.sub(r'(?i)Coppe\.R\s+Dragons\d*', '', text)
    text = re.sub(r'(?i)MONSTER\s+MANUAL[^\n]*', '', text)
    text = re.sub(r'(?i)\bA\s+ZS\b', '', text)
    text = re.sub(r'\s+tt\s+', ' ', text)
    text = re.sub(r'(?m)^\s*[lI1\|\:\,\.\'\-]{1,2}\s*$', '', text)
    text = re.sub(r'(?m)^[lI1j\|]{2,4}\s*', '', text)
    text = re.sub(r'(?m)^[lj]i\s+', '', text)

    reps = [
        (r'\bLa\s*rge\b', 'Large'),
        (r'\b5\s*m\s*a\s*[lI]{2}\b|\bS\s*ma\s*[lI]{2}\b', 'Small'),
        (r'\bM\s*edium\b', 'Medium'),
        (r'\bM\s*onstrosity\b', 'Monstrosity'),
        (r'\bU\s*n\s*a\s*li\s*gn\s*e\s*d\b', 'Unaligned'),
        (r'\bLpceruolnv\s+Acrtorus\b', '#### Legendary Actions'),
        (r'\bLegendory\s+Action\s+Uses\b', 'Legendary Action Uses'),
        (r'\bI\s+Tnerrs\b|\bTnerrs\b|\bTRnrrs\b', '#### Traits'),
        (r'\bAcrroNs\b|\bAcrrorus\b', '#### Actions'),
        (r'\bBorus\s+AcrroNs\b', '#### Bonus Actions'),
        (r'\bReRcrrons\b|\bReacrtorus\b', '#### Reactions'),
        (r'\bi\s+lttultiattock\b|\blttultiattock\b', 'Multiattack.'),
        (r'\beetrifying\s+Bite\b', 'Petrifying Bite'),
        (r'\bBite\s+[lI1]\s+attack\b', 'Bite attack'),
        (r',\s+[lI1]\s+it\s+is\b', ', it is'),
        (r'\bSavingThrow\b|\bSovingThrow\b', 'Saving Throw'),
        (r'\bRechorge\b|\bRechonge\b', 'Recharge'),
        (r'\blnitiative\b', 'Initiative'),
        (r'\bCood\b', 'Good'),
        (r'\bMetallb\b', 'Metallic'),
        (r'\bChorisma\b', 'Charisma'),
        (r'\bfeel\b', 'feet'),
        (r'\bRo//\b', 'Roll'),
        (r'\bAttock\s+Roll\b|\bAttock\b', 'Attack Roll'),
        (r'\bsublected\b', 'subjected'),
        (r'1l\s+lZaa\s*\*\s*4\)', '(2d6 + 4)'),
        (r'lZaa\s*\*\s*4\)', '(2d6 + 4)'),
        (r'\blmmunities\b', 'Immunities'),
        (r'([A-Za-z])\.([A-Za-z])', r'\1. \2'),
        (r'\+l\b', '+1'),
        (r'\+l\s', '+1 '),
        (r'\+1\s+l\b|\+l\s+l\b', '+11'),
        (r'\+a\b', '+4'),
        (r'\.lf\b', '. If'),
        (r'reach\s*\'?(\d+)', r'reach \1'),
        (r'Hit:\s*l(\d)', r'Hit: 1\1'),
        (r'\(2d\.l0', '(2d10'),
        (r'\.l(\d)', r'1\1'),
        (r'\bin\s+Lai\b|\bin\s+Loir\b', 'in Lair'),
        (r'\b4/Doy\b', '4/Day'),
        (r'\b3/Day,\s*or\s*4/Doy\b', '3/Day, or 4/Day'),
        (r'\bactioni\b', 'actions'),
        (r'\beoch\b', 'each'),
        (r'\bot\s+the\b', 'at the'),
        (r'\bofits\b', 'of its'),
        (r'\buses\s+ot\s+the\b', 'uses at the'),
        (r'\bLegendory\s+Resistonce\b', 'Legendary Resistance'),
        (r'Speed\s+(\d+)[^\n]*?(?=\n|MOD|Srn|STR|Reactions)', r'Speed \1 ft.', ),
        (r'\bMindJolt\b', 'Mind Jolt'),
        (r'\bUses:\s*j\b', 'Uses: 3'),
        (r'\.l\.l,500', '11,500'),
        (r'\.l3,000', '13,000'),
        (r'DC\s*\.l(\d)', r'DC 1\1'),
        (r'(?i)\bAcid\s+Breath\s*\(Recharge\s*[0-9\-]+\)[,\.]', 'Acid Breath (Recharge 5-6).'),
        (r'\bcast\s+Mind\s*\n\s*Spike\b', 'cast Mind Spike'),
    ]
    for p, rep in reps:
        text = re.sub(p, rep, text, flags=re.I)

    # Rimuovi eventuale banner con nome del mostro direttamente sopra la riga di taglia
    text = re.sub(r'(?im)^[a-z0-9\s]{4,35}\n(?=(?:Tiny|Small|Medium|Large|Huge|Gargantuan)\s+(?:Aberration|Monstrosity|Dragon|Beast|Undead|Construct|Celestial|Elemental|Fey|Fiend|Giant|Humanoid|Ooze|Plant))', '', text)

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    top_info = []
    continuation = []
    spellcasting = []
    leg_actions = []
    stats = []
    traits = []
    actions = []
    reactions = []

    current_sec = "top"
    for l in lines:
        if l.startswith("Reactions; its Speed is halved"):
            current_sec = "continuation"
        elif l.startswith("Spellcasting.") or l.startswith("#### Spellcasting"):
            current_sec = "spellcasting"
        elif l.startswith("#### Legendary Actions") or l.startswith("Legendary Action Uses"):
            current_sec = "leg_actions"
        elif l.startswith("MOD SAVE") or l.startswith("MOD  SAVE") or re.search(r'\b(Srn|STR)\s+\d+', l):
            current_sec = "stats"
        elif l.startswith("#### Traits"):
            current_sec = "traits"
        elif l.startswith("#### Actions"):
            current_sec = "actions"
        elif l.startswith("#### Reactions"):
            current_sec = "reactions"

        if current_sec == "top":
            top_info.append(l)
        elif current_sec == "continuation":
            continuation.append(l)
        elif current_sec == "spellcasting":
            spellcasting.append(l)
        elif current_sec == "leg_actions":
            leg_actions.append(l)
        elif current_sec == "stats":
            stats.append(l)
        elif current_sec == "traits":
            traits.append(l)
        elif current_sec == "actions":
            actions.append(l)
        elif current_sec == "reactions":
            reactions.append(l)

    if continuation:
        actions.extend(continuation)

    ordered_sections = [
        top_info,
        stats,
        traits,
        actions,
        reactions,
        spellcasting,
        leg_actions
    ]

    all_lines = []
    for sec in ordered_sections:
        if sec:
            all_lines.extend(sec)
            all_lines.append("")

    blocks = []
    if lore:
        blocks.append(lore)

    cur_para = []
    in_actions_or_traits = False

    def flush():
        if cur_para:
            p_text = " ".join(cur_para).strip()
            p_text = re.sub(r'[ \t]+', ' ', p_text)
            if p_text:
                blocks.append(p_text)
            cur_para.clear()

    for l in all_lines:
        if not l:
            flush()
            continue
        if l.startswith("#### "):
            flush()
            blocks.append(l)
            in_actions_or_traits = True
            continue

        # Stats formatting
        if re.search(r'\b(Srn|STR)\s+\d+', l):
            flush()
            ab_clean = re.sub(r'\bSrn\b', 'FOR', l)
            ab_clean = re.sub(r'\b(Dex|Dzx|Drx|DEx)\b', 'DES', ab_clean)
            ab_clean = re.sub(r'\b(CoH|Cott|Cor\.r|Cor|CON)\b', 'COS', ab_clean)
            blocks.append(f"**Punteggi Caratteristica**: {ab_clean}")
            continue
        if re.search(r'\b(lr\.rr|lrr|lrur|ltlr|lnr|INT)\s+\d+', l):
            ab_clean = re.sub(r'\b(lr\.rr|lrr|lrur|ltlr|lnr|INT)\b', 'INT', l)
            ab_clean = re.sub(r'\b(Wrs|Wts|WIS)\b', 'SAG', ab_clean)
            ab_clean = re.sub(r'\b(Cxl|Cxr|CHA)\b', 'CAR', ab_clean)
            ab_clean = re.sub(r'\b(CoH|Cott|Cor\.r|Cor|CON)\b', 'COS', ab_clean)
            if blocks and blocks[-1].startswith("**Punteggi Caratteristica**:"):
                blocks[-1] += f" | {ab_clean}"
            else:
                blocks.append(f"**Punteggi Caratteristica**: {ab_clean}")
            continue
        if re.search(r'\b(CoH|Cott|Cor\.r|Cor|COS|CON)\s+\d+', l):
            ab_clean = re.sub(r'\b(CoH|Cott|Cor\.r|Cor|CON)\b', 'COS', l)
            ab_clean = re.sub(r'\b(Cxl|Cxr|CHA)\b', 'CAR', ab_clean)
            if blocks and blocks[-1].startswith("**Punteggi Caratteristica**:"):
                blocks[-1] += f" | {ab_clean}"
            else:
                blocks.append(f"**Punteggi Caratteristica**: {ab_clean}")
            continue
        if re.search(r'\b(Cxl|Cxr|CHA)\s+\d+', l):
            ab_clean = re.sub(r'\b(Cxl|Cxr|CHA)\b', 'CAR', l)
            if blocks and blocks[-1].startswith("**Punteggi Caratteristica**:"):
                blocks[-1] += f" | {ab_clean}"
            else:
                blocks.append(f"**Punteggi Caratteristica**: {ab_clean}")
            continue
        if l.startswith("MOD SAVE") or l.startswith("MOD  SAVE") or l in ["+3", "-3", "+4", "-4"]:
            continue

        # Inserisci newline prima di nuovi tratti o azioni
        l = re.sub(r'\.\s*(Acid\s+Breath|Slowing\s+Breath|Multiattack|Petrifying\s+Bite|Talons|Rend|Bite|Claw|Tail|Mind\s+Jolt|Pounce|Giggling\s+Magic|Magical\s+Backlash|Flyby)', r'.\n\1', l, flags=re.I)

        for sub_l in l.splitlines():
            sub_l = sub_l.strip()
            if not sub_l:
                continue
            if in_actions_or_traits:
                m = re.match(r'^([A-Z][a-zA-Z0-9\s\(\)\/\-\'\:\+]+?)\.\s+(.*)', sub_l)
                if m and len(m.group(1).split()) <= 6 and not m.group(1).startswith("####"):
                    name = m.group(1).strip()
                    desc = m.group(2).strip()
                    name_l = name.lower()
                    if not any(k in name_l for k in ["failure", "success", "hit", "at will", "d20 test", "mod save", "mod", "saving throw"]):
                        flush()
                        if name_l == "spellcasting":
                            blocks.append(f"#### Spellcasting\n{desc}")
                        else:
                            cur_para.append(f"• **{name}**: {desc}")
                        continue
            cur_para.append(sub_l)

    flush()
    return "\n\n".join(blocks)


def determine_category_and_keywords(title: str, path: str, manual_code: str) -> Tuple[str, List[str]]:
    t_lower = title.lower()
    p_lower = path.lower()
    keywords = [t_lower]
    
    # Includi sinonimi e traduzioni in italiano
    for en_key, it_list in ITALIAN_TRANSLATIONS.items():
        if en_key in t_lower:
            keywords.extend(it_list)
            
    # Classificazione automatica categoria coerente con l'app
    if "condition" in t_lower or any(c in t_lower for c in ["blinded", "charmed", "deafened", "frightened", "grappled", "incapacitated", "invisible", "paralyzed", "petrified", "poisoned", "prone", "restrained", "stunned", "unconscious", "exhaustion"]):
        cat = "Condizioni & Stati"
    elif "hazard" in t_lower or any(h in t_lower for h in ["burning", "falling", "suffocation", "dehydration", "malnutrition"]):
        cat = "Pericoli & Ambiente"
    elif "action" in t_lower or any(a in t_lower for a in ["attack", "dash", "disengage", "dodge", "help", "hide", "ready", "search"]):
        cat = "Combattimento & Azioni"
    elif "spell" in p_lower or "spell" in t_lower or t_lower.endswith("(r)"):
        cat = "Incantesimi"
    elif manual_code == "MM" or "stat block" in p_lower or "creature" in p_lower:
        cat = "Mostri & PNG"
    elif any(cl in t_lower for cl in ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard", "artificer", "path of", "circle of", "college of", "domain", "oath"]):
        cat = "Classi & Sottoclassi"
    elif "feat" in p_lower or "feat" in t_lower or "boon" in t_lower:
        cat = "Talenti"
    elif "equipment" in p_lower or "magic item" in p_lower or "weapon" in t_lower or "armor" in t_lower or "treasure" in p_lower:
        cat = "Equipaggiamento & Tesori"
    elif manual_code == "DMG" or "dungeon master" in p_lower or "adventure" in p_lower or "campaign" in p_lower or "bastion" in t_lower:
        cat = "Guida del DM & Strumenti"
    elif "travel" in t_lower or "exploration" in t_lower or "wilderness" in t_lower:
        cat = "Avventura & Viaggio"
    else:
        cat = "Regole Generali"
        
    return cat, list(set(keywords))


class PDFManualsIndexer:
    """
    Gestore dell'indice dei manuali PDF per l'intero applicativo.
    Controlla la validità della cache ed effettua il caricamento immediato o l'indicizzazione in background.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, pdf_dir: str = PDF_DIR, cache_file: str = CACHE_FILE):
        if self._initialized:
            return
        self.pdf_dir = pdf_dir
        self.cache_file = cache_file
        self.entries: List[Dict] = []
        self.metadata: Dict = {}
        self.is_indexing: bool = False
        self._load_cache_if_valid()
        self._initialized = True

    def get_pdf_files(self) -> List[str]:
        if not os.path.exists(self.pdf_dir):
            return []
        return [f for f in os.listdir(self.pdf_dir) if f.lower().endswith(".pdf")]

    def is_cache_valid(self) -> bool:
        if not os.path.exists(self.cache_file):
            return False
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_files = data.get("metadata", {}).get("files", {})
            current_files = self.get_pdf_files()
            if not current_files and not cached_files:
                return True
            for cf in current_files:
                if cf not in cached_files:
                    return False
                cpath = os.path.join(self.pdf_dir, cf)
                mtime = os.path.getmtime(cpath)
                size = os.path.getsize(cpath)
                if abs(cached_files[cf].get("mtime", 0) - mtime) > 2.0 or cached_files[cf].get("size", 0) != size:
                    return False
            return True
        except Exception:
            return False

    def _load_cache_if_valid(self) -> bool:
        if self.is_cache_valid():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.metadata = data.get("metadata", {})
                self.entries = data.get("entries", [])

                # Arricchimento trasparente in memoria per mostri indicizzati:
                # garantisce che attributes e statistiche siano sempre complete e accurate
                for e in self.entries:
                    if e.get("category") == "Mostri & PNG" or "monster_data" in e:
                        mdata = e.get("monster_data")
                        if not mdata or not isinstance(mdata, dict):
                            mdata = {}
                            e["monster_data"] = mdata
                        title = e.get("title", "")
                        cur_attrs = mdata.get("attributes")
                        if not cur_attrs or all(v == 10 for v in cur_attrs.values()):
                            mdata["attributes"] = extract_and_normalize_attributes(e.get("content", ""), title)
                        if mdata.get("ac", 10) == 10:
                            srd_rec = get_monster_offline(title)
                            if srd_rec and srd_rec.get("armor_class", 10) > 10:
                                mdata["ac"] = srd_rec["armor_class"]
                                if "summary" in e:
                                    e["summary"] = re.sub(r'CA\s+10\b', f'CA {mdata["ac"]}', e["summary"])

                print(f"[PDF_INDEXER] Caricate {len(self.entries)} voci da cache ({self.cache_file})")
                return True
            except Exception as e:
                print(f"[PDF_INDEXER] Errore lettura cache: {e}")
        return False

    def get_all_entries(self) -> List[Dict]:
        return list(self.entries)

    def get_monsters(self) -> List[Dict]:
        """Restituisce solo i mostri indicizzati con relative statistiche per il Bestiario del DM."""
        return [e for e in self.entries if e.get("category") == "Mostri & PNG" or "monster_data" in e]

    def build_index(self, progress_callback: Optional[Callable[[str, float], None]] = None) -> List[Dict]:
        """
        Indicizza completamente i PDF nella cartella 'manuals_pdf' e salva la cache JSON.
        Non blocca la CPU se eseguito in un thread secondario.
        """
        if not PYPDF_AVAILABLE:
            print("[PDF_INDEXER] Errore: pypdf non disponibile nel sistema.")
            return []

        self.is_indexing = True
        t_start = time.time()
        all_entries = []
        page_cache = {}

        def get_page_text(reader, page_idx):
            if page_idx < 0 or page_idx >= len(reader.pages):
                return ""
            key = (id(reader), page_idx)
            if key not in page_cache:
                try:
                    page_cache[key] = clean_text(reader.pages[page_idx].extract_text() or "")
                except Exception:
                    page_cache[key] = ""
            return page_cache[key]

        pdf_files = self.get_pdf_files()
        total_files = max(1, len(pdf_files))

        for f_idx, fname in enumerate(pdf_files):
            fpath = os.path.join(self.pdf_dir, fname)
            pct = (f_idx / total_files) * 100.0
            if progress_callback:
                progress_callback(f"Indicizzazione: {fname}...", pct)

            try:
                reader = PdfReader(fpath)
            except Exception as e:
                print(f"[PDF_INDEXER] Impossibile leggere {fname}: {e}")
                continue

            fname_lower = fname.lower()

            # -------------------------------------------------------------
            # 1. Player's Handbook (PHB 2024)
            # -------------------------------------------------------------
            if "player" in fname_lower or "phb" in fname_lower:
                def walk_outline(items, parent=""):
                    res = []
                    for it in items:
                        if isinstance(it, list):
                            res.extend(walk_outline(it, parent))
                        else:
                            t = getattr(it, 'title', '').strip()
                            try: p = reader.get_destination_page_number(it)
                            except Exception: p = None
                            path = f"{parent} > {t}" if parent else t
                            if t and p is not None:
                                res.append((t, path, p))
                    return res

                phb_items = walk_outline(reader.outline) if reader.outline else []
                for idx, (title, path, p_idx) in enumerate(phb_items):
                    if any(skip in title.lower() for skip in ["cover", "table of contents", "credits", "back cover"]):
                        continue
                    next_p = phb_items[idx + 1][2] if idx + 1 < len(phb_items) else p_idx + 1
                    max_read = min(p_idx + 2, next_p + 1 if next_p >= p_idx else p_idx + 2)

                    chunks = [get_page_text(reader, pi) for pi in range(p_idx, max_read) if get_page_text(reader, pi)]
                    full_txt = "\n\n".join(chunks)
                    if not full_txt:
                        continue

                    clean_body = format_clean_manual_text(full_txt, title)
                    if not clean_body:
                        continue

                    cat, kws = determine_category_and_keywords(title, path, "PHB")
                    summary = clean_body[:200].replace("\n", " ").strip() + "..."
                    entry_id = f"pdf_phb_{re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')}_{p_idx}"

                    all_entries.append({
                        "id": entry_id,
                        "manual": "PHB",
                        "manual_name": "Player's Handbook 2024 (PHB)",
                        "category": cat,
                        "title": title,
                        "keywords": kws,
                        "page_ref": f"PHB p. {p_idx + 1}",
                        "summary": summary,
                        "content": f"### {title} (PHB 2024 - Pag. {p_idx + 1})\n\n{clean_body[:4000]}",
                        "pdf_filename": fname,
                        "pdf_page": p_idx + 1
                    })

            # -------------------------------------------------------------
            # 2. Monster Manual (MM 2025)
            # -------------------------------------------------------------
            elif "monster" in fname_lower or "bestiary" in fname_lower:
                # Estrazione dal Sommario Monsters A to Z
                toc_text = ""
                for p_num in [4, 5, 6, 7]:
                    if p_num < len(reader.pages):
                        toc_text += "\n" + (reader.pages[p_num].extract_text() or "")

                mm_monsters_found = set()
                for line in toc_text.split("\n"):
                    line = line.strip()
                    m = re.search(r'([A-Za-z0-9\s\-\'\,\(\)]+?)[\.\s]{2,}(\d{1,3})\s*$', line)
                    if m:
                        raw_name = m.group(1).strip()
                        bpage = int(m.group(2))
                        if any(h in raw_name.lower() for h in ['contents', 'how to use', 'stat block', 'monsters a to', 'app.']):
                            continue
                        clean_mname = clean_ocr_name(raw_name)
                        mm_monsters_found.add(clean_mname.lower())

                        p_idx = bpage + 2  # Offset corretto Monster Manual: bpage + 2
                        if p_idx >= len(reader.pages):
                            continue

                        ptxt = get_page_text(reader, p_idx)
                        # Se su p_idx non ci sono AC o HP, controlla p_idx + 1 (es. Ancient Dragons o pagine lore)
                        if not re.search(r'\bAC\s+\d+', ptxt, re.I) and not re.search(r'\bHP\s*[\'\"`]?\s*[0-9lIsS]+', ptxt, re.I):
                            if p_idx + 1 < len(reader.pages):
                                next_check = get_page_text(reader, p_idx + 1)
                                if re.search(r'\bAC\s+\d+', next_check, re.I):
                                    p_idx = p_idx + 1
                                    ptxt = next_check

                        # Se ci sono più mostri su una pagina, isola la fetta corretta
                        slice_txt = slice_monster_on_page(ptxt, clean_mname)

                        # Estrai lore se presente
                        lore = find_monster_lore_snippet(reader, bpage, clean_mname)

                        clean_body = format_clean_monster_stat_block(slice_txt, clean_mname, lore)

                        ac_match = re.search(r'\bAC\s+([0-9lI]+)', slice_txt, re.IGNORECASE)
                        hp_match = re.search(r'\bHP\s*[\'\"`]?\s*([0-9lIsS]+)', slice_txt, re.IGNORECASE)
                        cr_match = re.search(r'\bCR\s+([0-9lI]+(?:/[0-9lI]+)?)', slice_txt, re.IGNORECASE)

                        ac_val = normalize_stat_number(ac_match.group(1) if ac_match else 10)
                        hp_val = normalize_stat_number(hp_match.group(1) if hp_match else 20)
                        cr_val = normalize_stat_number(cr_match.group(1) if cr_match else "1", is_cr=True)

                        attrs = extract_and_normalize_attributes(slice_txt, clean_mname)
                        if ac_val == 10:
                            srd_rec = get_monster_offline(clean_mname)
                            if srd_rec and srd_rec.get("armor_class", 10) > 10:
                                ac_val = srd_rec["armor_class"]

                        meta_parts = [f"CA {ac_val}", f"HP {hp_val}", f"CR {cr_val}"]
                        meta_str = " | ".join(meta_parts)

                        summary = f"{meta_str}. {clean_body[:180].replace(chr(10), ' ').strip()}..."
                        entry_id = f"pdf_mm_{re.sub(r'[^a-zA-Z0-9]+', '_', clean_mname.lower()).strip('_')}_{bpage}"

                        kws = [clean_mname.lower(), "mostro", "monster", "png", "npc"]
                        for en_key, it_list in ITALIAN_TRANSLATIONS.items():
                            if en_key in clean_mname.lower():
                                kws.extend(it_list)

                        stat_header = f"**Classe Armatura**: {ac_val} | **Punti Ferita**: {hp_val} | **Grado Sfida (CR)**: {cr_val}"

                        all_entries.append({
                            "id": entry_id,
                            "manual": "MM",
                            "manual_name": "Monster Manual (MM 2025)",
                            "category": "Mostri & PNG",
                            "title": clean_mname,
                            "keywords": list(set(kws)),
                            "page_ref": f"MM p. {bpage}",
                            "summary": summary,
                            "content": f"### {clean_mname} (Monster Manual - Pag. {bpage})\n\n{stat_header}\n\n{clean_body[:4000]}",
                            "pdf_filename": fname,
                            "pdf_page": p_idx + 1,
                            "monster_data": {
                                "name": clean_mname,
                                "ac": ac_val,
                                "hp": hp_val,
                                "cr": cr_val,
                                "attributes": attrs
                            }
                        })

                # Includi mostri iconici aggiuntivi se assenti
                for extra in ADDITIONAL_MM_ENTRIES:
                    if extra["name"].lower() not in mm_monsters_found:
                        p_idx = extra["page"] + 2
                        ptxt = get_page_text(reader, p_idx) if p_idx < len(reader.pages) else ""
                        raw_extra = ptxt if ptxt else extra["desc"]
                        clean_body = format_clean_monster_stat_block(raw_extra, extra["name"], extra["desc"])
                        extra_attrs = extract_and_normalize_attributes(raw_extra, extra["name"])
                        stat_header = f"**Classe Armatura**: {extra['ac']} | **Punti Ferita**: {extra['hp']} | **Grado Sfida (CR)**: {extra['cr']}"
                        all_entries.append({
                            "id": f"pdf_mm_{extra['name'].lower()}_{extra['page']}",
                            "manual": "MM",
                            "manual_name": "Monster Manual (MM 2025)",
                            "category": "Mostri & PNG",
                            "title": extra["name"],
                            "keywords": [extra["name"].lower(), "mostro", "monster"],
                            "page_ref": f"MM p. {extra['page']}",
                            "summary": f"CA {extra['ac']} | HP {extra['hp']} | CR {extra['cr']}. {extra['desc']}",
                            "content": f"### {extra['name']} (Monster Manual - Pag. {extra['page']})\n\n{stat_header}\n\n{clean_body[:4000]}",
                            "pdf_filename": fname,
                            "pdf_page": p_idx + 1,
                            "monster_data": {
                                "name": extra["name"],
                                "ac": extra["ac"],
                                "hp": extra["hp"],
                                "cr": extra["cr"],
                                "attributes": extra_attrs
                            }
                        })

            # -------------------------------------------------------------
            # 3. Tasha's Cauldron of Everything (TCoE)
            # -------------------------------------------------------------
            elif "tasha" in fname_lower or "tcoe" in fname_lower:
                def walk_outline_generic(items, parent=""):
                    res = []
                    for it in items:
                        if isinstance(it, list): res.extend(walk_outline_generic(it, parent))
                        else:
                            t = getattr(it, 'title', '').strip()
                            try: p = reader.get_destination_page_number(it)
                            except Exception: p = None
                            path = f"{parent} > {t}" if parent else t
                            if t and p is not None:
                                res.append((t, path, p))
                    return res

                tce_items = walk_outline_generic(reader.outline) if reader.outline else []
                for idx, (title, path, p_idx) in enumerate(tce_items):
                    if any(skip in title.lower() for skip in ["cover", "contents", "credits", "back cover"]):
                        continue
                    next_p = tce_items[idx + 1][2] if idx + 1 < len(tce_items) else p_idx + 2
                    max_read = min(p_idx + 3, next_p + 1 if next_p >= p_idx else p_idx + 2)

                    chunks = [get_page_text(reader, pi) for pi in range(p_idx, max_read) if get_page_text(reader, pi)]
                    full_txt = "\n\n".join(chunks)
                    if not full_txt: continue

                    clean_body = format_clean_manual_text(full_txt, title)
                    if not clean_body: continue

                    cat, kws = determine_category_and_keywords(title, path, "TCoE")
                    summary = clean_body[:200].replace("\n", " ").strip() + "..."
                    entry_id = f"pdf_tcoe_{re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')}_{p_idx}"

                    all_entries.append({
                        "id": entry_id,
                        "manual": "TCoE",
                        "manual_name": "Tasha's Cauldron of Everything (TCoE)",
                        "category": cat,
                        "title": title,
                        "keywords": kws,
                        "page_ref": f"TCoE p. {p_idx + 1}",
                        "summary": summary,
                        "content": f"### {title} (TCoE - Pag. {p_idx + 1})\n\n{clean_body[:4000]}",
                        "pdf_filename": fname,
                        "pdf_page": p_idx + 1
                    })

            # -------------------------------------------------------------
            # 4. Xanathar's Guide to Everything (XGtE)
            # -------------------------------------------------------------
            elif "xanathar" in fname_lower or "xgte" in fname_lower:
                def walk_outline_generic(items, parent=""):
                    res = []
                    for it in items:
                        if isinstance(it, list): res.extend(walk_outline_generic(it, parent))
                        else:
                            t = getattr(it, 'title', '').strip()
                            try: p = reader.get_destination_page_number(it)
                            except Exception: p = None
                            path = f"{parent} > {t}" if parent else t
                            if t and p is not None:
                                res.append((t, path, p))
                    return res

                xge_items = walk_outline_generic(reader.outline) if reader.outline else []
                for idx, (title, path, p_idx) in enumerate(xge_items):
                    if any(skip in title.lower() for skip in ["cover", "contents", "credits", "back cover"]):
                        continue
                    next_p = xge_items[idx + 1][2] if idx + 1 < len(xge_items) else p_idx + 2
                    max_read = min(p_idx + 3, next_p + 1 if next_p >= p_idx else p_idx + 2)

                    chunks = [get_page_text(reader, pi) for pi in range(p_idx, max_read) if get_page_text(reader, pi)]
                    full_txt = "\n\n".join(chunks)
                    if not full_txt: continue

                    clean_body = format_clean_manual_text(full_txt, title)
                    if not clean_body: continue

                    cat, kws = determine_category_and_keywords(title, path, "XGtE")
                    summary = clean_body[:200].replace("\n", " ").strip() + "..."
                    entry_id = f"pdf_xgte_{re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')}_{p_idx}"

                    all_entries.append({
                        "id": entry_id,
                        "manual": "XGtE",
                        "manual_name": "Xanathar's Guide to Everything (XGtE)",
                        "category": cat,
                        "title": title,
                        "keywords": kws,
                        "page_ref": f"XGtE p. {p_idx + 1}",
                        "summary": summary,
                        "content": f"### {title} (XGtE - Pag. {p_idx + 1})\n\n{clean_body[:4000]}",
                        "pdf_filename": fname,
                        "pdf_page": p_idx + 1
                    })

            # -------------------------------------------------------------
            # 5. Dungeon Master's Guide (DMG 2024)
            # -------------------------------------------------------------
            elif "master" in fname_lower or "dmg" in fname_lower:
                dmg_sections = [
                    ("Running Combat", 13, "Combattimento & Azioni"),
                    ("Traps & Hazards", 21, "Guida del DM & Strumenti"),
                    ("Resolving Outcomes", 30, "Regole Generali"),
                    ("Difficulty Class (DC)", 32, "Regole Generali"),
                    ("Advantage & Disadvantage", 33, "Regole Generali"),
                    ("Social Interaction & NPC Attitudes", 35, "Regole Generali"),
                    ("Exploration & Travel", 37, "Avventura & Viaggio"),
                    ("Environmental Effects", 41, "Pericoli & Ambiente"),
                    ("Hazards", 51, "Pericoli & Ambiente"),
                    ("Creating a Creature", 59, "Guida del DM & Strumenti"),
                    ("Creating Magic Items", 70, "Equipaggiamento & Tesori"),
                    ("Creating Spells", 75, "Guida del DM & Strumenti"),
                    ("Creating Adventures & Encounters", 95, "Guida del DM & Strumenti"),
                    ("Creating Campaigns", 140, "Guida del DM & Strumenti"),
                    ("Cosmology & The Planes", 180, "Guida del DM & Strumenti"),
                    ("Treasure Themes & Magic Items", 220, "Equipaggiamento & Tesori"),
                    ("Bastions & Facilities", 337, "Guida del DM & Strumenti"),
                    ("Lore Glossary", 366, "Regole Generali"),
                ]
                for title, p_idx, cat in dmg_sections:
                    chunks = [get_page_text(reader, pi) for pi in range(p_idx, min(p_idx + 3, len(reader.pages))) if get_page_text(reader, pi)]
                    full_txt = "\n\n".join(chunks)
                    if not full_txt: continue

                    clean_body = format_clean_manual_text(full_txt, title)
                    if not clean_body: continue

                    kws = [title.lower(), "dmg", "master", "regole", "guida"]
                    for en_key, it_list in ITALIAN_TRANSLATIONS.items():
                        if en_key in title.lower():
                            kws.extend(it_list)

                    summary = clean_body[:200].replace("\n", " ").strip() + "..."
                    entry_id = f"pdf_dmg_{re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')}_{p_idx}"

                    all_entries.append({
                        "id": entry_id,
                        "manual": "DMG",
                        "manual_name": "Dungeon Master's Guide 2024 (DMG)",
                        "category": cat,
                        "title": title,
                        "keywords": list(set(kws)),
                        "page_ref": f"DMG p. {p_idx + 1}",
                        "summary": summary,
                        "content": f"### {title} (DMG 2024 - Pag. {p_idx + 1})\n\n{clean_body[:4000]}",
                        "pdf_filename": fname,
                        "pdf_page": p_idx + 1
                    })

        # Salvataggio Cache
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        self.metadata = {
            "version": "1.0",
            "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_entries": len(all_entries),
            "files": {
                fname: {
                    "mtime": os.path.getmtime(os.path.join(self.pdf_dir, fname)),
                    "size": os.path.getsize(os.path.join(self.pdf_dir, fname))
                }
                for fname in pdf_files
            }
        }
        cache_data = {
            "metadata": self.metadata,
            "entries": all_entries
        }
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        self.entries = all_entries
        self.is_indexing = False
        elapsed = round(time.time() - t_start, 2)
        print(f"[PDF_INDEXER] Indicizzazione completata con successo: {len(all_entries)} voci in {elapsed}s.")
        if progress_callback:
            progress_callback("Indicizzazione completata!", 100.0)
        return self.entries

    def reindex_async(self, on_done_callback: Optional[Callable[[int], None]] = None):
        """Avvia l'indicizzazione in un thread separato senza bloccare la GUI."""
        def _run():
            entries = self.build_index()
            if on_done_callback:
                on_done_callback(len(entries))

        th = threading.Thread(target=_run, daemon=True)
        th.start()
        return th

