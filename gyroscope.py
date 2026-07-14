import tkinter as tk
import customtkinter as ctk
import math
import logging
from collections import deque
from datetime import datetime

# Matplotlib integration
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class GyroscopePage(ctk.CTkFrame):
    """Gyroscope page with real-time graphs, angular velocity gauge, and rotation disks."""
    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.settings = settings

        # Configuration points length
        self.max_points = self.settings.get("graph_speed_points")
        self.x_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.y_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.z_history = deque([0.0] * self.max_points, maxlen=self.max_points)

        # State variables
        self.paused = False
        self.latest_vals = (0.0, 0.0, 0.0)
        self.integrated_angle = 0.0  # Simulated integrated Z angle
        self.peaks = {"X": 0.0, "Y": 0.0, "Z": 0.0, "Magnitude": 0.0}

        # Grid Layout
        self.grid_columnconfigure(0, weight=3) # Chart area
        self.grid_columnconfigure(1, weight=2) # Gauges & animations
        self.grid_rowconfigure(0, weight=1)

        # Left Frame: Plot & Controls
        self.left_frame = ctk.CTkFrame(self, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(1, weight=1)

        # Chart Header
        self.chart_header = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.chart_header.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(
            self.chart_header, text="Real-Time Angular Velocity",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFFFFF"
        ).pack(side="left")

        # Custom Graph Action Controls
        self.ctrl_bar = ctk.CTkFrame(self.chart_header, fg_color="transparent")
        self.ctrl_bar.pack(side="right")

        self.btn_pause = ctk.CTkButton(
            self.ctrl_bar, text="Pause", fg_color="#4E5173", hover_color="#363953", width=60, height=26,
            font=ctk.CTkFont(size=11, weight="bold"), command=self._toggle_pause
        )
        self.btn_pause.pack(side="left", padx=3)

        self.btn_zoom_in = ctk.CTkButton(
            self.ctrl_bar, text="Zoom +", fg_color="#2E3047", hover_color="#3E425E", width=55, height=26,
            font=ctk.CTkFont(size=11), command=self._zoom_in
        )
        self.btn_zoom_in.pack(side="left", padx=3)

        self.btn_zoom_out = ctk.CTkButton(
            self.ctrl_bar, text="Zoom -", fg_color="#2E3047", hover_color="#3E425E", width=55, height=26,
            font=ctk.CTkFont(size=11), command=self._zoom_out
        )
        self.btn_zoom_out.pack(side="left", padx=3)

        self.btn_reset = ctk.CTkButton(
            self.ctrl_bar, text="Reset", fg_color="#FF1744", hover_color="#D50000", width=55, height=26,
            font=ctk.CTkFont(size=11, weight="bold"), command=self._reset_history
        )
        self.btn_reset.pack(side="left", padx=3)

        self.btn_export = ctk.CTkButton(
            self.ctrl_bar, text="Export PNG", fg_color="#2E3047", hover_color="#3E425E", width=80, height=26,
            font=ctk.CTkFont(size=11), command=self._export_graph
        )
        self.btn_export.pack(side="left", padx=3)

        # Plot setup
        self._init_chart()

        # Right Frame: Gauges & Peak statistics
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure((0, 1), weight=1)

        # Visuals Card (Gauge & Spin Disk)
        self.visuals_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.visuals_card.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        self.visuals_card.grid_columnconfigure((0, 1), weight=1)
        self.visuals_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.visuals_card, text="Rotation Speed & Integrated Heading",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 0), sticky="w")

        # Gauge Canvas (Magnitude)
        self.canvas_gauge = tk.Canvas(self.visuals_card, bg="#181924", highlightthickness=0)
        self.canvas_gauge.grid(row=1, column=0, padx=10, pady=15, sticky="nsew")

        # Rotation Animation Canvas
        self.canvas_spin = tk.Canvas(self.visuals_card, bg="#181924", highlightthickness=0)
        self.canvas_spin.grid(row=1, column=1, padx=10, pady=15, sticky="nsew")

        # Stats Card
        self.stats_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.stats_card.grid(row=1, column=0, pady=(10, 0), sticky="nsew")
        self.stats_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.stats_card, text="Peak Rotation Velocity",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        self.lbl_peak_x = self._create_metric_row(self.stats_card, "Peak X Velocity:", "0.0 d/s", 1)
        self.lbl_peak_y = self._create_metric_row(self.stats_card, "Peak Y Velocity:", "0.0 d/s", 2)
        self.lbl_peak_z = self._create_metric_row(self.stats_card, "Peak Z Velocity:", "0.0 d/s", 3)
        self.lbl_peak_mag = self._create_metric_row(self.stats_card, "Peak Magnitude:", "0.0 d/s", 4)
        
        # Reset Peaks Button
        self.btn_reset_peaks = ctk.CTkButton(
            self.stats_card, text="Reset Peak Values", fg_color="#4E5173", hover_color="#3E425E",
            font=ctk.CTkFont(size=12, weight="bold"), command=self._reset_peaks
        )
        self.btn_reset_peaks.grid(row=5, column=0, columnspan=2, padx=20, pady=15, sticky="ew")

    def _create_metric_row(self, parent, label_text, default_val, row_idx):
        lbl_desc = ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=13), text_color="#A9B1D6")
        lbl_desc.grid(row=row_idx, column=0, padx=20, pady=5, sticky="w")
        lbl_val = ctk.CTkLabel(parent, text=default_val, font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF")
        lbl_val.grid(row=row_idx, column=1, padx=20, pady=5, sticky="e")
        return lbl_val

    def _init_chart(self):
        """Initializes the Matplotlib line plot in the GUI."""
        self.fig, self.ax = plt.subplots(figsize=(6, 4), facecolor="#1E1F2E")
        self.ax.set_facecolor("#181924")

        # Styles
        self.ax.grid(True, color="#2E3047", linestyle="--", linewidth=0.5)
        self.ax.spines['bottom'].set_color('#2E3047')
        self.ax.spines['top'].set_color('#2E3047')
        self.ax.spines['left'].set_color('#2E3047')
        self.ax.spines['right'].set_color('#2E3047')
        self.ax.tick_params(colors='#A9B1D6', labelsize=9)

        # Set bounds
        self.ax.set_ylim(-250.0, 250.0)
        self.ax.set_xlim(0, self.max_points)

        # Lines
        self.line_x, = self.ax.plot([], [], label="X Rate", color="#D500F9", linewidth=1.5)
        self.line_y, = self.ax.plot([], [], label="Y Rate", color="#FF4081", linewidth=1.5)
        self.line_z, = self.ax.plot([], [], label="Z Rate", color="#E040FB", linewidth=1.5)

        self.ax.legend(loc="upper left", facecolor="#1E1F2E", edgecolor="#2E3047", labelcolor="#FFFFFF", fontsize=8)

        # Embed
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.left_frame)
        self.canvas_plot.get_tk_widget().grid(row=1, column=0, padx=15, pady=15, sticky="nsew")

    def push_data(self, x, y, z):
        """Appends new gyroscope readings."""
        self.latest_vals = (x, y, z)
        if not self.paused:
            self.x_history.append(x)
            self.y_history.append(y)
            self.z_history.append(z)

    def update_history_length(self, new_length):
        self.max_points = new_length
        self.x_history = deque(self.x_history, maxlen=new_length)
        self.y_history = deque(self.y_history, maxlen=new_length)
        self.z_history = deque(self.z_history, maxlen=new_length)
        self.ax.set_xlim(0, new_length)
        self.canvas_plot.draw_idle()

    def _toggle_pause(self):
        self.paused = not self.paused
        self.btn_pause.configure(
            text="Resume" if self.paused else "Pause",
            fg_color="#00E676" if self.paused else "#4E5173",
            text_color="#0D0E15" if self.paused else "#FFFFFF",
            hover_color="#00C853" if self.paused else "#363953"
        )

    def _zoom_in(self):
        ymin, ymax = self.ax.get_ylim()
        span = ymax - ymin
        self.ax.set_ylim(ymin + span*0.1, ymax - span*0.1)
        self.canvas_plot.draw_idle()

    def _zoom_out(self):
        ymin, ymax = self.ax.get_ylim()
        span = ymax - ymin
        self.ax.set_ylim(ymin - span*0.1, ymax + span*0.1)
        self.canvas_plot.draw_idle()

    def _reset_history(self):
        self.x_history.clear()
        self.y_history.clear()
        self.z_history.clear()
        for _ in range(self.max_points):
            self.x_history.append(0.0)
            self.y_history.append(0.0)
            self.z_history.append(0.0)
        self.canvas_plot.draw_idle()

    def _export_graph(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"exports/gyr_chart_{timestamp}.png"
        try:
            self.fig.savefig(export_path, facecolor=self.fig.get_facecolor(), edgecolor='none')
            logging.info(f"Chart saved to {export_path}")
        except Exception as e:
            logging.error(f"Failed to export chart: {e}")

    def _reset_peaks(self):
        self.peaks = {"X": 0.0, "Y": 0.0, "Z": 0.0, "Magnitude": 0.0}

    def update_ui(self):
        """Timer callback (50ms) to update graph lines, gauges, and spin visualizers."""
        # 1. Update Graph lines
        if not self.paused:
            self.line_x.set_data(range(len(self.x_history)), list(self.x_history))
            self.line_y.set_data(range(len(self.y_history)), list(self.y_history))
            self.line_z.set_data(range(len(self.z_history)), list(self.z_history))
            self.canvas_plot.draw_idle()

        # 2. Extract latest values & calculate peaks
        x, y, z = self.latest_vals
        magnitude = math.sqrt(x*x + y*y + z*z)

        # Update peak thresholds
        if abs(x) > self.peaks["X"]: self.peaks["X"] = abs(x)
        if abs(y) > self.peaks["Y"]: self.peaks["Y"] = abs(y)
        if abs(z) > self.peaks["Z"]: self.peaks["Z"] = abs(z)
        if magnitude > self.peaks["Magnitude"]: self.peaks["Magnitude"] = magnitude

        # Write peaks to label fields
        self.lbl_peak_x.configure(text=f"{self.peaks['X']:.1f} d/s")
        self.lbl_peak_y.configure(text=f"{self.peaks['Y']:.1f} d/s")
        self.lbl_peak_z.configure(text=f"{self.peaks['Z']:.1f} d/s")
        self.lbl_peak_mag.configure(text=f"{self.peaks['Magnitude']:.1f} d/s")

        # Update cumulative integrated heading angle (based on Z rotation rate)
        # 50ms polling interval corresponds to dt = 0.05 seconds
        self.integrated_angle = (self.integrated_angle + z * 0.05) % 360

        # 3. Draw Gauges
        self._draw_magnitude_gauge(magnitude)
        self._draw_rotation_disk()

    def _draw_magnitude_gauge(self, value):
        """Draws circular radial speed gauge on canvas."""
        self.canvas_gauge.delete("all")
        w = self.canvas_gauge.winfo_width()
        h = self.canvas_gauge.winfo_height()
        if w <= 1: w = 110
        if h <= 1: h = 150

        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.38
        if r <= 10: r = 40

        # Radial Gauge Arc Boundaries (from 135 to 405 degrees)
        # background dark track
        self.canvas_gauge.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=135, extent=270, style=tk.ARC, outline="#2C2E3E", width=8
        )

        # Value Arc fill, scaled from 0 to 500 d/s
        max_limit = 500.0
        val_clamped = min(value, max_limit)
        extent = -(val_clamped / max_limit) * 270.0 # extent goes clockwise (negative)
        
        self.canvas_gauge.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=225, extent=extent, style=tk.ARC, outline="#D500F9", width=8
        )

        # Center Text Display
        self.canvas_gauge.create_text(
            cx, cy - 5, text=f"{value:.0f}",
            fill="#FFFFFF", font=("Helvetica", 14, "bold")
        )
        self.canvas_gauge.create_text(
            cx, cy + 12, text="d/s",
            fill="#A9B1D6", font=("Helvetica", 9)
        )
        self.canvas_gauge.create_text(
            cx, cy + r + 15, text="Rotation Rate",
            fill="#A9B1D6", font=("Helvetica", 10, "bold")
        )

    def _draw_rotation_disk(self):
        """Draws rotating integrated heading disk on canvas."""
        self.canvas_spin.delete("all")
        w = self.canvas_spin.winfo_width()
        h = self.canvas_spin.winfo_height()
        if w <= 1: w = 110
        if h <= 1: h = 150

        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.38
        if r <= 10: r = 40

        # Outer ring
        self.canvas_spin.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2C2E3E", width=2)
        
        # Rotating needle line
        rad = math.radians(self.integrated_angle)
        nx = cx + r * math.sin(rad)
        ny = cy - r * math.cos(rad) # Flip Y-axis coordinate
        
        # Draw needle (magenta purple theme color)
        self.canvas_spin.create_line(cx, cy, nx, ny, fill="#D500F9", width=3)
        self.canvas_spin.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#E040FB", outline="#FFFFFF")

        # Heading indicator text
        self.canvas_spin.create_text(
            cx, cy + r + 15, text=f"Heading: {self.integrated_angle:.0f}°",
            fill="#A9B1D6", font=("Helvetica", 10, "bold")
        )
