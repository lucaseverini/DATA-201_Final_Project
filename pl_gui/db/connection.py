import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='seekrit',
        database='premier_league_analytics'
    )
