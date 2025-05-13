#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# views/visualization_view.py

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QComboBox, QLabel
from PyQt5.QtWidgets import QHBoxLayout, QSpacerItem, QSizePolicy, QFileDialog
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from models.league_table_model import get_league_table_data
from models.etl_model import get_all_seasons
import os

class VisualizationView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Premier League Visualizations")
        self.last_export_dir = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.season_selector = QComboBox()
        self.season_selector.addItems(get_all_seasons())
        self.season_selector.currentIndexChanged.connect(self.update_team_filter)

        self.chart_selector = QComboBox()
        self.chart_selector.addItems([
            "Points per Team",
            "Goal Difference per Team",
            "Goals Conceded per Team",
            "Goals Scored per Team",
            "Points vs Goal Difference",
            "Points Efficiency (Points per Match)",
            "Top 5 Attack vs Defense",
            "Win Ratio per Team",
            "Wins / Draws / Losses per Team"
        ])

        self.sort_selector = QComboBox()
        self.sort_selector.addItems([
            "Team Name",
            "Points",
            "Goals For",
            "Goals Against",
            "Goal Difference",
            "Wins"
        ])
        
        self.team_filter = QListWidget()       
        # font_height = self.team_filter.fontMetrics().height()
        # visible_rows = 6
        # padding = 2  # safe padding for borders/scrollbar
        # self.team_filter.setMinimumHeight((font_height + 4) * visible_rows + padding)
        self.team_filter.setMaximumHeight(142)
 
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate_chart)
 
        self.export_button = QPushButton("Export Chart")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_chart)
       
        self.figure = Figure()

        # --- Static controls ---
        self.layout.addWidget(QLabel("Select Season:"))
        self.layout.addWidget(self.season_selector)

        self.layout.addWidget(QLabel("Select Chart:"))
        self.layout.addWidget(self.chart_selector)

        self.layout.addWidget(QLabel("Sort Teams By:"))
        self.layout.addWidget(self.sort_selector)
        
        self.layout.addWidget(QLabel("Filter Teams:"))
        self.layout.addWidget(self.team_filter)

        self.layout.addWidget(self.generate_button)

        self.layout.addWidget(self.export_button)

        # --- Expanding canvas only ---
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.canvas, stretch=1)  # Only this widget gets extra space
        
        self.update_team_filter()

    def generate_chart(self):
        chart_type = self.chart_selector.currentText()
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        season = self.season_selector.currentText()
        data = get_league_table_data(season)
        
        # Get selected sort key
        sort_key = self.sort_selector.currentText()
        key_map = {
            "Team Name": lambda x: x["Team"],
            "Points": lambda x: x["Points"],
            "Goals For": lambda x: x["GF"],
            "Goals Against": lambda x: x["GA"],
            "Goal Difference": lambda x: x["GoalDifference"],
            "Wins": lambda x: x["Won"],
        }
        
        reverse_sort = sort_key != "Team Name"
        data.sort(key=key_map[sort_key], reverse=reverse_sort)

        # Filter selected teams
        # selected_teams = [item.text() for item in self.team_filter.selectedItems()]       
        selected_teams = [
            self.team_filter.item(idx).text()
            for idx in range(self.team_filter.count())
            if self.team_filter.item(idx).checkState() == Qt.Checked
        ]
        
        data = [row for row in data if row["Team"] in selected_teams]
        teams = [row["Team"] for row in data]

        if chart_type == "Points per Team":
            points = [row["Points"] for row in data]
            ax.bar(teams, points)
            ax.set_ylabel("Points")
            ax.set_title("Points per Team")

        elif chart_type == "Goal Difference per Team":
            gd = [row["GoalDifference"] for row in data]
            ax.bar(teams, gd)
            ax.set_ylabel("Goal Difference")
            ax.set_title("Goal Difference per Team")

        elif chart_type == "Goals Scored per Team":
            goals = [row["GF"] for row in data]
            ax.bar(teams, goals)
            ax.set_ylabel("Goals For")
            ax.set_title("Goals Scored per Team")

        elif chart_type == "Goals Conceded per Team":
            goals = [row["GA"] for row in data]
            ax.bar(teams, goals)
            ax.set_ylabel("Goals Against")
            ax.set_title("Goals Conceded per Team")
 
        elif chart_type == "Wins / Draws / Losses per Team":
            wins = [row["Won"] for row in data]
            draws = [row["Drawn"] for row in data]
            losses = [row["Lost"] for row in data]

            ax.bar(teams, wins, label="Wins")
            ax.bar(teams, draws, bottom=wins, label="Draws")
            bottoms = [w + d for w, d in zip(wins, draws)]
            ax.bar(teams, losses, bottom=bottoms, label="Losses")

            ax.set_ylabel("Match Results")
            ax.set_title("Wins / Draws / Losses per Team")
            ax.legend()

        elif chart_type == "Points vs Goal Difference":
            points = [row["Points"] for row in data]
            gd = [row["GoalDifference"] for row in data]
            ax.scatter(gd, points)

            for i, team in enumerate(teams):
                ax.annotate(team, (gd[i], points[i]), fontsize=8, alpha=0.7)

            ax.set_xlabel("Goal Difference")
            ax.set_ylabel("Points")
            ax.set_title("Points vs Goal Difference")
    
        elif chart_type == "Win Ratio per Team":
            played = [row["Played"] for row in data]
            won = [row["Won"] for row in data]
            win_ratio = [round(w / p * 100, 1) if p > 0 else 0 for w, p in zip(won, played)]
            ax.bar(teams, win_ratio)
            ax.set_ylabel("Win Ratio (%)")
            ax.set_title("Win Ratio per Team")

        elif chart_type == "Top 5 Attack vs Defense":
            # Sort data by Points descending
            top5 = sorted(data, key=lambda x: x["Points"], reverse=True)[:5]
            top5_teams = [row["Team"] for row in top5]
            gf = [row["GF"] for row in top5]
            ga = [row["GA"] for row in top5]

            x = range(len(top5_teams))
            bar_width = 0.35

            ax.bar([i - bar_width / 2 for i in x], gf, width=bar_width, label="Goals For", color='green')
            ax.bar([i + bar_width / 2 for i in x], ga, width=bar_width, label="Goals Against", color='red')

            ax.set_xticks(x)
            ax.set_xticklabels(top5_teams)
            ax.set_ylabel("Goals")
            ax.set_title("Top 5 Teams: Attack vs Defense")
            ax.legend()

        elif chart_type == "Points Efficiency (Points per Match)":
            efficiency = [round(row["Points"] / row["Played"], 2) if row["Played"] else 0 for row in data]
            ax.bar(teams, efficiency, color='purple')
            ax.set_ylabel("Points per Match")
            ax.set_title("Points Efficiency per Team")
                           
        ax.tick_params(axis='x', rotation=45)
        
        self.figure.tight_layout()
        self.canvas.draw()
 
        self.export_button.setEnabled(True)
       
    def export_chart(self):
        chart_name = self.chart_selector.currentText().replace(" / ", "-").replace(" ", "_")
        season = self.season_selector.currentText().replace("/", "-")
        base_name = f"{chart_name}_{season}"

        # Determine fallback folder
        if self.last_export_dir and os.path.isdir(self.last_export_dir):
            initial_dir = self.last_export_dir
        else:
            try:
                initial_dir = os.getcwd()
                if not os.access(initial_dir, os.W_OK):
                    raise PermissionError
            except Exception:
                # Fallback to desktop
                initial_dir = os.path.join(os.path.expanduser("~"), "Desktop")

        default_file = os.path.join(initial_dir, base_name)
    
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Chart As...",
            default_file,
            "PNG Image (*.png);;JPEG Image (*.jpg);;PDF File (*.pdf)"
        )

        if not file_path:
            return  # user cancelled
            
        self.last_export_dir = os.path.dirname(file_path)

        # Determine extension based on selected filter
        if "PNG" in selected_filter:
            ext = ".png"
        elif "JPEG" in selected_filter:
            ext = ".jpg"
        elif "PDF" in selected_filter:
            ext = ".pdf"
        else:
            ext = ".png"

        # Add extension if not present
        if not file_path.lower().endswith(ext):
            file_path += ext

        try:
            self.figure.savefig(file_path)
            QMessageBox.information(self, "Export Successful", f"Chart saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not save chart:\n{str(e)}")

    def update_team_filter(self):
        season = self.season_selector.currentText()
        data = get_league_table_data(season)
        self.team_filter.clear()       
        teams = sorted(row["Team"] for row in data)
        for team in teams:
            item = QListWidgetItem(team)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.team_filter.addItem(item)
    