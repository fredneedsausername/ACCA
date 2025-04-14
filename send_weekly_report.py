# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

import os
import sys
import logging
from datetime import datetime
import traceback

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email-logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "weekly_report.log")

logging.basicConfig(
    filename=log_file,
    filemode='w',  # 'w' mode overwrites the existing file
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)   
logger = logging.getLogger("WeeklyReport")

def main():
    """Main function to generate and email the weekly report."""
    try:
        logger.info("Starting weekly report generation and email process")
        
        # Import modules from python directory
        from python import passwords
        from python import fredbconn
        from python import report_generator
        from python import email_manager
        
        # Initialize database connection
        logger.info("Initializing database connection")
        fredbconn.initialize_database(*passwords.database_config_weekly_report)
        
        # Fetch recipients from database
        logger.info("Fetching email recipients from database")
        
        @fredbconn.connected_to_database
        def fetch_email_recipients(cursor):
            """Fetch email recipients from the dedicated table."""
            cursor.execute("""
            SELECT email
            FROM email_recipients
            """)
            
            recipients = []
            for row in cursor.fetchall():
                email = row[0].strip()
                if email:
                    recipients.append(email)
            
            return recipients
        
        recipients = fetch_email_recipients()
        
        # Check if we have any recipients
        if not recipients:
            logger.error("No email recipients found in database. Report will not be sent.")
            sys.exit(1)
        
        logger.info(f"Found {len(recipients)} email recipients")
            
        # Generate the report using the weekly report function
        logger.info("Generating weekly report (badge valido only)")
        report_data = report_generator.generate_weekly_report()
        
        # Initialize the email manager
        logger.info("Initializing email manager")
        email_mgr = email_manager.EmailManager(passwords.email_config, logger)
        
        # Send the email with the report
        logger.info(f"Sending report to {len(recipients)} recipients")
        success = email_mgr.send_weekly_report(recipients, report_data)
        
        if success:
            logger.info("Weekly report process completed successfully")
        else:
            logger.error("Failed to send weekly report email")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Unhandled exception in main function: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()