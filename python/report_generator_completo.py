import io
import xlsxwriter
from datetime import datetime

try:
    # First attempt direct import (works when running server.py)
    import fredbconn
except ImportError:
    # Fall back to package import (works when running send_weekly_report.py)
    from python import fredbconn

def generate_report():
    """Generate the report as a BytesIO object containing an Excel file."""
    
    @fredbconn.connected_to_database
    def fetch_dipendenti(cursor):
        cursor.execute("""
        SELECT
            dipendenti.id,
            ditte.nome AS ditta_nome,
            dipendenti.nome AS dipendente_nome,
            dipendenti.cognome,
            ruoli.nome_ruolo,
            dipendenti.scadenza_autorizzazione,
            dipendenti.is_badge_already_emesso,
            dipendenti.badge_sospeso,
            dipendenti.badge_annullato
        FROM 
            dipendenti
        JOIN 
            ditte
        ON 
            dipendenti.ditta_id = ditte.id
        LEFT JOIN
            ruoli
        ON
            dipendenti.ruolo_id = ruoli.id
        ORDER BY
            ditte.nome ASC
        """)
        return fredbconn.fetch_generator(cursor)

    # Process data
    custom_data = []

    for dipendente in fetch_dipendenti():
        try:
            ditta_nome = dipendente[1] if len(dipendente) > 1 else ""
            dipendente_nome = dipendente[2] if len(dipendente) > 2 else ""
            dipendente_cognome = dipendente[3] if len(dipendente) > 3 else ""
            ruolo = dipendente[4] if len(dipendente) > 4 else ""  # Use ruolo instead of note
            scadenza_autorizzazione = dipendente[5] if len(dipendente) > 5 else None
            is_badge_emesso = dipendente[6] if len(dipendente) > 6 else 0
            is_badge_sospeso = dipendente[7] if len(dipendente) > 7 else 0
            is_badge_annullato = dipendente[8] if len(dipendente) > 8 else 0
            
            badge_emesso = "X" if is_badge_emesso else ""
            badge_valido = "X" if is_badge_sospeso else ""
            
            # Format the date if exists
            validita_documenti = ""
            if scadenza_autorizzazione:
                if isinstance(scadenza_autorizzazione, str):
                    try:
                        scadenza_dt = datetime.strptime(scadenza_autorizzazione, "%Y-%m-%d")
                        validita_documenti = scadenza_dt.strftime("%d/%m/%Y")
                    except ValueError:
                        validita_documenti = scadenza_autorizzazione
                else:
                    try:
                        validita_documenti = scadenza_autorizzazione.strftime("%d/%m/%Y")
                    except AttributeError:
                        validita_documenti = str(scadenza_autorizzazione)
            
            custom_data.append((
                ditta_nome,
                dipendente_nome,
                dipendente_cognome,
                ruolo,  # Use ruolo instead of note
                validita_documenti,
                badge_emesso,
                badge_valido
            ))
        except Exception as e:
            print(f"Error processing record: {str(dipendente)}, Error: {str(e)}")
            continue

    # Create Excel workbook in memory
    output = io.BytesIO()
    todays_local_date = datetime.now().strftime("%d-%m-%Y")
    aggiornato_string = " (Agg. " + todays_local_date + ")"

    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("report")

    # Define formats
    default_format = workbook.add_format({
        'font_size': 13, 'align': 'center', 'valign': 'vcenter', 'border': 1,
    })
    
    ditta_header_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#FFFF00', 'text_wrap': True
    })
    
    nome_header_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#00B0F0', 'text_wrap': True
    })
    
    note_header_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#92D050', 'text_wrap': True
    })
    
    badge_header_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#92D050', 'text_wrap': True
    })
    
    ditta_data_format = workbook.add_format({
        'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter',
        'border': 1,
    })
    
    ruolo_data_format = workbook.add_format({  # Renamed from note_data_format
        'italic': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter',
        'border': 1,
    })
    
    rich_format_18 = workbook.add_format({
        'font_size': 18, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bold': True
    })
    
    rich_format_14 = workbook.add_format({
        'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bold': True
    })
    
    # Write report title
    worksheet.write_rich_string(0, 0,
                            rich_format_18, "LISTA PERSONALE AUTORIZZATO ALL'INGRESSO",
                            rich_format_14, aggiornato_string)

    # Set up headers
    header_row = 1
    worksheet.set_row(header_row, 45)

    worksheet.write(header_row, 0, "DITTA", ditta_header_format)
    worksheet.write(header_row, 1, "NOME", nome_header_format)
    worksheet.write(header_row, 2, "COGNOME", nome_header_format)
    worksheet.write(header_row, 3, "RUOLO", note_header_format)  # Changed from NOTE to RUOLO
    worksheet.write(header_row, 4, "SCADENZA\nDOCUMENTI", note_header_format)
    worksheet.write(header_row, 5, "BADGE\nEMESSO", badge_header_format)
    worksheet.write(header_row, 6, "BADGE\nVALIDO", badge_header_format)

    # Write data rows
    data_start_row = header_row + 1
    for row_idx, data_row in enumerate(custom_data):
        current_row = data_start_row + row_idx
        worksheet.set_row(current_row, 15)
        
        worksheet.write(current_row, 0, data_row[0], ditta_data_format)
        worksheet.write(current_row, 1, data_row[1], default_format)
        worksheet.write(current_row, 2, data_row[2], default_format)
        worksheet.write(current_row, 3, data_row[3], ruolo_data_format)  # Use ruolo instead of note
        worksheet.write(current_row, 4, data_row[4], default_format)
        worksheet.write(current_row, 5, data_row[5], default_format)
        worksheet.write(current_row, 6, data_row[6], default_format)

    # Set column widths
    headers = ["DITTA", "NOME", "COGNOME", "RUOLO", "VALIDITÁ DOCUMENTI", "BADGE EMESSO", "BADGE VALIDO"]  # Updated to RUOLO
    col_widths = [len(header) for header in headers]
    
    for row in custom_data:
        for i in range(min(len(headers), len(row))):
            cell_length = len(str(row[i]))
            if cell_length > col_widths[i]:
                col_widths[i] = cell_length
    
    extra_padding = 10
    col_widths = [width + extra_padding for width in col_widths]
    
    reduced_padding = 0
    col_widths[4] = len(headers[4]) + reduced_padding
    col_widths[5] = len(headers[5]) + reduced_padding
    col_widths[6] = len(headers[6]) + reduced_padding
    
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)

    workbook.close()
    output.seek(0)
    
    return output