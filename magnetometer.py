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

class MagnetometerPage(ctk.CTkFrame):
    """Magnetometer page showing a live compass and magnetic field strength plots."""
    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.settings = settings

        # Config points
        self.max_points = self.settings.get("graph_speed_points")
        self.x_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.y_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.z_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.mag_strength_history = deque([0.0] * self.max_points, maxlen=self.max_points)

        # State variables
        self.paused = False
        self.latest_vals = (0.0, 0.0, 0.0)
        self.heading = 0.0
        self.strength = 0.0

        # Grid Layout
        self.grid_columnconfigure(0, weight=3) # Chart area
        self.grid_columnconfigure(1, weight=2) # Compass area
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
            self.chart_header, text="Real-Time Magnetic Fields",
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

        # Right Frame: Compass & strength display
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure((0, 1), weight=1)

        # Compass Card
        self.compass_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.compass_card.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        self.compass_card.grid_columnconfigure(0, weight=1)
        self.compass_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.compass_card, text="Digital Compass (Field Orientation)",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")

        # Compass Canvas
        self.canvas_compass = tk.Canvas(self.compass_card, bg="#181924", highlightthickness=0)
        self.canvas_compass.grid(row=1, column=0, padx=20, pady=15, sticky="nsew")

        # Metrics Card
        self.stats_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.stats_card.grid(row=1, column=0, pady=(10, 0), sticky="nsew")
        self.stats_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.stats_card, text="Magnetic Strength Properties",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        self.lbl_mag_x = self._create_metric_row(self.stats_card, "Field X-axis:", "0.00 uT", 1)
        self.lbl_mag_y = self._create_metric_row(self.stats_card, "Field Y-axis:", "0.00 uT", 2)
        self.lbl_mag_z = self._create_metric_row(self.stats_card, "Field Z-axis:", "0.00 uT", 3)
        self.lbl_heading = self._create_metric_row(self.stats_card, "Calculated Heading:", "0.0° N", 4)
        self.lbl_strength = self._create_metric_row(self.stats_card, "Total Intensity (B):", "0.00 uT", 5)

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
        self.ax.set_ylim(-100.0, 100.0)
        self.ax.set_xlim(0, self.max_points)

        # Lines
        self.line_x, = self.ax.plot([], [], label="X Axis", color="#FF9E00", linewidth=1.5)
        self.line_y, = self.ax.plot([], [], label="Y Axis", color="#FF5F00", linewidth=1.5)
        self.line_z, = self.ax.plot([], [], label="Z Axis", color="#FFCC00", linewidth=1.5)
        self.line_str, = self.ax.plot([], [], label="Total Intensity (B)", color="#FFFFFF", linewidth=1.0, linestyle=":")

        self.ax.legend(loc="upper left", facecolor="#1E1F2E", edgecolor="#2E3047", labelcolor="#FFFFFF", fontsize=8)

        # Embed
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.left_frame)
        self.canvas_plot.get_tk_widget().grid(row=1, column=0, padx=15, pady=15, sticky="nsew")

    def push_data(self, x, y, z):
        """Adds new magnetometer reading."""
        self.latest_vals = (x, y, z)
        if not self.paused:
            self.x_history.append(x)
            self.y_history.append(y)
            self.z_history.append(z)
            self.mag_strength_history.append(math.sqrt(x*x + y*y + z*z))

    def update_history_length(self, new_length):
        self.max_points = new_length
        self.x_history = deque(self.x_history, maxlen=new_length)
        self.y_history = deque(self.y_history, maxlen=new_length)
        self.z_history = deque(self.z_history, maxlen=new_length)
        self.mag_strength_history = deque(self.mag_strength_history, maxlen=new_length)
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
        self.mag_strength_history.clear()
        for _ in range(self.max_points):
            self.x_history.append(0.0)
            self.y_history.append(0.0)
            self.z_history.append(0.0)
            self.mag_strength_history.append(0.0)
        self.canvas_plot.draw_idle()

    def _export_graph(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"exports/mag_chart_{timestamp}.png"
        try:
            self.fig.savefig(export_path, facecolor=self.fig.get_facecolor(), edgecolor='none')
            logging.info(f"Chart saved to {export_path}")
        except Exception as e:
            logging.error(f"Failed to export chart: {e}")

    def update_ui(self):
        """Called by UI update loop (50ms interval) to refresh compass drawings and metrics."""
        # 1. Update Graph lines
        if not self.paused:
            self.line_x.set_data(range(len(self.x_history)), list(self.x_history))
            self.line_y.set_data(range(len(self.y_history)), list(self.y_history))
            self.line_z.set_data(range(len(self.z_history)), list(self.z_history))
            self.line_str.set_data(range(len(self.mag_strength_history)), list(self.mag_strength_history))
            self.canvas_plot.draw_idle()

        # 2. Extract values & compute strength
        x, y, z = self.latest_vals
        self.strength = math.sqrt(x*x + y*y + z*z)
        
        # Calculate heading in degrees: angle = atan2(Y, X)
        self.heading = (math.atan2(y, x) * 180 / math.pi) % 360

        # Cardinal direction labels
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        dir_idx = int(((self.heading + 22.5) % 360) / 45)
        cardinal_str = directions[dir_idx]

        # Populate metric fields
        self.lbl_mag_x.configure(text=f"{x:.2f} uT")
        self.lbl_mag_y.configure(text=f"{y:.2f} uT")
        self.lbl_mag_z.configure(text=f"{z:.2f} uT")
        self.lbl_heading.configure(text=f"{self.heading:.1f}° {cardinal_str}")
        self.lbl_strength.configure(text=f"{self.strength:.2f} uT")

        # 3. Draw compass on canvas
        self._draw_compass()

    def _draw_compass(self):
        """Draws dynamic compass face and rotating dual-tip needle on canvas."""
        self.canvas_compass.delete("all")
        w = self.canvas_compass.winfo_width()
        h = self.canvas_compass.winfo_height()
        if w <= 1: w = 220
        if h <= 1: h = 200

        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.38
        if r <= 10: r = 70

        # Draw outer ring
        self.canvas_compass.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2E3047", width=3)
        self.canvas_compass.create_oval(cx - r - 4, cy - r - 4, cx + r + 4, cx + r + 4, outline="#1E1F2E", width=1)

        # Draw compass face ticks and labels (N, E, S, W)
        cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
        for text, angle in cardinals:
            rad_ang = math.radians(angle)
            lx = cx + (r - 18) * math.sin(rad_ang)
            ly = cy - (r - 18) * math.cos(rad_ang)
            self.canvas_compass.create_text(
                lx, ly, text=text, fill="#A9B1D6",
                font=("Helvetica", 10, "bold")
            )

        # Compass needle tips
        # Note: In a magnetic compass, the needle aligns with the magnetic field lines.
        # If heading = self.heading, then the heading angle shows where the nose of the device points.
        # We rotate the needle by -self.heading so that it points to magnetic North (0 degrees)!
        needle_angle = -self.heading
        n_rad = math.radians(needle_angle)

        # Vector tip points (length of needle is 85% of compass radius)
        nl = r * 0.8
        
        # North Point (Red arrow)
        nx = cx + nl * math.sin(n_rad)
        ny = cy - nl * math.cos(n_rad)
        
        # South Point (Silver arrow)
        sx = cx - nl * math.sin(n_rad)
        sy = cy + nl * math.cos(n_rad)

        # Needle width offsets for drawing triangles
        perp_rad = math.radians(needle_angle + 90)
        width_offset = 7
        wx = width_offset * math.sin(perp_rad)
        wy = width_offset * math.cos(perp_rad)

        # Draw North needle segment (red polygon)
        self.canvas_compass.create_polygon(
            nx, ny,
            cx + wx, cy - wy,
            cx - wx, cy + wy,
            fill="#FF1744", outline="#D50000"
        )

        # Draw South needle segment (silver polygon)
        self.canvas_compass.create_polygon(
            sx, sy,
            cx + wx, cy - wy,
            cx - wx, cy + wy,
            fill="#B0BEC5", outline="#90A4AE"
        )

        # Center cap button
        self.canvas_compass.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#181924", outline="#A9B1D6", width=2)
        
        # Degree reading at bottom
        self.canvas_compass.create_text(
            cx, cy + r + 15, text=f"{self.heading:.0f}° N",
            fill="#FFFFFF", font=("Helvetica", 11, "bold")
        )
