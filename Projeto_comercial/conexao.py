
import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def conectar():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "banco_v3_lab"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        autocommit=False,
    )


def consultar(sql, parametros=()):
    with conectar() as con, con.cursor(dictionary=True) as cur:
        cur.execute(sql, parametros)
        return cur.fetchall()


def consultar_um(sql, parametros=()):
    linhas = consultar(sql, parametros)
    return linhas[0] if linhas else None
