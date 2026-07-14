import os
import json
import logging

class Settings:
    """
    Manages application configurations and saves them to config.json.
    """
    DEFAULT_SETTINGS = {
        "theme": "Dark",
        "color_theme": "blue",  # "blue", "green", "dark-blue"
        "baud_rate": 115200,
        "refresh_rate_ms": 50,  # Serial polling rate
        "graph_speed_points": 100,  # Number of points displayed on charts
        "notification_sounds": True,
        "auto_connect": True,
        "last_com_port": ""
    }

    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Loads settings from config.json, creating it with defaults if missing."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge loaded settings into default to ensure all keys exist
                    for k, v in loaded.items():
                        if k in self.settings:
                            self.settings[k] = v
                logging.info("Settings loaded successfully.")
            else:
                self.save()
                logging.info("Settings file not found. Created defaults.")
        except Exception as e:
            logging.error(f"Error loading settings: {e}. Using defaults.")

    def save(self):
        """Saves current settings to config.json."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            logging.info("Settings saved successfully.")
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    def get(self, key):
        """Get a setting value by key."""
        return self.settings.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        """Set a setting value and save to file."""
        if key in self.DEFAULT_SETTINGS:
            self.settings[key] = value
            self.save()
        else:
            logging.warning(f"Attempted to set invalid setting key: {key}")
