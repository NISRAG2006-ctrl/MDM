import tkinter as tk
import customtkinter as ctk
from datetime import datetime
import time
import os
import psutil
import logging
from collections import deque

# Import individual pages (we will write these files next)
from accelerometer import AccelerometerPage
from gyroscope import GyroscopePage
from magnetometer import MagnetometerPage
from color_sensor import ColorSensorPage
from gesture_sensor import GestureSensorPage
from proximity_sensor import ProximitySensorPage
from serial_manager import SerialManager

class Sparkline(tk.Canvas):
    """A lightweight canvas-based sparkline for showing sensor history."""
    def __init__(self, parent, color="#00E5FF", **kwargs):
        super().__init__(parent, bg="#181924", highlightthickness=0, **kwargs)
        self.color = color
        self.data = []

    def set_data(self, data):
        self.data = list(data)
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1: w = 180  # Default fallback width
        if h <= 1: h = 50   # Default fallback height

        if not self.data or len(self.data) < 2:
            # Draw placeholder center line
            self.create_line(0, h/2, w, h/2, fill="#2C2E3E", width=1, dash=(2, 2))
            return

        min_v = min(self.data)
        max_v = max(self.data)
        range_v = max_v - min_v if max_v != min_v else 1.0

        coords = []
        n = len(self.data)
        for i, val in enumerate(self.data):
            x = (i / (n - 1)) * w
            # Scale to fit canvas, leaving padding
            y = h - 6 - ((val - min_v) / range_v) * (h - 12)
            coords.append((x, y))

        # Draw line segments
        for i in range(len(coords) - 1):
            self.create_line(
                coords[i][0], coords[i][1],
                coords[i+1][0], coords[i+1][1],
                fill=self.color, width=2, smooth=True
            )

class SensorCard(ctk.CTkFrame):
    """Grid card shown on the Dashboard home page."""
    def __init__(self, parent, title, unit, color, **kwargs):
        super().__init__(parent, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12, **kwargs)
        self.title = title
        self.unit = unit
        self.color = color
        self.history = deque(maxlen=30)
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header Label
        self.title_lbl = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="#A9B1D6", anchor="w"
        )
        self.title_lbl.grid(row=0, column=0, padx=15, pady=(12, 2), sticky="w")

        # Value Label
        self.value_lbl = ctk.CTkLabel(
            self, text="---", font=ctk.CTkFont(size=22, weight="bold"), text_color="#FFFFFF", anchor="w"
        )
        self.value_lbl.grid(row=1, column=0, padx=15, pady=2, sticky="w")

        # Status & Time Label
        self.status_lbl = ctk.CTkLabel(
            self, text="Status: Standby | --:--:--", font=ctk.CTkFont(size=11), text_color="#565F89", anchor="w"
        )
        self.status_lbl.grid(row=2, column=0, padx=15, pady=(0, 8), sticky="w")

        # Mini sparkline graph
        self.sparkline = Sparkline(self, color=self.color, height=45)
        self.sparkline.grid(row=3, column=0, padx=15, pady=(5, 12), sticky="nsew")

    def update_value(self, value, value_str, is_active=True):
        self.value_lbl.configure(text=value_str)
        t_str = datetime.now().strftime("%H:%M:%S")
        status_text = "Status: Active" if is_active else "Status: Stale"
        self.status_lbl.configure(text=f"{status_text} | {t_str}")
        
        # Save to sparkline history
        if value is not None:
            self.history.append(value)
            self.sparkline.set_data(self.history)


