# campaign.py
"""
Modulo per la gestione e persistenza delle Campagne preparate per D&D OmniCompanion.
Una campagna organizza metadati, mappe/scene, incontri preparati, quest, PNG e handouts.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional
from common.file_utils import safe_write_json

DEFAULT_CAMPAIGNS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "campaigns"))

def slugify(text: str) -> str:
    """Converte un titolo in una stringa adatta a un nome di cartella."""
    s = text.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_-]+', '_', s)
    return s or "campagna"

class Campaign:
    def __init__(self, name: str = "Nuova Campagna", folder_path: Optional[str] = None):
        self.name = name
        self.folder_path = folder_path
        self.description = ""
        self.level_range = "1-3"
        self.dm_notes = ""
        
        # Calendario & Meteo di partenza
        self.start_date = {
            "year": 1492,
            "month": 1,
            "day": 1,
            "hour": 8
        }
        self.start_weather = "Sereno"
        
        # Equipaggiamento di partenza
        self.starter_kit: List[Dict[str, Any]] = []
        
        # Mappa / Scena iniziale
        self.starting_map_file: Optional[str] = None
        
        # Scene collegate (nome visuale, percorso relativo mappa, descrizione)
        self.scenes: List[Dict[str, Any]] = []
        
        # Incontri preparati
        self.encounters: List[Dict[str, Any]] = []
        
        # Registro Quest
        self.quests: List[Dict[str, Any]] = []
        
        # PNG della campagna
        self.npcs: List[Dict[str, Any]] = []
        
        # Negozi preparati
        self.shops: Dict[str, Any] = {}
        
        # Handouts (lettere, indizi, mappe segrete)
        self.handouts: List[Dict[str, Any]] = []

        # Flow Builder & DndScript (Campaign-as-Code)
        self.flow_script: str = ""
        self.flow_graph: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "level_range": self.level_range,
            "dm_notes": self.dm_notes,
            "start_date": self.start_date,
            "start_weather": self.start_weather,
            "starter_kit": self.starter_kit,
            "starting_map_file": self.starting_map_file,
            "scenes": self.scenes,
            "encounters": self.encounters,
            "quests": self.quests,
            "npcs": self.npcs,
            "shops": self.shops,
            "handouts": self.handouts,
            "flow_script": self.flow_script,
            "flow_graph": self.flow_graph,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], folder_path: Optional[str] = None) -> "Campaign":
        c = cls(name=data.get("name", "Campagna Senza Nome"), folder_path=folder_path)
        c.description = data.get("description", "")
        c.level_range = data.get("level_range", "1-3")
        c.dm_notes = data.get("dm_notes", "")
        c.start_date = data.get("start_date", {"year": 1492, "month": 1, "day": 1, "hour": 8})
        c.start_weather = data.get("start_weather", "Sereno")
        c.starter_kit = data.get("starter_kit", [])
        c.starting_map_file = data.get("starting_map_file")
        c.scenes = data.get("scenes", [])
        c.encounters = data.get("encounters", [])
        c.quests = data.get("quests", [])
        c.npcs = data.get("npcs", [])
        c.shops = data.get("shops", {})
        c.handouts = data.get("handouts", [])
        c.flow_script = data.get("flow_script", "")
        c.flow_graph = data.get("flow_graph", {})
        return c

    def save(self, target_folder: Optional[str] = None) -> str:
        """Salva la campagna nella cartella specificata o nella cartella corrente."""
        if target_folder:
            self.folder_path = target_folder
        if not self.folder_path:
            slug = slugify(self.name)
            self.folder_path = os.path.join(DEFAULT_CAMPAIGNS_DIR, slug)
            
        os.makedirs(self.folder_path, exist_ok=True)
        manifest_file = os.path.join(self.folder_path, "campaign.json")
        safe_write_json(manifest_file, self.to_dict())
        return self.folder_path

    @classmethod
    def load(cls, folder_path: str) -> "Campaign":
        """Carica una campagna da una cartella o file campaign.json."""
        if os.path.isfile(folder_path):
            manifest_file = folder_path
            folder_path = os.path.dirname(manifest_file)
        else:
            manifest_file = os.path.join(folder_path, "campaign.json")
            
        if not os.path.exists(manifest_file):
            raise FileNotFoundError(f"Manifest di campagna non trovato: {manifest_file}")
            
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return cls.from_dict(data, folder_path=folder_path)

    def apply_to_game_state(self, game_state: Any) -> None:
        """Applica la configurazione della campagna a un GameState di gioco."""
        with game_state.lock:
            # Starter kit campagna
            if self.starter_kit:
                game_state.campaign_starter_kit = [item.copy() for item in self.starter_kit]
                
            # Calendario & Meteo
            if self.start_date:
                game_state.time_year = self.start_date.get("year", 1492)
                game_state.time_month = self.start_date.get("month", 1)
                game_state.time_day = self.start_date.get("day", 1)
                game_state.time_hour = self.start_date.get("hour", 8)
            if self.start_weather:
                game_state.weather = self.start_weather
                
            # Quest & Negozi
            if self.quests:
                game_state.quests = [q.copy() for q in self.quests]
            if self.shops:
                game_state.shops = {k: v.copy() for k, v in self.shops.items()}
                
            # Referenza alla campagna attiva
            game_state.active_campaign = self
            
            # Caricamento eventuale mappa iniziale
            if self.starting_map_file:
                map_path = self.starting_map_file
                if not os.path.isabs(map_path) and self.folder_path:
                    cand = os.path.join(self.folder_path, map_path)
                    if os.path.exists(cand):
                        map_path = cand
                if not os.path.exists(map_path):
                    # Prova nella cartella maps/ globale
                    cand_global = os.path.join(os.path.dirname(os.path.dirname(__file__)), "maps", os.path.basename(self.starting_map_file))
                    if os.path.exists(cand_global):
                        map_path = cand_global
                if os.path.exists(map_path):
                    try:
                        import base64
                        with open(map_path, "r", encoding="utf-8") as mf:
                            map_data = json.load(mf)
                        if 'base_image_path' in map_data and map_data['base_image_path']:
                            img_path = map_data['base_image_path']
                            if not os.path.isabs(img_path):
                                img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_path)
                            if os.path.exists(img_path):
                                with open(img_path, "rb") as image_file:
                                    map_data['bg_image_data'] = base64.b64encode(image_file.read()).decode('utf-8')
                        game_state.load_map(map_data)
                    except Exception as e:
                        print(f"[CAMPAIGN] Errore caricamento mappa iniziale {map_path}: {e}")
                        
        game_state._trigger_gui_update()

    def add_scene(self, name: str, map_file: str, description: str = "") -> None:
        self.scenes.append({
            "name": name,
            "map_file": map_file,
            "description": description
        })
        if not self.starting_map_file:
            self.starting_map_file = map_file

    def add_encounter(self, name: str, monsters: List[Dict[str, Any]], description: str = "", act: str = "Atto 1") -> None:
        self.encounters.append({
            "name": name,
            "act": act,
            "description": description,
            "monsters": monsters
        })

    def add_quest(self, title: str, description: str = "", chapter: str = "Capitolo 1", rewards: Optional[Dict[str, Any]] = None) -> None:
        self.quests.append({
            "title": title,
            "description": description,
            "chapter": chapter,
            "rewards": rewards or {"xp": 100, "gp": 25},
            "completed": False
        })

    def add_npc(self, name: str, role: str, hp: int = 20, ac: int = 12, notes: str = "", faction: str = "Neutrale") -> None:
        self.npcs.append({
            "name": name,
            "role": role,
            "hp": hp,
            "ac": ac,
            "faction": faction,
            "notes": notes
        })

    def add_handout(self, title: str, content: str = "", image_path: str = "") -> None:
        self.handouts.append({
            "title": title,
            "content": content,
            "image_path": image_path
        })


def create_sample_starter_campaign(target_dir: Optional[str] = None) -> Campaign:
    """Crea una campagna dimostrativa 'La Cripta dei Sussurri' pronta all'uso."""
    camp = Campaign(
        name="La Cripta dei Sussurri",
        folder_path=target_dir or os.path.join(DEFAULT_CAMPAIGNS_DIR, "la_cripta_dei_sussurri")
    )
    camp.level_range = "1-3"
    camp.description = (
        "Gli abitanti del villaggio di Rovescuro lamentano sinistri lamenti notturni "
        "provenienti dalle catacombe dimenticate sotto la collina. Il borgo ha promesso "
        "una ricca ricompensa a chi scoprirà l'origine del male e purificherà il santuario."
    )
    camp.dm_notes = (
        "SEGRETI DEL DM:\n"
        "1. I sussurri sono causati da uno spettro evocato da un cultista nascosto.\n"
        "2. Padre Lucian conosce il passato della cripta ma nasconde una chiave sacra.\n"
        "3. Nella sala est c'è una trappola a pressione: DC 13 Percezione per notarla."
    )
    camp.start_weather = "Nebbia"
    camp.start_date = {"year": 1492, "month": 10, "day": 13, "hour": 20}
    
    # Starter Kit Campagna
    camp.starter_kit = [
        {"name": "Torcia", "type": "Equipaggiamento", "qty": 3, "weight": 1.0, "desc": "Luce brillante raggio 20ft."},
        {"name": "Pozione di Cura", "type": "Consumabile", "qty": 1, "weight": 0.5, "desc": "Cura 2d4 + 2 HP."},
        {"name": "Razione da Viaggio", "type": "Consumabile", "qty": 5, "weight": 2.0, "desc": "Sostentamento per un giorno."},
        {"name": "Corda di Canapa (15m)", "type": "Equipaggiamento", "qty": 1, "weight": 10.0, "desc": "Resistente fino a 150kg."}
    ]
    
    # Scene
    camp.add_scene(
        name="Piazza di Rovescuro", 
        map_file="maps/faerun.json", 
        description="Il piccolo villaggio avvolto da una nebbia fitta e gelida."
    )
    camp.add_scene(
        name="Ingresso Catacombe", 
        map_file="maps/faerun.json", 
        description="Una pesante grata in ferro divelta che scende nell'oscurità."
    )
    
    # Incontri preparati
    camp.add_encounter(
        name="Pattuglia di Scheletri all'Ingresso",
        act="Atto 1 - La Discesa",
        description="3 Scheletri armati di archi corti nascosti dietro le colonne.",
        monsters=[
            {"name": "Scheletro Arciere", "count": 2, "hp": 13, "initiative": 2, "xp": 50},
            {"name": "Scheletro Guerriero", "count": 1, "hp": 15, "initiative": 2, "xp": 50}
        ]
    )
    camp.add_encounter(
        name="Lo Spettro dei Sussurri (Boss)",
        act="Atto 2 - Il Santuario Violato",
        description="Lo spirito inquieto di Lord Malakor che infesta l'altare.",
        monsters=[
            {"name": "Spettro dei Sussurri", "count": 1, "hp": 32, "initiative": 3, "xp": 200},
            {"name": "Teschio Fiammeggiante", "count": 1, "hp": 18, "initiative": 3, "xp": 100}
        ]
    )
    
    # Missioni
    camp.add_quest(
        title="L'Indagine di Rovescuro",
        description="Parla con Padre Lucian per scoprire da dove provengono i rumori notturni.",
        chapter="Atto 1",
        rewards={"xp": 150, "gp": 30}
    )
    camp.add_quest(
        title="Purifica l'Altare Sconsacrato",
        description="Sconfiggi lo Spettro e spezza la maledizione che infesta le catacombe.",
        chapter="Atto 2",
        rewards={"xp": 400, "gp": 100}
    )
    
    # PNG
    camp.add_npc(
        name="Padre Lucian",
        role="Sacerdote del villaggio",
        faction="Alleato",
        hp=18,
        ac=13,
        notes="Uomo devoto e timoroso. Consegnerà una pozione di cura se convinto con DC 12 Persuasione."
    )
    camp.add_npc(
        name="Krag l'Oscuro",
        role="Cultista rinnegato",
        faction="Nemico",
        hp=24,
        ac=12,
        notes="Fugge nelle ombre non appena la battaglia volge a suo sfavore."
    )
    
    # Handouts
    camp.add_handout(
        title="Pergamena Strappata di Lord Malakor",
        content=(
            "'...e quando il sangue toccherà la pietra di luna, la soglia tra i mondi si aprirà.\n"
            "Nessun mortale potrà arrestare la vendetta dei caduti...'\n"
            "(Trascrizione trovata accanto a uno scheletro)"
        )
    )
    
    camp.save()
    return camp


