import io
import xlsxwriter
from datetime import datetime

try:
    # First attempt direct import (works when running server.py)
    import fredbconn
except ImportError:
    # Fall back to package import (works when running send_weekly_report.py)
    from python import fredbconn

def generate_weekly_report():
    """Generate the weekly report with only badge_valido employees.
    This is used for the automated weekly email report.
    """
    # Create a BytesIO object for the Excel file
    output = io.BytesIO()
    
    @fredbconn.connected_to_database
    def fetch_dipendenti_with_valid_badge(cursor):
        cursor.execute("""
        SELECT
            dipendenti.id,
            ditte.nome AS ditta_nome,
            dipendenti.nome AS dipendente_nome,
            dipendenti.cognome,
            ruoli.nome_ruolo,
            dipendenti.scadenza_autorizzazione,
            dipendenti.is_badge_temporaneo
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
        WHERE
            dipendenti.badge_sospeso = 1  -- Only employees with badge_valido (badge_sospeso=1)
            AND dipendenti.badge_annullato = 0  -- Exclude annullato badges
        ORDER BY
            ditte.nome ASC
        """)
        return fredbconn.fetch_generator(cursor)

    # Process data
    temp_badges_data = []
    regular_badges_data = []

    for dipendente in fetch_dipendenti_with_valid_badge():
        try:
            ditta_nome = dipendente[1] if len(dipendente) > 1 else ""
            dipendente_nome = dipendente[2] if len(dipendente) > 2 else ""
            dipendente_cognome = dipendente[3] if len(dipendente) > 3 else ""
            ruolo = dipendente[4] if len(dipendente) > 4 else ""  # Use ruolo instead of note
            scadenza_autorizzazione = dipendente[5] if len(dipendente) > 5 else None
            is_badge_temporaneo = dipendente[6] if len(dipendente) > 6 else 0
            
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
            
            employee_data = (
                ditta_nome,
                dipendente_nome,
                dipendente_cognome,
                ruolo,  # Use ruolo instead of note
                validita_documenti
            )
            
            # Separate employees into temporary and regular badge groups
            if is_badge_temporaneo:
                temp_badges_data.append(employee_data)
            else:
                regular_badges_data.append(employee_data)
                
        except Exception as e:
            print(f"Error processing record: {str(dipendente)}, Error: {str(e)}")
            continue
    
    # Sort each group alphabetically by company name, then by employee last name, then by first name
    temp_badges_data.sort(key=lambda x: (x[0].lower(), x[2].lower(), x[1].lower()))
    regular_badges_data.sort(key=lambda x: (x[0].lower(), x[2].lower(), x[1].lower()))

    # Create Excel workbook in memory
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
    
    # Create section header format (grey background)
    section_header_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#D9D9D9'  # Light grey background
    })
    
    # Write report title - Use "LISTA PERSONALE CON BADGE VALIDO" for the weekly report
    worksheet.write_rich_string(0, 0,
                            rich_format_18, "LISTA PERSONALE CON BADGE VALIDO",
                            rich_format_14, aggiornato_string)

    # Set up headers - No checkbox columns for the weekly report
    header_row = 1
    worksheet.set_row(header_row, 45)

    worksheet.write(header_row, 0, "DITTA", ditta_header_format)
    worksheet.write(header_row, 1, "NOME", nome_header_format)
    worksheet.write(header_row, 2, "COGNOME", nome_header_format)
    worksheet.write(header_row, 3, "RUOLO", note_header_format)  # Changed from NOTE to RUOLO
    worksheet.write(header_row, 4, "SCADENZA\nDOCUMENTI", note_header_format)

    # Initialize the current row counter
    current_row = header_row + 1
    
    # Add "Badge temporanei" section header if there are any temporary badges
    if temp_badges_data:
        worksheet.set_row(current_row, 25)  # Taller row for section header
        for col in range(5):  # Merge all columns (only 5 in the weekly report)
            worksheet.write(current_row, col, "", section_header_format)
        worksheet.merge_range(current_row, 0, current_row, 4, "Badge temporanei", section_header_format)
        current_row += 1
        
        # Write temporary badge data
        for data_row in temp_badges_data:
            worksheet.set_row(current_row, 15)
            
            worksheet.write(current_row, 0, data_row[0], ditta_data_format)
            worksheet.write(current_row, 1, data_row[1], default_format)
            worksheet.write(current_row, 2, data_row[2], default_format)
            worksheet.write(current_row, 3, data_row[3], ruolo_data_format)  # Use ruolo instead of note
            worksheet.write(current_row, 4, data_row[4], default_format)
            
            current_row += 1
    
    # Add "Personale" section header if there are any regular badges
    if regular_badges_data:
        worksheet.set_row(current_row, 25)  # Taller row for section header
        for col in range(5):  # Merge all columns (only 5 in the weekly report)
            worksheet.write(current_row, col, "", section_header_format)
        worksheet.merge_range(current_row, 0, current_row, 4, "Personale", section_header_format)
        current_row += 1
        
        # Write regular badge data
        for data_row in regular_badges_data:
            worksheet.set_row(current_row, 15)
            
            worksheet.write(current_row, 0, data_row[0], ditta_data_format)
            worksheet.write(current_row, 1, data_row[1], default_format)
            worksheet.write(current_row, 2, data_row[2], default_format)
            worksheet.write(current_row, 3, data_row[3], ruolo_data_format)  # Use ruolo instead of note
            worksheet.write(current_row, 4, data_row[4], default_format)
            
            current_row += 1

    # Add summary of counts
    current_row += 2  # Add some space
    
    # Calculate totals
    total_employees = len(temp_badges_data) + len(regular_badges_data)
    
    # Count unique companies
    unique_companies = set()
    for data_row in temp_badges_data + regular_badges_data:
        company_name = data_row[0]
        if company_name:  # Skip empty company names if any
            unique_companies.add(company_name)
    
    total_companies = len(unique_companies)
    
    # Create summary format
    summary_format = workbook.add_format({
        'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter',
    })
    
    # Write summary information
    worksheet.write(current_row, 0, f"Totale ditte visualizzate: {total_companies}", summary_format)
    current_row += 1
    worksheet.write(current_row, 0, f"Totale dipendenti visualizzati: {total_employees}", summary_format)

    # Set column widths
    headers = ["DITTA", "NOME", "COGNOME", "RUOLO", "SCADENZA DOCUMENTI"]  # Updated to RUOLO
    col_widths = [len(header) for header in headers]
    
    # Consider all data rows for column width calculation
    all_data = temp_badges_data + regular_badges_data
    for row in all_data:
        for i in range(min(len(headers), len(row))):
            cell_length = len(str(row[i]))
            if cell_length > col_widths[i]:
                col_widths[i] = cell_length
    
    extra_padding = 10
    col_widths = [width + extra_padding for width in col_widths]
    
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)

    workbook.close()
    output.seek(0)
    
    return output