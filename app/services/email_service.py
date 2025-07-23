"""
Zentraler Email Service für Scandy
Alle E-Mail-Funktionalitäten an einem Ort
"""
from typing import Dict, Any, List, Optional
from flask import current_app, render_template_string
from app.utils.email_utils import send_email
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Zentraler Service für alle E-Mail-Operationen"""
    
    @staticmethod
    def send_password_reset_email(user_email: str, reset_token: str, username: str) -> bool:
        """
        Sendet E-Mail für Passwort-Reset
        
        Args:
            user_email: E-Mail-Adresse des Benutzers
            reset_token: Reset-Token
            username: Benutzername
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            subject = "Scandy - Passwort zurücksetzen"
            template = """
            <h2>Passwort zurücksetzen</h2>
            <p>Hallo {{ username }},</p>
            <p>Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.</p>
            <p>Falls Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.</p>
            <p>Der Link ist 24 Stunden gültig.</p>
            <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
            """
            
            html_content = render_template_string(template, 
                                                username=username)
            
            return send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Fehler beim Senden der Passwort-Reset-E-Mail: {str(e)}")
            return False
    
    @staticmethod
    def send_new_user_email(user_email: str, username: str, password: str, firstname: str) -> bool:
        """
        Sendet E-Mail mit Zugangsdaten für neue Benutzer
        
        Args:
            user_email: E-Mail-Adresse des Benutzers
            username: Benutzername
            password: Generiertes Passwort
            firstname: Vorname des Benutzers
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            login_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/auth/login"
            
            subject = "Scandy - Ihre Zugangsdaten"
            template = """
            <h2>Willkommen bei Scandy!</h2>
            <p>Hallo {{ firstname }},</p>
            <p>Ihr Benutzerkonto wurde erfolgreich erstellt.</p>
            <p><strong>Ihre Zugangsdaten:</strong></p>
            <ul>
                <li><strong>Benutzername:</strong> {{ username }}</li>
                <li><strong>Passwort:</strong> {{ password }}</li>
            </ul>
            <p>Bitte ändern Sie Ihr Passwort nach der ersten Anmeldung.</p>
            <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
            """
            
            html_content = render_template_string(template, 
                                                username=username, 
                                                password=password,
                                                firstname=firstname,
                                                login_url=login_url)
            
            return send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Fehler beim Senden der neuen Benutzer-E-Mail: {str(e)}")
            return False
    
    @staticmethod
    def send_notification_email(user_email: str, subject: str, message: str, notification_type: str = "info") -> bool:
        """
        Sendet allgemeine Benachrichtigungs-E-Mail
        
        Args:
            user_email: E-Mail-Adresse des Empfängers
            subject: Betreff der E-Mail
            message: Nachricht
            notification_type: Typ der Benachrichtigung (info, warning, error)
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            # CSS-Styles basierend auf Typ
            styles = {
                "info": "background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;",
                "warning": "background-color: #fff3cd; border-color: #ffeaa7; color: #856404;",
                "error": "background-color: #f8d7da; border-color: #f5c6cb; color: #721c24;"
            }
            
            style = styles.get(notification_type, styles["info"])
            
            template = f"""
            <div style="padding: 15px; border: 1px solid; border-radius: 5px; {style}">
                <h3>{{ subject }}</h3>
                <p>{{ message }}</p>
            </div>
            <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
            """
            
            html_content = render_template_string(template, subject=subject, message=message)
            
            return send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Fehler beim Senden der Benachrichtigungs-E-Mail: {str(e)}")
            return False
    
    @staticmethod
    def send_ticket_notification_email(user_email: str, ticket_data: Dict[str, Any], action: str) -> bool:
        """
        Sendet E-Mail-Benachrichtigung für Ticket-Aktionen
        
        Args:
            user_email: E-Mail-Adresse des Empfängers
            ticket_data: Ticket-Daten
            action: Aktion (created, updated, assigned, closed)
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            action_messages = {
                "created": "Ein neues Ticket wurde erstellt",
                "updated": "Ein Ticket wurde aktualisiert",
                "assigned": "Ein Ticket wurde Ihnen zugewiesen",
                "closed": "Ein Ticket wurde geschlossen"
            }
            
            subject = f"Scandy - Ticket {action_messages.get(action, 'Benachrichtigung')}"
            
            template = """
            <h2>{{ action_message }}</h2>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3>Ticket-Details:</h3>
                <p><strong>Titel:</strong> {{ ticket.title }}</p>
                <p><strong>Status:</strong> {{ ticket.status }}</p>
                <p><strong>Priorität:</strong> {{ ticket.priority }}</p>
                {% if ticket.description %}
                <p><strong>Beschreibung:</strong> {{ ticket.description }}</p>
                {% endif %}
                {% if ticket.due_date %}
                <p><strong>Fälligkeitsdatum:</strong> {{ ticket.due_date }}</p>
                {% endif %}
            </div>
            <p>Sie können das Ticket in Scandy einsehen und bearbeiten.</p>
            <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
            """
            
            html_content = render_template_string(template, 
                                                action_message=action_messages.get(action, "Benachrichtigung"),
                                                ticket=ticket_data)
            
            return send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Fehler beim Senden der Ticket-Benachrichtigung: {str(e)}")
            return False
    
    @staticmethod
    def send_lending_notification_email(user_email: str, lending_data: Dict[str, Any], action: str) -> bool:
        """
        Sendet E-Mail-Benachrichtigung für Ausleihe-Aktionen
        
        Args:
            user_email: E-Mail-Adresse des Empfängers
            lending_data: Ausleihe-Daten
            action: Aktion (lent, returned, overdue)
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            action_messages = {
                "lent": "Ein Werkzeug wurde ausgeliehen",
                "returned": "Ein Werkzeug wurde zurückgegeben",
                "overdue": "Ein Werkzeug ist überfällig"
            }
            
            subject = f"Scandy - {action_messages.get(action, 'Ausleihe-Benachrichtigung')}"
            
            template = """
            <h2>{{ action_message }}</h2>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3>Ausleihe-Details:</h3>
                <p><strong>Werkzeug:</strong> {{ lending.tool_name }}</p>
                <p><strong>Mitarbeiter:</strong> {{ lending.worker_name }}</p>
                <p><strong>Ausgeliehen am:</strong> {{ lending.lent_at }}</p>
                {% if lending.returned_at %}
                <p><strong>Zurückgegeben am:</strong> {{ lending.returned_at }}</p>
                {% endif %}
            </div>
            <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
            """
            
            html_content = render_template_string(template, 
                                                action_message=action_messages.get(action, "Ausleihe-Benachrichtigung"),
                                                lending=lending_data)
            
            return send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Fehler beim Senden der Ausleihe-Benachrichtigung: {str(e)}")
            return False 