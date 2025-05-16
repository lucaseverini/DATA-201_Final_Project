#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/league_table_view.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableWidget
from PyQt5.QtWidgets import QTableWidgetItem, QLabel, QComboBox, QMessageBox
from PyQt5.QtWidgets import QSizePolicy, QHeaderView
from models.etl_model import get_all_seasons, fetch_league_table

class LeagueTableView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Premier League Table")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.season_selector = QComboBox()
        self.season_selector.addItem("All Seasons")
        self.season_selector.addItems(get_all_seasons())  # dynamically populated
        self.season_selector.currentIndexChanged.connect(self.load_data)

        self.table = QTableWidget()
        self.table.setMinimumSize(0, 0)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(QLabel("Select Season:"))
        self.layout.addWidget(self.season_selector)
        self.layout.addWidget(self.table, stretch = 1)

        self.load_data()
        self.resize(1000, 600)

    def load_data(self):
        season = self.season_selector.currentText()
        if season == "All Seasons":
            data = fetch_league_table()
        else:
            data = fetch_league_table(season)

        if not data:
            QMessageBox.warning(self, "No Data", f"No data available for season: {season}")
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        self.table.setColumnCount(len(data[0]))
        self.table.setRowCount(len(data))
        self.table.setHorizontalHeaderLabels(data[0].keys())
        self.table.resizeColumnsToContents()

        for row_idx, row_data in enumerate(data):
            for col_idx, key in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(row_data[key])))
        
        # Set window size based on table content
        total_width = sum([self.table.columnWidth(i) for i in range(self.table.columnCount())]) + 40
        row_height = self.table.verticalHeader().defaultSectionSize()
        total_height = row_height * 20 + 80  # 20 rows + header + margins

        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        screen_width = screen.size().width()
        max_width = screen_width // 2

        final_width = min(total_width, max_width)
        self.resize(final_width, total_height)
 