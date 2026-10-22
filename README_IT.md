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
* **Sorgenti di Luce Dinamiche & Illuminazione Portatile (PHB p. 183)**:
  * **Pulsante Rapido HUD `[ 🕯️ ]`**: Presente nella Hero Summary Card per accendere o spegnere all'istante la fonte di luce.
  * **Preset Ufficiali D&D 5e**: Menu contestuale (click destro) con **Torcia** ($20\text{ ft}$ intensa / $20\text{ ft}$ fioca, raggio 8 esagoni, bagliore ambra), **Lanterna a Cappuccio** ($30\text{ ft} / 30\text{ ft}$, raggio 12 esagoni), **Lanterna Schermata** (fascio ristretto $5\text{ ft}$, raggio 1 esagono) e **Incantesimo Luce** ($20\text{ ft} / 20\text{ ft}$, raggio 8 esagoni con aura ciano).
  * **Sincronizzazione FoW**: L'accensione della luce estende istantaneamente il raggio di scoperta della Nebbia di Guerra calcolato su $\max(\text{vision\_radius}, \text{light\_radius})$.
* **Template Incantesimi ad Area (`[ 💥 ]`)**: Sfere, Coni ($60^\circ / 90^\circ$), Linee e Sfere di Oscurità Magica con anteprima geometrica sulla griglia.
* **Ping Animato sulla Mappa**: Click centrale (o strumento `[ 📍 ]`) per inviare un indicatore visivo animato a tutti i giocatori.
* **Badge Visivi delle Condizioni sui Token**: Rendering visuale sul canvas esagonale di icone badge bilingui ad alto contrasto per tutti gli status 5e (`💀` Morto, `💤` Incosciente, `🧎` Prono, `🧠` Concentrazione, `🛡️` Schivata, `🤝` Aiuto, `🟢` Avvelenato, `🙈` Accecato, `⚡` Paralizzato, `🕸️` Trattenuto, `⛓️` Afferrato, `👻` Invisibile, `😱` Spaventato, `💫` Stordito, `🩹` Stabilizzato, `🔇` Sordo, `💖` Incantato, `🗿` Pietrificato, `🔥` Ira).

### ⚔️ Motore di Combattimento D&D 5e & Economia del Turno
* **Economia del Turno Contestuale (Esplorazione vs Combattimento)**:
  * **Fuori dal Combattimento (`🧭 Modalità Esplorazione - Movimento Libero`)**: I giocatori si muovono, attaccano e lanciano incantesimi liberamente senza consumare o bloccare i badge di turno; la barra movimento indica la velocità per singolo spostamento.
  * **In Combattimento (`Economia Turno`)**: Tracciamento rigoroso e sincronizzato con il server di **⚡ Azione**, **✨ Azione Bonus**, **🛡️ Reazione** e **👟 Movimento**, con reset automatico all'inizio del proprio turno e a inizio/fine scontro.
* **Successi Critici (`🌟 20 Naturale`) e Fallimenti Critici (`💀 1 Naturale`)**:
  * **Tiri per Colpire**: `20 Naturale` colpisce sempre e raddoppia automaticamente tutti i dadi di danno; `1 Naturale` manca automaticamente.
  * **Tiri Salvezza, Prove di Abilità/Caratteristica e Tiri `1d20`**: Evidenziazione dorata/cremisi in chat e notifiche Toast broadcast (`CRITICAL_ROLL_BROADCAST`) a tutto il tavolo.
* **Copertura Tattica D&D 5e RAW (PHB p. 196)**:
  * **Selettore Rapido nei Dialoghi di Attacco e TS**: Possibilità di selezionare la copertura del bersaglio tra:
    * `Copertura Automatica`: Calcolo geometrico tramite algoritmo Bresenham esagonale (`hex_linedraw`) per ostacoli, muri e creature frapposte.
    * `Nessuna Copertura`: CA normale.
    * `Mezza Copertura`: $+2$ alla CA del bersaglio e $+2$ ai suoi Tiri Salvezza su Destrezza.
    * `Tre Quarti di Copertura`: $+5$ alla CA del bersaglio e $+5$ ai suoi Tiri Salvezza su Destrezza.
    * `Copertura Totale`: Il bersaglio non può essere bersagliato direttamente; attacco bloccato automaticamente.
