#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# dialogs/user_management_dialog.py

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QLineEdit, QLabel
from PyQt5.QtWidgets import QComboBox, QMessageBox, QInputDialog
import hashlib
from db.connection import get_connection

class UserManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Management")
        self.resize(600, 400)

        self.layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add User")
        self.delete_btn = QPushButton("Delete User")
        self.reset_btn = QPushButton("Reset Password")
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.reset_btn)
        self.layout.addLayout(button_layout)

        self.add_btn.clicked.connect(self.add_user)
        self.delete_btn.clicked.connect(self.delete_user)
        self.reset_btn.clicked.connect(self.reset_password)

        self.load_users()

    def load_users(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Username, Role, CreatedDate FROM Users ORDER BY Username")
        users = cursor.fetchall()
        cursor.close()
        conn.close()

        self.table.setRowCount(len(users))
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Username", "Role", "Created"])

        for i, row in enumerate(users):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
                              
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.resizeColumnsToContents()

    def add_user(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add User")
        layout = QVBoxLayout(dialog)

        username_input = QLineEdit()
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        role_box = QComboBox()
        role_box.addItems(["admin", "manager", "user"])

        layout.addWidget(QLabel("Username:"))
        layout.addWidget(username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(password_input)
        layout.addWidget(QLabel("Role:"))
        layout.addWidget(role_box)

        btn = QPushButton("Create")
        layout.addWidget(btn)

        def submit():
            username = username_input.text().strip()
            password = password_input.text()
            role = role_box.currentText()
            if not username or not password:
                QMessageBox.warning(dialog, "Error", "Username and password are required.")
                return
            hash_pw = hashlib.sha256(password.encode()).hexdigest()

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Users (Username, PasswordHash, Role)
                    VALUES (%s, %s, %s)
                """, (username, hash_pw, role))
                conn.commit()
                cursor.close()
                conn.close()
                dialog.accept()
                self.load_users()
            except Exception as e:
                QMessageBox.critical(dialog, "Error", str(e))

        btn.clicked.connect(submit)
        dialog.exec_()

    def delete_user(self):
        username, ok = self.prompt_for_username("Delete User", "Enter username to delete:")
        if not ok or not username:
            return
            
        try:
            username = username.strip()
            
            conn = get_connection()
            cursor = conn.cursor()

            # Get the role of the target user
            cursor.execute("SELECT Role FROM Users WHERE Username = %s", (username,))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                conn.close()
                QMessageBox.warning(self, "User Not Found", f"User '{username}' does not exist.")
                return

            target_role = row[0]
            current_role = getattr(self.parent(), "role", None)

            # Actually should never happen
            if target_role == "admin" and current_role != "admin":
                cursor.close()
                conn.close()
                QMessageBox.warning(
                    self,
                    "Permission Denied",
                    "Only an admin can delete another admin."
                )
                return

            confirm = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the {target_role} '{username}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                cursor.close()
                conn.close()
                return

            cursor.execute("DELETE FROM Users WHERE Username = %s", (username,))
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            if affected == 0:
                QMessageBox.warning(self, "Not Deleted", f"User '{username}' could not be deleted.")
            else:
                QMessageBox.information(self, "User Deleted", f"User '{username}' has been deleted.")
                self.load_users()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
                  
    def reset_password(self):
        username, ok1 = self.prompt_for_username("Reset Password", "Enter username:")
        if not ok1 or not username:
            return
        
        try:
            username = username.strip()
            
            conn = get_connection()
            cursor = conn.cursor()
 
            # Get the role of the target user
            cursor.execute("SELECT Role FROM Users WHERE Username = %s", (username,))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                conn.close()
                QMessageBox.warning(self, "User Not Found", f"User '{username}' does not exist.")
                return

            target_role = row[0]
            current_role = getattr(self.parent(), "role", None)

            # Actually should never happen
            if target_role == "admin" and current_role != "admin":
                cursor.close()
                conn.close()
                QMessageBox.warning(
                    self,
                    "Permission Denied",
                    "Only an admin can delete reset the password of an admin."
                )
                return
    
            cursor.execute("SELECT COUNT(*) FROM Users WHERE Username = %s", (username,))
            exists = cursor.fetchone()[0]
            if not exists:
                cursor.close()
                conn.close()
                QMessageBox.warning(self, "User Not Found", f"User '{username}' does not exist.")
                return

            new_pw, ok2 = self.prompt_for_password("Reset Password", f"New password for {target_role} '{username}':")
            if not ok2 or not new_pw:
                return
                
            new_pw = new_pw.strip()

            new_hash = hashlib.sha256(new_pw.encode()).hexdigest()
        
            cursor.execute("UPDATE Users SET PasswordHash = %s WHERE Username = %s", (new_hash, username))
            conn.commit()
            cursor.close()
            conn.close()
            QMessageBox.information(self, "Done", f"Password updated for {target_role} {username}.")
        
        except Exception as e:
            QMessageBox.critical(self, f"Error Resetting Password of {target_role} {username}", str(e))
 
    def prompt_for_username(self, title, message):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setFixedSize(300, 120)
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(message))

        input_field = QLineEdit()
        layout.addWidget(input_field)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        result = {}

        def accept():
            result['text'] = input_field.text().strip()
            dlg.accept()

        ok_btn.clicked.connect(accept)
        cancel_btn.clicked.connect(dlg.reject)

        if dlg.exec_() == QDialog.Accepted:
            return result['text'], True
        else:
            return None, False
            
    def prompt_for_password(self, title, message):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setFixedSize(300, 120)
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(message))

        pw_input = QLineEdit()
        pw_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(pw_input)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        result = {}

        def accept():
            result['text'] = pw_input.text().strip()
            dlg.accept()

        ok_btn.clicked.connect(accept)
        cancel_btn.clicked.connect(dlg.reject)

        if dlg.exec_() == QDialog.Accepted:
            return result['text'], True
        else:
            return None, False
