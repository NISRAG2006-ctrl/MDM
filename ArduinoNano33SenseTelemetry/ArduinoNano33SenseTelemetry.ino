/*
  Arduino Nano 33 BLE Sense Rev2 Telemetry Source
  
  Reads values from the onboard sensors and sends them over Serial Comm 
  using a custom prefix-formatted ASCII protocol:
  
  - ACC:x,y,z        (Accelerometer: G's)
  - GYR:x,y,z        (Gyroscope: d/s)
  - MAG:x,y,z        (Magnetometer: uT)
  - CLR:r,g,b,c      (Color Sensor: RGB + Clear)
  - PRX:val          (Proximity: 0-255)
  - GST:val          (Gesture: UP, DOWN, LEFT, RIGHT, NEAR, FAR)

  Flash this code using the Arduino IDE. Make sure to install:
  - Arduino_LSM6DSOX (IMU)
  - Arduino_LIS3MDL (Magnetometer)
  - Arduino_APDS9960 (Color/Proximity/Gesture)
*/

#include <Arduino_LSM6DSOX.h>
#include <Arduino_LIS3MDL.h>
#include <Arduino_APDS9960.h>

// Sampling Intervals (milliseconds)
const unsigned long IMU_INTERVAL = 50;       // 20 Hz
const unsigned long MAG_INTERVAL = 100;      // 10 Hz
const unsigned long COLOR_INTERVAL = 200;    // 5 Hz
const unsigned long PROX_INTERVAL = 100;     // 10 Hz

unsigned long lastIMUTime = 0;
unsigned long lastMagTime = 0;
unsigned long lastColorTime = 0;
unsigned long lastProxTime = 0;

void setup() {
  Serial.begin(115200);
  // Wait for serial connection to open (optional, commented out for standalone operation)
  // while (!Serial);

  // Initialize LSM6DSOX (IMU)
  if (!IMU.begin()) {
    Serial.println("SYS_ERR: Failed to initialize LSM6DSOX IMU!");
  }

  // Initialize LIS3MDL (Magnetometer)
  if (!magneticFieldAvailable() || !LIS3MDL.begin()) {
    Serial.println("SYS_ERR: Failed to initialize LIS3MDL Magnetometer!");
  }

  // Initialize APDS9960 (Color, Proximity, Gesture)
  if (!APDS.begin()) {
    Serial.println("SYS_ERR: Failed to initialize APDS9960 Sensor!");
  }
}

void loop() {
  unsigned long currentTime = millis();

  // 1. Read LSM6DSOX Accelerometer and Gyroscope
  if (currentTime - lastIMUTime >= IMU_INTERVAL) {
    lastIMUTime = currentTime;
    
    float ax, ay, az;
    float gx, gy, gz;
    
    // Read and send accelerometer
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(ax, ay, az);
      Serial.print("ACC:");
      Serial.print(ax, 3); Serial.print(",");
      Serial.print(ay, 3); Serial.print(",");
      Serial.println(az, 3);
    }
    
    // Read and send gyroscope
    if (IMU.gyroscopeAvailable()) {
      IMU.readGyroscope(gx, gy, gz);
      Serial.print("GYR:");
      Serial.print(gx, 2); Serial.print(",");
      Serial.print(gy, 2); Serial.print(",");
      Serial.println(gz, 2);
    }
  }

  // 2. Read LIS3MDL Magnetometer
  if (currentTime - lastMagTime >= MAG_INTERVAL) {
    lastMagTime = currentTime;
    
    float mx, my, mz;
    if (magneticFieldAvailable()) {
      readMagneticField(mx, my, mz);
      Serial.print("MAG:");
      Serial.print(mx, 2); Serial.print(",");
      Serial.print(my, 2); Serial.print(",");
      Serial.println(mz, 2);
    }
  }

  // 3. Read APDS9960 Gesture Events
  if (APDS.gestureAvailable()) {
    int gesture = APDS.readGesture();
    switch (gesture) {
      case GESTURE_UP:
        Serial.println("GST:UP");
        break;
      case GESTURE_DOWN:
        Serial.println("GST:DOWN");
        break;
      case GESTURE_LEFT:
        Serial.println("GST:LEFT");
        break;
      case GESTURE_RIGHT:
        Serial.println("GST:RIGHT");
        break;
      case GESTURE_NEAR:
        Serial.println("GST:NEAR");
        break;
      case GESTURE_FAR:
        Serial.println("GST:FAR");
        break;
      default:
        // Do not flood NONE packets, only send active events.
        // Python handles clearing events back to NONE automatically.
        break;
    }
  }

  // 4. Read APDS9960 Proximity Sensor
  if (currentTime - lastProxTime >= PROX_INTERVAL) {
    lastProxTime = currentTime;
    
    if (APDS.proximityAvailable()) {
      int proximity = APDS.readProximity();
      // APDS9960 returns proximity: 0 (far) to 255 (extremely close)
      Serial.print("PRX:");
      Serial.println(proximity);
    }
  }

  // 5. Read APDS9960 Color Sensor
  if (currentTime - lastColorTime >= COLOR_INTERVAL) {
    lastColorTime = currentTime;
    
    if (APDS.colorAvailable()) {
      int r, g, b, c;
      APDS.readColor(r, g, b, c);
      Serial.print("CLR:");
      Serial.print(r); Serial.print(",");
      Serial.print(g); Serial.print(",");
      Serial.print(b); Serial.print(",");
      Serial.println(c);
    }
  }
}
