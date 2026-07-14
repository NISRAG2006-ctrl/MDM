import tkinter as tk
import customtkinter as ctk
import math
import numpy as np
import logging
from collections import deque
from datetime import datetime

# Matplotlib integration
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class AccelerometerPage(ctk.CTkFrame):
    """Accelerometer page featuring real-time charts and a 3D tilt-cube visualization."""
    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.settings = settings
        
        # Point history length
        self.max_points = self.settings.get("graph_speed_points")
        self.x_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.y_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.z_history = deque([1.0] * self.max_points, maxlen=self.max_points)
        
        # State variables
        self.paused = False
        self.latest_vals = (0.0, 0.0, 1.0)
        self.roll = 0.0
        self.pitch = 0.0

        # Grid Layout
        self.grid_columnconfigure(0, weight=3) # Chart area
        self.grid_columnconfigure(1, weight=2) # 3D cube & stats area
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
            self.chart_header, text="Real-Time Acceleration G-Force",
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

        # Matplotlib Graph Setup
        self._init_chart()

        # Right Frame: 3D Animation & Metrics
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure((0, 1), weight=1)

        # 3D Tilt Card
        self.tilt_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.tilt_card.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        self.tilt_card.grid_columnconfigure(0, weight=1)
        self.tilt_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.tilt_card, text="Orientation (3D Tilt Cube)",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")

        # 3D Canvas
        self.canvas_3d = tk.Canvas(self.tilt_card, bg="#181924", highlightthickness=0)
        self.canvas_3d.grid(row=1, column=0, padx=20, pady=15, sticky="nsew")
        
        # Cube Definition: 8 vertices, coordinates in 3D
        self.vertices = [
            [-50, -50, -50], [50, -50, -50], [50, 50, -50], [-50, 50, -50],
            [-50, -50, 50],  [50, -50, 50],  [50, 50, 50],  [-50, 50, 50]
        ]
        # 12 edges connecting vertices
        self.edges = [
            (0, 1), (1, 2), (2, 3), (3, 0), # Front Face
            (4, 5), (5, 6), (6, 7), (7, 4), # Back Face
            (0, 4), (1, 5), (2, 6), (3, 7)  # Connecting edges
        ]

        # Stats Card
        self.stats_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.stats_card.grid(row=1, column=0, pady=(10, 0), sticky="nsew")
        self.stats_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.stats_card, text="Accelerometer Metrics",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        # Create Metric slots
        self.lbl_max = self._create_metric_row(self.stats_card, "Max G-Force:", "0.00 G", 1)
        self.lbl_min = self._create_metric_row(self.stats_card, "Min G-Force:", "0.00 G", 2)
        self.lbl_avg = self._create_metric_row(self.stats_card, "Avg G-Force:", "0.00 G", 3)
        self.lbl_roll = self._create_metric_row(self.stats_card, "Roll Angle:", "0.0°", 4)
        self.lbl_pitch = self._create_metric_row(self.stats_card, "Pitch Angle:", "0.0°", 5)

        # Motion Indicator Led
        self.motion_lbl = ctk.CTkLabel(
            self.stats_card, text="● STATIC", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00E676"
        )
        self.motion_lbl.grid(row=6, column=0, columnspan=2, pady=15)

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
        
        # Grid and styles
        self.ax.grid(True, color="#2E3047", linestyle="--", linewidth=0.5)
        self.ax.spines['bottom'].set_color('#2E3047')
        self.ax.spines['top'].set_color('#2E3047')
        self.ax.spines['left'].set_color('#2E3047')
        self.ax.spines['right'].set_color('#2E3047')
        self.ax.tick_params(colors='#A9B1D6', labelsize=9)
        
        # Set limit bounds
        self.ax.set_ylim(-3.0, 3.0)
        self.ax.set_xlim(0, self.max_points)

        # Line objects
        self.line_x, = self.ax.plot([], [], label="X Axis", color="#00E5FF", linewidth=1.5)
        self.line_y, = self.ax.plot([], [], label="Y Axis", color="#D500F9", linewidth=1.5)
        self.line_z, = self.ax.plot([], [], label="Z Axis", color="#FFFF00", linewidth=1.5)
        
        self.ax.legend(loc="upper left", facecolor="#1E1F2E", edgecolor="#2E3047", labelcolor="#FFFFFF", fontsize=8)

        # Embed in Tkinter
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.left_frame)
        self.canvas_plot.get_tk_widget().grid(row=1, column=0, padx=15, pady=15, sticky="nsew")

    def push_data(self, x, y, z):
        """Adds new reading to deques."""
        self.latest_vals = (x, y, z)
        if not self.paused:
            self.x_history.append(x)
            self.y_history.append(y)
            self.z_history.append(z)

    def update_history_length(self, new_length):
        self.max_points = new_length
        # Re-initialize deques with correct maxlen
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
        # Refill with zeros
        for _ in range(self.max_points):
            self.x_history.append(0.0)
            self.y_history.append(0.0)
            self.z_history.append(1.0)
        self.canvas_plot.draw_idle()

    def _export_graph(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"exports/acc_chart_{timestamp}.png"
        try:
            self.fig.savefig(export_path, facecolor=self.fig.get_facecolor(), edgecolor='none')
            logging.info(f"Chart saved to {export_path}")
        except Exception as e:
            logging.error(f"Failed to export chart image: {e}")

    def update_ui(self):
        """Called periodically (50ms) to update graph lines and 3D cube rotation."""
        # 1. Update Graph lines
        if not self.paused:
            self.line_x.set_data(range(len(self.x_history)), list(self.x_history))
            self.line_y.set_data(range(len(self.y_history)), list(self.y_history))
            self.line_z.set_data(range(len(self.z_history)), list(self.z_history))
            self.canvas_plot.draw_idle()

        # 2. Extract latest values & calculate stats
        x, y, z = self.latest_vals
        magnitude = math.sqrt(x*x + y*y + z*z)

        # Calculate limits and averages on history
        history_mags = [math.sqrt(hx*hx + hy*hy + hz*hz) for hx, hy, hz in zip(self.x_history, self.y_history, self.z_history)]
        max_g = max(history_mags) if history_mags else 0.0
        min_g = min(history_mags) if history_mags else 0.0
        avg_g = sum(history_mags) / len(history_mags) if history_mags else 0.0

        # Update stats text
        self.lbl_max.configure(text=f"{max_g:.2f} G")
        self.lbl_min.configure(text=f"{min_g:.2f} G")
        self.lbl_avg.configure(text=f"{avg_g:.2f} G")

        # Roll & Pitch math (using gravitational vectors)
        # Roll = atan2(y, z), Pitch = atan2(-x, sqrt(y^2 + z^2))
        self.roll = math.atan2(y, z) * 180 / math.pi
        self.pitch = math.atan2(-x, math.sqrt(y*y + z*z)) * 180 / math.pi
        
        self.lbl_roll.configure(text=f"{self.roll:.1f}°")
        self.lbl_pitch.configure(text=f"{self.pitch:.1f}°")

        # Motion status check (standard deviation threshold for moving state)
        if len(history_mags) > 5:
            std_dev = np.std(list(history_mags)[-15:])
            if std_dev > 0.08:
                self.motion_lbl.configure(text="● MOVING", text_color="#FF1744")
            else:
                self.motion_lbl.configure(text="● STATIC", text_color="#00E676")

        # 3. Rotate and render the 3D cube
        self._draw_cube()

    def _draw_cube(self):
        """Projects and draws the rotating wireframe cube on the canvas."""
        self.canvas_3d.delete("all")
        w = self.canvas_3d.winfo_width()
        h = self.canvas_3d.winfo_height()
        if w <= 1: w = 220
        if h <= 1: h = 200
        
        cx, cy = w / 2, h / 2
        
        # Roll represents rotation around Z/Y axis, Pitch around X axis
        # Convert degrees to radians for trig functions
        r_rad = math.radians(self.roll)
        p_rad = math.radians(self.pitch)
        
        rotated_vertices = []
        for vert in self.vertices:
            # 1. Rotate around X axis (Pitch)
            x1 = vert[0]
            y1 = vert[1] * math.cos(p_rad) - vert[2] * math.sin(p_rad)
            z1 = vert[1] * math.sin(p_rad) + vert[2] * math.cos(p_rad)
            
            # 2. Rotate around Y axis (Roll)
            x2 = x1 * math.cos(r_rad) + z1 * math.sin(r_rad)
            y2 = y1
            z2 = -x1 * math.sin(r_rad) + z1 * math.cos(r_rad)
            
            # Orthographic 2D Projection
            proj_x = cx + x2
            proj_y = cy - y2 # Flip Y-axis coordinate
            rotated_vertices.append((proj_x, proj_y))
            
        # Draw edges
        for edge in self.edges:
            p1 = rotated_vertices[edge[0]]
            p2 = rotated_vertices[edge[1]]
            
            # Use color scheme matching accelerometer themes (cyan)
            self.canvas_3d.create_line(p1[0], p1[1], p2[0], p2[1], fill="#00E5FF", width=2)
            
        # Draw small axis indicators
        self.canvas_3d.create_line(cx - 70, cy + 70, cx - 40, cy + 70, fill="#FF1744", width=2, arrow=tk.LAST)
        self.canvas_3d.create_text(cx - 30, cy + 70, text="X", fill="#FF1744", font=("Helvetica", 8, "bold"))
        
        self.canvas_3d.create_line(cx - 70, cy + 70, cx - 70, cy + 40, fill="#00E676", width=2, arrow=tk.LAST)
        self.canvas_3d.create_text(cx - 70, cy + 30, text="Y", fill="#00E676", font=("Helvetica", 8, "bold"))