* **Modificatori Ambientali di Combattimento (Meteo & Terreni Difficili)**:
  * **Meteo (DMG p. 109-110)**: Tempesta violenta e Nebbia fitta impongono Svantaggio agli attacchi a distanza (> 1 esagono); pioggia battente e bufere di neve impongono Svantaggio a lunga gittata.
  * **Terreni Difficili**: Attaccare da superfici instabili (Ghiaccio, Macerie, Palude, Fango) impone Svantaggio; attaccare nemici intralciati nei Rovi o bloccati nel Fango conferisce **Vantaggio**.
  * **Regole Oscurità e Scurovisione (PHB p. 194-195)**: Attaccare dalle tenebre con Scurovisione (o contro un bersaglio che impugna una torcia) conferisce **Vantaggio** (*Attaccante Celato*); attaccare un bersaglio che non si vede impone **Svantaggio**; nell'oscurità totale reciproca vantaggio e svantaggio si annullano.
* **Attacchi di Opportunità Automatizzati**: Rileva quando un combattente esce dalla portata di mischia ostile senza aver usato *Disimpegno*.
* **Concentrazione Rigorosa & Upcasting (PHB p. 201-204)**:
  * Lanciando un nuovo incantesimo a concentrazione dal Grimorio, la concentrazione precedente viene interrotta automaticamente e notificata in chat al gruppo.
  * Subire danni mentre si è concentrati innesca automaticamente un Tiro Salvezza su Costituzione ($\text{CD} = \max(10, \lfloor\text{Danni}/2\rfloor)$); se fallisce, l'incantesimo cade e le AoE collegate vengono rimosse.
  * **Upcasting**: Possibilità di lanciare magie con slot di livello superiore scalando la potenza dell'effetto.
* **Tiri Salvezza contro la Morte e Morte Istantanea**: Gestione completa a 0 PV (`20 Naturale` = risveglio a 1 PV, `1 Naturale` = 2 fallimenti, 3 successi = Stabilizzato, 3 fallimenti o danno eccessivo $\ge \text{PV Max}$ = Morto).
* **Meccaniche Boss RAW (MM p. 11)**:
  * **Azioni Leggendarie**: Fino a 3 azioni a round spendibili al termine del turno di un'altra creatura, promemoria automatici al DM, e ripristino delle cariche all'inizio del turno del boss.
  * **Azioni di Tana (Iniziativa 20)**: Notifica e attivazione automatica all'Iniziativa 20 per i boss con tana attiva.
  * **Resistenze Leggendarie**: Fino a 3/giorno per trasformare un fallimento al TS in successo.

### 🧙‍♂️ Creazione Personaggio, Scheda PG & Progressione
* **Wizard Stile Baldur's Gate con Compendi Comparativi Master-Detail**:
  * **Compendio Comparativo Razze Master-Detail (9 Razze Canoniche 5e)**: Accessibile con il pulsante `[ 📊 Tabella Comparativa ]` nel Passo 1 del Wizard:
    * **Ricerca e Filtri Rapidi**: Ricerca istantanea su qualsiasi campo e filtri a pulsante (`[Tutte (9)]`, `[🛡️ Resistenze]`, `[👁️ Scurovisione]`, `[🏃 Taglia Piccola]`, `[⚔️ Mischia / Forza]`, `[✨ Magiche / Carisma]`).
    * **Layout Split-View Master-Detail**: Tabella comparativa a sinistra (6 colonne: Razza con icona, Bonus, Tratti Chiave, Resistenze & Difese, Taglia/Vel., Classi Consigliate) e Scheda Anteprima reattiva a destra.
    * **Dati Meccanici & Lore RAW 5e**: Censimento completo delle difese passive (Resistenza Infernale al Fuoco, Resilienza Nanica vs Veleno, Retaggio Fatato con Immunità al Sonno Magico, Astuzia Gnomesca vs Magia, Tenacia Implacabile a 1 PF, Fortunato), Sinergie e Classi ideali, longevità, tutti i tratti con spiegazione delle meccaniche e sottorazze con selezione rapida a doppio click.
  * **Compendio Comparativo Classi (12 Classi Canoniche 5e)**: Accessibile nel Passo 2 con filtri per categoria (`[Tutte]`, `[Marziali]`, `[Incantatori]`, `[Ibridi]`, `[Esperti]`), Dadi Vita (d6–d12), Caratteristiche Primarie, Tiri Salvezza, Ruolo nel party, consigli Quick Build, anteprima equipaggiamento iniziale e sottoclassi.
  * **Level-Up Assistito**: Recupero automatico di privilegi di classe, dadi vita e slot incantesimo dal Compendio SRD 5e.
* **Avatar Personaggio & Generazione Automatica Token sulla Mappa**:
  * Possibilità per i giocatori (e per il DM con PNG e mostri) di caricare un'immagine per il proprio personaggio.
  * L'immagine caricata diventa automaticamente il **Token visivo renderizzato sulla mappa tattica**, con ritaglio circolare ad alta definizione, bordo colorato coordinato e scalatura dinamica in base alla Taglia della creatura (da *Minuscola* a *Mastodontica*).
