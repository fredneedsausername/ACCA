"""
No manual preprocessing is needed, just feed the algorithm the raw csv data given by the company.
This script takes the lines available and migrates the provided data to the db.
"""

from python import fredbconn
from python import passwords
import csv
from datetime import datetime, date, timedelta

def main():
    data_file_path = 'data.csv'
    temp_file_path = 'processed_data.csv'

    def pre_process_data():
        with open(data_file_path, 'r', encoding='utf-8') as infile, \
            open(temp_file_path, 'w', encoding='utf-8', newline='') as outfile:

            reader = csv.reader(infile, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')

            # Skip the first two header lines
            next(reader)  # Skip header line 1
            next(reader)  # Skip header line 2
            
            for row in reader:
                # Skip empty rows or rows with only separators/whitespace
                if not any(field.strip() for field in row):
                    continue

                # Extract relevant fields
                ditta = row[0].strip('*').strip().strip('*')
                nome = row[1].strip() if len(row) > 1 and row[1].strip() else ''
                cognome = row[2].strip() if len(row) > 2 and row[2].strip() else ''
                note = row[3].strip() if len(row) > 3 and row[3].strip() else ''
                
                # New fields in the updated CSV
                scadenza = row[4].strip() if len(row) > 4 and row[4].strip() else ''
                badge_emesso = 'X' if len(row) > 5 and row[5].strip() == 'X' else ''
                badge_valido = 'X' if len(row) > 6 and row[6].strip() == 'X' else ''
                
                # Write the processed row to the output file
                writer.writerow([
                    ditta,
                    nome,
                    cognome,
                    note,
                    scadenza,
                    badge_emesso,
                    badge_valido
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
                INSERT INTO ditte (nome)
                VALUES (%s)
                """, (ditta,))
            
            for ditta in ditte:
                aggiungi_ditta_to_db(ditta)

        with open(temp_file_path, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile, delimiter=';')

            for row in reader:
                ditta = row[0]
                nome = row[1]
                cognome = row[2]
                note = row[3]
                scadenza_str = row[4]
                badge_emesso = row[5]
                badge_valido = row[6]
                
                # Convert scadenza_str to a proper date if it exists
                scadenza_autorizzazione = None
                if scadenza_str:
                    try:
                        # Parse date in format DD/MM/YYYY
                        scadenza_autorizzazione = datetime.strptime(scadenza_str, "%d/%m/%Y").date()
                    except ValueError:
                        # If parsing fails, try alternate format
                        try:
                            scadenza_autorizzazione = datetime.strptime(scadenza_str, "%d-%m-%Y").date()
                        except ValueError:
                            # If both fail, set to None
                            scadenza_autorizzazione = None

                @fredbconn.connected_to_database
                def associa_nome_ditta_a_id(cursor, ditta):
                    cursor.execute("""
                    SELECT id
                    FROM ditte
                    WHERE nome = %s
                    """, (ditta,))

                    result = cursor.fetchone()
                    return result[0] if result else None  # Extract the ID from the tuple
                
                id_ditta = associa_nome_ditta_a_id(ditta)

                @fredbconn.connected_to_database
                def add_dipendente_to_db(cursor):
                    # Map CSV fields to database fields directly
                    # - badge_valido in CSV maps to badge_sospeso in DB (direct mapping)
                    # - accesso_bloccato in DB is set to 1 by default as per requirement
                    
                    is_badge_emesso = 1 if badge_emesso == 'X' else 0
                    badge_sospeso = 1 if badge_valido == 'X' else 0  # Direct mapping as requested
                    
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
                        is_badge_emesso,
                        scadenza_autorizzazione,
                        1,              # accesso_bloccato (default: yes as per requirement)
                        badge_sospeso,  # Inverted from badge_valido
                        note
                    ))

                add_dipendente_to_db()

    pre_process_data()
    add_pre_processed_data_to_db()
        
if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)
    main()