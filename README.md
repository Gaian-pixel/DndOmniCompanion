# D&D OmniCompanion

D&D OmniCompanion è un'applicazione Client-Server sviluppata in Python (Tkinter) per facilitare la gestione e la riproduzione di campagne di Dungeons & Dragons 5e. È stata concepita per digitalizzare il lavoro del Dungeon Master (DM) e centralizzare le schede dei giocatori, pur mantenendo un'interfaccia semplice, veloce e coerente con il flusso di gioco al tavolo o da remoto.

## Caratteristiche Principali

### 🐉 Lato Server (Dungeon Master)
* **Gestione Connessioni**: Host locale/remoto con tracciamento in tempo reale degli utenti connessi.
* **Tracker Iniziativa & Combattimento**: Sistema completo per avviare combattimenti (con filtro per distanza esagonale), calcolare automaticamente l'iniziativa dei mostri, tracciare il turno corrente e aggiungere/rimuovere entità (Player e NPC) "mid-combat" senza interrompere il flusso.
* **Integrazione SRD (Open5e)**: Un potente scaricatore di contenuti dal SRD (Monsters, Spells, Magic Items, ecc.) per popolare istantaneamente la mappa con nemici.
* **Mappe Dinamiche & AoE**: Caricamento di mappe ad alta risoluzione (supporto pan/zoom), editor per piazzare Punti di Interesse (POI) a griglia esagonale e visualizzazione sincrona delle Aree di Effetto (AoE) piazzate dai giocatori.
* **Controllo Schede**: Ispezione completa in tempo reale degli HP, delle condizioni e degli attributi di ogni personaggio.

### 🛡️ Lato Client (Player)
* **Character Creation Wizard**: Procedura guidata passo-passo per creare un nuovo personaggio (Classe, Razza, Statistiche, ecc.) e salvarlo in locale.
* **Scheda Personaggio Interattiva**: Gestione automatizzata dell'Inventario, degli HP, e del lancio dei Dadi per attacchi, prove e tiri salvezza.
* **Mappa Sincronizzata**: Il giocatore vede in tempo reale la mappa condivisa dal DM, può posizionare coni/sfere/linee (AoE) per gli incantesimi cliccando sugli esagoni, o selezionare i bersagli per i propri attacchi graficamente.
* **Notifiche UX**: Avvisi visivi ("È IL TUO TURNO!") con controlli contestuali che compaiono solo quando si è effettivamente in combattimento, seguendo i principi della *Progressive Disclosure*.
* **Chat di Gruppo & Sussurri**: Chat di sistema, chat globale per il roleplay o risultati dei dadi e sussurri privati con il DM.

## Struttura del Progetto

* `client/` - Contiene la logica dell'applicazione giocatore, l'interfaccia UI, la gestione dei personaggi (`character_manager.py`) e la creazione guidata.
* `server/` - Contiene il demone del server (`server.py`), i gestori dei comandi (`commands.py`), gli importer SRD, l'editor mappe e l'interfaccia del Dungeon Master.
* `common/` - Moduli condivisi per Protocolli di Rete, Utility dei Dadi, Logica della Griglia Esagonale (`hex_utils.py`), Theme manager per la GUI Tkinter e condivisione del `GameState`.
* `components/` - Widget UI custom, tra cui la complessa Canvas della Mappa Esagonale.
* `maps/`, `client_data/`, `srd_data/` - Cartelle per i salvataggi di asset, schede, immagini e database JSON.

## Requisiti

* **Python 3.8+**
* Libreria **Pillow** (`pip install Pillow`)
* Nessuna dipendenza complessa esterna (tutta l'interfaccia grafica è sviluppata con librerie standard `tkinter` e moduli `ttk` personalizzati in un tema dark nativo).

## Come Avviare

L'applicazione è ora unificata in un singolo eseguibile per massima semplicità:

```bash
python main.py
```

All'avvio, un **Launcher** ti chiederà di scegliere il ruolo per la sessione corrente:
* **Ospita Partita (Dungeon Master)**: Apre il pannello DM, mettendo il server in ascolto per le connessioni in ingresso.
* **Unisciti alla Partita (Giocatore)**: Avvia il Client, dove potrai generare/caricare la tua scheda e connetterti all'indirizzo IP fornito dal Master.

## Testing

Il progetto include robusti test per assicurare che le GUI funzionino correttamente senza finestre bloccanti.
* `python test_ui_smoke.py`: Test di apertura rapida di ogni finestra e dialogo con screenshot automatico di validazione per verificare errori di tema o runtime.
* `python test_e2e_gui.py`: Test end-to-end simulando la connessione reale di un client socket, l'inizio di un combattimento, l'uso di target/AoE sulla mappa e l'avanzamento dei turni.