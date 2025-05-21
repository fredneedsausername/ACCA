"""
OAuth routes for Gmail authentication.
This module provides the Flask routes needed for OAuth authentication with Gmail.
"""

import os
from flask import Blueprint, redirect, request, url_for, session, flash, render_template

import email_manager_oauth

oauth_bp = Blueprint('oauth', __name__)

# Store flow objects temporarily during authentication
active_flows = {}

def init_oauth_routes(app, email_config):
    """
    Initialize the OAuth routes with the application and configuration.
    
    Args:
        app: Flask application
        email_config: Email configuration dictionary
    """
    email_mgr = email_manager_oauth.EmailManager(email_config)
    
    @oauth_bp.route('/authorize_gmail')
    def authorize_gmail():
        """Start the Gmail OAuth authorization flow."""
        if 'user' not in session:
            flash("Devi effettuare l'accesso per autorizzare Gmail", "error")
            return redirect(url_for('login'))
        
        # Create the redirect URI
        redirect_uri = url_for('oauth.oauth_callback', _external=True)
        
        # Get the authorization URL
        auth_url, state, flow = email_mgr.get_authorization_url(redirect_uri)
        
        if not auth_url:
            flash("Errore durante la generazione dell'URL di autorizzazione", "error")
            return redirect(url_for('index'))
        
        # Store the flow object for later
        session['oauth_state'] = state
        active_flows[state] = flow
        
        # Redirect to the authorization URL
        return redirect(auth_url)
    
    @oauth_bp.route('/oauth2callback')
    def oauth_callback():
        """Handle the OAuth callback from Google."""
        error = request.args.get('error', '')
        if error:
            flash(f"Errore di autorizzazione: {error}", "error")
            return redirect(url_for('index'))
        
        # Get the code and state from the request
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify state matches what we stored
        if state != session.get('oauth_state'):
            flash("Errore di validazione dello stato OAuth", "error")
            return redirect(url_for('index'))
        
        # Get the flow object we stored earlier
        flow = active_flows.get(state)
        if not flow:
            flash("Sessione di autorizzazione scaduta o invalida", "error")
            return redirect(url_for('index'))
        
        # Exchange the code for tokens
        success = email_mgr.handle_oauth_callback(code, flow)
        
        if success:
            flash("Gmail autorizzato con successo! Ora puoi inviare email.", "success")
        else:
            flash("Errore durante l'autorizzazione di Gmail", "error")
        
        # Clean up session and active flows
        if state in active_flows:
            del active_flows[state]
        if 'oauth_state' in session:
            del session['oauth_state']
        
        return redirect(url_for('index'))
    
    @oauth_bp.route('/check_gmail_auth')
    def check_gmail_auth():
        """Check if Gmail is authorized and display status page."""
        if 'user' not in session:
            flash("Devi effettuare l'accesso per verificare lo stato di autorizzazione", "error")
            return redirect(url_for('login'))
        
        # Create a new EmailManager instance
        email_mgr_check = email_manager_oauth.EmailManager(email_config)
        
        # Check if authenticated
        is_authenticated = email_mgr_check.oauth_handler.authenticate()
        
        return render_template('gmail_auth_status.html', 
                              is_authenticated=is_authenticated,
                              email=email_config['sender_email'])
    
    # Register the blueprint with the app
    app.register_blueprint(oauth_bp, url_prefix='/oauth')