def get_available_campaigns(campaigns_dir: str = DEFAULT_CAMPAIGNS_DIR) -> List[Dict[str, Any]]:
    """Restituisce un elenco sintetico delle campagne disponibili su disco. Crea quella di default se non ve ne sono."""
    if not os.path.exists(campaigns_dir):
        os.makedirs(campaigns_dir, exist_ok=True)
        
    result = []
    for item in os.listdir(campaigns_dir):
        subpath = os.path.join(campaigns_dir, item)
        manifest = os.path.join(subpath, "campaign.json")
        if os.path.isdir(subpath) and os.path.exists(manifest):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result.append({
                    "name": data.get("name", item),
                    "description": data.get("description", ""),
                    "level_range": data.get("level_range", "1-3"),
                    "scenes_count": len(data.get("scenes", [])),
                    "encounters_count": len(data.get("encounters", [])),
                    "quests_count": len(data.get("quests", [])),
                    "folder_path": subpath,
                    "manifest_path": manifest
                })
            except Exception as e:
                print(f"[CAMPAIGN] Errore lettura campagna in {subpath}: {e}")
                
    if not result:
        # Crea la campagna dimostrativa automatica
        try:
            sample = create_sample_starter_campaign(os.path.join(campaigns_dir, "la_cripta_dei_sussurri"))
            result.append({
                "name": sample.name,
                "description": sample.description,
                "level_range": sample.level_range,
                "scenes_count": len(sample.scenes),
                "encounters_count": len(sample.encounters),
                "quests_count": len(sample.quests),
                "folder_path": sample.folder_path,
                "manifest_path": os.path.join(sample.folder_path, "campaign.json")
            })
        except Exception as e:
            print(f"[CAMPAIGN] Errore creazione campagna starter: {e}")
            
    return sorted(result, key=lambda x: x["name"])

