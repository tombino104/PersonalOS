# Personal OS — Scaletta di lavoro
 
Qui si tiene traccia dell'avanzamento. La specifica (`PERSONAL-OS-SPEC.md`) dice **cosa** costruire, questo file dice **in che ordine** e **a che punto siamo**.
Regola: si fa un passo alla volta, con commit piccoli. Si spunta un passo solo quando il criterio "Fatto quando" è vero. Stato: `[ ]` da fare · `[~]` in corso · `[x]` fatto.
 
---
 
## 0. Spike (prova tecnica) `[ ]`
Pagina minima, prima di costruirci sopra.
- Servita in HTTPS tramite Tailscale Serve (mai Funnel).
- **Fatto quando**: si apre da iPhone e da Mac; il form di login minimo fa proporre la password salvata con FaceID/TouchID; si riesce a ricevere una notifica push di prova dall'app installata sulla Home dell'iPhone.
- Se qualcosa non funziona (es. push su indirizzo `.ts.net`), si annota qui e si decide prima di proseguire.
## 1. Repo e scheletro `[ ]`
- Repo pubblico (licenza PolyForm Noncommercial), `.gitignore` dal primo commit, struttura delle cartelle, Dockerfile e Docker Compose.
- **Fatto quando**: il container parte, `/health` risponde, si riavvia da solo dopo un arresto.
## 2. Modello dati e motore di punteggio `[ ]`
- Tabelle del core (spec 4.6), attività template (spec 4.7), motore di punteggio come funzione isolata, snapshot giornaliero.
- **Fatto quando**: i test passano, inclusi: massimo = 0 dà punteggio nullo (non 0%); cambiare peso o attività non modifica i report passati; giorno non compilato = nessuna riga; taglio del giorno alle 04:00.
## 3. API del core (versionate) `[ ]`
- Rotte sotto `/api/v1/` per ambiti, attività, report, punteggi.
- **Fatto quando**: tutte le operazioni della v1 si possono fare via API e sono coperte da test.
## 4. Login `[ ]`
- Password, sessioni con scadenza, limite ai tentativi, comando di reset da terminale.
- **Fatto quando**: senza login non si vede nulla; il reset funziona.
## 5. Interfaccia base `[ ]`
- File dei token (chiaro/scuro), dock, questionario serale, Home con trend e widget heatmap, archivio report, impostazioni attività.
- **Fatto quando**: compili un questionario dall'iPhone, vedi l'animazione di completamento e il dato compare nella Home.
## 6. Sistema plugin `[ ]`
- Manifest, caricamento, eventi dopo il salvataggio, isolamento dei guasti, voci del dock (spec 5.1).
- **Fatto quando**: un plugin di prova si attiva e si spegne senza toccare il core, e un errore dentro il plugin non abbatte l'app.
## 7. Primi plugin `[ ]`
- Tracker emozioni, poi skill.
- **Fatto quando**: ognuno aggiunge il proprio blocco al questionario e la propria vista, e spegnerlo non rompe nulla.
## 8. Backup `[ ]`
- Backup notturno, "Scarica adesso", scelta del percorso, ripristino da file.
- **Fatto quando**: hai fatto davvero un ripristino da un backup e i dati sono tornati identici.
## 9. Notifiche e agenti `[ ]`
- Plugin notifiche (promemoria serale), token API e coda di proposte per Hermes.
- **Fatto quando**: arriva il promemoria solo se il report non è completato; Hermes può leggere e proporre, non scrivere punteggi.
## 10. Packaging per Umbrel `[ ]`
- Negozio app della community, `umbrel-app.yml`, `docker-compose.yml` (da verificare i dettagli sul disco di backup).
- **Fatto quando**: l'app si installa da Umbrel e sopravvive a un riavvio.
---
 
## Dopo la v1 (non adesso)
Calendario (lettura, poi scrittura), compiti/matrice di Eisenhower (solo se decisi), temi extra.
 