import os
import csv
import json
import logging
from datetime import datetime
from collections import deque

# Ensure logs and exports directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("exports", exist_ok=True)

# Configure standard application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class DataLogger:
    """
    Manages recording and exporting of real-time sensor data.
    """
    def __init__(self, max_buffer_size=1000):
        self.logging_active = False
        self.log_buffer = deque(maxlen=max_buffer_size)
        self.current_session_file = None
        self.csv_writer = None
        self.session_start_time = None

    def start_logging(self):
        """Starts recording sensor data to a new session file."""
        if self.logging_active:
            return
        
        self.logging_active = True
        self.session_start_time = datetime.now()
        timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"exports/sensor_log_{timestamp}.csv"
        
        try:
            self.current_session_file = open(filename, mode='w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.current_session_file)
            # Write Header
            self.csv_writer.writerow(["Timestamp", "Sensor Name", "Values"])
            logging.info(f"Sensor data logging started. Session file: {filename}")
        except Exception as e:
            logging.error(f"Failed to start session file logger: {e}")
            self.logging_active = False
            self.current_session_file = None
            self.csv_writer = None

    def stop_logging(self):
        """Stops the current logging session."""
        if not self.logging_active:
            return
        
        self.logging_active = False
        if self.current_session_file:
            try:
                self.current_session_file.close()
                logging.info("Sensor data logging stopped.")
            except Exception as e:
                logging.error(f"Error closing logging session file: {e}")
            finally:
                self.current_session_file = None
                self.csv_writer = None

    def is_logging(self):
        """Checks if data logging is currently active."""
        return self.logging_active

    def log_sensor_data(self, sensor_name, values):
        """
        Logs a single sensor reading.
        values can be a list, dict, or string.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        val_str = str(values)
        
        # Add to standard in-memory buffer
        log_entry = {
            "timestamp": timestamp,
            "sensor": sensor_name,
            "values": val_str
        }
        self.log_buffer.append(log_entry)

        # Write to active session file if logging is enabled
        if self.logging_active and self.csv_writer:
            try:
                self.csv_writer.writerow([timestamp, sensor_name, val_str])
            except Exception as e:
                logging.error(f"Failed to write sensor data line: {e}")

    def get_recent_logs(self, limit=100):
        """Returns the most recent log entries from the buffer."""
        logs = list(self.log_buffer)
        return logs[-limit:]

    def clear_logs(self):
        """Clears the memory buffer."""
        self.log_buffer.clear()
        logging.info("In-memory logs cleared.")

    def export_to_csv(self, file_path):
        """Exports all in-memory logs to a specific CSV file."""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Sensor Name", "Values"])
                for entry in self.log_buffer:
                    writer.writerow([entry["timestamp"], entry["sensor"], entry["values"]])
            logging.info(f"Logs exported to CSV: {file_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting CSV: {e}")
            return False

    def export_to_json(self, file_path):
        """Exports all in-memory logs to a specific JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(list(self.log_buffer), f, indent=4)
            logging.info(f"Logs exported to JSON: {file_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting JSON: {e}")
            return False
