#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# test.py

import os
import sys
import math
import pandas as pd
from data201 import GREEN, BOLD, RESET
from connection import get_connection

TABLE_NAME = "stg_test"

# === Optional: create table (run once) ===
def create_sql_table(conn, columns):
    cursor = conn.cursor()
    
    # Drop table if it exists
    drop_query = f"DROP TABLE IF EXISTS `{TABLE_NAME}`;"
    cursor.execute(drop_query)

     # Create table
    columns_sql = ",\n".join(f"`{col}` TEXT" for col in columns)
    query = f"CREATE TABLE IF NOT EXISTS `{TABLE_NAME}` (`id` INT PRIMARY KEY AUTO_INCREMENT, {columns_sql});"
    print(f"Query: {query}")
    cursor.execute(query)
    conn.commit()

# === Import one CSV file ===
def import_pl_csv(conn, columns, file_path):
    print(f"{BOLD}Processing file: {file_path}{RESET}")
    
    bad_rows = 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if line.count(",") > 60:  # 57 expected columns = ~56 commas
                    # print(f"⚠️ Line {i} might be malformed ({line.count(',')} commas)")
                    # print(line.strip())
                    bad_rows += 1
                    
    except UnicodeDecodeError as e:
        print(f"❌ Skipping file: encoding error: {e}\n")
        return
                
    if bad_rows > 0:
        # print(f"❌ Skipping malformed file")
        # return
        print(f"⚠️ Possibly malformed file: {bad_rows} rows")
    
    # df = pd.read_csv(file_path)
    # df = pd.read_csv(file_path, on_bad_lines='warn')  # for pandas >= 1.3
    df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="warn")  # or encoding="windows-1252"
    
    # Rename normalized columns in file
    schema_df = pd.read_csv("stg_columns.csv")
    column_map = dict(zip(schema_df["Original Column"], schema_df["Normalized Column"]))
    if column_map:
        df.rename(columns=column_map, inplace=True)
        print(f"File column names normalized: {column_map}")

    initial_len = len(df)
    
    # 1. Drop rows that are completely empty
    df_cleaned = df.dropna(how='all')
    if len(df_cleaned) < len(df):
        print(f"⚠️ Dropped {len(df) - len(df_cleaned)} fully empty rows.")
    df = df_cleaned

    # 2. Drop rows where *critical identifying columns* are missing (e.g., no match date or teams)
    df_cleaned = df.dropna(subset=["Date", "HomeTeam", "AwayTeam"], how='any')
    if len(df_cleaned) < len(df):
        print(f"⚠️ Dropped {len(df) - len(df_cleaned)} rows missing Date, HomeTeam, or AwayTeam.")
    df = df_cleaned

    # 3. Optionally strip whitespace from column names (helps avoid accidental mismatches)
    original_columns = df.columns.tolist()
    df.columns = df.columns.str.strip()
    if df.columns.tolist() != original_columns:
        print("⚠️ Stripped whitespace from column names.")   
 
    # print("🧪 Columns in file:", list(df.columns))
    
    if df.columns.isnull().any():
        print("⚠️ CSV file contains unnamed (NaN) columns — dropping them.")
    
    # Check for missing columns in file
    missing_cols_in_file = set(columns) - set(df.columns)
    if missing_cols_in_file:
        print(f"⚠️ Missing {len(missing_cols_in_file)} columns in file: {sorted(missing_cols_in_file)}")

    # Check for missing columns in table
    cursor = conn.cursor()
    cursor.execute(f"SHOW COLUMNS FROM `{TABLE_NAME}`;")
    table_cols = set(row[0] for row in cursor.fetchall())
    missing_cols_in_table = set(columns) - table_cols
    if missing_cols_in_table:
        print(f"❌ Missing {len(missing_cols_in_table)} columns in table '{TABLE_NAME}': {sorted(missing_cols_in_table)}")

    # Use only the columns available in both schema and table
    # available_columns = [col for col in columns if col in table_cols]
    available_columns = [col for col in columns if col in table_cols and isinstance(col, str) and col.strip().lower() != "nan"]
    if any(col.strip().lower() == "nan" or not col for col in available_columns):
        print(f"❌ Invalid column name found in available_columns: {available_columns}")
    
    # Warn if extra columns are present in table but not in the expected schema
    extra_in_table = table_cols - set(available_columns) - {"id"}
    if extra_in_table:
        print(f"⚠️ Table '{TABLE_NAME}' contains {len(extra_in_table)} columns not in the schema: {sorted(extra_in_table)}")
    
    # Ensure all expected columns are present (add NaN if missing)
    for col in available_columns:
        if col not in df.columns:
            df[col] = None

    # Reorder and trim extra columns
    df = df[available_columns]

    # Check for missing values per row
    missing_by_row = df.isnull().sum(axis=1)
    rows_with_missing = df[missing_by_row > 0]
    if not rows_with_missing.empty:
        print(f"⚠️ Found {len(rows_with_missing)} rows with missing values.")
        
    # Ensure full output without truncation
    with pd.option_context('display.max_columns', None,
                           'display.max_rows', None,
                           'display.max_colwidth', None,
                           'display.width', 1000):
        print(rows_with_missing.head(3))
        
    # Manually insert rows using parameterized SQL
    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join(f"`{col}`" for col in columns)
    insert_sql = f"INSERT INTO `{TABLE_NAME}` ({col_names}) VALUES ({placeholders})"
     # print(f"Query: {insert_sql}")
        
    # Unsanitized values
    bad_values = df.where(pd.notnull(df), None).values.tolist()  # Convert NaN to None
    
    # Sanitized values to be imported
    def sanitize(row):
        return [None if (isinstance(x, float) and math.isnan(x)) else x for x in row]
    values = [sanitize(row) for row in df.values.tolist()]

    # Compared Unsanitized and values
    for i, (bad_row, good_row) in enumerate(zip(bad_values, values)):
        for j, (bad_val, good_val) in enumerate(zip(bad_row, good_row)):
            if bad_val != good_val:
                print(f"🔍 Row {i}, Column {available_columns[j]}: bad = {bad_val!r}, good = {good_val!r}") 
                  
    '''
    print(f"🧪 Number of rows to insert: {len(values)}")
    print(f"🧪 Any None rows? {[i for i, row in enumerate(values) if row is None]}")
    print(f"🧪 Check column names for literal 'nan':", [col for col in available_columns if col.lower() == 'nan'])

    for row_index, row in enumerate(values):
        if len(row) != len(available_columns):
            print(f"❌ Row {row_index} has {len(row)} values but {len(available_columns)} columns.")
            break

    for i, row in enumerate(values):
        for j, v in enumerate(row):
            if isinstance(v, str) and v.strip().lower() == "nan":
                print(f"❌ String 'nan' found at row {i}, column {available_columns[j]}")
                break
    '''
        
    cursor = conn.cursor()
    cursor.executemany(insert_sql, values)
    conn.commit()

    print(f"✅ Imported {len(df)} rows into table '{TABLE_NAME}'\n")

