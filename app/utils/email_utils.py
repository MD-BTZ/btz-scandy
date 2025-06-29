from flask_mail import Mail, Message
from flask import current_app
import os
import logging

mail = None
logger = logging.getLogger(__name__)

def init_mail(app):
    global mail
    # Verwende Umgebungsvariablen oder Fallback auf Dummy-Daten
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'dummy@example.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'dummy-password')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'dummy@example.com')
    
    # Prüfe ob wir im Entwicklungsmodus sind (Dummy-E-Mail-Daten)
    is_dev_mode = (app.config['MAIL_USERNAME'] == 'dummy@example.com' or 
                   app.config['MAIL_PASSWORD'] == 'dummy-password')
    
    if is_dev_mode:
        app.logger.info("E-Mail-System im Entwicklungsmodus - E-Mails werden in der Konsole ausgegeben")
        mail = None
    else:
        mail = Mail(app)
        app.logger.info("E-Mail-System mit SMTP initialisiert")


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


def send_password_mail(recipient, password):
    subject = 'Ihr Zugang zu Scandy'
    body = f"Willkommen bei Scandy!\n\nIhr initiales Passwort lautet: {password}\nBitte ändern Sie es nach dem ersten Login.\n\nViele Grüße\nIhr Scandy-Team"
    
    if mail is None:
        _log_email(subject, recipient, body)
        return True
    else:
        try:
            msg = Message(subject, recipients=[recipient])
            msg.body = body
            mail.send(msg)
            logger.info(f"Passwort-E-Mail erfolgreich an {recipient} gesendet")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Versenden der Passwort-E-Mail: {e}")
            return False


def send_password_reset_mail(recipient, password=None, reset_link=None):
    subject = 'Scandy Passwort-Reset'
    
    if reset_link:
        body = f"Sie haben einen Passwort-Reset angefordert.\nBitte klicken Sie auf folgenden Link, um Ihr Passwort zurückzusetzen:\n{reset_link}\n\nViele Grüße\nIhr Scandy-Team"
    elif password:
        body = f"Ihr neues Passwort lautet: {password}\nBitte ändern Sie es nach dem Login.\n\nViele Grüße\nIhr Scandy-Team"
    else:
        body = "Es ist ein Fehler aufgetreten."
    
    if mail is None:
        _log_email(subject, recipient, body)
        return True
    else:
        try:
            msg = Message(subject, recipients=[recipient])
            msg.body = body
            mail.send(msg)
            logger.info(f"Passwort-Reset-E-Mail erfolgreich an {recipient} gesendet")
            return True
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
            msg = Message(subject, recipients=[recipient])
            msg.body = body
            if os.path.getsize(backup_path) < 15 * 1024 * 1024:  # 15MB Limit
                with open(backup_path, 'rb') as f:
                    msg.attach(os.path.basename(backup_path), 'application/zip', f.read())
            mail.send(msg)
            logger.info(f"Backup-E-Mail erfolgreich an {recipient} gesendet")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Versenden der Backup-E-Mail: {e}")
            return False 