import tkinter as tk
from tkinter import Menu, colorchooser
import time
import os
import sys
import json
import threading
import ctypes
from PIL import Image
import pystray

# Windows API constants
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
ERROR_ALREADY_EXISTS = 183
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_RUN_NAME = "DesktopDigitalClock_AsR"

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def remove_from_taskbar(window):
    """Guarantees the window will never appear on the Windows Taskbar."""
    try:
        window.update_idletasks()
        user32 = ctypes.windll.user32
        try:
            hwnd = int(window.wm_frame(), 16)
        except Exception:
            hwnd = user32.GetParent(window.winfo_id())
            if not hwnd:
                hwnd = window.winfo_id()
                
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        # Notify Windows Shell to update taskbar state immediately
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
    except Exception:
        pass

class DesktopDigitalClock:
    def __init__(self, master):
        self.master = master  # Hidden base Tk window
        
        # Window attributes: frameless, floating toplevel, always on top
        self.root = tk.Toplevel(self.master)
        self.root.title("Desktop Digital Clock")
        self.root.overrideredirect(True)
        
        # System Tray icon path
        self.ico_path = resource_path("clock.ico")
        
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
        self.font_family = "Segoe UI" # Default Font
        self.is_24hr = False
        self.show_seconds = True      # Show/Hide seconds
        self.is_locked = False        # Lock position toggle
        self.always_on_top = True
        self.bg_mode = "auto"         # Auto-detects wallpaper/screen luminance by default
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
            font=(self.font_family, int(self.base_time_size * self.scale), "bold"), 
            fg=self.text_color,
            cursor="fleur" if not self.is_locked else "arrow"
        )
        self.time_label.pack()

        # Date Label
        self.date_label = tk.Label(
            self.frame, 
            font=(self.font_family, max(8, int(self.base_date_size * self.scale))),
            cursor="fleur" if not self.is_locked else "arrow"
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
            widget.bind("<Double-Button-1>", self.on_double_click)

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

        # Initial positioning
        self.apply_position()
        self.update_time()

        # One-time background check at startup, and a single follow-up check after 2 minutes (then fixed)
        self.master.after(120000, self.check_auto_bg_once)

        # Remove window from Windows Taskbar completely
        remove_from_taskbar(self.root)

        # Start System Tray Icon
        self.tray_icon = None
        self.start_system_tray()

    # --- Double Click Action ---
    def on_double_click(self, event=None):
        """Open Windows Clock/Alarms application on double click, or fallback to toggle format."""
        try:
            os.startfile("ms-clock:")
        except Exception:
            self.toggle_format()

    # --- Windows Autostart (Run on Startup) ---
    def is_autostart_enabled(self):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, REG_RUN_NAME)
                return bool(val)
        except Exception:
            return False

    def toggle_autostart(self):
        import winreg
        try:
            if self.is_autostart_enabled():
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, REG_RUN_NAME)
            else:
                if getattr(sys, 'frozen', False):
                    cmd = f'"{sys.executable}"'
                else:
                    script_path = os.path.abspath(__file__)
                    python_exe = sys.executable
                    pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
                    if os.path.exists(pythonw):
                        cmd = f'"{pythonw}" "{script_path}"'
                    else:
                        cmd = f'"{python_exe}" "{script_path}"'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, REG_RUN_NAME, 0, winreg.REG_SZ, cmd)
        except Exception:
            pass

    # --- Lock Position ---
    def toggle_lock_position(self):
        self.is_locked = not self.is_locked
        cursor = "arrow" if self.is_locked else "fleur"
        for w in (self.frame, self.time_label, self.date_label):
            try:
                w.config(cursor=cursor)
            except Exception:
                pass
        if self.is_locked:
            self.grip.place_forget()
        self.save_config()

    # --- Toggle Seconds ---
    def toggle_seconds(self):
        self.show_seconds = not self.show_seconds
        self.update_time()
        self.save_config()

    # --- Font Family Selection ---
    def set_font_family(self, font_name):
        self.font_family = font_name
        self.set_scale(self.scale, save=True)

    # --- System Tray Integration ---
    def create_tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Desktop Digital Clock by AsR", lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show / Hide Clock", self.toggle_visibility_from_tray, default=True),
            pystray.MenuItem(lambda text: "✓ 24h Format" if self.is_24hr else "12h Format (AM/PM)", lambda icon, item: self.master.after(0, self.toggle_format)),
            pystray.MenuItem(lambda text: "✓ Show Seconds" if self.show_seconds else "Show Seconds", lambda icon, item: self.master.after(0, self.toggle_seconds)),
            pystray.MenuItem(lambda text: "🔒 Lock Position" if self.is_locked else "Lock Position", lambda icon, item: self.master.after(0, self.toggle_lock_position)),
            pystray.MenuItem(lambda text: "✓ Start with Windows" if self.is_autostart_enabled() else "Start with Windows", lambda icon, item: self.master.after(0, self.toggle_autostart)),
            pystray.MenuItem("Change Color", lambda icon, item: self.master.after(0, self.pick_color)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("About", lambda icon, item: self.master.after(0, self.show_about)),
            pystray.MenuItem("Exit Clock", self.exit_from_tray)
        )

    def start_system_tray(self):
        try:
            if os.path.exists(self.ico_path):
                img = Image.open(self.ico_path)
            else:
                img = Image.new("RGBA", (32, 32), (0, 255, 204, 255))

            self.tray_icon = pystray.Icon(
                "DesktopDigitalClock_AsR",
                img,
                "Desktop Digital Clock by AsR",
                menu=self.create_tray_menu()
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
        remove_from_taskbar(self.root)
        self.is_visible = True

    def hide_clock(self):
        self.root.withdraw()
        self.is_visible = False

    def exit_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
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
        if self.is_locked:
            return
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
    def check_auto_bg_once(self):
        """Single follow-up check 2 minutes after startup, then permanently fixed."""
        if self.bg_mode == "auto":
            self.apply_bg_mode("auto", save=False)

    def detect_background_is_light(self):
        """Returns True if the desktop area under the clock is bright/white, False if dark."""
        try:
            import winreg
            wp_path = None
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as k:
                    wp_path = winreg.QueryValueEx(k, "WallPaper")[0]
            except Exception:
                pass

            if wp_path and os.path.exists(wp_path):
                with Image.open(wp_path) as im:
                    sw = self.root.winfo_screenwidth()
                    sh = self.root.winfo_screenheight()
                    if sw > 0 and sh > 0:
                        iw, ih = im.size
                        cx = max(0, min(sw - 10, self.root.winfo_x()))
                        cy = max(0, min(sh - 10, self.root.winfo_y()))
                        cw = max(20, self.root.winfo_width())
                        ch = max(20, self.root.winfo_height())
                        
                        box = (
                            int(cx / sw * iw),
                            int(cy / sh * ih),
                            min(iw, int((cx + cw) / sw * iw)),
                            min(ih, int((cy + ch) / sh * ih))
                        )
                        if box[2] > box[0] and box[3] > box[1]:
                            crop = im.crop(box)
                        else:
                            crop = im
                        
                        thumb = crop.resize((15, 15))
                        pixels = list(thumb.getdata())
                        avg_lum = sum(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in pixels) / len(pixels)
                        return avg_lum > 130
        except Exception:
            pass

        # Fallback: check Windows system theme (1 = Light, 0 = Dark)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                val = winreg.QueryValueEx(k, "AppsUseLightTheme")[0]
                return val == 1
        except Exception:
            return False

    def apply_bg_mode(self, mode, save=True):
        self.bg_mode = mode
        effective_mode = mode
        if mode == "auto":
            effective_mode = "transparent_light" if self.detect_background_is_light() else "transparent_dark"

        if effective_mode == "card":
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
        elif effective_mode == "transparent_light":
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
        else: # transparent_dark
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
        is_light = (self.bg_mode == "transparent_light") or (self.bg_mode == "auto" and self.detect_background_is_light())
        if self.bg_mode == "card":
            self.grip.config(fg="#4E5569")
        elif is_light:
            self.grip.config(fg="#999999")
        else:
            self.grip.config(fg="#454D5A")

    # --- Position Management (Multi-Monitor aware) ---
    def apply_position(self):
        try:
            user32 = ctypes.windll.user32
            v_x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
            v_y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
            v_w = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            v_h = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        except Exception:
            v_x, v_y = 0, 0
            v_w = self.root.winfo_screenwidth()
            v_h = self.root.winfo_screenheight()

        if hasattr(self, 'saved_x') and hasattr(self, 'saved_y') and self.saved_x is not None and self.saved_y is not None:
            x = self.saved_x
            y = self.saved_y
            if x < v_x - 50 or x > (v_x + v_w) - 50:
                x = (v_x + v_w) - 380
            if y < v_y - 50 or y > (v_y + v_h) - 50:
                y = v_y + 60
        else:
            x = self.root.winfo_screenwidth() - 380
            y = 60
            
        self.root.geometry(f"+{int(x)}+{int(y)}")

    # --- Drag & Move ---
    def start_move(self, event):
        if self.is_locked:
            return
        self._offset_x = event.x
        self._offset_y = event.y

    def do_move(self, event):
        if self.is_locked:
            return
        x = self.root.winfo_x() + (event.x - self._offset_x)
        y = self.root.winfo_y() + (event.y - self._offset_y)
        self.root.geometry(f"+{x}+{y}")

    def end_move(self, event):
        if self.is_locked:
            return
        if self.bg_mode == "auto":
            self.apply_bg_mode("auto", save=False)
        self.save_config()

    # --- Resize Functionality ---
    def start_resize(self, event):
        if self.is_locked:
            return
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_scale = self.scale

    def do_resize(self, event):
        if self.is_locked:
            return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        delta = (dx + dy) / 280.0
        new_scale = self._resize_start_scale + delta
        self.set_scale(new_scale, save=False)

    def end_resize(self, event):
        if self.is_locked:
            return
        self.save_config()

    def change_scale(self, delta):
        if self.is_locked:
            return
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
        self.time_label.config(font=(self.font_family, time_size, "bold"))
        self.date_label.config(font=(self.font_family, date_size))
        self.grip.config(font=("Segoe UI", grip_size))
        
        self.root.update_idletasks()
        if save:
            self.save_config()

    # --- Context Menu & Actions ---
    def build_context_menu(self):
        menu = Menu(self.root, tearoff=0)
        
        # Background Style submenu
        bg_menu = Menu(menu, tearoff=0)
        bg_menu.add_command(
            label=("✓ " if self.bg_mode == "auto" else "   ") + "⚡ Auto Detect (Adapts to Wallpaper)", 
            command=lambda: self.apply_bg_mode("auto")
        )
        bg_menu.add_separator()
        bg_menu.add_command(
            label=("✓ " if self.bg_mode == "transparent_dark" else "   ") + "Pure Transparent (Dark Screen)", 
            command=lambda: self.apply_bg_mode("transparent_dark")
        )
        bg_menu.add_command(
            label=("✓ " if self.bg_mode == "transparent_light" else "   ") + "Pure Transparent (Light Screen)", 
            command=lambda: self.apply_bg_mode("transparent_light")
        )
        bg_menu.add_command(
            label=("✓ " if self.bg_mode == "card" else "   ") + "Sleek Widget Card", 
            command=lambda: self.apply_bg_mode("card")
        )
        menu.add_cascade(label="Background Style", menu=bg_menu)

        # Font Style submenu
        font_menu = Menu(menu, tearoff=0)
        fonts = [
            ("Segoe UI", "Modern Clean (Segoe UI)"),
            ("Consolas", "Digital Monospace (Consolas)"),
            ("Bahnschrift", "Tech Sans (Bahnschrift)"),
            ("Arial", "Classic Sans (Arial)")
        ]
        for fname, flabel in fonts:
            chk = "✓ " if self.font_family == fname else "   "
            font_menu.add_command(
                label=f"{chk}{flabel}",
                command=lambda f=fname: self.set_font_family(f)
            )
        menu.add_cascade(label="Font Style", menu=font_menu)

        # Size submenu
        size_menu = Menu(menu, tearoff=0)
        size_menu.add_command(label="Make Bigger (Ctrl +)", command=lambda: self.change_scale(0.1))
        size_menu.add_command(label="Make Smaller (Ctrl -)", command=lambda: self.change_scale(-0.1))
        size_menu.add_separator()
        size_menu.add_command(label="Mini (60%)", command=lambda: self.set_scale(0.6))
        size_menu.add_command(label="Small (80%)", command=lambda: self.set_scale(0.8))
        size_menu.add_command(label="Medium / Normal (100%)", command=lambda: self.set_scale(1.0))
        size_menu.add_command(label="Large (130%)", command=lambda: self.set_scale(1.3))
        size_menu.add_command(label="Extra Large (160%)", command=lambda: self.set_scale(1.6))
        size_menu.add_separator()
        size_menu.add_command(label="Reset to Default Size (Ctrl 0)", command=lambda: self.set_scale(1.0))
        menu.add_cascade(label="Resize Clock", menu=size_menu)

        menu.add_command(label="Change Clock Color", command=self.pick_color)
        
        # 12h / 24h
        fmt_txt = "✓ 24-Hour Format" if self.is_24hr else "12-Hour Format (AM/PM)"
        menu.add_command(label=fmt_txt, command=self.toggle_format)

        # Show / Hide Seconds
        sec_txt = "✓ Show Seconds" if self.show_seconds else "Show Seconds"
        menu.add_command(label=sec_txt, command=self.toggle_seconds)

        # Always on Top
        top_txt = "✓ Always on Top" if self.always_on_top else "Always on Top"
        menu.add_command(label=top_txt, command=self.toggle_topmost)

        # Lock Position
        lock_txt = "🔒 Lock Position" if self.is_locked else "🔓 Lock Position"
        menu.add_command(label=lock_txt, command=self.toggle_lock_position)

        # Start with Windows
        auto_txt = "✓ Start with Windows" if self.is_autostart_enabled() else "Start with Windows"
        menu.add_command(label=auto_txt, command=self.toggle_autostart)

        menu.add_separator()
        menu.add_command(label="Hide to System Tray", command=self.hide_clock)
        menu.add_command(label="About Desktop Digital Clock", command=self.show_about)
        menu.add_command(label="Exit Clock", command=self.exit_app)
        
        return menu

    def show_context_menu(self, event):
        menu = self.build_context_menu()
        menu.post(event.x_root, event.y_root)

    def pick_color(self):
        color = colorchooser.askcolor(parent=self.root, color=self.text_color, title="Choose Clock Color")[1]
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
                    self.font_family = data.get("font_family", "Segoe UI")
                    self.is_24hr = data.get("is_24hr", False)
                    self.show_seconds = data.get("show_seconds", True)
                    self.is_locked = data.get("is_locked", False)
                    self.always_on_top = data.get("always_on_top", True)
                    self.bg_mode = data.get("bg_mode", "auto")
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
                "font_family": self.font_family,
                "is_24hr": self.is_24hr,
                "show_seconds": self.show_seconds,
                "is_locked": self.is_locked,
                "always_on_top": self.always_on_top,
                "bg_mode": self.bg_mode,
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
        about_win.geometry("420x330")
        about_win.resizable(False, False)
        about_win.configure(bg="#1E1E2E")
        about_win.attributes("-topmost", True)
        about_win.transient(self.root)
        remove_from_taskbar(about_win)
        
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
            text="Version 1.3.0 (x64 Release)", 
            font=("Segoe UI", 10), 
            fg="#AAAAAA", 
            bg="#1E1E2E"
        )
        ver_lbl.pack()

        desc_lbl = tk.Label(
            about_win, 
            text="A clean, floating, resizable desktop digital clock with System Tray and multi-font support.", 
            font=("Segoe UI", 10), 
            fg="#CCCCCC", 
            bg="#1E1E2E",
            wraplength=360
        )
        desc_lbl.pack(pady=(6, 4))

        tips_lbl = tk.Label(
            about_win, 
            text="💡 Tips: Double-click to open Windows Clock/Alarms.\nRight-click for Lock Position, Seconds toggle & Font Styles.\nHover mouse over clock to see resize handle (⤡).", 
            font=("Segoe UI", 9, "italic"), 
            fg="#FFE066", 
            bg="#1E1E2E",
            justify="center",
            wraplength=360
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
        copy_lbl.pack(pady=(2, 10))

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
            fmt = "%H:%M:%S" if self.show_seconds else "%H:%M"
        else:
            fmt = "%I:%M:%S %p" if self.show_seconds else "%I:%M %p"
            
        t_str = time.strftime(fmt, now)
        d_str = time.strftime("%a, %d %b %Y", now)

        self.time_label.config(text=t_str)
        self.date_label.config(text=d_str)

        self.root.after(200, self.update_time)

if __name__ == "__main__":
    # Prevent multiple instances using a Windows named mutex
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "DesktopDigitalClock_AsR_SingleInstance_Mutex")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        # An instance is already running! Exit silently so duplicate clocks don't appear.
        sys.exit(0)

    base_root = tk.Tk()
    base_root.withdraw()  # Hidden master window
    app = DesktopDigitalClock(base_root)
    base_root.mainloop()
