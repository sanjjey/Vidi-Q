import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/vidi_q")

def create_database():
    parsed = urlparse(DB_URL)
    user = parsed.username or "postgres"
    password = parsed.password or "postgres"
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    target_db = parsed.path.lstrip("/") or "vidi_q"

    print(f"Connecting to PostgreSQL server at {host}:{port} as user '{user}'...")
    try:
        # Connect to default postgres maintenance database
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database already exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{target_db}'")
        exists = cursor.fetchone()

        if exists:
            print(f"[SUCCESS] Database '{target_db}' already exists on PostgreSQL.")
        else:
            cursor.execute(f'CREATE DATABASE "{target_db}";')
            print(f"[SUCCESS] Database '{target_db}' created successfully on PostgreSQL!")

        cursor.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"\n[FAIL] Cannot connect to PostgreSQL server: {e}\n")
        print("Root cause: PostgreSQL server is not running on localhost:5432.")
        print("\nOptions:")
        print("1. Use Local SQLite (Zero setup):")
        print("   Database is ALREADY created at 'vidi_q_local.db' with all tables!")
        print("   Just run 'python server.py' to start working immediately.\n")
        print("2. Run PostgreSQL via Docker:")
        print("   - Start Docker Desktop")
        print("   - Run: docker run --name vidiq-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=vidi_q -p 5432:5432 -d postgres")
        print("   - Run: python create_postgres_db.py\n")

if __name__ == "__main__":
    create_database()
