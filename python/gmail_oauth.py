# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

"""Gmail OAuth 2.0 authentication module for web applications.

This module handles OAuth 2.0 authentication for Gmail in a web application context,
storing tokens in the database for persistence across application restarts.
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.utils import formatdate
from email import encoders
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the scopes for Gmail API access
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailOAuth:
    """Class to handle Gmail OAuth 2.0 authentication and email sending for web applications."""
    
    def __init__(self, credentials_file, db_connection, user_email, logger=None):
        """
        Initialize the Gmail OAuth handler.
        
        Args:
            credentials_file (str): Path to the credentials.json file from Google Cloud Console
            db_connection: Database connection function to store/retrieve tokens
            user_email (str): Email address of the sender
            logger (logging.Logger, optional): Logger instance
        """
        self.credentials_file = credentials_file
        self.db_connection = db_connection
        self.user_email = user_email
        
        # Set up logging
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize credentials
        self.creds = None
        self.service = None
    
    def get_authorization_url(self, redirect_uri):
        """
        Get the authorization URL for the OAuth flow.
        
        Args:
            redirect_uri (str): The URI to redirect to after authorization
            
        Returns:
            tuple: (authorization_url, state)
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force to generate refresh token
            )
            
            return authorization_url, state, flow
        except Exception as e:
            self.logger.error(f"Error generating authorization URL: {str(e)}")
            raise
    
    def exchange_code(self, code, flow):
        """
        Exchange authorization code for tokens.
        
        Args:
            code (str): The authorization code from Google
            flow (Flow): The OAuth flow object used to create the authorization URL
            
        Returns:
            dict: The token data to be stored
        """
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Format token data for storage
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            
            # Store token in database
            self._store_token(token_data)
            
            self.creds = creds
            return token_data
        except Exception as e:
            self.logger.error(f"Error exchanging code for token: {str(e)}")
            raise
    
    def _store_token(self, token_data):
        """
        Store token data in the database.
        
        Args:
            token_data (dict): Token data to store
        """
        try:
            @self.db_connection
            def store_token(cursor):
                # Check if token entry exists
                cursor.execute("""
                SELECT id FROM oauth_tokens 
                WHERE email = %s
                """, (self.user_email,))
                
                token_exists = cursor.fetchone()
                
                if token_exists:
                    # Update existing token
                    cursor.execute("""
                    UPDATE oauth_tokens
                    SET 
                        token = %s,
                        refresh_token = %s,
                        token_uri = %s,
                        client_id = %s,
                        client_secret = %s,
                        scopes = %s,
                        expiry = %s,
                        updated_at = %s
                    WHERE email = %s
                    """, (
                        token_data['token'],
                        token_data['refresh_token'],
                        token_data['token_uri'],
                        token_data['client_id'],
                        token_data['client_secret'],
                        ','.join(token_data['scopes']),
                        token_data['expiry'],
                        datetime.now().isoformat(),
                        self.user_email
                    ))
                else:
                    # Insert new token
                    cursor.execute("""
                    INSERT INTO oauth_tokens
                    (email, token, refresh_token, token_uri, client_id, client_secret, scopes, expiry, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.user_email,
                        token_data['token'],
                        token_data['refresh_token'],
                        token_data['token_uri'],
                        token_data['client_id'],
                        token_data['client_secret'],
                        ','.join(token_data['scopes']),
                        token_data['expiry'],
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
            
            store_token()
            self.logger.info(f"Token stored successfully for {self.user_email}")
        except Exception as e:
            self.logger.error(f"Error storing token: {str(e)}")
            raise
    
    def _load_token(self):
        """
        Load token data from the database.
        
        Returns:
            dict: Token data or None if not found
        """
        try:
            @self.db_connection
            def load_token(cursor):
                cursor.execute("""
                SELECT 
                    token, refresh_token, token_uri, client_id, 
                    client_secret, scopes, expiry
                FROM oauth_tokens
                WHERE email = %s
                """, (self.user_email,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                token_data = {
                    'token': result[0],
                    'refresh_token': result[1],
                    'token_uri': result[2],
                    'client_id': result[3],
                    'client_secret': result[4],
                    'scopes': result[5].split(','),
                    'expiry': result[6]
                }
                
                return token_data
            
            return load_token()
        except Exception as e:
            self.logger.error(f"Error loading token: {str(e)}")
            return None
    
    def authenticate(self):
        """
        Authenticate using stored tokens.
        
        Returns:
            bool: True if authentication was successful, False if needs authorization
        """
        try:
            # Load token from database
            token_data = self._load_token()
            
            if not token_data:
                self.logger.info("No token found in database")
                return False
            
            # Create credentials from token data
            try:
                expiry = None
                if token_data['expiry']:
                    try:
                        expiry = datetime.fromisoformat(token_data['expiry'])
                    except ValueError:
                        # Handle older ISO format
                        expiry = datetime.strptime(token_data['expiry'], "%Y-%m-%dT%H:%M:%S.%f")
            except Exception as e:
                self.logger.warning(f"Error parsing expiry: {str(e)}")
                expiry = None
            
            self.creds = Credentials(
                token=token_data['token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=token_data['scopes'],
                expiry=expiry
            )
            
            # Refresh token if expired
            if not self.creds.valid:
                if self.creds.expired and self.creds.refresh_token:
                    self.logger.info("Refreshing expired token")
                    self.creds.refresh(Request())
                    
                    # Update token in database
                    token_data = {
                        'token': self.creds.token,
                        'refresh_token': self.creds.refresh_token,
                        'token_uri': self.creds.token_uri,
                        'client_id': self.creds.client_id,
                        'client_secret': self.creds.client_secret,
                        'scopes': self.creds.scopes,
                        'expiry': self.creds.expiry.isoformat() if self.creds.expiry else None
                    }
                    self._store_token(token_data)
                else:
                    self.logger.warning("Token is invalid and cannot be refreshed")
                    return False
            
            # Create Gmail API service
            self.service = build('gmail', 'v1', credentials=self.creds)
            self.logger.info("Gmail OAuth authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return False
    
    def create_message(self, to, subject, body, attachments=None, use_bcc=False):
        """
        Create a message for the Gmail API.
        
        Args:
            to (list): Recipients' email addresses
            subject (str): Email subject
            body (str): Email body text
            attachments (list, optional): List of dict with format:
                [{'data': bytes_or_file, 'filename': 'name.ext', 'mimetype': 'type/subtype'}]
            use_bcc (bool): Whether to use BCC instead of TO field
            
        Returns:
            dict: A message object for the Gmail API
        """
        msg = MIMEMultipart()
        msg['From'] = self.user_email
        
        if use_bcc:
            # Set the TO field to the sender (common practice for BCC emails)
            msg['To'] = self.user_email
            # Add BCC recipients
            if to:
                msg['Bcc'] = ", ".join(to)
        else:
            # All recipients can see each other
            msg['To'] = ", ".join(to)
        
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject
        
        # Attach text body
        msg.attach(MIMEText(body))
        
        # Attach files if present
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
        
        # Convert to base64 format for Gmail API
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return {'raw': raw_message}
    
    def send_message(self, message):
        """
        Send a message via the Gmail API.
        
        Args:
            message (dict): Message created by create_message()
            
        Returns:
            dict: The sent message response from the API
        """
        try:
            if not self.service:
                if not self.authenticate():
                    raise Exception("Authentication failed. Need to complete OAuth flow.")
            
            # Attempt to send the message
            sent_message = self.service.users().messages().send(
                userId='me', body=message).execute()
            self.logger.info(f"Message sent successfully. Message ID: {sent_message['id']}")
            return sent_message
            
        except HttpError as error:
            if error.resp.status == 401:
                # Token might be invalid - try to refresh
                self.logger.warning("Authentication error - attempting to refresh token")
                self.creds = None
                if self.authenticate():
                    # Retry sending after re-authentication
                    return self.send_message(message)
                else:
                    raise Exception("Authentication failed. Need to complete OAuth flow.")
            
            self.logger.error(f"Error sending message: {error}")
            raise
    
    def send_email(self, subject, recipients, body, attachments=None, use_bcc=True):
        """
        High-level method to create and send an email.
        
        Args:
            subject (str): Email subject line
            recipients (list): List of recipient email addresses
            body (str): Email body content
            attachments (list, optional): List of dicts with format:
                [{'data': bytes_or_file, 'filename': 'name.ext', 'mimetype': 'type/subtype'}]
            use_bcc (bool): Whether to use BCC for recipients
                
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Create the message
            message = self.create_message(
                recipients, subject, body, attachments, use_bcc)
            
            # Send the message
            self.send_message(message)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
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