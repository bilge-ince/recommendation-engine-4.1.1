import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_db_connection():
    """Create and return a database connection."""
    conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    password=os.getenv("DB_PASSWORD"),
    user=os.getenv("DB_USER"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)
    return conn