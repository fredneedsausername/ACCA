# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

import os
import logging
from datetime import datetime
import traceback

# Import the OAuth module
import gmail_oauth
import fredbconn

class EmailManager:
    """Class to manage all email operations using Gmail OAuth 2.0."""
    
    def __init__(self, config, logger=None):
        """
        Initialize the email manager with configuration.
        
        Args:
            config (dict): Email configuration containing OAuth details
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
        
        # Initialize the OAuth handler
        self.oauth_handler = gmail_oauth.GmailOAuth(
            credentials_file=self.config['credentials_file'],
            db_connection=fredbconn.connected_to_database,
            user_email=self.config['sender_email'],
            logger=self.logger
        )
        
        # Ensure OAuth token table exists
        self._ensure_oauth_table_exists()
    
    def _validate_config(self):
        """Validate that all required configuration parameters are present."""
        required_params = ['credentials_file', 'sender_email']
        
        for param in required_params:
            if param not in self.config or not self.config[param]:
                self.logger.error(f"Missing required email configuration parameter: {param}")
                raise ValueError(f"Missing required email configuration parameter: {param}")
    
    def _ensure_oauth_table_exists(self):
        """Ensure that the OAuth tokens table exists in the database."""
        try:
            @fredbconn.connected_to_database
            def create_oauth_table(cursor):
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_uri VARCHAR(255) NOT NULL,
                    client_id VARCHAR(255) NOT NULL,
                    client_secret VARCHAR(255) NOT NULL,
                    scopes TEXT NOT NULL,
                    expiry VARCHAR(100),
                    created_at VARCHAR(100) NOT NULL,
                    updated_at VARCHAR(100) NOT NULL
                )
                """)
            
            create_oauth_table()
            self.logger.info("OAuth tokens table initialized")
        except Exception as e:
            self.logger.error(f"Error ensuring OAuth table exists: {str(e)}")
            raise
    
    def send_email(self, subject, recipients, body, attachments=None, use_bcc=True):
        """
        Send an email with optional attachments using Gmail OAuth 2.0.
        
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
            # Try to authenticate
            authenticated = self.oauth_handler.authenticate()
            
            if not authenticated:
                self.logger.warning("Authentication failed - OAuth flow may need to be completed")
                # Script is running - can't do OAuth flow here
                # Will need to be done via web interface first
                return False
            
            # Send the email using the OAuth handler
            success = self.oauth_handler.send_email(
                subject, recipients, body, attachments, use_bcc)
            
            if success:
                self.logger.info(f"Email sent successfully to {len(recipients)} recipients using {'BCC' if use_bcc else 'TO'}")
            else:
                self.logger.error("Failed to send email through OAuth handler")
            
            return success
            
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
        try:
            # Try to authenticate
            authenticated = self.oauth_handler.authenticate()
            
            if not authenticated:
                self.logger.warning("Authentication failed - OAuth flow may need to be completed")
                # Script is running - can't do OAuth flow here
                # Will need to be done via web interface first
                return False
            
            # Use the OAuth handler's method for sending weekly reports
            success = self.oauth_handler.send_weekly_report(recipients, report_data)
            
            if success:
                self.logger.info(f"Weekly report sent successfully to {len(recipients)} recipients")
            else:
                self.logger.error("Failed to send weekly report")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending weekly report: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def get_authorization_url(self, redirect_uri):
        """
        Get the authorization URL for initiating OAuth flow.
        
        Args:
            redirect_uri (str): The URI to redirect to after authorization
            
        Returns:
            tuple: (authorization_url, state, flow) or (None, None, None) on error
        """
        try:
            return self.oauth_handler.get_authorization_url(redirect_uri)
        except Exception as e:
            self.logger.error(f"Error getting authorization URL: {str(e)}")
            return None, None, None
    
    def handle_oauth_callback(self, code, flow):
        """
        Handle the OAuth callback and exchange code for tokens.
        
        Args:
            code (str): The authorization code from Google
            flow: The flow object from get_authorization_url
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.oauth_handler.exchange_code(code, flow)
            return True
        except Exception as e:
            self.logger.error(f"Error handling OAuth callback: {str(e)}")
            return False