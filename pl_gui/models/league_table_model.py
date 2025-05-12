#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# models/league_table_model.py

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

def get_league_table_data(season_name):
    """
    Return a list of team standings (dicts) for the given season.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT TeamName AS Team,
                   Played,
                   Won,
                   Drawn,
                   Lost,
                   GF,
                   GA,
                   GD AS GoalDifference,
                   Points
            FROM vw_LeagueTable
            WHERE SeasonName = %s
            ORDER BY Points DESC, GoalDifference DESC, GF DESC
        """, (season_name,))
        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()