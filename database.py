import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def conectar():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except Exception as e:
        print("Erro na conexão com o banco:", e)
        return None
