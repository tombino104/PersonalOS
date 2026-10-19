# Personal OS — istruzioni per Claude Code

La specifica completa (`PERSONAL-OS-SPEC.md`) è **fuori da questo repo**, nella cartella `Concept` accanto ad `App`, perché contiene dettagli personali. Leggila sempre per prima. È la fonte di verità: se una decisione cambia, aggiornala nello stesso lavoro.

## Progetto in una riga
Un sistema personale di crescita (sei ambiti, punteggio relativo, questionario serale) per un solo utente, leggero, modulare a plugin, che gira in un container su UmbrelOS, dietro Tailscale.

## Filosofia (vincoli non negoziabili)
- Specchio, non tribunale. Non è un gioco.
- Si misurano i comportamenti, mai i risultati.
- Nessuna notifica legata ai punti. Nessuna fascia di giudizio.
- Un giorno non compilato è **vuoto**, non 0%.
- Pochi task per ambito.

## Regole di lavoro
1. Rispetta i marcatori della specifica: `[DECISO]` si implementa; `[PROPOSTO]` si implementa ma si può contestare; `[DA VERIFICARE]` e `[APERTO]` non si implementano a memoria.
2. Modularità: core minuscolo, il resto sono plugin con manifest. I plugin non si importano tra loro.
3. Il motore di punteggio è una funzione isolata, coperta da test.
4. **Il repo è PUBBLICO.** Mai dati, segreti o testi personali: database, backup, chiavi, token, `.env`, documenti di `Concept`. Gli esempi (seed) sono dati finti e generici, mai le vere abitudini. Prima di ogni push controlla `git diff --staged`.
5. Colori solo da token del tema.
6. Nessuna cancellazione fisica di attività o report: si archivia.
7. Commit piccoli, in italiano, nel formato Conventional Commits.
8. Interfaccia e nomi di tabelle/campi in italiano.
9. Prima di aggiungere una dipendenza, chiediti se serve.

## Ordine di lavoro
Segui `ROADMAP.md`, un passo alla volta. Si parte dallo spike prima di costruirci sopra.

## Se qualcosa non è chiaro
Non inventare: segnala e proponi opzioni.
