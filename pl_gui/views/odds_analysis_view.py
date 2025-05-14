#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/odds_analysis_view.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from models.etl_model import get_all_seasons, get_all_bookmakers
from models.etl_model import get_avg_margins_per_bookmaker, get_implied_probability_data
import os
import numpy as np

class OddsAnalysisView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Implied Probability vs Result")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Season selector
        self.season_selector = QComboBox()
        self.season_selector.addItems(get_all_seasons())
        self.layout.addWidget(QLabel("Select Season:"))
        self.layout.addWidget(self.season_selector)

        # Bookmaker selector
        self.bookmaker_selector = QComboBox()
        self.bookmaker_selector.addItems(get_all_bookmakers())
        self.layout.addWidget(QLabel("Select Bookmaker:"))
        self.layout.addWidget(self.bookmaker_selector)

        self.chart_type_selector = QComboBox()
        self.chart_type_selector.addItems([
            "Implied Probability vs Result",
            "Bookmaker Margin",
            "Margin Distribution",
            "Compare Bookmaker Margins"
        ])
        self.layout.addWidget(QLabel("Chart Type:"))
        self.layout.addWidget(self.chart_type_selector)

        # Generate
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate_chart)
        self.layout.addWidget(self.generate_button)

        # Chart
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas, stretch=1)

        # Export
        self.export_button = QPushButton("Export Data (CSV)")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_data)
        self.layout.addWidget(self.export_button)

        self.latest_data = None
        self.last_export_dir = None

    def generate_chart(self):
        season = self.season_selector.currentText()
        bookmaker = self.bookmaker_selector.currentText()

        chart_mode = self.chart_type_selector.currentText()
        data = get_implied_probability_data(season, bookmaker)    
        if not data:
            QMessageBox.information(self, "No Data", "No odds data found for this bookmaker and season.")
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if chart_mode == "Implied Probability vs Result":
            outcomes = ['H', 'D', 'A']
            implied_totals = {'H': [], 'D': [], 'A': []}
            actual_counts = {'H': 0, 'D': 0, 'A': 0}
            total_matches = 0

            for row in data:
                odds = [row['HomeOdds'], row['DrawOdds'], row['AwayOdds']]
                if any(o <= 1.01 for o in odds):  # skip invalid odds
                    continue

                inv_sum = sum(1/o for o in odds)
                probs = [(1/o)/inv_sum for o in odds]  # normalized

                implied_totals['H'].append(probs[0])
                implied_totals['D'].append(probs[1])
                implied_totals['A'].append(probs[2])
                actual_counts[row['FTR']] += 1
                total_matches += 1

            avg_implied = {k: np.mean(implied_totals[k]) * 100 for k in outcomes}
            actual_freq = {k: (actual_counts[k] / total_matches) * 100 for k in outcomes}

            self.figure.clear()
            ax = self.figure.add_subplot(111)

            x = np.arange(len(outcomes))
            width = 0.35

            ax.bar(x - width/2, [avg_implied[o] for o in outcomes], width, label='Implied %', color='gray')
            ax.bar(x + width/2, [actual_freq[o] for o in outcomes], width, label='Actual %', color='blue')

            ax.set_xticks(x)
            ax.set_xticklabels(['Home Win', 'Draw', 'Away Win'])
            ax.set_ylabel("Percentage")
            ax.set_title(f"{bookmaker} — Implied vs Actual Outcome Rates ({season})")
            ax.legend()

        elif chart_mode == "Bookmaker Margin":
            margins = []
            for row in data:
                odds = [row['HomeOdds'], row['DrawOdds'], row['AwayOdds']]
                if any(o <= 1.01 for o in odds):
                    continue
                margin = sum(1 / o for o in odds)
                margins.append((margin - 1.0) * 100)

            if not margins:
                QMessageBox.information(self, "No Valid Odds", "No valid margin data available.")
                return

            x = list(range(1, len(margins) + 1))
            ax.plot(x, margins, label="Bookmaker Margin", color="purple", marker='o')
            ax.axhline(np.mean(margins), color="gray", linestyle="--", label="Average Margin")

            ax.set_title(f"{bookmaker} — Bookmaker Margin per Match ({season})")
            ax.set_ylabel("Bookmaker Margin (%)")
            ax.set_xlabel("Match Index")
            ax.legend()
 
        elif chart_mode == "Margin Distribution":
            margins = []
            for row in data:
                odds = [row['HomeOdds'], row['DrawOdds'], row['AwayOdds']]
                if any(o <= 1.01 for o in odds):
                    continue
                margin = sum(1 / o for o in odds)
                margins.append((margin - 1.0) * 100)  # percent overround

            if not margins:
                QMessageBox.information(self, "No Valid Odds", "No valid margin data available.")
                return

            ax.hist(margins, bins=15, color="purple", edgecolor="black", alpha=0.7)
            ax.axvline(np.mean(margins), color="red", linestyle="--", label="Mean Margin")

            ax.set_title(f"{bookmaker} — Margin Distribution ({season})")
            ax.set_xlabel("Margin (%)")
            ax.set_ylabel("Match Count")
            ax.legend()
 
        elif chart_mode == "Compare Bookmaker Margins":
            margins = get_avg_margins_per_bookmaker(season)
            if not margins:
                QMessageBox.information(self, "No Data", "No margin data found for this season.")
                return

            names = [row['BookmakerName'] for row in margins]
            values = [row['AvgMargin'] for row in margins]
            errors = [row['StdMargin'] for row in margins]

            x = np.arange(len(names))

            self.figure.clear()
            ax = self.figure.add_subplot(111)

            ax.bar(x, values, yerr=errors, capsize=5, color='skyblue', alpha=0.9)
            ax.set_xticks(x)
            ax.set_xticklabels(names, rotation=45, ha='right')

            ax.set_title(f"Average Bookmaker Margin by Bookmaker ({season})")
            ax.set_ylabel("Average Margin (%)")
            ax.set_xlabel("Bookmaker")
            ax.grid(axis='y', linestyle='--', linewidth=0.5)
           
        self.figure.tight_layout()
        self.canvas.draw()

        self.latest_data = data
        self.export_button.setEnabled(True)
   
    def export_data(self):
        if not self.latest_data:
            QMessageBox.information(self, "No Data", "No data available to export.")
            return

        season = self.season_selector.currentText().replace("/", "-")
        bookmaker = self.bookmaker_selector.currentText().replace(" ", "_")
        default_name = f"OddsData_{bookmaker}_{season}.csv"

        folder = self.last_export_dir or os.getcwd()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Odds Data", os.path.join(folder, default_name),
            "CSV File (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="") as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(["MatchDate", "HomeOdds", "DrawOdds", "AwayOdds", "FTR",
                                 "ImpliedH", "ImpliedD", "ImpliedA"])
                for row in self.latest_data:
                    odds = [row['HomeOdds'], row['DrawOdds'], row['AwayOdds']]
                    if any(o <= 1.01 for o in odds):
                        continue
                    inv_sum = sum(1 / o for o in odds)
                    probs = [(1 / o) / inv_sum for o in odds]
                    writer.writerow([
                        row.get("MatchDate", ""),
                        *odds,
                        row.get("FTR", ""),
                        f"{probs[0]:.4f}", f"{probs[1]:.4f}", f"{probs[2]:.4f}"
                    ])
            QMessageBox.information(self, "Export Complete", f"File saved:\n{file_path}")
            self.last_export_dir = os.path.dirname(file_path)

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
