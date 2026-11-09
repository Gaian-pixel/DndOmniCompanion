"""
client.sheet_panels - Sotto-moduli e pannelli specializzati per la Scheda Personaggio (CharacterSheetFrame).
Decompone il monolite della scheda personaggio in componenti modulari riutilizzabili e testabili:
- vitals_panel: Gestione PF, CA, TS Morte, Dadi Vita e Riposi
- inventory_panel: Griglia inventario 5x5, contenitori, monete e peso trasportabile
- spells_panel: Slot incantesimi 1-9, libro incantesimi, CD e bonus attacco incantesimi
- combat_panel: Armi, attacchi, danni e azioni di combattimento
"""

from .vitals_panel import VitalsPanel
from .inventory_panel import InventoryPanel
from .spells_panel import SpellsPanel
from .combat_panel import CombatPanel

__all__ = ["VitalsPanel", "InventoryPanel", "SpellsPanel", "CombatPanel"]

