# 🐉 D&D OmniCompanion — Guida Completa all'Utilizzo

> 🌐 **Lingua / Language**: 🇮🇹 **[Italiano (GUIDA_ALL_UTILIZZO.md)](GUIDA_ALL_UTILIZZO.md)** | 🇬🇧 **[English (USER_GUIDE.md)](USER_GUIDE.md)**
> ⚙️ **Manuale Tecnico & Architettura**: Consulta anche la **[Guida Operativa (GUIDA_OPERATIVA.md)](GUIDA_OPERATIVA.md)**.

Benvenuto nel manuale d'uso ufficiale di **D&D OmniCompanion**, il Virtual Tabletop (VTT) e gestore di campagna per **Dungeons & Dragons 5a Edizione**.
Questa guida illustra passo dopo passo come avviare una sessione, configurare l'interfaccia, gestire personaggi, mappe, combattimenti, esplorazione, unità di misura e strumenti del Dungeon Master.

---

## 📑 Indice

1. [Avvio Rapido e Connessione](#1-avvio-rapido-e-connessione)
2. [Panoramica dell'Interfaccia e Impostazioni Globali](#2-panoramica-dellinterfaccia-e-impostazioni-globali)
   - [Barra dei Menu: Lingua e Unità di Misura](#barra-dei-menu-lingua-e-unità-di-misura)
   - [Layout a 3 Colonne e HUD sulla Mappa](#layout-a-3-colonne-e-hud-sulla-mappa)
   - [Tavolozza Comandi Rapida (`Ctrl+K`)](#tavolozza-comandi-rapida-ctrlk)
3. [Sistema di Unità di Misura, Scale Mappa e Righello](#3-sistema-di-unità-di-misura-scale-mappa-e-righello)
   - [Scelta tra Piedi/Miglia (`ft/mi`) e Metri/Chilometri (`m/km`)](#scelta-tra-piedimiglia-ftmi-e-metrichilometri-mkm)
   - [Le 4 Scale della Mappa (DMG p. 14)](#le-4-scale-della-mappa-dmg-p-14)
   - [Utilizzo del Righello Dinamico (`[ 📏 ]`)](#utilizzo-del-righello-dinamico---)
4. [Guida per il Giocatore (Player)](#4-guida-per-il-giocatore-player)
   - [Creazione Personaggio (Wizard) e Level-Up](#creazione-personaggio-wizard-e-level-up)
   - [Hero Summary Card e Scheda Personaggio Interattiva](#hero-summary-card-e-scheda-personaggio-interattiva)
   - [Economia del Turno: Esplorazione vs Combattimento](#economia-del-turno-esplorazione-vs-combattimento)
   - [Azioni in Combattimento e Incantesimi ad Area (AoE)](#azioni-in-combattimento-e-incantesimi-ad-area-aoe)
   - [Punti Ferita, Riposi e Tiri Salvezza contro la Morte](#punti-ferita-riposi-e-tiri-salvezza-contro-la-morte)
   - [Inventario, Ingombro, Scambi e Richieste al DM](#inventario-ingombro-scambi-e-richieste-al-dm)
   - [Macro Hotbar (Slot Rapidi 1–10)](#macro-hotbar-slot-rapidi-110)
5. [Guida per il Dungeon Master (DM)](#5-guida-per-il-dungeon-master-dm)
   - [Gestione Campagne, Atti, Scene e Starter Pack](#gestione-campagne-atti-scene-e-starter-pack)
   - [Gestione Mappe, Editor Mappe, Muri, Trappole e Portali](#gestione-mappe-editor-mappe-muri-trappole-e-portali)
   - [Nebbia di Guerra (FoW), Line of Sight e Illuminazione](#nebbia-di-guerra-fow-line-of-sight-e-illuminazione)
   - [Gestione del Combattimento e Bilanciatore Incontri (DMG p. 82)](#gestione-del-combattimento-e-bilanciatore-incontri-dmg-p-82)
   - [Bestiario SRD, Manuali PDF Offline e Generatori Procedurali](#bestiario-srd-manuali-pdf-offline-e-generatori-procedurali)
   - [Mondo, Calendario, Meteo, Viaggio, Negozi e Quest](#mondo-calendario-meteo-viaggio-negozi-e-quest)
   - [Handout (Documenti/Immagini) e Soundboard Audio](#handout-documentiimmagini-e-soundboard-audio)
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
     * Clicca su **🛡️ Unisciti alla Partita** per aprire il client Giocatore.
     * Dal menu `Server -> Connetti al Server...` (oppure `Riconnetti Ultimo Server`), scegli o crea il tuo personaggio, inserisci l'indirizzo IP del DM (`127.0.0.1` se giochi sullo stesso PC, oppure l'IP LAN/VPN del Master) e clicca su **Connetti**.

---

## 2. Panoramica dell'Interfaccia e Impostazioni Globali

### Barra dei Menu: Lingua e Unità di Misura
Nella barra superiore (sia lato DM che lato Giocatore) trovi due menu di configurazione istantanea salvati automaticamente in `client_data/settings.json`:
* **`🌐 Lingua / Language`**: cambia in tempo reale tutta l'interfaccia, le condizioni, le abilità e i messaggi di sistema tra **Italiano 🇮🇹** e **English 🇬🇧** senza riavviare l'applicazione.
* **`📏 Unità di Misura` (`📏 Distance Units`)**: permette di scegliere in qualsiasi momento tra:
  * **Piedi / Miglia (`ft / mi`)** — Sistema Imperiale standard USA (1 esagono tattico = `5 ft`).
  * **Metri / Chilometri (`m / km`)** — Sistema Metrico edizione italiana (1 esagono tattico = `1.5 m`).

### Layout a 3 Colonne e HUD sulla Mappa
L'interfaccia è divisa in tre aree ergonomiche:
1. **Toolbar Sinistra (Strumenti Mappa)**: barra compatta con pulsanti iconici per interagire con la griglia esagonale (`👆` Centra/Seleziona, `💥` Area d'Effetto, `📏` Misura Distanza, `📍` Ping, `📖` Manuali, più `☁️` Nebbia e `🚪` Porta/Teletrasporto per il DM).
2. **Viewport Centrale (`HexMapCanvas`)**: la mappa esagonale interattiva, arricchita da due HUD sovrapposti:
   * **Initiative Ribbon HUD (in alto al centro)**: appare automaticamente durante il combattimento mostrando le card di tutti i combattenti in ordine di turno (`#1`, `#2`...), la freccia `▼` sul turno attivo e una mini-barra PV per ciascuno. Cliccando su una card la mappa si centra su quel token.
   * **Controlli Mappa Glassmorphism (in basso a sinistra)**: pulsanti flottanti `[ - ]`, `[ 100% ]`, `[ + ]` e `[ ⌖ ]` per regolare lo zoom o ricentrare la visuale con un click.
3. **Sidebar Destra (Pannello a Tab)**: contiene la Chat & Voice Chat, i Controlli PG / Tracker Iniziativa, il Mondo/Calendario, il Bestiario e la Soundboard Audio.

### Tavolozza Comandi Rapida (`Ctrl+K`)
Premendo **`Ctrl+K`** in qualsiasi momento (o da `Strumenti/Libreria -> Tavolozza Comandi Rapida`) si apre una barra di ricerca universale:
* Digita il nome di un **mostro**, di un **incantesimo** o di una **regola 5e** per leggerne i dettagli.
* Digita il nome di un **token sulla mappa** per centrare immediatamente la telecamera su di esso.
* Digita un'espressione come `/roll 2d6+4` o `1d20+5` e premi `Invio` per lanciare subito i dadi in chat.

---

## 3. Sistema di Unità di Misura, Scale Mappa e Righello

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

### Utilizzo del Righello Dinamico (`[ 📏 ]`)
1. Clicca sul pulsante **`[ 📏 ]`** nella toolbar a sinistra per attivare la modalità Righello (il bottone si illumina d'oro).
2. **Clicca e trascina** con il tasto sinistro da un esagono di partenza a un esagono di arrivo sulla mappa.
3. Sulla mappa apparirà un vettore tratteggiato dorato con un badge ad alto contrasto che mostra:
   * Su mappe di **Combattimento**: `6 hex (30 ft)` oppure `6 hex (9 m)`.
   * Su mappe di **Esplorazione**: `3 hex (3 mi [~1h])` oppure `3 hex (4.5 km [~1h])`.
   * Su mappe **Mondo / Regione**: `8 hex (48 mi [~2 gg])` oppure `8 hex (72 km [~2 gg])`.

---

## 4. Guida per il Giocatore (Player)

### Creazione Personaggio (Wizard) e Level-Up
* **Nuovo Personaggio (Livello 1)**: Dalla finestra di selezione personaggio o dalla scheda, avvia il **Wizard di Creazione**. Ti guiderà nella scelta di Razza, Classe, Background, distribuzione delle Caratteristiche (Standard Array, Point Buy o Tiro Dadi) ed equipaggiamento iniziale.
* **Salita di Livello (`Level Up (+)`)**: Nella Scheda PG, clicca su `Level Up (+)`:
  * Scegli se prendere il **valore medio** del Dado Vita o effettuare il **tiro**.
  * Il sistema scarica automaticamente dal Compendio SRD 5e i **nuovi privilegi di classe** e aggiorna gli **slot incantesimo** del nuovo livello.
  * Ai livelli previsti (es. 4, 8, 12, 16, 19) puoi assegnare l'**Aumento dei Punteggi di Caratteristica (+2 / +1+1)** o un Talento.

### Hero Summary Card e Scheda Personaggio Interattiva
Nel tab **`Controlli PG`** della sidebar destra trovi sempre in primo piano la **Hero Summary Card**:
* Mostra Nome, Classe/Razza/Livello, Punti Ferita attuali/massimi (più eventuali PV Temporanei, livello di Indebolimento e Condizioni attive).
* **Barra della Salute Dinamica**: si riempie proporzionalmente da `0%` a `100%` cambiando colore dal verde (`> 50%`) all'ambra (`25%–50%`) fino al rosso (`< 25%`).
* Badge rapidi per **🛡️ CA**, **👟 Velocità** (convertita in `ft` o `m`) e **⚡ Iniziativa**.

Cliccando su **`📋 Scheda PG`** si apre la scheda completa divisa in schede:
1. **Statistiche & Combattimento**: Punteggi di Caratteristica, Tiri Salvezza, Abilità con selettore di Competenza (`0 = Nessuna`, `1 = Competente +PB`, `2 = Maestria +2×PB`) e pulsante `🎲` per tirare direttamente in chat, Gestione PV rapidi (`-5`, `-1`, `+1`, `+5`), Riposo Breve/Lungo, Dadi Vita e Tiri contro la Morte.
2. **⚔️ Armi & Attacchi**: elenco delle armi con calcolo automatico del bonus al tiro per colpire e del danno.
3. **🎒 Inventario**: gestione oggetti con peso individuale, sintonizzazione magica (max 3 oggetti `🔮`), Borsa delle Monete (`MR`, `MA`, `ME`, `MO`, `MP`) e calcolo automatico dell'**Ingombro** ($\text{Forza} \times 15\text{ lbs}$).
4. **📖 Grimorio**: contatori degli Slot Incantesimo dal livello 1 al 9, ricerca incantesimi SRD e pulsante **Lancia** che scala automaticamente lo slot e annuncia l'incantesimo in chat.
5. **🌟 Privilegi & Note / 📜 Diario**: tratti razziali, privilegi di classe e appunti di sessione.

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

### Azioni in Combattimento e Incantesimi ad Area (AoE)
* **Pulsante `⚔️ Azione`**: apre la finestra Azioni Standard 5e:
  * **Attacco con Arma / Incantesimo**: scegli il bersaglio, l'arma, eventuale Vantaggio/Svantaggio e invia l'attacco al server.
  * **Azioni Tattiche 5e**: **Scatto (Dash)** (raddoppia il movimento del turno), **Disimpegno (Disengage)** (evita attacchi di opportunità), **Schivata (Dodge)** (infligge svantaggio agli attaccanti), **Aiuto (Help)** (conferisce vantaggio a un alleato).
* **Pulsante `[ 💥 ]` (Area d'Effetto)**:
  * Scegli la forma geometrica (**Sfera**, **Cono**, **Linea**), la dimensione in esagoni, il colore e (opzionalmente) il Tiro Salvezza richiesto (es. `DES CD 15` con `8d6` danni da fuoco).
  * Clicca sulla mappa per posizionare l'area: il server calcola automaticamente tutti i bersagli coinvolti, richiede i Tiri Salvezza e applica i danni (dimezzati in caso di successo).
* **Pulsante `⏭️ Termina Turno`**: attivo durante il tuo turno di combattimento; passa immediatamente l'iniziativa al combattente successivo.

### Punti Ferita, Riposi e Tiri Salvezza contro la Morte
* **Scendere a 0 PV**: il personaggio perde automaticamente la `Concentrazione` e riceve le condizioni `Incosciente` e `Prono`. Se il danno residuo in eccesso è $\ge \text{PV Massimi}$, si verifica la **Morte Istantanea**.
* **Tiri Salvezza contro la Morte**:
  * All'inizio del tuo turno a 0 PV (o digitando `/ds` / `/tsmorte` in chat, o dalla Scheda PG) esegui il Tiro contro la Morte:
    * **`20 Naturale`**: torni immediatamente a **1 PV** e perdi la condizione `Incosciente`!
    * **`10–19`**: +1 Successo (a 3 successi diventi `Stabilizzato`).
    * **`2–9`**: +1 Fallimento.
    * **`1 Naturale`**: **+2 Fallimenti** (a 3 fallimenti il personaggio muore).
* **Riposo Breve e Riposo Lungo**:
  * **Riposo Breve**: permette di spendere i Dadi Vita disponibili per curarsi ($\text{Dado Vita} + \text{Mod. COS}$) e ricarica le abilità a riposo breve.
  * **Riposo Lungo**: ripristina tutti i PV, tutti gli Slot Incantesimo, metà dei Dadi Vita totali e riduce di 1 livello l'Indebolimento (*Exhaustion*).

### Inventario, Ingombro, Scambi e Richieste al DM
* **Sicurezza Online (Approvazione DM)**: mentre sei connesso a una sessione live, i punteggi di caratteristica e i PV massimi sono protetti. Per aggiungere monete o oggetti custom puoi cliccare su **`🤝 Richiedi Valuta al DM`** o aggiungere un oggetto: il DM riceverà un pop-up di approvazione istantanea.
* **Scambi con Alleati (`Dai` / `🤝 Dai Oro a Compagno`)**: puoi trasferire oggetti o monete direttamente a un altro giocatore connesso.

### Macro Hotbar (Slot Rapidi 1–10)
In fondo alla finestra del Giocatore è presente una barra con **10 pulsanti numerati (`1`–`10`)**:
* **Click Destro su uno slot**: assegna un nome e un comando o tiro rapido (es. `Spada Lunga` $\rightarrow$ `/roll 1d20+6`, oppure `/ds`).
* **Click Sinistro su uno slot**: esegue immediatamente la macro. Le macro vengono salvate nel profilo del personaggio.

---

## 5. Guida per il Dungeon Master (DM)

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
* **Porte e Teletrasporti (`[ 🚪 ]`)**: clicca sullo strumento `[ 🚪 ]` nella toolbar sinistra e poi su un esagono per collegarlo a un altro file mappa (es. `cripta_livello2.json`). Quando un giocatore cammina su quell'esagono, il server carica automaticamente la nuova mappa per tutto il gruppo.

### Nebbia di Guerra (FoW), Line of Sight e Illuminazione
* Cliccando su **`[ ☁️ ]`** nella toolbar sinistra del DM si apre il menu rapido della **Nebbia di Guerra**:
  * **Attiva / Disattiva Nebbia di Guerra**.
  * **Rivela Tutta la Mappa** / **Nascondi Tutta la Mappa** / **Ripristina Nebbia Iniziale**.
* Quando la FoW è attiva, i giocatori vedono solo gli esagoni entro il proprio raggio visivo e non bloccati dai muri (Line of Sight).
* Usa il comando chat `/vision <NomePG> <RaggioInEsagoni>` (es. `/vision Gildor 12` per Scurovisione a $60\text{ ft} / 18\text{ m}$) per modificare il raggio visivo di un personaggio.

### Gestione del Combattimento e Bilanciatore Incontri (DMG p. 82)
Nel tab **`Iniziativa & PG`** della sidebar destra del DM:
1. **Separazione Party vs PNG**: fuori dal combattimento, la lista separa chiaramente `--- MEMBRI DEL PARTY ---` e `--- PNG & MOSTRI ---`. Con il **Click Destro** su qualsiasi entità puoi visualizzarne la scheda completa, modificarne i PV, applicare condizioni, impostare un'**Aura Magica** o aggiungerla/rimuoverla dal Party.
2. **Bilanciatore Difficoltà Incontri Live**: un badge mostra in tempo reale la difficoltà dello scontro (**Banale**, **Facile**, **Medio**, **Difficile**, **Mortale**) calcolata secondo le tabelle della *Dungeon Master's Guide (p. 82)* in base ai livelli del party e ai Grado di Sfida (CR) dei mostri presenti.
3. **Avvio e Gestione Turni**:
   * Clicca su **`🎲 Tira Iniziativa Mostri`** per tirare automaticamente l'iniziativa di tutti i PNG/Mostri.
   * Clicca su **`Inizia Combattimento`** per ordinare i partecipanti, attivare l'**Initiative Ribbon HUD** sulla mappa e resettare l'economia del turno.
   * Usa **`Prossimo Turno ⏩`** e **`⏪ Turno Precedente`** per far avanzare i turni e i round.
4. **Azioni e Resistenze Leggendarie**: per i Boss dotati di punti leggendari, il DM dispone di controlli dedicati per spendere Azioni Leggendarie o Resistenze Leggendarie con ricarica automatica all'inizio del round.

### Bestiario SRD, Manuali PDF Offline e Generatori Procedurali
* **Tab `Bestiario` e `Strumenti -> Compendio & SRD`**: cerca mostri dal database SRD 5e o dai manuali PDF indicizzati e clicca su **Spawna sulla Mappa** per schierarli subito con statistiche, CA, PV e azioni complete.
* **Consultazione Manuali PDF (`📖` o `Strumenti -> Consulta Manuali di Gioco`)**: ricerca istantanea offline all'interno dei manuali PDF presenti nella cartella `manuals_pdf/` (*Player's Handbook*, *Dungeon Master's Guide*, *Monster Manual*, *Tasha's*, *Xanathar's*).
* **Generatore di Bottino 5e (`Strumenti -> 💰 Generatore di Bottino`)**: genera tesori casuali bilanciati per Grado di Sfida (CR 0–4, 5–10, 11–16, 17+) e distribuisci oro al party con 1 click.
* **Generatore Rapido PNG (`Strumenti -> 🎭 Generatore Rapido PNG`)**: crea all'istante PNG con nome, razza, tratto caratteriale, segreto, statistiche e pulsante per schierarli sulla mappa.

### Mondo, Calendario, Meteo, Viaggio, Negozi e Quest
* **Tab `Mondo` e `Strumenti -> Pannello Viaggio`**:
  * Gestisci il **Calendario di Harptos (Forgotten Realms)** o standard, l'ora del giorno (con filtro luce diurno/notturno sulla mappa) e il **Meteo dinamico** (Sereno, Pioggia, Nebbia, Tempesta, Neve).
  * Gestisci l'**Ordine di Marcia** del party (Avanguardia, Centro, Retroguardia), i ruoli di viaggio (Esploratore, Navigatore, Foraggiatore), il consumo di razioni/acqua e i Tiri Salvezza su Costituzione per la **Marcia Forzata**.
  * Apri e trasmetti ai giocatori i **Negozi dei Mercanti** (`shop_ui.py`) e il **Registro delle Missioni (Quest Log)** (`quest_ui.py`).

### Handout (Documenti/Immagini) e Soundboard Audio
* **Condividi Immagine / Documento (`Strumenti -> Condividi Immagine / Condividi Documento testuale`)**: mostra istantaneamente sullo schermo di tutti i giocatori un'illustrazione (ritratto di un PNG, mappa antica) o una pergamena leggibile.
* **Tab `Audio / SFX`**: riproduci musica d'ambiente (Taverna, Combattimento, Dungeon) ed effetti sonori sincronizzati su tutti i client connessi.

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
| `/tsmorte` / `/deathsave` / `/ds` | Giocatori (a 0 PV) | Esegue un Tiro Salvezza contro la Morte | `/ds` |
| `/vision <nome> <raggio_hex>` | Solo DM | Imposta il raggio visivo (in esagoni) di un token | `/vision Gildor 12` |

