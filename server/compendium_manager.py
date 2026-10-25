import json
import os
from typing import Dict, Any, List, Optional

class CompendiumManager:
    def __init__(self):
        self.data_file = os.path.join(os.path.dirname(__file__), "..", "srd_data", "custom_compendium.json")
        self.data: Dict[str, List[Dict[str, Any]]] = {
            "Mostri": [],
            "PNG": [],
            "Armi": [],
            "Pozioni": [],
            "Equipaggiamento": [],
            "Oggetti Magici": [],
            "Incantesimi": [],
            "Regole": [],
            "Classi": [],
            "Sottoclassi": [],
            "Razze": [],
            "Tratti": [],
            "Talenti": [],
            "Background": []
        }
        self.favorites: List[Dict[str, Any]] = []
        self.recent: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        # Assicurati che la cartella esista
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for k, v in loaded.items():
                        if k == "_favorites" and isinstance(v, list):
                            self.favorites = v
                        elif k == "_recent" and isinstance(v, list):
                            self.recent = v
                        elif isinstance(v, list):
                            self.data[k] = v
            except Exception as e:
                print(f"Errore nel caricamento del compendio custom: {e}")

    def save(self):
        try:
            payload = dict(self.data)
            payload["_favorites"] = self.favorites
            payload["_recent"] = self.recent[:25]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Errore nel salvataggio del compendio custom: {e}")

    def get_items(self, category: str) -> List[Dict[str, Any]]:
        return self.data.get(category, [])

    def add_item(self, category: str, item_data: Dict[str, Any]):
        if category not in self.data:
            self.data[category] = []
        item_data["is_custom"] = True
        item_data.setdefault("category", category)
        # Se esiste già con lo stesso nome, aggiorna invece di duplicare
        name = (item_data.get("name") or item_data.get("title") or "").strip()
        for idx, existing in enumerate(self.data[category]):
            if (existing.get("name") or existing.get("title") or "").strip().lower() == name.lower():
                self.data[category][idx] = item_data
                self.save()
                return
        self.data[category].append(item_data)
        self.save()

    def update_item(self, category: str, old_name: str, new_item_data: Dict[str, Any]) -> bool:
        """Modifica un elemento custom esistente preservandone la posizione."""
        new_item_data["is_custom"] = True
        new_item_data.setdefault("category", category)
        target_cats = [category] if category in self.data else list(self.data.keys())
        for cat in target_cats:
            items = self.data.get(cat, [])
            for idx, it in enumerate(items):
                it_name = (it.get("name") or it.get("title") or "").strip()
                if it_name.lower() == old_name.strip().lower():
                    items[idx] = new_item_data
                    self.save()
                    return True
        self.add_item(category if category in self.data else "Mostri", new_item_data)
        return True

    def remove_item(self, category: str, item_name: str) -> bool:
        removed = False
        target_cats = [category] if category in self.data else list(self.data.keys())
        for cat in target_cats:
            before = len(self.data.get(cat, []))
            self.data[cat] = [
                i for i in self.data.get(cat, [])
                if (i.get("name") or i.get("title") or "").strip().lower() != item_name.strip().lower()
            ]
            if len(self.data[cat]) < before:
                removed = True
        if removed:
            self.save()
        return removed

    # -------------------------------------------------------------------------
    # SEGNALIBRI / PREFERITI (⭐) & CRONOLOGIA RECENTI (🕒)
    # -------------------------------------------------------------------------
    @staticmethod
    def _item_key(item: Dict[str, Any]) -> str:
        return str(item.get("name") or item.get("title") or "").strip().lower()

    def is_favorite(self, item: Dict[str, Any]) -> bool:
        if not isinstance(item, dict):
            return False
        key = self._item_key(item)
        return bool(key) and any(self._item_key(f) == key for f in self.favorites)

    def toggle_favorite(self, item: Dict[str, Any], category: str = "") -> bool:
        """Aggiunge o rimuove un elemento dai preferiti. Restituisce True se ora è preferito."""
        if not isinstance(item, dict):
            return False
        key = self._item_key(item)
        if not key:
            return False
        if self.is_favorite(item):
            self.favorites = [f for f in self.favorites if self._item_key(f) != key]
            self.save()
            return False
        fav_copy = dict(item)
        if category and not fav_copy.get("category"):
            fav_copy["category"] = category
        self.favorites.insert(0, fav_copy)
        self.save()
        return True

    def get_favorites(self, monsters_only: bool = False) -> List[Dict[str, Any]]:
        if not monsters_only:
            return list(self.favorites)
        out = []
        for f in self.favorites:
            cat = str(f.get("category", "")).lower()
            if "mostr" in cat or "png" in cat or "npc" in cat or "monster_data" in f or "armor_class" in f or "ac" in f:
                out.append(f)
        return out

    def add_recent(self, item: Dict[str, Any], category: str = ""):
        if not isinstance(item, dict):
            return
        key = self._item_key(item)
        if not key:
            return
        self.recent = [r for r in self.recent if self._item_key(r) != key]
        rec_copy = dict(item)
        if category and not rec_copy.get("category"):
            rec_copy["category"] = category
        self.recent.insert(0, rec_copy)
        self.recent = self.recent[:25]
        self.save()

    def get_recent(self, monsters_only: bool = False) -> List[Dict[str, Any]]:
        if not monsters_only:
            return list(self.recent)
        out = []
        for r in self.recent:
            cat = str(r.get("category", "")).lower()
            if "mostr" in cat or "png" in cat or "npc" in cat or "monster_data" in r or "armor_class" in r or "ac" in r:
                out.append(r)
        return out