class DashboardPage(ctk.CTkFrame):
    """Dashboard Home showing summary cards of all sensors."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        # Create cards
        self.cards = {
            "ACC": SensorCard(self, "Accelerometer", "G", "#00E5FF"),
            "GYR": SensorCard(self, "Gyroscope", "d/s", "#D500F9"),
            "MAG": SensorCard(self, "Magnetometer", "uT", "#FF9E00"),
            "CLR": SensorCard(self, "Color Sensor", "RGB", "#00E676"),
            "GST": SensorCard(self, "Gesture Sensor", "Event", "#FF1744"),
            "PRX": SensorCard(self, "Proximity Sensor", "Units", "#FFFF00")
        }

        # Grid placement: 2 rows, 3 columns
        sensor_keys = ["ACC", "GYR", "MAG", "CLR", "GST", "PRX"]
        idx = 0
        for r in range(2):
            for c in range(3):
                key = sensor_keys[idx]
                self.cards[key].grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
                idx += 1

    def update_sensor(self, prefix, numeric_val, display_str):
        if prefix in self.cards:
            self.cards[prefix].update_value(numeric_val, display_str, is_active=True)


class DataLoggerPage(ctk.CTkFrame):
    """View to control and display recorded sensor data logs."""
    def __init__(self, parent, logger, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.logger = logger
        self.raw_lines = deque(maxlen=100)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Control Panel
        self.ctrl_panel = ctk.CTkFrame(self, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.ctrl_panel.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Logging status light
        self.status_indicator = ctk.CTkLabel(
            self.ctrl_panel, text="● IDLE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FF1744"
        )
        self.status_indicator.pack(side="left", padx=20, pady=15)

        # Buttons
        self.btn_start = ctk.CTkButton(
            self.ctrl_panel, text="Start Logging", fg_color="#00E5FF", text_color="#0D0E15",
            hover_color="#00B2CC", font=ctk.CTkFont(weight="bold"), command=self._start
        )
        self.btn_start.pack(side="left", padx=10, pady=15)

        self.btn_stop = ctk.CTkButton(
            self.ctrl_panel, text="Stop Logging", fg_color="#4E5173", text_color="#FFFFFF",
            hover_color="#363953", state="disabled", font=ctk.CTkFont(weight="bold"), command=self._stop
        )
        self.btn_stop.pack(side="left", padx=10, pady=15)

        self.btn_clear = ctk.CTkButton(
            self.ctrl_panel, text="Clear Buffer", fg_color="#FF1744", text_color="#FFFFFF",
            hover_color="#D50000", font=ctk.CTkFont(weight="bold"), command=self._clear
        )
        self.btn_clear.pack(side="left", padx=10, pady=15)

        self.btn_export_csv = ctk.CTkButton(
            self.ctrl_panel, text="Export CSV", fg_color="#2E3047", text_color="#FFFFFF",
            hover_color="#3E425E", command=self._export_csv
        )
        self.btn_export_csv.pack(side="right", padx=10, pady=15)

        self.btn_export_json = ctk.CTkButton(
            self.ctrl_panel, text="Export JSON", fg_color="#2E3047", text_color="#FFFFFF",
            hover_color="#3E425E", command=self._export_json
        )
        self.btn_export_json.pack(side="right", padx=15, pady=15)

        # Text View for live system logs
        self.log_display_frame = ctk.CTkFrame(self, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.log_display_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.log_display_frame.grid_columnconfigure(0, weight=1)
        self.log_display_frame.grid_rowconfigure(1, weight=1)

        self.lbl_log_title = ctk.CTkLabel(
            self.log_display_frame, text="Serial Debug Panel (Raw Telemetry Streams)",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#A9B1D6"
        )
        self.lbl_log_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Scrollable textbox for logs
        self.txt_logs = ctk.CTkTextbox(
            self.log_display_frame, fg_color="#181924", font=ctk.CTkFont(family="Consolas", size=12), text_color="#C0CAF5"
        )
        self.txt_logs.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def _start(self):
        self.logger.start_logging()
        self.status_indicator.configure(text="● RECORDING", text_color="#00E676")
        self.btn_start.configure(state="disabled", fg_color="#4E5173", text_color="#888888")
        self.btn_stop.configure(state="normal", fg_color="#FF1744", text_color="#FFFFFF", hover_color="#D50000")

    def _stop(self):
        self.logger.stop_logging()
        self.status_indicator.configure(text="● IDLE", text_color="#FF1744")
        self.btn_start.configure(state="normal", fg_color="#00E5FF", text_color="#0D0E15", hover_color="#00B2CC")
        self.btn_stop.configure(state="disabled", fg_color="#4E5173", text_color="#FFFFFF")

    def _clear(self):
        self.logger.clear_logs()
        self.txt_logs.delete("1.0", tk.END)

    def _export_csv(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"exports/manual_export_{timestamp}.csv"
        if self.logger.export_to_csv(file_path):
            self.txt_logs.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Logs successfully exported to {file_path}\n")
            self.txt_logs.see(tk.END)

    def _export_json(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"exports/manual_export_{timestamp}.json"
        if self.logger.export_to_json(file_path):
            self.txt_logs.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Logs successfully exported to {file_path}\n")
            self.txt_logs.see(tk.END)

    def append_raw_line(self, line):
        """Appends a raw serial line to the local debug accumulator."""
        t_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.raw_lines.append(f"[{t_str}] RX: {line}")

    def update_logs(self):
        """Updates the text block with raw serial lines from the debug accumulator."""
        self.txt_logs.delete("1.0", tk.END)
        if not self.raw_lines:
            self.txt_logs.insert(tk.END, "No Serial Data Received\n")
        else:
            for line in self.raw_lines:
                self.txt_logs.insert(tk.END, line + "\n")
        self.txt_logs.see(tk.END)


class SettingsPage(ctk.CTkFrame):
    """Page allowing configurations change."""
    def __init__(self, parent, settings, on_settings_changed, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.settings = settings
        self.on_settings_changed = on_settings_changed

        self.grid_columnconfigure(0, weight=1)

        # Settings Card
        self.card = ctk.CTkFrame(self, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.card.grid(row=0, column=0, padx=10, pady=10, sticky="nwe")
        self.card.grid_columnconfigure((0, 1), weight=1)

        title = ctk.CTkLabel(
            self.card, text="Application Preferences", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFFFFF"
        )
        title.grid(row=0, column=0, columnspan=2, padx=25, pady=20, sticky="w")

        # 1. Theme Configuration
        ctk.CTkLabel(self.card, text="Color Theme Mode:", font=ctk.CTkFont(size=14), text_color="#A9B1D6").grid(
            row=1, column=0, padx=25, pady=12, sticky="w"
        )
        self.theme_option = ctk.CTkOptionMenu(
            self.card, values=["Dark", "Light"], fg_color="#2E3047", button_color="#3E425E",
            command=self._theme_change
        )
        self.theme_option.grid(row=1, column=1, padx=25, pady=12, sticky="e")
        self.theme_option.set(self.settings.get("theme"))

        # 2. Graph Update Speed (points displayed)
        ctk.CTkLabel(self.card, text="Graph History Length (data points):", font=ctk.CTkFont(size=14), text_color="#A9B1D6").grid(
            row=2, column=0, padx=25, pady=12, sticky="w"
        )
        self.graph_pts = ctk.CTkSlider(
            self.card, from_=50, to=500, number_of_steps=9, progress_color="#00E5FF", button_color="#00E5FF",
            command=self._slider_change
        )
        self.graph_pts.grid(row=2, column=1, padx=25, pady=12, sticky="e")
        self.graph_pts.set(self.settings.get("graph_speed_points"))
        
        self.lbl_slider_val = ctk.CTkLabel(self.card, text=str(int(self.graph_pts.get())), text_color="#A9B1D6")
        self.lbl_slider_val.grid(row=2, column=1, padx=(0, 220), pady=12, sticky="e")

        # 3. Notification Sounds Switch
        ctk.CTkLabel(self.card, text="Sound Effects / Notifications:", font=ctk.CTkFont(size=14), text_color="#A9B1D6").grid(
            row=3, column=0, padx=25, pady=12, sticky="w"
        )
        self.switch_sound = ctk.CTkSwitch(
            self.card, text="", progress_color="#00E5FF", button_color="#00E5FF", command=self._sound_change
        )
        self.switch_sound.grid(row=3, column=1, padx=25, pady=12, sticky="e")
        if self.settings.get("notification_sounds"):
            self.switch_sound.select()

        # 4. Auto-Connect on Launch
        ctk.CTkLabel(self.card, text="Auto-Connect to Last Serial Device:", font=ctk.CTkFont(size=14), text_color="#A9B1D6").grid(
            row=4, column=0, padx=25, pady=12, sticky="w"
        )
        self.switch_auto = ctk.CTkSwitch(
            self.card, text="", progress_color="#00E5FF", button_color="#00E5FF", command=self._auto_change
        )
        self.switch_auto.grid(row=4, column=1, padx=25, pady=12, sticky="e")
        if self.settings.get("auto_connect"):
            self.switch_auto.select()

        # Save Button
        self.btn_save = ctk.CTkButton(
            self.card, text="Save Preferences", fg_color="#00E5FF", text_color="#0D0E15",
            hover_color="#00B2CC", font=ctk.CTkFont(weight="bold"), command=self._save_settings
        )
        self.btn_save.grid(row=5, column=0, columnspan=2, padx=25, pady=30, sticky="ew")

    def _theme_change(self, val):
        self.settings.set("theme", val)
        ctk.set_appearance_mode(val.lower())

    def _slider_change(self, val):
        val_int = int(val)
        self.lbl_slider_val.configure(text=str(val_int))
        self.settings.set("graph_speed_points", val_int)

    def _sound_change(self):
        self.settings.set("notification_sounds", bool(self.switch_sound.get()))

    def _auto_change(self):
        self.settings.set("auto_connect", bool(self.switch_auto.get()))

    def _save_settings(self):
        self.settings.save()
        self.on_settings_changed()
        # Prompt a beautiful pop up
        logging.info("Settings explicitly saved by user.")


class AboutPage(ctk.CTkFrame):
    """About developer and hardware specifications page."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # Card info
        self.card = ctk.CTkFrame(self, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.card.grid_columnconfigure(0, weight=1)

        lbl_title = ctk.CTkLabel(
            self.card, text="Arduino Nano 33 BLE Sense Rev2\nTelemetry Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"), text_color="#00E5FF", justify="center"
        )
        lbl_title.pack(padx=20, pady=(40, 20))

        lbl_desc = ctk.CTkLabel(
            self.card,
            text="A real-time monitoring and visualization desktop dashboard for engineering demonstrations.",
            font=ctk.CTkFont(size=14), text_color="#A9B1D6", justify="center"
        )
        lbl_desc.pack(padx=30, pady=5)

        # Hardware Specifications List
        self.hardware_frame = ctk.CTkFrame(self.card, fg_color="#181924", border_color="#2C2E3E", border_width=1, corner_radius=8)
        self.hardware_frame.pack(padx=40, pady=25, fill="x")

        specs = [
            ("Microcontroller", "Nordic nRF52840 (ARM Cortex-M4 @ 64MHz)"),
            ("IMU Sensors", "LSM6DSOX (6-axis Accel + Gyro) & BMI270"),
            ("Magnetometer", "LIS3MDL (3-axis Digital Magnetometer)"),
            ("Color & Proximity & Gesture", "APDS9960 (Digital RGB, Proximity, and Gesture)"),
            ("Serial Comm Protocol", "USB CDC (Universal Asynchronous Receiver-Transmitter)"),
            ("Application Stack", "Python 3.12+, CustomTkinter, Matplotlib, NumPy, PySerial")
        ]

        for i, (spec_lbl, spec_val) in enumerate(specs):
            row_f = ctk.CTkFrame(self.hardware_frame, fg_color="transparent")
            row_f.pack(fill="x", padx=15, pady=6)
            ctk.CTkLabel(row_f, text=spec_lbl, font=ctk.CTkFont(size=13, weight="bold"), text_color="#A9B1D6").pack(side="left")
            ctk.CTkLabel(row_f, text=spec_val, font=ctk.CTkFont(size=13), text_color="#FFFFFF").pack(side="right")

        # Developer Info
        lbl_dev = ctk.CTkLabel(
            self.card, text="Developed by: engineering student (Placeholder Name)\nVersion: 1.0.0 (Release Build)",
            font=ctk.CTkFont(size=13, slant="italic"), text_color="#565F89", justify="center"
        )
        lbl_dev.pack(side="bottom", padx=20, pady=30)