* **Regole di Approvazione Master Anti-Cheat & Integrità Scheda (Online & Offline)**:
  * **Blocco Aggiunta/Rimozione Autonoma da SRD**: I giocatori non possono inserire o rimuovere arbitrariamente oggetti dall'inventario o incantesimi dal grimorio tramite l'SRD compendium senza l'approvazione del Dungeon Master.
  * Tale regola vige rigorosamente **sia durante le sessioni connesse, sia in modalità offline**, garantendo la totale integrità delle schede e prevenendo alterazioni non autorizzate.
  * **Diario e Note con Markdown & Approvazione DM**: Rendering visivo integrato per il testo formattato in Markdown (`**grassetto**`, `*corsivo*`, elenchi puntati, intestazioni) e richiesta di convalida del Master per il salvataggio delle cronache di campagna.
  * **Visualizzazione Riorganizzata di Tratti & Privilegi**: Chiara separazione tra tratti razziali biologici, privilegi di classe attivi e risorse spendibili.
* **Inventario, Monete, Contenitori e Consumabili Spendibili**:
  * **Sincronizzazione Valute & Peso Corretto**: Calcolo dinamico e veritiero del peso reale dell'inventario comprensivo del peso delle monete ($50\text{ monete} = 1\text{ lb}$) con sincronizzazione automatica bidirezionale tra gli oggetti fisici e la tabella superiore delle valute (`MR`, `MA`, `ME`, `MO`, `MP`).
  * **Gestione Contenitori Comoda**: Assegnazione immediata degli oggetti a `🎒 Zaino`, `⚔️ Equipaggiato`, `🔮 Borsa Conservante`, `✨ Zaino Pratico`, o `🐴 Cavalcatura`, con peso proprio vs peso trasportato.
  * **Materiali di Consumo Spendibili**: Pulsanti rapidi `[-1]` / `[+1]` sulla riga di munizioni (frecce, quadrelli), razioni, torce e pozioni per spendere risorse al volo durante l'avventura.
* **Spesa Dadi Vita nel Riposo Breve (RAW PHB p. 186)**:
  * Dialogo modale interattivo `ShortRestDialog` con anteprima PV attuali/massimi, barra salute progressiva e dadi vita rimasti.
  * Pulsante per **spendere 1 singolo Dado Vita** alla volta ($1\text{dY} + \text{Mod COS}$, min 1 recuperato), aggiornando istantaneamente la scheda e la chat.
  * Pulsante per spendere tutti i dadi vita disponibili o concludere il riposo.
  * Al Riposo Lungo vengono ripristinati tutti i PV e recuperati fino a metà dei Dadi Vita massimi ($\max(1, \lfloor\text{Totale}/2\rfloor)$).
* **Sistema Risorse di Classe Speciali**: Popolazione e tracciamento automatico di Punti Ki, Ira, Ispirazione Bardica, Forma Selvatica, Canale di Divinità, Azione Impetuosa, Secondo Fiato, Punti Stregoneria, ecc., con ricarica intelligente al Riposo Breve/Lungo.
* **Hero Summary Card & Scheda Interattiva**:
  * Card riassuntiva sempre visibile nella sidebar con barra PV reattiva, CA, Velocità effettiva (in `ft` o `m`), Iniziativa, toggle luce `[ 🕯️ ]` e pulsante rapido `[ 🎒 ]` per sfilare lo zaino a terra.
  * Scheda completa divisa in tab: **Combattimento**, **Statistiche & Abilità** (con Competenza e Maestria $2\times\text{PB}$), **Armi & Attacchi**, **Inventario & Ingombro** ($\text{FOR} \times 15\text{ lbs}$), **Grimorio & Slot Incantesimo (1–9)** con dialog di **Upcasting**, **Privilegi & Diario**.
