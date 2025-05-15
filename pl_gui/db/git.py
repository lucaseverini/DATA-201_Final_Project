#!/usr/bin/env python3

# Final project (May-23-2025)
# Class: DATA 201-21
# Instructor: Ronald Mak ron.mak@sjsu.edu
# Student: Luca Severini 008879273 luca.severini@sjsu.edu

# db/git.py

import subprocess

def get_git_version():
    version = None
    try:
        version = subprocess.check_output(["git", "rev-list", "--all", "--count"], stderr=subprocess.DEVNULL)
        version = version.decode().strip()
    except Exception:
        version = ""
    # print(f"Git version: {version}")
    return version
