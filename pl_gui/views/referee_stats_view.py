#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/referee_stats_view.py

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QCheckBox
from PyQt5.QtWidgets import  QPushButton, QFileDialog, QMessageBox, QSpinBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from models.etl_model import get_referee_stats, get_all_referees, get_all_seasons, get_referee_trend_stats
import os
import mplcursors
import numpy as np

class RefereeStatsView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Referee Statistics Dashboard")
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Season selector
        self.season_selector = QComboBox()
        self.season_selector.addItems(get_all_seasons())
        self.layout.addWidget(QLabel("Select Season:"))
        self.layout.addWidget(self.season_selector)

        # Chart Mode selector
        self.chart_mode_selector = QComboBox()
        self.chart_mode_selector.addItems([
            "Single Referee View",
            "Compare Two Referees",
            "All Referees Overview",
            "Referee Trend Over Time"
        ])
        self.chart_mode_selector.currentIndexChanged.connect(self.update_mode_visibility)
        self.layout.addWidget(QLabel("Chart Mode:"))
        self.layout.addWidget(self.chart_mode_selector)

        # Metric selector
        self.metric_label = QLabel("Select Metric:")
        self.metric_selector = QComboBox()
        self.metric_selector.addItems(["Yellow Cards", "Red Cards", "Fouls"])
        self.metric_selector.setCurrentIndex(0)
        self.metric_label.hide()
        self.metric_selector.hide()
        self.layout.addWidget(self.metric_label)
        self.layout.addWidget(self.metric_selector)

        self.yellow_check = QCheckBox("Yellow Cards")
        self.red_check = QCheckBox("Red Cards")
        self.foul_check = QCheckBox("Fouls")

        for box in [self.yellow_check, self.red_check, self.foul_check]:
            box.setChecked(True)
            box.hide()
            self.layout.addWidget(box)
 
         # Smooth Trend
        self.smooth_checkbox = QCheckBox("Smooth Trend (Moving Average)")
        self.smooth_checkbox.setChecked(False)
        self.smooth_checkbox.hide()
        self.smooth_checkbox.stateChanged.connect(self.toggle_smoothing_controls)
 
        self.window_label = QLabel("Smoothing Window:")
        self.window_spin = QSpinBox()
        self.window_spin.setRange(1, 10)
        self.window_spin.setValue(3)

        self.window_label.hide()
        self.window_spin.hide()

        self.layout.addWidget(self.smooth_checkbox)
        self.layout.addWidget(self.window_label)
        self.layout.addWidget(self.window_spin)
   
        # Referee selector
        self.ref_selector = QComboBox()
        self.ref_selector.addItems(get_all_referees())
        self.layout.addWidget(QLabel("Select Referee:"))
        self.layout.addWidget(self.ref_selector)

        # Referee 2 selector
        self.ref_label_2 = QLabel("Select Second Referee:")
        self.ref_selector_2 = QComboBox()
        self.ref_selector_2.addItems(get_all_referees())

        self.ref_label_2.hide()
        self.ref_selector_2.hide()

        self.layout.addWidget(self.ref_label_2)
        self.layout.addWidget(self.ref_selector_2)

        # Generate button
        self.generate_button = QPushButton("Generate Chart")
        self.generate_button.clicked.connect(self.generate_chart)
        self.layout.addWidget(self.generate_button)

        # Chart canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(self.canvas.sizePolicy().Expanding, self.canvas.sizePolicy().Expanding)
        self.layout.addWidget(self.canvas, stretch=1)

        # Export Chart button
        self.export_button = QPushButton("Export Chart")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_chart)
        self.layout.addWidget(self.export_button)

        # Export Data button
        self.export_data_button = QPushButton("Export Data (CSV)")
        self.export_data_button.setEnabled(False)
        self.export_data_button.clicked.connect(self.export_trend_data)
        self.layout.addWidget(self.export_data_button)

        self.season_selector.currentIndexChanged.connect(self.mark_generate_outdated)
        self.ref_selector.currentIndexChanged.connect(self.mark_generate_outdated)
        self.ref_selector_2.currentIndexChanged.connect(self.mark_generate_outdated)
        self.chart_mode_selector.currentIndexChanged.connect(self.mark_generate_outdated)
        self.metric_selector.currentIndexChanged.connect(self.mark_generate_outdated)
        self.smooth_checkbox.stateChanged.connect(self.mark_generate_outdated)
        self.window_spin.valueChanged.connect(self.mark_generate_outdated)
        self.yellow_check.stateChanged.connect(self.mark_generate_outdated)
        self.red_check.stateChanged.connect(self.mark_generate_outdated)
        self.foul_check.stateChanged.connect(self.mark_generate_outdated)

        self.last_export_dir = None
        self.latest_trend_data = None

    def export_trend_data(self):
        import csv

        if not self.latest_trend_data:
            QMessageBox.information(self, "No Data", "No trend data available to export.")
            return

        referee = self.ref_selector.currentText().replace(" ", "_")
        season = self.season_selector.currentText().replace("/", "-")
        default_name = f"TrendData_{referee}_{season}.csv"

        folder = self.last_export_dir or os.getcwd()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Trend Data As...",
            os.path.join(folder, default_name),
            "CSV File (*.csv)"
        )

        if not file_path:
            return

        self.last_export_dir = os.path.dirname(file_path)
 
        try:
            with open(file_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "YellowCards", "RedCards", "Fouls"])
                for row in self.latest_trend_data:
                    date = row["MatchDate"]
                    yellow = row["HomeYellowCards"] + row["AwayYellowCards"]
                    red = row["HomeRedCards"] + row["AwayRedCards"]
                    fouls = row["HomeFouls"] + row["AwayFouls"]
                    writer.writerow([date, yellow, red, fouls])
            
            QMessageBox.information(self, "Export Successful", f"Data saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
        
    def export_chart(self):
        chart_type = "Referee_Stats"
        season = self.season_selector.currentText().replace("/", "-")
        referee = self.ref_selector.currentText().replace(" ", "_")
        base_name = f"{chart_type}_{referee}_{season}"

        # Directory fallback
        if self.last_export_dir and os.path.isdir(self.last_export_dir):
            initial_dir = self.last_export_dir
        else:
            try:
                initial_dir = os.getcwd()
                if not os.access(initial_dir, os.W_OK):
                    raise PermissionError
            except Exception:
                initial_dir = os.path.join(os.path.expanduser("~"), "Desktop")

        default_file = os.path.join(initial_dir, base_name)

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Chart As...",
            default_file,
            "PNG Image (*.png);;JPEG Image (*.jpg);;PDF File (*.pdf)"
        )

        if not file_path:
            return

        self.last_export_dir = os.path.dirname(file_path)

        if "PNG" in selected_filter:
            ext = ".png"
        elif "JPEG" in selected_filter:
            ext = ".jpg"
        elif "PDF" in selected_filter:
            ext = ".pdf"
        else:
            ext = ".png"

        if not file_path.lower().endswith(ext):
            file_path += ext

        try:
            self.figure.savefig(file_path)
            QMessageBox.information(self, "Export Successful", f"Chart saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not save chart:\n{str(e)}")
 
    def update_mode_visibility(self):
        mode = self.chart_mode_selector.currentText()
        is_compare = (mode == "Compare Two Referees")
        is_single = (mode == "Single Referee View")
        is_all = (mode == "All Referees Overview")
        is_trend = (mode == "Referee Trend Over Time")

        self.ref_selector.setVisible(is_single or is_compare)
        self.ref_selector_2.setVisible(is_compare)
        self.ref_label_2.setVisible(is_compare)
        self.metric_label.setVisible(is_all)
        self.metric_selector.setVisible(is_all)
        self.ref_selector.setVisible(is_single or is_compare or is_trend)
        self.ref_label_2.setVisible(is_compare)
        self.ref_selector_2.setVisible(is_compare)
        self.metric_label.setVisible(is_all)
        self.metric_selector.setVisible(is_all)
        self.yellow_check.setVisible(is_trend)
        self.red_check.setVisible(is_trend)
        self.foul_check.setVisible(is_trend)
        self.smooth_checkbox.setVisible(is_trend)
        self.window_label.setVisible(is_trend and self.smooth_checkbox.isChecked())
        self.window_spin.setVisible(is_trend and self.smooth_checkbox.isChecked())
        self.export_data_button.setEnabled(is_trend)

    def generate_chart(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        season = self.season_selector.currentText()
        mode = self.chart_mode_selector.currentText()

        if mode == "Single Referee View":
            referee = self.ref_selector.currentText()
            stats = get_referee_stats(season, referee)
            if not stats:
                QMessageBox.information(self, "No Data", "No match statistics found.")
                return
            values = [stats["AvgYellow"], stats["AvgRed"], stats["AvgFouls"]]
            ax.bar(["Yellow", "Red", "Fouls"], values, color=["gold", "red", "gray"])
            ax.set_title(f"{referee} ({season})")

            self.figure.tight_layout()
            self.canvas.draw()      
            self.export_button.setEnabled(True)
            self.clear_generate_flag()

        elif mode == "Compare Two Referees":
            ref1 = self.ref_selector.currentText()
            ref2 = self.ref_selector_2.currentText()
            if ref1 == ref2:
                QMessageBox.warning(self, "Invalid Selection", "Please select two different referees.")
                return
    
            s1 = get_referee_stats(season, ref1)
            s2 = get_referee_stats(season, ref2)
            if not s1 or not s2:
                QMessageBox.information(self, "No Data", "No match stats for one or both referees.")
                return

            categories = ["Yellow", "Red", "Fouls"]
            values1 = [s1["AvgYellow"], s1["AvgRed"], s1["AvgFouls"]]
            values2 = [s2["AvgYellow"], s2["AvgRed"], s2["AvgFouls"]]
            x = range(len(categories))
            width = 0.35
            ax.bar([i - width/2 for i in x], values1, width, label=ref1)
            ax.bar([i + width/2 for i in x], values2, width, label=ref2)
            ax.set_xticks(list(x))
            ax.set_xticklabels(categories)
            ax.set_title(f"{ref1} vs {ref2} ({season})")
            ax.legend()

            self.figure.tight_layout()
            self.canvas.draw()      
            self.export_button.setEnabled(True)
            self.clear_generate_flag()

        elif mode == "All Referees Overview":
            metric_map = {
                "Yellow Cards": "AvgYellow",
                "Red Cards": "AvgRed",
                "Fouls": "AvgFouls"
            }
            selected_metric = self.metric_selector.currentText()
            metric = metric_map[selected_metric]
            stat_label = selected_metric
            refs = get_all_referees()
            data = []
            for ref in refs:
                stats = get_referee_stats(season, ref)
                if stats and stats["AvgYellow"] is not None:
                    data.append((ref, stats[metric]))

            data.sort(key=lambda x: x[1], reverse=True)
            labels = [x[0] for x in data]
            values = [x[1] for x in data]
            
            color_map = {
                "AvgYellow": "gold",
                "AvgRed": "red",
                "AvgFouls": "gray"
            }
            bar_color = color_map[metric]
            ax.bar(labels, values, color=bar_color)

            ax.set_title(f"{stat_label} per Match by Referee ({season})")
            ax.tick_params(axis='x', rotation=45)

            self.figure.tight_layout()
            self.canvas.draw()      
            self.export_button.setEnabled(True)
            self.clear_generate_flag()

        elif mode == "Referee Trend Over Time":
            referee = self.ref_selector.currentText()
            trend_data = get_referee_trend_stats(season, referee)
            self.latest_trend_data = trend_data

            if not trend_data:
                QMessageBox.information(self, "No Data", "No matches found for this referee and season.")
                return

            dates = [row["MatchDate"] for row in trend_data]
            yellow = [row["HomeYellowCards"] + row["AwayYellowCards"] for row in trend_data]
            red = [row["HomeRedCards"] + row["AwayRedCards"] for row in trend_data]
            fouls = [row["HomeFouls"] + row["AwayFouls"] for row in trend_data]

            if self.smooth_checkbox.isChecked():
                window = self.window_spin.value()
                yellow = self.smooth_series(yellow, window)
                red = self.smooth_series(red, window)
                fouls = self.smooth_series(fouls, window)
    
            if self.yellow_check.isChecked():
                ax.plot(dates, yellow, label="Yellow Cards", color="gold", marker='o')
            if self.red_check.isChecked():
                ax.plot(dates, red, label="Red Cards", color="red", marker='o')
            if self.foul_check.isChecked():
                ax.plot(dates, fouls, label="Fouls", color="gray", marker='o')
    
            ax.set_title(f"{referee} — Match Trend ({season})")
            
            match_count = len(trend_data)
            subtitle = f"Total Matches: {match_count}"
            ax.text(0.00, 1.02, subtitle, transform=ax.transAxes, ha='left', fontsize=10, color='gray')
        
            ax.set_ylabel("Count per Match")
            ax.set_xlabel("Match Date")
            ax.tick_params(axis='x', rotation=45)
            ax.legend()
  
            self.figure.tight_layout()
            self.canvas.draw()

            cursor = mplcursors.cursor(ax.lines, hover=True)
            
            def format_hover(sel):
                label = sel.artist.get_label()
                x_val = sel.target[0]
                y_val = sel.target[1]
                sel.annotation.set_text(f"{label}\n{x_val:.0f}: {y_val:.1f}")
  
            cursor.connect("add", format_hover)
                  
            self.export_button.setEnabled(True)
            self.clear_generate_flag()
 
    def smooth_series(self, data, window):
        if len(data) < window:
            return data  # not enough points to smooth
        return np.convolve(data, np.ones(window) / window, mode='same')  
 
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
 