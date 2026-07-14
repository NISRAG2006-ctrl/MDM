import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from collections import deque

class GestureSensorPage(ctk.CTkFrame):
    """Gesture recognizer page showing active direction arrows, tallies, and history logs."""
    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.settings = settings

        # State variables
        self.active_gesture = "NONE"
        self.gesture_counts = {"UP": 0, "DOWN": 0, "LEFT": 0, "RIGHT": 0, "NEAR": 0, "FAR": 0}
        self.history = deque(maxlen=20)

        # Theme styling colors
        self.inactive_color = "#1E1F2E"
        self.inactive_border = "#2E3047"
        self.active_color = "#FF1744"
        self.active_border = "#FF1744"

        # Grid Layout
        self.grid_columnconfigure(0, weight=3) # D-Pad controller visual
        self.grid_columnconfigure(1, weight=2) # History list & Counters
        self.grid_rowconfigure(0, weight=1)

        # Left Frame: D-Pad visualization
        self.left_frame = ctk.CTkFrame(self, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.left_frame, text="Real-Time Gesture Tracking",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, padx=25, pady=(20, 10), sticky="w")

        # The D-Pad layout container
        self.dpad_container = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.dpad_container.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.dpad_container.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.dpad_container.grid_rowconfigure((0, 1, 2), weight=1)

        # 1. UP Arrow Frame
        self.arrow_up = self._create_arrow_box(self.dpad_container, "▲\nUP", 0, 2)
        
        # 2. LEFT Arrow Frame
        self.arrow_left = self._create_arrow_box(self.dpad_container, "◀\nLEFT", 1, 1)

        # 3. CENTER / Current Display Frame
        self.center_box = ctk.CTkFrame(
            self.dpad_container, fg_color="#181924", border_color="#2E3047", border_width=2, corner_radius=8
        )
        self.center_box.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        self.center_box.grid_columnconfigure(0, weight=1)
        self.center_box.grid_rowconfigure(0, weight=1)
        
        self.lbl_center = ctk.CTkLabel(
            self.center_box, text="NONE", font=ctk.CTkFont(size=18, weight="bold"), text_color="#A9B1D6"
        )
        self.lbl_center.grid(row=0, column=0, sticky="nsew")

        # 4. RIGHT Arrow Frame
        self.arrow_right = self._create_arrow_box(self.dpad_container, "▶\nRIGHT", 1, 3)

        # 5. DOWN Arrow Frame
        self.arrow_down = self._create_arrow_box(self.dpad_container, "▼\nDOWN", 2, 2)

        # 6. NEAR Panel (left side of D-pad)
        self.box_near = self._create_arrow_box(self.dpad_container, "●\nNEAR", 1, 0)
        
        # 7. FAR Panel (right side of D-pad)
        self.box_far = self._create_arrow_box(self.dpad_container, "○\nFAR", 1, 4)

        # Right Frame: Counters & History Logs
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure((0, 1), weight=1)

        # Counters Card
        self.counts_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.counts_card.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        self.counts_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.counts_card, text="Gesture Tally List",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        # Metric rows for tallies
        self.lbl_counts = {}
        idx = 1
        for name in ["UP", "DOWN", "LEFT", "RIGHT", "NEAR", "FAR"]:
            lbl_val = self._create_metric_row(self.counts_card, f"Gesture {name}:", "0 events", idx)
            self.lbl_counts[name] = lbl_val
            idx += 1

        # History Logs Card
        self.history_card = ctk.CTkFrame(self.right_frame, fg_color="#1E1F2E", border_color="#2E3047", border_width=1, corner_radius=12)
        self.history_card.grid(row=1, column=0, pady=(10, 0), sticky="nsew")
        self.history_card.grid_columnconfigure(0, weight=1)
        self.history_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.history_card, text="Gesture Event Feed",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF"
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Event log textbox
        self.txt_history = ctk.CTkTextbox(
            self.history_card, fg_color="#181924", font=ctk.CTkFont(family="Consolas", size=12), text_color="#A9B1D6"
        )
        self.txt_history.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def _create_arrow_box(self, parent, text, r, c):
        frame = ctk.CTkFrame(parent, fg_color=self.inactive_color, border_color=self.inactive_border, border_width=1, corner_radius=8)
        frame.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        lbl = ctk.CTkLabel(frame, text=text, font=ctk.CTkFont(size=14, weight="bold"), text_color="#565F89")
        lbl.grid(row=0, column=0, sticky="nsew")
        
        # Save reference to both components so we can style them later
        return {"frame": frame, "label": lbl}

    def _create_metric_row(self, parent, label_text, default_val, row_idx):
        lbl_desc = ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=12), text_color="#A9B1D6")
        lbl_desc.grid(row=row_idx, column=0, padx=20, pady=4, sticky="w")
        lbl_val = ctk.CTkLabel(parent, text=default_val, font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
        lbl_val.grid(row=row_idx, column=1, padx=20, pady=4, sticky="e")
        return lbl_val

    def push_data(self, gesture):
        """Processes a new gesture event, increments tallies, and updates local state."""
        self.active_gesture = gesture.upper()

        if self.active_gesture != "NONE":
            # Increment count
            if self.active_gesture in self.gesture_counts:
                self.gesture_counts[self.active_gesture] += 1
                
                # Push to history
                t_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.history.append(f"[{t_str}] Gesture detected: {self.active_gesture}")

    def update_ui(self):
        """Called by UI update loop (50ms interval) to light up D-pad slots and refresh tallies."""
        # 1. Update tally labels
        for name, lbl in self.lbl_counts.items():
            cnt = self.gesture_counts[name]
            lbl.configure(text=f"{cnt} event{'s' if cnt != 1 else ''}")

        # 2. Update active center display
        self.lbl_center.configure(text=self.active_gesture)
        if self.active_gesture != "NONE":
            self.lbl_center.configure(text_color="#FF1744")
        else:
            self.lbl_center.configure(text_color="#A9B1D6")

        # 3. Handle Arrow box highlights
        arrow_map = {
            "UP": self.arrow_up,
            "DOWN": self.arrow_down,
            "LEFT": self.arrow_left,
            "RIGHT": self.arrow_right,
            "NEAR": self.box_near,
            "FAR": self.box_far
        }

        # Reset all arrows to inactive status first
        for name, widget in arrow_map.items():
            widget["frame"].configure(fg_color=self.inactive_color, border_color=self.inactive_border)
            widget["label"].configure(text_color="#565F89")

        # Highlight the matching active gesture
        if self.active_gesture in arrow_map:
            active_widget = arrow_map[self.active_gesture]
            active_widget["frame"].configure(fg_color=self.active_color, border_color=self.active_border)
            active_widget["label"].configure(text_color="#0D0E15")

        # 4. Refresh history text box feed
        self.txt_history.delete("1.0", tk.END)
        for line in reversed(self.history):
            self.txt_history.insert(tk.END, line + "\n")
