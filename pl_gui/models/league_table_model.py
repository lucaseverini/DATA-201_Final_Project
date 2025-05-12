from db.connection import get_connection

def fetch_league_table(season=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = "SELECT * FROM vw_LeagueTable"
    if season:
        sql += " WHERE SeasonName = %s"
        cursor.execute(sql, (season,))
    else:
        cursor.execute(sql)

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def get_all_seasons():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SeasonName FROM Seasons ORDER BY StartDate DESC")
    seasons = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return seasons
