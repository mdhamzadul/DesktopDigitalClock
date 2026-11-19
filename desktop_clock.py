import tkinter as tk
from tkinter import Menu, colorchooser
import time
import os
import sys
import json
import threading
from PIL import Image
import pystray

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class DesktopDigitalClock:
    def __init__(self, master):
        self.master = master  # Hidden base Tk window (prevents taskbar icon)
        
        # Window attributes: frameless, floating toplevel, always on top
        self.root = tk.Toplevel(self.master)
        self.root.title("Desktop Digital Clock")
        self.root.overrideredirect(True)
        
        # Set application icon if available
        self.ico_path = resource_path("clock.ico")
        if os.path.exists(self.ico_path):
            try:
                self.root.iconbitmap(self.ico_path)
            except Exception:
                pass
        
        # Base dimensions and typography
        self.base_time_size = 44
        self.base_date_size = 12
        self.base_pad_x = 18
        self.base_pad_y = 8
        self.min_scale = 0.45
        self.max_scale = 2.4
        
        # Default Settings
        self.scale = 1.0
        self.text_color = "#00FFCC"   # Neon Cyan
        self.is_24hr = False
        self.always_on_top = True
        self.bg_mode = "transparent_dark"  # Default frameless transparent for dark screen
        self.short_date = True             # Short date: 'Thu, 19 Nov 2026'
        self.is_visible = True
        
        # Load user configuration if previously saved
        self.config_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "DesktopDigitalClock_AsR"
        )
        self.config_file = os.path.join(self.config_dir, "clock_config.json")
        self.load_config()

        self.root.attributes("-topmost", self.always_on_top)

        # Container Frame
        self.frame = tk.Frame(
            self.root, 
            padx=int(self.base_pad_x * self.scale), 
            pady=int(self.base_pad_y * self.scale)
        )
        self.frame.pack(padx=2, pady=2)

        # Time Label
        self.time_label = tk.Label(
            self.frame, 
            font=("Segoe UI", int(self.base_time_size * self.scale), "bold"), 
            fg=self.text_color,
            cursor="fleur"
        )
        self.time_label.pack()

        # Date Label
        self.date_label = tk.Label(
            self.frame, 
            font=("Segoe UI", max(8, int(self.base_date_size * self.scale))),
            cursor="fleur"
        )
        self.date_label.pack(pady=(0, 2))

        # Resize grip handle at bottom-right corner (⤡) - Hidden by default, shows on hover
        self.grip = tk.Label(
            self.frame,
            text="⤡",
            font=("Segoe UI", max(8, int(10 * self.scale))),
            cursor="size_nw_se"
        )

        # Apply Background Style & Transparency
        self.apply_bg_mode(self.bg_mode, save=False)

        # Mouse Drag & Move Bindings
        self._offset_x = 0
        self._offset_y = 0
        for widget in (self.frame, self.time_label, self.date_label):
            widget.bind("<ButtonPress-1>", self.start_move)
            widget.bind("<B1-Motion>", self.do_move)
            widget.bind("<ButtonRelease-1>", self.end_move)
            widget.bind("<Button-3>", self.show_context_menu)

        # Hover-only visibility for Resize Grip (shows only when mouse is over clock)
        for w in (self.root, self.frame, self.time_label, self.date_label):
            w.bind("<Enter>", self.show_grip, add="+")
            w.bind("<Leave>", self.hide_grip, add="+")

        # Mouse Resize Bindings on Grip
        self.grip.bind("<ButtonPress-1>", self.start_resize)
        self.grip.bind("<B1-Motion>", self.do_resize)
        self.grip.bind("<ButtonRelease-1>", self.end_resize)
        self.grip.bind("<Enter>", lambda e: self.grip.config(fg=self.text_color))
        self.grip.bind("<Leave>", lambda e: self.update_grip_color())

        # Global Keyboard Shortcuts
        self.root.bind("<Control-plus>", lambda e: self.change_scale(0.1))
        self.root.bind("<Control-equal>", lambda e: self.change_scale(0.1))
        self.root.bind("<Control-minus>", lambda e: self.change_scale(-0.1))
        self.root.bind("<Control-0>", lambda e: self.set_scale(1.0))

        # Right-click Context Menu on Clock
        self.menu = Menu(self.root, tearoff=0)
        
        # Background Style submenu
        self.bg_menu = Menu(self.menu, tearoff=0)
        self.bg_menu.add_command(
            label="Pure Transparent (For Dark Desktop / Screen)", 
            command=lambda: self.apply_bg_mode("transparent_dark")
        )
        self.bg_menu.add_command(
            label="Pure Transparent (For White / Light Screens)", 
            command=lambda: self.apply_bg_mode("transparent_light")
        )
        self.bg_menu.add_command(
            label="Sleek Widget Card (Clean on All Screens)", 
            command=lambda: self.apply_bg_mode("card")
        )
        self.menu.add_cascade(label="Background Style", menu=self.bg_menu)

        # Size submenu
        self.size_menu = Menu(self.menu, tearoff=0)
        self.size_menu.add_command(label="Make Bigger (Ctrl +)", command=lambda: self.change_scale(0.1))
        self.size_menu.add_command(label="Make Smaller (Ctrl -)", command=lambda: self.change_scale(-0.1))
        self.size_menu.add_separator()
        self.size_menu.add_command(label="Mini (60%)", command=lambda: self.set_scale(0.6))
        self.size_menu.add_command(label="Small (80%)", command=lambda: self.set_scale(0.8))
        self.size_menu.add_command(label="Medium / Normal (100%)", command=lambda: self.set_scale(1.0))
        self.size_menu.add_command(label="Large (130%)", command=lambda: self.set_scale(1.3))
        self.size_menu.add_command(label="Extra Large (160%)", command=lambda: self.set_scale(1.6))
        self.size_menu.add_separator()
        self.size_menu.add_command(label="Reset to Default Size", command=lambda: self.set_scale(1.0))
        
        self.menu.add_cascade(label="Resize Clock", menu=self.size_menu)
        self.menu.add_command(label="Toggle Date Format (Short / Full)", command=self.toggle_date_format)
        self.menu.add_command(label="Change Clock Color", command=self.pick_color)
        self.menu.add_command(label="Toggle 12h / 24h", command=self.toggle_format)
        self.menu.add_command(label="Toggle Always on Top", command=self.toggle_topmost)
        self.menu.add_separator()
        self.menu.add_command(label="Hide to System Tray", command=self.hide_clock)
        self.menu.add_command(label="About Desktop Digital Clock", command=self.show_about)
        self.menu.add_command(label="Exit Clock", command=self.exit_app)

        # Initial positioning
        self.apply_position()
        self.update_time()

        # Start System Tray Icon
        self.tray_icon = None
        self.start_system_tray()

    # --- System Tray Integration ---
    def start_system_tray(self):
        try:
            if os.path.exists(self.ico_path):
                img = Image.open(self.ico_path)
            else:
                img = Image.new("RGBA", (32, 32), (0, 255, 204, 255))

            tray_menu = pystray.Menu(
                pystray.MenuItem("Desktop Digital Clock by AsR", lambda icon, item: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Show / Hide Clock", self.toggle_visibility_from_tray, default=True),
                pystray.MenuItem("Change Color", lambda icon, item: self.master.after(0, self.pick_color)),
                pystray.MenuItem("Toggle 12h / 24h", lambda icon, item: self.master.after(0, self.toggle_format)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("About", lambda icon, item: self.master.after(0, self.show_about)),
                pystray.MenuItem("Exit Clock", self.exit_from_tray)
            )

            self.tray_icon = pystray.Icon(
                "DesktopDigitalClock_AsR",
                img,
                "Desktop Digital Clock by AsR",
                tray_menu
            )
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception:
            pass

    def toggle_visibility_from_tray(self, icon=None, item=None):
        if self.is_visible:
            self.master.after(0, self.hide_clock)
        else:
            self.master.after(0, self.show_clock)

    def show_clock(self):
        self.root.deiconify()
        self.root.attributes("-topmost", self.always_on_top)
        self.is_visible = True

    def hide_clock(self):
        self.root.withdraw()
        self.is_visible = False

    def exit_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.master.after(0, self.master.destroy)

    def exit_app(self):
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.master.destroy()

    # --- Hover-only Grip Logic ---
    def show_grip(self, event=None):
        self.grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.grip.lift()

    def hide_grip(self, event=None):
        try:
            x, y = self.root.winfo_pointerxy()
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
                self.grip.place_forget()
        except Exception:
            self.grip.place_forget()

    # --- Background Styles & Clean Antialiasing ---
    def apply_bg_mode(self, mode, save=True):
        self.bg_mode = mode
        if mode == "card":
            chroma = "#000001"
            card_bg = "#151722"
            self.root.configure(bg=chroma)
            try:
                self.root.wm_attributes("-transparentcolor", chroma)
                self.root.attributes("-alpha", 0.92)
            except Exception:
                pass
            self.frame.configure(bg=card_bg, highlightthickness=1, highlightbackground="#2A2F40")
            self.time_label.configure(bg=card_bg)
            self.date_label.configure(bg=card_bg, fg="#D8DCE5")
            self.grip.configure(bg=card_bg, fg="#4E5569")
        elif mode == "transparent_light":
            bg = "#FFFFFF"
            self.root.configure(bg=bg)
            try:
                self.root.wm_attributes("-transparentcolor", bg)
                self.root.attributes("-alpha", 1.0)
            except Exception:
                pass
            self.frame.configure(bg=bg, highlightthickness=0)
            self.time_label.configure(bg=bg)
            self.date_label.configure(bg=bg, fg="#22252C")
            self.grip.configure(bg=bg, fg="#999999")
        else: # transparent_dark (default)
            self.bg_mode = "transparent_dark"
            bg = "#101216"
            self.root.configure(bg=bg)
            try:
                self.root.wm_attributes("-transparentcolor", bg)
                self.root.attributes("-alpha", 1.0)
            except Exception:
                pass
            self.frame.configure(bg=bg, highlightthickness=0)
            self.time_label.configure(bg=bg)
            self.date_label.configure(bg=bg, fg="#D8DCE5")
            self.grip.configure(bg=bg, fg="#454D5A")

        self.root.update_idletasks()
        if save:
            self.save_config()

    def update_grip_color(self):
        if self.bg_mode == "transparent_light":
            self.grip.config(fg="#999999")
        elif self.bg_mode == "card":
            self.grip.config(fg="#4E5569")
        else:
            self.grip.config(fg="#454D5A")

    # --- Position Management ---
    def apply_position(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        # Check if saved pos is valid
        if hasattr(self, 'saved_x') and hasattr(self, 'saved_y'):
            x = self.saved_x
            y = self.saved_y
            if x < -50 or x > screen_w - 50:
                x = screen_w - 380
            if y < 0 or y > screen_h - 50:
                y = 60
        else:
            x = screen_w - 380
            y = 60
            
        self.root.geometry(f"+{int(x)}+{int(y)}")

    # --- Drag & Move ---
    def start_move(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self._offset_x)
        y = self.root.winfo_y() + (event.y - self._offset_y)
        self.root.geometry(f"+{x}+{y}")

    def end_move(self, event):
        self.save_config()

    # --- Resize Functionality ---
    def start_resize(self, event):
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_scale = self.scale

    def do_resize(self, event):
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        delta = (dx + dy) / 280.0
        new_scale = self._resize_start_scale + delta
        self.set_scale(new_scale, save=False)

    def end_resize(self, event):
        self.save_config()

    def change_scale(self, delta):
        self.set_scale(self.scale + delta)

    def set_scale(self, new_scale, save=True):
        self.scale = max(self.min_scale, min(self.max_scale, round(new_scale, 2)))
        
        # Update fonts & padding
        time_size = max(16, int(self.base_time_size * self.scale))
        date_size = max(8, int(self.base_date_size * self.scale))
        pad_x = max(6, int(self.base_pad_x * self.scale))
        pad_y = max(4, int(self.base_pad_y * self.scale))
        grip_size = max(7, int(10 * self.scale))
        
        self.frame.config(padx=pad_x, pady=pad_y)
        self.time_label.config(font=("Segoe UI", time_size, "bold"))
        self.date_label.config(font=("Segoe UI", date_size))
        self.grip.config(font=("Segoe UI", grip_size))
        
        self.root.update_idletasks()
        if save:
            self.save_config()

    # --- Context Menu & Actions ---
    def show_context_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def toggle_date_format(self):
        self.short_date = not self.short_date
        self.update_time()
        self.save_config()

    def pick_color(self):
        color = colorchooser.askcolor(color=self.text_color, title="Choose Clock Color")[1]
        if color:
            self.text_color = color
            self.time_label.config(fg=self.text_color)
            self.save_config()

    def toggle_format(self):
        self.is_24hr = not self.is_24hr
        self.update_time()
        self.save_config()

    def toggle_topmost(self):
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        self.save_config()

    # --- Settings Persistence ---
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.scale = data.get("scale", 1.0)
                    self.text_color = data.get("text_color", "#00FFCC")
                    self.is_24hr = data.get("is_24hr", False)
                    self.always_on_top = data.get("always_on_top", True)
                    self.bg_mode = data.get("bg_mode", "transparent_dark")
                    self.short_date = data.get("short_date", True)
                    self.saved_x = data.get("x")
                    self.saved_y = data.get("y")
        except Exception:
            pass

    def save_config(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            data = {
                "scale": self.scale,
                "text_color": self.text_color,
                "is_24hr": self.is_24hr,
                "always_on_top": self.always_on_top,
                "bg_mode": self.bg_mode,
                "short_date": self.short_date,
                "x": self.root.winfo_x(),
                "y": self.root.winfo_y()
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About Desktop Digital Clock")
        about_win.geometry("400x300")
        about_win.resizable(False, False)
        about_win.configure(bg="#1E1E2E")
        about_win.attributes("-topmost", True)
        if os.path.exists(self.ico_path):
            try:
                about_win.iconbitmap(self.ico_path)
            except Exception:
                pass
        
        x = self.root.winfo_x() + 20
        y = self.root.winfo_y() + 20
        about_win.geometry(f"+{x}+{y}")

        title_lbl = tk.Label(
            about_win, 
            text="Desktop Digital Clock", 
            font=("Segoe UI", 16, "bold"), 
            fg=self.text_color, 
            bg="#1E1E2E"
        )
        title_lbl.pack(pady=(16, 2))

        ver_lbl = tk.Label(
            about_win, 
            text="Version 1.2.0 (x64 Release)", 
            font=("Segoe UI", 10), 
            fg="#AAAAAA", 
            bg="#1E1E2E"
        )
        ver_lbl.pack()

        desc_lbl = tk.Label(
            about_win, 
            text="A clean, floating, resizable desktop digital clock with System Tray support.", 
            font=("Segoe UI", 10), 
            fg="#CCCCCC", 
            bg="#1E1E2E",
            wraplength=340
        )
        desc_lbl.pack(pady=(6, 4))

        tips_lbl = tk.Label(
            about_win, 
            text="💡 Tip: Check the System Tray (notification area) for clock controls.\nHover mouse over clock to see resize handle (⤡).", 
            font=("Segoe UI", 9, "italic"), 
            fg="#FFE066", 
            bg="#1E1E2E",
            justify="center",
            wraplength=350
        )
        tips_lbl.pack(pady=(2, 6))

        author_lbl = tk.Label(
            about_win, 
            text="Developed & Signed by: AsR", 
            font=("Segoe UI", 11, "bold"), 
            fg="#55FFAA", 
            bg="#1E1E2E"
        )
        author_lbl.pack(pady=(2, 2))

        copy_lbl = tk.Label(
            about_win, 
            text="Copyright © 2026 AsR. All rights reserved.", 
            font=("Segoe UI", 9), 
            fg="#777777", 
            bg="#1E1E2E"
        )
        copy_lbl.pack(pady=(2, 12))

        btn = tk.Button(
            about_win, 
            text="OK", 
            width=12, 
            bg="#2B2D42", 
            fg="#FFFFFF", 
            relief="flat",
            activebackground="#3E4265",
            activeforeground="#FFFFFF",
            cursor="hand2",
            command=about_win.destroy
        )
        btn.pack()

    def update_time(self):
        now = time.localtime()
        if self.is_24hr:
            t_str = time.strftime("%H:%M:%S", now)
        else:
            t_str = time.strftime("%I:%M:%S %p", now)
            
        if self.short_date:
            d_str = time.strftime("%a, %d %b %Y", now)
        else:
            d_str = time.strftime("%A, %d %B %Y", now)

        self.time_label.config(text=t_str)
        self.date_label.config(text=d_str)

        self.root.after(200, self.update_time)

if __name__ == "__main__":
    base_root = tk.Tk()
    base_root.withdraw()  # Keeps app off Windows Taskbar!
    app = DesktopDigitalClock(base_root)
    base_root.mainloop()
