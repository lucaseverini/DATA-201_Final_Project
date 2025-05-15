#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/team_trend_view.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QCheckBox, QSpinBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from models.etl_model import get_all_seasons, get_all_teams, get_team_match_trend_data
import os
import numpy as np
import csv
import mplcursors

class TeamTrendView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Team Performance Trend")

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Season
        self.season_selector = QComboBox()
        self.season_selector.addItems(get_all_seasons())
        self.layout.addWidget(QLabel("Select Season:"))
        self.layout.addWidget(self.season_selector)

        # Chart mode
        self.chart_mode = QComboBox()
        self.chart_mode.addItems([
            "Cumulative Points",
            "Goal Difference",
            "Goals For / Against",
            "Match Results (W / D / L)"
        ])
        self.chart_mode.currentIndexChanged.connect(self.update_mode_visibility)
        self.layout.addWidget(QLabel("Chart Type:"))
        self.layout.addWidget(self.chart_mode)

        # Chart mode
        self.chart_mode_selector = QComboBox()
        self.chart_mode_selector.addItems(["Single Team View", "Compare Two Teams"])
        self.chart_mode_selector.currentIndexChanged.connect(self.update_mode_visibility)
        self.chart_mode_label = QLabel("Chart Mode:")
        self.layout.addWidget(self.chart_mode_label)
        self.layout.addWidget(self.chart_mode_selector)

        # Team
        self.team_selector = QComboBox()
        self.team_selector.addItems(get_all_teams())
        self.layout.addWidget(QLabel("Select Team:"))
        self.layout.addWidget(self.team_selector)

        # Team 2
        self.team_selector_2 = QComboBox()
        self.team_selector_2.addItems(get_all_teams())
        self.team_label_2 = QLabel("Compare With Team:")
        self.team_label_2.hide()
        self.team_selector_2.hide()
        self.layout.addWidget(self.team_label_2)
        self.layout.addWidget(self.team_selector_2)
 
        # Smooth toggle + window
        self.smooth_checkbox = QCheckBox("Smooth Trend")
        self.smooth_checkbox.setChecked(False)
        self.smooth_checkbox.stateChanged.connect(self.toggle_smoothing_controls)
        self.layout.addWidget(self.smooth_checkbox)

        self.window_label = QLabel("Smoothing Window:")
        self.window_spin = QSpinBox()
        self.window_spin.setRange(1, 10)
        self.window_spin.setValue(3)
        self.layout.addWidget(self.window_label)
        self.layout.addWidget(self.window_spin)

        # Generate
        self.generate_button = QPushButton("Generate Chart")
        self.generate_button.clicked.connect(self.generate_chart)
        self.layout.addWidget(self.generate_button)

        # Chart canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas, stretch=1)

        # Export Chart
        self.export_button = QPushButton("Export Chart")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_chart)
        self.layout.addWidget(self.export_button)

        # Export Data
        self.export_data_button = QPushButton("Export Data (CSV)")
        self.export_data_button.setEnabled(False)
        self.export_data_button.clicked.connect(self.export_data)
        self.layout.addWidget(self.export_data_button)

        self.toggle_smoothing_controls()
        self.update_mode_visibility()

        self.season_selector.currentIndexChanged.connect(self.mark_generate_outdated)
        self.team_selector.currentIndexChanged.connect(self.mark_generate_outdated)
        self.chart_mode.currentIndexChanged.connect(self.mark_generate_outdated)
        self.chart_mode_selector.currentIndexChanged.connect(self.mark_generate_outdated)
        self.team_selector_2.currentIndexChanged.connect(self.mark_generate_outdated)
        self.smooth_checkbox.stateChanged.connect(self.mark_generate_outdated)
        self.window_spin.valueChanged.connect(self.mark_generate_outdated)

        self.last_export_dir = None
        self.latest_data = None
        self.export_mode = None

    def smooth_series(self, data, window):
        if len(data) < window:
            return data
        return np.convolve(data, np.ones(window)/window, mode='same')

    def update_mode_visibility(self):
        chart_type = self.chart_mode.currentText()
        compare_supported = (chart_type == "Cumulative Points")
    
        view_mode = self.chart_mode_selector.currentText()
        is_compare = compare_supported and (view_mode == "Compare Two Teams")
    
        self.chart_mode_label.setVisible(compare_supported)
        self.chart_mode_selector.setVisible(compare_supported)
        self.team_label_2.setVisible(is_compare)
        self.team_selector_2.setVisible(is_compare)
        
    def generate_chart(self):
        season = self.season_selector.currentText()
        team = self.team_selector.currentText()
        mode = self.chart_mode.currentText()
        view_mode = self.chart_mode_selector.currentText()

        data = get_team_match_trend_data(season, team)
        if not data:
            QMessageBox.information(self, "No Data", "No data available for this team and season.")
            return

        matchdays = list(range(1, len(data) + 1))

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if mode == "Cumulative Points":
            if view_mode == "Compare Two Teams":
                team2 = self.team_selector_2.currentText()
                
                if team == team2:
                    QMessageBox.warning(self, "Invalid Selection", "Please select two different teams for comparison.")
                    return
        
                data2 = get_team_match_trend_data(season, team2)
                if not data2:
                    QMessageBox.information(self, "No Data", f"No data for {team2}")
                    return

                points1 = [row["Points"] for row in data]
                points2 = [row["Points"] for row in data2]
                series1 = np.cumsum(points1)
                series2 = np.cumsum(points2)

                if self.smooth_checkbox.isChecked():
                    w = self.window_spin.value()
                    series1 = self.smooth_series(series1, w)
                    series2 = self.smooth_series(series2, w)

                md1 = list(range(1, len(series1) + 1))
                md2 = list(range(1, len(series2) + 1))

                ax.plot(md1, series1, marker='o', label=team, color='blue')
                ax.plot(md2, series2, marker='o', label=team2, color='green')
                ax.set_ylabel("Points")
                self.export_mode = "Compare-Points"
                self.latest_data = data  # Only exporting team 1 for now

            else:  # Single team view
                points = [row["Points"] for row in data]
                series = np.cumsum(points)

                if self.smooth_checkbox.isChecked():
                    series = self.smooth_series(series, self.window_spin.value())

                ax.plot(matchdays, series, marker='o', label="Cumulative Points")
                for i, row in enumerate(data):
                    row["Matchday"] = i + 1
                self.latest_data = data
                ax.set_ylabel("Points")
                self.export_mode = "Points"
                
            ax.set_title(f"{team} — {mode} ({season})")
                
        elif mode == "Goal Difference":
            gd = [row["GF"] - row["GA"] for row in data]

            if self.smooth_checkbox.isChecked():
                gd = self.smooth_series(gd, self.window_spin.value())

            ax.plot(matchdays, gd, marker='o', label="Goal Difference")
            self.latest_data = list(zip(matchdays, gd))
            ax.set_ylabel("Goal Diff")
            self.export_mode = "Goal-Diff"
            ax.set_title(f"{team} — {mode} ({season})")

        elif mode == "Goals For / Against":
            gf = [row["GF"] for row in data]
            ga = [row["GA"] for row in data]

            if self.smooth_checkbox.isChecked():
                gf = self.smooth_series(gf, self.window_spin.value())
                ga = self.smooth_series(ga, self.window_spin.value())

            ax.plot(matchdays, gf, marker='o', label="Goals For", color='green')
            ax.plot(matchdays, ga, marker='o', label="Goals Against", color='red')
            self.latest_data = list(zip(matchdays, gf, ga))
            ax.set_ylabel("Goals")
            self.export_mode = "Goals-For-Against"
            ax.set_title(f"{team} — {mode} ({season})")

        elif mode == "Match Results (W / D / L)":
            points = [row["Points"] for row in data]
            colors = []
            result_labels = []

            for p in points:
                if p == 3:
                    colors.append("green")
                    result_labels.append("W")
                elif p == 1:
                    colors.append("orange")
                    result_labels.append("D")
                else:
                    colors.append("red")
                    result_labels.append("L")

            ax.scatter(matchdays, points, color=colors, label="Match Result", zorder=3)

            # Optional: annotate W/D/L above each point
            for i, (x, y, label) in enumerate(zip(matchdays, points, result_labels)):
                ax.text(x, y + 0.2, label, ha="center", va="bottom", fontsize=8)

            self.latest_data = data  # Store full data rows
            ax.set_ylabel("Result (W=3, D=1, L=0)")            
            self.export_mode = "Match-Results"
            ax.set_title(f"{team} — {mode} ({season})", pad=20)
        
        ax.set_xlabel("Matchday")
        ax.legend()
        self.figure.tight_layout()
        self.canvas.draw()
        
        cursor = mplcursors.cursor(ax.lines, hover=True)

        def format_hover(sel):
            matchday = int(sel.target[0])
            y_val = sel.target[1]
            label = sel.artist.get_label()

            if self.latest_data and len(self.latest_data) >= matchday:
                row = self.latest_data[matchday - 1]
                opponent = row.get("Opponent", "?")
                ha = row.get("HomeOrAway", "?")
                date = row.get("MatchDate", "?")
                gf = row.get("GF", 0)
                ga = row.get("GA", 0)

                if gf > ga:
                    result = "W"
                elif gf == ga:
                    result = "D"
                else:
                    result = "L"

                scoreline = f"{gf}–{ga}"

                tooltip = (
                    f"{label}\n"
                    f"Matchday {matchday} — {date}\n"
                    f"vs {opponent} ({ha})\n"
                    f"Result: {result} ({scoreline})\n"
                    f"Value: {y_val:.1f}"
                )
            else:
                tooltip = (
                    f"{label}\nMatchday {matchday}\n"
                    f"Value: {y_val:.1f}"
            )

            sel.annotation.set_text(tooltip)
    
        cursor.connect("add", format_hover)

        self.export_button.setEnabled(True)
        self.export_data_button.setEnabled(True)
        self.clear_generate_flag()

    def export_chart(self):
        team = self.team_selector.currentText().replace(" ", "_")
        season = self.season_selector.currentText().replace("/", "-")
        filename = f"TeamTrend_{self.export_mode}_{team}_{season}.png"
        folder = self.last_export_dir or os.getcwd()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Chart", os.path.join(folder, filename),
            "PNG Image (*.png);;JPEG Image (*.jpg);;PDF File (*.pdf)"
        )
        if file_path:
            self.figure.savefig(file_path)
            self.last_export_dir = os.path.dirname(file_path)
            QMessageBox.information(self, "Export Successful", f"Chart saved:\n{file_path}")

    def export_data(self):
        if not self.latest_data:
            QMessageBox.information(self, "No Data", "No data to export.")
            return

        team = self.team_selector.currentText().replace(" ", "_")
        season = self.season_selector.currentText().replace("/", "-")
        filename = f"TeamTrendData_{team}_{season}.csv"
        folder = self.last_export_dir or os.getcwd()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", os.path.join(folder, filename),
            "CSV File (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                
                mode = self.chart_mode.currentText()
                writer.writerow(["Matchday", "Date", "Opponent", "Home/Away", "Value"])

                for row in self.latest_data:
                    matchday = row.get("Matchday")
                    date = row.get("MatchDate")
                    opponent = row.get("Opponent")
                    ha = row.get("HomeOrAway")
    
                    if mode == "Cumulative Points":
                        val = np.cumsum([r["Points"] for r in self.latest_data])[matchday - 1]
                    elif mode == "Goal Difference":
                        val = row["GF"] - row["GA"]
                    elif mode == "Goals For / Against":
                        val = f'{row["GF"]} / {row["GA"]}'
                    elif mode == "Match Results (W/D/L)":
                        val = row["Points"]
                    else:
                        val = ""

                    writer.writerow([matchday, date, opponent, ha, val])
                                         
            QMessageBox.information(self, "Export Successful", f"Data saved:\n{file_path}")
            self.last_export_dir = os.path.dirname(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def get_all_teams():
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT TeamName FROM Teams ORDER BY TeamName")
            return [row[0] for row in cursor.fetchall()]
        
        finally:
            cursor.close()
            conn.close()

    def toggle_smoothing_controls(self):
        enabled = self.smooth_checkbox.isChecked()
        self.window_label.setVisible(enabled)
        self.window_spin.setVisible(enabled)

    def mark_generate_outdated(self):
        self.generate_button.setText("Generate Chart (Outdated)")
        self.generate_button.setStyleSheet("font-weight: bold; color: darkred;")

    def clear_generate_flag(self):
        self.generate_button.setText("Generate Chart")
        self.generate_button.setStyleSheet("")
