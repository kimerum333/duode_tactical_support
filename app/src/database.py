import sqlite3

DB_NAME = "duode-tactical-support.db"

def setup_database():
    """
    데이터베이스와 테이블을 초기 설정합니다.
    """

    conn =  sqlite3.connect(DB_NAME)
    cursor = conn.cursor()