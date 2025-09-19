import io
import os
import sys
import xlsxwriter
import logging
from datetime import datetime
import traceback

import fredbconn
from passwords import email_config
import email_manager_oauth  # Import OAuth version

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "email-logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "scadenza_documenti.log")

logging.basicConfig(
    filename=log_file,
    filemode='w',  # 'w' mode overwrites the existing file
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ExpiredBadgesReport")


def get_email_recipients():
    """Fetch email recipients from the database."""
    logger.info("Fetching email recipients from database")
    
    @fredbconn.connected_to_database
    def fetch_recipients(cursor):
        cursor.execute("SELECT email FROM email_recipients_scaduti")
        return [row[0] for row in fredbconn.fetch_generator(cursor)]
    
    recipients = fetch_recipients()
    if not recipients:
        # Fallback to sender email if no recipients configured
        recipients = [email_config['sender_email']]
        logger.warning("No email recipients found in database. Using sender email as fallback.")
    else:
        logger.info(f"Found {len(recipients)} email recipients")
    
    return recipients


def get_expired_badges():
    """Fetch employees with expired badges, only including issued and valid badges that aren't canceled."""
    logger.info("Checking for expired badges (only issued and valid badges that aren't canceled)")
    
    @fredbconn.connected_to_database
    def fetch_expired_badges(cursor):
        # Get today's date for comparison
        today = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
        SELECT
            dipendenti.nome,
            dipendenti.cognome,
            ditte.nome AS ditta_nome,
            dipendenti.scadenza_autorizzazione,
            dipendenti.is_badge_temporaneo
        FROM 
            dipendenti
        JOIN 
            ditte ON dipendenti.ditta_id = ditte.id
        WHERE 
            dipendenti.scadenza_autorizzazione <= %s
            AND dipendenti.is_badge_already_emesso = 1
            AND dipendenti.badge_annullato = 0
            AND dipendenti.badge_sospeso = 1
        ORDER BY
            dipendenti.is_badge_temporaneo DESC,
            ditte.nome ASC,
            dipendenti.cognome ASC,
            dipendenti.nome ASC
        """, (today,))
        
        return list(fredbconn.fetch_generator(cursor))
    
    return fetch_expired_badges()


def generate_excel_report(expired_badges):
    """Generate Excel report with expired badges data."""
    logger.info("Generating Excel report")
    output = io.BytesIO()
    current_date = datetime.now().strftime("%d-%m-%Y")
    
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Badge Scaduti")
    
    # Define formats
    title_format = workbook.add_format({
        'font_size': 18, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bold': True
    })
    
    header_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#92D050', 'text_wrap': True
    })
    
    default_format = workbook.add_format({
        'font_size': 13, 'align': 'center', 'valign': 'vcenter', 'border': 1,
    })
    
    ditta_format = workbook.add_format({
        'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter',
        'border': 1,
    })
    
    # Create section header format (grey background)
    section_header_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#D9D9D9'  # Light grey background
    })
    
    # Write report title
    worksheet.merge_range('A1:D1', f"ELENCO BADGE SCADUTI (Agg. {current_date})", title_format)
    
    # Set up headers
    header_row = 1
    worksheet.set_row(header_row, 45)  # Increased to 45 to match other reports
    
    headers = ["NOME", "COGNOME", "DITTA", "SCADENZA DOCUMENTI"]
    for col, header in enumerate(headers):
        worksheet.write(header_row, col, header, header_format)
    
    # Separate badges into temporary and non-temporary
    temp_badges = []
    non_temp_badges = []
    
    for badge in expired_badges:
        # Check is_badge_temporaneo (position 4 in the tuple)
        is_temp = badge[4] if len(badge) > 4 else 0
        
        if is_temp:
            temp_badges.append(badge)
        else:
            non_temp_badges.append(badge)
    
    # Initialize current row counter
    current_row = header_row + 1
    
    # Process temporary badges
    if temp_badges:
        # Add section header for temporary badges
        worksheet.set_row(current_row, 25)  # Taller row for section header
        worksheet.merge_range(current_row, 0, current_row, 3, "Badge temporanei", section_header_format)
        current_row += 1
        
        # Write temporary badge data
        for badge in temp_badges:
            # Extract data with safety checks
            nome = badge[0] if len(badge) > 0 and badge[0] else ""
            cognome = badge[1] if len(badge) > 1 and badge[1] else ""
            ditta = badge[2] if len(badge) > 2 and badge[2] else ""
            
            # Format the date
            scadenza = badge[3] if len(badge) > 3 else None
            formatted_date = format_date(scadenza)
            
            # Write to worksheet
            worksheet.write(current_row, 0, nome, default_format)
            worksheet.write(current_row, 1, cognome, default_format)
            worksheet.write(current_row, 2, ditta, ditta_format)
            worksheet.write(current_row, 3, formatted_date, default_format)
            current_row += 1
    
    # Process non-temporary badges
    if non_temp_badges:
        # Add section header for non-temporary badges
        worksheet.set_row(current_row, 25)  # Taller row for section header
        worksheet.merge_range(current_row, 0, current_row, 3, "Badge non temporanei", section_header_format)
        current_row += 1
        
        # Write non-temporary badge data
        for badge in non_temp_badges:
            # Extract data with safety checks
            nome = badge[0] if len(badge) > 0 and badge[0] else ""
            cognome = badge[1] if len(badge) > 1 and badge[1] else ""
            ditta = badge[2] if len(badge) > 2 and badge[2] else ""
            
            # Format the date
            scadenza = badge[3] if len(badge) > 3 else None
            formatted_date = format_date(scadenza)
            
            # Write to worksheet
            worksheet.write(current_row, 0, nome, default_format)
            worksheet.write(current_row, 1, cognome, default_format)
            worksheet.write(current_row, 2, ditta, ditta_format)
            worksheet.write(current_row, 3, formatted_date, default_format)
            current_row += 1
    
    # Add summary counts
    current_row += 1  # Add space
    summary_format = workbook.add_format({
        'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter',
    })
    
    worksheet.write(current_row, 0, f"Totale badge temporanei: {len(temp_badges)}", summary_format)
    current_row += 1
    worksheet.write(current_row, 0, f"Totale badge non temporanei: {len(non_temp_badges)}", summary_format)
    current_row += 1
    worksheet.write(current_row, 0, f"Totale badge scaduti: {len(expired_badges)}", summary_format)
    
    # Set column widths based on content
    set_column_widths(worksheet, expired_badges, headers)
    
    workbook.close()
    output.seek(0)
    logger.info("Excel report generated successfully")
    return output

def format_date(scadenza):
    """Helper function to format dates consistently."""
    formatted_date = ""
    if scadenza:
        if isinstance(scadenza, str):
            try:
                scadenza_dt = datetime.strptime(scadenza, "%Y-%m-%d")
                formatted_date = scadenza_dt.strftime("%d/%m/%Y")
            except ValueError:
                formatted_date = scadenza
        else:
            try:
                formatted_date = scadenza.strftime("%d/%m/%Y")
            except AttributeError:
                formatted_date = str(scadenza)
    return formatted_date

def set_column_widths(worksheet, data, headers):
    """Helper function to set column widths based on content."""
    col_widths = [len(header) for header in headers]
    
    # Adjust widths based on content
    for row in data:
        for i in range(min(len(headers), len(row))):
            if i < len(row) and row[i]:
                cell_length = len(str(row[i]))
                if cell_length > col_widths[i]:
                    col_widths[i] = min(cell_length, 50)  # Cap at 50 to prevent excessive width
    
    # Add padding
    extra_padding = 5
    col_widths = [width + extra_padding for width in col_widths]
    
    # Set final column widths
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)


def send_email(has_expired_badges, excel_data=None, temp_count=0, non_temp_count=0, total_count=0):
    """Send email with or without the Excel attachment using OAuth."""
    try:
        # Get email recipients from database
        recipients = get_email_recipients()
        
        logger.info(f"Preparing to send email to {len(recipients)} recipients")
        
        # Initialize the OAuth email manager
        email_mgr = email_manager_oauth.EmailManager(email_config, logger)
        
        # Check if OAuth is authenticated
        if not email_mgr.oauth_handler.authenticate():
            logger.error("""
            Gmail OAuth not authenticated. Please authenticate first by:
            1. Open your web browser
            2. Go to http://localhost:16000/oauth/check_gmail_auth
            3. Click 'Authorize Gmail' and follow the prompts
            4. Once authorization is complete, run this script again
            """)
            return False
        
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        if has_expired_badges:
            subject = f"Badge scaduti al {current_date}"
            body = (
                f"In allegato si trova l'elenco dei badge scaduti al {current_date}.\n\n"
                f"Totale badge temporanei: {temp_count}\n"
                f"Totale badge non temporanei: {non_temp_count}\n"
                f"Totale badge scaduti: {total_count}\n\n"
                "Questo è un messaggio automatico generato dal sistema."
            )
            
            attachments = [{
                'data': excel_data,
                'filename': f"Badge_Scaduti_{current_date.replace('/', '-')}.xlsx",
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }]
            
            logger.info("Attaching Excel report to email")
            success = email_mgr.send_email(subject, recipients, body, attachments, use_bcc=True)
        else:
            subject = f"Badge scaduti al {current_date}"
            body = (
                f"Si informa che non ci sono badge scaduti alla data del {current_date}.\n\n"
                "Questo è un messaggio automatico generato dal sistema."
            )
            
            success = email_mgr.send_email(subject, recipients, body, None, use_bcc=True)
        
        if success:
            logger.info("Email sent successfully")
            return True
        else:
            logger.error("Failed to send email")
            return False
            
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def main():
    """Main function to run the script."""
    try:
        logger.info(f"Starting expired badges check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize database
        logger.info("Initializing database connection")
        from passwords import database_config
        fredbconn.initialize_database(*database_config)
        
        # Get list of all expired badges
        expired_badges = get_expired_badges()
        
        if expired_badges:
            # Calculate counts for email
            temp_badges = []
            non_temp_badges = []
            for badge in expired_badges:
                # Check is_badge_temporaneo (position 4 in the tuple)
                is_temp = badge[4] if len(badge) > 4 else 0
                
                if is_temp:
                    temp_badges.append(badge)
                else:
                    non_temp_badges.append(badge)
            
            # Generate Excel report
            excel_data = generate_excel_report(expired_badges)
            
            # Send email with attachment
            success = send_email(True, excel_data, len(temp_badges), len(non_temp_badges), len(expired_badges))
            if success:
                logger.info(f"Process completed successfully: {len(expired_badges)} expired badge(s) reported")
            else:
                logger.error("Failed to send email with expired badges report")
                return 1
        else:
            logger.info("No expired badges found")
            
            # ----- Uncomment this if you want emails to be sent even when no expired badges are found -----

            # # Send email informing no expired badges
            # success = send_email(False)
            # if success:
            #     logger.info("Process completed successfully: No expired badges to report")
            # else:
            #     logger.error("Failed to send confirmation email")
            #     return 1

            # ----------------------------------------------------------------------------------------------
        
        return 0
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())