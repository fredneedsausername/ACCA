> [!CAUTION]
> Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

# Progetto ACCA
Il Progetto ACCA, o accesso cantieri, consiste in un gestionale di accesso ai cantieri per una azienda locale dalla quale sono stato commissionato.

## Database

Attori: segretaria: usa il sito per mettere i dati, portiere: guarda i dati immessi, report settimanali (ancora poco chiari)


Utenti:
- due livelli di autenticazione: admin e watcher
- abilitato sì/no (per disattivarlo in un qualunque momento senza cancellare l'account)
- nome utente
- password

Ditta:
- nome
- piva
- note (campo testuale enorme di 1024 caratteri, se non più grande)
- scadenza autorizzazione
- autorizzata sì/no (per disattivarla in un qualunque momento senza cancellare l'account)
- referente

Referente:
- nome e cognonme (unico campo)
- email
- numero telefonico

Dipendente:
- nome
- ditra
- badge già emesso (per quando un dipendente è stato censito ma il suo badge ancora non emesso)
- autorizzato sì/no

si può cercare un dipendente per nome, cognome, ditta di appartenenza. Da questa pagina è possibile esportare in pdf l'elenco delle persone trovate
