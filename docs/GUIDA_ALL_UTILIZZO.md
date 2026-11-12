# 🐉 D&D OmniCompanion — Guida Completa all'Utilizzo

> 🌐 **Lingua / Language**: 🇮🇹 **[Italiano (GUIDA_ALL_UTILIZZO.md)](GUIDA_ALL_UTILIZZO.md)** | 🇬🇧 **[English (USER_GUIDE.md)](USER_GUIDE.md)**
> ⚙️ **Manuale Tecnico & Architettura**: Consulta anche la **[Guida Operativa (GUIDA_OPERATIVA.md)](GUIDA_OPERATIVA.md)**.

Benvenuto nel manuale d'uso ufficiale di **D&D OmniCompanion**, il Virtual Tabletop (VTT) e gestore di campagna per **Dungeons & Dragons 5a Edizione**.
Questa guida illustra passo dopo passo come avviare una sessione, configurare l'interfaccia, gestire personaggi, mappe, combattimenti, esplorazione, unità di misura e strumenti del Dungeon Master.

---

## 📑 Indice

1. [Avvio Rapido e Connessione](#1-avvio-rapido-e-connessione)
2. [Panoramica dell'Interfaccia e Impostazioni Globali](#2-panoramica-dellinterfaccia-e-impostazioni-globali)
   - [Barra dei Menu: Lingua, Unità di Misura ed Esportazione Log](#barra-dei-menu-lingua-unità-di-misura-ed-esportazione-log)
   - [Layout a 3 Colonne, HUD e Strumenti Lavagna (`[ ✏️ ]`)](#layout-a-3-colonne-hud-e-strumenti-lavagna---)
   - [Tavolozza Comandi Rapida (`Ctrl+K`)](#tavolozza-comandi-rapida-ctrlk)
   - [Motore di Dadi 3D Nativo su Mappa (`🎲`)](#motore-di-dadi-3d-nativo-su-mappa-)
3. [Sistema di Unità di Misura, Scale Mappa, Griglie e Righello](#3-sistema-di-unità-di-misura-scale-mappa-griglie-e-righello)
   - [Scelta tra Piedi/Miglia (`ft/mi`) e Metri/Chilometri (`m/km`)](#scelta-tra-piedimiglia-ftmi-e-metrichilometri-mkm)
   - [Le 4 Scale della Mappa (DMG p. 14)](#le-4-scale-della-mappa-dmg-p-14)
   - [Supporto Multi-Griglia: Esagonale, Quadrata e Senza Griglia](#supporto-multi-griglia-esagonale-quadrata-e-senza-griglia)
   - [Utilizzo del Righello Dinamico (`[ 📏 ]`)](#utilizzo-del-righello-dinamico---)
4. [Guida per il Giocatore (Player)](#4-guida-per-il-giocatore-player)
   - [Gestione e Creazione Personaggi Offline (Senza Connessione al Server)](#gestione-e-creazione-personaggi-offline-senza-connessione-al-server)
   - [Creazione Personaggio (Wizard) e Level-Up](#creazione-personaggio-wizard-e-level-up)
   - [Hero Summary Card e Scheda Personaggio Interattiva](#hero-summary-card-e-scheda-personaggio-interattiva)
   - [Risorse di Classe Speciali (Ki, Ira, Ispirazione Bardica, ecc.)](#risorse-di-classe-speciali-ki-ira-ispirazione-bardica-ecc)
   - [Sintonia con Oggetti Magici (Attunement `🔮`) e Ispirazione DM](#sintonia-con-oggetti-magici-attunement--e-ispirazione-dm)
   - [Economia del Turno: Esplorazione vs Combattimento](#economia-del-turno-esplorazione-vs-combattimento)
   - [Azioni in Combattimento, Incantesimi AoE e Upcasting](#azioni-in-combattimento-incantesimi-aoe-e-upcasting)
   - [Targeting Tattico con Mirino, Fiancheggiamento (DMG p. 251) e Manovre RAW (Lotta & Spinta)](#targeting-tattico-con-mirino-fiancheggiamento-dmg-p-251-e-manovre-raw-lotta--spinta)
   - [Spazio 3D, Quota & Elevazione, Cadute RAW (PHB p. 183) e Concentration Tethers](#spazio-3d-quota--elevazione-cadute-raw-phb-p-183-e-concentration-tethers)
   - [Reazioni RAW e Incantesimo Scudo (*Shield*)](#reazioni-raw-e-incantesimo-scudo-shield)
   - [Tratti Speciali: Evasione (Ladro/Monaco) e Attacco Furtivo](#tratti-speciali-evasione-ladromonaco-e-attacco-furtivo)
   - [Punti Ferita, Riposi e Tiri Salvezza contro la Morte](#punti-ferita-riposi-e-tiri-salvezza-contro-la-morte)
   - [Inventario, Ingombro, Scambi e Richieste al DM](#inventario-ingombro-scambi-e-richieste-al-dm)
   - [Spoglie dei Mostri (Loot Drop DMG p. 133) e Recupero 50% Munizioni RAW (PHB p. 146)](#spoglie-dei-mostri-loot-drop-dmg-p-133-e-recupero-50-munizioni-raw-phb-p-146)
   - [Esportazione Scheda Personaggio (PDF Ufficiale D&D 5e e JSON)](#esportazione-scheda-personaggio-pdf-ufficiale-dd-5e-e-json)
   - [Macro Hotbar (Slot Rapidi 1–10)](#macro-hotbar-slot-rapidi-110)
   - [Diario Narrativo di Campagna e Memorie Personali (Player)](#diario-narrativo-di-campagna-e-memorie-personali-player)
5. [Guida per il Dungeon Master (DM)](#5-guida-per-il-dungeon-master-dm)
   - [Stili di Gestione della Campagna (DM Agency vs Full Automation) e Barra Decisioni](#stili-di-gestione-della-campagna-dm-agency-vs-full-automation-e-barra-decisioni)
   - [Gestione Campagne, Atti, Scene e Starter Pack](#gestione-campagne-atti-scene-e-starter-pack)
   - [Diario Narrativo di Sessione Continuativo (Campaign Adventure Journal)](#diario-narrativo-di-sessione-continuativo-campaign-adventure-journal)
   - [Gestione Mappe, Editor Mappe, Muri, Trappole e Portali](#gestione-mappe-editor-mappe-muri-trappole-e-portali)
   - [Gestione Porte, Serrature e Meccanica di Scasso RAW 5e](#gestione-porte-serrature-e-meccanica-di-scasso-raw-5e)
   - [Spille di Stanza del Dungeon (Room Pins) e Narrazione al Tavolo](#spille-di-stanza-del-dungeon-room-pins-e-narrazione-al-tavolo)
   - [Tiri Segreti del DM (Blind Rolls: `/broll`, `/gmroll`)](#tiri-segreti-del-dm-blind-rolls-broll-gmroll)
   - [Nebbia di Guerra (FoW), Pennello Manuale, Line of Sight e Luci](#nebbia-di-guerra-fow-pennello-manuale-line-of-sight-e-luci)
   - [Taglie Creature (Dimensioni Token) e Livello Nascosto DM (GM Layer)](#taglie-creature-dimensioni-token-e-livello-nascosto-dm-gm-layer)
   - [Gestione del Combattimento e Bilanciatore Incontri (DMG p. 82)](#gestione-del-combattimento-e-bilanciatore-incontri-dmg-p-82)
   - [Multi-Selezione Token ed Operazioni di Gruppo del DM](#multi-selezione-token-ed-operazioni-di-gruppo-del-dm)
   - [Bestiario SRD, Manuali PDF Offline e Generatori Procedurali](#bestiario-srd-manuali-pdf-offline-e-generatori-procedurali)
   - [Mondo, Calendario, Meteo, Viaggio, Negozi e Quest](#mondo-calendario-meteo-viaggio-negozi-e-quest)
   - [Handout (Documenti/Immagini) e Soundboard Audio](#handout-documentiimmagini-e-soundboard-audio)
   - [Lavagna Tattica Condivisa (Whiteboard) ed Esportazione Session Log](#lavagna-tattica-condivisa-whiteboard-ed-esportazione-session-log)
6. [Successi Critici (`20 Naturale`) e Fallimenti Critici (`1 Naturale`)](#6-successi-critici-20-naturale-e-fallimenti-critici-1-naturale)
7. [Chat Stile Discord, Sussurri e Voice Chat UDP](#7-chat-stile-discord-sussurri-e-voice-chat-udp)
8. [Riferimento Rapido: Comandi Chat e Scorciatoie](#8-riferimento-rapido-comandi-chat-e-scorciatoie)

---

## 1. Avvio Rapido e Connessione

### 📦 Download Eseguibili Precompilati (Windows & Linux)
Se desideri utilizzare D&D OmniCompanion senza installare Python, puoi scaricare l'eseguibile standalone pronto all'uso dalla pagina [GitHub Releases](https://github.com/Gaian-pixel/DndOmniCompanion/releases):
* **Windows (64-bit)**: Scarica `DndOmniCompanion-v*-win64.zip`, estrai l'archivio in una cartella a tua scelta ed avvia `DndOmniCompanion.exe`.
* **Linux (x86_64)**: Scarica `DndOmniCompanion-v*-linux-x64.tar.gz`, estrai l'archivio ed esegui `./run.sh` (oppure `./DndOmniCompanion`).

---

### 💻 Avvio da Codice Sorgente (Python)

1. Apri un terminale nella cartella del progetto ed avvia il launcher:
   * **Su Windows**:
     ```bash
     python main.py
     ```
   * **Su Linux**:
     ```bash
     chmod +x run_linux.sh
     ./run_linux.sh
     # oppure: python3 main.py
     ```
2. Si aprirà il **Launcher principale** con due sezioni:
   * **Dungeon Master (Host)**:
     * **⚔️ Avvia con Campagna**: carica una campagna esistente (con atti, scene, incontri preparati e mappe).
     * **📜 Prepara / Modifica Campagna**: apre direttamente l'Editor di Campagna per creare la tua avventura prima della sessione.
     * **⚡ Sessione Rapida (Vuota)**: avvia subito il server sulla porta TCP `5000` (e Voice UDP `53912`) per una partita estemporanea.
   * **Giocatore (Player)**:
     * **👤 Gestione Personaggi (Offline)**: apre direttamente la schermata di gestione eroi per creare, consultare, modificare la scheda, duplicare, eliminare ed esportare personaggi in PDF o JSON senza dover connettersi ad alcun server.
     * **✨ Crea Personaggio (Guidato)**: avvia subito la procedura guidata passo-passo (Razza, Classe, Statistiche, Background, Equipaggiamento) per creare un eroe di 1° livello.
     * **🛡️ Unisciti alla Partita**: apre immediatamente la finestra modale di accesso (`LoginDialog`) per selezionare o inserire l'indirizzo IP del server (con cronologia automatica dei server recenti e pulsante rapido `🖥️ Locale (127.0.0.1)`) e scegliere il personaggio; cliccando su **Connetti** il client si avvia già connesso ed entra direttamente nella sessione. Se ti disconnetti, trovi sempre il pulsante `[ 🔗 Connetti ]` direttamente nel tab `Controlli PG`.

* **Esperienza Mono-Finestra (In-Place)**: Tutte le viste secondarie del launcher (*👤 Gestione Personaggi*, *✨ Crea Personaggio* e *📜 Prepara / Modifica Campagna*) si aprono direttamente in-place all'interno della stessa finestra principale, corredate da una barra superiore `[ ← Torna al Menu Principale ]` per tornare alla schermata iniziale con un click, azzerando la proliferazione di finestre sul desktop.

---

## 2. Panoramica dell'Interfaccia e Impostazioni Globali

### Barra dei Menu: Lingua, Unità di Misura ed Esportazione Log
Nella barra superiore (sia lato DM che lato Giocatore) trovi menu di configurazione rapida e strumenti di gestione sessione:
* **`🌐 Lingua / Language`**: cambia in tempo reale tutta l'interfaccia, le condizioni, le abilità e i messaggi di sistema tra **Italiano 🇮🇹** e **English 🇬🇧** senza riavviare l'applicazione.
* **`📏 Unità di Misura` (`📏 Distance Units`)**: permette di scegliere in qualsiasi momento tra:
  * **Piedi / Miglia (`ft / mi`)** — Sistema Imperiale standard USA (1 esagono tattico = `5 ft`).
  * **Metri / Chilometri (`m / km`)** — Sistema Metrico edizione italiana (1 esagono tattico = `1.5 m`).
* **`File -> 📜 Esporta Registro di Sessione...`**: consente sia al DM che ai Giocatori di esportare l'intera cronologia della sessione (chat, tiri di dado, eventi tattici, danni ed evocazioni) in un comodo file **Markdown (`.md`)** formattato o in formato **HTML interattivo**.

### Layout a 3 Colonne, HUD e Strumenti Lavagna (`[ ✏️ ]`)
L'interfaccia è divisa in tre aree ergonomiche:
1. **Toolbar Sinistra (Strumenti Mappa e Lavagna)**: barra compatta con pulsanti iconici per interagire con la mappa:
   * `👆` Centra/Seleziona token e mappa.
   * `💥` Template Incantesimi ad Area (AoE) e Sfere di Oscurità Magica.
   * `📏` Righello dinamico di misurazione distanze e tempi di marcia.
   * `📍` Segnale di Ping animato condiviso.
   * `📖` Consultazione rapida manuali di gioco PDF offline.
   * `[ ✏️ ]` **Lavagna / Penna Tattica**: permette a DM e Giocatori di disegnare a mano libera annotazioni, frecce di manovra e percorsi sulla mappa in tempo reale.
   * `[ 🧹 ]` / `[ 🗑️ ]` **Cancella Lavagna**: rimuove istantaneamente tutti i tratti disegnati sulla mappa sia in locale che sui client connessi.
   * `🚪` Portali e Teletrasporti tra mappe (solo DM).
   * `[ 🪨 ]` **Pennello Terreni Difficili (solo DM)**: permette di selezionare un tipo di terreno (Fango, Ghiaccio, Rovi, Macerie, Palude, Gomma) e dipingerlo o cancellarlo al volo sulle caselle della mappa attiva.
   * `[ 🌑 ]` **Filtro Oscurità 1-Click (solo DM)**: attiva o disattiva all'istante il filtro di Oscurità ambientale sulla mappa, con gestione automatica delle regole D&D 5e su visibilità e Scurovisione.
   * `☁️` Nebbia di Guerra (FoW con raggio pennello da 0 a 3, solo DM).
   * `🎲` **Attiva/Disattiva Dadi 3D**: abilita o disabilita al volo il motore di simulazione dei dadi poliedrici tridimensionali sulla mappa.
2. **Viewport Centrale (`HexMapCanvas`)**: la mappa interattiva (esagonale, quadrata o senza griglia), arricchita da due HUD sovrapposti:
   * **Initiative Ribbon HUD (in alto al centro)**: appare automaticamente durante il combattimento mostrando le card di tutti i combattenti in ordine di turno (`#1`, `#2`...), la freccia `▼` sul turno attivo e una mini-barra PV per ciascuno. Cliccando su una card la mappa si centra su quel token.
   * **Controlli Mappa Glassmorphism (in basso a sinistra)**: pulsanti flottanti `[ - ]`, `[ 100% ]`, `[ + ]` e `[ ⌖ ]` per regolare lo zoom o ricentrare la visuale con un click.
3. **Sidebar Destra (Pannello a Tab)**: contiene la Chat & Voice Chat, i Controlli PG / Tracker Iniziativa, il Mondo/Calendario, il Bestiario e la Soundboard Audio.

### Tavolozza Comandi Rapida (`Ctrl+K`)
Premendo **`Ctrl+K`** in qualsiasi momento (o da `Strumenti/Libreria -> Tavolozza Comandi Rapida`) si apre una barra di ricerca universale:
* Digita il nome di un **mostro**, di un **incantesimo** o di una **regola 5e** per leggerne i dettagli.
* Digita il nome di un **token sulla mappa** per centrare immediatamente la telecamera su di esso.
* Digita un'espressione come `/roll 2d6+4` o `1d20+5` e premi `Invio` per lanciare subito i dadi in chat.

### Motore di Dadi 3D Nativo su Mappa (`🎲`)
D&D OmniCompanion include un motore tridimensionale poliedrico nativo disegnato direttamente sopra la mappa tattica (`HexMapCanvas`):
* **Nessuna Dipendenza Esterna**: zero OpenGL o librerie esterne pesanti; pura geometria analitica e proiezioni prospettiche da tavolo renderizzate direttamente sul canvas Tkinter.
* **Geometrie Poliedriche Complete RAW 5e**:
  * **d4**: Tetraedro regolare a 4 vertici e 4 facce triangolari.
  * **d6**: Cubo regolare con facce opposte che sommano a 7.
  * **d8**: Ottaedro regolare con facce opposte che sommano a 9.
  * **d10**: Trapezoedro pentagonale numerato 0–9.
  * **d12**: Dodecaedro regolare con facce opposte che sommano a 13.
  * **d20**: Icosaedro regolare con facce opposte che sommano a 21.
  * **d100 (Zocchihedron Autentico)**: Sfera poliedrica singola a 92 vertici e 100 facce planari numerate 1–100 con coppie opposte a somma 101, fedele all'iconico dado di Lou Zocchi.
* **Overlay Trasparente Senza Oscurare la Mappa**:
  * I dadi rotolano in primo piano con ombra di contatto sfumata (`stipple="gray50"`), preservando al 100% la visibilità della mappa, dei token, della griglia e della nebbia di guerra.
* **Fisica Balistica, Rimbalzo e Slerp di Orientamento**:
  * I dadi subiscono gravità ($980\text{ px/s}^2$), rimbalzi elastici e attrito angolare, assestandosi con interpolazione sferica (Slerp) per esporre la faccia vincente esattamente verso la telecamera con orientamento del testo perfettamente verticale.
* **Feedback Visivo e Audio Immediato**:
  * **20 Naturale**: Aspetto oro splendente (`#D97706`), bagliore e annuncio trionfale.
  * **1 Naturale**: Aspetto vermiglio cupo ossidiana (`#7F1D1D`).
  * **Vantaggio e Svantaggio**: Rotolamento sincrono di due d20; il dado scartato si attenua in grigio ferro con etichetta `(scartato)`.
  * **Banner HUD Fluttuante**: Mostra la formula, i dadi e il totale finale; include il pulsante `[ ✕ ]` per chiudere subito l'animazione o scompare in automatico dopo 4.5s. Cliccando durante il lancio si salta subito all'esito.

---

## 3. Sistema di Unità di Misura, Scale Mappa, Griglie e Righello

### Scelta tra Piedi/Miglia (`ft/mi`) e Metri/Chilometri (`m/km`)
Quando cambi l'unità dal menu **`📏 Unità di Misura`**, l'intero applicativo converte automaticamente:
* La **Velocità** del personaggio nella Hero Summary Card, nella Scheda PG e nel Wizard di creazione (`30 ft` $\leftrightarrow$ `9 m`).
* La **Barra del Movimento** nell'Economia del Turno.
* Il **Righello di misurazione** (`[ 📏 ]`) e le etichette di scala mappa.

### Le 4 Scale della Mappa (DMG p. 14)
Ogni mappa ha una propria scala geografica. Il DM può visualizzarla e cambiarla con 1 click tramite il badge **`📏 Scala: ...`** posto nella barra superiore sopra la mappa (o nell'Editor Mappe):

| Scala Mappa | Valore per 1 Esagono (Imperiale) | Valore per 1 Esagono (Metrico) | Tempo di Marcia Stimato | Utilizzo Tipico |
|---|---|---|---|---|
| **⚔️ Combattimento** | `5 ft` | `1.5 m` | Tempo reale (6 sec/round) | Scontri tattici, stanze di dungeon, locande |
| **🌲 Esplorazione (POI)** | `1 mi` | `1.5 km` | `~20 min` per esagono | Esplorazione locale, valli, foreste, quartieri |
| **🌍 Mondo / Regione** | `6 mi` | `9 km` | `2 ore` per esagono (`4 hex = 1 giorno`) | Mappe continentali (es. Costa della Spada, Faerûn) |
| **⚙️ Personalizzata** | Configurabile (`ft`/`mi`) | Configurabile (`m`/`km`) | Calcolato automaticamente | Mappe con griglie fuori standard |

> [!TIP]
> Quando il DM cambia la scala dal selettore rapido `📏 Scala`, la modifica viene salvata e trasmessa in tempo reale a tutti i giocatori connessi!

### Supporto Multi-Griglia: Esagonale, Quadrata e Senza Griglia
OmniCompanion supporta tre diverse modalità di griglia per adattarsi a qualsiasi stile di mappa:
* **Griglia Esagonale (`hex`)**: la modalità tattica preferita per le campagne aperte e la precisione geometrica di coni e sfere.
* **Griglia a Scacchiera / Quadrata (`square`)**: la classica griglia da dungeon D&D 5e. Utilizza la metrica di Chebyshev standard per il movimento (ogni spostamento diagonale conta $5\text{ ft} / 1.5\text{ m}$, esattamente come un passo ortogonale).
* **Senza Griglia (`none` / `gridless`)**: nasconde ogni linea di griglia per mappe pittoriche a mano libera; il righello e il movimento calcolano la reale distanza euclidea.
* **Cambio Rapido Griglia**: il DM può cambiare il tipo di griglia in tempo reale con un click sul pulsante **`📐 Griglia: ...`** nella barra superiore sopra la mappa.

### Utilizzo del Righello Dinamico (`[ 📏 ]`)
1. Clicca sul pulsante **`[ 📏 ]`** nella toolbar a sinistra per attivare la modalità Righello (il bottone si illumina d'oro).
2. **Clicca e trascina** con il tasto sinistro da un esagono di partenza a un esagono di arrivo sulla mappa.
3. Sulla mappa apparirà un vettore tratteggiato dorato con un badge ad alto contrasto che mostra:
   * Su mappe di **Combattimento**: `6 hex (30 ft)` oppure `6 hex (9 m)`.
   * Su mappe di **Esplorazione**: `3 hex (3 mi [~1h])` oppure `3 hex (4.5 km [~1h])`.
   * Su mappe **Mondo / Regione**: `8 hex (48 mi [~2 gg])` oppure `8 hex (72 km [~2 gg])`.

---

## 4. Guida per il Giocatore (Player)

### Gestione e Creazione Personaggi Offline (Senza Connessione al Server)
Non è necessario avviare una sessione o collegarsi a un server per creare, consultare, modificare o esportare i tuoi personaggi:
* **Dal Launcher Principale (`main.py`)**:
  * **👤 Gestione Personaggi (Offline)**: apre un pannello completo dedicato con la lista degli eroi salvati, ricerca per nome/classe/razza, anteprima rapida delle statistiche base (PV, CA, Velocità, Caratteristiche con modificatori), pulsanti per **aprire la scheda completa**, **duplicare**, **eliminare** ed **esportare in PDF o JSON**. Se desideri avviare subito la partita, un pulsante dedicato ti permette di selezionare il personaggio e giocare direttamente.
  * **✨ Crea Personaggio (Guidato)**: apre immediatamente il wizard in stile Baldur's Gate 3 per creare un eroe di 1° livello e salvarlo localmente.
* **Dall'Interfaccia di Gioco (Client)**:
  * Dal menu in alto: **`Personaggio -> Gestione Personaggi (Offline)...`** oppure **`Crea Nuovo Personaggio (Guidato)...`** / **`Crea Personaggio Manuale...`**.
  * Nella barra laterale destra (Tab `Controlli PG`): trovi i pulsanti rapidi `[ ✨ ]` (Nuovo PG) e `[ 👤 ]` (Gestione) posti accanto al menu a tendina del personaggio attivo.
  * Il pulsante **`📜 Scheda PG`** rimane **sempre attivo anche da disconnesso**: cliccandolo puoi visualizzare e modificare la scheda dell'eroe selezionato, testare i tiri di dado offline, gestire armi, inventario, grimorio ed esportare la scheda.

### Creazione Personaggio (Wizard) e Level-Up
* **Nuovo Personaggio (Livello 1 — Procedura Guidata in 5 Passi)**: Dalla finestra di selezione personaggio, dalla Gestione Personaggi o dal menu, avvia il **Wizard di Creazione** in stile Baldur's Gate 3:
  1. **Passo 1: Razza**: selezione interattiva delle 9 razze canoniche 5e (*Umano, Elfo, Nano, Halfling, Draconide, Gnomo, Mezzelfo, Mezzorco, Tiefling*) con navigazione rapida `[ ◀ Prec. ]` / `[ Succ. ▶ ]`, matrice statistiche, longevità, sensori speciali, riquadro resistenze e sinergie di classe.
     * **Compendio Comparativo Avanzato Master-Detail (`[ 📊 Tabella Comparativa ]`)**:
       * **Ricerca Live & Filtri Tematici Rapidi**: Barra di ricerca istantanea su qualsiasi parola chiave e pillole filtro a 1-click (`[Tutte (9)]`, `[🛡️ Resistenze]`, `[👁️ Scurovisione]`, `[🏃 Taglia Piccola]`, `[⚔️ Mischia / Forza]`, `[✨ Magiche / Carisma]`).
       * **Layout Split-View Master-Detail**: A sinistra, tabella master a 6 colonne (`Razza` con icona, `Bonus Caratteristiche`, `Tratti Razziali Chiave`, `Resistenze & Difese`, `Taglia / Vel.`, `Classi Consigliate`) con scroll verticale e orizzontale. A destra, **Scheda Anteprima Reattiva** che si aggiorna in tempo reale cliccando su una riga o scorrendo con la tastiera.
       * **Dati Meccanici & Lore RAW 5e**: Censimento completo delle difese passive (*Resistenza Infernale al Fuoco* per Tiefling, *Resilienza Nanica vs Veleno* per Nani, *Retaggio Fatato con Immunità al Sonno Magico* per Elfi/Mezzelfi, *Astuzia Gnomesca sui TS vs Magia* per Gnomi, *Resistenza Elementale da Stirpe* per Draconidi, *Tenacia Implacabile a 1 PF* per Mezzorchi, *Fortunato e Coraggioso* per Halfling), classi e sinergie consigliate, spiegazione approfondita di tutti i tratti razziali e anteprima delle sottorazze/varianti.
       * **Selezione Immediata**: Doppio click su una riga o pulsante `[ ✓ Scegli Questa Razza ]` per applicare la scelta al personaggio e tornare al wizard.
  2. **Passo 2: Classe**: selezione tra le 12 classi canoniche 5e con Dado Vita ($1\text{d6}$–$1\text{d12}$), Caratteristiche Primarie, Tiri Salvezza con competenza, Ruolo Tattico, Complessità di gioco, consigli Quick Build per neofiti, anteprima equipaggiamento iniziale e sottoclassi.
     * **Compendio Comparativo Classi**: Tabella comparativa con filtri per categoria (`[Tutte]`, `[Marziali]`, `[Incantatori]`, `[Ibridi]`, `[Esperti]`) per analizzare ruoli e bilanciamento del party.
  3. **Passo 3: Caratteristiche**: assegnazione punteggi con **Standard Array** (15, 14, 13, 12, 10, 8), **Point Buy** (27 punti) o **Tiro Dadi** (4d6 drop lowest), con somma trasparente e automatica dei bonus razziali alla scheda finale.
  4. **Passo 4: Background & Allineamento**: scelta dell'origine narrativa, competenze aggiuntive e tratti di personalità.
  5. **Passo 5: Dettagli, Avatar e Finalizzazione**: assegnazione nome, divinità, note e caricamento dell'immagine avatar del personaggio.
* **Salita di Livello (`Level Up (+)`) e Multiclasse (PHB Cap. 6)**: Nella Scheda PG, clicca su `Level Up (+)`:
  * **Selettore Multiclasse**: Scegli se avanzare nella tua classe principale o acquisire un livello in una qualsiasi delle **12 classi base 5e**. Il sistema verifica automaticamente i **prerequisiti di caratteristica RAW** (punteggio minimo 13 nelle caratteristiche primarie sia della classe attuale sia della nuova classe scelta).
  * **Calcolo Automatico Slot Incantatore Multiclasse**: Combina automaticamente i livelli da Incantatore Pieno (Bardo, Chierico, Druido, Mago, Stregone), Mezzo Incantatore (Paladino, Ranger, Artefice) e Terzo Incantatore (Cavaliere Mistico, Mistificatore Arcano) secondo la tabella ufficiale PHB p. 165, mantenendo separati gli slot di *Magia del Patto* del Warlock.
  * Scegli se prendere il **valore medio** del Dado Vita della classe selezionata o effettuare il **tiro**.
  * Il sistema scarica automaticamente dal Compendio SRD 5e i **nuovi privilegi di classe** e aggiorna gli **slot incantesimo** del nuovo livello, includendo le tabelle dedicate per **Artefice** (2 slot al 1° livello) e **Terzi Incantatori** (*Cavaliere Mistico* e *Mistificatore Arcano* a partire dal 3° livello).
  * **Persistenza e Integrità dei Privilegi**: I privilegi selezionati vengono salvati sia in `features` che in `features_list` e sincronizzati con il server, garantendo che nessuna capacità acquisita vada persa salvando o ricaricando la scheda.
  * **Bonus di Competenza Dinamico**: Il bonus viene ricalcolato all'istante ($2 + \lfloor(\text{Livello Totale}-1)/4\rfloor$) e applicato a tiri salvezza, prove di abilità e tiri per colpire delle armi.
  * **Aumento Caratteristiche (ASI)**: Ai livelli previsti (4, 8, 12, 16, 19) puoi scegliere tra Talento e Incremento (+2 o +1/+1). Il sistema impone il **tetto massimo di 20** per i punteggi base e impedisce la selezione duplicata della stessa caratteristica in modalità +1/+1.

### Avatar Personaggio e Generazione Automatica Token su Mappa
* **Caricamento Avatar**: Sia durante la creazione guidata (Passo 5) sia dalla Scheda Personaggio, il giocatore può caricare un'immagine personalizzata per il proprio eroe (formati PNG, JPG, WEBP).
* **Token Tattico ad Alta Risoluzione**:
  * L'immagine del personaggio diventa automaticamente il **Token Grafico visualizzato sul Canvas della Mappa**.
  * Il motore esegue un ritaglio circolare antialiasing con bordo coordinato (colore fazione/classe) e integra il badge delle condizioni attive.
  * Il token viene scalato automaticamente in base alla **Taglia della creatura** (da *Minuscola* $0.5\times$ a *Media* $1.0\times$ fino a *Mastodontica* $3.5\times$).
  * La stessa logica si applica al DM per il caricamento dei ritratti di PNG e mostri.

### Hero Summary Card e Scheda Personaggio Interattiva
Nel tab **`Controlli PG`** della sidebar destra trovi sempre in primo piano la **Hero Summary Card**:
* Mostra Nome, Classe/Razza/Livello, Punti Ferita attuali/massimi (più eventuali PV Temporanei, livello di Indebolimento e Condizioni attive).
* **Barra della Salute Dinamica**: si riempie proporzionalmente da `0%` a `100%` cambiando colore dal verde (`> 50%`) all'ambra (`25%–50%`) fino al rosso (`< 25%`).
* Badge rapidi per **🛡️ CA**, **👟 Velocità** (convertita in `ft` o `m`) e **⚡ Iniziativa**.
* **Pulsante Sorgente di Luce `[ 🕯️ ]` (PHB p. 183)**:
  * **Click Sinistro**: accende o spegne all'istante la fonte luminosa attiva del personaggio.
  * **Click Destro**: apre il menu contestuale per scegliere il preset desiderato:
    * **Torcia**: $20\text{ ft}$ luce intensa, $20\text{ ft}$ luce fioca (raggio 8 esagoni), bagliore ambrato `#FFD700`.
    * **Lanterna a Cappuccio**: $30\text{ ft}$ luce intensa, $30\text{ ft}$ luce fioca (raggio 12 esagoni), bagliore arancio `#FFA500`.
    * **Lanterna Schermata (Fascio Ristretto)**: $5\text{ ft}$ luce fioca (raggio 1 esagono), bagliore soffuso `#FF8C00`.
    * **Incantesimo Luce**: $20\text{ ft}$ luce intensa, $20\text{ ft}$ luce fioca (raggio 8 esagoni), bagliore ciano magico `#66D9E8`.
  * **Sincronizzazione FoW**: accendere la luce aggiorna in tempo reale la visibilità del token sulla mappa, svelando la Nebbia di Guerra calcolata su $\max(\text{vision\_radius}, \text{light\_radius})$.

#### Architettura Mono-Finestra: Center Overlay e Docking/Detaching
Nel client di gioco, la Scheda Personaggio adotta una moderna architettura mono-finestra:
* **Center Overlay sulla Mappa**: Cliccando su **`📋 Scheda PG`** o premendo il tasto rapido **`C`**, la scheda si apre direttamente come un elegante overlay fluttuante al centro della mappa tattica (`Center Overlay`), senza moltiplicare finestre.
* **Chiusura Immediata con `Esc`**: Puoi chiudere l'overlay in qualsiasi momento premendo **`Esc`** o cliccando la `✖` in alto a destra, riprendendo subito il controllo completo della mappa.
* **Stacco e Riaggancio Flessibile (Multi-Monitor)**:
  * **`[ ◱ Stacca Finestra ]`**: Cliccando questo pulsante nella testata dell'overlay, la Scheda PG viene staccata in una finestra Tkinter fluttuante e indipendente, ideale per postazioni a doppio monitor o per chi desidera affiancare scheda e canvas.
  * **`[ ◰ Riaggancia alla Mappa ]`**: Dalla finestra staccata, un click su questo pulsante riaggancia immediatamente la scheda al centro del canvas del VTT come overlay, preservando modifiche e stato.

Cliccando su **`📋 Scheda PG`** o aprendo l'overlay, la scheda si presenta divisa nei seguenti tab:
1. **Statistiche & Combattimento**: Punteggi di Caratteristica, Tiri Salvezza, Abilità con selettore di Competenza (`0 = Nessuna`, `1 = Competente +PB`, `2 = Maestria +2×PB`) e pulsante `🎲` per tirare direttamente in chat, Gestione PV rapidi (`-5`, `-1`, `+1`, `+5`), Riposo Breve/Lungo, Dadi Vita e Tiri contro la Morte.
2. **⚔️ Armi & Attacchi**: elenco delle armi con calcolo automatico del bonus al tiro per colpire e del danno.
3. **🎒 Inventario**: gestione oggetti con peso individuale, sintonizzazione magica (max 3 oggetti `🔮`), Borsa delle Monete (`MR`, `MA`, `ME`, `MO`, `MP`) e calcolo automatico dell'**Ingombro** ($\text{Forza} \times 15\text{ lbs}$).
4. **📖 Grimorio**: contatori degli Slot Incantesimo dal livello 1 al 9, ricerca incantesimi SRD e pulsante **Lancia** che scala automaticamente lo slot e annuncia l'incantesimo in chat.
5. **🌟 Privilegi & Note / 📜 Diario**: tratti razziali, privilegi di classe, tracciatore risorse speciali e appunti di sessione.

### Risorse di Classe Speciali (Ki, Ira, Ispirazione Bardica, ecc.)
Nel tab **`🌟 Privilegi`** della Scheda PG è presente il riquadro interattivo **`⚡ Risorse di Classe Speciali`**:
* **Popolamento Automatico**: alla creazione del PG o al Level-Up, il sistema assegna automaticamente le risorse ufficiali della classe (es. *Punti Ki* per il Monaco, *Usi d'Ira* per il Barbaro, *Dadi di Ispirazione Bardica* per il Bardo, *Forme Selvatiche* per il Druido, *Canale di Divinità* per Chierico/Paladino, *Azione Impetuosa* e *Secondo Fiato* per il Guerriero, *Punti Stregoneria* per lo Stregone, *Imposizione delle Mani* per il Paladino).
* **Contatori Rapidi `[-]` / `[+]`**: spendi o ricarica le tue cariche con un click durante la sessione.
* **Risorse Personalizzate**: puoi aggiungere nuove risorse personalizzate tramite il pulsante **`+ Aggiungi Risorsa`** specificando Nome, Valore Massimo e Tipo di Recupero (*Riposo Breve* o *Riposo Lungo*), oppure eliminarle con `🗑️`.
* **Ricarica Intelligente nei Riposi**: quando effettui un *Riposo Breve* o un *Riposo Lungo*, il sistema ripristina automaticamente solo le risorse che recuperano con quel tipo di riposo.
* **Forma Selvatica del Druido (*Wild Shape* - PHB p. 66)**:
  * Pulsante dedicato **`[ 🌿 Forma Selvatica ]`** nella Scheda PG. Permette di scegliere tra una forma predefinita (Lupo, Orso Bruno, Cinghiale, Falco, Pantera, ecc.) o inserire valori custom.
  * Durante la trasformazione, il Druido ottiene un pool di Punti Ferita della Bestia separato (`beast_hp`), CA, velocità e caratteristiche fisiche dell'animale.
  * **Assorbimento Danni & Spillover**: I danni in arrivo intaccano unicamente i PV della bestia. Quando la bestia scende a 0 PV, la forma decade istantaneamente e il danno eccedente si trasferisce sui normali PV del Druido senza provocare svenimento se la sua salute residua rimane superiore a 0.
* **Fonte di Magia & Metamagia dello Stregone (PHB p. 101)**:
  * Pulsante **`[ ✨ Fonte di Magia ]`** nel tab Grimorio. Consente la conversione flessibile tra Slot Incantesimo e Punti Stregoneria:
    * *Slot $\to$ Punti*: 1 slot di 1° livello dà 1 SP, 2° dà 2 SP, 3° dà 3 SP, ecc.
    * *Punti $\to$ Slot*: creazione di slot secondo la tabella ufficiale RAW (1° liv = 2 SP, 2° liv = 3 SP, 3° liv = 5 SP, 4° liv = 6 SP, 5° liv = 7 SP).
  * Gestione e spesa per Metamagia (*Incantesimo Rapido*, *Raddoppiato*, *Accurato*, *Celato*, *Esteso*, ecc.) con ricarica totale al Riposo Lungo.
* **Recupero Arcano (*Arcane Recovery* - PHB p. 115)**:
  * Nel dialogo di **Riposo Breve** (`ShortRestDialog`), per Maghi e Druidi del Circolo della Terra appare il pulsante **`[ ✨ Recupero Arcano ]`**.
  * Permette di recuperare slot incantesimo spesi fino a un livello complessivo pari a $\lceil \text{Livello}/2 \rceil$ (con nessun singolo slot superiore al 5° livello) una volta al giorno, resettandosi al Riposo Lungo.
* **Tuttofare del Bardo (*Jack of All Trades* - PHB p. 54) & Talento Affidabile del Ladro (*Reliable Talent* - PHB p. 96)**:
  * **Tuttofare**: I Bardi di 2° livello o superiore applicano automaticamente metà del loro Bonus di Competenza arrotondato per difetto ($+\lfloor\text{PB}/2\rfloor$) a qualsiasi prova di abilità o caratteristica in cui non siano competenti, compreso il tiro di Iniziativa.
  * **Talento Affidabile**: Per i Ladri di 11° livello o superiore, qualsiasi tiro di d20 pari a 9 o inferiore su una prova di abilità competente viene automaticamente elevato a 10 prima dell'applicazione del modificatore.
* **Scaling Danni dei Trucchetti & Limite Incantesimi Preparati (PHB p. 201)**:
  * I dadi di danno dei cantrip d'attacco scalano automaticamente in base al livello complessivo del personaggio (1 dado ai liv 1–4, 2 dadi ai liv 5–10, 3 dadi ai liv 11–16, 4 dadi ai liv 17+).
  * Il Grimorio calcola e mostra chiaramente il numero massimo di incantesimi preparabili ($\text{Livello} + \text{Modificatore Caratteristica}$) per Chierici, Druidi, Maghi, Paladini e Artefici.

### Sintonia con Oggetti Magici (Attunement `🔮`), Modificatori Automatici, Cariche e Ispirazione DM
* **Sintonia con Oggetti Magici (Attunement `🔮`)**:
  * Come da regole ufficiali RAW 5e (DMG p. 136), un personaggio può essere in sintonia con un massimo di **3 oggetti magici contemporaneamente**.
  * Nel tab **🎒 Inventario** della Scheda PG, ogni oggetto possiede un indicatore/selettore `🔮 Sintonizzato`.
  * Il sistema conteggia dinamicamente gli slot occupati (`🔮 Sintonie Attive: X / 3`) e impedisce di superare il limite delle 3 sintonie senza prima averne sciolta una (durante un riposo breve).
* **Calcolo Automatico dei Modificatori degli Oggetti Magici (`common/item_modifiers.py`)**:
  * Gli oggetti equipaggiati (`⚔️ Equipaggiato`) e sintonizzati (`🔮 Sintonizzato`) applicano in tempo reale tutti i propri modificatori passivi alla scheda del personaggio:
    * **Classe Armatura (CA)**: armature e scudi magici `+1 / +2 / +3`, *Mantello della Protezione*, *Anello della Protezione*, *Pietra di Ioun della Protezione*, *Bracciali della Difesa* (`+2 CA` senza armatura né scudo), *Veste dell'Arcimago* (CA base `15 + Mod DES`) e *Bastone del Potere* (`+2 CA`).
    * **Override dei Punteggi di Caratteristica**: *Amuleto della Salute* (`COS = 19`), *Fascia dell'Intelletto* (`INT = 19`), *Guanti del Potere Orchesco* (`FOR = 19`) e *Cinture della Forza dei Giganti* (`FOR` da `21` a `29`).
    * **Bonus a Tiri Salvezza, CD Incantesimi, TxC e Velocità**: bonus globali ai Tiri Salvezza, incremento CD e Bonus Attacco Incantesimi (*Verga del Custode del Patto*, *Bacchetta del Mago da Guerra*, *Bastone del Potere*, *Veste dell'Arcimago*) e bonus alla velocità di movimento (*Stivali della Velocità*, *Stivali del Passo e del Balzo*).
* **Cariche degli Oggetti Magici e Ricarica all'Alba (DMG p. 141)**:
  * Oggetti come *Bastone del Potere*, *Bacchetta delle Palle di Fuoco* o *Bacchetta dei Dardi Incantati* mostrano il contatore delle cariche (`[⚡ X/Y]`) direttamente nella riga dell'inventario.
  * **Spesa Carica a 1 Click**: tramite il pulsante `[⚡]` o il menu contestuale (`⚡ Usa 1 Carica`) puoi spendere cariche istantaneamente.
  * **Regola dell'Ultima Carica (DMG p. 141)**: quando spendi l'ultima carica residua (`0 / Max`), il sistema tira automaticamente `1d20`; con un risultato di `1`, segnala il rischio di distruzione/esaurimento dell'oggetto magico!
  * **Ricarica Automatica al Riposo Lungo**: all'alba (durante il *Riposo Lungo*), gli oggetti dotati di formula di ricarica (es. `1d6+4` o `1d6+1`) tirano automaticamente i dadi e ripristinano le cariche spese.
* **Portento del Divinatore (`🔮 Portento`) e Talento Fortunato (`🍀 Fortunato`)**:
  * **Portento (Scuola di Divinazione)**: al termine di ogni Riposo Lungo, il sistema tira automaticamente `2d20` (`3d20` dal 14° livello) e li mostra come pulsanti rapidi nella barra superiore della Scheda PG; cliccando su un dado Portento lo spendi e ne dichiari il valore sostitutivo in chat.
  * **Talento Fortunato (*Lucky*)**: mostra i `3 / 3` Punti Fortuna nell'intestazione della Scheda PG; un click su **`[ 🍀 Usa Punto Fortuna ]`** spende 1 punto e tira immediatamente `1d20` sostitutivo in chat (con ricarica automatica al Riposo Lungo).
* **Ispirazione del Dungeon Master (`✨ Ispirazione`)**:
  * Nella parte superiore della Scheda PG e nella Hero Summary Card è presente il badge **`✨ Ispirazione DM`**.
  * Può essere conferita dal DM con un click per premiare ottime interpretazioni di ruolo, decisioni audaci o fedeltà ai difetti/legami del personaggio.
  * Il giocatore può spendere l'Ispirazione in qualsiasi momento prima di effettuare un tiro per ottenere immediatamente **Vantaggio** (2d20kh1) a un tiro per colpire, tiro salvezza o prova di caratteristica.

### Gestione Zaini, Contenitori ed Ingombro 5e (RAW PHB p. 143, 176, 190)
OmniCompanion gestisce in modo autentico e conforme alle regole ufficiali D&D 5e la collocazione degli oggetti, lo spazio extradimensionale e il carico corporeo:

1. **Scomparti e Contenitori nell'Inventario**:
   * Ciascun oggetto possiede un badge di collocazione (`container`):
     * `🎒 Zaino` (`backpack`): scomparto predefinito per provviste, attrezzi e attrezzatura da viaggio.
     * `⚔️ Equipaggiato / Addosso` (`equipped`): armi impugnate, armature indossate, scudi e oggetti portati alla cintura o indosso.
     * `🔮 Borsa Conservante` (`bag_of_holding`): spazio extradimensionale (capienza massima 500 lbs / volume 64 piedi cubi). Il peso degli oggetti contenuti non grava sul personaggio.
     * `✨ Zaino Pratico di Heward` (`haversack`): spazio extradimensionale (capienza fino a 120 lbs distribuita nelle tasche, peso proprio dello zaino 5 lbs).
     * `🐴 Sacca da Sella / Cavalcatura` (`mount`): oggetti caricati su cavalli, muli o carri (non gravano sul PG).
   * È possibile impostare o modificare la collocazione di un oggetto direttamente dal dialogo di creazione o modifica con 1 click.

2. **Tattica "Sfila lo Zaino a Terra" (*Drop Backpack*, PHB p. 190)**:
   * Nelle regole 5e sfilarsi lo zaino dalle spalle e lasciarlo cadere a terra è un'**Interazione con Oggetto Gratuita** eseguibile durante il proprio turno di movimento o azione.
   * Nella Scheda PG (tab Inventario) e sulla **Hero Summary Card** della barra laterale è presente il pulsante rapido `[ 🎒 Sfila Zaino a Terra ]` $\leftrightarrow$ `[ 🎒 Raccogli Zaino ]`.
   * Quando lo zaino viene sfilato a terra:
     * Lo stato passa a `⚠️ Zaino a Terra`.
     * Gli oggetti nello zaino vengono contrassegnati visivamente con il tag `[A Terra]`.
     * Il peso di tutti gli oggetti contenuti nello zaino viene **istantaneamente escluso dal carico corporeo trasportato**, consentendo al personaggio di alleggerirsi e ripristinare la velocità piena per combattere o fuggire.
     * L'azione viene annunciata in chat con la citazione della regola RAW.

3. **Regola Variante di Ingombro 5e (Variant: Encumbrance, PHB p. 176)**:
   * **Peso Reale delle Monete**: 50 monete di qualsiasi metallo pesano esattamente 1 libbra (es. 500 MO = 10 lbs di carico alla cintura).
   * **Scaglioni Basati sulla Forza del Personaggio**:
     * **🟢 Normale** ($\le \text{FOR} \times 5\text{ lbs}$): nessuna penalità.
     * **🟡 Ingombrato** ($> \text{FOR} \times 5\text{ lbs}$ fino a $\text{FOR} \times 10\text{ lbs}$): velocità ridotta di **10 ft (3 m)**.
     * **🔴 Gravemente Ingombrato** ($> \text{FOR} \times 10\text{ lbs}$ fino a $\text{FOR} \times 15\text{ lbs}$): velocità ridotta di **20 ft (6 m)** e **Svantaggio** a tutti i tiri per colpire, prove di caratteristica e tiri salvezza basati su Forza, Destrezza o Costituzione.
     * **⛔ Sovraccarico** ($> \text{FOR} \times 15\text{ lbs}$): peso superiore alla capacità massima di carico corporeo; la velocità di movimento scende a **0**.
   * Le penalità di velocità vengono riflesse dinamicamente sul badge velocità della Hero Summary Card e sulla barra del movimento nell'Economia del Turno.

### Economia del Turno: Esplorazione vs Combattimento
La sezione **Economia Turno** nel tab `Controlli PG` si adatta automaticamente alla fase di gioco:

* **Fuori dal Combattimento (`🧭 Modalità Esplorazione - Movimento Libero`)**:
  * L'intestazione mostra **`🧭 Modalità Esplorazione (Movimento Libero)`**.
  * I tre badge (**`⚡ Azione`**, **`✨ Bonus`**, **`🛡️ Reazione`**) sono sempre attivi con tooltip `Libera (Esplorazione)`: puoi muoverti sulla mappa, attaccare o lanciare incantesimi senza che i badge diventino grigi/rossi o ti blocchino.
  * La barra inferiore mostra **`👟 Velocità: 30 ft (Libero)`** (o `9 m (Libero)`), ricordandoti la tua velocità per singolo spostamento senza scalare un budget di turno.
* **Durante il Combattimento (`Economia Turno`)**:
  * Quando il DM avvia il combattimento, l'economia passa in modalità rigorosa D&D 5e sincronizzata con il server.
  * Effettuare un attacco o un'azione standard consuma **`⚡ Azione`**; usare un'azione bonus consuma **`✨ Bonus`**; muoversi sulla griglia scala i piedi/metri dalla barra **`👟 Movimento`**.
  * Puoi anche cliccare manualmente sui singoli badge per segnarli come usati/disponibili (es. se usi una `🛡️ Reazione` per *Scudo* o un *Attacco di Opportunità*), oppure cliccare su **`↺ Reset`** per ripristinarli.
  * Tutte le risorse si **resettano automaticamente** all'inizio di ogni tuo turno e quando il combattimento inizia o termina.

### Azioni in Combattimento, Incantesimi AoE, Copertura e Upcasting
* **Pulsante `⚔️ Azione`**: apre la finestra Azioni Standard 5e:
  * **Attacco con Arma / Incantesimo**: scegli il bersaglio, l'arma, eventuale Vantaggio/Svantaggio e il livello di **Copertura Tattica 5e RAW**:
    * `Copertura Automatica`: raycasting geometrico sulla mappa (`hex_linedraw`) per rilevare muri, porte chiuse o bloccate (`get_effective_map_walls`), coperture e creature interposte (escludendo cadaveri e token invisibili sul livello GM). Le porte chiuse bloccano completamente la linea di vista per gli attacchi a distanza.
    * `Nessuna Copertura`: CA normale del bersaglio.
    * `Mezza Copertura (+2 CA / +2 TS DES)`: bersaglio protetto da un muretto, un albero o un'altra creatura vivente.
    * `Tre Quarti di Copertura (+5 CA / +5 TS DES)`: bersaglio dietro a una feritoia o grata pesante.
    * `Copertura Totale`: il bersaglio è completamente celato; l'attacco viene bloccato.
  * **Colpi Critici Automatici su Bersagli Incoscienti / Paralizzati (PHB p. 291-292)**:
    * Qualsiasi attacco a segno entro 5 piedi (1 casella) contro un bersaglio con condizione *Incosciente* o *Paralizzato* diventa automaticamente un **Colpo Critico**, raddoppiando tutti i dadi di danno.
  * **Resistenze e Vulnerabilità ai Danni Bilingue**:
    * Il motore mappa automaticamente i tipi di danno sia in italiano che in inglese (`fuoco` $\leftrightarrow$ `fire`, `tagliente` $\leftrightarrow$ `slashing`, `radioso` $\leftrightarrow$ `radiant`, ecc.), dimezzando (resistenza) o raddoppiando (vulnerabilità) i danni calcolati.
  * **Azioni Tattiche 5e**: **Scatto (Dash)** (raddoppia il movimento del turno), **Disimpegno (Disengage)** (evita attacchi di opportunità), **Schivata (Dodge)** (infligge svantaggio agli attaccanti e conferisce vantaggio ai propri TS su Destrezza), **Aiuto (Help)** (conferisce vantaggio a un alleato).
* **Pulsante `[ 💥 ]` (Area d'Effetto)**:
  * Scegli la forma geometrica (**Sfera**, **Cono**, **Linea**), la dimensione in esagoni, il colore e (opzionalmente) il Tiro Salvezza richiesto (es. `DES CD 15` con `8d6` danni da fuoco).
  * Clicca sulla mappa per posizionare l'area: il server calcola automaticamente tutti i bersagli coinvolti, richiede i Tiri Salvezza (applicando i bonus di Mezza o 3/4 Copertura se specificati) e applica i danni (dimezzati in caso di successo).
* **Lancio Incantesimi, Scaling Upcasting, Lancio Rituale e Concentrazione Rigorosa (PHB p. 201-204)**:
  * Quando clicchi su **`Lancia`** su un incantesimo dal Grimorio, se l'incantesimo è di 1° livello o superiore appare una finestra modale di scelta dello slot.
  * **Scaling Automatico dei Dadi in Upcast**: scegliendo uno slot di livello superiore al livello base dell'incantesimo, il sistema scala automaticamente la formula di danno o guarigione aggiungendo `+1dX` per ogni livello di slot superiore (es. *Palla di Fuoco* o *Cura Ferite* lanciati con slot superiori).
  * **Lancio come Rituale (`🕯️ Lancia come Rituale (+10 min, 0 slot)`)**: se l'incantesimo possiede il tag *Rituale* (es. *Individuazione del Magico*, *Identificare*, *Trova Famiglio*), la finestra modale mostra una casella di spunta per lanciarlo come rituale aggiungendo 10 minuti al tempo di lancio e **senza consumare alcuno slot incantesimo**.
  * **Concentrazione Rigorosa**:
    * Il sistema riconosce automaticamente gli incantesimi a concentrazione (es. *Benedizione*, *Volare*, *Invisibilità*, *Muro di Fuoco*, *Spiriti Guardiani*).
    * Se lanci un incantesimo a concentrazione mentre ne stai già mantenendo un altro, la vecchia concentrazione cade all'istante con un annuncio pubblico in chat, evitando concentrazioni multiple non consentite dalle regole RAW.
    * Subire danni richiede automaticamente un TS Costituzione ($\text{CD} \ge 10$): in caso di fallimento, l'incantesimo crolla immediatamente.
* **Attacco Poderoso (`-5/+10`) e Combattere con Due Armi (Mano Secondaria - PHB p. 195)**:
  * Nel tab **`⚔️ Armi & Attacchi`** della Scheda PG:
    * **Toggle `⚡ Attacco Poderoso (-5 TxC / +10 Danni)`**: attivabile per i talenti *Maestro d'Armi Possenti (Great Weapon Master)* e *Tiratore Scelto (Sharpshooter)*; sottrae automaticamente `5` al tiro per colpire e aggiunge `+10` ai danni dell'arma.
    * **Pulsante `🗡️ 2ª Mano` (Off-Hand Bonus Attack)**: esegue l'attacco con l'arma secondaria come Azione Bonus omettendo il modificatore positivo di caratteristica dai danni, a meno che il personaggio non possieda lo Stile di Combattimento *Combattere con Due Armi*.
* **Punizione Divina del Paladino (*Divine Smite* - PHB p. 85)**:
  * Nel tab armi, per i Paladini è presente il selettore a tendina dello slot (1°–5° livello).
  * Quando selezionato, all'impatto con un attacco con arma da mischia, il server consuma lo slot e aggiunge automaticamente `+2d8` danni radiosi per il 1° livello, più `+1d8` per ogni livello di slot superiore (max `5d8`).
  * Se il bersaglio appartiene alla categoria **Non Morti** (*Undead*) o **Immondi** (*Fiend*), il danno incrementa automaticamente di un ulteriore `+1d8` (max `6d8`).
  * In caso di Colpo Critico, tutti i dadi di Punizione Divina vengono raddoppiati (`4d8`–`12d8`).
* **Colpo Stordente del Monaco (PHB p. 79) & Dadi di Superiorità del Battle Master (PHB p. 73)**:
  * **Colpo Stordente**: Checkbox dedicato nella barra armi. Spendendo 1 Punto Ki all'impatto, forza il bersaglio a un Tiro Salvezza su Costituzione contro la CD Ki del Monaco ($8 + \text{PB} + \text{Mod SAG}$); in caso di fallimento, la creatura subisce lo status **Stordito (Stunned)** fino al termine del turno successivo del monaco.
  * **Dadi di Superiorità**: Pool spendibile (`d8`, `d10`, `d12`) con pulsante rapido `[ 🎲 Spendi Dado Superiorità ]` per l'esecuzione di manovre marziali, con notifica in chat e ricarica a riposo breve o lungo.
* **Critico Migliorato (Campione 19-20 / 18-20) & Dadi Critico Brutale (PHB p. 49, 72, 73)**:
  * Riconoscimento automatico del colpo critico espanso a 19–20 (livello 3) o 18–20 (livello 15) per il Guerriero Campione.
  * Dadi aggiuntivi di danno dell'arma sui colpi critici in mischia per il *Critico Brutale* del Barbaro e gli *Attacchi Selvaggi* del Mezzorco.
* **Tracciamento Attacco Extra nell'Economia del Turno (PHB p. 72, 79, 85, 91)**:
  * I combattenti dotati del privilegio *Attacco Extra* (fino a 4 attacchi per il Guerriero di 20° livello) possono eseguire attacchi multipli all'interno della stessa Azione senza consumare anticipatamente l'azione di turno prima di aver completato tutti i colpi a disposizione.
* **Azione Preparare (*Ready Action* - PHB p. 193)**:
  * Nella barra **Economia Turno** del VTT è presente il pulsante **`[ ⏱️ Prepara ]`**:
    * Consente di spendere l'**Azione** del proprio turno per dichiarare una condizione di innesco (*trigger*, es. *"Appena il goblin entra nella stanza"*) e il tipo di risposta (**Attacco**, **Movimento** o **Incantesimo**).
    * Come da regole RAW 5e, preparare un **Incantesimo** attiva immediatamente la **Concentrazione** dell'incantatore.
    * Quando l'innesco si verifica fuori dal proprio turno, il pulsante diventa **`[ ⚡ Innesca ]`**: cliccandolo il personaggio spende la propria **`🛡️ Reazione`** ed esegue l'azione preparata!
* **Pulsante `⏭️ Termina Turno`**: attivo durante il tuo turno di combattimento; passa immediatamente l'iniziativa al combattente successivo.

### Targeting Tattico con Mirino, Fiancheggiamento (DMG p. 251) e Manovre RAW (Lotta & Spinta)
OmniCompanion introduce un sistema integrato di ingaggio tattico sulla mappa:

1. **Mirino Tattico & Linea di Tiro Dinamica (Raycasting & Cover)**:
   * **Selezione del Bersaglio**: Clicca su un token nemico oppure usa **`Shift + Click Sinistro`** su qualsiasi token della mappa (o tasto destro $\to$ **`🎯 Bersaglia Token`**).
   * **Mirino a 4 Tacche**: Sul token agganciato compare un mirino circolare rosso neon pulsante con 4 tacche di collimazione e badge informativo fluttuante.
   * **Linea di Tiro / Copertura Dinamica**: Dal token del giocatore al bersaglio viene proiettata una linea tratteggiata codificata per colore in base al raycasting degli ostacoli:
     * 🟢 **Verde Smeraldo**: Linea di vista libera, nessuna copertura (+0 CA).
     * 🔷 **Ciano / Blu Elettrico**: Mezza Copertura (+2 CA / +2 TS DES, es. feritoia leggera o muretto parziale).
     * 🟧 **Ambra / Arancio Intenso**: Tre Quarti di Copertura (+5 CA / +5 TS DES, es. feritoia stretta o creatura interposta).
     * 🔴 **Rosso Neon**: Linea di vista bloccata da muro o ostacolo solido (nessun attacco a distanza consentito).
   * **HUD Bersaglio Attivo**: Nella barra laterale dei Controlli PG compare il badge `🎯 Bersaglio: [Nome] [ ✕ ]`. Cliccando su `[ ✕ ]` o ripremendo `Shift + Click` il bersaglio viene sganciato. Quando un bersaglio è agganciato, il pulsante **`⚔️ Azione`** apre l'attacco pre-impostato direttamente su di esso senza doverlo riselezionare manualmente.

2. **Fiancheggiamento Opzionale (Flanking - DMG p. 251)**:
   * Quando l'opzione è attiva nelle impostazioni del DM (`enable_flanking`), due alleati posizionati su lati opposti rispetto a una creatura nemica concedono reciprocamente **Vantaggio (2d20kh1)** a tutti gli attacchi in mischia ($dist \le 1$ casella).
   * Il sistema calcola l'opposto geometrico sulla griglia esagonale o quadrata ($2 \cdot q_{\text{bersaglio}} - q_{\text{attaccante}}, 2 \cdot r_{\text{bersaglio}} - r_{\text{attaccante}}$). Se un alleato cosciente e non incapacitato si trova su tale casella, il bonus viene applicato automaticamente con annuncio esplicito in chat.

3. **Manovre di Lotta & Spinta RAW 5e (Grapple & Shove - PHB p. 195)**:
   * Direttamente dai pulsanti rapidi **`[ 🤼 Lotta ]`** e **`[ 💨 Spingi ]`** (o dal menu contestuale col tasto destro sul token del bersaglio):
     * **🤼 Lotta (Grapple)**: Richiede una contesa tra l'**Atletica (Forza)** dell'attaccante e l'**Atletica (Forza)** o **Acrobazia (Destrezza)** del difensore (a scelta del valore più alto per il difensore). Il bersaglio non può essere più di 1 taglia superiore all'attaccante. In caso di successo, al bersaglio viene applicata la condizione **Afferrato (Grappled)** che azzera istantaneamente la velocità di movimento (`speed = 0`).
     * **💨 Spinta (Shove)**: Contesa analoga di Forza (Atletica). L'attaccante può scegliere tra **Atterrare Prono** (infliggendo la condizione **Prono**, che concede vantaggio agli attacchi in mischia entro 5 ft) oppure **Spingere Indietro di 5 ft** (la creatura viene respinta lungo il vettore di attacco verso la casella successiva, fermandosi in sicurezza qualora vi sia un muro o un ostacolo impraticabile).
     * **Supporto Condizioni RAW**: Sia per Lotta che per Spinta, l'Ira barbarica conferisce automaticamente Vantaggio alle prove di Forza (Atletica), l'Indebolimento o la Paura infliggono Svantaggio, e le creature Incapacitate, Incoscienti o Paralizzate falliscono automaticamente la contesa.

### Spazio 3D, Quota & Elevazione, Cadute RAW (PHB p. 183) e Concentration Tethers
D&D OmniCompanion gestisce nativamente la tridimensionalità dei combattimenti e il ciclo di vita della concentrazione visiva:

1. **Quota 3D & Altitudine dei Token (Volo, Arrampicata e Dislivelli)**:
   * **Impostazione Quota**: Ogni token possiede un'altitudine tridimensionale $Z$ (in piedi, convertibile a runtime in metri).
   * **Interfaccia e Controlli**:
     * **HUD Controlli PG**: Pulsante rapido `[ 📐 0ft ]` / `[ ⬆ 30ft ]` nella Hero Summary Card.
     * **Menu Contestuale Token**: Clic destro su qualsiasi token $\to$ **`📐 Imposta Quota 3D...`** per aprire la finestra di configurazione quota con preset rapidi (`0 ft Suolo`, `10 ft`, `20 ft`, `30 ft Volo`, `60 ft`).
     * **Comandi Chat Slash**: `/quota <valore>` (es. `/quota 30`, `/quota 9m`), `/elevation`, `/vola`, `/fly`.
   * **Visualizzazione Canvas & Ombre Proiettate**:
     * I token in quota vengono traslati verticalmente sul canvas proporzionalmente all'altitudine e allo zoom.
     * Al suolo viene proiettata l'ombra della creatura unita a una linea guida tratteggiata verticale di quota.
     * Un badge ciano/blu o marrone (es. `⬆ 30ft` o `⬆ 9m` / `⬇ 10ft`) indica l'altitudine esatta accanto al token.
   * **Distanze 3D & Portata in Mischia**:
     * Il motore calcola la distanza tridimensionale euclidea ($D_{\text{3D}} = \sqrt{D_{\text{2D}}^2 + \Delta z^2}$).
     * Se una creatura volante è a 30 ft di quota, gli attacchi in mischia da terra non possono raggiungerla ($D_{\text{3D}} > 1\text{ casella}$), proteggendola dagli attacchi corpo a corpo senza armi con portata o volo.

2. **Risoluzione Cadute RAW 5e (Falling - PHB p. 183)**:
   * **Danno da Caduta**: $1\text{d6}$ danni contundenti per ogni 10 piedi di caduta, fino a un massimo ufficiale di **$20\text{d6}$**.
   * **Condizione Prono**: All'atterraggio la creatura diventa automaticamente **Prono**, a meno che non eviti completamente il danno.
   * **Mitigazioni Ufficiali RAW**:
     * **Caduta Lenta del Monaco (Slow Fall, liv. 4+)**: Riduce il danno da caduta di $5 \times \text{livello Monaco}$. Se il danno scende a 0, il monaco atterra in piedi senza cadere Prono.
     * **Caduta Morbida (Feather Fall)**: Annulla completamente i danni da caduta e consente di atterrare dolcemente sui propri piedi.
   * **Caduta Automatica su Perdita di Volo (PHB p. 191)**:
     * Una creatura volante a quota elevata priva di volo stazionario (*hover*) che viene atterrata **Prono** (es. tramite Spinta) o ridotta a **0 HP** o resa **Incosciente/Paralizzata/Stordita** precipita immediatamente al suolo subendo i relativi danni da caduta.

3. **Fasci Eterei di Concentrazione (Concentration Tethers)**:
   * Quando un incantatore mantiene la concentrazione su un bersaglio (es. *Benedizione*, *Blocca Persone*, *Volare*, *Cacciatore di Nemici*) o su un'area AoE persistente (es. *Muro di Fuoco*, *Spiriti Guardiani*), il canvas disegna eleganti **fasci eterei violacei e smeraldo** (`Concentration Tethers`) che collegano visivamente l'incantatore ai suoi bersagli con una runa magica `✦`.
   * **Interruzione a Catena**: Se la concentrazione dell'incantatore crolla (subendo danni e fallendo il TS su Costituzione, o cadendo a 0 HP), tutti gli effetti legati e le aree AoE svaniscono all'istante, e qualsiasi creatura sorretta in volo dall'incantesimo cade immediatamente al suolo risolvendo la caduta RAW.

### Reazioni RAW (*Scudo*, *Assorbire Elementi*, *Controincantesimo*, *Deviare Proiettili*)
* **Economia delle Reazioni RAW (PHB p. 190)**:
  * Ogni creatura dispone di una sola `🛡️ Reazione` per round, che si ripristina all'inizio del proprio turno.
  * Il sistema monitora in tempo reale gli eventi scatenanti (*triggers*) che avvengono durante i turni degli altri combattenti.
* **Prompt di Reazione per l'Incantesimo Scudo (*Shield*)**:
  * Quando un attacco nemico supera la CA di un personaggio (o quando viene bersagliato da *Dardo Incantato*), se l'eroe conosce o ha preparato l'incantesimo *Scudo* e dispone della propria reazione e di almeno uno slot di 1° livello o superiore, il client visualizza un prompt interattivo con conto alla rovescia:
    * Se il giocatore accetta: consuma la `🛡️ Reazione` del round, scala uno slot di 1° livello e aggiunge un bonus invisibile di **+5 alla Classe Armatura (CA)** fino all'inizio del suo prossimo turno.
    * **Risoluzione Retroattiva**: Se il nuovo punteggio di CA ($CA + 5$) è superiore o uguale al tiro per colpire dell'avversario, l'attacco viene retroattivamente convertito da "Colpito" a "Mancato", salvando il personaggio dai danni!
* **Assorbire Elementi (*Absorb Elements*), Controincantesimo (*Counterspell*) e Deviare Proiettili (*Deflect Missiles*)**:
  * **Assorbire Elementi**: attivabile in reazione quando si subiscono danni da *Acido, Freddo, Fuoco, Fulmine o Tuono*; consuma la reazione e uno slot di 1° livello, conferisce resistenza al danno elementale e aggiunge `+1d6` danni al prossimo attacco in mischia.
  * **Controincantesimo**: interrompe il lancio di un incantesimo nemico entro 60 piedi spendendo la reazione e uno slot di 3° livello o superiore.
  * **Deviare Proiettili (Monaco liv. 3+)**: riduce i danni di un attacco con arma a distanza subito di `1d10 + Mod DES + Livello Monaco` spendendo la reazione.
* **Attacchi di Opportunità Dinamici & Reazioni Fuori Turno**:
  * Quando un nemico adiacente (a distanza di 1 esagono / $5\text{ ft}$) si allontana uscendo dalla portata di mischia senza aver intrapreso l'azione di *Disimpegno (Disengage)*, il server rileva l'apertura e invia una notifica al difensore permettendogli di spendere la sua `🛡️ Reazione` per sferrare un attacco immediato in mischia.
  * **Bypass del Blocco Turno (`is_reaction=True`)**: Le reazioni legittime e gli Attacchi di Opportunità aggirano il blocco rigido del turno (`strict_turn_lock`), consentendo di agire istantaneamente durante il movimento del nemico senza interrompere la sequenza dell'iniziativa.

### Aure Dinamiche (*Aura di Protezione* & *Spiriti Guardiani*), Tratti Razziali e Sopravvivenza a 0 PV
* **Aura di Protezione del Paladino (PHB p. 85)**:
  * I Paladini coscienti di 6° livello o superiore proiettano automaticamente un'aura protettiva di 10 piedi / 2 esagoni (estesa a 30 piedi / 6 esagoni al 18° livello) che somma il **Modificatore di Carisma** del Paladino ($\min +1$) a tutti i Tiri Salvezza effettuati dal Paladino stesso e dagli alleati entro il raggio.
* **Spiriti Guardiani (*Spirit Guardians*, PHB p. 278)**:
  * Mantenendo la concentrazione su *Spiriti Guardiani*, qualsiasi creatura ostile che inizi il proprio turno entro 15 piedi (3 esagoni) dall'incantatore subisce automaticamente un Tiro Salvezza su Saggezza contro la CD incantesimi dell'incantatore, subendo `3d8` danni radiosi (o la metà in caso di successo).
* **Tenacia Implacabile (Mezzorco) e Interdizione alla Morte (*Death Ward*)**:
  * Se un personaggio dotato di *Tenacia Implacabile* (1/Riposo Lungo) o protetto da *Interdizione alla Morte* subisce danni che lo ridurrebbero a `0 PV` senza ucciderlo sul colpo, il motore intercetta l'evento e lo lascia automaticamente a **`1 PV`**, annunciando l'attivazione in chat!
* **Fortuna dell'Halfling (*Fortunato*) e Combattere con Armi Possenti (*GWF*)**:
  * **Fortuna dell'Halfling**: ritira automaticamente qualsiasi `1` naturale ottenuto su un tiro di `d20` (tiro per colpire, prova di caratteristica o tiro salvezza).
  * **Combattere con Armi Possenti (*Great Weapon Fighting*)**: ritira automaticamente gli `1` e i `2` sui dadi di danno delle armi da mischia a due mani o versatili.
* **Evasione (*Evasion*, PHB p. 79/96)**:
  * Per Ladri e Monaci di 7° livello o superiore, l'agilità istintiva trasforma la gestione degli effetti ad area che richiedono un Tiro Salvezza su Destrezza (es. *Palla di Fuoco*, soffio di drago):
    * **TS Superato**: subiscono **0 danni** (invece della metà normale).
    * **TS Fallito**: subiscono solo la **metà del danno** (invece del danno pieno).
  * Il motore di gioco riconosce automaticamente la classe e il livello dell'entità coinvolta applicando la riduzione senza necessità di calcoli manuali.
* **Attacco Furtivo (*Sneak Attack*, PHB p. 96)**:
  * Quando un Ladro mette a segno un attacco, il sistema valuta automaticamente i requisiti RAW:
    * L'arma deve essere **Accurata (*Finesse*)** o un'arma a **Distanza**.
    * L'attaccante ha **Vantaggio** al tiro per colpire, OPPURE un alleato del ladro è entro 1 esagono ($5\text{ ft}$) dal bersaglio, non è inabile e il ladro **non ha Svantaggio**.
    * La meccanica è limitata a **una sola volta per turno**.
  * Al verificarsi delle condizioni, il server calcola e somma automaticamente i dadi di danno extra previsti per il livello del ladro (da $+1d6$ a livello 1 fino a $+10d6$ a livello 19), annunciando l'attacco furtivo nel registro di combattimento.

### Punti Ferita, Riposi e Tiri Salvezza contro la Morte
* **Scendere a 0 PV, Danni e Morte Istantanea (PHB p. 197)**:
  * Quando i PV scendono a 0, il personaggio perde automaticamente la `Concentrazione` e riceve le condizioni `Incosciente` e `Prono`. Se il danno residuo in eccesso è $\ge \text{PV Massimi}$, si verifica la **Morte Istantanea**.
  * **Subire Danni a 0 PV**: Ogni volta che un personaggio a 0 PV subisce danni, registra automaticamente **1 fallimento** ai tiri contro la morte (o **2 fallimenti** se il danno deriva da un Colpo Critico).
  * **Morte Permanente e Cadavere Lootabile**: Al terzo fallimento accumulato, il personaggio riceve lo status permanente di `💀 Morto`; il server genera automaticamente un token cadavere interattivo sul terreno di scontro contenente l'equipaggiamento e il bottino recuperabile dal party.
  * **Cure a 0 PV**: Ricevere una guarigione a 0 PV ripristina immediatamente la salute, **azzera completamente il conteggio di successi e fallimenti** dei tiri contro la morte, e rimuove all'istante le condizioni `Incosciente` e `Stabilizzato`.
* **Tiri Salvezza contro la Morte (All'Inizio del Turno)**:
  * All'inizio del tuo turno a 0 PV (o digitando `/ds` / `/tsmorte` in chat, o dalla Scheda PG) esegui il Tiro contro la Morte:
    * **`20 Naturale`**: torni immediatamente a **1 PV** e perdi la condizione `Incosciente`!
    * **`10–19`**: +1 Successo (a 3 successi diventi `Stabilizzato`).
    * **`2–9`**: +1 Fallimento.
    * **`1 Naturale`**: **+2 Fallimenti** (a 3 fallimenti il personaggio muore permanentemente).
* **Riposo Breve e Riposo Lungo (RAW PHB p. 186)**:
  * **Spesa Dadi Vita nel Riposo Breve (`ShortRestDialog`)**:
    * Cliccando su **`Riposo Breve`** nella Scheda PG si apre la nuova finestra modale interattiva:
      * Visualizza i PV attuali e massimi con **barra della salute progressiva** e il numero esatto di **Dadi Vita rimanenti** (es. `3 / 5 (d8)`).
      * **Pulsante `🎲 Spendi 1 Dado Vita`**: tira un singolo dado della classe ($1\text{dY} + \text{Mod. Costituzione}$, con guarigione minima di 1 PV anche con COS negativa), incrementa i PV fino al massimale e aggiorna la cronologia progressiva dei tiri in tempo reale.
      * **Pulsante `⚡ Spendi Tutti i Dadi Vita`**: spende automaticamente i dadi rimanenti fino al raggiungimento dei PV massimi o all'esaurimento dei dadi.
      * **Pulsante `✅ Concludi Riposo`**: chiude il dialogo, annuncia pubblicamente in chat il recupero totale e i dadi spesi, e ricarica i privilegi a riposo breve (es. *Secondo Fiato*, *Azione Impetuosa*, e slot da *Patto del Warlock*).
  * **Riposo Lungo**: ripristina tutti i PV, tutti gli Slot Incantesimo, azzera i livelli di Indebolimento (Exhaustion -1), ricarica tutte le risorse di classe e **recupera fino a metà dei Dadi Vita totali** del personaggio ($\max(1, \lfloor\text{Totale}/2\rfloor)$ come da regole RAW 5e).

### Inventario, Ingombro, Scambi e Richieste al DM
* **Regole di Approvazione Master Anti-Cheat & Integrità Scheda (Online & Offline)**:
  * **Blocco Aggiunta/Rimozione Autonoma da SRD**: I giocatori non possono inserire arbitrariamente nuovi oggetti nell'inventario né incantesimi nel grimorio sfogliando l'SRD compendium, né rimuoverli a proprio piacimento senza l'approvazione del Dungeon Master.
  * Questa regola opera rigorosamente **sia durante le sessioni connesse, sia in modalità offline durante la gestione del personaggio**, garantendo la fedeltà alla narrazione del Master e impedendo alterazioni arbitrarie dell'equipaggiamento e della lista incantesimi.
  * Qualsiasi aggiunta o rimozione genera una richiesta formale di approvazione al DM (`ITEM_APPROVAL_REQUEST` / `SPELL_APPROVAL_REQUEST`) o rimane bloccata in attesa di convalida.
* **Sincronizzazione Valute & Calcolo Dinamico del Peso**:
  * **Sincronizzazione Bidirezionale**: Le monete possedute (`MR`, `MA`, `ME`, `MO`, `MP`) sono sincronizzate in tempo reale tra la lista dell'inventario e la tabella superiore delle valute. Modificare le monete nella tabella superiore aggiorna istantaneamente la borsa delle monete nell'inventario e viceversa.
  * **Peso Reale Corretto (RAW PHB p. 143)**: Il peso dell'inventario non è più azzerato o statico, ma riflette fedelmente il peso sommato di tutti gli oggetti fisici, munizioni, armi, armature e il peso reale delle monete ($50\text{ monete} = 1\text{ lb}$).
* **Gestione Comoda Contenitori & Spazi Extradimensionali**:
  * Assegnazione immediata a `🎒 Zaino`, `⚔️ Equipaggiato`, `🔮 Borsa Conservante`, `✨ Zaino Pratico`, o `🐴 Cavalcatura`.
  * Il peso degli oggetti contenuti in spazi extradimensionali (es. *Borsa Conservante*, fino a 500 lbs) viene escluso dal carico corporeo del personaggio, preservandone la mobilità.
* **Materiali di Consumo Spendibili (`[-1]` / `[+1]`) & Pozioni di Cura**:
  * Nella riga di ciascun oggetto di consumo (frecce, quadrelli, dardi, razioni, torce, fiale d'olio, pozioni) sono presenti comodi pulsanti rapidi `[-1]` e `[+1]` per spendere o reintegrare una singola unità con 1 click senza dover aprire finestre di modifica.
  * **Sincronizzazione Cura Istantanea**: L'assunzione di pozioni di cura o consumabili terapeutici aggiorna istantaneamente sia il contatore numerico e la barra dei PV sulla scheda, sia lo stato memorizzato sul server di gioco.
* **Diario e Note con Markdown & Convalida Master**:
  * Il diario di campagna e le note personali della Scheda PG supportano il rendering visivo completo in Markdown (`**grassetto**`, `*corsivo*`, elenchi puntati, titoli).
  * La modifica del diario e delle cronache richiede l'approvazione del Master per preservare la coerenza della storia.
* **Scambi con Alleati Sicuri (`Dai` / `🤝 Dai Oro a Compagno`)**:
  * Puoi trasferire oggetti o monete direttamente a un altro giocatore connesso.
  * **Anti-Duplicazione**: Lo slot nell'inventario del mittente viene svuotato preventivamente prima dell'invio e della conferma da parte del destinatario, impedendo qualsiasi duplicazione accidentale di oggetti anche in condizioni di latenza di rete.

### Spoglie dei Mostri (Loot Drop DMG p. 133) e Recupero 50% Munizioni RAW (PHB p. 146)
D&D OmniCompanion automatizza l'economia post-combattimento secondo le regole autentiche della Guida del Dungeon Master e del Manuale del Giocatore:

1. **Spoglie dei Mostri & Drop Bottino Dinamico (DMG p. 133)**:
   * Alla morte di un mostro o PNG (`hp <= 0` o eliminazione durante lo scontro), il server genera automaticamente sulla mappa un contenitore di spoglie (`Spoglie di [Nome]`).
   * **Monete Generate per Grado di Sfida (CR)**:
     * **CR 0–4**: genera una borsa di monete contenente $3\text{d6}$ Monete d'Argento (MA) e $2\text{d6}$ Monete d'Oro (MO).
     * **CR 5–10**: genera un tesoro di $4\text{d6} \times 10$ Monete d'Oro (MO).
     * **CR 11+**: tesori epici con monete d'oro e platino.
   * **Equipaggiamento Recuperabile**: tutti gli oggetti presenti nell'inventario del mostro (armi, armature, pozioni, pergamene) vengono inseriti nelle spoglie.
   * **Raccolta Istantanea**: un personaggio posizionato sulle spoglie o che interagisce con esse riceve immediatamente le monete nel proprio portafoglio e gli oggetti nello zaino, con notifica e annuncio pubblico in chat.

2. **Tracciamento e Recupero 50% Munizioni RAW (PHB p. 146)**:
   * Nelle regole di D&D 5e, al termine di un combattimento un arciere o balestriere può impiegare 1 minuto per recuperare la metà (50%) di tutte le munizioni scagliate durante la battaglia.
   * **Tracciamento Automatico**: ogni attacco a distanza con arco, balestra, fionda o dardi tiene traccia delle munizioni consumate nel turno.
   * **Recupero Automatico a Fine Scontro**: quando il DM preme **`Termina Combattimento`**, il server calcola automaticamente $\lfloor \text{munizioni} / 2 \rfloor$ per ciascun eroe, le ripristina all'istante nello zaino e invia un report dettagliato in chat (es. `🏹 Legolas recupera 4x Frecce dal campo di battaglia!`).
   * **Pulsante e Comando Rapido**: il giocatore può attivare il recupero in qualsiasi momento cliccando sul pulsante **`[ 🏹 Munizioni ]`** nella terza riga dei Controlli PG oppure digitando `/recupera_munizioni` (o `/ammo_recover`, `/munizioni`) in chat.

### Esportazione Scheda Personaggio (PDF Ufficiale D&D 5e e JSON)
In fondo alla finestra della Scheda PG trovi il pulsante **`📥 Esporta Scheda...`**: cliccandolo si apre una finestra modale dedicata che ti permette di scegliere chiaramente tra due formati:
* **📄 Scheda Ufficiale D&D 5e (PDF)**: richiede in input di selezionare il file PDF del modello vuoto ministeriale a 3 pagine (es. `dnd_blankcharactersheet_it.pdf`, non caricato su Git per ragioni di copyright e dimensioni) e compila direttamente la scheda. Include:
  - **Pagina 1**: Intestazione completa, Caratteristiche e Modificatori centrati nei riquadri ufficiali, Ispirazione, Bonus di Competenza, Tiri Salvezza con spunte nere di competenza, 18 Abilità (con pallino pieno per competenza o doppio cerchio per maestria), Percezione Passiva, Classe Armatura nello scudo, Iniziativa, Velocità, Punti Ferita massimi, attuali e temporanei, Dadi Vita totali e rimanenti, Tiri Salvezza contro la Morte compilati, Tabella Armi con bonus e danni/tipo, Monete nei rispettivi esagoni (MR, MA, ME, MO, MP), Equipaggiamento/Inventario, Tratti Caratteriali, Ideali, Legami, Difetti e Privilegi di Classe (con tracciamento risorse speciali come Ira, Secondo Fiato, Punti Ki).
  - **Pagina 2**: Dettagli del personaggio, età, altezza, peso, occhi, pelle, capelli, aspetto fisico, alleati e organizzazioni, storia del personaggio (backstory) e tesoro.
  - **Pagina 3 (Grimorio)**: Classe da incantatore, caratteristica chiave, CD Tiro Salvezza, Bonus Attacco Incantesimi, slot totali e spesi per ciascun livello da 1 a 9, ed elenco completo degli incantesimi con spunta di preparazione.
* **💾 File Dati Personaggio (JSON)**: salva la struttura dati pura del personaggio (`.json`) formattata con indentazione, ideale per backup rapidi, modifiche testuali avanzate o per importare il personaggio in altre campagne o installazioni.

### Macro Hotbar (Slot Rapidi 1–10)
In fondo alla finestra del Giocatore è presente una barra con **10 pulsanti numerati (`1`–`10`)**:
* **Click Destro su uno slot**: assegna un nome e un comando o tiro rapido (es. `Spada Lunga` $\rightarrow$ `/roll 1d20+6`, oppure `/ds`).
* **Click Sinistro su uno slot**: esegue immediatamente la macro. Le macro vengono salvate nel profilo del personaggio.

### Diario Narrativo di Campagna e Memorie Personali (Player)
I giocatori possono consultare in qualsiasi momento la storia viva dell'avventura dal menu **`Libreria -> 📖 Diario Narrativo di Campagna...`** o dal pulsante rapido **`[ 📓 ]`** posto nella barra verticale degli strumenti di sinistra:
* **Indice Storico Multi-Sessione**: sfoglia l'elenco cronologico di tutte le sessioni giocate (Sessione 1, 2, 3...) con data reale, calendario di Harptos, meteo e ambientazione geografica.
* **Cronaca Narrativa Ufficiale**: leggi il resoconto in prosa pura approvato dal Dungeon Master, senza statistiche aride o gergo di sistema.
* **Memorie Personali dell'Eroe (Tab `✏️ Memorie Personali`)**: un blocco note privato legato al proprio personaggio in cui annotare pensieri, sospetti, indizi o promemoria specifici per quella sessione, salvabili localmente con il pulsante `[ 💾 Salva Memorie ]`.
* **Registro Eventi Chiave**: linea temporale degli eventi salienti (combattimenti, trappole disinnescate, tesori raccolti, riposi).
* **Esportazione a Portata di Click**: esporta il diario in pergamena dark fantasy HTML (`.html`), documento Markdown (`.md`) o copia negli appunti un recap pronto per essere incollato su Discord o WhatsApp.

---

## 5. Guida per il Dungeon Master (DM)

### Stili di Gestione della Campagna (DM Agency vs Full Automation) e Barra Decisioni
D&D OmniCompanion offre al Dungeon Master il pieno controllo sull'equilibrio tra **automazione informatica** e **arbitraggio umano (DM Agency)**, garantendo che il software non sostituisca mai la voce, il ritmo e le scelte narrative del Master:

* **I 3 Profili Preimpostati**:
  * **🎲 Tavolo Tradizionale (Pen & Paper / Controllo DM RAW)**:
    * Esperienza pura cartacea. Nessuna modifica irreversibile alle schede avviene a scatola chiusa.
    * Quando viene sferrato un attacco o lanciata una magia AoE, i danni non vengono sottratti in automatico: il sistema calcola la proposta numerica e la invia alla **Barra Fluttuante delle Decisioni del DM** per approvazione o modifica.
    * Le porte chiuse lasciano spazio all'interazione narrativa e alla descrizione del DM (es. serrature arrugginite, trappole con aghi avvelenati), senza che un click apra direttamente la stanza.
    * La concentrazione dei personaggi non viene infranta silenziosamente e i Tiri Salvezza contro la Morte o 0 HP vengono gestiti con il giusto pathos al tavolo.
  * **⚖️ Ibrido Assistito (Consigliato per Sessioni Fluide)**:
    * Il perfetto equilibrio per le sessioni moderne. Il motore gestisce la contabilità complessa (resistenze ai danni, coperture, visibilità al buio, penalità dei terreni difficili e condizioni), mentre il DM riceve schede decisionali a 1-click (`[Pieno]`, `[Dimezza]`, `[Modifica]`, `[Annulla]`) per confermare o modulare gli esiti all'istante.
  * **⚡ Full Automation (CRPG / Tattico Rapido)**:
    * Modalità stile videogioco tattico. I danni vengono applicati istantaneamente ai PV, le porte si sbloccano su successo della CD, i turni sono bloccati rigidamente per i giocatori non attivi e le reazioni/TS partono in automatico.
* **Come Cambiare Profilo al Volo**:
  * Clicca sul badge colorato **`🎲 Tavolo`**, **`⚖️ Ibrido`** o **`⚡ Full Auto`** posizionato nella barra superiore della mappa.
  * Oppure apri il pannello completo da **`Strumenti -> ⚙️ Stile Gestione Campagna (Automazioni)...`**.
* **12 Switch Granulari Indipendenti**:
  * Dalla finestra di configurazione il DM può personalizzare singolarmente ciascun aspetto:
    1. `auto_attack_damage`: applicazione automatica danni da attacchi con armi.
    2. `auto_aoe_damage`: applicazione automatica danni da magie AoE.
    3. `auto_concentration`: prove automatiche di Concentrazione (TS COS).
    4. `auto_advantage_disadvantage`: calcolo automatico Vantaggio/Svantaggio 5e.
    5. `auto_critical_damage`: raddoppio automatico dadi sui critici Nat 20.
    6. `auto_traps`: innesco e danno automatico delle trappole.
    7. `auto_turn_economy`: blocco rigido del turno fuori dal proprio ordine.
    8. `auto_spell_slots`: deduzione automatica degli slot incantesimo al lancio.
    9. `auto_encumbrance`: blocco del movimento in caso di sovraccarico di peso.
    10. `auto_death_saves`: gestione automatica TS morte a 0 PV.
    11. `auto_weather_effects`: applicazione automatica svantaggi da tempesta, nebbia e pioggia.
    12. `auto_distribute_xp`: calcolo e ripartizione automatica dei Punti Esperienza (XP) dai mostri sconfitti a fine scontro con notifiche di avanzamento livello (PHB p. 15). Disattivabile per campagne a Milestone o calcoli manuali.
* **Barra Fluttuante delle Decisioni DM in Sospeso (*Pending Actions Dock*)**:
  * Quando è attivo il profilo Tradizionale o Ibrido e un evento richiede l'intervento del Master (es. danno in arrivo, richiesta di riposo, scasso o trappola), in basso al centro appare un dock ergonomico non invasivo:
  * Mostra il dettaglio dell'evento (es. `Attacco su Gildor: 14 Danni Taglienti`) e offre comodi pulsanti:
    * `[ ✅ Applica ]` — convalida ed esegue l'azione con un click.
    * `[ ✂️ Dimezza (Resistenza) ]` — dimezza il valore prima di applicarlo.
    * `[ ✏️ Modifica ]` — permette di digitare un importo numerico differente.
    * `[ ❌ Nega / Annulla ]` — respinge l'azione senza alcuna modifica allo stato di gioco.

### Gestione Campagne, Atti, Scene e Starter Pack
Dal menu **`File`** e **`Strumenti`** della plancia DM:
* **Nuova Campagna / Editor Campagna Attiva**: organizza la tua avventura in **Atti**, **Scene** (ciascuna collegata a un file mappa e a tracce audio), **PNG** e **Incontri preparati**.
* **Pulsante `🗺️ Cambia Scena`** (nel tab `Iniziativa & PG`): carica istantaneamente la mappa della scena selezionata e la trasmette a tutti i giocatori.
* **Pulsante `⚔️ Schiera Incontro`**: posiziona con un solo click tutti i mostri di un incontro preparato sulla mappa attiva.
* **Starter Pack Campagna (`Strumenti -> Starter Pack Campagna`)**: configura la lista di oggetti iniziali (es. Razioni, Torcia, Pozione di Guarigione) che ogni nuovo personaggio riceverà automaticamente al suo primo ingresso nella campagna.

### Diario Narrativo di Sessione Continuativo (Campaign Adventure Journal)
Il **Diario Narrativo di Campagna** è il cuore della memoria dell'avventura: non un semplice file di log disconnesso per singola giocata, ma un **libro continuativo multi-sessione** legato alla campagna, accessibile da **`File -> 📖 Diario Narrativo di Campagna...`** o dal pulsante **`[ 📖 Diario ]`** nella scheda della campagna attiva:
* **Architettura Continuativa**: ogni sessione viene registrata in sequenza (Sessione 1, Sessione 2, Sessione 3...) preservando la storia completa del gruppo dall'inizio al termine della campagna.
* **Cattura Automatica degli Eventi**: il motore di gioco traccia automaticamente in background tutti gli avvenimenti salienti:
  - Inizi e conclusioni dei combattimenti con elenco nemici.
  - Mostri sconfitti e personaggi che scendono a 0 PF (con attacchi mortali o salvataggi).
  - Serrature scassinate, porte forzate e trappole individuate/disinnescate.
  - Bottini e tesori raccolti dai cadaveri o forzieri.
  - Riposi Brevi e Riposi Lunghi con ripristino risorse.
  - Data reale e temporale (Calendario Harptos), meteo e posizione geografica.
* **Sintesi Narrativa RPG Immersiva**: con il pulsante **`↺ Rigenera Sintesi Narrativa`**, il sistema analizza tutti gli eventi della sessione e li fonde in una prosa fluida e pulita suddivisa per sezioni tematiche (*Esplorazione & Percorso*, *Pericoli & Trappole*, *Fatti d'Arme & Combattimenti*, *Spoglie & Tesori*, *Bivacco & Riposo*). Non una cantata bardica in rima né un freddo resoconto statistico, ma una cronaca autentica di gioco di ruolo.
* **Editing e Note Riservate del DM (Anti-Metagame)**:
  - Il DM può modificare liberamente il titolo e il testo della prosa nella scheda principale.
  - Nella scheda **`🔒 Note Private DM`**, il Master può inserire segreti di trama, retroscena su PNG e piani futuri. Queste note sono protette e **non vengono mai inviate ai giocatori**.
* **Sincronizzazione in Tempo Reale (`📢 Trasmetti ai Giocatori`)**: con un solo click, il DM trasmette l'intera cronaca aggiornata a tutti i giocatori connessi, che ricevono una notifica dorata e visualizzano il diario nei propri client.
* **Nuova Sessione e Archiviazione**:
  - `[ ➕ Nuova Sessione ]`: archivia la sessione corrente come conclusa e apre la successiva, sincronizzando il meteo e la data.
  - `[ 🏁 Concludi Sessione ]`: conclude la sessione attiva generando la cronaca definitiva.
* **Esportazione Tripla**:
  1. **Pergamena Medievale HTML (`📜 Pergamena HTML`)**: genera una pagina web dark fantasy stile pergamena miniata, con layout a due colonne, stili tipografici medievali e supporto nativo per la stampa.
  2. **Documento Markdown (`📑 Esporta Markdown`)**: salva l'intero diario o la singola sessione per Obsidian, Notion o GitHub.
  3. **Recap per Discord/WhatsApp (`📋 Copia per Discord`)**: formatta la cronaca con blocchi citazione ed emoji per essere incollata istantaneamente nella chat del gruppo.

### Gestione Mappe, Editor Mappe, Muri, Trappole e Portali
* **Editor Mappe (`Strumenti -> Editor Mappe`)**:
  * Carica un'immagine di sfondo, regola la dimensione degli esagoni (`hex_size`) e imposta la **Scala della Mappa** (Combattimento, Esplorazione, Mondo o Personalizzata).
  * Disegna **Muri / Ostacoli** (bloccano il movimento e la Line of Sight).
  * Piazza **Trappole** (con CD di Percezione Passiva, CD del Tiro Salvezza e formula del danno, es. `2d6`).
  * Piazza **Luci** ambientali e **Oggetti / Bottino (Loot)** raccoglibili.
  * **Pittura Terreni Difficili**: clicca su **`🌾 Terreno Difficile`**, scegli la tipologia (Fango, Ghiaccio, Rovi, Macerie, Palude) dal menu a tendina e dipingi le celle direttamente sulla mappa con texture e colori distintivi. Salva la mappa in formato JSON per conservare i dati.
* **Terreni Difficili al Volo in Sessione (`[ 🪨 ]` e Tasto Destro)**:
  * **Pennello Toolbar `[ 🪨 ]`**: cliccando sul pulsante nella toolbar sinistra si apre il menu rapido di selezione pennello (**💩 Fango**, **🧊 Ghiaccio**, **🌿 Rovi**, **🪨 Macerie**, **🌊 Palude**, **🗑️ Gomma**). Clicca sulle caselle della mappa per applicare o rimuovere istantaneamente il terreno difficile durante la sessione.
  * **Menu Contestuale Tasto Destro**: fai click destro su una qualsiasi cella della mappa $\rightarrow$ **`🌾 Terreno Difficile...`** per impostare o cancellare il tipo di superficie.
  * **Regole D&D 5e Integrate**:
    * **Movimento**: il costo di movimento è raddoppiato per ogni casella difficile calcolata lungo la traiettoria (`hex_linedraw`); se la creatura è anche **Prona**, il costo sale a 3 esagoni di budget per casella.
    * **Pericoli al Passaggio**: entrare sul Ghiaccio richiede un **TS Destrezza CD 10** o si cade Proni; entrare nei Rovi infligge **1d4 danni perforanti**.
    * **Combattimento**: attaccare stando su terreno instabile (Ghiaccio, Macerie, Palude, Fango) impone **Svantaggio**; attaccare bersagli intralciati nei Rovi o bloccati nel Fango conferisce **Vantaggio**.
    * **HUD Coordinate**: passando il cursore sopra una cella, la targhetta in basso a destra visualizza il tipo di terreno e il moltiplicatore (es. `⬡ q:2, r:1 [Ghiaccio x2 Mov]`).
* **Portali e Teletrasporti (`[ 🚪 ]`)**: clicca sullo strumento `[ 🚪 ]` nella toolbar sinistra e poi su un esagono per collegarlo a un altro file mappa (es. `cripta_livello2.json`). Quando un giocatore cammina su quell'esagono, il server carica automaticamente la nuova mappa per tutto il gruppo.

### Gestione Porte, Serrature e Meccanica di Scasso RAW 5e
OmniCompanion gestisce le porte e le vie di passaggio con un sistema interattivo aderente al regolamento ufficiale D&D 5e:

* **Stati della Porta**:
  * **Aperta (`open`)**: passaggio libero, la Line of Sight attraversa l'apertura.
  * **Chiusa (`closed`)**: blocca la visione e il passaggio, ma può essere aperta con una semplice interazione con oggetto.
  * **Chiusa a Chiave / Bloccata (`locked`)**: serratura ingaggiata con una specifica Classe Difficoltà (es. CD 15 o CD 20).
  * **Segreta (`secret`)**: invisibile sulla mappa dei giocatori finché non viene scoperta tramite Percezione Passiva o una prova attiva di Investigazione; il DM la vede evidenziata con icona tratteggiata.
  * **Sbarrata (`barred`)**: bloccata dall'interno con travi o catene pesanti, richiede di essere sfondata o sbloccata dall'altro lato.
* **Azioni del Giocatore sulle Porte**:
  * Cliccando su una porta o selezionandola con click destro, il giocatore accede alle opzioni RAW:
  * **🗝️ Apri con Chiave**: se il personaggio possiede la chiave corrispondente nell'inventario, la serratura si apre senza tiri.
  * **🛠️ Scassinare con Arnesi da Scasso (*Thieves' Tools*)**:
    * Richiede il possesso di *Arnesi da Scasso* nell'inventario del PG (PHB p. 154).
    * Esegue una prova di **Destrezza (Arnesi da Scasso)** applicando il bonus di competenza (o maestria se ladro esperto).
    * Se il risultato eguaglia o supera la CD della porta, la serratura scatta e la porta diventa sbloccata.
    * Con il profilo *Tavolo Tradizionale* o *Ibrido Assistito*, il tiro viene notificato al DM che può descrivere l'esito narrativo o applicare complicanze (es. rottura dei grimaldelli con un 1 Naturale o allarme che suona).
  * **💥 Forzare / Sfondare la Porta**:
    * Prova di **Forza (Atletica)** contro la CD di sfondamento della porta.
    * Un successo abbatte o scardina la porta, ma allerta tutte le creature nelle stanze limitrofe.
  * **✨ Incantesimo Scassinare (*Knock*)**:
    * Sblocca istantaneamente fino a due serrature o sbarramenti, ma emette un fortissimo rimbombo sonoro udibile fino a 300 piedi (90 metri).
* **Configurazione DM**:
  * Fai **Click Destro** su una porta $\rightarrow$ **`Modifica Porta...`** per configurare stato iniziale, CD di scasso, CD di sfondamento, se è segreta e il file mappa di destinazione se funge da portale.

### Spille di Stanza del Dungeon (Room Pins) e Narrazione al Tavolo
Le **Spille di Stanza (`[ 📌 ]`)** trasformano OmniCompanion in un modulo d'avventura interattivo:

* **Piazzamento Spille**:
  * Il DM seleziona lo strumento **`[ 📌 ]`** nella toolbar sinistra o fa click destro su un esagono della mappa $\rightarrow$ **`Piazza Spilla di Stanza`**.
  * Sulla mappa compare una spilla numerata/titolata (es. `[ 📌 1: Ingresso della Cripta ]`), visibile solo al Dungeon Master o rivelabile se desiderato.
* **Finestra Narrativa della Stanza**:
  * Cliccando su una spilla si apre un pannello a due sezioni:
    1. **📜 Testo Narratore in Riquadro (*Boxed Text*)**: la descrizione d'atmosfera scritta per i giocatori (in tipico stile manuale ufficiale Wizards of the Coast).
       * Cliccando su **`📢 Leggi al Tavolo (Broadcast)`**, l'intero testo viene formattato come pergamena dorata nella chat di tutti i giocatori con 1 click!
    2. **🔒 Note Segrete del DM**: visibili **esclusivamente al Master**. Contengono trappole celate, posizioni dei mostri, tesori nascosti, tattiche di combattimento e CD delle prove di Investigazione.

### Tiri Segreti del DM (Blind Rolls: `/broll`, `/gmroll`)
Per preservare la suspense e prevenire il metagaming, OmniCompanion implementa i tiri alla cieca (*Blind Rolls*):

* **Comando Chat**: digita `/broll <formula> [motivo]` oppure `/gmroll <formula> [motivo]`:
  * Esempi: `/broll 1d20+5 Furtività`, `/broll 1d20+3 Percezione Passiva`, `/gmroll 1d20+7 Disattivare Trappole`.
* **Comportamento Anti-Metagame**:
  * Il server calcola il tiro con il motore matematico completo (inclusi modificatori, critici ed espressioni).
  * Il **risultato numerico, il dado e il totale vengono inviati ESCLUSIVAMENTE al Dungeon Master**.
  * Il giocatore vede solo una notifica rassicurante e discreta in chat:
    > `🎲 Hai inviato un tiro segreto al DM (1d20+5: Furtività). Il Master ne conosce l'esito!`
  * In questo modo, se un giocatore tira un 2 naturale su una prova di individuare trappole o muoversi silenziosamente, non potrà sapere se non ha trovato nulla perché la stanza è sicura o perché ha fallito clamorosamente il tiro!

### Nebbia di Guerra (FoW), Pennello Manuale, Line of Sight e Luci
* Cliccando su **`[ ☁️ ]`** nella toolbar sinistra del DM si apre la barra avanzata della **Nebbia di Guerra**:
  * **Attiva / Disattiva Nebbia di Guerra**.
  * **Rivela Tutta la Mappa** / **Nascondi Tutta la Mappa** / **Ripristina Nebbia Iniziale**.
  * **Pennello Manuale FoW (`Raggio: 0, 1, 2, 3`)**: seleziona il raggio del pennello dal menu a tendina. Cliccando con il tasto sinistro (rivela) o destro (nasconde) su una cella della mappa, la nebbia viene dipinta o rimossa su un'intera area circolare, permettendo al DM di scoprire o coprire stanze complesse con pochi gesti.
* Quando la FoW è attiva, i giocatori vedono solo le celle entro il proprio raggio visivo e non bloccate dai muri (Line of Sight dinamica).
* Usa il comando chat `/vision <NomePG> <Raggio>` (es. `/vision Gildor 12` per Scurovisione a $60\text{ ft} / 18\text{ m}$) per impostare la vista del token.

### Taglie Creature (Dimensioni Token) e Livello Nascosto DM (GM Layer)
* **Taglie Creature Ufficiali 5e**:
  * OmniCompanion gestisce le 6 categorie di taglia 5e: **Minuscola (Tiny)** ($0.5\times$), **Piccola (Small)** ($0.8\times$), **Media (Medium)** ($1.0\times$), **Grande (Large)** ($1.8\times$), **Enorme (Huge)** ($2.6\times$) e **Mastodontica (Gargantuan)** ($3.5\times$).
  * Il token si espande o restringe visivamente sul canvas occupando la proporzione corretta di spazio tattico.
  * Per cambiare la taglia: fai **Click Destro** sul token o sulla voce nella lista PG $\rightarrow$ **`Taglia Creatura (Size)`** $\rightarrow$ scegli la dimensione desiderata.
* **Livello Nascosto del DM (GM Layer)**:
  * Permette di preparare mostri, trappole o elementi di scena tenendoli completamente invisibili ai giocatori.
  * **Visibilità DM**: il token appare semitrasparente con un anello tratteggiato viola (`#A855F7`) e un badge `[GM]`.
  * **Isolamento Giocatori e Sicurezza di Rete**: i token sul GM Layer non vengono renderizzati sul canvas dei giocatori e vengono filtrati direttamente dal server nei broadcast TCP (`GAME_STATE`, `PLAYER_JOINED`, `PLAYER_MOVE`), garantendo l'assoluta assenza di fughe di dati (*anti-metagame*).
  * Per spostare un token sul GM Layer o riportarlo sul livello visibile: **Click Destro** sul token $\rightarrow$ **`👁️ Livello DM (GM Layer)`**.

### Gestione del Combattimento e Bilanciatore Incontri (DMG p. 82)
Nel tab **`Iniziativa & PG`** della sidebar destra del DM:
1. **Separazione Party vs PNG**: fuori dal combattimento, la lista separa chiaramente `--- MEMBRI DEL PARTY ---` e `--- PNG & MOSTRI ---`. Con il **Click Destro** su qualsiasi entità puoi visualizzarne la scheda completa, modificarne i PV, applicare condizioni, impostare un'**Aura Magica** o aggiungerla/rimuoverla dal Party.
2. **Bilanciatore Difficoltà Incontri Live**: un badge mostra in tempo reale la difficoltà dello scontro (**Banale**, **Facile**, **Medio**, **Difficile**, **Mortale**) calcolata secondo le tabelle della *Dungeon Master's Guide (p. 82)* in base ai livelli del party e ai Grado di Sfida (CR) dei mostri presenti.
3. **Avvio e Gestione Turni**:
   * Clicca su **`🎲 Tira Iniziativa Mostri`** per tirare automaticamente l'iniziativa di tutti i PNG/Mostri.
   * Clicca su **`Inizia Combattimento`** per ordinare i partecipanti, attivare l'**Initiative Ribbon HUD** sulla mappa e resettare l'economia del turno.
   * Usa **`Prossimo Turno ⏩`** e **`⏪ Turno Precedente`** per far avanzare i turni e i round.
4. **Azioni Leggendarie & Azioni di Tana per Boss (MM p. 11)**:
   * **Azioni Leggendarie**:
     * I Boss leggendari possono compiere fino a 3 Azioni Leggendarie per round, spendibili solo al termine del turno di un'altra creatura.
     * Quando un altro personaggio conclude il proprio turno, il sistema invia un **promemoria nel log del DM** segnalando quante azioni leggendarie il boss ha ancora a disposizione.
     * Il DM può spendere le azioni selezionando il costo (1, 2 o 3) e l'abilità (es. *Colpo d'Ala*, *Attacco con Coda*, *Sguardo Terrorizzante*).
     * All'inizio del turno del Boss, il contatore delle azioni leggendarie viene **automaticamente ripristinato al valore massimo**.
   * **Azioni di Tana (Iniziativa 20)**:
     * Per le creature con tana attiva (`has_lair_actions = True`), all'inizio di ogni round a **Iniziativa 20** il sistema annuncia l'Azione di Tana sia in chat che nel log DM, consentendo al Master di attivare gli effetti ambientali della tana.
   * **Resistenze Leggendarie (3/giorno)**: quando il boss fallisce un Tiro Salvezza, il DM può convertirlo all'istante in successo.

### Multi-Selezione Token ed Operazioni di Gruppo del DM
Per velocizzare la gestione di gruppi numerosi di mostri ed alleati sul campo di battaglia, OmniCompanion include un sistema completo di multi-selezione token per il Dungeon Master:

1. **Selezione Multipla su Canvas e Lista**:
   * **Dalla Lista Iniziativa & PG**: la lista delle creature supporta la selezione estesa nativa (selectmode=tk.EXTENDED). Puoi selezionare più entità tenendo premuto **Ctrl** (per selezioni multiple disgiunte) oppure **Shift** (per intervalli continui).
   * **Dal Canvas della Mappa**: tieni premuto **Ctrl + Click Sinistro** su qualsiasi token della mappa per aggiungerlo o rimuoverlo istantaneamente dal gruppo selezionato.
   * **Feedback Visivo sulla Mappa**: tutti i token facenti parte della multi-selezione attiva vengono evidenziati sul canvas con un distintivo **cerchio dorato tratteggiato** (#F59E0B).

2. **Operazioni Massive a 1-Click**:
   * **🎲 Iniziativa Gruppo**: nella sidebar destra compare il pulsante per tirare l'iniziativa simultaneamente solo per i mostri/token selezionati, aggiornando la sequenza dei turni in un colpo solo.
   * **🩹 Modifica PV Gruppo**: apre una finestra di dialogo di massa per applicare danni o cure a tutti i token selezionati contemporaneamente (supporta sia modificatori relativi +10 o -5, sia impostazioni a valore assoluto).
   * **🗑️ Elimina Gruppo**: rimuove con un solo click e finestra di conferma tutti i token selezionati dalla mappa e dalla lista partecipanti.

### Bestiario SRD, Compendio Split View e Generatori Procedurali
* **Compendio & SRD Split View (`Strumenti -> Compendio & SRD` o `Libreria -> Compendio & Regole`)**:
  * **Interfaccia Master-Detail Interattiva**: il compendio unificato offre una vista a due pannelli; la colonna sinistra elenca i risultati filtrati con barra di ricerca in tempo reale e conteggio elementi, mentre il pannello destro renderizza istantaneamente la scheda dettagliata della voce selezionata.
  * **Statblock 5e Autentico (`StatblockCardView`)**:
    * **Mostri & PNG**: layout fedele al *Monster Manual* con badge tematici ad alto contrasto per **Classe Armatura** (con indicazione del tipo di armatura/scudo), **Punti Ferita** (con formula dei Dadi Vita) e **Velocità** (camminata, volo, nuoto, scavo, scalata). Tabella orizzontale delle 6 caratteristiche con punteggi e modificatori calcolati in tempo reale ($(\text{stat}-10)//2$), tiri salvezza con competenza, abilità, resistenze/immunità a danni e condizioni, sensi (scurovisione, percezione passiva), lingue e Grado di Sfida (CR con XP relativi). Sezione per Tratti Speciali, Azioni con bonus di attacco e formule di danno evidenziate, Reazioni e Azioni Leggendarie con costo in azioni.
    * **Oggetti Magici**: pergamena descrittiva con badge di rarità (*Comune*, *Non Comune*, *Raro*, *Molto Raro*, *Leggendario*), tipo di oggetto, requisiti di sintonia (`Richiede Sintonia`), proprietà magiche ed effetti narrativi.
    * **Incantesimi**: scheda con livello e scuola di magia, tempo di lancio, gittata, componenti (V, S, M), durata, concentrazione/rituale, descrizione completa e incremento ad alti livelli (*Ai Livelli Superiori*).
  * **Filtri Rapidi Multi-Criterio**:
    * **Mostri**: selezione rapida per scaglioni di Grado di Sfida (*Tutti*, *CR 0–1/2*, *CR 1–4*, *CR 5–9*, *CR 10–14*, *CR 15–19*, *CR 20+*) e per Tipo Creatura (*Tutti*, *Drago*, *Non Morto*, *Umanoide*, *Bestia*, *Aberrazione*, *Costrutto*, *Fata*, *Mostruosità*, *Gigante*, *Celestiale*, *Immondezzaio*...).
    * **Oggetti Magici**: filtri per Rarità e Tipologia (*Arma*, *Armatura*, *Bacchetta*, *Anello*, *Pozione*, *Meraviglioso*...).
    * **Incantesimi**: filtri per Livello (Trucchetto, 1–9) e Scuola di Magia.
  * **Pulsante di Azione Primario Contestuale**: in basso a destra dello statblock compare l'azione principale adatta al contesto:
    * *Mostri*: **`Spawna sulla Mappa 🐉`** piazza immediatamente la creatura sull'ultimo esagono cliccato o al centro della visuale con iniziativa, PV, CA, velocità e scheda completa.
    * *Incantesimi*: **`Aggiungi al Grimorio ✨`** memorizza l'incantesimo nella scheda del personaggio attivo.
    * *Oggetti*: **`Aggiungi all'Inventario 🎒`** assegna l'oggetto al personaggio selezionato.
* **Tab `Bestiario` nella Sidebar Destra del DM**:
  * Barra di ricerca rapida con pulsanti di filtro istantaneo per Grado di Sfida (CR) e Tipo Creatura.
  * **Mini-Statblock Visuale**: visualizzazione card compatta con badge CA, PV, Velocità e tabella caratteristiche essenziali.
  * **Spawning Istantaneo**: doppio click su una voce dell'elenco o click sul pulsante **Spawna sulla Mappa** per posizionare il mostro in 1 secondo.
* **Normalizzazione Deterministica di CA e Velocità (Anti-Raw `[{}]`)**:
  * Il sistema depura automaticamente tutte le voci SRD e quelle estratte dai manuali PDF, eliminando formattazioni grezze o annidamenti JSON (`[{'value': 18, ...}]`).
  * Estrae correttamente valori base e secondari di movimento (es. *Camminata 30 ft, Volo 80 ft, Nuoto 40 ft*) e note di armatura (es. *18 (Armatura a Piastre)*).
* **Consultazione Manuali PDF (`📖` o `Strumenti -> Consulta Manuali di Gioco`)**: ricerca istantanea offline all'interno dei manuali PDF presenti nella cartella `manuals_pdf/` (*Player's Handbook*, *Dungeon Master's Guide*, *Monster Manual*, *Tasha's*, *Xanathar's*).
* **Generatore di Bottino 5e (`Strumenti -> 💰 Generatore di Bottino`)**: genera tesori casuali bilanciati per Grado di Sfida (CR 0–4, 5–10, 11–16, 17+) e distribuisci oro al party con 1 click.
* **Generatore Rapido PNG (`Strumenti -> 🎭 Generatore Rapido PNG`)**: crea all'istante PNG con nome, razza, tratto caratteriale, segreto, statistiche e pulsante per schierarli sulla mappa.

### Mondo, Calendario, Meteo, Viaggio, Negozi e Registro Missioni (Quest Log)
* **Tab `Mondo` e `Strumenti -> Pannello Viaggio`**:
  * Gestisci il **Calendario di Harptos (Forgotten Realms)** o standard, l'ora del giorno (con filtro luce diurno, alba, tramonto e notturno) e il **Meteo dinamico** con 6 condizioni ambientali animate:
    * **☀️ Sereno**: visuale limpida standard.
    * **🌧️ Pioggia**: scrosci d'acqua e increspature; Svantaggio a lunga gittata ($\ge 4$ esagoni).
    * **⛈️ Tempesta**: pioggia battente, raffiche di vento e fulmini animati ramificati; **Svantaggio a tutti gli attacchi a distanza** ($> 1$ esagono).
    * **❄️ Neve**: tormenta di fiocchi e cristalli di brina; Svantaggio a lunga gittata ($\ge 3$ esagoni).
    * **🌫️ Nebbia**: banchi di nebbia densi volumetrici; **Svantaggio a tutti gli attacchi a distanza** ($> 1$ esagono).
    * **🌑 Oscurità**: buio pesto stipple, vignettatura ai bordi e volute di tenebra fluttuanti.
  * **Filtro Oscurità 1-Click e Scurovisione (`[ 🌑 ]`)**:
    * Cliccando sul pulsante **`[ 🌑 ]`** nella toolbar sinistra del DM, o digitando `/darkness` o `/oscurita`, la mappa piomba nelle tenebre.
    * **Luce Dinamica di Torce e Lanterne**: le entità con `light_radius > 0` proiettano un raggio dorato che squarcia l'oscurità illuminando l'area circostante.
    * **Sfera di Oscurità Magica**: click destro su un esagono $\rightarrow$ **`🌑 Piazza Sfera di Oscurità Magica (R=3)`** per creare una zona di oscurità magica impenetrabile alla normale Scurovisione (richiede *Vista del Diavolo*).
    * **Regole di Combattimento 5e (Unseen Attackers)**: chi attacca dalle tenebre vedendo il bersaglio ha **Vantaggio**; chi non vede il bersaglio ha **Svantaggio**; nell'oscurità totale reciproca i due effetti si annullano.
  * Gestisci l'**Ordine di Marcia** del party (Avanguardia, Centro, Retroguardia), i ruoli di viaggio (Esploratore, Navigatore, Foraggiatore), il consumo di razioni/acqua e i Tiri Salvezza su Costituzione per la **Marcia Forzata**.
  * Apri e trasmetti ai giocatori i **Negozi dei Mercanti** (`shop_ui.py`).
  * **Registro delle Missioni Condiviso (Quest Log)**: accessibile da `Libreria -> 📜 Registro Missioni (Quest Log)` o dal menu DM:
    * Traccia tutte le quest principali e secondarie con titolo, descrizione narrativa, committente e ricompense in monete o oggetti.
    * Ogni operazione di aggiunta, completamento (`[✅ Completa]`) o cancellazione viene sincronizzata istantaneamente in broadcast a tutti i client connessi con relativo annuncio in chat.

### Documenti Condivisi (Handout) e Soundboard Audio
* **Condivisione Documenti & Handout (`Strumenti -> Condividi Documento testuale / Condividi Immagine`)**:
  * Mostra istantaneamente sullo schermo di tutti i giocatori un'illustrazione (mappa del tesoro, ritratto, lettera sigillata) o una pergamena narrativa.
  * I client ricevono il pacchetto di broadcast ed aprono automaticamente la finestra del visualizzatore pergamena in stile pergamena medievale.
* **Tab `Audio / SFX`**: riproduci musica d'ambiente (Taverna, Combattimento, Dungeon) ed effetti sonori sincronizzati su tutti i client connessi.

### Lavagna Tattica Condivisa (Whiteboard) ed Esportazione Session Log
* **Lavagna Tattica (`[ ✏️ ]` / `[ 🗑️ ]`)**: traccia linee e annotazioni direttamente sulla mappa; con il pulsante `[ 🗑️ ]` svuoti la lavagna per tutti i partecipanti con un solo click.
* **Esportazione Log di Sessione (`File -> 📜 Esporta Registro di Sessione...`)**: salva e scarica l'intero registro della sessione in formato **Markdown (`.md`)** pulito o **HTML stampabile**, ideale come diario d'avventura o resoconto narrativo.

---

## 6. Successi Critici (`20 Naturale`) e Fallimenti Critici (`1 Naturale`)

Il motore di gioco rileva automaticamente ogni `20 Naturale` e `1 Naturale` tirato su un dado a 20 facce (`1d20`, inclusi i tiri con Vantaggio o Svantaggio `2d20kh1` / `2d20kl1`):

1. **Tiri per Colpire (Attacchi)**:
   * **`🌟 CRITICO NATURALE 20!`**: l'attacco colpisce **automaticamente** a prescindere dalla CA del bersaglio e **raddoppia tutti i dadi di danno** dell'arma/incantesimo (i modificatori fissi vengono sommati una sola volta come da regole 5e).
   * **`💀 FALLIMENTO CRITICO (1 Naturale)!`**: l'attacco **manca automaticamente** a prescindere dai bonus.
2. **Tiri Salvezza (`SAVE_RESULT`)**:
   * Mostra i banner **`🌟 20 NATURALE!`** o **`💀 1 NATURALE!`** nel messaggio di risultato e invia una notifica Toast a tutto il tavolo.
3. **Tiri Salvezza contro la Morte**:
   * **`20 Naturale`**: il personaggio recupera immediatamente **1 PV** e riprende conoscenza.
   * **`1 Naturale`**: infligge **2 fallimenti** invece di 1.
4. **Prove di Abilità, Caratteristica e Tiri `1d20` in Chat**:
   * Ogni tiro di `1d20` effettuato dalla Scheda PG, dalla Tavolozza Comandi o via `/roll 1d20+...` viene evidenziato in chat con formattazione dorata (`🌟 20 NATURALE!`) o cremisi (`💀 1 NATURALE!`) e scatena un **Toast Broadcast** visivo e sonoro su tutti i client connessi.

---

## 7. Chat Stile Discord, Sussurri e Voice Chat UDP

* **Chat Formattata**: supporta timestamp, colori distinti per DM e Giocatori, blocchi evidenziati per i tiri di dado e i critici.
* **Sussurri Privati**: digita `/w <Nome> <Messaggio>` (o `/whisper`, `/sussurra`) per inviare un messaggio segreto visibile solo a te e al destinatario (`[🔒 Sussurro]`). Se il nome del destinatario contiene spazi, puoi racchiuderlo tra virgolette (es. `/w "Goblin Esploratore" Ciao`).
* **Voice Chat UDP Integrata**: in fondo al pannello Chat trovi i controlli vocali in tempo reale:
  * **`[ 🎤 ]`**: Muta / Smuta il tuo microfono.
  * **`[ 🎧 ]`**: Disattiva / Riattiva l'audio in entrata (Deafen).

---

## 8. Riferimento Rapido: Comandi Chat e Scorciatoie

| Comando / Scorciatoia | Chi può usarlo | Effetto | Esempio |
|---|---|---|---|
| `C` | Tutti | Mostra / Nascondi la Scheda Personaggio (Center Overlay / Riaggancia) | `C` |
| `Esc` | Tutti | Chiude la Scheda Personaggio o l'Overlay aperto | `Esc` |
| `F11` | Tutti | Attiva / Disattiva la modalità Schermo Intero (Fullscreen) | `F11` |
| `Ctrl + K` | Tutti | Apre la Tavolozza Comandi Rapida | `Ctrl+K` $\rightarrow$ `fireball` |
| `/roll <dadi>` o `/r <dadi>` | Tutti | Lancia dadi (supporta `kh1`/`kl1` per vantaggio/svantaggio) | `/roll 2d20kh1+5`, `/r 4d6` |
| `/w <nome> <testo>` | Tutti | Invia un sussurro privato | `/w DM Cerco porte segrete` |
| `/whisper <nome> <testo>` | Tutti | Alias inglese per sussurro privato | `/whisper Gildor Seguimi` |
| `/sussurra <nome> <testo>` | Tutti | Alias italiano per sussurro privato | `/sussurra Elidor Cura!` |
| `/manuale <termine>` | Tutti | Cerca una regola, incantesimo o mostro nei PDF | `/manuale lotta` |
| `/rule <termine>` | Tutti | Alias per la ricerca nei manuali PDF | `/rule concentration` |
| `/broll <dadi> [motivo]` | Tutti | Esegue un tiro segreto il cui risultato è visibile **solo al DM** | `/broll 1d20+5 Furtività` |
| `/gmroll <dadi> [motivo]` | Tutti | Alias per tiro segreto al DM | `/gmroll 1d20+3 Percezione` |
| `/tsmorte` / `/deathsave` / `/ds` | Giocatori (a 0 PV) | Esegue un Tiro Salvezza contro la Morte | `/ds` |
| `/vision <nome> <raggio_hex>` | Solo DM | Imposta il raggio visivo (in esagoni) di un token | `/vision Gildor 12` |
| `/darkness` / `/oscurita` | Solo DM | Attiva/Disattiva all'istante il filtro Oscurità sulla mappa | `/darkness` |
| `/meteo <clima>` / `/weather <clima>` | Solo DM | Imposta la condizione meteo attiva | `/meteo Tempesta` |

