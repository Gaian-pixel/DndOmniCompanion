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
   - [Reazioni RAW e Incantesimo Scudo (*Shield*)](#reazioni-raw-e-incantesimo-scudo-shield)
   - [Tratti Speciali: Evasione (Ladro/Monaco) e Attacco Furtivo](#tratti-speciali-evasione-ladromonaco-e-attacco-furtivo)
   - [Punti Ferita, Riposi e Tiri Salvezza contro la Morte](#punti-ferita-riposi-e-tiri-salvezza-contro-la-morte)
   - [Inventario, Ingombro, Scambi e Richieste al DM](#inventario-ingombro-scambi-e-richieste-al-dm)
   - [Esportazione Scheda Personaggio (PDF Ufficiale D&D 5e e JSON)](#esportazione-scheda-personaggio-pdf-ufficiale-dd-5e-e-json)
   - [Macro Hotbar (Slot Rapidi 1–10)](#macro-hotbar-slot-rapidi-110)
5. [Guida per il Dungeon Master (DM)](#5-guida-per-il-dungeon-master-dm)
   - [Stili di Gestione della Campagna (DM Agency vs Full Automation) e Barra Decisioni](#stili-di-gestione-della-campagna-dm-agency-vs-full-automation-e-barra-decisioni)
   - [Gestione Campagne, Atti, Scene e Starter Pack](#gestione-campagne-atti-scene-e-starter-pack)
   - [Gestione Mappe, Editor Mappe, Muri, Trappole e Portali](#gestione-mappe-editor-mappe-muri-trappole-e-portali)
   - [Gestione Porte, Serrature e Meccanica di Scasso RAW 5e](#gestione-porte-serrature-e-meccanica-di-scasso-raw-5e)
   - [Spille di Stanza del Dungeon (Room Pins) e Narrazione al Tavolo](#spille-di-stanza-del-dungeon-room-pins-e-narrazione-al-tavolo)
   - [Tiri Segreti del DM (Blind Rolls: `/broll`, `/gmroll`)](#tiri-segreti-del-dm-blind-rolls-broll-gmroll)
   - [Nebbia di Guerra (FoW), Pennello Manuale, Line of Sight e Luci](#nebbia-di-guerra-fow-pennello-manuale-line-of-sight-e-luci)
   - [Taglie Creature (Dimensioni Token) e Livello Nascosto DM (GM Layer)](#taglie-creature-dimensioni-token-e-livello-nascosto-dm-gm-layer)
   - [Gestione del Combattimento e Bilanciatore Incontri (DMG p. 82)](#gestione-del-combattimento-e-bilanciatore-incontri-dmg-p-82)
   - [Bestiario SRD, Manuali PDF Offline e Generatori Procedurali](#bestiario-srd-manuali-pdf-offline-e-generatori-procedurali)
   - [Mondo, Calendario, Meteo, Viaggio, Negozi e Quest](#mondo-calendario-meteo-viaggio-negozi-e-quest)
   - [Handout (Documenti/Immagini) e Soundboard Audio](#handout-documentiimmagini-e-soundboard-audio)
   - [Lavagna Tattica Condivisa (Whiteboard) ed Esportazione Session Log](#lavagna-tattica-condivisa-whiteboard-ed-esportazione-session-log)
6. [Successi Critici (`20 Naturale`) e Fallimenti Critici (`1 Naturale`)](#6-successi-critici-20-naturale-e-fallimenti-critici-1-naturale)
7. [Chat Stile Discord, Sussurri e Voice Chat UDP](#7-chat-stile-discord-sussurri-e-voice-chat-udp)
8. [Riferimento Rapido: Comandi Chat e Scorciatoie](#8-riferimento-rapido-comandi-chat-e-scorciatoie)

---

## 1. Avvio Rapido e Connessione

1. Apri un terminale nella cartella del progetto ed esegui:
   ```bash
   python main.py
   ```
2. Si aprirà il **Launcher principale** con due sezioni:
   * **Dungeon Master (Host)**:
     * **⚔️ Avvia con Campagna**: carica una campagna esistente (con atti, scene, incontri preparati e mappe).
     * **📜 Prepara / Modifica Campagna**: apre direttamente l'Editor di Campagna per creare la tua avventura prima della sessione.
     * **⚡ Sessione Rapida (Vuota)**: avvia subito il server sulla porta TCP `53911` (e Voice UDP `53912`) per una partita estemporanea.
   * **Giocatore (Player)**:
     * **👤 Gestione Personaggi (Offline)**: apre direttamente la schermata di gestione eroi per creare, consultare, modificare la scheda, duplicare, eliminare ed esportare personaggi in PDF o JSON senza dover connettersi ad alcun server.
     * **✨ Crea Personaggio (Guidato)**: avvia subito la procedura guidata passo-passo (Razza, Classe, Statistiche, Background, Equipaggiamento) per creare un eroe di 1° livello.
     * **🛡️ Unisciti alla Partita**: avvia il client Giocatore. Dal menu `Server -> Connetti al Server...` (oppure `Riconnetti Ultimo Server`), scegli il tuo personaggio, inserisci l'indirizzo IP del DM (`127.0.0.1` o IP LAN/VPN) e clicca su **Connetti**.

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
2. **Viewport Centrale (`HexMapCanvas`)**: la mappa interattiva (esagonale, quadrata o senza griglia), arricchita da due HUD sovrapposti:
   * **Initiative Ribbon HUD (in alto al centro)**: appare automaticamente durante il combattimento mostrando le card di tutti i combattenti in ordine di turno (`#1`, `#2`...), la freccia `▼` sul turno attivo e una mini-barra PV per ciascuno. Cliccando su una card la mappa si centra su quel token.
   * **Controlli Mappa Glassmorphism (in basso a sinistra)**: pulsanti flottanti `[ - ]`, `[ 100% ]`, `[ + ]` e `[ ⌖ ]` per regolare lo zoom o ricentrare la visuale con un click.
3. **Sidebar Destra (Pannello a Tab)**: contiene la Chat & Voice Chat, i Controlli PG / Tracker Iniziativa, il Mondo/Calendario, il Bestiario e la Soundboard Audio.

### Tavolozza Comandi Rapida (`Ctrl+K`)
Premendo **`Ctrl+K`** in qualsiasi momento (o da `Strumenti/Libreria -> Tavolozza Comandi Rapida`) si apre una barra di ricerca universale:
* Digita il nome di un **mostro**, di un **incantesimo** o di una **regola 5e** per leggerne i dettagli.
* Digita il nome di un **token sulla mappa** per centrare immediatamente la telecamera su di esso.
* Digita un'espressione come `/roll 2d6+4` o `1d20+5` e premi `Invio` per lanciare subito i dadi in chat.

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
* **Nuovo Personaggio (Livello 1)**: Dalla finestra di selezione personaggio, dalla Gestione Personaggi o dal menu, avvia il **Wizard di Creazione**. Ti guiderà nella scelta di Razza, Classe, Background, distribuzione delle Caratteristiche (Standard Array, Point Buy o Tiro Dadi) ed equipaggiamento iniziale.
* **Salita di Livello (`Level Up (+)`)**: Nella Scheda PG, clicca su `Level Up (+)`:
  * Scegli se prendere il **valore medio** del Dado Vita o effettuare il **tiro**.
  * Il sistema scarica automaticamente dal Compendio SRD 5e i **nuovi privilegi di classe** e aggiorna gli **slot incantesimo** del nuovo livello.
  * Ai livelli previsti (es. 4, 8, 12, 16, 19) puoi assegnare l'**Aumento dei Punteggi di Caratteristica (+2 / +1+1)** o un Talento.

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

Cliccando su **`📋 Scheda PG`** si apre la scheda completa divisa in schede:
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

### Sintonia con Oggetti Magici (Attunement `🔮`) e Ispirazione DM
* **Sintonia con Oggetti Magici (Attunement `🔮`)**:
  * Come da regole ufficiali RAW 5e (DMG p. 136), un personaggio può essere in sintonia con un massimo di **3 oggetti magici contemporaneamente**.
  * Nel tab **🎒 Inventario** della Scheda PG, ogni oggetto possiede un indicatore/selettore `🔮 Sintonizzato`.
  * Il sistema conteggia dinamicamente gli slot occupati (`🔮 Sintonie Attive: X / 3`) e impedisce di superare il limite delle 3 sintonie senza prima averne sciolta una (durante un riposo breve).
  * Gli effetti passivi degli oggetti sintonizzati (bonus a CA, tiri per colpire, caratteristiche o tiri salvezza) si applicano istantaneamente alle statistiche calcolate del personaggio.
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
    * `Copertura Automatica`: raycasting geometrico sulla mappa (`hex_linedraw`) per rilevare muri, coperture e token interposti.
    * `Nessuna Copertura`: CA normale del bersaglio.
    * `Mezza Copertura (+2 CA / +2 TS DES)`: bersaglio protetto da un muretto, un albero o un'altra creatura.
    * `Tre Quarti di Copertura (+5 CA / +5 TS DES)`: bersaglio dietro a una feritoia o grata pesante.
    * `Copertura Totale`: il bersaglio è completamente celato; l'attacco viene bloccato.
  * **Azioni Tattiche 5e**: **Scatto (Dash)** (raddoppia il movimento del turno), **Disimpegno (Disengage)** (evita attacchi di opportunità), **Schivata (Dodge)** (infligge svantaggio agli attaccanti e conferisce vantaggio ai propri TS su Destrezza), **Aiuto (Help)** (conferisce vantaggio a un alleato).
* **Pulsante `[ 💥 ]` (Area d'Effetto)**:
  * Scegli la forma geometrica (**Sfera**, **Cono**, **Linea**), la dimensione in esagoni, il colore e (opzionalmente) il Tiro Salvezza richiesto (es. `DES CD 15` con `8d6` danni da fuoco).
  * Clicca sulla mappa per posizionare l'area: il server calcola automaticamente tutti i bersagli coinvolti, richiede i Tiri Salvezza (applicando i bonus di Mezza o 3/4 Copertura se specificati) e applica i danni (dimezzati in caso di successo).
* **Lancio Incantesimi, Upcasting e Concentrazione Rigorosa (PHB p. 201-204)**:
  * Quando clicchi su **`Lancia`** su un incantesimo dal Grimorio, se l'incantesimo è di 1° livello o superiore appare una finestra modale di scelta dello slot.
  * Puoi scegliere di lanciarlo al suo livello base oppure effettuare l'**Upcast** spendendo uno slot di livello più alto disponibile (es. lanciare *Dardo Incantato* di 1° livello con uno slot di 3° livello).
  * **Concentrazione Rigorosa**:
    * Il sistema riconosce automaticamente gli incantesimi a concentrazione (es. *Benedizione*, *Volare*, *Invisibilità*, *Muro di Fuoco*).
    * Se lanci un incantesimo a concentrazione mentre ne stai già mantenendo un altro, la vecchia concentrazione cade all'istante con un annuncio pubblico in chat, evitando concentrazioni multiple non consentite dalle regole RAW.
    * Subire danni richiede automaticamente un TS Costituzione ($\text{CD} \ge 10$): in caso di fallimento, l'incantesimo crolla immediatamente.
* **Pulsante `⏭️ Termina Turno`**: attivo durante il tuo turno di combattimento; passa immediatamente l'iniziativa al combattente successivo.

### Reazioni RAW e Incantesimo Scudo (*Shield*)
* **Economia delle Reazioni RAW (PHB p. 190)**:
  * Ogni creatura dispone di una sola `🛡️ Reazione` per round, che si ripristina all'inizio del proprio turno.
  * Il sistema monitora in tempo reale gli eventi scatenanti (*triggers*) che avvengono durante i turni degli altri combattenti.
* **Prompt di Reazione per l'Incantesimo Scudo (*Shield*)**:
  * Quando un attacco nemico supera la CA di un personaggio (o quando viene bersagliato da *Dardo Incantato*), se l'eroe conosce o ha preparato l'incantesimo *Scudo* e dispone della propria reazione e di almeno uno slot di 1° livello o superiore, il client visualizza un prompt interattivo con conto alla rovescia:
    * Se il giocatore accetta: consuma la `🛡️ Reazione` del round, scala uno slot di 1° livello e aggiunge un bonus invisibile di **+5 alla Classe Armatura (CA)** fino all'inizio del suo prossimo turno.
    * **Risoluzione Retroattiva**: Se il nuovo punteggio di CA ($CA + 5$) è superiore o uguale al tiro per colpire dell'avversario, l'attacco viene retroattivamente convertito da "Colpito" a "Mancato", salvando il personaggio dai danni!
* **Attacchi di Opportunità Dinamici**:
  * Quando un nemico adiacente (a distanza di 1 esagono / $5\text{ ft}$) si allontana uscendo dalla portata di mischia senza aver intrapreso l'azione di *Disimpegno (Disengage)*, il server rileva l'apertura e invia una notifica al difensore permettendogli di spendere la sua `🛡️ Reazione` per sferrare un attacco immediato in mischia.

### Tratti Speciali: Evasione (Ladro/Monaco) e Attacco Furtivo
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
* **Scendere a 0 PV**: il personaggio perde automaticamente la `Concentrazione` e riceve le condizioni `Incosciente` e `Prono`. Se il danno residuo in eccesso è $\ge \text{PV Massimi}$, si verifica la **Morte Istantanea**.
* **Tiri Salvezza contro la Morte**:
  * All'inizio del tuo turno a 0 PV (o digitando `/ds` / `/tsmorte` in chat, o dalla Scheda PG) esegui il Tiro contro la Morte:
    * **`20 Naturale`**: torni immediatamente a **1 PV** e perdi la condizione `Incosciente`!
    * **`10–19`**: +1 Successo (a 3 successi diventi `Stabilizzato`).
    * **`2–9`**: +1 Fallimento.
    * **`1 Naturale`**: **+2 Fallimenti** (a 3 fallimenti il personaggio muore).
* **Riposo Breve e Riposo Lungo (RAW PHB p. 186)**:
  * **Spesa Dadi Vita nel Riposo Breve (`ShortRestDialog`)**:
    * Cliccando su **`Riposo Breve`** nella Scheda PG si apre la nuova finestra modale interattiva:
      * Visualizza i PV attuali e massimi con **barra della salute progressiva** e il numero esatto di **Dadi Vita rimanenti** (es. `3 / 5 (d8)`).
      * **Pulsante `🎲 Spendi 1 Dado Vita`**: tira un singolo dado della classe ($1\text{dY} + \text{Mod. Costituzione}$, con guarigione minima di 1 PV anche con COS negativa), incrementa i PV fino al massimale e aggiorna la cronologia progressiva dei tiri in tempo reale.
      * **Pulsante `⚡ Spendi Tutti i Dadi Vita`**: spende automaticamente i dadi rimanenti fino al raggiungimento dei PV massimi o all'esaurimento dei dadi.
      * **Pulsante `✅ Concludi Riposo`**: chiude il dialogo, annuncia pubblicamente in chat il recupero totale e i dadi spesi, e ricarica i privilegi a riposo breve (es. *Secondo Fiato*, *Azione Impetuosa*, e slot da *Patto del Warlock*).
  * **Riposo Lungo**: ripristina tutti i PV, tutti gli Slot Incantesimo, azzera i livelli di Indebolimento (Exhaustion -1), ricarica tutte le risorse di classe e **recupera fino a metà dei Dadi Vita totali** del personaggio ($\max(1, \lfloor\text{Totale}/2\rfloor)$ come da regole RAW 5e).

### Inventario, Ingombro, Scambi e Richieste al DM
* **Sicurezza Online (Approvazione DM)**: mentre sei connesso a una sessione live, i punteggi di caratteristica e i PV massimi sono protetti. Per aggiungere monete o oggetti custom puoi cliccare su **`🤝 Richiedi Valuta al DM`** o aggiungere un oggetto: il DM riceverà un pop-up di approvazione istantanea.
* **Scambi con Alleati (`Dai` / `🤝 Dai Oro a Compagno`)**: puoi trasferire oggetti o monete direttamente a un altro giocatore connesso.

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
* **11 Switch Granulari Indipendenti**:
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

### Bestiario SRD, Manuali PDF Offline e Generatori Procedurali
* **Tab `Bestiario` e `Strumenti -> Compendio & SRD`**: cerca mostri dal database SRD 5e o dai manuali PDF indicizzati e clicca su **Spawna sulla Mappa** per schierarli subito con statistiche, CA, PV e azioni complete.
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

