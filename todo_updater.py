# updater.py
import sys
import os
import json
import urllib.request
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# Configuration (Update these values!)
REPO_URL = "https://github.com/Kairu1206/todoapp/releases/latest"
CURRENT_VERSION_FILE = "version.txt"  # Version file in your main app directory
MAIN_APP_EXE = "todo.exe"  # Name of your main executable

class Updater:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main window
        self.check_for_updates()

    def get_local_version(self):
        try:
            with open(CURRENT_VERSION_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0"  #Fallback version

    def get_remote_version(self):
        try:
            response = urllib.request.urlopen(REPO_URL)
            data = json.load(response)
            return data["tag_name"]
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to check updates: {str(e)}")
            return None

    def download_new_version(self, asset_url):
        temp_dir = Path("update_temp")
        temp_dir.mkdir(exist_ok=True)
        
        # Download new EXE
        new_exe_path = temp_dir / MAIN_APP_EXE
        with urllib.request.urlopen(asset_url) as response:
            with open(new_exe_path, "wb") as f:
                f.write(response.read())
        
        # Download new version.txt
        version_url = asset_url.replace(MAIN_APP_EXE, CURRENT_VERSION_FILE)
        with urllib.request.urlopen(version_url) as response:
            with open(temp_dir / CURRENT_VERSION_FILE, "wb") as f:
                f.write(response.read())
        
        return new_exe_path

    def create_update_script(self, new_exe_path):
        script = f"""@echo off
timeout /t 3 /nobreak >nul
del "{MAIN_APP_EXE}"
move "{new_exe_path}" "{MAIN_APP_EXE}"
del "{new_exe_path.parent / CURRENT_VERSION_FILE}"
move "{new_exe_path.parent / CURRENT_VERSION_FILE}" "{CURRENT_VERSION_FILE}"
rmdir /s /q "{new_exe_path.parent}"
start "" "{MAIN_APP_EXE}"
del "%~f0"
"""
        with open("update_script.bat", "w") as f:
            f.write(script)

    def check_for_updates(self):
        local_version = self.get_local_version()
        remote_version = self.get_remote_version()

        if remote_version and remote_version > local_version:
            if messagebox.askyesno(
                "Update Available",
                f"New version {remote_version} available!\nUpdate now?",
            ):
                # Get download URL for the EXE from GitHub
                response = urllib.request.urlopen(REPO_URL)
                data = json.load(response)
                asset_url = next(
                    (a["browser_download_url"] for a in data["assets"] if a["name"] == MAIN_APP_EXE),
                    None
                )
                
                if asset_url:
                    new_exe_path = self.download_new_version(asset_url)
                    self.create_update_script(new_exe_path)
                    
                    # Launch update script and close updater
                    subprocess.Popen(["update_script.bat"], shell=True)
                    self.root.destroy()
                else:
                    messagebox.showerror("Error", "Could not find update asset")
        else:
            # Launch main app if no update needed
            subprocess.Popen([MAIN_APP_EXE], shell=True)
            self.root.destroy()

if __name__ == "__main__":
    Updater()