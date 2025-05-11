from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict, Any, ClassVar, Type, TypeVar
from tracker.core.database import get_connection

T = TypeVar('T', bound='BaseModel')

class BaseModel:
    """Base model class with common database operations"""
    table_name: ClassVar[str] = ""
    id_column: ClassVar[str] = "id"
    
    id: Optional[int] = None
    
    @classmethod
    def get_by_id(cls: Type[T], id: int) -> Optional[T]:
        """Fetch a record by its ID"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {cls.table_name} WHERE {cls.id_column} = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        columns = [col[0] for col in cursor.description]
        data = {columns[i]: row[i] for i in range(len(columns))}
        
        return cls(**data)
    
    @classmethod
    def find_all(cls: Type[T], where_clause: str = "", params: tuple = ()) -> List[T]:
        """Find all records matching the criteria"""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {cls.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        if rows:
            columns = [col[0] for col in cursor.description]
            for row in rows:
                data = {columns[i]: row[i] for i in range(len(columns))}
                result.append(cls(**data))
        
        conn.close()
        return result
    
    def save(self) -> int:
        """Save or update the record"""
        conn = get_connection()
        cursor = conn.cursor()
        
        data = self.to_dict()
        
        if self.id:
            update_data = {k: v for k, v in data.items() 
                          if k not in [self.id_column, 'created_at']}
            
            update_data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values())
            
            cursor.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE {self.id_column} = ?",
                [*values, self.id]
            )
            conn.commit()
            conn.close()
            return self.id
        else:
            insert_data = {k: v for k, v in data.items() if k != self.id_column}
            
            columns = ", ".join(insert_data.keys())
            placeholders = ", ".join(["?"] * len(insert_data))
            values = list(insert_data.values())
            
            cursor.execute(
                f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
                values
            )
            
            cursor.execute("SELECT last_insert_rowid()")
            new_id = cursor.fetchone()[0]
            self.id = new_id
            
            conn.commit()
            conn.close()
            return new_id
    
    def delete(self) -> bool:
        """Delete the record"""
        if not self.id:
            return False
            
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"DELETE FROM {self.table_name} WHERE {self.id_column} = ?", (self.id,))
        conn.commit()
        conn.close()
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for database operations"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


class Contact(BaseModel):
    """Model for outreach contacts"""
    table_name = "outreaches"
    
    def __init__(self, id=None, name="", company="", title="", email="", linkedin_url="",
                 status="🔵 Not Connected", last_response="", notes="", created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.name = name
        self.company = company
        self.title = title
        self.email = email
        self.linkedin_url = linkedin_url
        self.status = status
        self.last_response = last_response
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at
    
    def get_linked_documents(self) -> List['Document']:
        """Get all documents linked to this contact"""
        return Document.find_related('contact', self.id)
    
    def get_reminders(self) -> List['Reminder']:
        """Get all reminders for this contact"""
        return Reminder.find_by_related('contact', self.id)


class Application(BaseModel):
    """Model for job applications"""
    table_name = "applications"
    
    def __init__(self, id=None, title="", name="", application_link="",
                 status="📝 Not Applied", notes="", created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.title = title
        self.name = name
        self.application_link = application_link
        self.status = status
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at
    
    def get_linked_documents(self) -> List['Document']:
        """Get all documents linked to this application"""
        return Document.find_related('application', self.id)
    
    def get_reminders(self) -> List['Reminder']:
        """Get all reminders for this application"""
        return Reminder.find_by_related('application', self.id)


class Document(BaseModel):
    """Model for documents"""
    table_name = "documents"
    
    def __init__(self, id=None, name="", type="", version="1.0", file_content=None, file_type="", 
                 notes="", created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.name = name
        self.type = type
        self.version = version
        self.file_content = file_content
        self.file_type = file_type
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def find_related(cls, related_type: str, related_id: int) -> List['Document']:
        """Find all documents linked to a specific contact or application"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.* FROM documents d
            JOIN document_usage du ON d.id = du.document_id
            WHERE du.related_type = ? AND du.related_id = ?
        ''', (related_type, related_id))
        
        rows = cursor.fetchall()
        
        result = []
        if rows:
            columns = [col[0] for col in cursor.description]
            for row in rows:
                data = {columns[i]: row[i] for i in range(len(columns))}
                result.append(cls(**data))
        
        conn.close()
        return result
    
    def link_to(self, related_type: str, related_id: int) -> bool:
        """Link this document to a contact or application"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM document_usage 
            WHERE document_id = ? AND related_type = ? AND related_id = ?
        ''', (self.id, related_type, related_id))
        
        if cursor.fetchone():
            conn.close()
            return False 
        
        cursor.execute('''
            INSERT INTO document_usage (document_id, related_type, related_id)
            VALUES (?, ?, ?)
        ''', (self.id, related_type, related_id))
        
        conn.commit()
        conn.close()
        return True
    
    def unlink_from(self, related_type: str, related_id: int) -> bool:
        """Remove link between this document and a contact or application"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM document_usage 
            WHERE document_id = ? AND related_type = ? AND related_id = ?
        ''', (self.id, related_type, related_id))
        
        conn.commit()
        conn.close()
        return True


class Reminder(BaseModel):
    """Model for reminders"""
    table_name = "reminders"
    
    def __init__(self, id=None, title="", related_type="", related_id=None, 
                 description="", due_date="", status="pending", created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.title = title
        self.related_type = related_type
        self.related_id = related_id
        self.description = description
        self.due_date = due_date
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def find_by_related(cls, related_type: str, related_id: int) -> List['Reminder']:
        """Find all reminders for a specific contact or application"""
        return cls.find_all("related_type = ? AND related_id = ?", (related_type, related_id))
    
    @classmethod
    def find_upcoming(cls, days: int = 7) -> List['Reminder']:
        """Find reminders due within the specified number of days"""
        conn = get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%m/%d/%Y")
        
        cursor.execute('''
            SELECT r.*, 
                   CASE 
                       WHEN r.related_type = 'contact' THEN o.name
                       WHEN r.related_type = 'application' THEN a.title || ' at ' || a.name
                       ELSE 'Unknown'
                   END as related_name
            FROM reminders r
            LEFT JOIN outreaches o ON r.related_id = o.id AND r.related_type = 'contact'
            LEFT JOIN applications a ON r.related_id = a.id AND r.related_type = 'application'
            WHERE r.status = 'pending'
            AND julianday(r.due_date) - julianday(?) <= ?
        ''', (today, days))
        
        rows = cursor.fetchall()
        
        result = []
        if rows:
            columns = [col[0] for col in cursor.description]
            for row in rows:
                data = {columns[i]: row[i] for i in range(len(columns)) if i < len(columns) - 1}
                reminder = cls(**data)
                reminder.related_name = row[len(columns) - 1]
                result.append(reminder)
        
        conn.close()
        return result
    
    def mark_complete(self) -> bool:
        """Mark this reminder as completed"""
        self.status = "completed"
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        return True
    
    def snooze(self, new_date: str) -> bool:
        """Snooze this reminder to a new date"""
        self.due_date = new_date
        self.status = "snoozed"
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        return True


class MessageTemplate(BaseModel):
    """Model for message templates"""
    table_name = "message_templates"
    
    def __init__(self, id=None, name="", category="", content="", 
                 created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.name = name
        self.category = category
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at
    
    def render(self, data: Dict[str, str]) -> str:
        """Render the template with the provided data"""
        try:
            return self.content.format(**data)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")