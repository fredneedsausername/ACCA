> [!CAUTION]
> Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

# Progetto ACCA
Il Progetto ACCA, o accesso cantieri, consiste in un gestionale di accesso ai cantieri per una azienda locale dalla quale sono stato commissionato.

## Database
These is the SQL code to recreate the MySQL database the app runs on

```sql
CREATE DATABASE IF NOT EXISTS ACCA
  CHARACTER SET utf8mb4;

use ACCA;

CREATE TABLE IF NOT EXISTS utenti (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50),
  password VARCHAR(50),
  is_admin TINYINT,
  abilitato TINYINT
);

CREATE TABLE IF NOT EXISTS ditte (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(150),
  piva VARCHAR(20),
  scadenza_autorizzazione VARCHAR(50),
  blocca_accesso TINYINT,
  nome_cognome_referente VARCHAR(100),
  email_referente VARCHAR(100),
  telefono_referente VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS dipendenti (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(50),
  cognome VARCHAR(50),
  ditta_id INT UNSIGNED,
  is_badge_already_emesso TINYINT,
  autorizzato TINYINT,
  note VARCHAR(512),
  FOREIGN KEY (ditta_id) REFERENCES ditte(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

CREATE INDEX indice_nome ON dipendenti (nome);
CREATE INDEX indice_cognome ON dipendenti (cognome);
CREATE INDEX indice_ditta ON dipendenti (ditta_id);
```
