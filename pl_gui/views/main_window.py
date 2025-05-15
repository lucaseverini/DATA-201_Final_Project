#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/main_window.py

from PyQt5.QtWidgets import QMainWindow, QAction, QMenu, QApplication
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QLineEdit, QLabel
from PyQt5.QtWidgets import QComboBox, QMessageBox
from PyQt5.QtWidgets import QWidget, QInputDialog, QFileDialog
from views.league_table_view import LeagueTableView
from views.etl_control_view import ETLControlView
from models.etl_model import clean_all_tables, has_season_data, clear_etl_logs
from models.etl_model import deduplicate_bookmakers
from views.visualization_view import VisualizationView
from views.referee_stats_view import RefereeStatsView
from views.team_trend_view import TeamTrendView
from views.odds_analysis_view import OddsAnalysisView
from dialogs.user_management_dialog import UserManagementDialog
from dialogs.login_dialog import LoginDialog
from db.connection import get_connection, get_db_config
import hashlib
import sys
import subprocess
from datetime import datetime

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Premier League DB Manager")

        self.menu = self.menuBar()

        # Just to check if the DB connection works
        get_connection()
        
        self.current_widget = None
        
        # Login
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            sys.exit(1)

        self.username = login_dialog.username
        self.role = login_dialog.role
        
        # Views menu
        self.view_menu = self.menu.addMenu("Views")

        self.league_action = QAction("League Table", self)
        self.league_action.triggered.connect(self.show_league_table)
        self.view_menu.addAction(self.league_action)
        # self.league_action.setEnabled(has_season_data())

        self.etl_action = QAction("ETL Control", self)
        self.etl_action.triggered.connect(self.show_etl_control)
        self.view_menu.addAction(self.etl_action)

        self.viz_action = QAction("Team Insights", self)
        self.viz_action.triggered.connect(self.show_visualizations)
        self.view_menu.addAction(self.viz_action)

        self.ref_stats_action = QAction("Referee Stats", self)
        self.ref_stats_action.triggered.connect(self.show_referee_stats)
        self.view_menu.addAction(self.ref_stats_action)

        self.team_trend_action = QAction("Team Trend", self)
        self.team_trend_action.triggered.connect(self.show_team_trend)
        self.view_menu.addAction(self.team_trend_action)

        self.odds_analysis_action = QAction("Odds Analysis", self)
        self.odds_analysis_action.triggered.connect(self.show_odds_analysis)
        self.view_menu.addAction(self.odds_analysis_action)

        # Utilities menu
        self.util_menu = self.menu.addMenu("Utilities")
        self.clean_action = QAction("Clean All Tables", self)
        self.clean_action.triggered.connect(self.clean_tables)
        self.util_menu.addAction(self.clean_action)
 
        self.clear_logs_action = QAction("Clear All Logs", self)
        self.clear_logs_action.triggered.connect(self.clear_logs)
        self.util_menu.addAction(self.clear_logs_action)

        self.dedup_bookmakers_action = QAction("Fix Duplicate Bookmakers", self)
        self.dedup_bookmakers_action.triggered.connect(self.fix_duplicate_bookmakers)
        self.util_menu.addAction(self.dedup_bookmakers_action)

        self.snapshot_save_action = QAction("Save DB Snapshot", self)
        self.snapshot_save_action.triggered.connect(self.save_snapshot)
        self.util_menu.addAction(self.snapshot_save_action)

        self.snapshot_restore_action = QAction("Restore DB Snapshot", self)
        self.snapshot_restore_action.triggered.connect(self.restore_snapshot)
        self.util_menu.addAction(self.snapshot_restore_action)

        self.util_menu.setEnabled(self.role in ["admin", "manager"])

        # Admin-only menu
        if self.role == "admin":
            self.admin_menu = self.menu.addMenu("Admin")
            self.user_mgmt_action = QAction("User Management", self)
            self.user_mgmt_action.triggered.connect(self.open_user_management)
            self.admin_menu.addAction(self.user_mgmt_action)
                       
        if has_season_data():
            self.show_league_table()
        else:
            self.show_etl_control()
            
        self.resize(1200, 700)

    def set_central_widget(self, widget, view_name=None):
        if self.current_widget:
            self.current_widget.setParent(None)
        self.current_widget = widget
        self.setCentralWidget(widget)

        title = "Premier League DB Manager"
        if view_name:
            title += f" — {view_name}"
        self.setWindowTitle(title)
            
    def clean_tables(self):
        reply = QMessageBox.question(
            self,
            "Confirm Clean",
            "This will delete all data from staging and operational tables. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                clean_all_tables()
                QMessageBox.information(self, "Success", "All relevant tables have been cleaned.")
                # Close League Table view if currently visible
                if isinstance(self.current_widget, LeagueTableView):
                    self.setCentralWidget(QWidget())  # replace with empty widget
                    self.current_widget = None
                
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def clear_logs(self):
        reply = QMessageBox.question(
            self,
            "Confirm Log Deletion",
            "This will permanently delete all ETL log entries. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                clear_etl_logs()
                if hasattr(self, "etl_control"):
                    self.etl_control.load_etl_log()
                QMessageBox.information(self, "Logs Cleared", "All ETL logs have been deleted.")
  
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def show_league_table(self):
        self.league_view = LeagueTableView()
        self.set_central_widget(self.league_view, "League Table")

    def show_etl_control(self):
        if not hasattr(self, "etl_control") or self.etl_control is None:
            self.etl_control = ETLControlView()
        self.set_central_widget(self.etl_control, "ETL Control")

    def show_visualizations(self):
        self.viz_view = VisualizationView()
        self.set_central_widget(self.viz_view, "Team Insights")

    def show_referee_stats(self):
        self.ref_stats_view = RefereeStatsView()
        self.set_central_widget(self.ref_stats_view, "Referee Stats")

    def show_team_trend(self):
        self.team_trend_view = TeamTrendView()
        self.set_central_widget(self.team_trend_view, "Team Trend")

    def show_odds_analysis(self):
        self.set_central_widget(OddsAnalysisView(), "Odds Analysis")

    def fix_duplicate_bookmakers(self):
        reply = QMessageBox.question(
            self,
            "Confirm Cleanup",
            "This will remove duplicate bookmaker names and reassign related odds.\n"
            "Do you want to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            msg = deduplicate_bookmakers()
            QMessageBox.information(self, "Cleanup Result", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
 
 
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def authenticate_user(self):
        username, ok1 = QInputDialog.getText(None, "Login", "Username:")
        if not ok1 or not username:
            return None, None
        password, ok2 = QInputDialog.getText(None, "Login", "Password:", QInputDialog.Password)
        if not ok2 or not password:
            return None, None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PasswordHash, Role FROM Users WHERE Username = %s", (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return None, None
        hash_db, role = row
        if hash_password(password) == hash_db:
            return username, role
        return None, None      
         
    def open_user_management(self):
        dlg = UserManagementDialog(self)
        dlg.exec_()

    def save_snapshot(self):
        conn = get_connection()
        db_name = conn.database
        conn.close()
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"DB_Snapshot_{timestamp}.sql"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save DB Snapshot",
            default_name,
            "SQL Files (*.sql)"
        )
        if not file_path:
            return

        try:
            config = get_db_config()
            cmd = [
                "mysqldump",
                f"-h{config['host']}",
                f"-P{config['port']}",
                f"-u{config['user']}",
                f"-p{config['password']}",
                config['database'],
            ]
            with open(file_path, "w") as f:
                subprocess.run(cmd, stdout=f, check=True)
            QMessageBox.information(self, "Success", f"Snapshot saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Snapshot Error", str(e))

    def restore_snapshot(self):
        conn = get_connection()
        db_name = conn.database
        conn.close()

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Restore DB Snapshot", "", "SQL Files (*.sql)"
        )
        if not file_path:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Restore",
            f"This will overwrite all data in '{db_name}'. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            config = get_db_config()
            cmd = [
                "mysql",
                f"-h{config['host']}",
                f"-P{config['port']}",
                f"-u{config['user']}",
                f"-p{config['password']}",
                config['database'],
            ]
            with open(file_path, "r") as f:
                subprocess.run(cmd, stdin=f, check=True)
            QMessageBox.information(self, "Restored", f"Snapshot loaded from:\n{file_path}")
        
            if has_season_data():
                self.show_league_table()
            else:
                self.show_etl_control()

        except Exception as e:
            QMessageBox.critical(self, "Restore Error", str(e))
