import time
import threading
import random
import math
import logging
import serial
import serial.tools.list_ports

class SerialManager:
    """
    Handles serial connection and reading in a separate thread.
    Supports a mock/demo mode for simulation.
    """
    def __init__(self, data_callback, status_callback):
        self.data_callback = data_callback          # Callback format: fn(sensor_type, data_tuple)
        self.status_callback = status_callback      # Callback format: fn(status_str, message)
        
        self.serial_port = None
        self.port_name = ""
        self.baud_rate = 115200
        
        self.running = False
        self.thread = None
        self.is_mock = False
        self.reconnect_attempts = 0
        self.auto_reconnect = True
        self.current_status = "Disconnected"

    @staticmethod
    def list_ports():
        """Lists available hardware serial ports."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports

    def connect(self, port_name, baud_rate=115200, auto_reconnect=True):
        """Initializes and starts the serial reading thread."""
        if self.running:
            self.disconnect()

        self.port_name = port_name
        self.baud_rate = baud_rate
        self.auto_reconnect = auto_reconnect
        self.running = True

        if port_name == "MOCK_DEMO":
            self.is_mock = True
            self.thread = threading.Thread(target=self._run_mock, name="MockSerialThread", daemon=True)
            self.thread.start()
            self.status_callback("Connected", "Mock serial simulation started successfully.")
            logging.info("Connected to MOCK_DEMO serial simulation.")
        else:
            self.is_mock = False
            self.thread = threading.Thread(target=self._run_serial, name="PySerialThread", daemon=True)
            self.thread.start()

    def disconnect(self):
        """Stops the reader thread and closes any open port."""
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception as e:
                logging.error(f"Error closing serial port: {e}")
        
        self.serial_port = None
        self.is_mock = False
        self.status_callback("Disconnected", "Serial communication stopped.")
        logging.info("Disconnected from serial port.")

    def is_connected(self):
        """Checks if the connection is active."""
        if self.is_mock:
            return self.running
        return self.serial_port is not None and self.serial_port.is_open

    def _set_status(self, status, msg):
        if self.current_status != status:
            self.current_status = status
            self.status_callback(status, msg)

    def _run_serial(self):
        """Main serial loop running in a background thread."""
        self._set_status("Connecting", f"Connecting to {self.port_name}...")
        
        while self.running:
            try:
                self.serial_port = serial.Serial()
                self.serial_port.port = self.port_name
                self.serial_port.baudrate = self.baud_rate
                self.serial_port.timeout = 1.0
                
                # Assert DTR and RTS (critical for Arduino Nano 33 BLE and CDC USB)
                self.serial_port.dtr = True
                self.serial_port.rts = True
                
                self.serial_port.open()
                self._set_status("Connected", f"Connected to {self.port_name} @ {self.baud_rate}")
                self.reconnect_attempts = 0
                
                # Toggle DTR to trigger microcontroller boot reset
                self.serial_port.dtr = False
                time.sleep(0.1)
                self.serial_port.dtr = True
                
                # Clear buffer
                self.serial_port.reset_input_buffer()
                
                accumulator = ""
                self.last_rx_time = time.time()
                timeout_triggered = False
                
                while self.running and self.serial_port.is_open:
                    # Timeout check: if no serial data is received for 2 seconds
                    if time.time() - self.last_rx_time > 2.0:
                        if not timeout_triggered:
                            self._set_status("No Serial Data Received", "No telemetry packets received for 2 seconds.")
                            self.data_callback("RAW", ("[WARNING] No Serial Data Received",))
                            timeout_triggered = True
                            
                    if self.serial_port.in_waiting > 0:
                        try:
                            # Read whatever is available in the buffer
                            chunk = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                            accumulator += chunk
                            
                            # Extract complete lines by splitting on newline
                            while "\n" in accumulator:
                                line, accumulator = accumulator.split("\n", 1)
                                line = line.strip()
                                if line:
                                    self.last_rx_time = time.time()
                                    if timeout_triggered:
                                        self._set_status("Connected", f"Connected to {self.port_name} @ {self.baud_rate}")
                                        timeout_triggered = False
                                    
                                    # Print raw packet to standard console for debugging
                                    print(f"RAW RX: {line}", flush=True)
                                    
                                    # Forward raw line to UI logger page
                                    self.data_callback("RAW", (line,))
                                    
                                    # Run the parser on the line
                                    self._parse_line(line)
                        except Exception as e:
                            logging.warning(f"Error reading/parsing serial chunk: {e}")
                    else:
                        time.sleep(0.005) # Small sleep to prevent high CPU usage
                        
            except (serial.SerialException, OSError) as e:
                logging.error(f"Serial port connection error: {e}")
                self._set_status("Connecting", f"Connection lost. Reconnecting...")
                
                if self.serial_port:
                    try:
                        self.serial_port.close()
                    except Exception:
                        pass
                    self.serial_port = None
                
                # Check if we should attempt reconnecting
                if self.auto_reconnect and self.running:
                    self.reconnect_attempts += 1
                    logging.info(f"Reconnecting attempt {self.reconnect_attempts} in 3 seconds...")
                    time.sleep(3.0)
                else:
                    self.running = False
                    self._set_status("Disconnected", f"Connection failed: {str(e)}")
                    break
            except Exception as e:
                logging.error(f"Unexpected exception in serial thread: {e}")
                time.sleep(1.0)

    def _parse_line(self, line):
        """
        Intelligently auto-detects and parses raw telemetry formats:
        - JSON: {"accelerometer": ...}
        - Prefix: ACC:x,y,z
        - Key-Value pairs: r = 120 g = 70 b = 50
        - CSV/Space/Tab separated: x \t y \t z
        - Plain text gesture: Detected UP gesture
        - Single integer: 148 (Proximity)
        """
        line = line.strip()
        if not line:
            return

        # 1. JSON Format
        if line.startswith("{") and line.endswith("}"):
            try:
                import json
                data = json.loads(line)
                parsed = False
                if "accelerometer" in data:
                    acc = data["accelerometer"]
                    self.data_callback("ACC", (float(acc.get("x", 0.0)), float(acc.get("y", 0.0)), float(acc.get("z", 1.0))))
                    parsed = True
                if "gyroscope" in data:
                    gyr = data["gyroscope"]
                    self.data_callback("GYR", (float(gyr.get("x", 0.0)), float(gyr.get("y", 0.0)), float(gyr.get("z", 0.0))))
                    parsed = True
                if "magnetometer" in data:
                    mag = data["magnetometer"]
                    self.data_callback("MAG", (float(mag.get("x", 0.0)), float(mag.get("y", 0.0)), float(mag.get("z", 0.0))))
                    parsed = True
                if "color" in data:
                    clr = data["color"]
                    r = int(clr.get("r", 0))
                    g = int(clr.get("g", 0))
                    b = int(clr.get("b", 0))
                    c = int(clr.get("c", int((r+g+b)/3*1.2)))
                    self.data_callback("CLR", (r, g, b, c))
                    parsed = True
                if "gesture" in data:
                    self.data_callback("GST", (str(data["gesture"]).upper(),))
                    parsed = True
                if "proximity" in data:
                    self.data_callback("PRX", (int(data["proximity"]),))
                    parsed = True
                
                if parsed:
                    return
            except Exception as e:
                logging.debug(f"JSON auto-detect fail: {e}")

        # 2. Custom Prefix Format (ACC:, GYR:, etc.)
        if ":" in line and not line.startswith("http"):
            try:
                parts = line.split(":", 1)
                prefix = parts[0].strip().upper()
                data_str = parts[1].strip()
                if prefix in ("ACC", "GYR", "MAG", "CLR", "GST", "PRX"):
                    if prefix in ("ACC", "GYR", "MAG"):
                        vals = [float(v) for v in data_str.split(",")]
                        if len(vals) == 3:
                            self.data_callback(prefix, tuple(vals))
                            return
                    elif prefix == "CLR":
                        vals = [int(v) for v in data_str.split(",")]
                        if len(vals) == 4:
                            self.data_callback(prefix, tuple(vals))
                            return
                    elif prefix == "GST":
                        self.data_callback(prefix, (data_str.upper(),))
                        return
                    elif prefix == "PRX":
                        self.data_callback(prefix, (int(data_str),))
                        return
            except Exception as e:
                logging.debug(f"Prefix parse fail: {e}")

        # 3. Plain Text Gesture: "Detected UP gesture"
        if "detected" in line.lower() and "gesture" in line.lower():
            for g in ["UP", "DOWN", "LEFT", "RIGHT", "NEAR", "FAR"]:
                if g in line.upper():
                    self.data_callback("GST", (g,))
                    return

        # 4. Key-Value pairs: "r = 120 g = 70 b = 50" or "R:120, G:70, B:50"
        if any(k in line.lower() for k in ["r =", "g =", "b ="]) or any(k in line.lower() for k in ["r:", "g:", "b:"]):
            try:
                import re
                numbers = [int(n) for n in re.findall(r'\d+', line)]
                if len(numbers) >= 3:
                    r, g, b = numbers[:3]
                    c = numbers[3] if len(numbers) > 3 else int((r+g+b)/3*1.2)
                    self.data_callback("CLR", (r, g, b, c))
                    return
            except Exception as e:
                logging.debug(f"Key-value parse fail: {e}")

        # 5. CSV / Space / Tab separated values: "0.01 \t -0.02 \t 0.98"
        normalized = line.replace(",", " ").replace("\t", " ").strip()
        tokens = normalized.split()
        if len(tokens) == 3:
            try:
                vals = [float(t) for t in tokens]
                x, y, z = vals
                mag = math.sqrt(x*x + y*y + z*z)
                
                # Check ranges to classify sensor type
                if 0.1 <= mag <= 4.0:
                    self.data_callback("ACC", (x, y, z))
                elif mag > 4.0:
                    self.data_callback("MAG", (x, y, z))
                    self.data_callback("GYR", (x, y, z))
                return
            except ValueError:
                pass

        # 6. Single Integer: Proximity or light intensity "148"
        if line.isdigit():
            val = int(line)
            self.data_callback("PRX", (val,))
            return

        # If we reach here, we could not parse it
        self._set_status("Invalid Serial Format", f"Failed to parse format for: {line}")
        self.data_callback("RAW", (f"[ERROR] Invalid Serial Format: {line}",))

    def _run_mock(self):
        """Simulates sensor readings at regular intervals."""
        import math
        import random
        import time
        import threading
        
        t = 0.0
        gesture_options = ["UP", "DOWN", "LEFT", "RIGHT", "NEAR", "FAR", "NONE"]
        last_gesture_time = time.time()
        
        # Color cycle parameter
        color_hue = 0.0

        while self.running:
            try:
                # 1. Accelerometer simulation: gravity + wave oscillation
                # Simulate a rotating gravity vector (roll & pitch oscillation)
                roll = math.sin(t * 0.5) * 0.3          # Roll oscillates between -17 and +17 deg
                pitch = math.cos(t * 0.3) * 0.4         # Pitch oscillates between -23 and +23 deg
                
                # Back-calculate gravity vector elements based on angles
                acc_x = -math.sin(pitch) + random.uniform(-0.02, 0.02)
                acc_y = math.sin(roll) * math.cos(pitch) + random.uniform(-0.02, 0.02)
                acc_z = math.cos(roll) * math.cos(pitch) + random.uniform(-0.02, 0.02)
                self.data_callback("ACC", (acc_x, acc_y, acc_z))

                # 2. Gyroscope simulation: rate of change of roll/pitch
                # Plus some random noise and occasional spin impulses
                gyr_x = (math.cos(roll) * 0.5 * 180 / math.pi) + random.uniform(-2.0, 2.0)
                gyr_y = (-math.sin(pitch) * 0.3 * 180 / math.pi) + random.uniform(-2.0, 2.0)
                gyr_z = math.sin(t * 0.8) * 10.0 + random.uniform(-1.0, 1.0)
                
                # Add an occasional rotation burst
                if int(t) % 15 == 0 and (t % 1.0 < 0.2):
                    gyr_z += 150.0 if (int(t) % 30 == 0) else -150.0
                    
                self.data_callback("GYR", (gyr_x, gyr_y, gyr_z))

                # 3. Magnetometer simulation: digital compass sweep
                # Sweep heading slowly from 0 to 360 deg
                heading_rad = (t * 0.05) % (2 * math.pi)
                # Field strength components (simulate a typical magnetic vector)
                mag_x = math.cos(heading_rad) * 30.0 + random.uniform(-1.0, 1.0)
                mag_y = math.sin(heading_rad) * 30.0 + random.uniform(-1.0, 1.0)
                mag_z = -45.0 + random.uniform(-2.0, 2.0)  # Dip angle component
                self.data_callback("MAG", (mag_x, mag_y, mag_z))

                # 4. Color Sensor simulation: HSV cycle to RGB
                color_hue = (color_hue + 0.005) % 1.0
                # HSV to RGB Conversion
                h_i = int(color_hue * 6)
                f = color_hue * 6 - h_i
                p = 0.1
                q = 1.0 - f
                t_val = f
                
                # Map Hue to RGB
                r_f, g_f, b_f = 0.0, 0.0, 0.0
                if h_i == 0: r_f, g_f, b_f = 1.0, t_val, p
                elif h_i == 1: r_f, g_f, b_f = q, 1.0, p
                elif h_i == 2: r_f, g_f, b_f = p, 1.0, t_val
                elif h_i == 3: r_f, g_f, b_f = p, q, 1.0
                elif h_i == 4: r_f, g_f, b_f = t_val, p, 1.0
                elif h_i == 5: r_f, g_f, b_f = 1.0, p, q
                
                # Add white noise and scale
                clr_r = int(r_f * 220 + random.uniform(0, 15))
                clr_g = int(g_f * 220 + random.uniform(0, 15))
                clr_b = int(b_f * 220 + random.uniform(0, 15))
                clr_c = int((clr_r + clr_g + clr_b) / 3 * 1.2) # Clear/ambient
                self.data_callback("CLR", (clr_r, clr_g, clr_b, clr_c))

                # 5. Gesture Sensor simulation: trigger every 4 to 6 seconds
                now = time.time()
                if now - last_gesture_time > random.uniform(4.0, 6.0):
                    # Pick a real gesture (avoiding NONE 70% of the time when triggered)
                    active_gestures = ["UP", "DOWN", "LEFT", "RIGHT", "NEAR", "FAR"]
                    gesture = random.choice(active_gestures)
                    self.data_callback("GST", (gesture,))
                    last_gesture_time = now
                    # We send the gesture, and after a small delay, return to NONE
                    threading.Thread(target=self._send_none_gesture_delayed, daemon=True).start()

                # 6. Proximity Sensor simulation: sine wave sweep between 10 and 240
                # Representing something moving closer and further
                prox = int(127 + 110 * math.sin(t * 0.2))
                self.data_callback("PRX", (prox,))

                # Time step
                t += 0.05
                time.sleep(0.05) # Send updates at 20Hz (50ms interval)
                
            except Exception as e:
                logging.error(f"Error in mock serial generation loop: {e}")
                time.sleep(1.0)

    def _send_none_gesture_delayed(self):
        """Sends a NONE gesture event after a short delay to clear UI flash."""
        time.sleep(1.2)
        if self.running and self.is_mock:
            self.data_callback("GST", ("NONE",))
