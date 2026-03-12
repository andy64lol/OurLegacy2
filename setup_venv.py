#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# ---------- Setup functions ----------
def get_venv_path():
    return os.path.join(os.path.dirname(__file__), 'venv')

def venv_exists():
    return os.path.isdir(get_venv_path())

def get_python_executable():
    venv_path = get_venv_path()
    if platform.system() == 'Windows':
        return os.path.join(venv_path, 'Scripts', 'python.exe')
    else:
        return os.path.join(venv_path, 'bin', 'python')

def get_pip_executable():
    venv_path = get_venv_path()
    if platform.system() == 'Windows':
        return os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        return os.path.join(venv_path, 'bin', 'pip')

def create_venv(log):
    log(f"Creating virtual environment at {get_venv_path()}...\n")
    try:
        subprocess.run([sys.executable, '-m', 'venv', get_venv_path()], check=True)
        log("✓ Virtual environment created successfully.\n")
        return True
    except subprocess.CalledProcessError as e:
        log(f"✗ Failed to create virtual environment: {e}\n")
        return False

def upgrade_pip(log):
    pip_exe = get_pip_executable()
    log("Upgrading pip...\n")
    try:
        subprocess.run([pip_exe, 'install', '--upgrade', 'pip'], check=True)
        log("✓ Pip upgraded successfully.\n")
        return True
    except subprocess.CalledProcessError as e:
        log(f"✗ Failed to upgrade pip: {e}\n")
        return False

def install_dependencies(log):
    pip_exe = get_pip_executable()
    dependencies = [
        'customtkinter>=5.0.0',
        'pillow>=9.0.0',
        'requests>=2.28.0',
    ]
    log("Installing dependencies...\n")
    for package in dependencies:
        log(f"  Installing {package}...\n")
        try:
            subprocess.run([pip_exe, 'install', package], check=True)
            log(f"  ✓ {package} installed successfully.\n")
        except subprocess.CalledProcessError as e:
            log(f"  ✗ Failed to install {package}: {e}\n")
            return False
    log("✓ All dependencies installed successfully.\n")
    return True

def register_game_font(font_path, log):
    font_path = Path(font_path).resolve()
    if not font_path.exists():
        log(f"✗ Font file not found at {font_path}\n")
        return False

    system = platform.system()
    if system in ["Linux", "Darwin"]:
        user_fonts = Path.home() / ".local/share/fonts"
        user_fonts.mkdir(parents=True, exist_ok=True)
        dest_font = user_fonts / font_path.name
        if not dest_font.exists():
            log(f"Copying font to {dest_font}...\n")
            shutil.copy2(str(font_path), str(dest_font))
        log("Updating font cache...\n")
        subprocess.run(["fc-cache", "-fv"], check=True)
        log(f"✓ Font '{font_path.name}' registered successfully!\n")
        return True
    elif system == "Windows":
        log("ℹ Windows detected: ensure font is installed or bundled.\n")
        return True
    else:
        log(f"⚠ Unsupported system: {system}. Font may not load automatically.\n")
        return False

# ---------- Tkinter GUI ----------
class SetupGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Our Legacy - Setup")
        self.geometry("700x550")
        self.resizable(False, False)

        self.log_area = scrolledtext.ScrolledText(self, state='disabled', width=90, height=25)
        self.log_area.pack(pady=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)

        self.setup_btn = ttk.Button(btn_frame, text="Run Full Setup", command=self.run_full_setup)
        self.setup_btn.pack(side='left', padx=5)

        self.font_btn = ttk.Button(btn_frame, text="Register Game Font", command=self.register_font)
        self.font_btn.pack(side='left', padx=5)

        self.run_btn = ttk.Button(btn_frame, text="Run Game", command=self.run_game)
        self.run_btn.pack(side='left', padx=5)

        self.exit_btn = ttk.Button(btn_frame, text="Exit", command=self.destroy)
        self.exit_btn.pack(side='left', padx=5)

    def log(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message)
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')
        self.update()

    def run_full_setup(self):
        self.setup_btn.config(state='disabled')
        self.log("="*60 + "\n")
        self.log("Starting virtual environment setup...\n")

        if not venv_exists():
            if not create_venv(self.log):
                messagebox.showerror("Error", "Failed to create virtual environment.")
                self.setup_btn.config(state='normal')
                return
        else:
            self.log("✓ Virtual environment already exists.\n")

        if not upgrade_pip(self.log):
            messagebox.showerror("Error", "Failed to upgrade pip.")
            self.setup_btn.config(state='normal')
            return

        if not install_dependencies(self.log):
            messagebox.showerror("Error", "Failed to install dependencies.")
            self.setup_btn.config(state='normal')
            return

        register_game_font("data/assets/fonts/Game_Font_Main.ttf", self.log)
        self.log("\n✓ Setup completed successfully!\n" + "="*60 + "\n")
        self.setup_btn.config(state='normal')

    def register_font(self):
        font_file = filedialog.askopenfilename(title="Select TTF Font", filetypes=[("TTF files", "*.ttf")])
        if font_file:
            register_game_font(font_file, self.log)

    def run_game(self):
        if not venv_exists():
            messagebox.showwarning("Warning", "Virtual environment not found. Please run setup first.")
            return
        python_exe = get_python_executable()
        main_py = os.path.join(os.path.dirname(__file__), "main.py")
        if not os.path.exists(main_py):
            messagebox.showerror("Error", "main.py not found in project directory!")
            return
        self.log(f"Launching game with {python_exe}...\n")
        try:
            subprocess.Popen([python_exe, main_py])
            self.log("✓ Game launched successfully.\n")
        except Exception as e:
            self.log(f"✗ Failed to launch game: {e}\n")

if __name__ == "__main__":
    app = SetupGUI()
    app.mainloop()