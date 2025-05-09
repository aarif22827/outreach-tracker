import sqlite3

REQUIRED_COLUMNS = {
    "outreaches": [
        ("last_response", "TEXT"),
        ("status", "TEXT"),
        ("notes", "TEXT"),
        ("email", "TEXT")
    ],
    "applications": [
        ("title", "TEXT"),
        ("application_link", "TEXT"),
        ("status", "TEXT"),
        ("notes", "TEXT")
    ]
}

def get_connection():
    return sqlite3.connect("outreach_tracker.db")

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS outreaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            company TEXT,
            title TEXT,
            email TEXT,
            linkedin_url TEXT,
            connection_sent BOOLEAN DEFAULT 0,
            message_sent BOOLEAN DEFAULT 0,
            followup_sent BOOLEAN DEFAULT 0,
            status TEXT,
            last_response TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            title TEXT,
            application_link TEXT,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            related_type TEXT,
            related_id INTEGER,
            title TEXT,
            description TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # New tables for resources
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,  -- 'resume', 'cover_letter', 'other'
            version TEXT,
            file_content BLOB,
            file_type TEXT,  -- 'pdf', 'docx', etc.
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            related_type TEXT,  -- 'application', 'contact'
            related_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,  -- 'connection_request', 'follow_up', 'thank_you', etc.
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    migrate_schema()

def migrate_schema():
    conn = get_connection()
    cursor = conn.cursor()

    for table, columns in REQUIRED_COLUMNS.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [col[1] for col in cursor.fetchall()]

        for column_name, column_type in columns:
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")

    conn.commit()
    conn.close()