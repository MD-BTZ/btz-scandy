"""
Zentraler Ticket Service für Scandy
Alle Ticket-Funktionalitäten an einem Ort
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from flask import current_app
from app.models.mongodb_database import mongodb
from app.services.notification_service import NotificationService
from app.services.utility_service import UtilityService
from app.utils.database_helpers import get_ticket_categories_from_settings, get_next_ticket_number
import logging

logger = logging.getLogger(__name__)

class TicketService:
    """Zentraler Service für alle Ticket-Operationen"""
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.utility_service = UtilityService()
    
    def create_ticket(self, ticket_data: Dict[str, Any], created_by: str) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein neues Ticket
        
        Args:
            ticket_data: Ticket-Daten
            created_by: Benutzername des Erstellers
            
        Returns:
            Tuple: (success, message, ticket_id)
        """
        try:
            # Validierung
            if not ticket_data.get('title'):
                return False, 'Titel ist erforderlich', None
            
            # Kategorie validieren/erstellen
            category = ticket_data.get('category')
            if category:
                ticket_categories = get_ticket_categories_from_settings()
                if category not in ticket_categories:
                    # Füge die neue Kategorie zu den Settings hinzu
                    mongodb.update_one_array(
                        'settings',
                        {'key': 'ticket_categories'},
                        {'$push': {'value': category}},
                        upsert=True
                    )
            
            # Fälligkeitsdatum formatieren
            due_date = ticket_data.get('due_date')
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    due_date = None
            
            # Ticket-Daten vorbereiten
            ticket = {
                'title': ticket_data['title'],
                'description': ticket_data.get('description', ''),
                'priority': ticket_data.get('priority', 'normal'),
                'created_by': created_by,
                'category': category,
                'due_date': due_date,
                'estimated_time': ticket_data.get('estimated_time'),
                'status': 'offen',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'ticket_number': get_next_ticket_number()
            }
            
            # Ticket in Datenbank speichern
            result = mongodb.insert_one('tickets', ticket)
            ticket_id = str(result)
            
            logger.info(f"Ticket erstellt: {ticket_id} von {created_by}")
            return True, 'Ticket wurde erfolgreich erstellt', ticket_id
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            return False, f'Fehler beim Erstellen des Tickets: {str(e)}', None
    
    def get_tickets_by_user(self, username: str, role: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Holt Tickets basierend auf Benutzerrolle
        
        Args:
            username: Benutzername
            role: Benutzerrolle
            
        Returns:
            Dict: Verschiedene Ticket-Listen
        """
        try:
            print(f"DEBUG: Lade Tickets für Benutzer: {username}, Rolle: {role}")
            
            # Debug: Prüfe alle Tickets in der Datenbank
            all_tickets_debug = list(mongodb.find('tickets', {}))
            print(f"DEBUG: Gesamtanzahl Tickets in DB: {len(all_tickets_debug)}")
            
            # Offene Tickets (nicht zugewiesene, offene Tickets)
            open_query = {
                '$or': [
                    {'assigned_to': None},
                    {'assigned_to': ''}
                ],
                'status': 'offen',
                'deleted': {'$ne': True}
            }
            print(f"DEBUG: Offene Tickets Query: {open_query}")
            open_tickets = mongodb.find('tickets', open_query)
            open_tickets = list(open_tickets)
            print(f"DEBUG: Offene Tickets gefunden: {len(open_tickets)}")
            
            # Zugewiesene Tickets
            if role in ['admin', 'mitarbeiter']:
                # Für Admins/Mitarbeiter: Eigene zugewiesene Tickets + alle gelösten/geschlossenen
                assigned_query = {
                    '$or': [
                        {'assigned_to': username, 'deleted': {'$ne': True}},
                        {'status': {'$in': ['gelöst', 'geschlossen']}, 'deleted': {'$ne': True}}
                    ]
                }
            else:
                # Für normale User: Nur eigene zugewiesene Tickets
                assigned_query = {
                    'assigned_to': username,
                    'deleted': {'$ne': True}
                }
            
            print(f"DEBUG: Zugewiesene Tickets Query: {assigned_query}")
            assigned_tickets = mongodb.find('tickets', assigned_query)
            assigned_tickets = list(assigned_tickets)
            print(f"DEBUG: Zugewiesene Tickets gefunden: {len(assigned_tickets)}")
            
            # Alle Tickets (nur für Admins/Mitarbeiter)
            all_tickets = []
            if role in ['admin', 'mitarbeiter']:
                all_query = {'deleted': {'$ne': True}}
                print(f"DEBUG: Alle Tickets Query: {all_query}")
                all_tickets = mongodb.find('tickets', all_query)
                all_tickets = list(all_tickets)
                print(f"DEBUG: Alle Tickets gefunden: {len(all_tickets)}")
            
            # Nachrichtenanzahl und Auftragsdetails hinzufügen
            print(f"DEBUG: Verarbeite {len(open_tickets)} offene, {len(assigned_tickets)} zugewiesene, {len(all_tickets)} alle Tickets")
            
            for ticket_list in [open_tickets, assigned_tickets, all_tickets]:
                for ticket in ticket_list:
                    print(f"DEBUG: Verarbeite Ticket: {ticket.get('title', 'Kein Titel')} (ID: {ticket.get('_id')})")
                    
                    # ID-Feld für Template-Kompatibilität
                    ticket['id'] = str(ticket['_id'])
                    
                    # Nachrichtenanzahl - verwende verschiedene ID-Formate
                    ticket_id_str = str(ticket['_id'])
                    message_query = {
                        '$or': [
                            {'ticket_id': ticket['_id']},
                            {'ticket_id': ticket_id_str}
                        ]
                    }
                    message_count = mongodb.count_documents('ticket_messages', message_query)
                    ticket['message_count'] = message_count
                    print(f"DEBUG:   Nachrichtenanzahl für Ticket {ticket_id_str}: {message_count}")
                    
                    # Auftragsdetails - verwende verschiedene ID-Formate
                    auftrag_query = {
                        '$or': [
                            {'ticket_id': ticket['_id']},
                            {'ticket_id': ticket_id_str}
                        ]
                    }
                    auftrag_details = mongodb.find_one('auftrag_details', auftrag_query)
                    if auftrag_details:
                        ticket['auftrag_details'] = auftrag_details
                        print(f"DEBUG:   Auftragsdetails gefunden für Ticket {ticket_id_str}")
                    
                    # Datetime-Felder konvertieren
                    ticket = self._convert_datetime_fields(ticket)
            
            # Sichere Sortierung mit None-Behandlung
            def safe_sort_key(ticket):
                created_at = ticket.get('created_at')
                if created_at is None:
                    return datetime.min
                elif isinstance(created_at, str):
                    try:
                        # Versuche String zu datetime zu konvertieren
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                return datetime.strptime(created_at, fmt)
                            except ValueError:
                                continue
                        return datetime.min
                    except:
                        return datetime.min
                elif isinstance(created_at, datetime):
                    return created_at
                else:
                    return datetime.min
            
            # Sortierung
            open_tickets.sort(key=safe_sort_key, reverse=True)
            assigned_tickets.sort(key=safe_sort_key, reverse=True)
            all_tickets.sort(key=safe_sort_key, reverse=True)
            
            result = {
                'open_tickets': open_tickets,
                'assigned_tickets': assigned_tickets,
                'all_tickets': all_tickets
            }
            
            print(f"DEBUG: Endergebnis: {len(open_tickets)} offene, {len(assigned_tickets)} zugewiesene, {len(all_tickets)} alle Tickets")
            return result
            
        except Exception as e:
            print(f"DEBUG: Fehler beim Laden der Tickets: {str(e)}")
            return {
                'open_tickets': [],
                'assigned_tickets': [],
                'all_tickets': []
            }
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt ein Ticket anhand der ID
        
        Args:
            ticket_id: Ticket-ID
            
        Returns:
            Optional[Dict]: Ticket-Daten oder None
        """
        try:
            ticket = self.utility_service.find_document_by_id('tickets', ticket_id)
            if ticket:
                ticket = self._convert_datetime_fields(ticket)
                ticket['id'] = str(ticket['_id'])
            return ticket
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Tickets {ticket_id}: {str(e)}")
            return None
    
    def update_ticket_status(self, ticket_id: str, new_status: str, updated_by: str) -> Tuple[bool, str]:
        """
        Aktualisiert den Status eines Tickets
        
        Args:
            ticket_id: Ticket-ID
            new_status: Neuer Status
            updated_by: Benutzername des Aktualisierenden
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            # Status aktualisieren
            mongodb.update_one('tickets', 
                             {'_id': self.utility_service.convert_id_for_query(ticket_id)}, 
                             {'$set': {
                                 'status': new_status,
                                 'updated_at': datetime.now(),
                                 'updated_by': updated_by
                             }})
            
            # Benachrichtigung senden falls gewünscht
            if ticket.get('assigned_to') and ticket['assigned_to'] != updated_by:
                assigned_user = mongodb.find_one('users', {'username': ticket['assigned_to']})
                if assigned_user and assigned_user.get('email'):
                    self.notification_service.notify_ticket_update(ticket, assigned_user['email'])
            
            logger.info(f"Ticket-Status aktualisiert: {ticket_id} -> {new_status} von {updated_by}")
            return True, f'Status erfolgreich auf "{new_status}" geändert'
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Ticket-Status: {str(e)}")
            return False, f'Fehler beim Aktualisieren: {str(e)}'
    
    def assign_ticket(self, ticket_id: str, assigned_to: str, assigned_by: str) -> Tuple[bool, str]:
        """
        Weist ein Ticket einem Benutzer zu
        
        Args:
            ticket_id: Ticket-ID
            assigned_to: Benutzername des Zugewiesenen
            assigned_by: Benutzername des Zuweisenden
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            # Prüfe ob Benutzer existiert
            assigned_user = mongodb.find_one('users', {'username': assigned_to})
            if not assigned_user:
                return False, 'Zugewiesener Benutzer nicht gefunden'
            
            # Ticket zuweisen
            mongodb.update_one('tickets', 
                             {'_id': self.utility_service.convert_id_for_query(ticket_id)}, 
                             {'$set': {
                                 'assigned_to': assigned_to,
                                 'updated_at': datetime.now(),
                                 'updated_by': assigned_by
                             }})
            
            # Benachrichtigung senden
            if assigned_user.get('email'):
                self.notification_service.notify_ticket_assignment(ticket, assigned_user['email'])
            
            logger.info(f"Ticket zugewiesen: {ticket_id} -> {assigned_to} von {assigned_by}")
            return True, f'Ticket erfolgreich {assigned_user.get("firstname", "")} {assigned_user.get("lastname", "")} zugewiesen'
            
        except Exception as e:
            logger.error(f"Fehler beim Zuweisen des Tickets: {str(e)}")
            return False, f'Fehler beim Zuweisen: {str(e)}'
    
    def add_message_to_ticket(self, ticket_id: str, message: str, author: str) -> Tuple[bool, str]:
        """
        Fügt eine Nachricht zu einem Ticket hinzu
        
        Args:
            ticket_id: Ticket-ID
            message: Nachricht
            author: Autor der Nachricht
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            # Nachricht erstellen
            message_data = {
                'ticket_id': ticket_id,
                'message': message,
                'author': author,
                'created_at': datetime.now()
            }
            
            mongodb.insert_one('ticket_messages', message_data)
            
            # Ticket aktualisieren
            mongodb.update_one('tickets', 
                             {'_id': self.utility_service.convert_id_for_query(ticket_id)}, 
                             {'$set': {'updated_at': datetime.now()}})
            
            logger.info(f"Nachricht zu Ticket hinzugefügt: {ticket_id} von {author}")
            return True, 'Nachricht erfolgreich hinzugefügt'
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Nachricht: {str(e)}")
            return False, f'Fehler beim Hinzufügen: {str(e)}'
    
    def get_ticket_messages(self, ticket_id: str) -> List[Dict[str, Any]]:
        """
        Holt alle Nachrichten zu einem Ticket
        
        Args:
            ticket_id: Ticket-ID
            
        Returns:
            List: Liste der Nachrichten
        """
        try:
            messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id})
            messages = list(messages)
            
            # Datetime-Felder konvertieren
            for message in messages:
                message = self._convert_datetime_fields(message)
            
            # Nach Datum sortieren
            messages.sort(key=lambda x: x.get('created_at', datetime.min))
            
            return messages
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Nachrichten: {str(e)}")
            return []
    
    def delete_ticket(self, ticket_id: str, deleted_by: str, permanent: bool = False) -> Tuple[bool, str]:
        """
        Löscht ein Ticket (soft oder permanent)
        
        Args:
            ticket_id: Ticket-ID
            deleted_by: Benutzername des Löschers
            permanent: True für permanente Löschung
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            if permanent:
                # Permanente Löschung
                mongodb.delete_one('tickets', {'_id': self.utility_service.convert_id_for_query(ticket_id)})
                # Auch alle zugehörigen Nachrichten löschen
                mongodb.delete_many('ticket_messages', {'ticket_id': ticket_id})
                mongodb.delete_many('ticket_notes', {'ticket_id': ticket_id})
                mongodb.delete_many('auftrag_details', {'ticket_id': ticket_id})
                
                logger.info(f"Ticket permanent gelöscht: {ticket_id} von {deleted_by}")
                return True, 'Ticket permanent gelöscht'
            else:
                # Soft-Delete
                mongodb.update_one('tickets', 
                                 {'_id': self.utility_service.convert_id_for_query(ticket_id)}, 
                                 {'$set': {
                                     'deleted': True,
                                     'deleted_at': datetime.now(),
                                     'deleted_by': deleted_by
                                 }})
                
                logger.info(f"Ticket soft-gelöscht: {ticket_id} von {deleted_by}")
                return True, 'Ticket gelöscht'
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Tickets: {str(e)}")
            return False, f'Fehler beim Löschen: {str(e)}'
    
    def get_unassigned_ticket_count(self) -> int:
        """
        Gibt die Anzahl der nicht zugewiesenen Tickets zurück
        
        Returns:
            int: Anzahl der nicht zugewiesenen Tickets
        """
        try:
            count = mongodb.count_documents('tickets', {
                '$or': [
                    {'assigned_to': None},
                    {'assigned_to': ''}
                ],
                'status': 'offen',
                'deleted': {'$ne': True}
            })
            return count
            
        except Exception as e:
            logger.error(f"Fehler beim Zählen der nicht zugewiesenen Tickets: {str(e)}")
            return 0
    
    def _convert_datetime_fields(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Konvertiert datetime-Strings zu datetime-Objekten
        
        Args:
            ticket: Ticket-Daten
            
        Returns:
            Dict: Ticket mit konvertierten Datetime-Feldern
        """
        date_fields = ['created_at', 'updated_at', 'due_date', 'deleted_at']
        for field in date_fields:
            if ticket.get(field):
                if isinstance(ticket[field], str):
                    try:
                        # Versuche verschiedene Datumsformate zu parsen
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                ticket[field] = datetime.strptime(ticket[field], fmt)
                                break
                            except ValueError:
                                continue
                    except:
                        # Wenn alle Formate fehlschlagen, setze auf None
                        ticket[field] = None
                elif isinstance(ticket[field], datetime):
                    # Bereits ein datetime-Objekt, nichts zu tun
                    pass
                else:
                    # Versuche es als datetime zu konvertieren
                    try:
                        ticket[field] = datetime.fromisoformat(str(ticket[field]))
                    except:
                        # Wenn Konvertierung fehlschlägt, setze auf None
                        ticket[field] = None
            else:
                # Feld ist None oder nicht vorhanden, setze auf None
                ticket[field] = None
        return ticket 