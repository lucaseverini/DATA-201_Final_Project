#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/etl_control_view.py

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox, QMainWindow
from models.etl_model import load_csv_to_staging, trigger_etl_job, fetch_etl_log
from models.etl_model import get_staging_columns, fetch_dead_letter
import pandas as pd
import os

class ETLControlView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETL Control Panel")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # CSV File Selection
        self.file_label = QLabel("No file selected")
        self.select_button = QPushButton("Select CSV File")
        self.select_button.clicked.connect(self.select_file)
        self.upload_button = QPushButton("Upload CSV File to Staging")
        self.upload_button.clicked.connect(self.upload_file)

        self.layout.addWidget(self.select_button)
        self.layout.addWidget(self.file_label)
        self.layout.addWidget(self.upload_button)

        # Trigger ETL Job
        self.etl_button = QPushButton("Trigger ETL Job")
        self.etl_button.clicked.connect(self.run_etl)
        self.layout.addWidget(self.etl_button)

        # ETL Log
        self.log_label = QLabel("ETL Job Log")
        self.log_table = QTableWidget()
        self.refresh_log_button = QPushButton("Refresh Log")
        self.refresh_log_button.clicked.connect(self.load_etl_log)

        self.layout.addWidget(self.log_label)
        self.layout.addWidget(self.log_table)
        self.layout.addWidget(self.refresh_log_button)

        # Dead Letter Table
        self.dlq_label = QLabel("ETL Dead Letter Records")
        self.dlq_table = QTableWidget()
        self.refresh_dlq_button = QPushButton("Refresh Dead Letters")
        self.refresh_dlq_button.clicked.connect(self.load_dead_letters)

        self.layout.addWidget(self.dlq_label)
        self.layout.addWidget(self.dlq_table)
        self.layout.addWidget(self.refresh_dlq_button)

        self.csv_path = None
        self.resize(1000, 600)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if path:
            self.csv_path = path
            filename = os.path.basename(path)
            self.file_label.setText(f"Selected: {filename}")
            self.upload_button.setText(f"Upload {filename} to staging")

    def upload_file(self):
        if not self.csv_path:
            QMessageBox.warning(self, "No File", "Please select a CSV file first.")
            return
        try:
            df = pd.read_csv(self.csv_path, encoding='latin1')  # match notebook behavior

            # Apply exact column renaming as in notebook
            df.columns = (
                df.columns
                .str.replace('>', '_2_5O', regex=False)
                .str.replace('<', '_2_5U', regex=False)
                .str.replace('.', '_', regex=False)
                .str.strip()
            )

            # Drop columns not in DB table, just like notebooks did manually
            from models.etl_model import get_staging_columns
            valid_cols = get_staging_columns()
            df = df[[col for col in df.columns if col in valid_cols]]

            # Fix European-style date format to standard ISO
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
            df['Time'] = pd.to_datetime(df['Time'], format='%H:%M', errors='coerce').dt.time

            # Load cleaned DataFrame into staging
            load_csv_to_staging(df)
            
            QMessageBox.information(self, "Success", "CSV loaded to staging table.")
            
        except Exception as e:
            QMessageBox.critical(self, "Upload Failed", str(e))

    def run_etl(self):
        try:
            result = trigger_etl_job()
            QMessageBox.information(self, "ETL Status", result)

            mw = self.window()
            if isinstance(mw, QMainWindow) and hasattr(mw, 'league_action'):
                from models.etl_model import has_season_data
                mw.league_action.setEnabled(has_season_data())
               
        except Exception as e:
            QMessageBox.critical(self, "ETL Error", str(e))

    def load_etl_log(self):
        data = fetch_etl_log()        
        if not data:
            self.log_table.clear()
            self.log_table.setRowCount(0)
            self.log_table.setColumnCount(0)
            return

        self.log_table.setColumnCount(len(data[0]))
        self.log_table.setRowCount(len(data))
        self.log_table.setHorizontalHeaderLabels(data[0].keys())
        for i, row in enumerate(data):
            for j, key in enumerate(row):
                self.log_table.setItem(i, j, QTableWidgetItem(str(row[key])))

    def load_dead_letters(self):
        data = fetch_dead_letter()
        if not data:
            QMessageBox.information(self, "No Dead Letters", "No dead-letter records found.")
            self.dlq_table.setRowCount(0)
            self.dlq_table.setColumnCount(0)
            return

        self.dlq_table.setColumnCount(len(data[0]))
        self.dlq_table.setRowCount(len(data))
        self.dlq_table.setHorizontalHeaderLabels(data[0].keys())

        for i, row in enumerate(data):
            for j, key in enumerate(row):
                self.dlq_table.setItem(i, j, QTableWidgetItem(str(row[key])))

