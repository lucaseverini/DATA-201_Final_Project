#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/main_window.py

from PyQt5.QtWidgets import QMainWindow, QAction, QMenu, QApplication, QMessageBox, QWidget
from views.league_table_view import LeagueTableView
from views.etl_control_view import ETLControlView
from models.etl_model import clean_all_tables, has_season_data, clear_etl_logs
from views.visualization_view import VisualizationView
from views.referee_stats_view import RefereeStatsView
from views.team_trend_view import TeamTrendView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Premier League DB Manager")

        self.menu = self.menuBar()
        
        # Views menu
        self.view_menu = self.menu.addMenu("Views")

        self.league_action = QAction("League Table", self)
        self.league_action.triggered.connect(self.show_league_table)
        self.view_menu.addAction(self.league_action)
        self.league_action.setEnabled(has_season_data())

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

        # Utilities menu
        self.util_menu = self.menu.addMenu("Utilities")
        self.clean_action = QAction("Clean All Tables", self)
        self.clean_action.triggered.connect(self.clean_tables)
        self.util_menu.addAction(self.clean_action)
 
        self.clear_logs_action = QAction("Clear All Logs", self)
        self.clear_logs_action.triggered.connect(self.clear_logs)
        self.util_menu.addAction(self.clear_logs_action)
       
        self.current_widget = None
        
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
                self.league_action.setEnabled(False)
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