class MainWindow(ctk.CTk):
    """The main Dashboard Window including navigation and top status bar."""
    def __init__(self, serial_mgr, logger_mgr, settings_mgr):
        super().__init__()
        self.serial_mgr = serial_mgr
        self.logger = logger_mgr
        self.settings = settings_mgr

        # Window properties
        self.title("Arduino Nano 33 BLE Sense Rev2 Dashboard")
        self.geometry("1400x850")
        self.minsize(1200, 750)
        
        # Apply theme
        ctk.set_appearance_mode(self.settings.get("theme").lower())
        
        # Grid layout configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # State Variables
        self.fps_time = time.time()
        self.fps_counter = 0
        self.fps_display = 0
        self.recent_acc_data = deque(maxlen=20)
        self.recent_gyr_data = deque(maxlen=20)
        self.recent_mag_data = deque(maxlen=20)
        self.recent_clr_data = deque(maxlen=20)
        self.recent_prx_data = deque(maxlen=20)

        # Setup Components
        self._build_top_bar()
        self._build_sidebar()
        self._build_page_container()

        # Load first page
        self.show_page("Dashboard")

        # Start UI loop updates
        self.after(50, self._ui_update_loop)

        # Auto-connect if enabled
        if self.settings.get("auto_connect"):
            self.after(2200, self._auto_connect_on_start)

    def _build_top_bar(self):
        """Top bar for serial controls, status indicators, and system resource monitors."""
        self.top_bar = ctk.CTkFrame(self, height=70, fg_color="#161622", corner_radius=0, border_color="#2E3047", border_width=1)
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="nsew")
        
        # Logo & App Title
        logo_lbl = ctk.CTkLabel(
            self.top_bar, text="⚡ NANO 33 BLE SENSE REV2",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#00E5FF"
        )
        logo_lbl.pack(side="left", padx=20, pady=10)

        # Connection status indicator
        self.status_light = ctk.CTkLabel(
            self.top_bar, text="● Disconnected", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FF1744"
        )
        self.status_light.pack(side="left", padx=15, pady=10)

        # COM Port Selector
        self.com_selector = ctk.CTkOptionMenu(
            self.top_bar, values=["Scanning..."], fg_color="#2E3047", button_color="#3E425E", width=130
        )
        self.com_selector.pack(side="left", padx=5, pady=10)
        self._refresh_ports()

        # Baud Rate Selector
        self.baud_selector = ctk.CTkOptionMenu(
            self.top_bar, values=["9600", "19200", "38400", "57600", "115200"], fg_color="#2E3047", button_color="#3E425E", width=100
        )
        self.baud_selector.pack(side="left", padx=5, pady=10)
        self.baud_selector.set(str(self.settings.get("baud_rate")))

        # Connect / Disconnect Buttons
        self.btn_connect = ctk.CTkButton(
            self.top_bar, text="Connect", fg_color="#00E5FF", text_color="#0D0E15",
            hover_color="#00B2CC", font=ctk.CTkFont(weight="bold"), width=80, command=self._on_connect_clicked
        )
        self.btn_connect.pack(side="left", padx=5, pady=10)

        self.btn_disconnect = ctk.CTkButton(
            self.top_bar, text="Disconnect", fg_color="#4E5173", text_color="#FFFFFF",
            hover_color="#3E425E", font=ctk.CTkFont(weight="bold"), width=80, state="disabled", command=self._on_disconnect_clicked
        )
        self.btn_disconnect.pack(side="left", padx=5, pady=10)

        self.btn_refresh = ctk.CTkButton(
            self.top_bar, text="Refresh Ports", fg_color="#2E3047", text_color="#FFFFFF",
            hover_color="#3E425E", width=100, command=self._refresh_ports
        )
        self.btn_refresh.pack(side="left", padx=5, pady=10)

        # System Metrics (right side)
        self.sys_metrics_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.sys_metrics_frame.pack(side="right", padx=20, pady=10)

        self.lbl_sys_info = ctk.CTkLabel(
            self.sys_metrics_frame, text="CPU: --% | RAM: --% | FPS: --",
            font=ctk.CTkFont(size=12, family="Consolas"), text_color="#A9B1D6"
        )
        self.lbl_sys_info.pack(side="right")

        self.lbl_datetime = ctk.CTkLabel(
            self.top_bar, text="--/--/---- --:--:--", font=ctk.CTkFont(size=13), text_color="#A9B1D6"
        )
        self.lbl_datetime.pack(side="right", padx=15)

    def _build_sidebar(self):
        """Navigation sidebar with expandable behavior."""
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color="#12131A", corner_radius=0, border_color="#2E3047", border_width=1)
        self.sidebar.grid(row=1, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Navigation Buttons list
        nav_buttons = [
            ("Dashboard", "🏠  Dashboard"),
            ("Accelerometer", "📐  Accelerometer"),
            ("Gyroscope", "🌀  Gyroscope"),
            ("Magnetometer", "🧭  Magnetometer"),
            ("Color", "🎨  Color Sensor"),
            ("Gesture", "👋  Gesture Sensor"),
            ("Proximity", "📏  Proximity Sensor"),
            ("DataLogger", "📂  Data Logger"),
            ("Settings", "⚙️  Settings"),
            ("About", "ℹ️  About")
        ]

        self.nav_btns = {}
        for i, (page_name, label_text) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar, text=label_text, font=ctk.CTkFont(size=14, weight="normal"),
                fg_color="transparent", text_color="#A9B1D6", hover_color="#1E1F2E", anchor="w",
                corner_radius=6, height=42, command=lambda p=page_name: self.show_page(p)
            )
            btn.pack(fill="x", padx=12, pady=5)
            self.nav_btns[page_name] = btn

    def _build_page_container(self):
        """Central frame holding the pages."""
        self.container = ctk.CTkFrame(self, fg_color="#0D0E15", corner_radius=0)
        self.container.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # Pages instantiation
        self.pages = {
            "Dashboard": DashboardPage(self.container),
            "Accelerometer": AccelerometerPage(self.container, self.settings),
            "Gyroscope": GyroscopePage(self.container, self.settings),
            "Magnetometer": MagnetometerPage(self.container, self.settings),
            "Color": ColorSensorPage(self.container, self.settings),
            "Gesture": GestureSensorPage(self.container, self.settings),
            "Proximity": ProximitySensorPage(self.container, self.settings),
            "DataLogger": DataLoggerPage(self.container, self.logger),
            "Settings": SettingsPage(self.container, self.settings, self._on_settings_saved),
            "About": AboutPage(self.container)
        }

        # Grid-pack all frames in the same location (stacking)
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove() # Start hidden

        self.current_page = None

    def show_page(self, page_name):
        """Swaps the visible page frame and highlights the sidebar button."""
        if self.current_page:
            self.pages[self.current_page].grid_remove()
            self.nav_btns[self.current_page].configure(fg_color="transparent", text_color="#A9B1D6")

        self.current_page = page_name
        self.pages[page_name].grid()
        self.nav_btns[page_name].configure(fg_color="#1E1F2E", text_color="#00E5FF")

    def _auto_connect_on_start(self):
        """Attempts auto-connection to last COM port on startup."""
        last_port = self.settings.get("last_com_port")
        if last_port:
            ports = SerialManager.list_ports()
            if last_port in ports:
                baud = self.settings.get("baud_rate")
                auto_recon = self.settings.get("auto_connect")
                logging.info(f"Auto-connecting to last device: {last_port} @ {baud}")
                self.serial_mgr.connect(last_port, baud, auto_reconnect=auto_recon)

    def _refresh_ports(self):
        """Scans systems serial ports and updates option dropdown."""
        ports = SerialManager.list_ports()
        if not ports:
            self.com_selector.configure(values=["No COM Ports"])
            self.com_selector.set("No COM Ports")
        else:
            self.com_selector.configure(values=ports)
            # Try to restore last connection port
            last_port = self.settings.get("last_com_port")
            if last_port in ports:
                self.com_selector.set(last_port)
            else:
                self.com_selector.set(ports[0])

    def _on_connect_clicked(self):
        port = self.com_selector.get()
        if port in ("No COM Ports", "Scanning..."):
            return
        
        baud = int(self.baud_selector.get())
        auto_recon = self.settings.get("auto_connect")
        
        # Connect
        self.serial_mgr.connect(port, baud, auto_reconnect=auto_recon)
        self.settings.set("last_com_port", port)
        self.settings.set("baud_rate", baud)
        self.settings.save()

    def _on_disconnect_clicked(self):
        self.serial_mgr.disconnect()

    def _on_settings_saved(self):
        """Propagates updated settings properties to pages."""
        # Update point history lengths
        max_pts = self.settings.get("graph_speed_points")
        self.pages["Accelerometer"].update_history_length(max_pts)
        self.pages["Gyroscope"].update_history_length(max_pts)
        self.pages["Magnetometer"].update_history_length(max_pts)
        self.pages["Color"].update_history_length(max_pts)
        self.pages["Proximity"].update_history_length(max_pts)

    def update_connection_status(self, status, msg):
        """Callback from serial manager thread to update status widgets."""
        try:
            if status == "Connected":
                self.status_light.configure(text=f"● {status}", text_color="#00E676")
                self.btn_connect.configure(state="disabled", fg_color="#4E5173")
                self.btn_disconnect.configure(state="normal", fg_color="#FF1744", hover_color="#D50000")
            elif status == "Connecting":
                self.status_light.configure(text=f"● {status}", text_color="#FF9E00")
                self.btn_connect.configure(state="disabled")
                self.btn_disconnect.configure(state="normal")
            else:
                self.status_light.configure(text=f"● {status}", text_color="#FF1744")
                self.btn_connect.configure(state="normal", fg_color="#00E5FF")
                self.btn_disconnect.configure(state="disabled", fg_color="#4E5173")
        except Exception:
            pass

    def handle_serial_data(self, prefix, vals):
        """Thread-safe routing callback for parsed serial values."""
        try:
            if prefix == "RAW":
                raw_line = vals[0]
                self.pages["DataLogger"].append_raw_line(raw_line)
                return

            self.logger.log_sensor_data(prefix, vals)

            # Route to UI pages in a thread-safe manner
            # In python, basic setting variables is thread-safe
            # The main UI update loop running in the Tkinter main thread will poll/pull these values
            if prefix == "ACC":
                x, y, z = vals
                self.recent_acc_data.append(vals)
                magnitude = math.sqrt(x*x + y*y + z*z)
                self.pages["Dashboard"].update_sensor("ACC", magnitude, f"X:{x:.2f} Y:{y:.2f} Z:{z:.2f} G")
                self.pages["Accelerometer"].push_data(x, y, z)
            elif prefix == "GYR":
                x, y, z = vals
                self.recent_gyr_data.append(vals)
                magnitude = math.sqrt(x*x + y*y + z*z)
                self.pages["Dashboard"].update_sensor("GYR", magnitude, f"X:{x:.1f} Y:{y:.1f} Z:{z:.1f} d/s")
                self.pages["Gyroscope"].push_data(x, y, z)
            elif prefix == "MAG":
                x, y, z = vals
                self.recent_mag_data.append(vals)
                magnitude = math.sqrt(x*x + y*y + z*z)
                heading = (math.atan2(y, x) * 180 / math.pi) % 360
                self.pages["Dashboard"].update_sensor("MAG", magnitude, f"Heading: {heading:.1f}° ({magnitude:.1f} uT)")
                self.pages["Magnetometer"].push_data(x, y, z)
            elif prefix == "CLR":
                r, g, b, c = vals
                self.recent_clr_data.append(vals)
                self.pages["Dashboard"].update_sensor("CLR", c, f"R:{r} G:{g} B:{b} Clear:{c}")
                self.pages["Color"].push_data(r, g, b, c)
            elif prefix == "GST":
                val = vals[0]
                self.pages["Dashboard"].update_sensor("GST", 1.0 if val != "NONE" else 0.0, f"Gesture: {val}")
                self.pages["Gesture"].push_data(val)
            elif prefix == "PRX":
                val = vals[0]
                self.recent_prx_data.append(val)
                self.pages["Dashboard"].update_sensor("PRX", float(val), f"Distance: {val}")
                self.pages["Proximity"].push_data(val)
        except Exception:
            pass

    def _ui_update_loop(self):
        """Regular polling callback (50ms interval) to refresh elements."""
        # 1. Update Current Time
        self.lbl_datetime.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 2. Update System Metrics
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        self._calculate_fps()
        self.lbl_sys_info.configure(text=f"CPU: {cpu_usage:.1f}% | RAM: {ram_usage:.1f}% | FPS: {self.fps_display}")

        # 3. Pull status from serial manager to sync button states
        is_conn = self.serial_mgr.is_connected()
        status_str = "Connected" if is_conn else ("Connecting" if self.serial_mgr.running else "Disconnected")
        self.update_connection_status(status_str, "")

        # 4. Trigger UI refreshes on pages that require timed polling
        if self.current_page == "DataLogger":
            self.pages["DataLogger"].update_logs()
        elif self.current_page == "Accelerometer":
            self.pages["Accelerometer"].update_ui()
        elif self.current_page == "Gyroscope":
            self.pages["Gyroscope"].update_ui()
        elif self.current_page == "Magnetometer":
            self.pages["Magnetometer"].update_ui()
        elif self.current_page == "Color":
            self.pages["Color"].update_ui()
        elif self.current_page == "Gesture":
            self.pages["Gesture"].update_ui()
        elif self.current_page == "Proximity":
            self.pages["Proximity"].update_ui()

        # Re-schedule
        self.after(50, self._ui_update_loop)

    def _calculate_fps(self):
        """Calculates render loop ticks count."""
        self.fps_counter += 1
        now = time.time()
        if now - self.fps_time >= 1.0:
            self.fps_display = self.fps_counter
            self.fps_counter = 0
            self.fps_time = now
