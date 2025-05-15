#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# dialogs/login_dialog.py

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QMessageBox
from db.connection import get_connection
from db.git import get_git_version
import hashlib

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        version = get_git_version()
        self.setWindowTitle(f"Premier League DB Manager (v. 0.{version})")

        self.setFixedSize(350, 200)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

        self.username = None
        self.role = None

        layout = QVBoxLayout(self)

        self.user_input = QLineEdit()
        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.Password)

        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.user_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.pw_input)

        btns = QHBoxLayout()
        login_btn = QPushButton("Login")
        cancel_btn = QPushButton("Cancel")
        btns.addWidget(login_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        login_btn.clicked.connect(self.try_login)
        cancel_btn.clicked.connect(self.reject)

    def try_login(self):
        username = self.user_input.text().strip()
        password = self.pw_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Missing Info", "Please enter username and password.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PasswordHash, Role FROM Users WHERE Username = %s", (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            QMessageBox.critical(self, "Login Failed", f"User {username} not found.")
            return

        hash_pw, role = row
        hash_entered = hashlib.sha256(password.encode()).hexdigest()

        if hash_pw != hash_entered:
            QMessageBox.critical(self, "Login Failed", f"Invalid password for {username}.")
            return

        self.username = username
        self.role = role
        self.accept()
