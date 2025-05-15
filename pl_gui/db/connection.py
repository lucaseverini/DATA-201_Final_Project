#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# db/connection.py

from PyQt5.QtWidgets import QMessageBox, QApplication
import os
import sys
import mysql.connector
import configparser

CONNECTION_FILE = "connection.ini"

def get_connection():
    config = configparser.ConfigParser()
 
    # First: try to load connection.ini from same directory as main.py
    # Second: fall back to current working directory
    try_main_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), CONNECTION_FILE)
    try_cwd_path = os.path.join(os.getcwd(), CONNECTION_FILE)
    ini_path = try_main_path if os.path.exists(try_main_path) else try_cwd_path

    # print(f"Connection configuration file: {ini_path}")

    if not os.path.exists(ini_path):
        fatal_message(f"Configuration file {CONNECTION_FILE} was not found.")

    config.read(ini_path)

    if "mysql" not in config:
        fatal_message(f"Section [mysql] not found in {CONNECTION_FILE}")

    db_cfg = config["mysql"]
    required = ["host", "port", "user", "password", "database"]

    for key in required:
        if key not in db_cfg:
            fatal_message(f"Missing '{key}' in [mysql] section of {CONNECTION_FILE}")

    return mysql.connector.connect(
        host=db_cfg["host"],
        port=int(db_cfg["port"]),
        user=db_cfg["user"],
        password=db_cfg["password"],
        database=db_cfg["database"],
    )

def get_db_config():
    config = configparser.ConfigParser()
    
    try_main_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), CONNECTION_FILE)
    try_cwd_path = os.path.join(os.getcwd(), CONNECTION_FILE)
    ini_path = try_main_path if os.path.exists(try_main_path) else try_cwd_path

    config.read(ini_path)
    return {
        "host": config["mysql"]["host"],
        "port": config["mysql"]["port"],
        "user": config["mysql"]["user"],
        "password": config["mysql"]["password"],
        "database": config["mysql"]["database"],
    }

def fatal_message(message):
    app = QApplication.instance() or QApplication(sys.argv)    
    box = QMessageBox()
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle("Startup Error")
    box.setText(message)
    box.setStandardButtons(QMessageBox.Ok)
    box.button(QMessageBox.Ok).setText("Quit")
    box.exec_()
    sys.exit(1)

 
'''
def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='seekrit',
        database='premier_league_analytics'
    )
'''
