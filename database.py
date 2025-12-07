"""
SQLite database management for persistent storage of users and guilds
"""

import sqlite3
from typing import Optional, List, Dict
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("databases/rebac.db")

def init_db():
    """Initialize the SQLite database with required tables"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Guilds table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(user_id)
        )
    """)
    
    # Roles table (for tracking created roles)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            role_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
        )
    """)
    
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# User operations
def save_user(user_id: str) -> bool:
    """Save a user to the database"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (user_id) VALUES (?)",
                (user_id,)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def get_user(user_id: str) -> Optional[Dict[str, str]]:
    """Get a user by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None

def get_all_users() -> List[Dict[str, str]]:
    """Get all users"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [dict(row) for row in cursor.fetchall()]

def delete_user(user_id: str) -> bool:
    """Delete a user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        return cursor.rowcount > 0

# Guild operations
def save_guild(guild_id: str, owner_id: str) -> bool:
    """Save a guild to the database"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO guilds (guild_id, owner_id) VALUES (?, ?)",
                (guild_id, owner_id)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def get_guild(guild_id: str) -> Optional[Dict[str, str]]:
    """Get a guild by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT guild_id, owner_id FROM guilds WHERE guild_id = ?",
            (guild_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None

def get_all_guilds() -> List[Dict[str, str]]:
    """Get all guilds"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT guild_id, owner_id FROM guilds")
        return [dict(row) for row in cursor.fetchall()]

def update_guild_owner(guild_id: str, new_owner_id: str) -> bool:
    """Update guild owner"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE guilds SET owner_id = ? WHERE guild_id = ?",
            (new_owner_id, guild_id)
        )
        return cursor.rowcount > 0

def delete_guild(guild_id: str) -> bool:
    """Delete a guild"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM guilds WHERE guild_id = ?", (guild_id,))
        return cursor.rowcount > 0

# Role operations
def save_role(role_id: str, guild_id: str) -> bool:
    """Save a role to the database"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO roles (role_id, guild_id) VALUES (?, ?)",
                (role_id, guild_id)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def get_role(role_id: str) -> Optional[Dict[str, str]]:
    """Get a role by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role_id, guild_id FROM roles WHERE role_id = ?",
            (role_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None

def get_guild_roles(guild_id: str) -> List[Dict[str, str]]:
    """Get all roles for a guild"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role_id, guild_id FROM roles WHERE guild_id = ?",
            (guild_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def delete_guild_roles(guild_id: str) -> bool:
    """Delete all roles for a guild"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM roles WHERE guild_id = ?", (guild_id,))
        return cursor.rowcount > 0

# Database management
def clear_all_data():
    """Clear all data from the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM roles")
        cursor.execute("DELETE FROM guilds")
        cursor.execute("DELETE FROM users")

def get_db_stats() -> Dict[str, int]:
    """Get database statistics"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM guilds")
        guilds_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM roles")
        roles_count = cursor.fetchone()[0]
    
    return {
        "users": users_count,
        "guilds": guilds_count,
        "roles": roles_count
    }