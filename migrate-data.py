# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details
"""
No manual preprocessing is needed, just feed the algorithm the raw csv data given by the company.
This script takes the lines available and migrates the provided data to the db, assuming all dipendenti in the csv were already given a badge.
"""

from python import fredbconn
from python import passwords
import csv
from datetime import date, timedelta

def main():
    data_file_path = 'data.csv'
    temp_file_path = 'processed_data.csv'

    def pre_process_data():
        with open(data_file_path, 'r', encoding='utf-8') as infile, \
            open(temp_file_path, 'w', encoding='utf-8', newline='') as outfile:

            reader = csv.reader(infile, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')

            next(reader)  # Skip header line
            next(reader)  # Skip header line
            for row in reader:
                # Skip empty rows or rows with only separators/whitespace
                if not any(field.strip() for field in row):
                    continue

                # Extract relevant fields
                ditta = row[0].strip('*').strip().strip('*')
                nome = row[1].strip()
                cognome = row[2].strip()
                note = row[3].strip() if len(row) > 3 and row[3].strip() else None

                # Write the processed row directly to the output file
                writer.writerow([
                    ditta,
                    nome,
                    cognome,
                    note if note else ''
                ])
    
    def add_pre_processed_data_to_db():
        with open(temp_file_path, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile, delimiter=';')

            ditte = set()

            for row in reader:
                ditte.add(row[0])

            @fredbconn.connected_to_database
            def aggiungi_ditta_to_db(cursor, ditta: str):
                cursor.execute("""
                INSERT INTO ditte (nome, blocca_accesso)
                VALUES (%s, %s)
                """, (ditta, 0))
            
            for ditta in ditte:
                aggiungi_ditta_to_db(ditta)

        # No default expiration date
        default_expiration = None

        with open(temp_file_path, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile, delimiter=';')

            for row in reader:
                ditta = row[0]
                nome = row[1]
                cognome = row[2]
                note = row[3]

                @fredbconn.connected_to_database
                def associa_nome_ditta_a_id(cursor, ditta):
                    cursor.execute("""
                    SELECT id
                    FROM ditte
                    WHERE nome = %s
                    """, (ditta,))

                    return cursor.fetchone()
                
                id_ditta = associa_nome_ditta_a_id(ditta)

                @fredbconn.connected_to_database
                def add_dipendente_to_db(cursor):
                    # Updated SQL to match the new database schema
                    cursor.execute("""
                    INSERT INTO dipendenti (
                        nome, 
                        cognome, 
                        ditta_id, 
                        is_badge_already_emesso, 
                        scadenza_autorizzazione, 
                        accesso_bloccato, 
                        badge_sospeso, 
                        note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        nome, 
                        cognome, 
                        id_ditta, 
                        1,              # is_badge_already_emesso (default: yes)
                        default_expiration,  # scadenza_autorizzazione (default: 1 year from now)
                        0,              # accesso_bloccato (default: no)
                        0,              # badge_sospeso (default: no)
                        note
                    ))

                add_dipendente_to_db()

    pre_process_data()
    add_pre_processed_data_to_db()
        
if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)
    main()