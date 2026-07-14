import time
import logging
import customtkinter as ctk
from settings import Settings
from logger import DataLogger
from serial_manager import SerialManager
from dashboard import MainWindow

# Initialize appearance theme modes
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SplashScreen(ctk.CTkToplevel):
    """
    Borderless, centered splash screen with a loading bar
    running simulated configuration initialization checks.
    """
    def __init__(self, parent, width=600, height=350):
        super().__init__(parent)
        self.parent = parent
        self.width = width
        self.height = height

        # Configure window: borderless and topmost
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Center the window on screen
        self._center_window()

        # Dark theme background color
        self.configure(fg_color="#0D0E15")

        # Outer border frame
        self.border_frame = ctk.CTkFrame(self, fg_color="transparent", border_color="#2E3047", border_width=2, corner_radius=12)
        self.border_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Title Label
        self.lbl_title = ctk.CTkLabel(
            self.border_frame, text="⚡ ARDUINO TELEMETRY DASHBOARD",
            font=ctk.CTkFont(size=20, weight="bold"), text_color="#00E5FF"
        )
        self.lbl_title.pack(pady=(45, 10))

        # Subtitle Label
        self.lbl_subtitle = ctk.CTkLabel(
            self.border_frame, text="Arduino Nano 33 BLE Sense Rev2 Interface",
            font=ctk.CTkFont(size=13), text_color="#A9B1D6"
        )
        self.lbl_subtitle.pack(pady=(0, 30))

        # Status Label
        self.lbl_status = ctk.CTkLabel(
            self.border_frame, text="Loading application dependencies...",
            font=ctk.CTkFont(size=12, slant="italic"), text_color="#565F89"
        )
        self.lbl_status.pack(pady=(20, 5))

        # Loading Progress Bar
        self.progress = ctk.CTkProgressBar(
            self.border_frame, width=400, height=12, progress_color="#00E5FF", fg_color="#1E1F2E"
        )
        self.progress.pack(pady=5)
        self.progress.set(0.0)

        # Developer Credit Label
        self.lbl_credit = ctk.CTkLabel(
            self.border_frame, text="College Engineering Presentation Build | v1.0.0",
            font=ctk.CTkFont(size=10), text_color="#2C2E3E"
        )
        self.lbl_credit.pack(side="bottom", pady=20)

        # Start loading sequence
        self.progress_val = 0.0
        self.after(200, self._perform_step)

    def _center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (self.width / 2))
        y = int((screen_height / 2) - (self.height / 2))
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _perform_step(self):
        """Simulates loading system configurations by updating progress and messages."""
        steps = [
            (0.15, "Loading configuration settings..."),
            (0.35, "Initializing file logger components..."),
            (0.55, "Scanning hardware COM serial ports..."),
            (0.75, "Configuring dashboard interface themes..."),
            (0.95, "Allocating visual canvas memory buffers..."),
            (1.0, "Launching Telemetry Dashboard...")
        ]

        # Find current stage matching progress_val
        current_msg = "Starting initialization sequence..."
        for prog, msg in steps:
            if self.progress_val < prog:
                current_msg = msg
                break
            elif self.progress_val >= 1.0:
                current_msg = steps[-1][1]

        # Update visual properties
        self.lbl_status.configure(text=current_msg)
        self.progress.set(self.progress_val)

        # Increment progress
        self.progress_val += 0.04

        if self.progress_val <= 1.05:
            # Re-schedule next step
            self.after(50, self._perform_step)
        else:
            # End splash screen: destroy splash and reveal main window
            self.destroy()
            self.parent.deiconify()


def main():
    logging.info("Application starting...")

    # 1. Initialize settings manager
    settings = Settings()

    # 2. Initialize log manager
    logger = DataLogger()

    # 3. Create SerialManager and register callback methods
    def on_serial_data(prefix, vals):
        if hasattr(app, "handle_serial_data"):
            app.handle_serial_data(prefix, vals)

    def on_serial_status(status, msg):
        if hasattr(app, "update_connection_status"):
            app.update_connection_status(status, msg)

    serial_mgr = SerialManager(
        data_callback=on_serial_data,
        status_callback=on_serial_status
    )

    # 4. Instantiate MainWindow (start withdrawn/hidden)
    global app
    app = MainWindow(serial_mgr, logger, settings)
    app.withdraw()

    # 5. Launch Splash Screen overlay on top of MainWindow
    SplashScreen(app)

    # 6. Enter application main event loop
    try:
        app.mainloop()
    except KeyboardInterrupt:
        logging.info("Application closed by keyboard interrupt.")
    except Exception as e:
        logging.critical(f"Unhandled critical exception in application mainloop: {e}")
    finally:
        # Stop background worker threads on exit
        serial_mgr.disconnect()
        logger.stop_logging()
        logging.info("Application terminated cleanly.")

if __name__ == "__main__":
    main()
