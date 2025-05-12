#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

from PyQt5.QtWidgets import QMainWindow, QAction, QMenu, QApplication, QMessageBox, QWidget
from views.league_table_view import LeagueTableView
from views.etl_control_view import ETLControlView
from models.etl_model import clean_all_tables, has_season_data, clear_etl_logs

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

    def set_central_widget(self, widget):
        if self.current_widget:
            self.current_widget.setParent(None)
        self.current_widget = widget
        self.setCentralWidget(widget)

    def show_league_table(self):
        self.set_central_widget(LeagueTableView())

    def show_etl_control(self):
        if not hasattr(self, "etl_control") or self.etl_control is None:
            self.etl_control = ETLControlView()
        self.set_central_widget(self.etl_control)
    
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

