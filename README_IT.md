# D&D OmniCompanion 🐉🎲

> 🌐 **Language / Lingua**: 🇬🇧 **[English (README.md)](README.md)** | 🇮🇹 **[Italiano (README_IT.md)](README_IT.md)**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Ruleset: D&D 5e](https://img.shields.io/badge/ruleset-D%26D%205e-red.svg)](https://dnd.wizards.com/)
[![UI: ttkbootstrap](https://img.shields.io/badge/ui-ttkbootstrap-orange.svg)](https://ttkbootstrap.readthedocs.io/)
[![Multiplayer: TCP/UDP](https://img.shields.io/badge/networking-TCP%20%2B%20UDP-green.svg)]()
[![Tests: Passing](https://img.shields.io/badge/tests-100%25%20passing-brightgreen.svg)]()
[![Localization: IT / EN](https://img.shields.io/badge/i18n-Italiano%20%7C%20English-blueviolet.svg)]()
[![Units: Imperial / Metric](https://img.shields.io/badge/units-ft%2Fmi%20%7C%20m%2Fkm-informational.svg)]()

**D&D OmniCompanion** è un Virtual Tabletop (VTT) Client-Server all-in-one e un motore di gestione campagne per **Dungeons & Dragons 5a Edizione**, sviluppato in Python. Progettato sia per sessioni al tavolo in presenza sia per il gioco online da remoto, unisce l'automazione completa delle regole D&D 5e, una mappa esagonale interattiva ad alte prestazioni, chat vocale UDP in tempo reale e una suite completa di strumenti per il Dungeon Master.

---

## 📚 Documentazione e Guide

| Documento | 🇮🇹 Versione Italiana | 🇬🇧 English Version |
|---|---|---|
| **README Principale** | [README_IT.md](README_IT.md) | [README.md](README.md) |
| **Guida all'Utilizzo (Manuale Utente)** | [docs/GUIDA_ALL_UTILIZZO.md](docs/GUIDA_ALL_UTILIZZO.md) | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) |
| **Guida Operativa & Architettura di Sistema** | [docs/GUIDA_OPERATIVA.md](docs/GUIDA_OPERATIVA.md) | [docs/OPERATIONAL_GUIDE.md](docs/OPERATIONAL_GUIDE.md) |
| **Regole Homebrew / Campagna** | [manuals/Regole_Personalizzate_Campagna.md](manuals/Regole_Personalizzate_Campagna.md) | [manuals/Custom_Campaign_Rules.md](manuals/Custom_Campaign_Rules.md) |

---

## 🌟 Caratteristiche Principali

### 🗺️ Virtual Tabletop (VTT) Multi-Griglia & Multi-Scala
* **Supporto Multi-Griglia (Esagonale, Quadrata, Senza Griglia)**:
  * **Griglia Esagonale (`hex`)**: La classica griglia tattica esagonale per avventure e dungeon.
  * **Griglia a Scacchiera / Quadrata (`square`)**: Standard D&D 5e con **distanza di Chebyshev** (le diagonali contano come un passo da 5 ft / 1.5 m).
  * **Senza Griglia (`none` / `gridless`)**: Mappe libere senza reticolo con distanze euclidee reali in pixel.
  * **Selettore Griglia Live (`📐 Griglia: ...`)**: Il DM può cambiare la griglia al volo con 1 click.
* **Navigazione Fluida e HUD Moderni**: Canvas infinito con zoom centrato sul cursore, panning con tasto destro/centrale, **HUD Glassmorphism** in basso a sinistra per zoom/centratura rapida e **Initiative Ribbon HUD** in alto al centro durante i combattimenti.
* **Sistema Multi-Scala (DMG p. 14) & Righello Intelligente (`[ 📏 ]`)**:
  * Supporta 4 scale mappa selezionabili in tempo reale dal DM (`📏 Scala`): **Combattimento** ($5\text{ ft} / 1.5\text{ m}$), **Esplorazione** ($1\text{ mi} / 1.5\text{ km}$, $\sim 20\text{ min/hex}$), **Mondo** ($6\text{ mi} / 9\text{ km}$, $2\text{ h/hex}$), e **Scala Personalizzata**.
  * Il **Righello (`[ 📏 ]`)** calcola automaticamente la distanza nella scala e nella griglia della mappa attiva, mostrando tempi di viaggio stimati per marce e viaggi.
* **Doppio Sistema di Unità di Misura (`📏 Unità di Misura`)**: Passaggio istantaneo a runtime tra **Sistema Imperiale (`ft / mi`)** e **Sistema Metrico (`m / km`)**, con conversione automatica di velocità del PG, distanze di movimento, righello e gittate.
* **Taglie Creature (Dimensioni Token)**: Scalatura visiva sul canvas per le 6 categorie 5e (da *Minuscola* $0.5\times$ a *Mastodontica* $3.5\times$) con menu rapido click destro.
* **Livello Nascosto DM (GM Layer)**: Schiera mostri in imboscata o elementi segreti visibili solo al DM (semitrasparenti con anello viola e badge `[GM]`). Isolamento a livello di rete TCP (`GAME_STATE`, `PLAYER_JOINED`, `PLAYER_MOVE`) che impedisce qualunque fuga di dati verso i client dei giocatori.
* **Nebbia di Guerra Dinamica (FoW) & Pennello Manuale**: Esplorazione con Line of Sight (LoS) automatica dei token, visione condivisa del party, scurovisione (`/vision`) e **Pennello Manuale FoW** (raggio 0–3) per rivelare o nascondere stanze con precisione.
* **Terreni Difficili & Pericolosi (D&D 5e)**: Gestione completa di 5 tipologie di terreno (Fango, Ghiaccio, Rovi, Macerie, Palude) con raddoppio del costo di movimento per cella calcolato lungo la traiettoria (`hex_linedraw`), penalità aumentata se Prono (+1), pericoli istantanei (TS Des CD 10 sul Ghiaccio o Prono, 1d4 danni perforanti sui Rovi), pennello DM rapido `[ 🪨 ]`, menu tasto destro ed Editor Mappe con salvataggio JSON.
* **Filtri Atmosferici, Meteo & Oscurità Dinamica**:
  * 6 condizioni ambientali animate: **Sereno**, **Pioggia**, **Tempesta** (fulmini e vento), **Neve** (fiocchi e brina), **Nebbia** (banchi di nebbia volumetrici) e **Oscurità** (buio profondo e vignettatura).
  * Ciclo orario (Giorno, Tramonto, Alba, Notte) con badge HUD reattivo.
  * Luce dinamica di torce e lanterne (`light_radius > 0`) che rischiara l'oscurità squarciando le tenebre con un bagliore dorato.
  * Toggle rapido del DM `[ 🌑 ]` per attivare o disattivare il filtro Oscurità con 1 click o tramite comandi chat (`/darkness`, `/meteo Oscurità`).
* **Lavagna Tattica Condivisa (`[ ✏️ ]` / `[ 🧹 ]`)**: Disegno a mano libera in tempo reale sincronizzato tra DM e giocatori, con pulsante di cancellazione rapida.
* **Illuminazione Dinamica e Aure**: Torce, lanterne, incantesimi di luce e aure magiche proiettano anelli luminosi in tempo reale mentre i token si muovono.
* **Template Incantesimi ad Area (`[ 💥 ]`)**: Sfere, Coni ($60^\circ / 90^\circ$), Linee e Sfere di Oscurità Magica con anteprima geometrica sulla griglia.
* **Ping Animato sulla Mappa**: Click centrale (o strumento `[ 📍 ]`) per inviare un indicatore visivo animato a tutti i giocatori.
* **Badge Condizioni sui Token**: Indicatori visivi renderizzati direttamente sui token (`💀` Morto, `💤` Incosciente, `🔻` Prono, `⚡` Paralizzato/Concentrazione, `🛡️` Schivata, `🤝` Aiuto, `🤢` Avvelenato, `👁️` Accecato, ecc.).

### ⚔️ Motore di Combattimento D&D 5e & Economia del Turno
* **Economia del Turno Contestuale (Esplorazione vs Combattimento)**:
  * **Fuori dal Combattimento (`🧭 Modalità Esplorazione - Movimento Libero`)**: I giocatori si muovono, attaccano e lanciano incantesimi liberamente senza consumare o bloccare i badge di turno; la barra movimento indica la velocità per singolo spostamento.
  * **In Combattimento (`Economia Turno`)**: Tracciamento rigoroso e sincronizzato con il server di **⚡ Azione**, **✨ Azione Bonus**, **🛡️ Reazione** e **👟 Movimento**, con reset automatico all'inizio del proprio turno e a inizio/fine scontro.
* **Successi Critici (`🌟 20 Naturale`) e Fallimenti Critici (`💀 1 Naturale`)**:
  * **Tiri per Colpire**: `20 Naturale` colpisce sempre e raddoppia automaticamente tutti i dadi di danno; `1 Naturale` manca automaticamente.
  * **Tiri Salvezza, Prove di Abilità/Caratteristica e Tiri `1d20`**: Evidenziazione dorata/cremisi in chat e notifiche Toast broadcast (`CRITICAL_ROLL_BROADCAST`) a tutto il tavolo.
* **Vantaggio, Svantaggio e Copertura Dinamica**: Calcolo automatico in base a condizioni (Invisibile, Prono in mischia vs distanza, Accecato, Paralizzato, Schivata, Aiuto) e ostacoli sulla traiettoria (+2 CA per Mezza Copertura).
* **Modificatori Ambientali di Combattimento (Meteo & Terreni Difficili)**:
  * **Meteo (DMG p. 109-110)**: Tempesta violenta e Nebbia fitta impongono Svantaggio agli attacchi a distanza (> 1 esagono); pioggia battente e bufere di neve impongono Svantaggio a lunga gittata.
  * **Terreni Difficili**: Attaccare da superfici instabili (Ghiaccio, Macerie, Palude, Fango) impone Svantaggio; attaccare nemici intralciati nei Rovi o bloccati nel Fango conferisce **Vantaggio**.
  * **Regole Oscurità e Scurovisione (PHB p. 194-195)**: Attaccare dalle tenebre con Scurovisione (o contro un bersaglio che impugna una torcia) conferisce **Vantaggio** (*Attaccante Celato*); attaccare un bersaglio che non si vede impone **Svantaggio**; nell'oscurità totale reciproca vantaggio e svantaggio si annullano.
* **Attacchi di Opportunità Automatizzati**: Rileva quando un combattente esce dalla portata di mischia ostile senza aver usato *Disimpegno*.
* **Controlli di Concentrazione Automatici**: Subire danni con la condizione `Concentrazione` attiva richiede automaticamente un Tiro Salvezza su Costituzione ($\text{CD} = \max(10, \lfloor\text{Danni}/2\rfloor)$).
* **Tiri Salvezza contro la Morte e Morte Istantanea**: Gestione completa a 0 PV (`20 Naturale` = risveglio a 1 PV, `1 Naturale` = 2 fallimenti, 3 successi = Stabilizzato, 3 fallimenti o danno eccessivo $\ge \text{PV Max}$ = Morto).
* **Meccaniche Boss**: Azioni Leggendarie e Resistenze Leggendarie con reset automatico a ogni round.

### 🧙‍♂️ Creazione Personaggio, Scheda PG & Progressione
* **Wizard Stile Baldur's Gate**: Creazione guidata al Livello 1 e Level-Up assistito con recupero automatico di privilegi di classe, dadi vita e slot incantesimo dal Compendio SRD 5e.
* **Sistema Risorse di Classe Speciali**: Popolazione e tracciamento automatico di Punti Ki, Ira, Ispirazione Bardica, Forma Selvatica, Canale di Divinità, Azione Impetuosa, Secondo Fiato, Punti Stregoneria, ecc., con ricarica intelligente al Riposo Breve/Lungo.
* **Hero Summary Card & Scheda Interattiva**:
  * Card riassuntiva sempre visibile nella sidebar con barra PV reattiva, CA, Velocità (in `ft` o `m`) e Iniziativa.
  * Scheda completa divisa in tab: **Combattimento**, **Statistiche & Abilità** (con Competenza e Maestria $2\times\text{PB}$), **Armi & Attacchi**, **Inventario & Ingombro** ($\text{FOR} \times 15\text{ lbs}$), **Grimorio & Slot Incantesimo (1–9)** con dialog di **Upcasting**, **Privilegi & Diario**.
* **Esportazione Scheda Personaggio (PDF Ufficiale D&D 5e e JSON Dati)**: Finestra modale per scegliere tra **PDF Ufficiale** (richiede in input il modello PDF vuoto D&D 5e e compila automaticamente la scheda a 3 pagine pronta per la stampa o la condivisione) e **JSON** (backup grezzo per import/export tra campagne).
* **Approvazione DM Anti-Cheat in Sessione**: Durante le sessioni online, l'aggiunta manuale di valuta o oggetti custom invia una richiesta di approvazione al DM (`🤝 Richiedi Valuta al DM`).
* **Scambi Peer-to-Peer e Macro Hotbar**: Scambio diretto di oggetti/monete con gli alleati e barra rapida a 10 slot personalizzabili.

### 📜 Suite Operativa per il Dungeon Master
* **Calcolatore Difficoltà Incontri Live (DMG p. 82)**: Valutazione in tempo reale (**Banale**, **Facile**, **Medio**, **Difficile**, **Mortale**) con moltiplicatori XP per numero di mostri.
* **Gestore Campagne, Scene & Starter Pack**: Prepara atti, scene collegate a mappe/mostri da schierare con 1 click e configura l'equipaggiamento iniziale automatico per i nuovi PG.
* **Esportazione Registro di Sessione**: Salva l'intera cronologia della sessione (tiri, eventi di combattimento, chat, sussurri) in formato Markdown (`.md`) o HTML da `File -> Esporta Registro di Sessione`.
* **Generatori Procedurali & Handout**: Generatore di Bottino 5e, Generatore Rapido PNG, condivisione di immagini e documenti su pergamena.
* **Manuali PDF Offline & Tavolozza Comandi (`Ctrl+K`)**: Ricerca istantanea su manuali PDF ufficiali indicizzati, regole, mostri, incantesimi e token.
* **Viaggio, Calendario, Meteo, Negozi e Quest**: Ordine di marcia, ruoli di viaggio, razioni/acqua, marcia forzata, calendario fantasy interattivo, negozi e registro missioni.
* **Soundboard & Voice Chat UDP Integrata**: Streaming vocale a bassa latenza con controlli Mute/Deafen (`[ 🎤 ]` / `[ 🎧 ]`) e soundboard musicale sincronizzata.

---

## 🚀 Installazione e Avvio Rapido

### Requisiti
* **Python 3.9 o superiore** (compatibile fino a Python 3.14)
* Installazione dipendenze:
  ```bash
  pip install pillow ttkbootstrap requests sounddevice numpy
  ```

### Avvio dell'Applicazione
Esegui il launcher unificato dalla cartella principale del progetto:
```bash
python main.py
```
Dal selettore iniziale potrai scegliere:
1. **Dungeon Master**: Avvia il server TCP (`53911`) e UDP Voice (`53912`) aprendo la plancia del DM (con campagna, editor campagna o sessione rapida).
2. **Giocatore (Player)**:
   * **👤 Gestione Personaggi (Offline)**: Crea, consulta, duplica, elimina ed esporta le schede dei tuoi eroi (PDF/JSON) in piena autonomia, senza richiedere l'avvio o la connessione a un server.
   * **✨ Crea Personaggio (Guidato)**: Avvia subito il wizard guidato passo-passo stile Baldur's Gate 3 per generare un nuovo eroe di 1° livello con razze, classi, caratteristiche e statistiche calcolate.
   * **🛡️ Unisciti a Partita**: Avvia il client VTT Giocatore per collegarti alla sessione online del Dungeon Master.

---

## 🎮 Comandi Rapidi & Controlli

### Controlli Mappa (Canvas)
| Input / Strumento | Azione |
|---|---|
| **Click Destro / Centrale + Trascina** | Sposta l'inquadratura della mappa (Pan) |
| **Rotellina del Mouse Su / Giù** | Zoom avanti / indietro centrato sul cursore |
| **Click Sinistro su Esagono / Trascina Token** | Muove il token lungo il percorso esagonale valido |
| **Click Centrale su Esagono** (o `[ 📍 ]`) | Invia un **Ping** animato visibile a tutti |
| **Strumento `[ 📏 ]` + Trascina** | Misura distanza in esagoni, `ft`/`m` o `mi`/`km` + tempo di viaggio |
| **Strumento `[ 💥 ]` + Click** | Posiziona template Area d'Effetto (Sfera, Cono, Linea) |
| **Strumento `[ 👆 ]`** | Seleziona / Centra la visuale sul token attivo |
| **`Ctrl + K`** | Apre la **Tavolozza Comandi Rapida** (ricerca globale e tiri) |

### Comandi Chat
| Comando | Descrizione | Esempio |
|---|---|---|
| `/roll <formula>` o `/r <formula>` | Tira dadi con espressioni matematiche | `/roll 1d20+5`, `/r 8d6+3` |
| `/w <nome> <msg>` | Invia un sussurro privato a un giocatore o al DM | `/w Gildor Attento alla trappola` |
| `/whisper <nome> <msg>` | Alias per sussurro privato | `/whisper DM Controllo il baule` |
| `/sussurra <nome> <msg>` | Alias italiano per sussurro privato | `/sussurra Elidor Ti copro io` |
| `/manuale <termine>` o `/rule <termine>` | Cerca nei manuali PDF 5e indicizzati | `/manuale fireball`, `/rule stealth` |
| `/tsmorte`, `/deathsave`, `/ds` | Esegue un Tiro Salvezza contro la Morte | `/ds` |
| `/vision <nome> <raggio_hex>` | *(Solo DM)* Imposta il raggio di visione di un token | `/vision Gildor 12` |

---

## 📁 Struttura del Repository

```text
DndOmniCompanion/
├── client/                         # Client VTT Giocatore, Scheda PG e Voice Client
│   ├── client.py                   # GUI principale del Giocatore, HUD ed economia turno
│   ├── character_manager_ui.py     # Gestione autonoma dei personaggi (Offline)
│   ├── character_sheet_ui.py       # Scheda personaggio interattiva 5e
│   ├── character_manager.py        # Persistenza e serializzazione personaggi
│   ├── character_creation_wizard.py# Wizard di creazione personaggio (Livello 1)
│   ├── progression_ui.py           # Wizard di Level-Up e integrazione SRD
│   ├── pdf_sheet_generator.py      # Generatore PDF ufficiale a 3 pagine
│   ├── login_ui.py                 # Finestra di selezione PG e connessione
│   ├── manuals_ui.py               # Consultazione manuali e compendio lato client
│   ├── network.py                  # Gestione socket TCP lato client
│   └── voice_client.py             # Client streaming vocale UDP
├── server/                         # Server DM, Regole 5e, Plancia DM e Voice Server
│   ├── server.py                   # Server TCP multi-client
│   ├── dm_gui.py                   # Plancia principale del Dungeon Master
│   ├── commands.py                 # Dispatcher centrale dei pacchetti di rete
│   ├── dm_dialogs.py               # Dialoghi DM (Handout, PNG Custom, Visualizzatore Schede, Starter Kit)
│   ├── dm_generators.py            # Generatori procedurali di Bottino 5e e PNG
│   ├── campaign_editor_ui.py       # Editor di Campagne, Atti, Scene e Incontri
│   ├── encounter_builder_ui.py     # Costruttore e bilanciatore incontri
│   ├── map_editor.py               # Editor Mappe (muri, luci, trappole, portali, scala)
│   ├── map_downloader.py           # Downloader mappe predefinite
│   ├── compendium_ui.py            # Interfaccia Compendio & SRD
│   ├── voice_server.py             # Server broadcast vocale UDP
│   └── rules/                      # Motore modulare regole D&D 5e
│       ├── combat.py               # Iniziativa, attacchi, critici, copertura, vantaggio, economia turno
│       ├── movement.py             # Movimento esagonale, FoW, trappole, teletrasporti
│       ├── character.py            # Danni, PV temp, TS morte, concentrazione, riposi
│       ├── chat.py                 # Chat, dadi, critici 1d20, sussurri, ricerca manuali
│       ├── inventory.py            # Scambi P2P, negozi, valuta, approvazione DM
│       ├── map_interaction.py      # Ping, righello, AoE, porte e interazioni mappa
│       └── audio.py                # Gestione broadcast audio e soundboard
├── common/                         # Protocolli condivisi, matematica esagonale e i18n
│   ├── game_state.py               # Modello centrale GameState e Player
│   ├── protocol.py                 # Costruttori pacchetti JSON di rete
│   ├── network_utils.py            # Framing TCP con prefisso di lunghezza
│   ├── hex_utils.py                # Geometria esagonale cubica, LoS, coni, linee, sfere
│   ├── dice.py                     # Motore di tiro dadi e rilevamento Nat 20 / Nat 1
│   ├── i18n.py                     # Traduzioni IT/EN live, unità Imperiale/Metrica e scale mappa
│   ├── encounter_calc.py           # Calcolatore difficoltà incontri DMG p. 82
│   ├── pdf_manuals_indexer.py      # Indicizzatore e motore di ricerca PDF offline
│   ├── campaign.py                 # Modello dati campagne, scene e incontri
│   ├── starter_equipment.py        # Kit equipaggiamento iniziale configurabile
│   └── theme.py                    # Palette colori Dark Fantasy e stili UI
├── components/                     # Widget grafici condivisi Tkinter/ttkbootstrap
│   ├── ui_components.py            # HexMapCanvas, HUD, Righello, ToolTip, Toast, Command Palette
│   ├── calendar_ui.py              # Calendario fantasy e meteo dinamico
│   ├── quest_ui.py                 # Gestione Quest Log
│   └── shop_ui.py                  # Interfaccia Negozi e Mercanti
├── docs/                           # Documentazione utente e tecnica (IT + EN)
│   ├── GUIDA_ALL_UTILIZZO.md       # Manuale completo all'utilizzo (Italiano)
│   ├── USER_GUIDE.md               # Complete User Guide (English)
│   ├── GUIDA_OPERATIVA.md          # Manuale operativo e architettura (Italiano)
│   └── OPERATIONAL_GUIDE.md        # System & Operational Manual (English)
├── main.py                         # Launcher unificato (DM Host / Player Client)
└── simulate_game_session.py        # Simulazione automatica end-to-end (53 fasi)
```

---

## 🧪 Test e Verifica Automatica

```powershell
# 1. Unit Test delle funzionalità (Righello multi-scala, Critici Nat20/Nat1, Economia Turno, Unità ft/m, Sussurri, TS Morte)
$env:DND_MOCK_AUDIO="1"; python test_new_features.py

# 2. Smoke Test completo di tutte le 19 schermate UI (Server DM e Client Player)
$env:DND_MOCK_AUDIO="1"; python test_ui_smoke.py --no-screens

# 3. Simulazione End-to-End Multiplayer completa (53 fasi)
$env:DND_MOCK_AUDIO="1"; python simulate_game_session.py

# 4. Test Sistema Campagne e Scene
$env:DND_MOCK_AUDIO="1"; python -m unittest test_campaign_system.py
```

---

## 📜 Licenza e Riconoscimenti

* Progettato per il regolamento **Dungeons & Dragons 5th Edition (D&D 5e)** sotto licenza Open Game License (OGL) / System Reference Document 5.1 (SRD5).
* Realizzato con [Python](https://www.python.org/), [ttkbootstrap](https://ttkbootstrap.readthedocs.io/) e [Pillow](https://python-pillow.org/).

