# common/starter_equipment.py
"""
Modulo per la gestione dell'equipaggiamento iniziale, delle armi, delle armature
e degli incantesimi base per classe, razza e campagna (D&D 5e).
"""
import os
import json

# Equipaggiamento iniziale standard D&D 5e per ogni classe
CLASS_STARTING_KITS = {
    "Guerriero": {
        "ac_base": 16, # Cotta di Maglia
        "ac_shield": 2, # Scudo
        "items": [
            {"name": "Cotta di Maglia", "type": "Armatura", "qty": 1, "desc": "Armatura pesante. CA 16.", "weight": 55.0},
            {"name": "Spada Lunga", "type": "Arma", "qty": 1, "desc": "1d8 (versatile 1d10) danni taglienti.", "weight": 3.0},
            {"name": "Scudo", "type": "Scudo", "qty": 1, "desc": "+2 CA quando impugnato.", "weight": 6.0},
            {"name": "Balestra Leggera", "type": "Arma", "qty": 1, "desc": "1d8 danni perforanti, gittata 24/96m.", "weight": 5.0},
            {"name": "Dardi da Balestra", "type": "Munizioni", "qty": 20, "desc": "Munizioni per balestra.", "weight": 0.075},
            {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "desc": "Sacco a pelo, acciarino, 10 torce, 10 razioni e corda 15m.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Mago": {
        "ac_base": 10, # 10 + Des
        "ac_shield": 0,
        "items": [
            {"name": "Pugnale", "type": "Arma", "qty": 1, "desc": "1d4 danni perforanti, accurata, leggera.", "weight": 1.0},
            {"name": "Focus Arcano (Bacchetta)", "type": "Focus", "qty": 1, "desc": "Canalizzatore magico per incantesimi.", "weight": 1.0},
            {"name": "Grimorio del Mago", "type": "Oggetto", "qty": 1, "desc": "Tomo contenente tutti gli incantesimi trascritti dal mago.", "weight": 3.0},
            {"name": "Borsa dei Componenti", "type": "Equipaggiamento", "qty": 1, "desc": "Borsello con componenti materiali per incantesimi.", "weight": 2.0},
            {"name": "Zaino da Studioso", "type": "Equipaggiamento", "qty": 1, "desc": "Libro di nozioni, inchiostro, penna d'oca, pergamene, razioni.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Ladro": {
        "ac_base": 11, # Corazza di cuoio 11 + Des
        "ac_shield": 0,
        "items": [
            {"name": "Corazza di Cuoio", "type": "Armatura", "qty": 1, "desc": "Armatura leggera. CA 11 + mod Destrezza.", "weight": 10.0},
            {"name": "Stocco", "type": "Arma", "qty": 1, "desc": "1d8 danni perforanti, accurata.", "weight": 2.0},
            {"name": "Arco Corto", "type": "Arma", "qty": 1, "desc": "1d6 danni perforanti, gittata 24/96m.", "weight": 2.0},
            {"name": "Frecce", "type": "Munizioni", "qty": 20, "desc": "Frecce per arco corto o lungo.", "weight": 0.05},
            {"name": "Due Pugnali", "type": "Arma", "qty": 2, "desc": "1d4 danni perforanti ciascuno.", "weight": 1.0},
            {"name": "Strumenti da Scasso", "type": "Strumenti", "qty": 1, "desc": "Grimaldelli per forzare serrature e disinnescare trappole.", "weight": 1.0},
            {"name": "Zaino da Scassinatore", "type": "Equipaggiamento", "qty": 1, "desc": "Piede di porco, martello, 10 chiodi, corda 15m, razioni.", "weight": 12.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 15, "desc": "Monete iniziali (15 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Chierico": {
        "ac_base": 14, # Cotta a Scaglie 14 + max 2 Des
        "ac_shield": 2, # Scudo
        "items": [
            {"name": "Cotta a Scaglie", "type": "Armatura", "qty": 1, "desc": "Armatura media. CA 14 + mod Destrezza (max +2).", "weight": 45.0},
            {"name": "Mazza da Guerra", "type": "Arma", "qty": 1, "desc": "1d6 danni schiaccianti.", "weight": 4.0},
            {"name": "Scudo con Emblema", "type": "Scudo", "qty": 1, "desc": "+2 CA quando impugnato.", "weight": 6.0},
            {"name": "Balestra Leggera", "type": "Arma", "qty": 1, "desc": "1d8 danni perforanti, gittata 24/96m.", "weight": 5.0},
            {"name": "Dardi da Balestra", "type": "Munizioni", "qty": 20, "desc": "Munizioni per balestra.", "weight": 0.075},
            {"name": "Simbolo Sacro", "type": "Focus", "qty": 1, "desc": "Amuleto consacrato della divinità.", "weight": 1.0},
            {"name": "Zaino da Sacerdote", "type": "Equipaggiamento", "qty": 1, "desc": "Coperta, candele, incensiere, vesti, razioni, borraccia.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Barbaro": {
        "ac_base": 10, # Difesa senz'armatura: 10 + Des + Cos
        "ac_shield": 0,
        "items": [
            {"name": "Ascia Bipenne", "type": "Arma", "qty": 1, "desc": "1d12 danni taglienti, pesante, due mani.", "weight": 7.0},
            {"name": "Due Asce da Lancio", "type": "Arma", "qty": 2, "desc": "1d6 danni taglienti ciascuna, gittata 6/18m.", "weight": 2.0},
            {"name": "Quattro Giavellotti", "type": "Arma", "qty": 4, "desc": "1d6 danni perforanti ciascuno, gittata 9/36m.", "weight": 2.0},
            {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "desc": "Sacco a pelo, torce, razioni, acciarino, corda 15m.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Bardo": {
        "ac_base": 11, # Corazza di cuoio 11 + Des
        "ac_shield": 0,
        "items": [
            {"name": "Corazza di Cuoio", "type": "Armatura", "qty": 1, "desc": "Armatura leggera. CA 11 + mod Destrezza.", "weight": 10.0},
            {"name": "Stocco", "type": "Arma", "qty": 1, "desc": "1d8 danni perforanti, accurata.", "weight": 2.0},
            {"name": "Pugnale", "type": "Arma", "qty": 1, "desc": "1d4 danni perforanti.", "weight": 1.0},
            {"name": "Liuto", "type": "Strumento", "qty": 1, "desc": "Strumento musicale e focus per incantesimi del bardo.", "weight": 2.0},
            {"name": "Zaino da Intrattenitore", "type": "Equipaggiamento", "qty": 1, "desc": "Costume, candele, razioni, borraccia.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 15, "desc": "Monete iniziali (15 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Druido": {
        "ac_base": 11, # Cuoio 11 + Des
        "ac_shield": 2, # Scudo di legno
        "items": [
            {"name": "Corazza di Cuoio", "type": "Armatura", "qty": 1, "desc": "Armatura leggera. CA 11 + mod Destrezza.", "weight": 10.0},
            {"name": "Scudo di Legno", "type": "Scudo", "qty": 1, "desc": "+2 CA quando impugnato (non di metallo).", "weight": 5.0},
            {"name": "Scimitarra", "type": "Arma", "qty": 1, "desc": "1d6 danni taglienti, accurata, leggera.", "weight": 3.0},
            {"name": "Focus Druidico", "type": "Focus", "qty": 1, "desc": "Bastone di tasso o ramoscello di vischio.", "weight": 1.0},
            {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "desc": "Sacco a pelo, razioni, borraccia, corda 15m.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Monaco": {
        "ac_base": 10, # Senz'armatura: 10 + Des + Sag
        "ac_shield": 0,
        "items": [
            {"name": "Spada Corta", "type": "Arma", "qty": 1, "desc": "1d6 danni perforanti, accurata, leggera.", "weight": 2.0},
            {"name": "Dieci Dardi", "type": "Arma", "qty": 10, "desc": "1d4 danni perforanti ciascuno, gittata 6/18m.", "weight": 0.25},
            {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "desc": "Sacco a pelo, razioni, borraccia, acciarino.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 5, "desc": "Monete iniziali (5 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Paladino": {
        "ac_base": 16, # Cotta di maglia
        "ac_shield": 2, # Scudo
        "items": [
            {"name": "Cotta di Maglia", "type": "Armatura", "qty": 1, "desc": "Armatura pesante. CA 16.", "weight": 55.0},
            {"name": "Spada Lunga", "type": "Arma", "qty": 1, "desc": "1d8 (versatile 1d10) danni taglienti.", "weight": 3.0},
            {"name": "Scudo con Emblema", "type": "Scudo", "qty": 1, "desc": "+2 CA quando impugnato.", "weight": 6.0},
            {"name": "Cinque Giavellotti", "type": "Arma", "qty": 5, "desc": "1d6 danni perforanti ciascuno, gittata 9/36m.", "weight": 2.0},
            {"name": "Simbolo Sacro", "type": "Focus", "qty": 1, "desc": "Emblema consacrato.", "weight": 1.0},
            {"name": "Zaino da Sacerdote", "type": "Equipaggiamento", "qty": 1, "desc": "Coperta, candele, incensiere, vesti, razioni.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Ranger": {
        "ac_base": 14, # Cotta a Scaglie 14 + max 2 Des
        "ac_shield": 0,
        "items": [
            {"name": "Cotta a Scaglie", "type": "Armatura", "qty": 1, "desc": "Armatura media. CA 14 + mod Destrezza (max +2).", "weight": 45.0},
            {"name": "Due Spade Corte", "type": "Arma", "qty": 2, "desc": "1d6 danni perforanti ciascuna, accurate, leggere.", "weight": 2.0},
            {"name": "Arco Lungo", "type": "Arma", "qty": 1, "desc": "1d8 danni perforanti, gittata 45/180m, pesante, due mani.", "weight": 2.0},
            {"name": "Frecce", "type": "Munizioni", "qty": 20, "desc": "Faretra con 20 frecce.", "weight": 0.05},
            {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "desc": "Sacco a pelo, corda 15m, torce, razioni, borraccia.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Stregone": {
        "ac_base": 10, # 10 + Des
        "ac_shield": 0,
        "items": [
            {"name": "Balestra Leggera", "type": "Arma", "qty": 1, "desc": "1d8 danni perforanti, gittata 24/96m.", "weight": 5.0},
            {"name": "Dardi da Balestra", "type": "Munizioni", "qty": 20, "desc": "Munizioni per balestra.", "weight": 0.075},
            {"name": "Due Pugnali", "type": "Arma", "qty": 2, "desc": "1d4 danni perforanti ciascuno.", "weight": 1.0},
            {"name": "Focus Arcano (Cristallo)", "type": "Focus", "qty": 1, "desc": "Focus arcano per incanalare la magia innata.", "weight": 1.0},
            {"name": "Zaino da Esploratore Sotterraneo", "type": "Equipaggiamento", "qty": 1, "desc": "Torce, acciarino, razioni, corda 15m.", "weight": 12.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    },
    "Warlock": {
        "ac_base": 11, # Corazza di cuoio 11 + Des
        "ac_shield": 0,
        "items": [
            {"name": "Corazza di Cuoio", "type": "Armatura", "qty": 1, "desc": "Armatura leggera. CA 11 + mod Destrezza.", "weight": 10.0},
            {"name": "Balestra Leggera", "type": "Arma", "qty": 1, "desc": "1d8 danni perforanti, gittata 24/96m.", "weight": 5.0},
            {"name": "Dardi da Balestra", "type": "Munizioni", "qty": 20, "desc": "Munizioni per balestra.", "weight": 0.075},
            {"name": "Due Pugnali", "type": "Arma", "qty": 2, "desc": "1d4 danni perforanti ciascuno.", "weight": 1.0},
            {"name": "Focus Arcano (Verga)", "type": "Focus", "qty": 1, "desc": "Canale del patto con l'entità ultraterrena.", "weight": 2.0},
            {"name": "Zaino da Studioso", "type": "Equipaggiamento", "qty": 1, "desc": "Libro, inchiostro, penna, pergamene, razioni.", "weight": 10.0},
            {"name": "Monete d'Oro", "type": "Valuta", "qty": 10, "desc": "Monete iniziali (10 MO).", "weight": 0.02, "_coins_synced": True}
        ]
    }
}

# Incantesimi e Trucchetti iniziali per classe (Livello 1)
CLASS_STARTING_SPELLS = {
    "Mago": {
        "slots_lvl1": 2,
        "spells": [
            {"name": "Dardo di Fuoco", "level": 0, "time": "1 Azione", "range": "36m", "desc": "Scaglia un dardo infuocato: tiro per colpire a distanza, 1d10 danni da fuoco."},
            {"name": "Raggio di Gelo", "level": 0, "time": "1 Azione", "range": "18m", "desc": "1d8 danni da freddo e riduce la velocità del bersaglio di 3m fino al prossimo turno."},
            {"name": "Mano Magica", "level": 0, "time": "1 Azione", "range": "9m", "desc": "Crea una mano spettrale che può manipolare oggetti fino a 4.5kg."},
            {"name": "Dardo Incantato", "level": 1, "time": "1 Azione", "range": "36m", "desc": "Crea 3 dardi luminosi che colpiscono automaticamente infliggendo 1d4+1 danni da forza ciascuno."},
            {"name": "Scudo", "level": 1, "time": "1 Reazione", "range": "Personale", "desc": "Conferisce +5 CA fino all'inizio del tuo prossimo turno e annulla i dardi incantati."},
            {"name": "Armatura Magica", "level": 1, "time": "1 Azione", "range": "Contatto", "desc": "La CA base di una creatura consenziente senz'armatura diventa 13 + mod Destrezza per 8 ore."},
            {"name": "Mani Brucianti", "level": 1, "time": "1 Azione", "range": "Cono 4.5m", "desc": "Fiamme escono dalle tue dita infliggendo 3d6 danni da fuoco (TS Destrezza dimezza)."},
            {"name": "Sonno", "level": 1, "time": "1 Azione", "range": "27m", "desc": "Addormenta creature per un totale di 5d8 Punti Ferita per 1 minuto senza tiro salvezza."},
            {"name": "Individuazione del Magico", "level": 1, "time": "1 Azione (Rituale)", "range": "Personale", "desc": "Percepisci la presenza e la scuola della magia entro 9m per 10 minuti."}
        ]
    },
    "Chierico": {
        "slots_lvl1": 2,
        "spells": [
            {"name": "Fiamma Sacra", "level": 0, "time": "1 Azione", "range": "18m", "desc": "Radiazione luminosa discende sul nemico: 1d8 danni radiosi (TS Destrezza nega)."},
            {"name": "Guida", "level": 0, "time": "1 Azione", "range": "Contatto", "desc": "Il bersaglio aggiunge 1d4 a una prova di caratteristica a sua scelta entro 1 minuto."},
            {"name": "Taumaturgia", "level": 0, "time": "1 Azione", "range": "9m", "desc": "Manifesta piccoli prodigi sovrannaturali, sussurri ultraterreni o amplifica la voce."},
            {"name": "Cura Ferite", "level": 1, "time": "1 Azione", "range": "Contatto", "desc": "Una creatura recupera 1d8 + mod Saggezza Punti Ferita."},
            {"name": "Parola Guaritrice", "level": 1, "time": "1 Azione Bonus", "range": "18m", "desc": "Cura a distanza una creatura visibile per 1d4 + mod Saggezza Punti Ferita."},
            {"name": "Benedizione", "level": 1, "time": "1 Azione", "range": "9m", "desc": "Fino a 3 creature aggiungono 1d4 a tutti i tiri per colpire e tiri salvezza per 1 minuto (Concentrazione)."},
            {"name": "Scudo della Fede", "level": 1, "time": "1 Azione Bonus", "range": "18m", "desc": "Un campo scintillante circonda una creatura conferendo +2 CA per 10 minuti."}
        ]
    },
    "Stregone": {
        "slots_lvl1": 2,
        "spells": [
            {"name": "Dardo di Fuoco", "level": 0, "time": "1 Azione", "range": "36m", "desc": "Scaglia fiamme per 1d10 danni da fuoco a distanza."},
            {"name": "Luce", "level": 0, "time": "1 Azione", "range": "Contatto", "desc": "Un oggetto tocca emette luce intensa per 6m e fioca per altri 6m per 1 ora."},
            {"name": "Illusione Minore", "level": 0, "time": "1 Azione", "range": "9m", "desc": "Crea un suono o un'immagine ottica statica entro un cubo di 1.5m per 1 minuto."},
            {"name": "Spruzzo Velenoso", "level": 0, "time": "1 Azione", "range": "3m", "desc": "Proietta gas nocivo infliggendo 1d12 danni da veleno (TS Costituzione nega)."},
            {"name": "Dardo Incantato", "level": 1, "time": "1 Azione", "range": "36m", "desc": "3 dardi da 1d4+1 danni da forza ciascuno infallibili."},
            {"name": "Onda Tonante", "level": 1, "time": "1 Azione", "range": "Cubo 4.5m", "desc": "2d8 danni da tuono e spinge indietro di 3m le creature che falliscono il TS Costituzione."}
        ]
    },
    "Warlock": {
        "slots_lvl1": 1,
        "spells": [
            {"name": "Deflagrazione Occulta", "level": 0, "time": "1 Azione", "range": "36m", "desc": "Un raggio di energia crepitante infligge 1d10 danni da forza a distanza."},
            {"name": "Tocco Gelido", "level": 0, "time": "1 Azione", "range": "36m", "desc": "1d8 danni necrotici e impedisce al bersaglio di recuperare PF fino al prossimo turno."},
            {"name": "Sortilegio", "level": 1, "time": "1 Azione Bonus", "range": "27m", "desc": "Maledice un nemico: subisce 1d6 danni necrotici extra ogni volta che lo colpisci."},
            {"name": "Braccia di Hadar", "level": 1, "time": "1 Azione", "range": "Raggio 3m", "desc": "Tentacoli oscuri infliggono 2d6 danni da forza e negano le reazioni (TS Forza)."}
        ]
    },
    "Bardo": {
        "slots_lvl1": 2,
        "spells": [
            {"name": "Beffa Crudele", "level": 0, "time": "1 Azione", "range": "18m", "desc": "Insulti intrisi di magia infliggono 1d4 psichici e svantaggio al prossimo attacco (TS Saggezza)."},
            {"name": "Luci Danzanti", "level": 0, "time": "1 Azione", "range": "36m", "desc": "Crea fino a 4 luci simili a torce o lanterne che si muovono a tuo comando."},
            {"name": "Cura Ferite", "level": 1, "time": "1 Azione", "range": "Contatto", "desc": "Ripristina 1d8 + mod Carisma Punti Ferita."},
            {"name": "Risata Incontenibile di Tasha", "level": 1, "time": "1 Azione", "range": "9m", "desc": "La creatura cade prona, incapace di agire e colta da riso compulsivo (TS Saggezza)."},
            {"name": "Sonno", "level": 1, "time": "1 Azione", "range": "27m", "desc": "Addormenta 5d8 PF di creature per 1 minuto."},
            {"name": "Onda Tonante", "level": 1, "time": "1 Azione", "range": "Cubo 4.5m", "desc": "2d8 danni da tuono in un'area cubica di 4.5m."}
        ]
    },
    "Druido": {
        "slots_lvl1": 2,
        "spells": [
            {"name": "Randello Magico", "level": 0, "time": "1 Azione Bonus", "range": "Contatto", "desc": "Un bastone o clava diventa magico, usa Saggezza per colpire e infligge 1d8 + mod Sag."},
            {"name": "Produrre Fiamma", "level": 0, "time": "1 Azione", "range": "Personale/9m", "desc": "Una fiamma appare nella tua mano fa luce o può essere lanciata per 1d8 danni da fuoco."},
            {"name": "Cura Ferite", "level": 1, "time": "1 Azione", "range": "Contatto", "desc": "Ripristina 1d8 + mod Saggezza Punti Ferita."},
            {"name": "Intralciare", "level": 1, "time": "1 Azione", "range": "27m", "desc": "Erbe e viticci trattengono le creature in un quadrato di 6m (TS Forza)."},
            {"name": "Bacche Benefiche", "level": 1, "time": "1 Azione", "range": "Contatto", "desc": "Crea 10 bacche magiche: ciascuna cura 1 PF e fornisce nutrimento per un giorno intero."}
        ]
    }
}

# Incantesimi e tratti razziali aggiuntivi
RACE_STARTING_SPELLS = {
    "Tiefling": [
        {"name": "Taumaturgia (Razza)", "level": 0, "time": "1 Azione", "range": "9m", "desc": "Tratto Eredità Infernale: manifesta prodigi soprannaturali e amplifica la voce."}
    ],
    "Elfo": [
        {"name": "Luce (Razza)", "level": 0, "time": "1 Azione", "range": "Contatto", "desc": "Tratto Trucchetto Elfico (Alto Elfo): un oggetto toccato emette luce intensa per 6m e fioca per altri 6m per 1 ora."}
    ],
    "Gnomo": [
        {"name": "Illusione Minore (Razza)", "level": 0, "time": "1 Azione", "range": "9m", "desc": "Tratto Illusione Naturale (Gnomo delle Foreste): crea un suono o un'immagine illusoria."}
    ],
    "Draconide": [
        {"name": "Arma a Soffio (Razza)", "level": 0, "time": "1 Azione", "range": "Cono 4.5m / Linea 9m", "desc": "Tratto Ascendenza Draconica: esala energia distruttiva infliggendo 2d6 danni (TS dimezza)."}
    ]
}

RACE_DEFAULT_SKILLS = {
    "Elfo": ["Percezione"],
    "Elf": ["Percezione"],
    "Mezzorco": ["Intimidire"],
    "Half-Orc": ["Intimidire"]
}

# Competenze nelle Abilità (Skills) standard 5e per ogni classe
CLASS_DEFAULT_SKILLS = {
    "Guerriero": ["Atletica", "Percezione"],
    "Fighter": ["Atletica", "Percezione"],
    "Ladro": ["Furtività", "Acrobazia", "Prestidigitazione", "Indagare"],
    "Rogue": ["Furtività", "Acrobazia", "Prestidigitazione", "Indagare"],
    "Mago": ["Arcano", "Storia"],
    "Wizard": ["Arcano", "Storia"],
    "Chierico": ["Religione", "Intuizione"],
    "Cleric": ["Religione", "Intuizione"],
    "Barbaro": ["Atletica", "Percezione"],
    "Barbarian": ["Atletica", "Percezione"],
    "Bardo": ["Intrattenere", "Inganno", "Persuasione"],
    "Bard": ["Intrattenere", "Inganno", "Persuasione"],
    "Paladino": ["Atletica", "Persuasione"],
    "Paladin": ["Atletica", "Persuasione"],
    "Ranger": ["Sopravvivenza", "Furtività", "Percezione"],
    "Druido": ["Natura", "Sopravvivenza"],
    "Druid": ["Natura", "Sopravvivenza"],
    "Monaco": ["Acrobazia", "Atletica"],
    "Monk": ["Acrobazia", "Atletica"],
    "Stregone": ["Arcano", "Inganno"],
    "Sorcerer": ["Arcano", "Inganno"],
    "Warlock": ["Arcano", "Inganno"]
}

# Equipaggiamento iniziale predefinito della campagna (impostato dal Master)
DEFAULT_CAMPAIGN_STARTER_KIT = [
    {
        "name": "Pozione di Cura",
        "type": "Consumabile",
        "qty": 2,
        "desc": "Ripristina 2d4 + 2 Punti Ferita quando bevuta.",
        "weight": 1.0
    },
    {
        "name": "Mappa della Regione",
        "type": "Documento",
        "qty": 1,
        "desc": "Mappa geografica dei territori della campagna consegnata dal Dungeon Master.",
        "weight": 0.5
    },
    {
        "name": "Lettera di Ingaggio del Master",
        "type": "Documento",
        "qty": 1,
        "desc": "La pergamena con il sigillo ufficiale che vi affida l'incarico iniziale della campagna.",
        "weight": 0.1
    },
    {
        "name": "Borsa di Monete Extra",
        "type": "Valuta",
        "qty": 15,
        "desc": "15 Monete d'Oro fornite dal Master come fondo iniziale per la spedizione.",
        "weight": 0.3
    }
]

CAMPAIGN_STARTER_FILE = "campaign_starter_kit.json"

def get_campaign_starter_kit():
    """Carica l'equipaggiamento iniziale della campagna dal file o usa quello di default."""
    from common.file_utils import load_json
    data = load_json(CAMPAIGN_STARTER_FILE, default=None)
    if isinstance(data, list) and len(data) > 0:
        return data
    return [item.copy() for item in DEFAULT_CAMPAIGN_STARTER_KIT]

def save_campaign_starter_kit(items):
    """Salva la lista di oggetti configurata dal DM per l'equipaggiamento della campagna."""
    try:
        from common.file_utils import atomic_save_json
        atomic_save_json(CAMPAIGN_STARTER_FILE, items, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print("Errore salvataggio starter kit campagna:", e)
        return False

def calculate_initial_ac(char_class, attributes, has_shield=False):
    """Calcola la Classe Armatura (CA) iniziale secondo le regole di D&D 5e."""
    des = attributes.get("DES", 10)
    cos = attributes.get("COS", 10)
    sag = attributes.get("SAG", 10)
    
    des_mod = (des - 10) // 2
    cos_mod = (cos - 10) // 2
    sag_mod = (sag - 10) // 2
    
    shield_bonus = 2 if has_shield else 0
    
    if char_class == "Guerriero" or char_class == "Paladino":
        return 16 + shield_bonus # Cotta di maglia (AC fissa 16) + eventuale scudo
    elif char_class == "Chierico" or char_class == "Ranger":
        return 14 + min(2, max(0, des_mod)) + shield_bonus # Cotta a scaglie 14 + max 2 Des
    elif char_class in ["Ladro", "Bardo", "Warlock", "Druido"]:
        return 11 + des_mod + shield_bonus # Cuoio 11 + Des
    elif char_class == "Barbaro":
        return 10 + des_mod + cos_mod + shield_bonus # Senz'armatura: 10 + Des + Cos
    elif char_class == "Monaco":
        return 10 + des_mod + sag_mod # Senz'armatura: 10 + Des + Sag
    else:
        # Mago, Stregone
        return 10 + des_mod

def apply_class_and_race_starter_kit(char_obj_or_dict):
    """
    Assegna equipaggiamento, armi, armature e incantesimi iniziali 
    in base alla classe e alla razza del personaggio.
    Funziona sia con un oggetto Character che con un dizionario full_sheet.
    """
    is_obj = not isinstance(char_obj_or_dict, dict)
    
    def get_attr(key, default=None):
        if is_obj:
            return getattr(char_obj_or_dict, key, default)
        return char_obj_or_dict.get(key, default)
        
    def set_attr(key, value):
        if is_obj:
            setattr(char_obj_or_dict, key, value)
        else:
            char_obj_or_dict[key] = value

    char_class = get_attr("char_class", "") or get_attr("character_class", "")
    race = get_attr("race", "")
    attributes = get_attr("attributes", {})
    
    # 1. Equipaggiamento di classe
    kit_info = CLASS_STARTING_KITS.get(char_class)
    if kit_info:
        items = [item.copy() for item in kit_info["items"]]
        has_shield = kit_info.get("ac_shield", 0) > 0
        
        # Inserisci gli oggetti nella griglia inventario
        grid = get_attr("inventory_grid", [None] * 25)
        if not isinstance(grid, list):
            grid = [None] * 25
        
        # Pulisci o aggiungi (se c'era solo il placeholder "Zaino Base", rimuovilo)
        cleaned_grid = []
        for it in grid:
            if it and it.get("name") != "Zaino Base":
                cleaned_grid.append(it)
                
        # Aggiungi i nuovi oggetti
        for item in items:
            cleaned_grid.append(item)
            
        # Riempi fino ad almeno 25 slot
        while len(cleaned_grid) < 25:
            cleaned_grid.append(None)
            
        set_attr("inventory_grid", cleaned_grid)
        
        # Riporta e assegna le monete del kit nella tabella valute
        cur = get_attr("currency", {})
        if not isinstance(cur, dict):
            cur = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        for itm in items:
            if itm.get("type") == "Valuta" or "monet" in itm.get("name", "").lower():
                cur["MO"] = cur.get("MO", 0) + itm.get("qty", 10)
                itm["_coins_synced"] = True
        set_attr("currency", cur)
        
        # Calcola e imposta la Classe Armatura (CA)
        computed_ac = calculate_initial_ac(char_class, attributes, has_shield=has_shield)
        set_attr("ac", computed_ac)

    # 2. Incantesimi di classe e razza
    spellbook = get_attr("spellbook", [])
    if not isinstance(spellbook, list):
        spellbook = []
        
    existing_spell_names = {s.get("name") for s in spellbook if isinstance(s, dict)}
    
    # Aggiungi incantesimi di classe
    class_spells_info = CLASS_STARTING_SPELLS.get(char_class)
    if class_spells_info:
        for sp in class_spells_info.get("spells", []):
            if sp.get("name") not in existing_spell_names:
                spellbook.append(sp.copy())
                existing_spell_names.add(sp.get("name"))
                
        # Inizializza gli slot incantesimo
        slots_count = class_spells_info.get("slots_lvl1", 0)
        spell_slots = get_attr("spell_slots", {})
        if not isinstance(spell_slots, dict):
            spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
            
        if "1" not in spell_slots or not isinstance(spell_slots["1"], dict):
            spell_slots["1"] = {"max": slots_count, "current": slots_count}
        else:
            spell_slots["1"]["max"] = max(spell_slots["1"].get("max", 0), slots_count)
            spell_slots["1"]["current"] = spell_slots["1"]["max"]
            
        set_attr("spell_slots", spell_slots)
        
    # Aggiungi incantesimi/tratti razziali
    race_spells = RACE_STARTING_SPELLS.get(race, [])
    for sp in race_spells:
        if sp.get("name") not in existing_spell_names:
            spellbook.append(sp.copy())
            existing_spell_names.add(sp.get("name"))

    # Aggiungi competenze abilità iniziali di classe se non ancora definite
    skills = get_attr("skills", None)
    if isinstance(skills, dict):
        total_p = sum(skills.values()) if skills else 0
        if total_p == 0 and char_class in CLASS_DEFAULT_SKILLS:
            for sk in CLASS_DEFAULT_SKILLS[char_class]:
                if sk in skills:
                    skills[sk] = 2 if char_class in ["Ladro", "Rogue"] and sk in ["Furtività", "Prestidigitazione"] else 1
        if race in RACE_DEFAULT_SKILLS:
            for r_sk in RACE_DEFAULT_SKILLS[race]:
                if r_sk in skills and skills[r_sk] == 0:
                    skills[r_sk] = 1
        set_attr("skills", skills)

    set_attr("spellbook", spellbook)
    set_attr("starting_kit_applied", True)
    return char_obj_or_dict

def apply_campaign_starter_kit(char_obj_or_dict, campaign_items=None):
    """
    Assegna l'equipaggiamento iniziale della campagna (deciso dal DM)
    al personaggio.
    """
    if campaign_items is None:
        campaign_items = get_campaign_starter_kit()
        
    is_obj = not isinstance(char_obj_or_dict, dict)
    
    def get_attr(key, default=None):
        if is_obj:
            return getattr(char_obj_or_dict, key, default)
        return char_obj_or_dict.get(key, default)
        
    def set_attr(key, value):
        if is_obj:
            setattr(char_obj_or_dict, key, value)
        else:
            char_obj_or_dict[key] = value

    grid = get_attr("inventory_grid", [None] * 25)
    if not isinstance(grid, list):
        grid = [None] * 25

    # Cerca slot vuoti dove inserire gli oggetti della campagna
    for item in campaign_items:
        placed = False
        for i in range(len(grid)):
            if grid[i] is None:
                grid[i] = item.copy()
                placed = True
                break
        if not placed:
            grid.append(item.copy())

    set_attr("inventory_grid", grid)
    set_attr("campaign_starter_received", True)
    return char_obj_or_dict

# Pesi standard D&D 5e (RAW) per oggetti ed equipaggiamento comune (in lbs)
STANDARD_ITEM_WEIGHTS = {
    # Armature & Scudi
    "imbottita": 8.0, "cuoio": 10.0, "corazza di cuoio": 10.0, "armatura di cuoio": 10.0, "cuoio borchiato": 13.0,
    "armatura di pelle": 12.0, "corazza di pelle": 12.0, "giaco di maglia": 20.0, "cotta a scaglie": 45.0, "corazza di piastre": 65.0,
    "cotta di maglia": 55.0, "corazza a strisce": 60.0, "armatura di piastre": 65.0,
    "armatura a piastre": 65.0, "scudo": 6.0, "scudo con emblema": 6.0,
    # Armi
    "pugnale": 1.0, "due pugnali": 2.0, "stocco": 2.0, "spada corta": 2.0, "due spade corte": 4.0,
    "spada lunga": 3.0, "spadone": 6.0, "spada a due mani": 6.0, "scimitarra": 3.0,
    "ascia": 4.0, "ascia da battaglia": 4.0, "ascia bipenne": 7.0, "ascia da lancio": 2.0,
    "martello da guerra": 2.0, "maglio": 10.0, "mazza": 4.0, "mazza da guerra": 4.0,
    "giavellotto": 2.0, "giavellotti": 6.0, "cinque giavellotti": 10.0, "lancia": 3.0,
    "alabarda": 6.0, "giusarma": 6.0, "giusarma / alabarda": 6.0, "randello": 2.0, "bastone ferrato": 4.0,
    "arco corto": 2.0, "arco lungo": 2.0, "balestra leggera": 5.0, "balestra pesante": 18.0,
    "balestra a mano": 3.0, "frecce": 1.0, "dardo": 0.25, "dardi": 1.5, "dardi da balestra": 1.5, "dieci dardi": 1.5, "faretra": 1.0,
    # Attrezzi, Zaini & Equipaggiamento
    "zaino da esploratore": 10.0, "zaino da studioso": 10.0, "zaino da scassinatore": 12.0,
    "zaino da sacerdote": 10.0, "zaino da intrattenitore": 8.0, "zaino da diplomatico": 8.0,
    "zaino da esploratore sotterraneo": 12.0, "zaino": 5.0, "sacco a pelo": 7.0,
    "corda di canapa (15m)": 10.0, "corda": 5.0, "torcia": 1.0, "torce (10)": 10.0, "lanterna": 2.0,
    "lanterna a occhio di bue": 2.0, "olio (fiaschetta)": 1.0, "fiaschetta d'olio": 1.0,
    "acciarino": 1.0, "razione": 2.0, "razioni": 10.0, "razioni (10 giorni)": 20.0,
    "borraccia": 5.0, "piede di porco": 5.0, "martello": 3.0, "chiodi da roccia": 2.5,
    "strumenti da scasso": 1.0, "borsa dei componenti": 2.0, "grimorio del mago": 3.0,
    "grimorio": 3.0, "focus arcano": 1.0, "simbolo sacro": 1.0, "borsa da guaritore": 3.0,
    "pozione di guarigione": 0.5, "pozione": 0.5, "antidoto": 0.1, "monete d'oro": 0.2
}

def lookup_standard_weight(item_name: str) -> float:
    """Restituisce il peso standard D&D 5e in lbs per un oggetto in base al nome."""
    if not item_name or not isinstance(item_name, str):
        return 0.0
    name_clean = item_name.strip().lower()
    
    # Ricerca esatta
    if name_clean in STANDARD_ITEM_WEIGHTS:
        return STANDARD_ITEM_WEIGHTS[name_clean]
        
    # Ricerca parziale ordinata per lunghezza chiave decrescente e confini di parola
    import re
    for k in sorted(STANDARD_ITEM_WEIGHTS.keys(), key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", name_clean):
            return STANDARD_ITEM_WEIGHTS[k]
            
    return 1.0  # Peso simbolico di default se oggetto comune non censito



# --- CONTENUTI DETTAGLIATI DEI PACK INIZIALI 5E (SPACCHETTABILI) ---
STARTER_PACK_CONTENTS = {
    "zaino da esploratore": [
        {"name": "Sacco a Pelo", "type": "Equipaggiamento", "qty": 1, "weight": 7.0, "container": "backpack", "desc": "Un caldo sacco a pelo per riposare all'aperto."},
        {"name": "Acciarino", "type": "Equipaggiamento", "qty": 1, "weight": 1.0, "container": "backpack", "desc": "Pietra focaia e acciarino per accendere fuochi."},
        {"name": "Torce", "type": "Consumabile", "qty": 10, "weight": 1.0, "container": "backpack", "desc": "10 torce. Ciascuna brucia per 1 ora illuminando 6m di luce intensa e 6m fioca."},
        {"name": "Razioni da Viaggio", "type": "Consumabile", "qty": 10, "weight": 2.0, "container": "backpack", "desc": "10 razioni giornaliere di cibo secco e nutriente."},
        {"name": "Corda di Canapa (15m)", "type": "Equipaggiamento", "qty": 1, "weight": 10.0, "container": "backpack", "desc": "Corda resistente da 15 metri (50 ft)."},
        {"name": "Borraccia", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Contiene fino a 2 litri d'acqua fresca."}
    ],
    "zaino da studioso": [
        {"name": "Libro di Nozioni", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Tomo di appunti accademici e teoria."},
        {"name": "Inchiostro e Penna d'Oca", "type": "Equipaggiamento", "qty": 1, "weight": 0.5, "container": "backpack", "desc": "Boccetta di inchiostro nero e penna."},
        {"name": "Fogli di Pergamena", "type": "Consumabile", "qty": 10, "weight": 0.1, "container": "backpack", "desc": "10 fogli di pergamena vergine per appunti o incantesimi."},
        {"name": "Borsa di Sabbia", "type": "Equipaggiamento", "qty": 1, "weight": 1.0, "container": "backpack", "desc": "Per asciugare l'inchiostro fresco."},
        {"name": "Razioni da Viaggio", "type": "Consumabile", "qty": 5, "weight": 2.0, "container": "backpack", "desc": "5 razioni giornaliere di cibo."},
        {"name": "Borraccia", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Contiene fino a 2 litri d'acqua."}
    ],
    "zaino da scassinatore": [
        {"name": "Piede di Porco", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Fornisce vantaggio alle prove di Forza per forzare porte e casse."},
        {"name": "Martello", "type": "Equipaggiamento", "qty": 1, "weight": 3.0, "container": "backpack", "desc": "Martello compatto da carpentiere."},
        {"name": "Chiodi da Roccia", "type": "Consumabile", "qty": 10, "weight": 0.25, "container": "backpack", "desc": "10 chiodi per ancoraggi e scalata."},
        {"name": "Corda di Canapa (15m)", "type": "Equipaggiamento", "qty": 1, "weight": 10.0, "container": "backpack", "desc": "Corda resistente da 15 metri."},
        {"name": "Candele", "type": "Consumabile", "qty": 5, "weight": 0.1, "container": "backpack", "desc": "5 candele. Ciascuna brucia per 1 ora (1.5m luce intensa)."},
        {"name": "Razioni da Viaggio", "type": "Consumabile", "qty": 5, "weight": 2.0, "container": "backpack", "desc": "5 razioni giornaliere di cibo."},
        {"name": "Acciarino", "type": "Equipaggiamento", "qty": 1, "weight": 1.0, "container": "backpack", "desc": "Per accendere il fuoco."}
    ],
    "zaino da sacerdote": [
        {"name": "Coperta", "type": "Equipaggiamento", "qty": 1, "weight": 3.0, "container": "backpack", "desc": "Coperta pesante di lana."},
        {"name": "Candele", "type": "Consumabile", "qty": 10, "weight": 0.1, "container": "backpack", "desc": "10 candele benedette."},
        {"name": "Acciarino", "type": "Equipaggiamento", "qty": 1, "weight": 1.0, "container": "backpack", "desc": "Per accendere candele e fuochi."},
        {"name": "Incensiere", "type": "Equipaggiamento", "qty": 1, "weight": 2.0, "container": "backpack", "desc": "Incensiere per riti sacri con incenso."},
        {"name": "Vesti da Cerimonia", "type": "Equipaggiamento", "qty": 1, "weight": 4.0, "container": "backpack", "desc": "Abiti sacri della propria fede."},
        {"name": "Razioni da Viaggio", "type": "Consumabile", "qty": 2, "weight": 2.0, "container": "backpack", "desc": "2 razioni di cibo."},
        {"name": "Borraccia", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Borraccia d'acqua."}
    ],
    "zaino da esploratore sotterraneo": [
        {"name": "Piede di Porco", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Vantaggio alle prove di Forza per forzare aperture."},
        {"name": "Martello", "type": "Equipaggiamento", "qty": 1, "weight": 3.0, "container": "backpack", "desc": "Martello da esplorazione."},
        {"name": "Chiodi da Roccia", "type": "Consumabile", "qty": 10, "weight": 0.25, "container": "backpack", "desc": "10 chiodi di metallo."},
        {"name": "Torce", "type": "Consumabile", "qty": 10, "weight": 1.0, "container": "backpack", "desc": "10 torce da dungeon."},
        {"name": "Acciarino", "type": "Equipaggiamento", "qty": 1, "weight": 1.0, "container": "backpack", "desc": "Acciarino e pietra focaia."},
        {"name": "Razioni da Viaggio", "type": "Consumabile", "qty": 10, "weight": 2.0, "container": "backpack", "desc": "10 razioni nutrienti."},
        {"name": "Borraccia", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Borraccia da 2 litri."},
        {"name": "Corda di Canapa (15m)", "type": "Equipaggiamento", "qty": 1, "weight": 10.0, "container": "backpack", "desc": "Corda da 15 metri."}
    ],
    "zaino da intrattenitore": [
        {"name": "Sacco a Pelo", "type": "Equipaggiamento", "qty": 1, "weight": 7.0, "container": "backpack", "desc": "Sacco a pelo da viaggio."},
        {"name": "Costumi di Scena", "type": "Equipaggiamento", "qty": 2, "weight": 4.0, "container": "backpack", "desc": "Due completi teatrali appariscenti."},
        {"name": "Candele", "type": "Consumabile", "qty": 5, "weight": 0.1, "container": "backpack", "desc": "5 candele."},
        {"name": "Razioni da Viaggio", "type": "Consumabile", "qty": 5, "weight": 2.0, "container": "backpack", "desc": "5 razioni di cibo."},
        {"name": "Borraccia", "type": "Equipaggiamento", "qty": 1, "weight": 5.0, "container": "backpack", "desc": "Borraccia per bevande."},
        {"name": "Trucchi e Cosmetici", "type": "Equipaggiamento", "qty": 1, "weight": 1.0, "container": "backpack", "desc": "Set per trucco e travestimento rapido."}
    ]
}

def get_pack_contents(pack_name: str):
    """Restituisce la lista di oggetti contenuti in uno zaino/kit iniziale 5e se apribile, altrimenti None."""
    if not pack_name or not isinstance(pack_name, str):
        return None
    p_lower = pack_name.strip().lower()
    for k, v in STARTER_PACK_CONTENTS.items():
        if k in p_lower:
            return [it.copy() for it in v]
    return None
