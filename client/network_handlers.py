"""ClientGUI network message handlers, audio downloads, and asset cache mixin."""

from io import BytesIO
import base64
import os
import re
import sys
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from common.i18n import _t
from common.messagebox import messagebox
from common.protocol import make_update_full_sheet_request
from common.theme import apply_modern_window_style, ACCENT_GOLD

_ORIG_TIME_MONOTONIC = time.monotonic


def _monotonic_now() -> float:
    """Return monotonic time, honoring unittest.mock patches on client.client.time.monotonic."""
    client_mod = sys.modules.get("client.client")
    if client_mod is not None:
        client_time = getattr(client_mod, "time", None)
        if client_time is not None and client_time.monotonic is not _ORIG_TIME_MONOTONIC:
            return client_time.monotonic()
    return time.monotonic()


class ClientNetworkHandlersMixin:
    """Mixin encapsulating server message handlers, audio track streaming, and asset cache lookup."""

    _MAX_ASSET_CACHE_ENTRIES = 32

    def _get_asset_cache(self) -> dict:
        cache = getattr(self, "_asset_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            try:
                self._asset_cache = cache
            except Exception:
                pass
        return cache

    def _store_asset_in_cache(self, asset_hash: str, b64_data: str):
        if not asset_hash or not isinstance(b64_data, str) or not b64_data:
            return
        cache = ClientNetworkHandlersMixin._get_asset_cache(self)
        raw_cap = getattr(self, "_MAX_ASSET_CACHE_ENTRIES", 32)
        max_entries = raw_cap if isinstance(raw_cap, int) and raw_cap > 0 else 32
        if asset_hash in cache:
            cache.pop(asset_hash, None)
        else:
            while len(cache) >= max_entries:
                oldest_key = next(iter(cache), None)
                if oldest_key is None:
                    break
                cache.pop(oldest_key, None)
        cache[asset_hash] = b64_data

    def _resolve_cached_map_assets(self, map_data):
        if not isinstance(map_data, dict):
            return map_data
        from common.network_utils import compute_asset_hash
        cache = ClientNetworkHandlersMixin._get_asset_cache(self)
        bg_data = map_data.get("bg_image_data")
        bg_hash = map_data.get("bg_image_hash")
        if isinstance(bg_data, str) and bg_data:
            eff_hash = compute_asset_hash(bg_data)
            ClientNetworkHandlersMixin._store_asset_in_cache(self, eff_hash, bg_data)
            map_data["bg_image_hash"] = eff_hash
            map_data.pop("bg_image_cached", None)
        elif isinstance(bg_hash, str) and bg_hash:
            if bg_hash in cache:
                cached_b64 = cache.pop(bg_hash)
                cache[bg_hash] = cached_b64
                map_data["bg_image_data"] = cached_b64
                map_data.pop("bg_image_cached", None)
            else:
                local_map = getattr(self, "local_map_data", None)
                if isinstance(local_map, dict) and local_map.get("bg_image_hash") == bg_hash:
                    fallback_b64 = local_map.get("bg_image_data")
                    if isinstance(fallback_b64, str) and fallback_b64:
                        ClientNetworkHandlersMixin._store_asset_in_cache(self, bg_hash, fallback_b64)
                        map_data["bg_image_data"] = fallback_b64
                        map_data.pop("bg_image_cached", None)
        return map_data

    def _resolve_cached_handout_assets(self, handouts_or_data):
        from common.network_utils import compute_asset_hash
        cache = ClientNetworkHandlersMixin._get_asset_cache(self)
        items = handouts_or_data if isinstance(handouts_or_data, list) else [handouts_or_data]
        for item in items:
            if not isinstance(item, dict):
                continue
            img_b64 = item.get("image_b64")
            img_hash = item.get("image_hash")
            if isinstance(img_b64, str) and img_b64:
                eff_hash = compute_asset_hash(img_b64)
                ClientNetworkHandlersMixin._store_asset_in_cache(self, eff_hash, img_b64)
                item["image_hash"] = eff_hash
                item.pop("image_cached", None)
            elif isinstance(img_hash, str) and img_hash and img_hash in cache:
                cached_b64 = cache.pop(img_hash)
                cache[img_hash] = cached_b64
                item["image_b64"] = cached_b64
                item.pop("image_cached", None)
        return handouts_or_data


    def handle_handout_broadcast(self, data):
        if isinstance(data, dict):
            ClientNetworkHandlersMixin._resolve_cached_handout_assets(self, data)
        title = data.get("title", "Documento Condiviso")
        content = data.get("content", "")
        img_b64 = data.get("image_b64")

        self.show_toast(f"Il Dungeon Master ha condiviso: '{title}'", title="📜 Nuovo Documento", toast_type="gold")
        self.log_to_chat(f"📜 [DOCUMENTO DM] '{title}' condiviso con il party.", "Globale", color="#E5A50A")

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.title(f"📜 {title}")
        win.minsize(480, 420)
        apply_modern_window_style(win)

        header_frame = tk.Frame(win, bg="#1A1B1E", padx=12, pady=10)
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text=f"📜 {title}", font=("Georgia", 14, "bold"), bg="#1A1B1E", fg="#D4AF37").pack(anchor="w")

        content_frame = tk.Frame(win, bg="#212529", padx=14, pady=12)
        content_frame.pack(fill=tk.BOTH, expand=True)

        if img_b64:
            try:
                img_data = base64.b64decode(img_b64)
                img = Image.open(BytesIO(img_data))
                img.thumbnail((420, 320))
                tk_img = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(content_frame, image=tk_img, bg="#212529")
                lbl_img.image = tk_img
                lbl_img.pack(pady=6)
            except Exception as e:
                print("Errore rendering immagine handout:", e)

        if content:
            txt = tk.Text(content_frame, wrap="word", font=("Georgia", 11), bg="#2B2D31", fg="#F8F9FA", padx=10, pady=10, relief="flat", height=10)
            txt.pack(fill=tk.BOTH, expand=True, pady=6)
            txt.insert("1.0", content)
            txt.configure(state="disabled")

        btn_box = tk.Frame(win, bg="#1A1B1E", padx=10, pady=8)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT)

    def handle_quest_list_update(self, data):
        self.quests = data.get("quests", [])
        self.show_toast("Registro Missioni aggiornato dal Dungeon Master!", title="📜 Missioni Aggiornate", toast_type="gold")

    def open_quest_log_dialog(self):
        """Apre il registro interattivo delle missioni ed obiettivi della campagna."""
        from components.quest_ui import QuestLogDialog
        quests = getattr(self, "quests", []) or []
        if not quests and hasattr(self, "server") and getattr(self.server, "game_state", None):
            quests = getattr(self.server.game_state, "quests", [])
        QuestLogDialog(self.master, {"quests": quests}, is_dm=False, network_or_server=getattr(self, "network", None))

    def handle_journal_sync(self, data):
        """Riceve l'aggiornamento in tempo reale del Diario di Campagna dal Dungeon Master."""
        j_data = data.get("journal", {})
        if j_data:
            from common.campaign_journal import CampaignJournal
            self.campaign_journal = CampaignJournal.from_dict(j_data)
            if hasattr(self, "journal_dialog") and self.journal_dialog and self.journal_dialog.winfo_exists():
                self.journal_dialog.update_journal(self.campaign_journal)
            self.show_toast(
                _t("toast_journal_synced", default="Il Diario di Campagna è stato sincronizzato dal DM!"),
                title=_t("toast_journal_title", default="📖 Diario di Campagna"),
                toast_type="gold"
            )

    def open_player_journal_dialog(self):
        """Apre il Diario Narrativo di Sessione per consultare le cronache della campagna e annotare memorie personali."""
        from client.player_journal_dialog import PlayerJournalDialog
        journal = getattr(self, "campaign_journal", None)
        if not journal and hasattr(self, "server") and getattr(self.server, "game_state", None):
            journal = getattr(self.server.game_state, "campaign_journal", None)
        if not journal:
            from common.campaign_journal import CampaignJournal
            journal = CampaignJournal()
            self.campaign_journal = journal

        char_name = self.active_character.name if self.active_character else getattr(self, "name", "Avventuriero")
        if hasattr(self, "journal_dialog") and self.journal_dialog and self.journal_dialog.winfo_exists():
            self.journal_dialog.lift()
            self.journal_dialog.focus_force()
            return
        self.journal_dialog = PlayerJournalDialog(self.master, journal, character_name=char_name)

    def handle_opportunity_alert(self, data):
        enemy_name = data.get("enemy_name", "Un nemico")
        self.show_toast(f"{enemy_name} si allontana da te!\nPuoi effettuare un Attacco d'Opportunità spendendo la tua Reazione.", title="⚠️ Attacco d'Opportunità!", duration=6000, toast_type="warning", icon="⚔️")

    def handle_custom_spell_response(self, data):
        approved = data.get("approved", False)
        spell = data.get("spell", {})
        spell_name = spell.get("name", "Incantesimo")
        is_remove = spell.get("action") == "remove"
        if approved:
            if self.active_character:
                if is_remove:
                    self.active_character.spellbook = [s for s in getattr(self.active_character, "spellbook", []) if s.get("name") != spell_name]
                    self.character_manager.save_characters()
                    if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                        self.stats_window.refresh_spell_list()
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                    self.show_toast(f"Il Dungeon Master ha APPROVATO la rimozione di '{spell_name}' dal Grimorio.", title="Rimozione Approvata", toast_type="info")
                    return
                if not hasattr(self.active_character, "spellbook") or not isinstance(self.active_character.spellbook, list):
                    self.active_character.spellbook = []
                if not any(s.get("name") == spell_name for s in self.active_character.spellbook):
                    self.active_character.spellbook.append(spell)
                    self.character_manager.save_characters()
                    if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                        self.stats_window.refresh_spell_list()
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.show_toast(f"Il Dungeon Master ha APPROVATO l'incantesimo '{spell_name}'!\nÈ stato aggiunto al tuo Grimorio.", title="Incantesimo Approvato!", toast_type="success")
        else:
            reason = data.get("reason", "Il Master ha respinto la richiesta.")
            act_disp = "la rimozione di" if is_remove else "la richiesta per"
            self.show_toast(f"Il Dungeon Master ha RESPINTO {act_disp} '{spell_name}'.\nMotivo: {reason}", title="Richiesta Rifiutata", toast_type="warning")

    def handle_currency_response(self, data):
        approved = data.get("approved", False)
        coin = data.get("coin", "MO")
        amount = data.get("amount", 0)
        reason = data.get("reason", "")
        if approved:
            if self.active_character:
                if not hasattr(self.active_character, "currency") or not isinstance(self.active_character.currency, dict):
                    self.active_character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
                self.active_character.currency[coin] = self.active_character.currency.get(coin, 0) + amount
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    if hasattr(self.stats_window, "currency_vars") and coin in self.stats_window.currency_vars:
                        self.stats_window.currency_vars[coin].set(self.active_character.currency[coin])
                    if hasattr(self.stats_window, "initial_currency"):
                        self.stats_window.initial_currency[coin] = self.active_character.currency[coin]
            self.show_toast(f"Il Dungeon Master ha APPROVATO la richiesta!\nHai ricevuto +{amount} {coin}.", title="Valuta Accreditata!", toast_type="gold")
        else:
            msg = reason or "La tua richiesta di valuta è stata respinta dal Master."
            self.show_toast(msg, title="Richiesta Respinta", toast_type="warning")

    def handle_journal_approval_response(self, data):
        approved = data.get("approved", False)
        field_name = data.get("field_name")
        content = data.get("content")
        reason = data.get("reason", "")
        field_disp = "Biografia & Diario" if "journal" in str(field_name) else ("Tratti & Privilegi" if "features" in str(field_name) else "Appunti di Sessione")
        if approved:
            if self.active_character:
                if hasattr(self.active_character, field_name):
                    setattr(self.active_character, field_name, content)
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.load_data()
            self.show_toast(f"Il Dungeon Master ha APPROVATO le tue modifiche a '{field_disp}'!", title="Modifica Approvata!", toast_type="success")
            self.log_to_chat(f"📜 Il Master ha approvato le modifiche a '{field_disp}'.", "Sistema", ACCENT_GOLD)
        else:
            msg = reason or f"La richiesta di modifica per '{field_disp}' è stata respinta dal Master."
            self.show_toast(msg, title="Modifica Respinta", toast_type="warning")
            self.log_to_chat(f"❌ {msg}", "Sistema", "#FF6B6B")

    def request_journal_approval(self, field_name, content, title=""):
        if self.is_connected:
            from common.protocol import make_journal_approval_request
            self.network.send(make_journal_approval_request(field_name, content, title))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso per richiedere l'approvazione al Master.")
            return False

    def handle_item_approval_response(self, data):
        approved = data.get("approved", False)
        item = data.get("item", {})
        slot_idx = data.get("slot_idx")
        reason = data.get("reason", "")
        it_name = item.get("name", "Oggetto")
        is_remove = item.get("action") == "remove"
        is_weapon_req = item.get("target_collection") == "weapons"
        if approved:
            if self.active_character:
                from common.protocol import make_update_full_sheet_request
                if is_weapon_req:
                    if not hasattr(self.active_character, "weapons") or not isinstance(self.active_character.weapons, list):
                        self.active_character.weapons = []
                    if is_remove:
                        if slot_idx is not None and 0 <= slot_idx < len(self.active_character.weapons):
                            self.active_character.weapons.pop(slot_idx)
                        else:
                            for w_i, w_obj in enumerate(self.active_character.weapons):
                                if isinstance(w_obj, dict) and w_obj.get("name") == it_name:
                                    self.active_character.weapons.pop(w_i)
                                    break
                        self.character_manager.save_characters()
                        if hasattr(self, "stats_window") and self.stats_window and self.stats_window.winfo_exists():
                            if hasattr(self.stats_window, "refresh_weapons_list"):
                                self.stats_window.refresh_weapons_list()
                        self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                        self.show_toast(f"Il Dungeon Master ha APPROVATO la rimozione dell'arma '{it_name}'.", title="Rimozione Arma Approvata", toast_type="info")
                        return
                    clean_weapon = {k: v for k, v in item.items() if k not in ("action", "target_collection")}
                    self.active_character.weapons.append(clean_weapon)
                    self.character_manager.save_characters()
                    if hasattr(self, "stats_window") and self.stats_window and self.stats_window.winfo_exists():
                        if hasattr(self.stats_window, "refresh_weapons_list"):
                            self.stats_window.refresh_weapons_list()
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                    self.show_toast(f"Il Dungeon Master ha APPROVATO l'arma '{it_name}'!", title="Arma Approvata!", toast_type="success")
                    return

                if is_remove:
                    if not hasattr(self.active_character, "inventory_grid") or not isinstance(self.active_character.inventory_grid, list):
                        self.active_character.inventory_grid = [None] * 25
                    if slot_idx is not None and 0 <= slot_idx < len(self.active_character.inventory_grid):
                        self.active_character.inventory_grid[slot_idx] = None
                    else:
                        for i in range(len(self.active_character.inventory_grid)):
                            if self.active_character.inventory_grid[i] and self.active_character.inventory_grid[i].get("name") == it_name:
                                self.active_character.inventory_grid[i] = None
                                break
                    self.character_manager.save_characters()
                    if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                        self.stats_window.refresh_inventory_grid()
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                    self.show_toast(f"Il Dungeon Master ha APPROVATO la rimozione di '{it_name}' dallo zaino.", title="Rimozione Approvata", toast_type="info")
                    return
                if not hasattr(self.active_character, "inventory_grid") or not isinstance(self.active_character.inventory_grid, list):
                    self.active_character.inventory_grid = [None] * 25
                clean_item = {k: v for k, v in item.items() if k not in ("action", "target_collection")}
                placed = False
                if slot_idx is not None and 0 <= slot_idx < len(self.active_character.inventory_grid) and self.active_character.inventory_grid[slot_idx] is None:
                    self.active_character.inventory_grid[slot_idx] = clean_item
                    placed = True
                else:
                    for i in range(len(self.active_character.inventory_grid)):
                        if self.active_character.inventory_grid[i] is None:
                            self.active_character.inventory_grid[i] = clean_item
                            placed = True
                            break
                if not placed:
                    self.active_character.inventory_grid.append(clean_item)
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.refresh_inventory_grid()
                self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.show_toast(f"Il Dungeon Master ha APPROVATO '{it_name}'!\nL'oggetto è stato aggiunto al tuo inventario.", title="Oggetto Approvato!", toast_type="success")
        else:
            act_disp = "la rimozione di" if is_remove else "la richiesta per"
            msg = reason or f"La richiesta per {act_disp} '{it_name}' è stata respinta dal Master."
            self.show_toast(msg, title="Richiesta Respinta", toast_type="warning")

    def handle_campaign_starter_granted(self, data):
        full_sheet = data.get("full_sheet")
        if full_sheet and self.active_character:
            for k in ["inventory_grid", "spellbook", "spell_slots", "ac", "starting_kit_applied", "campaign_starter_received"]:
                if k in full_sheet:
                    setattr(self.active_character, k, full_sheet[k])
            self.character_manager.save_characters()
            if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                self.stats_window.load_data()
        elif self.active_character:
            items = data.get("items", [])
            if items:
                self.active_character.inventory_grid = items
                self.active_character.campaign_starter_received = True
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.load_data()
        self.log_to_chat("Hai ricevuto l'equipaggiamento iniziale della campagna dal Master!", "Globale", sender="Sistema", color="#2ECC71")

    def request_custom_spell(self, spell_dict):
        if self.is_connected:
            from common.protocol import make_custom_spell_request
            self.network.send(make_custom_spell_request(spell_dict))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso al server per richiedere l'approvazione di un incantesimo al Master!")
            return False

    def request_currency(self, coin, amount, reason=""):
        if self.is_connected:
            from common.protocol import make_currency_request
            self.network.send(make_currency_request(coin, amount, reason))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso per richiedere valuta al Master.")
            return False

    def request_item_approval(self, item, slot_idx=None):
        if self.is_connected:
            from common.protocol import make_item_approval_request
            self.network.send(make_item_approval_request(item, slot_idx))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso per richiedere l'approvazione di oggetti al Master.")
            return False

    def handle_audio_play(self, data):
        import webbrowser
        from urllib.parse import urlparse
        url = str((data or {}).get("url") or "").strip()
        if not url:
            return
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            print(f"[SECURITY] URL audio bloccato (schema non consentito): {url}")
            return
        webbrowser.open(url)
        self.log_to_chat("Stai ascoltando un audio avviato dal DM", "Globale", sender="Sistema", color="#99AAB5")

    def handle_audio_track_play(self, data):
        track_id = data.get("track_id")
        name = data.get("name", "Audio")
        ext = data.get("ext", ".mp3")
        channel = data.get("channel", "music")
        loop = data.get("loop", False)
        volume = float(data.get("volume", 0.8))
        if not track_id:
            return

        clean_track_id = re.sub(r"[^A-Za-z0-9_-]", "", str(track_id))
        clean_ext = str(ext).lower() if str(ext).lower() in (".mp3", ".wav", ".ogg", ".flac") else ".mp3"
        if not clean_track_id:
            return
        track_id = clean_track_id
        ext = clean_ext

        cache_dir_abs = os.path.realpath(self.audio_cache_dir)
        target_path = os.path.realpath(os.path.join(self.audio_cache_dir, f"{track_id}{ext}"))
        if not target_path.startswith(cache_dir_abs + os.sep) and target_path != cache_dir_abs:
            return

        if os.path.isfile(target_path):
            self.audio_manager.play(target_path, channel=channel, loop=loop, volume=volume, name=name)
            icon = "🎵" if channel == "music" else "💥"
            self.log_to_chat(f"In riproduzione: {icon} {name}", "Globale", sender="Audio", color="#1ABC9C")
        else:
            self._pending_play = {
                "track_id": track_id,
                "name": name,
                "channel": channel,
                "loop": loop,
                "volume": volume,
                "ext": ext
            }
            from common.protocol import make_audio_track_request
            self.network.send(make_audio_track_request(track_id))
            self.log_to_chat(f"Scaricamento traccia '{name}' dal server in corso...", "Globale", sender="Audio", color="#7289DA")

    def _prune_stale_audio_downloads(self, now: float = None):
        """Rimuove trasferimenti audio incompleti o corrotti scaduti per TTL."""
        downloads = getattr(self, "_audio_downloads", None)
        if not isinstance(downloads, dict):
            return
        if now is None:
            now = _monotonic_now()
        ttl = getattr(self, "_audio_download_ttl", 60.0)
        ttl = float(ttl) if isinstance(ttl, (int, float)) and not isinstance(ttl, bool) else 60.0
        stale_ids = []
        for tid, rec in list(downloads.items()):
            if not isinstance(rec, dict):
                stale_ids.append(tid)
                continue
            last_ts = rec.get("updated_at", rec.get("started_at"))
            if isinstance(last_ts, (int, float)) and not isinstance(last_ts, bool) and (now - float(last_ts)) > ttl:
                stale_ids.append(tid)
        for tid in stale_ids:
            downloads.pop(tid, None)
            pending = getattr(self, "_pending_play", None)
            if isinstance(pending, dict) and pending.get("track_id") == tid:
                self._pending_play = None

    def handle_audio_track_chunk(self, data):
        if not isinstance(data, dict):
            return
        ClientNetworkHandlersMixin._prune_stale_audio_downloads(self)
        track_id = data.get("track_id")
        try:
            index = int(data.get("index", 0))
            total = int(data.get("total", 1))
        except (ValueError, TypeError):
            return
        if not (1 <= total <= 500) or not (0 <= index < total):
            return

        b64_data = data.get("data", "")
        if not isinstance(b64_data, str):
            return
        ext = data.get("ext") or (self._pending_play.get("ext") if self._pending_play and self._pending_play.get("track_id") == track_id else ".mp3")

        if not track_id:
            return

        clean_track_id = re.sub(r"[^A-Za-z0-9_-]", "", str(track_id))
        clean_ext = str(ext).lower() if str(ext).lower() in (".mp3", ".wav", ".ogg", ".flac") else ".mp3"
        if not clean_track_id:
            return
        track_id = clean_track_id
        ext = clean_ext

        try:
            decoded_chunk = base64.b64decode(b64_data, validate=True)
        except Exception as e:
            print(f"[AUDIO] Errore decodifica chunk {index}: {e}")
            return
        if len(decoded_chunk) > 512 * 1024:
            return

        now = _monotonic_now()
        if track_id not in self._audio_downloads:
            max_dl = getattr(self, "_max_audio_downloads", 8)
            max_dl = max(1, int(max_dl)) if isinstance(max_dl, int) and not isinstance(max_dl, bool) else 8
            while len(self._audio_downloads) >= max_dl and self._audio_downloads:
                oldest_tid = min(
                    self._audio_downloads,
                    key=lambda tid: (
                        float(self._audio_downloads[tid].get("updated_at", self._audio_downloads[tid].get("started_at", 0.0)))
                        if isinstance(self._audio_downloads[tid], dict)
                        and isinstance(self._audio_downloads[tid].get("updated_at", self._audio_downloads[tid].get("started_at", 0.0)), (int, float))
                        else 0.0
                    ),
                )
                self._audio_downloads.pop(oldest_tid, None)
                pending = getattr(self, "_pending_play", None)
                if isinstance(pending, dict) and pending.get("track_id") == oldest_tid:
                    self._pending_play = None
            self._audio_downloads[track_id] = {
                "total": total,
                "ext": ext,
                "chunks": {},
                "started_at": now,
                "updated_at": now,
            }

        rec = self._audio_downloads[track_id]
        if rec.get("total") != total:
            return
        if ext and not rec.get("ext"):
            rec["ext"] = ext
        rec["chunks"][index] = decoded_chunk
        rec["updated_at"] = now

        if len(rec["chunks"]) == rec["total"] and all(i in rec["chunks"] for i in range(rec["total"])):
            cache_dir_abs = os.path.realpath(self.audio_cache_dir)
            target_path = os.path.realpath(os.path.join(self.audio_cache_dir, f"{track_id}{rec['ext']}"))
            if not target_path.startswith(cache_dir_abs + os.sep) and target_path != cache_dir_abs:
                return
            tmp_path = f"{target_path}.tmp"
            try:
                os.makedirs(cache_dir_abs, exist_ok=True)
                with open(tmp_path, "wb") as f:
                    for i in range(rec["total"]):
                        f.write(rec["chunks"][i])
                os.replace(tmp_path, target_path)
            except Exception as e:
                print(f"[AUDIO] Errore salvataggio file in cache {target_path}: {e}")
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass
                return
            finally:
                if track_id in self._audio_downloads:
                    del self._audio_downloads[track_id]

            if self._pending_play and self._pending_play.get("track_id") == track_id:
                req = self._pending_play
                self._pending_play = None
                self.audio_manager.play(target_path, channel=req.get("channel", "music"), loop=req.get("loop", False), volume=req.get("volume", 0.8), name=req.get("name", "Audio"))
                icon = "🎵" if req.get("channel") == "music" else "💥"
                self.log_to_chat(f"In riproduzione: {icon} {req.get('name')}", "Globale", sender="Audio", color="#1ABC9C")

    def handle_audio_stop(self, data):
        channel = data.get("channel", "all")
        self.audio_manager.stop(channel)
        if self._pending_play:
            if channel == "all" or channel == self._pending_play.get("channel"):
                self._pending_play = None

    def handle_prompt_long_rest_vote(self, data):
        initiator = data.get("initiator", "Qualcuno")
        if messagebox.askyesno("Voto Riposo Lungo", f"{initiator} propone un Riposo Lungo. Questo resettera' slot, salute e dadi vita.\n\nSei d'accordo?"):
            self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": True}})
        else:
            self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": False}})

    def handle_do_long_rest(self, data):
        if self.active_character:
            self.active_character.long_rest()
            self.character_manager.update_character(self.active_character)
            from common.protocol import make_update_full_sheet_request
            self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.show_toast("Il gruppo ha completato un Riposo Lungo. Hai recuperato le tue statistiche.", title="Riposo Lungo Completato", toast_type="success")
            if hasattr(self, "stats_window") and self.stats_window and self.stats_window.winfo_exists():
                self.stats_window.load_data()

    def handle_draw_broadcast(self, data):
        points = data.get("points", [])
        color = data.get("color", "red")
        if hasattr(self, "map_canvas"):
            self.map_canvas.draw_remote_line(points, color)

    def handle_clear_drawings_broadcast(self, data):
        if hasattr(self, "map_canvas") and self.map_canvas:
            self.map_canvas.clear_drawings()

    def toggle_whiteboard_pen(self):
        if not hasattr(self, "map_canvas") or not self.map_canvas: return
        will_activate = not getattr(self.map_canvas, "pen_mode", False)
        if will_activate and hasattr(self, "_deactivate_all_map_tools"):
            self._deactivate_all_map_tools(except_tool="pen")
        is_active = self.map_canvas.toggle_pen_mode()
        if hasattr(self, "pen_btn"):
            self.pen_btn.config(style="ToolActive.TButton" if is_active else "Tool.TButton")
        self.show_toast("Modalità Penna Disegno: " + ("Attiva" if is_active else "Disattivata"), title="Lavagna", toast_type="info")

    def clear_whiteboard_drawings(self):
        from common.messagebox import messagebox
        if not messagebox.askyesno(_t("tool_clear_drawings"), "Cancellare tutti i disegni a mano libera dalla mappa?"):
            return
        if self.map_canvas:
            self.map_canvas.clear_drawings()
        if hasattr(self, "network") and self.network:
            from common.protocol import make_clear_drawings_request
            self.network.send(make_clear_drawings_request())
        self.show_toast("Disegni mappa cancellati", title="Lavagna", toast_type="info")

    def export_session_log(self):
        import html as _html
        chat_widget = getattr(self, "chat_display", None)
        if chat_widget is None and isinstance(getattr(self, "chat_tabs", None), dict):
            chat_widget = self.chat_tabs.get("Globale") or next(iter(self.chat_tabs.values()), None)
        if chat_widget is None:
            return
        log_text = chat_widget.get("1.0", tk.END).strip()
        from common.messagebox import messagebox
        if not log_text:
            messagebox.showinfo(_t("export_log_title"), _t("export_log_empty"))
            return

        from tkinter import filedialog
        from datetime import datetime
        default_filename = f"Player_Session_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = filedialog.asksaveasfilename(
            title=_t("menu_export_session_log"),
            initialfile=default_filename,
            filetypes=[("Markdown (*.md)", "*.md"), ("HTML (*.html)", "*.html"), ("Text (*.txt)", "*.txt")]
        )
        if not filepath:
            return

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        char_name = (
            self.active_character.name
            if getattr(self, "active_character", None)
            else (getattr(self, "name", None) or getattr(self, "username", None) or "Giocatore")
        )

        if filepath.endswith(".html"):
            safe_title = _html.escape(_t('export_log_title'))
            safe_char = _html.escape(str(char_name))
            safe_log = _html.escape(log_text)
            html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>{safe_title} - {safe_char}</title>