* **Gestione Zaini, Contenitori ed Ingombro Variante 5e (RAW PHB p. 143, 176, 190)**:
  * **Collocazione per Ogni Oggetto**: Assegnazione a `🎒 Zaino`, `⚔️ Equipaggiato / Addosso`, `🔮 Borsa Conservante` (capienza 500 lbs, peso interno escluso dal PG), `✨ Zaino Pratico di Heward` (capienza 120 lbs, peso proprio 5 lbs), o `🐴 Sacca da Sella / Cavalcatura`.
  * **Tattica "Sfila lo Zaino a Terra" (*Drop Backpack*)**: Azione rapida a 1-click (`[ 🎒 Sfila Zaino a Terra ]` $\leftrightarrow$ `[ 🎒 Raccogli Zaino ]`) come Interazione con Oggetto Gratuita; esclude istantaneamente il peso degli oggetti nello zaino dal carico corporeo del personaggio, annunciando l'azione in chat e ripristinando la velocità piena in combattimento.
  * **Regola Variante di Ingombro (Variant: Encumbrance)**: Riconoscimento scaglioni di peso basati su FOR ($\text{FOR} \times 5$, $\text{FOR} \times 10$, $\text{FOR} \times 15$), peso reale monete (50 monete = 1 lb) e penalità dinamiche: *Normale*, *Ingombrato* (-10 ft / -3 m vel.), *Gravemente Ingombrato* (-20 ft / -6 m vel. e Svantaggio a tiri per colpire, prove e TS FOR/DES/COS) e *Sovraccarico* (movimento 0).
* **Esportazione Scheda Personaggio (PDF Ufficiale D&D 5e e JSON Dati)**: Finestra modale per scegliere tra **PDF Ufficiale** (richiede in input il modello PDF vuoto D&D 5e e compila automaticamente la scheda a 3 pagine pronta per la stampa o la condivisione) e **JSON** (backup grezzo per import/export tra campagne).
* **Scambi Peer-to-Peer e Macro Hotbar**: Scambio diretto di oggetti/monete con gli alleati e barra rapida a 10 slot personalizzabili.

### 📜 Suite Operativa per il Dungeon Master
* **Calcolatore Difficoltà Incontri Live (DMG p. 82)**: Valutazione in tempo reale (**Banale**, **Facile**, **Medio**, **Difficile**, **Mortale**) con moltiplicatori XP per numero di mostri.
* **Gestore Campagne, Scene & Starter Pack**: Prepara atti, scene collegate a mappe/mostri da schierare con 1 click e configura l'equipaggiamento iniziale automatico per i nuovi PG.
* **Esportazione Registro di Sessione**: Salva l'intera cronologia della sessione (tiri, eventi di combattimento, chat, sussurri) in formato Markdown (`.md`) o HTML da `File -> Esporta Registro di Sessione`.
* **Registro Missioni Condiviso (Quest Log) & Documenti Condivisi (Handouts)**:
  * Gestione e tracciamento missioni (`Libreria ➔ Registro Missioni`) con sincronizzazione in tempo reale tra tutti i partecipanti, dettagli, assegnatore e ricompense.
  * Condivisione globale di documenti su pergamena e illustrazioni con visualizzatore pergamena dedicato su tutti i client.
* **Generatori Procedurali**: Generatore di Bottino 5e e Generatore Rapido PNG.
* **Compendio & SRD Split View e Statblock 5e Autentico**:
  * **Interfaccia Split View Master-Detail**: layout interattivo a due pannelli (`server/compendium_ui.py`) con lista filtrabile a sinistra e anteprima statblock completa a destra, accompagnata dal pulsante di azione primario contestuale (*Spawna Mostro sulla Mappa*, *Aggiungi al Grimorio*, *Equipaggia Oggetto*).
  * **Componente Statblock 5e (`components/statblock_view.py`)**: rendering Dark Fantasy ad alta fedeltà con badge per Classe Armatura, Punti Ferita e Velocità, tabella delle 6 caratteristiche con modificatori calcolati in tempo reale, tiri salvezza, abilità, sensi, lingue, Grado di Sfida (CR), tratti speciali, azioni con dadi evidenziati, reazioni e azioni leggendarie.
  * **Filtri Rapidi Multi-Criterio**: pulsanti per Grado di Sfida (Tutti, CR 0–1/2, 1–4, 5–9, 10–14, 15–19, 20+), Tipo Creatura (Tutti, Drago, Non Morto, Umanoide, Bestia, Aberrazione, Costrutto, Fata, Mostruosità, Gigante, Celestiale, Immondezzaio...), Rarità Oggetti Magici (Comune, Non Comune, Raro, Molto Raro, Leggendario) e Tipo Incantesimo.
  * **Normalizzazione CA e Velocità (Anti-Raw `[{}]`)**: conversione deterministica di armature complesse e movimenti secondari (volo, nuoto, scavo, scalata), garantendo schede mostro pulite sia per l'SRD ufficiale che per le voci estratte dai manuali PDF.
  * **Mini-Statblock nel Bestiario DM (`server/dm_bestiary_panel.py`)**: filtri rapidi per Grado di Sfida e Tipo con card di anteprima compatta nella sidebar del DM e spawning istantaneo con doppio click.
