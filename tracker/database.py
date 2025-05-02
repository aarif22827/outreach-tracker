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