<style>
body {{ background-color: #121316; color: #E5E7EB; font-family: 'Segoe UI', Tahoma, sans-serif; padding: 24px; line-height: 1.6; }}
h1 {{ color: #F59E0B; border-bottom: 2px solid #D97706; padding-bottom: 8px; }}
.meta {{ color: #9CA3AF; font-size: 0.9em; margin-bottom: 20px; }}
.log-box {{ background-color: #1A1B1E; border: 1px solid #374151; border-radius: 8px; padding: 18px; white-space: pre-wrap; font-family: 'Consolas', monospace; }}
</style>
</head>
<body>
<h1>📜 {safe_title} - {safe_char}</h1>
<div class="meta">Esportato il: {now_str} • D&D OmniCompanion</div>
<div class="log-box">{safe_log}</div>
</body>
</html>"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
        else:
            md_content = f"""# 📜 {_t('export_log_title')} - {char_name}
**Data Esportazione:** {now_str}
**Giocatore / Personaggio:** {char_name}
**Piattaforma:** D&D OmniCompanion

---

```
{log_text}
```
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)

        messagebox.showinfo(_t("export_log_title"), _t("export_log_saved").format(path=filepath))

    def handle_ping_broadcast(self, data):
        if self.map_canvas:
            self.map_canvas.draw_ping(data.get("q"), data.get("r"), data.get("color", "red"))

    def handle_fow_update_broadcast(self, data):
        if not hasattr(self, 'local_map_data') or self.local_map_data is None:
            self.local_map_data = {}
        self.local_map_data["fow_revealed"] = data.get("fow_revealed", [])
        self.local_map_data.pop("fow_draft", None)
        if "fow_enabled" in data:
            self.local_map_data["fow_enabled"] = bool(data.get("fow_enabled"))
        if isinstance(data.get("players"), list):
            prev_map = getattr(self, "players_data", None) if isinstance(getattr(self, "players_data", None), dict) else {}
            new_pdata = {}
            for p in data["players"]:
                if isinstance(p, dict) and p.get("name"):
                    pname = p["name"]
                    prev = prev_map.get(pname)
                    if isinstance(prev, dict):
                        p = dict(p)
                        for keep_k in ("full_sheet", "avatar_b64"):
                            if keep_k in prev and not p.get(keep_k):
                                p[keep_k] = prev[keep_k]
                    new_pdata[pname] = p
            self.players_data = new_pdata
            if hasattr(self, "update_player_listbox"):
                self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_request_initiative(self, data):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("Iniziativa")
        win.minsize(300, 200)
        from common.theme import apply_modern_window_style
        apply_modern_window_style(win)
        
        ttk.Label(win, text="Combattimento Iniziato!", font=("Georgia", 14, "bold"), foreground="#D4AF37").pack(pady=10)
        ttk.Label(win, text="Tira l'Iniziativa:").pack(pady=5)
        
        if self.active_character and hasattr(self.active_character, "get_initiative_bonus"):
            mod = self.active_character.get_initiative_bonus()
        else:
            mod = getattr(self.active_character, 'initiative', 0) if self.active_character else 0
        ttk.Label(win, text=f"Il tuo modificatore è: {mod:+d}").pack(pady=5)
        
        def roll():
            import random
            from common.protocol import make_submit_initiative
            roll_val = random.randint(1, 20)
            total = roll_val + mod
            self.network.send(make_submit_initiative(total))
            self.log_to_chat(f"Hai tirato iniziativa: {roll_val} + {mod} = {total}", "Globale", "orange")
            win.destroy()
            
        ttk.Button(win, text="Tira 1d20 + Iniziativa", command=roll, style='Primary.TButton').pack(pady=15)

    def handle_update_inspiration(self, data):
        has_insp = data.get("has_inspiration", True)
        if self.active_character:
            self.active_character.has_inspiration = has_insp
            self.character_manager.save_characters()
            if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                self.stats_window.set_inspiration(has_insp)
        if has_insp:
            self.log_to_chat("🌟 Hai ricevuto l'Ispirazione dal Dungeon Master!", "Globale", sender="Sistema", color="#FEE75C")
            self.show_toast("🌟 Hai ricevuto l'Ispirazione dal Dungeon Master!\nPuoi usarla per ottenere Vantaggio in un attacco o prova.", title="Ispirazione Assegnata", toast_type="gold")
        else:
            self.log_to_chat("☆ L'Ispirazione è stata consumata o rimossa.", "Globale", sender="Sistema", color="#99AAB5")

    def give_gold(self, target_name, amount):
        if not self.is_connected:
            self.show_toast("Devi essere connesso per donare oro.", title="Non Connesso", toast_type="warning")
            return
        if not self.active_character: return
        
        cur_gold = self.active_character.currency.get("MO", 0) if hasattr(self.active_character, "currency") else 0
        if amount > cur_gold:
            self.show_toast(f"Possiedi solo {cur_gold} MO.", title="Oro Insufficiente", toast_type="warning")
            return
            
        self.active_character.currency["MO"] -= amount
        self.character_manager.save_characters()
        from common.protocol import make_give_gold_request, make_update_full_sheet_request
        self.network.send(make_give_gold_request(target_name, amount))
        self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
        self.log_to_chat(f"Hai consegnato {amount} MO a {target_name}.", "Globale", sender="Sistema", color="#00B0F4")
        self.show_toast(f"Hai consegnato {amount} MO a {target_name}.", title="Oro Donato", toast_type="success")

    def handle_receive_gold(self, data):
        amount = data.get("amount", 0)
        sender = data.get("sender", "Il DM")
        if not self.active_character: return
        
        if not hasattr(self.active_character, "currency") or not isinstance(self.active_character.currency, dict):
            self.active_character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            
        self.active_character.currency["MO"] = self.active_character.currency.get("MO", 0) + amount
        
        self.character_manager.save_characters()
        from common.protocol import make_update_full_sheet_request
        self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
        
        if getattr(self, "sheet_ui", None) and self.sheet_ui.winfo_exists():
            self.sheet_ui.load_data()
        elif getattr(self, "stats_window", None) and self.stats_window.winfo_exists():
            self.stats_window.load_data()
            
        self.show_toast(f"{sender} ti ha inviato {amount} MO!", title="Loot Ricevuto", toast_type="gold")
        self.log_to_chat(f"Hai ricevuto {amount} MO da {sender}.", "Globale", sender="Sistema", color="#2ECC71")

    def handle_receive_item(self, data):
        item = data.get("item")
        if not self.active_character or not item: return
        
        sender = item.pop("_sender", "Il DM")
        
        # Trova il primo slot libero nella griglia
        for i in range(len(self.active_character.inventory_grid)):
            if self.active_character.inventory_grid[i] is None:
                self.active_character.inventory_grid[i] = item
                self.character_manager.save_characters()
                self.show_toast(f"{sender} ti ha assegnato/inviato: {item['name']}", title="Oggetto Ricevuto", toast_type="gold")
                # Invia l'aggiornamento della scheda al server
                self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                if hasattr(self, "stats_window") and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.load_data()
                return
        
        self.show_toast(f"{sender} ha provato ad inviarti '{item['name']}' ma non hai spazio nello zaino!", title="Inventario Pieno", toast_type="warning")
        if sender and sender != self.name:
            # Rimbalza l'oggetto al mittente per evitarne la distruzione
            from common.protocol import make_give_item_request
            self.network.send(make_give_item_request(sender, item))

    def handle_chat_broadcast(self, data):
        sender, text, is_whisper=data.get('sender'), data.get('text'), data.get('is_whisper')
        if not is_whisper:
            self.log_to_chat(text, "Globale", sender=sender, color="#5865F2")
        else:
            tab_name=sender.replace("Tu -> ", "") if sender.startswith("Tu -> ") else sender
            prefix="Tu" if sender.startswith("Tu -> ") else sender
            self.create_chat_tab(tab_name)
            self.log_to_chat(text, tab_name, sender=prefix, color="#EB459E")
            self.log_to_chat(f"🔒 [Sussurro] {text}", "Globale", sender=sender, color="#EB459E")

    def handle_dice_roll(self, data):
        res = data.get('result', {})
        reason = data.get('reason')
        reason_text = f" ({reason})" if reason else ""
        player_name = data.get('player_name', 'Qualcuno')
        formula = data.get('formula', '')
        rolls = res.get('rolls', [])
        other_rolls = res.get('other_rolls', [])
        mod = res.get('modifier', 0)
        total = res.get('total', 0)

        is_crit = res.get('is_crit', False)
        is_fumble = res.get('is_fumble', False) or res.get('is_crit_fail', False)

        rolls_display = f"{rolls}"
        if other_rolls:
            rolls_display = f"{rolls} (scartato: {other_rolls})"

        mod_str = f" + {mod}" if mod >= 0 else f" - {abs(mod)}"
        crit_badge = ""
        chat_color = "#FEE75C"
        if is_crit:
            crit_badge = " 🌟 SUCCESSO CRITICO! (20 Naturale)"
            chat_color = "#2ECC71"
            self.show_toast(
                f"{player_name} ha ottenuto un 20 NATURALE su {reason or formula} (Totale: {total})!",
                title="🌟 Successo Critico!",
                toast_type="gold",
            )
        elif is_fumble:
            crit_badge = " 💀 FALLIMENTO CRITICO! (1 Naturale)"
            chat_color = "#ED4245"
            self.show_toast(
                f"{player_name} ha ottenuto un 1 NATURALE su {reason or formula} (Totale: {total})!",
                title="💀 Fallimento Critico!",
                toast_type="danger",
            )

        log_text = f"tira {formula}{reason_text}: {rolls_display}{mod_str} = {total}{crit_badge}"
        self.log_to_chat(log_text, "Globale", sender=player_name, color=chat_color)
        self.trigger_3d_dice_roll(formula, res, player_name=player_name, reason=reason)
    
