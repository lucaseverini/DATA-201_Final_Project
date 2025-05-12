from models.league_table_model import fetch_league_table

def get_league_table(season=None):
    return fetch_league_table(season)
