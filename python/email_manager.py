# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from datetime import datetime
import traceback

class EmailManager:
    """Class to manage all email operations."""
    
    def __init__(self, config, logger=None):
        """
        Initialize the email manager with configuration.
        
        Args:
            config (dict): Email configuration containing SMTP details
            logger (logging.Logger, optional): Logger instance for operations
        """
        self.config = config
        
        # Setup logging if not provided
        if logger is None:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "email-logs")
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"email_log_{datetime.now().strftime('%Y-%m-%d')}.log")
            
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )
            self.logger = logging.getLogger("EmailManager")
        else:
            self.logger = logger
            
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required configuration parameters are present."""
        required_params = ['smtp_server', 'smtp_port', 'smtp_username', 
                          'smtp_password', 'sender_email']
        
        for param in required_params:
            if param not in self.config or not self.config[param]:
                self.logger.error(f"Missing required email configuration parameter: {param}")
                raise ValueError(f"Missing required email configuration parameter: {param}")
    
    def send_email(self, subject, recipients, body, attachments=None, use_bcc=True):
        """
        Send an email with optional attachments.
        
        Args:
            subject (str): Email subject line
            recipients (list): List of recipient email addresses
            body (str): Email body content
            attachments (list, optional): List of dictionaries with format:
                [{'data': bytes_or_file, 'filename': 'name.ext', 'mimetype': 'type/subtype'}]
            use_bcc (bool): Whether to use BCC for recipients instead of TO
                
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = self.config['sender_email']
            
            if use_bcc:
                # Set the TO field to the sender (or another appropriate address)
                # This will be shown in recipient's email client
                msg['To'] = self.config['sender_email']
                # Add recipients as BCC so they can't see each other
                if recipients:
                    msg['Bcc'] = ", ".join(recipients)
            else:
                # Traditional approach - all recipients can see each other
                msg['To'] = ", ".join(recipients)
            
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = subject
            
            # Attach text body
            msg.attach(MIMEText(body))
            
            # Attach any files
            if attachments:
                for attachment in attachments:
                    attachment_part = MIMEBase(*attachment.get('mimetype', 'application/octet-stream').split('/'))
                    
                    # Get the data
                    data = attachment['data']
                    # If data is a file-like object, read it
                    if hasattr(data, 'read'):
                        content = data.read()
                    else:
                        content = data
                        
                    attachment_part.set_payload(content)
                    encoders.encode_base64(attachment_part)
                    attachment_part.add_header(
                        'Content-Disposition', 
                        f'attachment; filename="{attachment["filename"]}"'
                    )
                    msg.attach(attachment_part)
            
            # Connect to server and send
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()  # Secure the connection
                server.login(self.config['smtp_username'], self.config['smtp_password'])
                
                # When sending via BCC, we need to ensure all recipients are included
                # in the sendmail call, even though they're not in the TO field
                server.send_message(msg)
                
            self.logger.info(f"Email sent successfully to {len(recipients)} recipients using {'BCC' if use_bcc else 'TO'}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def send_weekly_report(self, recipients, report_data):
        """
        Send the weekly report email with recipients in BCC.
        
        Args:
            recipients (list): List of recipient email addresses
            report_data (BytesIO): Excel report data as a BytesIO object
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        today = datetime.now().strftime('%d/%m/%Y')
        subject = f"Report Settimanale Accesso Cantieri - {today}"
        
        body = f"""
Buongiorno,

In allegato il report settimanale aggiornato al {today}.

Questo messaggio è stato generato automaticamente, si prega di non rispondere.

Cordiali saluti,
Sistema Gestionale Accesso Cantieri
        """
        
        attachments = [{
            'data': report_data,
            'filename': f"report_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }]
        
        # Always use BCC for the weekly report
        return self.send_email(subject, recipients, body, attachments, use_bcc=True)