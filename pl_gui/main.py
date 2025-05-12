#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

import sys
import signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from views.main_window import MainWindow
from views.league_table_view import LeagueTableView
from data201 import BOLD, RESET

def handle_interrupt():
    print(f"{BOLD}\nProgram interrupted.{RESET}")
    # QApplication.quit()
    sys.exit(1)

# Needed for clean Ctrl+C termination
signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ignore in Qt thread

app = QApplication(sys.argv)

# Reinstall signal handler in main thread
signal.signal(signal.SIGINT, lambda sig, frame: handle_interrupt())

# Dummy timer to keep the event loop processing signals
timer = QTimer()
timer.start(100)
timer.timeout.connect(lambda: None)

# window = LeagueTableView()
window = MainWindow()
window.show()

status = app.exec_()

print(f"{BOLD}Program quit.{RESET}")
sys.exit(status)
