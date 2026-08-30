import os
import sys
import mysql.connector
from werkzeug.security import generate_password_hash

# Add parent directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

def init_and_seed_db():
    print("Connecting to MySQL server...")
    try:
        # First connect without specifying database to create it if not exists
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Read schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Execute statements
        statements = schema_sql.split(';')
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database schema created/initialized successfully!")

        # Now connect to the database to insert seed data
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor(dictionary=True)

        # Check if users already exist
        cursor.execute("SELECT * FROM USER WHERE email = %s", ('teacher@college.edu',))
        if not cursor.fetchone():
            teacher_pass = generate_password_hash('teacher123')
            cursor.execute(
                "INSERT INTO USER (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ('Prof. Robert Smith', 'teacher@college.edu', teacher_pass, 'teacher')
            )
            print("Seeded Teacher Account: teacher@college.edu / teacher123")

        cursor.execute("SELECT * FROM USER WHERE email = %s", ('student@college.edu',))
        if not cursor.fetchone():
            student_pass = generate_password_hash('student123')
            cursor.execute(
                "INSERT INTO USER (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ('Alex Johnson', 'student@college.edu', student_pass, 'student')
            )
            user_id = cursor.lastrowid
            
            cursor.execute(
                "INSERT INTO STUDENT (user_id, roll_number, department, year) VALUES (%s, %s, %s, %s)",
                (user_id, 'CS2026-042', 'Computer Science & Engineering', 4)
            )
            print("Seeded Student Account: student@college.edu / student123")

        conn.commit()
        cursor.close()
        conn.close()
        print("Database seeding completed successfully!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    init_and_seed_db()
