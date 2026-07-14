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

class ColorSensorPage(ctk.CTkFrame):
    """Color sensor visualization with live swatch preview, name classifier, and channels plot."""
    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.settings = settings

        # Config points
        self.max_points = self.settings.get("graph_speed_points")
        self.r_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.g_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.b_history = deque([0.0] * self.max_points, maxlen=self.max_points)

        # Swatch block history
        self.color_chips = deque(maxlen=8)
        for _ in range(8):
            self.color_chips.append("#181924") # fill with dark background color

        # State variables
        self.paused = False
        self.latest_rgbc = (0, 0, 0, 0)
        self.hex_code = "#000000"
        self.color_name = "Black"

        # Anchors for closest color name classification
        self.anchor_colors = {
            "Red": (255, 0, 0),
            "Green": (0, 255, 0),
            "Blue": (0, 0, 255),
            "Yellow": (255, 255, 0),
            "Cyan": (0, 255, 255),
            "Magenta": (255, 0, 255),
            "Orange": (255, 127, 0),
            "Purple": (128, 0, 128),
            "Pink": (255, 192, 203),
            "White": (240, 240, 240),
            "Gray": (120, 120, 120),
            "Black": (30, 30, 30),
            "Brown": (139, 69, 19)
        }

        # Grid Layout
        self.grid_columnconfigure(0, weight=3) # Chart area
        self.grid_columnconfigure(1, weight=2) # Color Swatch & details
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
            self.chart_header, text="RGB Channel Intensities",
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

        # Right Frame: Color box Swatch & specs
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure((0, 1), weight=1)

        # Swatch Box Card
        self.swatch_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.swatch_card.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        self.swatch_card.grid_columnconfigure(0, weight=1)
        self.swatch_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.swatch_card, text="Live Color Swatch Box",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")

        # Color Block Swatch Container
        self.swatch_block = ctk.CTkFrame(
            self.swatch_card, fg_color="#000000", border_color="#2C2E3E", border_width=2, corner_radius=10
        )
        self.swatch_block.grid(row=1, column=0, padx=20, pady=15, sticky="nsew")
        self.swatch_block.grid_columnconfigure(0, weight=1)
        self.swatch_block.grid_rowconfigure((0, 1), weight=1)

        # Text inside Swatch box
        self.lbl_swatch_name = ctk.CTkLabel(
            self.swatch_block, text="Black", font=ctk.CTkFont(size=24, weight="bold"), text_color="#FFFFFF"
        )
        self.lbl_swatch_name.grid(row=0, column=0, padx=10, pady=(40, 5), sticky="s")

        self.lbl_swatch_hex = ctk.CTkLabel(
            self.swatch_block, text="#000000", font=ctk.CTkFont(family="Consolas", size=14), text_color="#FFFFFF"
        )
        self.lbl_swatch_hex.grid(row=1, column=0, padx=10, pady=(5, 40), sticky="n")

        # Details & History Card
        self.details_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.details_card.grid(row=1, column=0, pady=(10, 0), sticky="nsew")
        self.details_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.details_card, text="Color Metrics & History",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Metrics rows
        self.metrics_container = ctk.CTkFrame(self.details_card, fg_color="transparent")
        self.metrics_container.pack(fill="x", padx=10, pady=5)
        self.metrics_container.grid_columnconfigure((0, 1), weight=1)

        self.lbl_rgb = self._create_metric_row(self.metrics_container, "Raw RGB Value:", "(0, 0, 0)", 1)
        self.lbl_brightness = self._create_metric_row(self.metrics_container, "Clear/Brightness:", "0 Lux", 2)
        self.lbl_saturation = self._create_metric_row(self.metrics_container, "Saturation (S):", "0 %", 3)
        self.lbl_dominant = self._create_metric_row(self.metrics_container, "Dominant Channel:", "None", 4)

        # History Chips Row
        self.chips_title = ctk.CTkLabel(
            self.details_card, text="Recent Scanned Swatches",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#A9B1D6"
        )
        self.chips_title.pack(anchor="w", padx=20, pady=(15, 2))

        self.chips_frame = ctk.CTkFrame(self.details_card, fg_color="#181924", border_color="#2C2E3E", border_width=1, corner_radius=8, height=45)
        self.chips_frame.pack(fill="x", padx=20, pady=(5, 20))
        self.chips_frame.pack_propagate(False)

        self.chip_slots = []
        for i in range(8):
            slot = ctk.CTkFrame(self.chips_frame, fg_color="#181924", width=30, height=30, corner_radius=4)
            slot.pack(side="left", padx=5, pady=7)
            self.chip_slots.append(slot)

    def _create_metric_row(self, parent, label_text, default_val, row_idx):
        lbl_desc = ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=12), text_color="#A9B1D6")
        lbl_desc.grid(row=row_idx, column=0, padx=15, pady=4, sticky="w")
        lbl_val = ctk.CTkLabel(parent, text=default_val, font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
        lbl_val.grid(row=row_idx, column=1, padx=15, pady=4, sticky="e")
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

        # Set bounds (raw RGB values from APDS9960 range typically 0-255 or up to 65535, we'll map to 0-255)
        self.ax.set_ylim(0.0, 260.0)
        self.ax.set_xlim(0, self.max_points)

        # Lines
        self.line_r, = self.ax.plot([], [], label="Red Channel", color="#FF1744", linewidth=2.0)
        self.line_g, = self.ax.plot([], [], label="Green Channel", color="#00E676", linewidth=2.0)
        self.line_b, = self.ax.plot([], [], label="Blue Channel", color="#2979FF", linewidth=2.0)

        self.ax.legend(loc="upper left", facecolor="#1E1F2E", edgecolor="#2E3047", labelcolor="#FFFFFF", fontsize=8)

        # Embed
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.left_frame)
        self.canvas_plot.get_tk_widget().grid(row=1, column=0, padx=15, pady=15, sticky="nsew")

    def push_data(self, r, g, b, c):
        """Adds new raw RGBC readings, mapping inputs to a 0-255 range if they exceed it."""
        # APDS9960 can yield higher resolutions. Standardize to 0-255.
        max_val = max(r, g, b, 1)
        if max_val > 255:
            # Scale proportionally based on maximum value
            factor = 255.0 / max_val
            r_norm = int(r * factor)
            g_norm = int(g * factor)
            b_norm = int(b * factor)
        else:
            r_norm, g_norm, b_norm = r, g, b

        self.latest_rgbc = (r_norm, g_norm, b_norm, c)
        
        if not self.paused:
            self.r_history.append(r_norm)
            self.g_history.append(g_norm)
            self.b_history.append(b_norm)

    def update_history_length(self, new_length):
        self.max_points = new_length
        self.r_history = deque(self.r_history, maxlen=new_length)
        self.g_history = deque(self.g_history, maxlen=new_length)
        self.b_history = deque(self.b_history, maxlen=new_length)
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
        self.r_history.clear()
        self.g_history.clear()
        self.b_history.clear()
        for _ in range(self.max_points):
            self.r_history.append(0.0)
            self.g_history.append(0.0)
            self.b_history.append(0.0)
        self.canvas_plot.draw_idle()

    def _export_graph(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"exports/color_chart_{timestamp}.png"
        try:
            self.fig.savefig(export_path, facecolor=self.fig.get_facecolor(), edgecolor='none')
            logging.info(f"Chart saved to {export_path}")
        except Exception as e:
            logging.error(f"Failed to export chart: {e}")

    def update_ui(self):
        """Called by UI update loop (50ms interval) to refresh swatch box and color list."""
        # 1. Update Graph lines
        if not self.paused:
            self.line_r.set_data(range(len(self.r_history)), list(self.r_history))
            self.line_g.set_data(range(len(self.g_history)), list(self.g_history))
            self.line_b.set_data(range(len(self.b_history)), list(self.b_history))
            self.canvas_plot.draw_idle()

        # 2. Extract values & determine closest color name
        r, g, b, c = self.latest_rgbc
        self.hex_code = f"#{r:02X}{g:02X}{b:02X}"
        self.color_name = self._classify_color_name(r, g, b)

        # Update Swatch Box attributes
        self.swatch_block.configure(fg_color=self.hex_code)
        self.lbl_swatch_name.configure(text=self.color_name)
        self.lbl_swatch_hex.configure(text=self.hex_code)

        # Make swatch box text contrast with background (luminance check)
        # Standard relative luminance equation: L = 0.2126*R + 0.7152*G + 0.0722*B
        luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
        text_color = "#0D0E15" if luminance > 0.45 else "#FFFFFF"
        self.lbl_swatch_name.configure(text_color=text_color)
        self.lbl_swatch_hex.configure(text_color=text_color)

        # Write data to rows
        self.lbl_rgb.configure(text=f"({r}, {g}, {b})")
        self.lbl_brightness.configure(text=f"{c} Lux" if c > 0 else "0 Lux")
        
        # Calculate Saturation (S in HSV): (Max - Min) / Max
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        sat = 0.0
        if max_val > 0:
            sat = ((max_val - min_val) / max_val) * 100
        self.lbl_saturation.configure(text=f"{sat:.1f} %")

        # Determine Dominant Channel
        dominant = "None"
        if r > g and r > b: dominant = "Red (R)"
        elif g > r and g > b: dominant = "Green (G)"
        elif b > r and b > g: dominant = "Blue (B)"
        self.lbl_dominant.configure(text=dominant)

        # Update chips row: Check if current color is different from last added chip
        # and has actual values (avoid flooding black chips when starting)
        if self.hex_code != "#000000":
            if not self.color_chips or self.color_chips[-1] != self.hex_code:
                self.color_chips.append(self.hex_code)

        # Repaint chip frames
        for idx, slot in enumerate(self.chip_slots):
            if idx < len(self.color_chips):
                chip_color = self.color_chips[idx]
                slot.configure(fg_color=chip_color, border_color="#2C2E3E", border_width=1)

    def _classify_color_name(self, r, g, b):
        """Finds closest predefined color name based on Euclidean distance."""
        best_dist = float('inf')
        best_name = "Black"
        
        for name, rgb in self.anchor_colors.items():
            dist = math.sqrt((r - rgb[0])**2 + (g - rgb[1])**2 + (b - rgb[2])**2)
            if dist < best_dist:
                best_dist = dist
                best_name = name
        return best_name
