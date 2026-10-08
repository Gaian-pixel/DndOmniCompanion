import json
import os

class CompendiumManager:
    def __init__(self):
        self.data_file = os.path.join(os.path.dirname(__file__), "..", "srd_data", "custom_compendium.json")
        self.data = {
            "Mostri": [],
            "Armi": [],
            "Pozioni": [],
            "Equipaggiamento": [],
            "Oggetti Magici": [],
            "Incantesimi": [],
            "Regole": [],
            "Classi": [],
            "Tratti": []
        }
        self.load()

    def load(self):
        # Assicurati che la cartella esista
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for k, v in loaded.items():
                        if k in self.data:
                            self.data[k] = v
                        else:
                            self.data[k] = v
            except Exception as e:
                print(f"Errore nel caricamento del compendio custom: {e}")

    def save(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Errore nel salvataggio del compendio custom: {e}")

    def get_items(self, category):
        return self.data.get(category, [])

    def add_item(self, category, item_data):
        if category not in self.data:
            self.data[category] = []
        # Aggiungi un flag per distinguerli negli elenchi
        item_data["is_custom"] = True
        self.data[category].append(item_data)
        self.save()

    def remove_item(self, category, item_name):
        if category in self.data:
            self.data[category] = [i for i in self.data[category] if i.get("name") != item_name]
            self.save()

