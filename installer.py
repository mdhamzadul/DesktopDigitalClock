import os
import sys
import shutil
import subprocess
import winreg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Determine resource path (works for dev and for PyInstaller bundled)
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def run_silent(cmd, wait=True, cwd=None):
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE (No console window)
        kwargs = {
            "creationflags": subprocess.CREATE_NO_WINDOW,
            "startupinfo": si,
            "cwd": cwd
        }
        if wait:
            kwargs["capture_output"] = True
            return subprocess.run(cmd, **kwargs)
        else:
            return subprocess.Popen(cmd, **kwargs)
    except Exception:
        return None

PAYLOAD_NAME = "DesktopDigitalClock_AsR.exe"

class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Setup - Desktop Digital Clock")
        self.geometry("540x390")
        self.resizable(False, False)
        
        ico = resource_path("clock.ico")
        if os.path.exists(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass
        
        # Default Install Path: %LOCALAPPDATA%\Programs\DesktopDigitalClock_AsR
        local_app = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.dest_dir = tk.StringVar(value=os.path.join(local_app, "Programs", "DesktopDigitalClock_AsR"))
        
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_start_shortcut = tk.BooleanVar(value=True)
        self.autostart = tk.BooleanVar(value=False)
        self.launch_app = tk.BooleanVar(value=True)
        
        self.current_page = 0
        self.pages = []
        
        self.setup_ui()
        self.show_page(0)

    def setup_ui(self):
        # Bottom Navigation Bar
        self.bottom_bar = tk.Frame(self, height=52, bd=1, relief="ridge", bg="#F0F0F0")
        self.bottom_bar.pack(side="bottom", fill="x")
        self.bottom_bar.pack_propagate(False)
        
        self.btn_cancel = tk.Button(self.bottom_bar, text="Cancel", width=10, command=self.on_cancel)
        self.btn_cancel.pack(side="right", padx=10, pady=10)
        
        self.btn_next = tk.Button(self.bottom_bar, text="Next >", width=10, command=self.go_next)
        self.btn_next.pack(side="right", padx=5, pady=10)
        
        self.btn_back = tk.Button(self.bottom_bar, text="< Back", width=10, command=self.go_back)
        self.btn_back.pack(side="right", padx=5, pady=10)

        # Main Content Area
        self.content_frame = tk.Frame(self, bg="#FFFFFF")
        self.content_frame.pack(side="top", fill="both", expand=True)

        # Build Pages
        self.pages.append(self.create_welcome_page())
        self.pages.append(self.create_location_page())
        self.pages.append(self.create_tasks_page())
        self.pages.append(self.create_ready_page())
        self.pages.append(self.create_installing_page())
        self.pages.append(self.create_finish_page())

    def create_sidebar(self, parent):
        side = tk.Frame(parent, width=165, bg="#1E1E2E")
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        
        tk.Label(side, text="🕒", font=("Segoe UI", 48), fg="#00FFCC", bg="#1E1E2E").pack(pady=(40, 10))
        tk.Label(side, text="Desktop\nDigital Clock", font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#1E1E2E").pack()
        tk.Label(side, text="by AsR", font=("Segoe UI", 10, "italic"), fg="#55FFAA", bg="#1E1E2E").pack(pady=(4, 0))
        return side

    # --- Page 0: Welcome ---
    def create_welcome_page(self):
        page = tk.Frame(self.content_frame, bg="#FFFFFF")
        self.create_sidebar(page)
        
        right = tk.Frame(page, bg="#FFFFFF", padx=20, pady=30)
        right.pack(side="right", fill="both", expand=True)
        
        tk.Label(right, text="Welcome to the Desktop\nDigital Clock Setup Wizard", font=("Segoe UI", 14, "bold"), justify="left", bg="#FFFFFF").pack(anchor="w")
        tk.Label(right, text="\nThis will install Desktop Digital Clock by AsR on your computer.\n\nIt is recommended that you close all other applications before continuing.\n\nClick Next to continue, or Cancel to exit Setup.", font=("Segoe UI", 9), justify="left", bg="#FFFFFF", wraplength=310).pack(anchor="w")
        return page

    # --- Page 1: Destination ---
    def create_location_page(self):
        page = tk.Frame(self.content_frame, bg="#FFFFFF", padx=25, pady=20)
        
        tk.Label(page, text="Select Destination Location", font=("Segoe UI", 12, "bold"), bg="#FFFFFF").pack(anchor="w")
        tk.Label(page, text="Where should Desktop Digital Clock be installed?", font=("Segoe UI", 9), bg="#FFFFFF").pack(anchor="w", pady=(0, 15))
        
        tk.Label(page, text="Setup will install Desktop Digital Clock into the following folder:", font=("Segoe UI", 9), bg="#FFFFFF").pack(anchor="w")
        
        entry_frame = tk.Frame(page, bg="#FFFFFF")
        entry_frame.pack(fill="x", pady=10)
        
        entry = tk.Entry(entry_frame, textvariable=self.dest_dir, font=("Segoe UI", 9))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        btn_browse = tk.Button(entry_frame, text="Browse...", width=10, command=self.browse_folder)
        btn_browse.pack(side="right")
        
        tk.Label(page, text="At least 15.0 MB of free disk space is required.", font=("Segoe UI", 9, "italic"), fg="#666666", bg="#FFFFFF").pack(anchor="w", pady=(15, 0))
        return page

    def browse_folder(self):
        f = filedialog.askdirectory(initialdir=self.dest_dir.get(), title="Select Destination Folder")
        if f:
            self.dest_dir.set(os.path.join(f, "DesktopDigitalClock_AsR"))

    # --- Page 2: Additional Tasks ---
    def create_tasks_page(self):
        page = tk.Frame(self.content_frame, bg="#FFFFFF", padx=25, pady=20)
        
        tk.Label(page, text="Select Additional Tasks", font=("Segoe UI", 12, "bold"), bg="#FFFFFF").pack(anchor="w")
        tk.Label(page, text="Which additional tasks should be performed?", font=("Segoe UI", 9), bg="#FFFFFF").pack(anchor="w", pady=(0, 15))
        
        tk.Label(page, text="Additional shortcuts:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w", pady=(5, 5))
        
        tk.Checkbutton(page, text="Create a desktop shortcut", variable=self.create_desktop_shortcut, font=("Segoe UI", 9), bg="#FFFFFF", activebackground="#FFFFFF").pack(anchor="w", padx=10)
        tk.Checkbutton(page, text="Create a Start Menu shortcut", variable=self.create_start_shortcut, font=("Segoe UI", 9), bg="#FFFFFF", activebackground="#FFFFFF").pack(anchor="w", padx=10)
        
        tk.Label(page, text="\nStartup options:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w", pady=(5, 5))
        tk.Checkbutton(page, text="Start Desktop Digital Clock when Windows starts", variable=self.autostart, font=("Segoe UI", 9), bg="#FFFFFF", activebackground="#FFFFFF").pack(anchor="w", padx=10)
        return page

    # --- Page 3: Ready to Install ---
    def create_ready_page(self):
        page = tk.Frame(self.content_frame, bg="#FFFFFF", padx=25, pady=20)
        
        tk.Label(page, text="Ready to Install", font=("Segoe UI", 12, "bold"), bg="#FFFFFF").pack(anchor="w")
        tk.Label(page, text="Setup is now ready to begin installing Desktop Digital Clock on your computer.", font=("Segoe UI", 9), bg="#FFFFFF").pack(anchor="w", pady=(0, 15))
        
        self.lbl_summary = tk.Label(page, text="", font=("Segoe UI", 9), justify="left", bg="#F8F8F8", relief="solid", bd=1, padx=10, pady=10)
        self.lbl_summary.pack(fill="both", expand=True)
        return page

    def update_summary(self):
        tasks = []
        if self.create_desktop_shortcut.get():
            tasks.append("• Create a desktop shortcut")
        if self.create_start_shortcut.get():
            tasks.append("• Create a Start Menu shortcut")
        if self.autostart.get():
            tasks.append("• Start when Windows starts")
        tasks_str = "\n".join(tasks) if tasks else "None"
        
        summary = (
            f"Destination location:\n  {self.dest_dir.get()}\n\n"
            f"Selected tasks:\n{tasks_str}\n\n"
            f"Publisher:\n  AsR\n\n"
            "Click Install to continue with the installation."
        )
        self.lbl_summary.config(text=summary)

    # --- Page 4: Installing ---
    def create_installing_page(self):
        page = tk.Frame(self.content_frame, bg="#FFFFFF", padx=25, pady=40)
        
        tk.Label(page, text="Installing...", font=("Segoe UI", 12, "bold"), bg="#FFFFFF").pack(anchor="w")
        self.lbl_status = tk.Label(page, text="Please wait while Setup installs Desktop Digital Clock...", font=("Segoe UI", 9), bg="#FFFFFF")
        self.lbl_status.pack(anchor="w", pady=(0, 20))
        
        self.progress = ttk.Progressbar(page, mode="determinate", length=480)
        self.progress.pack(pady=10)
        return page

    # --- Page 5: Finish ---
    def create_finish_page(self):
        page = tk.Frame(self.content_frame, bg="#FFFFFF")
        self.create_sidebar(page)
        
        right = tk.Frame(page, bg="#FFFFFF", padx=20, pady=30)
        right.pack(side="right", fill="both", expand=True)
        
        tk.Label(right, text="Completing the Desktop\nDigital Clock Setup", font=("Segoe UI", 14, "bold"), justify="left", bg="#FFFFFF").pack(anchor="w")
        tk.Label(right, text="\nDesktop Digital Clock has been successfully installed on your computer.\n\nDeveloped & Signed by AsR.\n", font=("Segoe UI", 9), justify="left", bg="#FFFFFF", wraplength=310).pack(anchor="w")
        
        tk.Checkbutton(right, text="Launch Desktop Digital Clock now", variable=self.launch_app, font=("Segoe UI", 9), bg="#FFFFFF", activebackground="#FFFFFF").pack(anchor="w", pady=15)
        return page

    def show_page(self, idx):
        for p in self.pages:
            p.pack_forget()
        
        self.current_page = idx
        self.pages[idx].pack(fill="both", expand=True)
        
        if idx == 0:
            self.btn_back.config(state="disabled")
            self.btn_next.config(text="Next >", state="normal")
            self.btn_cancel.config(state="normal")
        elif idx == 1 or idx == 2:
            self.btn_back.config(state="normal")
            self.btn_next.config(text="Next >", state="normal")
            self.btn_cancel.config(state="normal")
        elif idx == 3:
            self.update_summary()
            self.btn_back.config(state="normal")
            self.btn_next.config(text="Install", state="normal")
            self.btn_cancel.config(state="normal")
        elif idx == 4:
            self.btn_back.config(state="disabled")
            self.btn_next.config(state="disabled")
            self.btn_cancel.config(state="disabled")
            self.after(200, self.perform_installation)
        elif idx == 5:
            self.btn_back.config(state="disabled")
            self.btn_next.config(text="Finish", state="normal")
            self.btn_cancel.config(state="disabled")

    def go_next(self):
        if self.current_page == 3:
            self.show_page(4)
        elif self.current_page == 5:
            self.finish_setup()
        else:
            self.show_page(self.current_page + 1)

    def go_back(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def on_cancel(self):
        if messagebox.askyesno("Exit Setup", "Setup is not complete. Are you sure you want to exit?"):
            self.destroy()

    def perform_installation(self):
        target_dir = self.dest_dir.get()
        try:
            self.progress["value"] = 15
            self.lbl_status.config(text="Creating directories...")
            self.update()
            os.makedirs(target_dir, exist_ok=True)

            self.progress["value"] = 35
            self.lbl_status.config(text="Extracting files...")
            self.update()
            
            src_exe = resource_path(PAYLOAD_NAME)
            dest_exe = os.path.join(target_dir, PAYLOAD_NAME)
            
            # Stop running instance silently if any
            run_silent(["taskkill", "/f", "/im", PAYLOAD_NAME])
            import time
            time.sleep(0.5)
            
            shutil.copy2(src_exe, dest_exe)

            self.progress["value"] = 65
            self.lbl_status.config(text="Creating shortcuts...")
            self.update()

            # Create Desktop Shortcut
            if self.create_desktop_shortcut.get():
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                self.create_shortcut(dest_exe, os.path.join(desktop, "Desktop Digital Clock.lnk"), target_dir)

            # Create Start Menu Shortcut
            if self.create_start_shortcut.get():
                start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
                self.create_shortcut(dest_exe, os.path.join(start_menu, "Desktop Digital Clock.lnk"), target_dir)

            # Autostart in registry
            if self.autostart.get():
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "DesktopDigitalClock_AsR", 0, winreg.REG_SZ, f'"{dest_exe}"')
                    winreg.CloseKey(key)
                except Exception:
                    pass

            self.progress["value"] = 85
            self.lbl_status.config(text="Registering uninstaller in Windows...")
            self.update()

            # Create uninstaller batch & silent VBS launcher
            uninst_bat = os.path.join(target_dir, "uninstall.bat")
            with open(uninst_bat, "w", encoding="utf-8") as f:
                f.write(f'''@echo off
taskkill /f /im {PAYLOAD_NAME} >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DesktopDigitalClock_AsR" /f >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "DesktopDigitalClock_AsR" /f >nul 2>&1
del /f /q "{os.path.join(os.path.expanduser("~"), "Desktop", "Desktop Digital Clock.lnk")}" >nul 2>&1
del /f /q "{os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Desktop Digital Clock.lnk")}" >nul 2>&1
cd /d "%TEMP%"
timeout /t 1 >nul
rmdir /s /q "{target_dir}" >nul 2>&1
''')

            uninst_vbs = os.path.join(target_dir, "uninstall.vbs")
            with open(uninst_vbs, "w", encoding="utf-8") as f:
                f.write(f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "{uninst_bat}" & chr(34), 0, True
MsgBox "Desktop Digital Clock by AsR has been uninstalled successfully.", 64, "Desktop Digital Clock"
''')

            # Register in Windows Add/Remove Programs (silent uninstall via wscript)
            self.register_uninstall(target_dir, dest_exe, uninst_vbs)

            self.progress["value"] = 100
            self.lbl_status.config(text="Installation complete!")
            self.update()
            
            self.after(500, lambda: self.show_page(5))
        except Exception as e:
            messagebox.showerror("Installation Error", f"An error occurred during installation:\n{e}")
            self.destroy()

    def create_shortcut(self, target, lnk_path, work_dir):
        vbs = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{lnk_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.WorkingDirectory = "{work_dir}"
oLink.Description = "Desktop Digital Clock by AsR"
oLink.Save
'''
        vbs_path = os.path.join(os.environ.get("TEMP", "C:\\"), "create_lnk.vbs")
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs)
        run_silent(["wscript", "//nologo", vbs_path])
        try:
            os.remove(vbs_path)
        except Exception:
            pass

    def register_uninstall(self, install_dir, exe_path, uninst_vbs):
        try:
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\DesktopDigitalClock_AsR"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Desktop Digital Clock")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.3.0")
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "AsR")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, exe_path)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'wscript.exe "{uninst_vbs}"')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        except Exception:
            pass

    def finish_setup(self):
        if self.launch_app.get():
            target_exe = os.path.join(self.dest_dir.get(), PAYLOAD_NAME)
            if os.path.exists(target_exe):
                run_silent([target_exe], wait=False, cwd=self.dest_dir.get())
        self.destroy()

if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
