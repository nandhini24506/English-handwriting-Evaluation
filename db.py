import mysql.connector
from config import Config

def get_db_connection():
    """Returns a new connection to the MySQL database."""
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    return conn

def execute_query(sql, params=(), commit=False):
    """Executes a SQL query. Returns (cursor, lastrowid) if commit=True."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    
    lastrowid = cursor.lastrowid
    if commit:
        conn.commit()
        cursor.close()
        conn.close()
        return lastrowid
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def fetch_one(sql, params=()):
    """Fetches a single row as a dictionary."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def fetch_all(sql, params=()):
    """Fetches all rows as a list of dictionaries."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
