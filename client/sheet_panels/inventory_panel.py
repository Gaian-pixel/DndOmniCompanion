"""
client/sheet_panels/inventory_panel.py - Gestione Inventario, Peso, Ingombro e Monete (5e RAW).
Modulo estratto da CharacterSheetFrame per separazione di responsabilità e testabilità.
"""

import tkinter as tk
from common.i18n import _t
from common.starter_equipment import lookup_standard_weight


class InventoryPanel:
    """Gestisce la logica del carico, ingombro, monete e contenitori della scheda personaggio."""

    COIN_RATES_TO_GP = {
        "MR": 0.01,  # 100 cp = 1 gp
        "MA": 0.1,   # 10 sp = 1 gp
        "ME": 0.5,   # 2 ep = 1 gp
        "MO": 1.0,   # 1 gp = 1 gp
        "MP": 10.0   # 1 pp = 10 gp
    }

    @staticmethod
    def get_estimated_gold_value(currency_dict):
        """Calcola il controvalore totale convertito in Monete d'Oro (gp)."""
        if not currency_dict or not isinstance(currency_dict, dict):
            return 0.0
        total_gp = 0.0
        for coin, amt in currency_dict.items():
            rate = InventoryPanel.COIN_RATES_TO_GP.get(coin, 1.0)
            try:
                total_gp += float(amt or 0) * rate
            except (ValueError, TypeError):
                pass
        return total_gp

    @staticmethod
    def calculate_total_weight(sheet):
        """Calcola e aggiorna la barra di ingombro (Regole 5e Standard e Variante)."""
        if not hasattr(sheet, 'weight_vars') or not hasattr(sheet, 'weight_label'):
            return
        if getattr(sheet, '_suppress_weight_sync', False):
            return

        slot_limit = min(len(sheet.character.inventory_grid), len(sheet.weight_vars))
        for i in range(slot_limit):
            item = sheet.character.inventory_grid[i]
            if item:
                try:
                    w_val = float(sheet.weight_vars[i].get())
                    if w_val > 0:
                        item["weight"] = w_val
                    elif not item.get("weight") or float(item.get("weight", 0)) == 0:
                        std_w = lookup_standard_weight(item.get("name", ""))
                        if std_w > 0:
                            item["weight"] = std_w
                            sheet.weight_vars[i].set(std_w)
                except (tk.TclError, ValueError):
                    pass

        enc = sheet.character.get_encumbrance_status()
        total = enc["carried_weight"]
        max_weight = enc["limit_max"]
        tier = enc["tier"]

        if hasattr(sheet, 'weight_bar'):
            sheet.weight_bar['maximum'] = max(1.0, max_weight)
            sheet.weight_bar['value'] = min(max_weight, total)

        enc_text = {
            "normal": _t("enc_normal"),
            "encumbered": _t("enc_encumbered"),
            "heavily_encumbered": _t("enc_heavily_encumbered"),
            "overloaded": _t("enc_overloaded")
        }.get(tier, _t("enc_normal"))

        sheet.weight_label.config(
            text=f"{_t('sheet_total_weight', current=f'{total:.1f}', max=f'{max_weight:.1f}')}  [{enc_text}]",
            fg=enc["color"]
        )

        if hasattr(sheet, 'weight_details_lbl'):
            details = []
            coin_count = (
                sum(int(v or 0) for v in sheet.character.currency.values() if str(v).isdigit())
                if hasattr(sheet.character, "currency") and isinstance(sheet.character.currency, dict)
                else 0
            )
            coin_lbs = round(coin_count / 50.0, 1)
            if coin_lbs > 0:
                details.append(_t("lbl_coins_weight", weight=f"{coin_lbs:.1f}"))

            if enc.get("backpack_dropped"):
                details.append(_t("lbl_backpack_ground_weight", weight=f"{enc['backpack_weight']:.1f}"))

            if enc.get("boh_weight", 0) > 0:
                details.append(_t("lbl_boh_capacity", cur=f"{enc['boh_weight']:.1f}"))

            if enc.get("haversack_weight", 0) > 0:
                details.append(_t("lbl_haversack_capacity", cur=f"{enc['haversack_weight']:.1f}"))

            if enc.get("mount_weight", 0) > 0:
                details.append(_t("lbl_mount_capacity", cur=f"{enc['mount_weight']:.1f}"))

            sheet.weight_details_lbl.config(text=" • ".join(details) if details else "")

        if hasattr(sheet, 'btn_drop_backpack') and hasattr(sheet, 'lbl_backpack_status'):
            from common.theme import ACCENT_GREEN
            if enc.get("backpack_dropped"):
                sheet.btn_drop_backpack.config(text=_t("btn_pickup_backpack"), style="Gold.TButton")
                sheet.lbl_backpack_status.config(text=_t("status_backpack_ground"), fg="#F59E0B")
            else:
                sheet.btn_drop_backpack.config(text=_t("btn_drop_backpack"), style="Slot.TButton")
                sheet.lbl_backpack_status.config(text=_t("status_backpack_worn"), fg=ACCENT_GREEN)

    @staticmethod
    def update_currency_total(sheet):
        """Aggiorna il conteggio totale e il valore stimato della borsa delle monete."""
        if not hasattr(sheet, 'currency_vars') or not hasattr(sheet, 'currency_total_lbl'):
            return
        total_gp = 0.0
        for coin, var in sheet.currency_vars.items():
            rate = InventoryPanel.COIN_RATES_TO_GP.get(coin, 1.0)
            try:
                amt = float(var.get() or 0)
                total_gp += amt * rate
            except (tk.TclError, ValueError):
                pass
        sheet.currency_total_lbl.config(text=f"{_t('sheet_currency_total')}: ≈ {total_gp:.2f} MO")
        InventoryPanel.calculate_total_weight(sheet)
