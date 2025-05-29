<div align="center">

  # 🏗️ Progetto ACCA - Accesso Cantieri
  
  **Un sistema gestionale completo per il controllo degli accessi ai cantieri**
  
  **[✨ Features](#features-)** | **[🚀 Installazione](#installazione-)** | **[⚙️ Configurazione](#configurazione-%EF%B8%8F)** | **[💻 Utilizzo](#utilizzo-%EF%B8%8F)** | **[🏗️ Architettura](#architettura-%EF%B8%8F)**
  
</div>

---

## 📋 Descrizione

**Progetto ACCA** è un sistema gestionale web sviluppato per una azienda locale per gestire e monitorare l'accesso del personale ai cantieri. Il sistema permette di tracciare dipendenti, aziende, badge di accesso e documenti in scadenza, garantendo sicurezza e conformità nei cantieri.

### 🎯 Problema Risolto

La azienda deve gestire numerosi dipendenti subappaltati ai cantieri, monitorando:
- Validità dei documenti di idoneità
- Emissione e stato dei badge di accesso
- Autorizzazioni agli accessi

Questo sistema automatizza e centralizza tutti questi processi in modo che multipli dipendenti possano operare in parallelo su un unico gestionale accessibile da più computer.

## Features ✨

### 👥 Gestione Personale
- **Gestione Ditte**: Registrazione completa delle aziende con dati di contatto dei referenti
- **Gestione Dipendenti**: Anagrafica completa con ruoli e associazione alle ditte
- **Sistema di Ruoli**: Differenziazione tra lavoratori regolari e ruoli speciali

### 🎫 Sistema Badge
- **Badge Permanenti**: Per i dipendenti subappaltati
- **Badge Temporanei**: Con scadenza per gli equipaggi
- **Stati Badge**:
  - ✅ Badge Emesso - è stato rilasciato
  - ✅ Badge Valido - consente l'accesso
  - ❌ Badge Sospeso - è temporaneamente sospeso
  - ❌ Badge Annullato - da rimuovere in futuro

### 📅 Monitoraggio Scadenze
- **Tracking Automatico**: Monitora la scadenza dei documenti di idoneità
- **Alert Email**: Notifiche automatiche per segnalare i documenti scaduti
- **Report Settimanali**: Email periodiche con le informazioni sul personale autorizzato

### 📊 Reporting
- **Presentazione**: Generazione report completi in formato Excel

### 🔐 Sicurezza e Controllo Accessi
- **Autenticazione**: Sistema di login con livelli di autorizzazione
- **Ruoli Utente**:
  - **Admin**: Accesso completo (CRUD su tutte le entità)
  - **User**: Solo visualizzazione
- **Controllo Granulare**: Permessi specifici per gestione dipendenti

## Installazione 🚀

### Prerequisiti

- Python 3.13.1
- MySQL 8.0+
- Credenziali OAuth 2.0 per Gmail API

### Setup Database

1. Crea il database MySQL:
```sql
CREATE DATABASE IF NOT EXISTS ACCA CHARACTER SET utf8mb4;
```

2. Esegui lo script di creazione tabelle dal file `database acca.txt`

3. Crea l'utente database:
```sql
CREATE USER user@localhost IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON ACCA.* TO 'user'@'localhost';
```

## Configurazione ⚙️

### 1. File passwords.py

Crea un file `python/passwords.py` con la seguente struttura:

```python
# Configurazione Database
database_config = (
    0,          # massimo connessioni totali
    0,          # connessioni minime in cache 
    0,          # connessione massime in cache
    'localhost', # host database
    'user', # utente database
    'password', # password database
    'ACCA'      # nome database
)

# Configurazione per report settimanali
database_config_weekly_report = database_config

# Secret key per Flask sessions
app_secret_key = 'secret'

# Configurazione Email
email_config = {
    'sender_email': 'email',
    'credentials_file': 'path to credentials json file'
}
```

### 2. Configurazione Gmail OAuth

1. Vai su [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuovo progetto o seleziona uno esistente
3. Abilita Gmail API
4. Crea credenziali OAuth 2.0
5. Scarica il file `credentials.json` e posizionalo nel path specificato in email_config dentro passwords.py
6. Aggiungi `http://localhost:16000/oauth/oauth2callback` come Redirect URI autorizzato
7. Aggiungi `http://localhost:16000` come origine JavaScript autorizzata

### 3. Prima Autorizzazione Gmail

Dopo aver avviato il server:
1. Vai su `http://localhost:16000/oauth/check_gmail_auth`
2. Clicca su "Autorizza Gmail"
3. Completa il flusso OAuth

## Utilizzo 🖥️

### Avvio del Server

```bash
python python/server.py
```

Il server sarà disponibile su `http://localhost:16000`

### Struttura Menu Base

- **🏢 Ditte**: Gestione aziende e subappaltatori
- **👷 Dipendenti**: Gestione personale e badge
- **📊 Report**: Generazione report Excel
- **🚪 Logout**: Uscita sicura

### Funzionalità Principali

#### Gestione Dipendenti
- Aggiungi nuovo dipendente con associazione ditta
- Modifica dati e stato badge
- Gestione badge temporanei con scadenza
- Tracking documenti in scadenza

#### Sistema di Ricerca
- 🔍 Ricerca per ditta
- 🔍 Ricerca per cognome
- 🔍 Visualizza badge annullati

#### Automazioni
- **Report Settimanali**: Esegui `python/send_weekly_report_oauth.py` settimanalmente
- **Controllo Scadenze**: Esegui `python/send_email_scaduti_oauth.py` quotidianamente

## Architettura 🏗️

### Stack Tecnologico
- **Struttura**: Web application
- **Backend**: Flask + Waitress production server
- **Database**: MySQL con connection pooling
- **Frontend**: Vanilla JavaScript + CSS
- **Email**: Gmail con OAuth 2.0

## 🧪 Testing

Il progetto include una test suite manuale documentata in `Test suite.txt` che copre:
- ✅ Operazioni CRUD su Ditte
- ✅ Operazioni CRUD su Dipendenti  
- ✅ Interfaccia grafica
- ✅ Generazione report

## 🔒 Sicurezza

- Validazione input lato server
- Prepared statements per prevenire le SQL injection
- OAuth 2.0 per autenticazione Gmail sicura

## ⚖️ Licenza

Copyright (c) Federico Veronesi. Tutti i diritti riservati.

Questo codice è fornito esclusivamente per la valutazione delle competenze tecniche dello sviluppatore. Vedi il file `LICENSE` per i dettagli completi.
