"""
SQLite session database for storing and managing user sessions.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "sessions.db"


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the sessions database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Sessions database initialized")


def store_session(token: str, username: str, expires_at: datetime) -> bool:
    """Store a new session in the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (token, username, expires_at)
            VALUES (?, ?, ?)
        """, (token, username, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error storing session: {e}")
        return False


def get_session(token: str) -> Optional[dict]:
    """Get a session by token."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sessions WHERE token = ?
    """, (token,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    # Check if session has expired
    expires_at = datetime.fromisoformat(row["expires_at"])
    if datetime.utcnow() > expires_at:
        delete_session(token)
        return None
    
    return dict(row)


def delete_session(token: str) -> bool:
    """Delete a session (logout)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM sessions WHERE token = ?
        """, (token,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting session: {e}")
        return False


def cleanup_expired_sessions() -> int:
    """Remove all expired sessions. Returns count of deleted sessions."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM sessions WHERE expires_at < ?
        """, (datetime.utcnow().isoformat(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    except Exception as e:
        print(f"Error cleaning up sessions: {e}")
        return 0


# Initialize database on import
init_db()
