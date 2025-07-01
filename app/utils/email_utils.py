from flask_mail import Mail, Message
from flask import current_app
import os
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import os
import hashlib

mail = None
logger = logging.getLogger(__name__)

def _get_encryption_key():
    """Generiert einen einfachen Verschlüsselungsschlüssel für E-Mail-Passwörter"""
    # Verwende SECRET_KEY als Basis für den Verschlüsselungsschlüssel
    secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
    # Erstelle einen 32-Byte-Schlüssel aus dem Secret Key
    key = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key)

def _encrypt_password(password):
    """Verschlüsselt ein E-Mail-Passwort mit XOR und Base64"""
    if not password:
        return None
    try:
        key = _get_encryption_key()
        # Einfache XOR-Verschlüsselung mit dem Schlüssel
        key_bytes = base64.urlsafe_b64decode(key)
        password_bytes = password.encode('utf-8')
        
        # XOR-Verschlüsselung
        encrypted = bytearray()
        for i, byte in enumerate(password_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return base64.urlsafe_b64encode(bytes(encrypted)).decode()
    except Exception as e:
        logger.error(f"Fehler beim Verschlüsseln des Passworts: {e}")
        return None

def _decrypt_password(encrypted_password):
    """Entschlüsselt ein E-Mail-Passwort"""
    if not encrypted_password:
        return None
    try:
        key = _get_encryption_key()
        key_bytes = base64.urlsafe_b64decode(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
        
        # XOR-Entschlüsselung
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return bytes(decrypted).decode('utf-8')
    except Exception as e:
        logger.error(f"Fehler beim Entschlüsseln des Passworts: {e}")
        return None

def get_email_config():
    """Lädt die E-Mail-Konfiguration aus der Datenbank"""
    try:
        from app.models.mongodb_database import MongoDBDatabase
        mongodb = MongoDBDatabase()
        
        config = {
            'mail_server': 'smtp.gmail.com',
            'mail_port': 587,
            'mail_use_tls': True,
            'mail_username': '',
            'mail_password': '',
            'test_email': '',
            'enabled': False,
            'use_auth': True
        }
        
        # Lade Konfiguration aus der Datenbank
        db_config = mongodb.find_one('email_config', {'_id': 'email_config'})
        if db_config:
            # Überschreibe Standard-Konfiguration mit Datenbank-Werten
            for key, value in db_config.items():
                if key != '_id':  # Überspringe MongoDB _id
                    if key == 'mail_password' and value:
                        # Passwort entschlüsseln, falls es verschlüsselt ist
                        if not value.startswith('$2b$'):  # Nicht gehasht
                            config[key] = _decrypt_password(value)
                        else:
                            config[key] = value  # Bereits gehasht (alte Daten)
                    else:
                        config[key] = value
        
        # Konvertiere Typen
        config['mail_port'] = int(config['mail_port'])
        config['mail_use_tls'] = config['mail_use_tls'] == 'true' if isinstance(config['mail_use_tls'], str) else config['mail_use_tls']
        config['enabled'] = config['enabled'] == 'true' if isinstance(config['enabled'], str) else config['enabled']
        
        return config
    except Exception as e:
        logger.error(f"Fehler beim Laden der E-Mail-Konfiguration: {e}")
        return None

def save_email_config(config_data):
    """Speichert die E-Mail-Konfiguration in der Datenbank"""
    try:
        from app.models.mongodb_database import MongoDBDatabase
        
        mongodb = MongoDBDatabase()
        
        # Absender-E-Mail automatisch aus SMTP-Anmeldedaten setzen
        config_data['mail_default_sender'] = config_data['mail_username']
        
        # Passwort verschlüsseln, falls vorhanden
        if 'mail_password' in config_data and config_data['mail_password']:
            # Prüfe ob das Passwort bereits verschlüsselt ist
            if not config_data['mail_password'].startswith('$2b$') and not config_data['mail_password'].startswith('gAAAAA'):
                encrypted_password = _encrypt_password(config_data['mail_password'])
                if encrypted_password:
                    config_data['mail_password'] = encrypted_password
                else:
                    logger.error("Fehler beim Verschlüsseln des E-Mail-Passworts")
                    return False
        
        # Konfiguration speichern oder aktualisieren
        # Passwort wird jetzt verschlüsselt gespeichert
        mongodb.update_one(
            'email_config',
            {'_id': 'email_config'},
            config_data,
            upsert=True
        )
        
        # E-Mail-System wird beim nächsten Neustart neu initialisiert
        logger.info("E-Mail-Konfiguration gespeichert. Neustart erforderlich für Aktivierung.")
        
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der E-Mail-Konfiguration: {e}")
        return False

def test_email_config(config_data):
    """Testet die E-Mail-Konfiguration"""
    try:
        from flask import Flask
        from flask_mail import Mail, Message
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Erstelle temporäre Flask-App für Test
        test_app = Flask(__name__)
        test_app.config['MAIL_SERVER'] = config_data['mail_server']
        test_app.config['MAIL_PORT'] = int(config_data['mail_port'])
        test_app.config['MAIL_USE_TLS'] = config_data['mail_use_tls']
        test_app.config['MAIL_USE_SSL'] = not config_data['mail_use_tls'] and int(config_data['mail_port']) == 465
        test_app.config['MAIL_USERNAME'] = config_data['mail_username']
        test_app.config['MAIL_PASSWORD'] = config_data['mail_password']
        test_app.config['MAIL_DEFAULT_SENDER'] = config_data['mail_username']
        
        # Zuerst SMTP-Verbindung testen
        try:
            if test_app.config['MAIL_USE_SSL']:
                server = smtplib.SMTP_SSL(test_app.config['MAIL_SERVER'], test_app.config['MAIL_PORT'])
            else:
                server = smtplib.SMTP(test_app.config['MAIL_SERVER'], test_app.config['MAIL_PORT'])
            
            # Prüfe ob STARTTLS verfügbar ist - verbesserte Erkennung
            capabilities_before = server.ehlo()
            starttls_available = False
            
            # Methode 1: Prüfe esmtp_features (am zuverlässigsten)
            if hasattr(server, 'esmtp_features') and server.esmtp_features:
                starttls_available = 'starttls' in server.esmtp_features
            
            # Methode 2: Prüfe in den Capabilities-Strings (Fallback)
            if not starttls_available and capabilities_before and len(capabilities_before) > 1:
                for cap in capabilities_before[1]:
                    if isinstance(cap, bytes):
                        try:
                            cap_str = cap.decode('utf-8', errors='ignore')
                        except UnicodeDecodeError:
                            cap_str = cap.decode('latin-1', errors='ignore')
                    else:
                        cap_str = str(cap)
                    
                    if 'starttls' in cap_str.lower():
                        starttls_available = True
                        break
            
            # Methode 3: Für bekannte Server - versuche STARTTLS auch wenn nicht erkannt
            known_servers = ['smtp.gmail.com', 'smtp.office365.com', 'smtp-mail.outlook.com']
            if not starttls_available and config_data['mail_server'] in known_servers and int(config_data['mail_port']) == 587:
                starttls_available = True
            
            # TLS aktivieren falls konfiguriert und verfügbar
            if test_app.config['MAIL_USE_TLS'] and starttls_available:
                server.starttls()
                # Neue EHLO nach TLS
                capabilities_after = server.ehlo()
            else:
                capabilities_after = capabilities_before
            
            # Prüfe ob AUTH unterstützt wird (nach TLS, also nach dem zweiten EHLO!)
            auth_supported = False
            
            # Methode 1: Prüfe esmtp_features NACH TLS
            if hasattr(server, 'esmtp_features') and server.esmtp_features:
                auth_supported = 'auth' in server.esmtp_features
            
            # Methode 2: Fallback - Prüfe in den Capabilities-Strings NACH TLS
            if not auth_supported and capabilities_after and len(capabilities_after) > 1:
                for cap in capabilities_after[1]:
                    if isinstance(cap, bytes):
                        try:
                            cap_str = cap.decode('utf-8', errors='ignore')
                        except UnicodeDecodeError:
                            cap_str = cap.decode('latin-1', errors='ignore')
                    else:
                        cap_str = str(cap)
                    
                    if 'auth' in cap_str.lower():
                        auth_supported = True
                        break
            
            # Methode 3: Konvertiere ASCII-Codes zu String und prüfe AUTH NACH TLS
            if not auth_supported and capabilities_after and len(capabilities_after) > 1:
                all_capabilities = []
                for cap in capabilities_after[1]:
                    if isinstance(cap, bytes):
                        try:
                            cap_str = cap.decode('utf-8', errors='ignore')
                        except UnicodeDecodeError:
                            cap_str = cap.decode('latin-1', errors='ignore')
                    else:
                        cap_str = str(cap)
                    all_capabilities.append(cap_str)
                combined_capabilities = ' '.join(all_capabilities)
                if 'auth' in combined_capabilities.lower():
                    auth_supported = True
            
            # Methode 4: Für bekannte Server - AUTH wird unterstützt
            known_servers = ['smtp.gmail.com', 'smtp.office365.com', 'smtp-mail.outlook.com']
            if not auth_supported and config_data['mail_server'] in known_servers and starttls_available:
                auth_supported = True
            
            # Authentifizierung nur testen, wenn unterstützt
            if auth_supported:
                if config_data['mail_username'] and config_data['mail_password']:
                    server.login(config_data['mail_username'], config_data['mail_password'])
                else:
                    server.quit()
                    return False, "Authentifizierung erforderlich, aber keine Anmeldedaten angegeben."
            else:
                # Server ohne Authentifizierung - verwende nur Absender-E-Mail
                if not config_data.get('mail_username'):
                    server.quit()
                    return False, "Für Server ohne Authentifizierung ist eine Absender-E-Mail-Adresse erforderlich."
                logger.info(f"SMTP-Server {config_data['mail_server']} verwendet ohne Authentifizierung")
            
            server.quit()
            
        except smtplib.SMTPAuthenticationError as e:
            return False, f"Authentifizierung fehlgeschlagen: {str(e)}"
        except smtplib.SMTPConnectError as e:
            return False, f"Verbindung zum SMTP-Server fehlgeschlagen: {str(e)}"
        except smtplib.SMTPException as e:
            return False, f"SMTP-Fehler: {str(e)}"
        except Exception as e:
            return False, f"Verbindungsfehler: {str(e)}"
        
        # Wenn SMTP-Test erfolgreich, versende Test-E-Mail
        test_mail = Mail(test_app)
        
        # Test-E-Mail-Adresse verwenden, falls vorhanden
        test_recipient = config_data.get('test_email', config_data['mail_username'])
        
        with test_app.app_context():
            msg = Message(
                'Scandy E-Mail-Test',
                recipients=[test_recipient],
                body='Dies ist eine Test-E-Mail von Scandy. Die E-Mail-Konfiguration funktioniert korrekt.'
            )
            test_mail.send(msg)
        
        return True, f"E-Mail-Test erfolgreich an {test_recipient} gesendet"
        
    except Exception as e:
        error_msg = str(e)
        if "SMTP AUTH extension not supported" in error_msg:
            return False, "SMTP-Server unterstützt keine Authentifizierung. Prüfen Sie die Server-Einstellungen oder verwenden Sie einen anderen Port."
        elif "Authentication failed" in error_msg:
            return False, "Authentifizierung fehlgeschlagen. Prüfen Sie Benutzername und Passwort."
        elif "Connection refused" in error_msg:
            return False, "Verbindung zum SMTP-Server verweigert. Prüfen Sie Server-Adresse und Port."
        elif "timeout" in error_msg.lower():
            return False, "Verbindungstimeout. Prüfen Sie Ihre Internetverbindung und Firewall-Einstellungen."
        else:
            return False, f"E-Mail-Test fehlgeschlagen: {error_msg}"

def init_mail(app):
    global mail
    # Lade Konfiguration aus der Datenbank
    config = get_email_config()
    
    if config and config['enabled']:
        # Verwende Datenbank-Konfiguration
        app.config['MAIL_SERVER'] = config['mail_server']
        app.config['MAIL_PORT'] = config['mail_port']
        app.config['MAIL_USE_TLS'] = config['mail_use_tls']
        app.config['MAIL_USE_SSL'] = not config['mail_use_tls'] and int(config['mail_port']) == 465
        
        # Prüfe ob Server Authentifizierung unterstützt
        # Verwende use_auth Einstellung, falls vorhanden, sonst prüfe Server-Capabilities
        if 'use_auth' in config:
            auth_required = config['use_auth']
        else:
            auth_required = _check_auth_required(config['mail_server'], config['mail_port'], config['mail_use_tls'])
        
        if auth_required:
            # Server benötigt Authentifizierung
            if not config['mail_username'] or not config['mail_password']:
                app.logger.error("E-Mail-Server benötigt Authentifizierung, aber keine Anmeldedaten angegeben")
                mail = None
                return
            
            app.config['MAIL_USERNAME'] = config['mail_username']
            app.config['MAIL_PASSWORD'] = config['mail_password']
            app.config['MAIL_DEFAULT_SENDER'] = config['mail_username']  # Absender = SMTP-Username
        else:
            # Server ohne Authentifizierung
            if not config.get('mail_username'):
                app.logger.error("Für Server ohne Authentifizierung ist eine Absender-E-Mail-Adresse erforderlich")
                mail = None
                return
                
            app.config['MAIL_USERNAME'] = config['mail_username']  # Wird als Absender verwendet
            app.config['MAIL_PASSWORD'] = ''  # Kein Passwort für Server ohne Auth
            app.config['MAIL_DEFAULT_SENDER'] = config['mail_username']
        
        # Zusätzliche Flask-Mail Konfiguration für bessere Kompatibilität
        app.config['MAIL_ASCII_ATTACHMENTS'] = False
        app.config['MAIL_SUPPRESS_SEND'] = False
        
        try:
            mail = Mail(app)
            app.logger.info("E-Mail-System mit Datenbank-Konfiguration initialisiert")
            app.logger.info(f"SMTP-Server: {config['mail_server']}:{config['mail_port']}")
            app.logger.info(f"TLS: {config['mail_use_tls']}, SSL: {app.config['MAIL_USE_SSL']}")
        except Exception as e:
            app.logger.error(f"Fehler bei E-Mail-Initialisierung: {e}")
            mail = None
    else:
        # Fallback auf Umgebungsvariablen oder Entwicklungsmodus
        app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
        app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
        app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
        app.config['MAIL_USE_SSL'] = not app.config['MAIL_USE_TLS'] and int(app.config['MAIL_PORT']) == 465
        app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'dummy@example.com')
        app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'dummy-password')
        app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'dummy@example.com')
        
        # Zusätzliche Flask-Mail Konfiguration
        app.config['MAIL_ASCII_ATTACHMENTS'] = False
        app.config['MAIL_SUPPRESS_SEND'] = False
        
        # Prüfe ob wir im Entwicklungsmodus sind (Dummy-E-Mail-Daten)
        is_dev_mode = (app.config['MAIL_USERNAME'] == 'dummy@example.com' or 
                       app.config['MAIL_PASSWORD'] == 'dummy-password')
        
        if is_dev_mode:
            app.logger.info("E-Mail-System im Entwicklungsmodus - E-Mails werden in der Konsole ausgegeben")
            mail = None
        else:
            try:
                mail = Mail(app)
                app.logger.info("E-Mail-System mit Umgebungsvariablen initialisiert")
                app.logger.info(f"SMTP-Server: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
                app.logger.info(f"TLS: {app.config['MAIL_USE_TLS']}, SSL: {app.config['MAIL_USE_SSL']}")
            except Exception as e:
                app.logger.error(f"Fehler bei E-Mail-Initialisierung: {e}")
                mail = None


def _check_auth_required(server, port, use_tls):
    """Prüft ob ein SMTP-Server Authentifizierung benötigt"""
    try:
        import smtplib
        
        # Verbindung testen
        if use_tls and port == 465:
            smtp_server = smtplib.SMTP_SSL(server, port)
        else:
            smtp_server = smtplib.SMTP(server, port)
        
        # EHLO senden
        capabilities = smtp_server.ehlo()
        
        # STARTTLS aktivieren falls konfiguriert
        if use_tls and port == 587:
            try:
                smtp_server.starttls()
                capabilities = smtp_server.ehlo()
            except:
                pass  # STARTTLS nicht verfügbar
        
        # Prüfe AUTH in Capabilities (korrigiert für btz-koeln.net)
        auth_supported = False
        if hasattr(smtp_server, 'esmtp_features') and smtp_server.esmtp_features:
            auth_supported = 'auth' in smtp_server.esmtp_features
        
        # Fallback: Prüfe in Capabilities-Strings
        if not auth_supported and capabilities and len(capabilities) > 1:
            for cap in capabilities[1]:
                if isinstance(cap, bytes):
                    try:
                        cap_str = cap.decode('utf-8', errors='ignore')
                    except UnicodeDecodeError:
                        cap_str = cap.decode('latin-1', errors='ignore')
                else:
                    cap_str = str(cap)
                
                if 'auth' in cap_str.lower():
                    auth_supported = True
                    break
        
        smtp_server.quit()
        return auth_supported
        
    except Exception as e:
        logger.warning(f"Konnte Auth-Status für {server}:{port} nicht prüfen: {e}")
        # Bei Fehlern annehmen, dass Auth erforderlich ist (sicherer Fallback)
        return True


def _log_email(subject, recipient, body):
    """Loggt E-Mails in der Entwicklungsumgebung"""
    logger.info("=" * 60)
    logger.info("E-MAIL SIMULATION (Entwicklungsmodus)")
    logger.info("=" * 60)
    logger.info(f"An: {recipient}")
    logger.info(f"Betreff: {subject}")
    logger.info("-" * 60)
    logger.info(body)
    logger.info("=" * 60)


def _send_email_direct(recipient, subject, body, attachments=None):
    """Sendet E-Mails direkt über SMTP ohne Speicherung im 'Gesendet'-Ordner"""
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        import smtplib
        
        # Lade E-Mail-Konfiguration
        config = get_email_config()
        if not config or not config['enabled']:
            logger.error("E-Mail-Konfiguration nicht verfügbar oder deaktiviert")
            return False
        
        # Erstelle E-Mail-Nachricht
        msg = MIMEMultipart()
        msg['From'] = config['mail_username']
        msg['To'] = recipient
        
        # Subject korrekt als UTF-8 kodieren
        from email.header import Header
        msg['Subject'] = Header(subject, 'utf-8')
        
        # Message-ID hinzufügen (RFC 5322 Compliance für Gmail)
        import uuid
        import socket
        from email.utils import formatdate
        hostname = socket.gethostname()
        message_id = f"<{uuid.uuid4()}@{hostname}>"
        msg['Message-ID'] = message_id
        msg['Date'] = formatdate(localtime=True)
        
        # Spezielle Header um Speicherung im "Gesendet"-Ordner zu verhindern
        msg['X-Auto-Response-Suppress'] = 'All'
        msg['Precedence'] = 'bulk'
        msg['X-Mailer'] = 'Scandy-System'
        
        # Body hinzufügen - explizit UTF-8 kodieren
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Anhänge hinzufügen (falls vorhanden)
        if attachments:
            for attachment in attachments:
                with open(attachment['path'], 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 
                                   f'attachment; filename= {attachment["filename"]}')
                    msg.attach(part)
        
        # SMTP-Verbindung aufbauen
        if config['mail_use_tls'] and config['mail_port'] == 465:
            server = smtplib.SMTP_SSL(config['mail_server'], config['mail_port'])
        else:
            server = smtplib.SMTP(config['mail_server'], config['mail_port'])
        
        # STARTTLS aktivieren falls konfiguriert
        if config['mail_use_tls'] and config['mail_port'] == 587:
            server.starttls()
        
        # UTF-8 für SMTP-Verbindung aktivieren
        server.ehlo()
        if hasattr(server, 'esmtp_features') and server.esmtp_features:
            if '8bitmime' in server.esmtp_features:
                logger.info("8BITMIME wird unterstützt - UTF-8 E-Mails möglich")
            else:
                logger.warning("8BITMIME nicht unterstützt - E-Mails werden als 7-bit gesendet")
        
        # Authentifizierung (falls erforderlich)
        if config.get('use_auth', True) and config['mail_username'] and config['mail_password']:
            server.login(config['mail_username'], config['mail_password'])
        
        # E-Mail senden - explizit als UTF-8 kodieren
        text = msg.as_string()
        # Stelle sicher, dass der Text als UTF-8 Bytes gesendet wird
        if isinstance(text, str):
            text = text.encode('utf-8')
        server.sendmail(config['mail_username'], recipient, text)
        server.quit()
        
        return True
        
    except Exception as e:
        logger.error(f"Fehler beim direkten E-Mail-Versand: {e}")
        return False


def send_password_mail(recipient, password):
    subject = 'Ihr Zugang zu Scandy'
    body = f"Willkommen bei Scandy!\n\nIhr initiales Passwort lautet: {password}\nBitte ändern Sie es nach dem ersten Login.\n\nMit freundlichen Grüßen\nIhr Scandy-Team"
    
    if mail is None:
        _log_email(subject, recipient, body)
        return True
    else:
        try:
            # Verwende direkte SMTP-Verbindung um "Gesendet"-Ordner zu vermeiden
            success = _send_email_direct(recipient, subject, body)
            if success:
                logger.info(f"Passwort-E-Mail erfolgreich an {recipient} gesendet (ohne Speicherung im Gesendet-Ordner)")
            return success
        except Exception as e:
            logger.error(f"Fehler beim Versenden der Passwort-E-Mail: {e}")
            return False


def send_password_reset_mail(recipient, password=None, reset_link=None):
    subject = 'Scandy Passwort-Reset'
    
    if reset_link:
        body = f"Sie haben einen Passwort-Reset angefordert.\nBitte klicken Sie auf folgenden Link, um Ihr Passwort zurückzusetzen:\n{reset_link}\n\nMit freundlichen Grüßen\nIhr Scandy-Team"
    elif password:
        body = f"Ihr neues Passwort lautet: {password}\nBitte ändern Sie es nach dem Login.\n\nMit freundlichen Grüßen\nIhr Scandy-Team"
    else:
        body = "Es ist ein Fehler aufgetreten."
    
    if mail is None:
        _log_email(subject, recipient, body)
        return True
    else:
        try:
            # Verwende direkte SMTP-Verbindung um "Gesendet"-Ordner zu vermeiden
            success = _send_email_direct(recipient, subject, body)
            if success:
                logger.info(f"Passwort-Reset-E-Mail erfolgreich an {recipient} gesendet (ohne Speicherung im Gesendet-Ordner)")
            return success
        except Exception as e:
            logger.error(f"Fehler beim Versenden der Passwort-Reset-E-Mail: {e}")
            return False


def send_backup_mail(recipient, backup_path):
    subject = 'Scandy Backup'
    body = "Im Anhang finden Sie das aktuelle Backup."
    
    if os.path.getsize(backup_path) < 15 * 1024 * 1024:  # 15MB Limit
        body += f"\n\nBackup-Datei: {os.path.basename(backup_path)}"
    else:
        body += f"\n\nDas Backup ist zu groß für den Versand. Sie finden es unter: {backup_path}"
    
    if mail is None:
        _log_email(subject, recipient, body)
        return True
    else:
        try:
            # Verwende direkte SMTP-Verbindung um "Gesendet"-Ordner zu vermeiden
            attachments = None
            if os.path.getsize(backup_path) < 15 * 1024 * 1024:  # 15MB Limit
                attachments = [{
                    'path': backup_path,
                    'filename': os.path.basename(backup_path)
                }]
            
            success = _send_email_direct(recipient, subject, body, attachments)
            if success:
                logger.info(f"Backup-E-Mail erfolgreich an {recipient} gesendet (ohne Speicherung im Gesendet-Ordner)")
            return success
        except Exception as e:
            logger.error(f"Fehler beim Versenden der Backup-E-Mail: {e}")
            return False

def send_weekly_backup_mail(recipient, archive_path):
    """Sendet wöchentliches Backup-Archiv per E-Mail"""
    subject = 'Scandy - Wöchentliches Backup-Archiv'
    body = f"""Hallo,

anbei erhalten Sie das wöchentliche Backup-Archiv von Scandy.

Das Archiv enthält alle aktuellen Backups der letzten Woche und wurde automatisch am {datetime.now().strftime('%d.%m.%Y um %H:%M')} erstellt.

Archiv-Datei: {os.path.basename(archive_path)}

Mit freundlichen Grüßen
Ihr Scandy-System"""

    if mail is None:
        _log_email(subject, recipient, body)
        return True
    else:
        try:
            # Verwende direkte SMTP-Verbindung um "Gesendet"-Ordner zu vermeiden
            attachments = None
            if os.path.getsize(archive_path) < 25 * 1024 * 1024:  # 25MB Limit für Archive
                attachments = [{
                    'path': archive_path,
                    'filename': os.path.basename(archive_path)
                }]
            else:
                body += f"\n\nDas Backup-Archiv ist zu groß für den E-Mail-Versand (>25MB).\nSie finden es unter: {archive_path}"
            
            success = _send_email_direct(recipient, subject, body, attachments)
            if success:
                logger.info(f"Wöchentliches Backup-Archiv erfolgreich an {recipient} gesendet (ohne Speicherung im Gesendet-Ordner)")
            return success
        except Exception as e:
            logger.error(f"Fehler beim Versenden des wöchentlichen Backup-Archivs: {e}")
            return False

def reload_email_config(app):
    """Lädt die E-Mail-Konfiguration neu und initialisiert das E-Mail-System"""
    global mail
    try:
        # Schließe bestehende Mail-Verbindung
        if mail:
            mail = None
        
        # Initialisiere E-Mail-System neu
        init_mail(app)
        
        # Teste die neue Konfiguration
        config = get_email_config()
        if config and config['enabled'] and config['mail_username'] and config['mail_password']:
            app.logger.info("E-Mail-Konfiguration erfolgreich neu geladen und aktiviert")
        else:
            app.logger.info("E-Mail-Konfiguration neu geladen - System im Entwicklungsmodus")
        
        return True
    except Exception as e:
        app.logger.error(f"Fehler beim Neuladen der E-Mail-Konfiguration: {e}")
        return False

def diagnose_smtp_connection(config_data):
    """Diagnostiziert die SMTP-Verbindung ohne E-Mail zu versenden"""
    try:
        import smtplib
        
        server_info = {
            'server': config_data['mail_server'],
            'port': int(config_data['mail_port']),
            'use_tls': config_data['mail_use_tls'],
            'use_ssl': not config_data['mail_use_tls'] and int(config_data['mail_port']) == 465
        }
        
        # Verbindung testen
        if server_info['use_ssl']:
            server = smtplib.SMTP_SSL(server_info['server'], server_info['port'])
        else:
            server = smtplib.SMTP(server_info['server'], server_info['port'])
        
        # Server-Capabilities vor TLS abrufen
        capabilities_before = server.ehlo()
        
        # Debug: Zeige rohe Capabilities
        logger.info(f"Rohe Capabilities: {capabilities_before}")
        logger.info(f"ESMTP Features: {getattr(server, 'esmtp_features', 'Nicht verfügbar')}")
        
        # Prüfe ob STARTTLS verfügbar ist - verbesserte Erkennung
        starttls_available = False
        
        # Methode 1: Prüfe esmtp_features (am zuverlässigsten)
        if hasattr(server, 'esmtp_features') and server.esmtp_features:
            starttls_available = 'starttls' in server.esmtp_features
            logger.info(f"STARTTLS in esmtp_features gefunden: {starttls_available}")
        
        # Methode 2: Prüfe in den Capabilities-Strings (Fallback)
        if not starttls_available and capabilities_before and len(capabilities_before) > 1:
            for cap in capabilities_before[1]:
                if isinstance(cap, bytes):
                    try:
                        cap_str = cap.decode('utf-8', errors='ignore')
                    except UnicodeDecodeError:
                        cap_str = cap.decode('latin-1', errors='ignore')
                else:
                    cap_str = str(cap)
                
                if 'starttls' in cap_str.lower():
                    starttls_available = True
                    logger.info(f"STARTTLS in Capability gefunden: {cap_str}")
                    break
        
        # Methode 3: Für bekannte Server - versuche STARTTLS auch wenn nicht erkannt
        known_servers = ['smtp.gmail.com', 'smtp.office365.com', 'smtp-mail.outlook.com']
        if not starttls_available and config_data['mail_server'] in known_servers and int(config_data['mail_port']) == 587:
            logger.info(f"{config_data['mail_server']} mit Port 587 - versuche STARTTLS trotz fehlender Erkennung")
            starttls_available = True
        
        # TLS aktivieren falls konfiguriert und verfügbar
        tls_activated = False
        tls_error = None
        capabilities_after = capabilities_before
        
        if server_info['use_tls'] and starttls_available:
            try:
                logger.info("Versuche STARTTLS zu aktivieren...")
                server.starttls()
                # Neue Capabilities nach TLS
                capabilities_after = server.ehlo()
                tls_activated = True
                logger.info("STARTTLS erfolgreich aktiviert")
            except Exception as e:
                capabilities_after = capabilities_before
                tls_error = str(e)
                logger.error(f"STARTTLS Fehler: {tls_error}")
        else:
            if not starttls_available:
                logger.warning("STARTTLS nicht verfügbar")
            if not server_info['use_tls']:
                logger.info("TLS nicht konfiguriert")
        
        # Authentifizierung testen - nach TLS-Aktivierung
        auth_supported = False
        
        # Methode 1: Prüfe esmtp_features nach TLS
        if hasattr(server, 'esmtp_features') and server.esmtp_features:
            auth_supported = 'auth' in server.esmtp_features
            logger.info(f"AUTH in esmtp_features gefunden: {auth_supported}")
        
        # Methode 2: Fallback - Prüfe in den Capabilities-Strings
        if not auth_supported and capabilities_after and len(capabilities_after) > 1:
            for cap in capabilities_after[1]:
                if isinstance(cap, bytes):
                    try:
                        cap_str = cap.decode('utf-8', errors='ignore')
                    except UnicodeDecodeError:
                        cap_str = cap.decode('latin-1', errors='ignore')
                else:
                    cap_str = str(cap)
                
                if 'auth' in cap_str.lower():
                    auth_supported = True
                    logger.info(f"AUTH in Capability gefunden: {cap_str}")
                    break
        
        # Methode 3: Konvertiere ASCII-Codes zu String und prüfe AUTH
        if not auth_supported and capabilities_after and len(capabilities_after) > 1:
            # Konvertiere alle Capabilities zu Strings für bessere Suche
            all_capabilities = []
            for cap in capabilities_after[1]:
                if isinstance(cap, bytes):
                    try:
                        cap_str = cap.decode('utf-8', errors='ignore')
                    except UnicodeDecodeError:
                        cap_str = cap.decode('latin-1', errors='ignore')
                else:
                    cap_str = str(cap)
                all_capabilities.append(cap_str)
            
            # Suche nach AUTH in allen konvertierten Capabilities
            combined_capabilities = ' '.join(all_capabilities)
            if 'auth' in combined_capabilities.lower():
                auth_supported = True
                logger.info(f"AUTH in kombinierten Capabilities gefunden: {combined_capabilities}")
        
        # Methode 4: Für bekannte Server - AUTH wird unterstützt
        known_servers = ['smtp.gmail.com', 'smtp.office365.com', 'smtp-mail.outlook.com']
        if not auth_supported and server_info['server'] in known_servers and tls_activated:
            logger.info(f"{server_info['server']} mit aktiviertem TLS - AUTH wird unterstützt")
            auth_supported = True
        
        # Authentifizierung durchführen
        if auth_supported and config_data['mail_username'] and config_data['mail_password']:
            try:
                server.login(config_data['mail_username'], config_data['mail_password'])
                auth_status = "Erfolgreich"
                logger.info("Authentifizierung erfolgreich")
            except smtplib.SMTPAuthenticationError as e:
                auth_status = f"Fehlgeschlagen (falsche Anmeldedaten): {str(e)}"
                logger.error(f"Authentifizierung fehlgeschlagen: {e}")
            except Exception as e:
                auth_status = f"Fehler: {str(e)}"
                logger.error(f"Authentifizierungsfehler: {e}")
        elif not auth_supported:
            auth_status = "Nicht unterstützt"
            logger.warning("AUTH nicht unterstützt")
        else:
            auth_status = "Übersprungen (keine Anmeldedaten)"
            logger.info("Authentifizierung übersprungen - keine Anmeldedaten")
        
        server.quit()
        
        # Nach TLS: Capabilities loggen
        logger.info(f"Capabilities nach STARTTLS (zweites EHLO): {capabilities_after}")
        # Capabilities nach TLS auch im Diagnose-Resultat anzeigen
        capabilities_list = []
        if capabilities_after and len(capabilities_after) > 1:
            for cap in capabilities_after[1]:
                if isinstance(cap, bytes):
                    try:
                        cap_str = cap.decode('utf-8')
                    except UnicodeDecodeError:
                        cap_str = cap.decode('latin-1', errors='ignore')
                    capabilities_list.append(cap_str)
                else:
                    capabilities_list.append(str(cap))
        # Zusätzlich: Capabilities nach TLS als kombinierten String für die Diagnose
        combined_capabilities_after = ' | '.join(capabilities_list)
        result = {
            'connection': 'Erfolgreich',
            'server': server_info['server'],
            'port': server_info['port'],
            'tls_configured': 'Ja' if server_info['use_tls'] else 'Nein',
            'tls_activated': 'Ja' if tls_activated else 'Nein',
            'ssl': 'Aktiviert' if server_info['use_ssl'] else 'Deaktiviert',
            'starttls_available': 'Ja' if starttls_available else 'Nein',
            'auth_supported': 'Ja' if auth_supported else 'Nein',
            'capabilities': capabilities_list,
            'capabilities_after_tls': combined_capabilities_after,
            'auth_status': auth_status
        }
        
        if tls_error:
            result['tls_error'] = tls_error
        
        return True, result
        
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Authentifizierung fehlgeschlagen: {str(e)}"
    except smtplib.SMTPConnectError as e:
        return False, f"Verbindung zum SMTP-Server fehlgeschlagen: {str(e)}"
    except smtplib.SMTPException as e:
        return False, f"SMTP-Fehler: {str(e)}"
    except Exception as e:
        return False, f"Verbindungsfehler: {str(e)}"

def test_bytes_conversion():
    """Testet die Bytes-Konvertierung für Debugging"""
    # Simuliere die ASCII-Codes aus der Diagnose
    ascii_codes = [115, 109, 116, 112, 46, 103, 109, 97, 105, 108, 46, 99, 111, 109, 32, 97, 116, 32, 121, 111, 117, 114, 32, 115, 101, 114, 118, 105, 99, 101, 44, 32, 91, 54, 49, 46, 56, 46, 49, 51, 48, 46, 49, 49, 56, 93, 10, 83, 73, 90, 69, 32, 51, 53, 54, 56, 50, 53, 55, 55, 10, 56, 66, 73, 84, 77, 73, 77, 69, 10, 83, 84, 65, 82, 84, 84, 76, 83, 10, 69, 78, 72, 65, 78, 67, 69, 68, 83, 84, 65, 84, 85, 83, 67, 79, 68, 69, 83, 10, 80, 73, 80, 69, 76, 73, 78, 73, 78, 71, 10, 67, 72, 85, 78, 75, 73, 78, 71, 10, 83, 77, 84, 80, 85, 84, 70, 56]
    
    # Konvertiere zu Bytes
    bytes_data = bytes(ascii_codes)
    
    # Versuche verschiedene Decodierungen
    try:
        utf8_str = bytes_data.decode('utf-8')
        logger.info(f"UTF-8 Decodierung: {utf8_str}")
    except Exception as e:
        logger.error(f"UTF-8 Decodierung fehlgeschlagen: {e}")
    
    try:
        latin1_str = bytes_data.decode('latin-1')
        logger.info(f"Latin-1 Decodierung: {latin1_str}")
    except Exception as e:
        logger.error(f"Latin-1 Decodierung fehlgeschlagen: {e}")
    
    # Suche nach STARTTLS
    if 'STARTTLS' in utf8_str:
        logger.info("STARTTLS in UTF-8 String gefunden!")
    else:
        logger.info("STARTTLS nicht in UTF-8 String gefunden")
    
    return utf8_str 