# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

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
    """Generate the regular report as a BytesIO object containing an Excel file."""
    
    @fredbconn.connected_to_database
    def fetch_dipendenti(cursor):
        cursor.execute("""
        SELECT
            dipendenti.id,
            ditte.nome AS ditta_nome,
            dipendenti.nome AS dipendente_nome,
            dipendenti.cognome,
            dipendenti.note,
            dipendenti.scadenza_autorizzazione,
            dipendenti.is_badge_already_emesso,
            dipendenti.badge_sospeso,
            dipendenti.badge_annullato,
            dipendenti.is_badge_temporaneo,
            dipendenti.numero_badge
        FROM 
            dipendenti
        JOIN 
            ditte
        ON 
            dipendenti.ditta_id = ditte.id
        WHERE
            dipendenti.badge_annullato = 0
        ORDER BY
            dipendenti.is_badge_temporaneo DESC,  -- Temporary badges first
            ditte.nome ASC
        """)
        return fredbconn.fetch_generator(cursor)

    @fredbconn.connected_to_database
    def count_companies_and_employees(cursor):
        # Count active companies with at least one active employee
        cursor.execute("""
        SELECT COUNT(DISTINCT ditte.id)
        FROM ditte
        JOIN dipendenti ON ditte.id = dipendenti.ditta_id
        WHERE dipendenti.badge_annullato = 0
        """)
        company_count = cursor.fetchone()[0]
        
        # Count active employees
        cursor.execute("""
        SELECT COUNT(*)
        FROM dipendenti
        WHERE badge_annullato = 0
        """)
        employee_count = cursor.fetchone()[0]
        
        return company_count, employee_count

    # Process data - separate temporary and regular badges
    temp_badge_data = []
    regular_data = []

    for dipendente in fetch_dipendenti():
        try:
            ditta_nome = dipendente[1] if len(dipendente) > 1 else ""
            dipendente_nome = dipendente[2] if len(dipendente) > 2 else ""
            dipendente_cognome = dipendente[3] if len(dipendente) > 3 else ""
            note = dipendente[4] if len(dipendente) > 4 else ""
            scadenza_autorizzazione = dipendente[5] if len(dipendente) > 5 else None
            is_badge_emesso = dipendente[6] if len(dipendente) > 6 else 0
            is_badge_sospeso = dipendente[7] if len(dipendente) > 7 else 0
            is_badge_annullato = dipendente[8] if len(dipendente) > 8 else 0
            is_badge_temporaneo = dipendente[9] if len(dipendente) > 9 and dipendente[9] is not None else 0
            numero_badge = dipendente[10] if len(dipendente) > 10 and dipendente[10] is not None else ""
            
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
            
            # Base data row without numero_badge
            row_data = (
                ditta_nome,
                dipendente_nome,
                dipendente_cognome,
                note,
                validita_documenti,
                badge_emesso,
                badge_valido
            )
            
            # Add to appropriate list based on badge type
            if is_badge_temporaneo:
                temp_badge_data.append(row_data + (numero_badge,))
            else:
                regular_data.append(row_data)
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
    
    note_data_format = workbook.add_format({
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
    
    temp_section_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#D3D3D3', 'color': '#000000', 'text_wrap': True
    })
    
    regular_section_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#D3D3D3', 'text_wrap': True
    })
    
    footer_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'left', 'valign': 'vcenter',
        'border': 0
    })
    
    # Write report title - Use "LISTA PERSONALE" as in the reduced version
    worksheet.write_rich_string(0, 0,
                            rich_format_18, "LISTA PERSONALE",
                            rich_format_14, aggiornato_string)

    # Set up standard headers
    header_row = 1
    worksheet.set_row(header_row, 45)

    worksheet.write(header_row, 0, "DITTA", ditta_header_format)
    worksheet.write(header_row, 1, "NOME", nome_header_format)
    worksheet.write(header_row, 2, "COGNOME", nome_header_format)
    worksheet.write(header_row, 3, "NOTE", note_header_format)
    worksheet.write(header_row, 4, "SCADENZA\nDOCUMENTI", note_header_format)
    worksheet.write(header_row, 5, "BADGE\nEMESSO", badge_header_format)
    worksheet.write(header_row, 6, "BADGE\nVALIDO", badge_header_format)

    # Start data rows after the header
    current_row = header_row + 1
    
    # Handle temporary badges if any exist
    if temp_badge_data:
        # Add "Badge temporanei" section header (span across all columns)
        worksheet.merge_range(current_row, 0, current_row, 6, "Badge temporanei", temp_section_format)
        current_row += 1
        
        # Add temporary badge header row with numero_badge column
        worksheet.write(current_row, 0, "DITTA", ditta_header_format)
        worksheet.write(current_row, 1, "NOME", nome_header_format)
        worksheet.write(current_row, 2, "COGNOME", nome_header_format)
        worksheet.write(current_row, 3, "NOTE", note_header_format)
        worksheet.write(current_row, 4, "SCADENZA\nDOCUMENTI", note_header_format)
        worksheet.write(current_row, 5, "BADGE\nEMESSO", badge_header_format)
        worksheet.write(current_row, 6, "BADGE\nVALIDO", badge_header_format)
        worksheet.write(current_row, 7, "NUMERO\nBADGE", badge_header_format)
        current_row += 1
        
        # Write temporary badge data with numero_badge
        for data_row in temp_badge_data:
            worksheet.set_row(current_row, 15)
            
            worksheet.write(current_row, 0, data_row[0], ditta_data_format)
            worksheet.write(current_row, 1, data_row[1], default_format)
            worksheet.write(current_row, 2, data_row[2], default_format)
            worksheet.write(current_row, 3, data_row[3], note_data_format)
            worksheet.write(current_row, 4, data_row[4], default_format)
            worksheet.write(current_row, 5, data_row[5], default_format)
            worksheet.write(current_row, 6, data_row[6], default_format)
            worksheet.write(current_row, 7, data_row[7], default_format)  # Numero badge
            
            current_row += 1
    
    # Add "Personale" section for regular employees
    if regular_data:
        # Only add the section header if we have both types of badges
        if temp_badge_data:
            worksheet.merge_range(current_row, 0, current_row, 6, "Personale", regular_section_format)
            current_row += 1
            
            # Regular header row (without numero_badge column)
            worksheet.write(current_row, 0, "DITTA", ditta_header_format)
            worksheet.write(current_row, 1, "NOME", nome_header_format)
            worksheet.write(current_row, 2, "COGNOME", nome_header_format)
            worksheet.write(current_row, 3, "NOTE", note_header_format)
            worksheet.write(current_row, 4, "SCADENZA\nDOCUMENTI", note_header_format)
            worksheet.write(current_row, 5, "BADGE\nEMESSO", badge_header_format)
            worksheet.write(current_row, 6, "BADGE\nVALIDO", badge_header_format)
            current_row += 1
        
        # Write regular employee data
        for data_row in regular_data:
            worksheet.set_row(current_row, 15)
            
            worksheet.write(current_row, 0, data_row[0], ditta_data_format)
            worksheet.write(current_row, 1, data_row[1], default_format)
            worksheet.write(current_row, 2, data_row[2], default_format)
            worksheet.write(current_row, 3, data_row[3], note_data_format)
            worksheet.write(current_row, 4, data_row[4], default_format)
            worksheet.write(current_row, 5, data_row[5], default_format)
            worksheet.write(current_row, 6, data_row[6], default_format)
            
            current_row += 1

    # Add footer with counts of companies and employees
    company_count, employee_count = count_companies_and_employees()
    
    current_row += 1
    worksheet.write(current_row, 0, f"Numero aziende: {company_count}", footer_format)
    current_row += 1
    worksheet.write(current_row, 0, f"Numero dipendenti: {employee_count}", footer_format)

    # Set column widths
    headers = ["DITTA", "NOME", "COGNOME", "NOTE", "VALIDITÁ DOCUMENTI", "BADGE EMESSO", "BADGE VALIDO", "NUMERO BADGE"]
    col_widths = [len(header) for header in headers]
    
    # Adjust widths based on content
    for row in temp_badge_data:
        for i in range(min(len(headers), len(row))):
            cell_length = len(str(row[i]))
            if cell_length > col_widths[i]:
                col_widths[i] = cell_length
    
    for row in regular_data:
        for i in range(min(len(headers) - 1, len(row))):  # -1 because no numero_badge
            cell_length = len(str(row[i]))
            if cell_length > col_widths[i]:
                col_widths[i] = cell_length
    
    extra_padding = 10
    col_widths = [width + extra_padding for width in col_widths]
    
    reduced_padding = 0
    col_widths[4] = len(headers[4]) + reduced_padding
    col_widths[5] = len(headers[5]) + reduced_padding
    col_widths[6] = len(headers[6]) + reduced_padding
    if len(col_widths) > 7:
        col_widths[7] = len(headers[7]) + reduced_padding
    
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)

    workbook.close()
    output.seek(0)
    
    return output