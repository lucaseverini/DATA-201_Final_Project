#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

from db.connection import get_connection
import pandas as pd
from datetime import datetime

def load_csv_to_staging(df: pd.DataFrame):
    """
    Load a DataFrame into the stg_premier_league_raw table.
    Only supports rows with matching column names.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Validate columns before attempting insert
    cursor.execute("SHOW COLUMNS FROM stg_premier_league_raw")
    db_columns = set(row[0] for row in cursor.fetchall())

    csv_columns = set(df.columns)

    missing = csv_columns - db_columns
    if missing:
        raise RuntimeError(f"CSV contains unknown columns: {', '.join(sorted(missing))}")
        
    cols = ', '.join([f"`{col}`" for col in df.columns])
    placeholders = ', '.join(['%s'] * len(df.columns))
    insert_sql = f"""
        INSERT INTO stg_premier_league_raw ({cols})
        VALUES ({placeholders})
    """

    data = [tuple(row) for row in df.to_numpy()]
    cursor.executemany(insert_sql, data)
    conn.commit()

    cursor.close()
    conn.close()
        
def trigger_etl_job():
    conn = get_connection()
    cursor = conn.cursor(buffered=True)
    log_id = None

    try:
        # Step 0: Insert ETLLog entry
        start_time = datetime.now()
        cursor.execute("""
            INSERT INTO ETLLog (ProcessName, StartTime, Status)
            VALUES (%s, %s, %s)
        """, ("GUI ETL Job", start_time, "Running"))
        log_id = cursor.lastrowid
        conn.commit()

        summary = []

        # Step 1: Teams
        cursor.execute("""
            SELECT DISTINCT HomeTeam FROM stg_premier_league_raw
            UNION
            SELECT DISTINCT AwayTeam FROM stg_premier_league_raw
        """)
        teams = [row[0] for row in cursor.fetchall()]
        insert_sql = """
            INSERT IGNORE INTO Teams (TeamName, ShortName)
            VALUES (%s, %s)
        """
        data = [(team, team[:12]) for team in teams]
        cursor.executemany(insert_sql, data)
        summary.append(f"{len(data)} team records processed.")

        # Step 2: Seasons
        cursor.execute("SELECT MIN(Date), MAX(Date) FROM stg_premier_league_raw")
        min_date, max_date = cursor.fetchone()
        sy, ey = min_date.year % 100, max_date.year % 100
        season_name = f"{sy:02d}-{ey:02d}"
        cursor.execute("""
            INSERT IGNORE INTO Seasons (SeasonName, StartDate, EndDate)
            VALUES (%s, %s, %s)
        """, (season_name, min_date, max_date))
        summary.append(f"Season '{season_name}' inserted or already present.")

        # Step 3: Referees
        cursor.execute("""
            SELECT DISTINCT Referee
            FROM stg_premier_league_raw
            WHERE Referee IS NOT NULL AND Referee <> ''
        """)
        referees = [row[0] for row in cursor.fetchall()]
        insert_sql = """
            INSERT IGNORE INTO Referees (RefereeName, YearsExperience, Nationality)
            VALUES (%s, %s, %s)
        """
        ref_data = [(ref, None, None) for ref in referees]
        cursor.executemany(insert_sql, ref_data)
        summary.append(f"{len(ref_data)} referees processed.")

        # Step 4: Divisions
        cursor.execute("""
            SELECT DISTINCT `Div`
            FROM stg_premier_league_raw
            WHERE `Div` IS NOT NULL AND `Div` <> ''
        """)
        divisions = [row[0] for row in cursor.fetchall()]
        insert_sql = """
            INSERT IGNORE INTO Divisions (DivisionCode, LeagueName, Country, Tier)
            VALUES (%s, %s, %s, %s)
        """
        div_data = [(div, "Premier League", "England", 1) for div in divisions]
        cursor.executemany(insert_sql, div_data)
        summary.append(f"{len(div_data)} divisions processed.")

        # Step 5: Matches
        cursor.execute("""
            SELECT Date, Time, `Div`, HomeTeam, AwayTeam, FTHG, FTAG, FTR,
                   HTHG, HTAG, HTR, Referee
            FROM stg_premier_league_raw
            ORDER BY Date, Time
        """)
        rows = cursor.fetchall()
        match_data = []

        for row in rows:
            match_date, match_time, div_code, home_name, away_name, fthg, ftag, ftr, hthg, htag, htr, ref_name = row

            cursor.execute("SELECT SeasonID FROM Seasons ORDER BY StartDate DESC LIMIT 1")
            season_id = cursor.fetchone()[0]

            cursor.execute("SELECT DivisionID FROM Divisions WHERE DivisionCode = %s", (div_code,))
            division_id = cursor.fetchone()[0]

            cursor.execute("SELECT TeamID FROM Teams WHERE TeamName = %s", (home_name,))
            home_id = cursor.fetchone()[0]

            cursor.execute("SELECT TeamID FROM Teams WHERE TeamName = %s", (away_name,))
            away_id = cursor.fetchone()[0]

            cursor.execute("SELECT RefereeID FROM Referees WHERE RefereeName = %s", (ref_name,))
            ref_row = cursor.fetchone()
            referee_id = ref_row[0] if ref_row else None

            match_data.append((
                season_id, division_id, match_date, match_time,
                home_id, away_id,
                fthg, ftag, ftr,
                hthg, htag, htr,
                referee_id
            ))

        insert_sql = """
            INSERT IGNORE INTO Matches (
                SeasonID, DivisionID, MatchDate, MatchTime,
                HomeTeamID, AwayTeamID,
                FTHG, FTAG, FTR,
                HTHG, HTAG, HTR,
                RefereeID
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s
            )
        """
        cursor.executemany(insert_sql, match_data)
        conn.commit()
        summary.append(f"{len(match_data)} matches inserted.")

        # Step 6: MatchStatistics
        cursor.execute("""
            SELECT Date, Time, HomeTeam, AwayTeam,
                   HS, `AS`, HST, AST, HC, AC, HF, AF, HY, AY, HR, AR
            FROM stg_premier_league_raw
            ORDER BY Date, Time
        """)
        stat_rows = cursor.fetchall()
        stat_data = []

        for row in stat_rows:
            match_date, match_time, home_name, away_name, *stats = row

            cursor.execute("""
                SELECT MatchID
                FROM Matches
                WHERE MatchDate = %s AND MatchTime = %s
                  AND HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                  AND AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
            """, (match_date, match_time, home_name, away_name))

            match_row = cursor.fetchone()
            if not match_row:
                continue

            match_id = match_row[0]
            stat_data.append((match_id, *stats))

        insert_sql = """
            INSERT IGNORE INTO MatchStatistics (
                MatchID,
                HomeShots, AwayShots,
                HomeShotsTarget, AwayShotsTarget,
                HomeCorners, AwayCorners,
                HomeFouls, AwayFouls,
                HomeYellowCards, AwayYellowCards,
                HomeRedCards, AwayRedCards
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """
        cursor.executemany(insert_sql, stat_data)
        conn.commit()
        summary.append(f"{len(stat_data)} match statistics inserted.")

        # Step 7: Log ETL success
        end_time = datetime.now()
        cursor.execute("""
            UPDATE ETLLog
            SET EndTime = %s,
                RecordsProcessed = %s,
                Status = %s,
                ErrorMessage = NULL
            WHERE LogID = %s
        """, (end_time, len(match_data), "Completed", log_id))
        conn.commit()

        # Step 8: insert Market definitions
        insert_market_sql = """
            INSERT IGNORE INTO Markets (MarketType, MarketSubtype, Parameter, Description)
            VALUES (%s, %s, %s, %s)
        """
        market_data = [
            ("1X2", "FullTime", "standard", "Full-time result: Home/Draw/Away"),
            ("OverUnder", "FullTime", "2.5", "Over/Under 2.5 total goals")
        ]
        cursor.executemany(insert_market_sql, market_data)
        conn.commit()
        summary.append(f"{len(market_data)} market definitions inserted.")
                
        # Step 9: Insert Bookmakers and fetch IDs
        bookmaker_map = {
            "Bet365": ("B365H", "B365D", "B365A"),
            "Bet&Win": ("BWH", "BWD", "BWA"),
            "Interwetten": ("IWH", "IWD", "IWA"),
            "Pinnacle Sports": ("PSH", "PSD", "PSA")
        }

        insert_bookmaker_sql = "INSERT IGNORE INTO Bookmakers (BookmakerName) VALUES (%s)"
        for name in bookmaker_map:
            cursor.execute(insert_bookmaker_sql, (name,))
        conn.commit()
    
        # Get IDs
        bookmaker_ids = {}
        for name in bookmaker_map:
            cursor.execute("SELECT BookmakerID FROM Bookmakers WHERE BookmakerName = %s", (name,))
            bookmaker_ids[name] = cursor.fetchone()[0]

        # Step 10: Get MarketID for 1X2 FullTime
        cursor.execute("""
            SELECT MarketID FROM Markets
            WHERE MarketType = %s AND MarketSubtype = %s AND Parameter = %s
        """, ("1X2", "FullTime", "standard"))
        # market_id = cursor.fetchone()[0]
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Market '1X2 / FullTime' not found in Markets table.")
        market_id = row[0]

        # Step 11: Insert BettingOdds
        cursor.execute("""
            SELECT MatchID, B365H, B365D, B365A, BWH, BWD, BWA, IWH, IWD, IWA, PSH, PSD, PSA
            FROM Matches m
            JOIN stg_premier_league_raw s
              ON m.MatchDate = s.Date AND m.MatchTime = s.Time
             AND m.HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = s.HomeTeam)
             AND m.AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = s.AwayTeam)
        """)
        rows = cursor.fetchall()

        odds_data = []
        for row in rows:
            match_id = row[0]
            field_values = row[1:]

            for i, (bookmaker, fields) in enumerate(bookmaker_map.items()):
                h, d, a = field_values[i*3:i*3+3]
                b_id = bookmaker_ids[bookmaker]

                if h and h > 1.0:
                    odds_data.append((match_id, b_id, market_id, "H", h))
                if d and d > 1.0:
                    odds_data.append((match_id, b_id, market_id, "D", d))
                if a and a > 1.0:
                    odds_data.append((match_id, b_id, market_id, "A", a))

        insert_odds_sql = """
            INSERT IGNORE INTO BettingOdds (
                MatchID, BookmakerID, MarketID, OutcomeCode, OddsValue
            ) VALUES (%s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_odds_sql, odds_data)
        conn.commit()
        summary.append(f"{len(odds_data)} 1X2 odds inserted.")

        # Step 12: Insert Over/Under 2.5 odds
        # Get MarketID for Over/Under 2.5
        cursor.execute("""
            SELECT MarketID FROM Markets
            WHERE MarketType = %s AND MarketSubtype = %s AND Parameter = %s
        """, ("OverUnder", "FullTime", "2.5"))
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Over/Under 2.5 market not found in Markets table.")
        ou_market_id = row[0]

        # Bookmaker to columns mapping
        ou_map = {
            "Bet365": ("B365_2_5O", "B365_2_5U"),
            "Pinnacle Sports": ("P_2_5O", "P_2_5U")
        }

        # Build SELECT dynamically
        all_columns = ["MatchID"]
        for pair in ou_map.values():
            all_columns.extend(pair)

        select_clause = ", ".join(set(all_columns))
        cursor.execute(f"""
            SELECT {select_clause}
            FROM Matches m
            JOIN stg_premier_league_raw s
              ON m.MatchDate = s.Date AND m.MatchTime = s.Time
             AND m.HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = s.HomeTeam)
             AND m.AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = s.AwayTeam)
        """)
        rows = cursor.fetchall()

        ou_odds = []
        for row in rows:
            match_id = row[0]
            values = row[1:]

            for i, (bookmaker, (col_over, col_under)) in enumerate(ou_map.items()):
                over = row[1 + list(ou_map.values()).index((col_over, col_under)) * 2]
                under = row[1 + list(ou_map.values()).index((col_over, col_under)) * 2 + 1]
                b_id = bookmaker_ids[bookmaker]

                if over and over > 1.0:
                    ou_odds.append((match_id, b_id, ou_market_id, "Over", over))
                if under and under > 1.0:
                    ou_odds.append((match_id, b_id, ou_market_id, "Under", under))

        insert_ou_sql = """
            INSERT IGNORE INTO BettingOdds (
                MatchID, BookmakerID, MarketID, OutcomeCode, OddsValue
            ) VALUES (%s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_ou_sql, ou_odds)
        conn.commit()
        summary.append(f"{len(ou_odds)} Over/Under 2.5 odds inserted.")
                
        return "\n".join(summary)

    except Exception as e:
        conn.rollback()
        end_time = datetime.now()
        if log_id:
            cursor.execute("""
                UPDATE ETLLog
                SET EndTime = %s,
                    RecordsProcessed = 0,
                    RecordsFailed = 1,
                    Status = %s,
                    ErrorMessage = %s
                WHERE LogID = %s
            """, (end_time, "Failed", str(e), log_id))
            conn.commit()
        raise RuntimeError(f"ETL error: {str(e)}")

    finally:
        cursor.close()
        conn.close()
    conn = get_connection()
    cursor = conn.cursor()
    log_id = None
    
    try:
        # Step 0: log start of ETL
        start_time = datetime.now()
        cursor.execute("""
            INSERT INTO ETLLog (ProcessName, StartTime, Status)
            VALUES (%s, %s, %s)
        """, ("GUI ETL Job", start_time, "Running"))
        log_id = cursor.lastrowid
        conn.commit()

        # Step 1–8: [All your current ETL logic goes here, unchanged except for return string moved below]
        # We'll accumulate messages and counts:
        summary = []

        # ... team insert ...
        summary.append(f"{len(data)} team records processed.")

        # ... season insert ...
        summary.append(f"Season '{season_name}' inserted or already present.")

        # ... referees ...
        summary.append(f"{len(ref_data)} referees processed.")

        # ... divisions ...
        summary.append(f"{len(div_data)} divisions processed.")

        # ... matches ...
        summary.append(f"{len(match_data)} matches inserted.")

        # ... match statistics ...
        summary.append(f"{len(stat_data)} match statistics inserted.")

        # Step 9: log success
        end_time = datetime.now()
        cursor.execute("""
            UPDATE ETLLog
            SET EndTime = %s,
                RecordsProcessed = %s,
                Status = %s,
                ErrorMessage = NULL
            WHERE LogID = %s
        """, (end_time, len(match_data), "Completed", log_id))
        conn.commit()

        return "\n".join(summary)

    except Exception as e:
        conn.rollback()
        end_time = datetime.now()
        if log_id:
            cursor.execute("""
                UPDATE ETLLog
                SET EndTime = %s,
                    RecordsProcessed = 0,
                    RecordsFailed = 1,
                    Status = %s,
                    ErrorMessage = %s
                WHERE LogID = %s
            """, (end_time, "Failed", str(e), log_id))
            conn.commit()
        raise RuntimeError(f"ETL error: {str(e)}")

    finally:
        cursor.close()
        conn.close()

def fetch_etl_log():
    """
    Fetch recent ETL job logs from the ETLLog table.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT LogID, ProcessName, StartTime, EndTime, RecordsProcessed, RecordsFailed, Status, ErrorMessage
        FROM ETLLog
        ORDER BY StartTime DESC
    """)
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results

def fetch_dead_letter():
    """
    Fetch recent dead-letter records from ETLDeadLetter table.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT Id, SourceTable, SourceId, ErrorMessage, ErrorTimestamp
        FROM ETLDeadLetter
        ORDER BY ErrorTimestamp DESC
    """)
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results

def clean_all_tables():
    """
    Truncate staging and operational tables in the correct dependency order.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        tables = [
            "MatchStatistics",
            "Matches",
            "BettingOdds",
            "Markets",
            "Referees",
            "Teams",
            "Divisions",
            "Seasons",
            "stg_premier_league_raw"
        ]

        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table}")

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error cleaning tables: {str(e)}")

    finally:
        cursor.close()
        conn.close()

