import tkinter as tk
import customtkinter as ctk
import logging
from collections import deque
from datetime import datetime

# Matplotlib integration
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class ProximitySensorPage(ctk.CTkFrame):
    """Proximity page displaying proximity charts, distance gauges, and alert zones."""
    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.settings = settings

        # Config points
        self.max_points = self.settings.get("graph_speed_points")
        self.history = deque([0.0] * self.max_points, maxlen=self.max_points)

        # State variables
        self.paused = False
        self.latest_val = 0
        self.status_zone = "SAFE"
        self.status_color = "#00E676" # Green default

        # Grid Layout
        self.grid_columnconfigure(0, weight=3) # Chart area
        self.grid_columnconfigure(1, weight=2) # Dial & Alert Panel
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
            self.chart_header, text="Real-Time Proximity Sweep",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFFFFF"
        ).pack(side="left")

        # Controls
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

        # Right Frame: Dial & Alert Card
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure((0, 1), weight=1)

        # Visual Gauge Card
        self.gauge_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.gauge_card.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        self.gauge_card.grid_columnconfigure(0, weight=1)
        self.gauge_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.gauge_card, text="Distance Proximity Gauge",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")

        # Dial Canvas
        self.canvas_dial = tk.Canvas(self.gauge_card, bg="#181924", highlightthickness=0)
        self.canvas_dial.grid(row=1, column=0, padx=20, pady=15, sticky="nsew")

        # Alarm Zone Status Card
        self.alarm_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.alarm_card.grid(row=1, column=0, pady=(10, 0), sticky="nsew")
        self.alarm_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.alarm_card, text="Proximity Alert Controller",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Big alarm status label
        self.lbl_zone = ctk.CTkLabel(
            self.alarm_card, text="SAFE", font=ctk.CTkFont(size=32, weight="bold"), text_color="#00E676"
        )
        self.lbl_zone.pack(padx=20, pady=10)

        self.lbl_desc = ctk.CTkLabel(
            self.alarm_card, text="No object detected within range thresholds.",
            font=ctk.CTkFont(size=12), text_color="#A9B1D6", justify="center"
        )
        self.lbl_desc.pack(padx=30, pady=5)

        # Alarm threshold progress bar indicator
        self.alarm_bar = ctk.CTkProgressBar(self.alarm_card, progress_color="#00E676")
        self.alarm_bar.pack(fill="x", padx=40, pady=(15, 25))
        self.alarm_bar.set(0.0)

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

        # Set bounds (Proximity range: 0 to 255)
        self.ax.set_ylim(0.0, 260.0)
        self.ax.set_xlim(0, self.max_points)

        # Lines
        self.line_prx, = self.ax.plot([], [], label="Proximity Value", color="#FFFF00", linewidth=2.0)

        self.ax.legend(loc="upper left", facecolor="#1E1F2E", edgecolor="#2E3047", labelcolor="#FFFFFF", fontsize=8)

        # Embed
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.left_frame)
        self.canvas_plot.get_tk_widget().grid(row=1, column=0, padx=15, pady=15, sticky="nsew")

    def push_data(self, val):
        """Adds new proximity value."""
        self.latest_val = val
        if not self.paused:
            self.history.append(float(val))

    def update_history_length(self, new_length):
        self.max_points = new_length
        self.history = deque(self.history, maxlen=new_length)
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
        self.ax.set_ylim(max(0, ymin - span*0.1), ymax + span*0.1)
        self.canvas_plot.draw_idle()

    def _reset_history(self):
        self.history.clear()
        for _ in range(self.max_points):
            self.history.append(0.0)
        self.canvas_plot.draw_idle()

    def _export_graph(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"exports/prox_chart_{timestamp}.png"
        try:
            self.fig.savefig(export_path, facecolor=self.fig.get_facecolor(), edgecolor='none')
            logging.info(f"Chart saved to {export_path}")
        except Exception as e:
            logging.error(f"Failed to export chart: {e}")

    def update_ui(self):
        """Timer callback (50ms interval) to refresh dial, progress bars, and alert triggers."""
        # 1. Update Graph line
        if not self.paused:
            self.line_prx.set_data(range(len(self.history)), list(self.history))
            self.canvas_plot.draw_idle()

        # 2. Extract values & determine warning zones
        # 0 is far, 255 is extremely close
        val = self.latest_val
        if val <= 80:
            self.status_zone = "SAFE"
            self.status_color = "#00E676" # Green
            desc = "Clear zone. No obstacle detected within threshold limits."
        elif val <= 180:
            self.status_zone = "WARNING"
            self.status_color = "#FFFF00" # Yellow
            desc = "Object detected approaching. Caution advised."
        else:
            self.status_zone = "DANGER ALARM"
            self.status_color = "#FF1744" # Red
            desc = "CRITICAL LIMIT! Object is extremely close to the sensor!"

        # Update card text & color styles
        self.lbl_zone.configure(text=self.status_zone, text_color=self.status_color)
        self.lbl_desc.configure(text=desc)

        # Progress bar fill (scaled 0.0 to 1.0)
        progress_val = float(val) / 255.0
        self.alarm_bar.configure(progress_color=self.status_color)
        self.alarm_bar.set(progress_val)

        # 3. Draw gauge
        self._draw_dial(val)

    def _draw_dial(self, value):
        """Draws semi-circular gauge on canvas with colors relative to threat zones."""
        self.canvas_dial.delete("all")
        w = self.canvas_dial.winfo_width()
        h = self.canvas_dial.winfo_height()
        if w <= 1: w = 220
        if h <= 1: h = 200

        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.38
        if r <= 10: r = 70

        # Background track
        self.canvas_dial.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=135, extent=270, style=tk.ARC, outline="#2E3047", width=10
        )

        # Colored value progress arc (scaled 0-255)
        # extent maps to 270 degrees total
        extent = -(float(value) / 255.0) * 270.0
        self.canvas_dial.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=225, extent=extent, style=tk.ARC, outline=self.status_color, width=10
        )

        # Digital values inside dial center
        self.canvas_dial.create_text(
            cx, cy - 8, text=str(value),
            fill="#FFFFFF", font=("Helvetica", 20, "bold")
        )
        self.canvas_dial.create_text(
            cx, cy + 12, text="proximity units",
            fill="#A9B1D6", font=("Helvetica", 8)
        )
        self.canvas_dial.create_text(
            cx, cy + r + 15, text=f"Status: {self.status_zone}",
            fill=self.status_color, font=("Helvetica", 10, "bold")
        )