def main():   

    # === Load the schema reference ===
    schema_df = pd.read_csv("stg_columns.csv")
    normalized_columns = schema_df["Normalized Column"].tolist()

    # === Initialize database connection ===
    conn = get_connection()
    
    create_sql_table(conn, normalized_columns)

    import_pl_csv(conn, normalized_columns, "PL00-01.csv")
    import_pl_csv(conn, normalized_columns, "PL01-02.csv")
    import_pl_csv(conn, normalized_columns, "PL02-03.csv")
    import_pl_csv(conn, normalized_columns, "PL03-04.csv")
    import_pl_csv(conn, normalized_columns, "PL04-05.csv")
    import_pl_csv(conn, normalized_columns, "PL05-06.csv")
    import_pl_csv(conn, normalized_columns, "PL06-07.csv")
    import_pl_csv(conn, normalized_columns, "PL07-08.csv")
    import_pl_csv(conn, normalized_columns, "PL08-09.csv")
    import_pl_csv(conn, normalized_columns, "PL09-10.csv")
    import_pl_csv(conn, normalized_columns, "PL10-11.csv")
    import_pl_csv(conn, normalized_columns, "PL11-12.csv")
    import_pl_csv(conn, normalized_columns, "PL12-13.csv")
    import_pl_csv(conn, normalized_columns, "PL13-14.csv")
    import_pl_csv(conn, normalized_columns, "PL14-15.csv")
    import_pl_csv(conn, normalized_columns, "PL15-16.csv")
    import_pl_csv(conn, normalized_columns, "PL16-17.csv")
    import_pl_csv(conn, normalized_columns, "PL17-18.csv")
    import_pl_csv(conn, normalized_columns, "PL18-19.csv")
    import_pl_csv(conn, normalized_columns, "PL19-20.csv")
    import_pl_csv(conn, normalized_columns, "PL20-21.csv")
    import_pl_csv(conn, normalized_columns, "PL21-22.csv")
    import_pl_csv(conn, normalized_columns, "PL22-23.csv")
    import_pl_csv(conn, normalized_columns, "PL23-24.csv")

    conn.close()
    
    print(f"{GREEN}{BOLD}", end="")
    print(f"\nDone.")
    print(f"{RESET}", end="")

    sys.exit(0)

def handle_interrupt():
    print(f"{BOLD}\nProgram interrupted.{RESET}")
    # QApplication.quit()
    sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    
    except KeyboardInterrupt:
        print(f"{BOLD}", end="")
        print("\nProgram interrupted.")
        print(f"{RESET}", end="")
        
        sys.exit(1)
        