def get_staging_columns():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM stg_premier_league_raw")
    cols = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return cols

def has_season_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Seasons")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0

def clear_etl_logs():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("TRUNCATE TABLE ETLLog")
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error clearing logs: {str(e)}")

    finally:
        cursor.close()
        conn.close()

def get_all_referees():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT RefereeName FROM Referees ORDER BY RefereeName")
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

def get_referee_stats(season_name, referee_name):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT COUNT(ms.MatchID) AS Matches,
                   SUM(ms.HomeYellowCards + ms.AwayYellowCards) / COUNT(ms.MatchID) AS AvgYellow,
                   SUM(ms.HomeRedCards + ms.AwayRedCards) / COUNT(ms.MatchID) AS AvgRed,
                   SUM(ms.HomeFouls + ms.AwayFouls) / COUNT(ms.MatchID) AS AvgFouls
            FROM MatchStatistics ms
            JOIN Matches m ON ms.MatchID = m.MatchID
            JOIN Seasons s ON m.SeasonID = s.SeasonID
            JOIN Referees r ON m.RefereeID = r.RefereeID
            WHERE s.SeasonName = %s AND r.RefereeName = %s
        """, (season_name, referee_name))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def get_all_seasons():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT SeasonName FROM Seasons ORDER BY StartDate DESC")
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

def get_referee_trend_stats(season_name, referee_name):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT m.MatchDate,
                   ms.HomeYellowCards, ms.AwayYellowCards,
                   ms.HomeRedCards, ms.AwayRedCards,
                   ms.HomeFouls, ms.AwayFouls
            FROM MatchStatistics ms
            JOIN Matches m ON ms.MatchID = m.MatchID
            JOIN Referees r ON m.RefereeID = r.RefereeID
            JOIN Seasons s ON m.SeasonID = s.SeasonID
            WHERE r.RefereeName = %s AND s.SeasonName = %s
            ORDER BY m.MatchDate
        """, (referee_name, season_name))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