* **Manuali PDF Offline & Tavolozza Comandi (`Ctrl+K`)**: Ricerca istantanea su manuali PDF ufficiali indicizzati, regole, mostri, incantesimi e token.
* **Viaggio, Calendario, Meteo e Negozi**: Ordine di marcia, ruoli di viaggio, razioni/acqua, marcia forzata, calendario fantasy interattivo e negozi mercantili.
* **Soundboard & Voice Chat UDP Integrata**: Streaming vocale a bassa latenza con controlli Mute/Deafen (`[ 🎤 ]` / `[ 🎧 ]`) e soundboard musicale sincronizzata.

### 🎲 Stili di Gestione Campagna: Controllo DM vs Automazione (RAW 5e)
Il DM può impostare in tempo reale il grado di automazione dell'applicativo da **Strumenti ➔ ⚙️ Stile Gestione Campagna (Automazioni)...** o cliccando la pillola di stato sull'header della mappa (`🎲 Tavolo`, `⚖️ Ibrido`, `⚡ Full Auto`):
* **🎲 Tavolo Tradizionale (Pen & Paper / Controllo DM RAW)**: Esperienza autentica cartacea. Nessuna modifica critica alle schede avviene a scatola chiusa: i danni e gli AoE attendono l'approvazione del DM, le porte lasciano spazio alla narrazione di serrature e trappole, il movimento non impone muri software invisibili, e la rottura di concentrazione o le morti sono arbitrate dal master senza rigidità.
* **⚖️ Ibrido Assistito (Consigliato per Sessioni Fluide)**: Il sistema gestisce matematicamente la contabilità 5e (resistenze, coperture, visibilità, condizioni, CD), ma fornisce al DM comode schede fluttuanti a 1-click (`[Pieno]`, `[Dimezza]`, `[Modifica]`, `[Annulla]`) per convalidare i danni a colpo sicuro.
* **⚡ Full Automation (Tattico Rapido / CRPG)**: Danni sottratti istantaneamente agli HP, porte aperte immediatamente su successo della CD, turni rigorosamente bloccati per chi non è attivo e prompt reazioni/TS automatici.
* **Estensione Granulare a Ogni Singola Meccanica**:
  * **⚔️ Combattimento & Danni**: Danni singoli da attacchi, Danni da magie/TS AoE, Calcolo automatico Vantaggio/Svantaggio (2d20), Prompt automatici per reazioni (AdO, Scudo), Verifica e rottura Concentrazione (TS Cos), Risoluzione 0 HP / Morte Istantanea e KO.
  * **🗺️ Mappa & Movimento**: Blocco rigido turni in combattimento, Blocco velocità massima e costo terreni difficili, Risoluzione porte/scasso CD, Svelamento dinamico Nebbia di Guerra (FoW).
  * **⛺ Riposo & Risorse**: Recupero automatico istantaneo risorse al riposo lungo (HP, Slot, Dadi Vita) vs convalida e verifica incontri casuali DM.

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
| `/broll <formula>` o `/gmroll <formula>` | Tira dadi in modalità segreta (visibile solo al DM) | `/broll 1d20+5 furtività` |
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
│   ├── dm_automation_panel.py      # Pannello di conduzione campagna (3 stili) e Barra Decisioni DM
│   ├── dm_travel_dialog.py         # Dialogo di viaggio overland, ordine di marcia e razioni
│   ├── dm_entity_dialogs.py        # Dialoghi per taglia creature, aure magiche e attributi token
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
│   ├── statblock_view.py           # Statblock 5e autentico per mostri, incantesimi e oggetti magici
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

# 2. Test Meccaniche Autentiche RAW 5e (Porte, Lockpicking, Room Pins, Reazioni, Shield, Evasione, Furtivo, Blind Rolls)
$env:DND_MOCK_AUDIO="1"; python test_authentic_5e.py

# 3. Smoke Test completo di tutte le 19 schermate UI (Server DM e Client Player)
$env:DND_MOCK_AUDIO="1"; python test_ui_smoke.py --no-screens

# 4. Simulazione End-to-End Multiplayer completa (53 fasi)
$env:DND_MOCK_AUDIO="1"; python simulate_game_session.py

# 5. Test Sistema Campagne e Scene
$env:DND_MOCK_AUDIO="1"; python -m unittest test_campaign_system.py
```

---

## 📜 Licenza e Riconoscimenti

* Progettato per il regolamento **Dungeons & Dragons 5th Edition (D&D 5e)** sotto licenza Open Game License (OGL) / System Reference Document 5.1 (SRD5).
* Realizzato con [Python](https://www.python.org/), [ttkbootstrap](https://ttkbootstrap.readthedocs.io/) e [Pillow](https://python-pillow.org/).

