"""Head tracking for a DIY Raspberry Pi VR headset using an MPU-6050 gyro/accelerometer.

Wiring (MPU-6050 -> Raspberry Pi):
    VCC -> pin 1 (3.3V)
    GND -> pin 6 (GND)
    SDA -> pin 3 (GPIO2)
    SCL -> pin 5 (GPIO3)

Mount the sensor flat on top of the goggles, chip facing up, with its
Y arrow pointing forward (the way you look) and X arrow pointing to your right.
If a direction comes out backwards, flip the matching sign in AXIS_SIGNS.

Run on its own to print your head angles:  python3 head_tracker.py
"""

import math
import threading
import time

MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
DATA_START = 0x3B  # accel X high byte; 14 bytes: accel xyz, temp, gyro xyz

GYRO_LSB_PER_DPS = 131.0     # +/-250 deg/s range
ACCEL_LSB_PER_G = 16384.0    # +/-2 g range

# Flip any of these to -1 if that direction moves the wrong way in the headset.
AXIS_SIGNS = {"yaw": 1, "pitch": 1, "roll": 1}

# How much to trust the gyro vs. the accelerometer for pitch/roll (0..1).
# Higher = smoother but drifts more slowly back to level.
GYRO_TRUST = 0.98


def _signed16(hi, lo):
    v = (hi << 8) | lo
    return v - 65536 if v >= 32768 else v


class HeadTracker:
    """Reads the MPU-6050 in a background thread and keeps yaw/pitch/roll in degrees.

    yaw   = turning your head (positive = right)
    pitch = nodding (positive = looking up)
    roll  = tilting your head (positive = right ear down)
    """

    def __init__(self, bus_number=1, rate_hz=200):
        from smbus2 import SMBus  # imported here so the demo can run without it

        self.bus = SMBus(bus_number)
        self.period = 1.0 / rate_hz
        self.yaw = self.pitch = self.roll = 0.0
        self._lock = threading.Lock()
        self._running = False
        self._bias = (0.0, 0.0, 0.0)

        self.bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)    # wake up
        self.bus.write_byte_data(MPU_ADDR, GYRO_CONFIG, 0)   # +/-250 deg/s
        self.bus.write_byte_data(MPU_ADDR, ACCEL_CONFIG, 0)  # +/-2 g
        time.sleep(0.1)

    def _read_raw(self):
        d = self.bus.read_i2c_block_data(MPU_ADDR, DATA_START, 14)
        ax = _signed16(d[0], d[1]) / ACCEL_LSB_PER_G
        ay = _signed16(d[2], d[3]) / ACCEL_LSB_PER_G
        az = _signed16(d[4], d[5]) / ACCEL_LSB_PER_G
        gx = _signed16(d[8], d[9]) / GYRO_LSB_PER_DPS
        gy = _signed16(d[10], d[11]) / GYRO_LSB_PER_DPS
        gz = _signed16(d[12], d[13]) / GYRO_LSB_PER_DPS
        return ax, ay, az, gx, gy, gz

    def calibrate(self, seconds=2.0):
        """Measure gyro drift. Keep the headset completely still while this runs."""
        sums = [0.0, 0.0, 0.0]
        n = 0
        end = time.time() + seconds
        while time.time() < end:
            _, _, _, gx, gy, gz = self._read_raw()
            sums[0] += gx
            sums[1] += gy
            sums[2] += gz
            n += 1
            time.sleep(0.005)
        self._bias = tuple(s / n for s in sums)
        ax, ay, az, *_ = self._read_raw()
        with self._lock:
            self.pitch = math.degrees(math.atan2(ay, az)) * AXIS_SIGNS["pitch"]
            self.roll = math.degrees(math.atan2(-ax, az)) * AXIS_SIGNS["roll"]
            self.yaw = 0.0

    def recenter(self):
        """Make the current direction 'straight ahead'."""
        with self._lock:
            self.yaw = 0.0

    def get(self):
        with self._lock:
            return self.yaw, self.pitch, self.roll

    def _loop(self):
        last = time.perf_counter()
        while self._running:
            ax, ay, az, gx, gy, gz = self._read_raw()
            now = time.perf_counter()
            dt = now - last
            last = now

            gx -= self._bias[0]
            gy -= self._bias[1]
            gz -= self._bias[2]

            accel_pitch = math.degrees(math.atan2(ay, az)) * AXIS_SIGNS["pitch"]
            accel_roll = math.degrees(math.atan2(-ax, az)) * AXIS_SIGNS["roll"]

            with self._lock:
                # Complementary filter: gyro for fast motion, accelerometer to stop drift.
                self.pitch = GYRO_TRUST * (self.pitch + gx * AXIS_SIGNS["pitch"] * dt) + (1 - GYRO_TRUST) * accel_pitch
                self.roll = GYRO_TRUST * (self.roll + gy * AXIS_SIGNS["roll"] * dt) + (1 - GYRO_TRUST) * accel_roll
                # Yaw has no accelerometer reference, so it slowly drifts; press C to recenter.
                self.yaw += -gz * AXIS_SIGNS["yaw"] * dt
                self.yaw = (self.yaw + 180.0) % 360.0 - 180.0

            time.sleep(max(0.0, self.period - (time.perf_counter() - now)))

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False


class FakeTracker:
    """Stand-in for testing without a sensor: the demo drives it with the mouse/arrow keys."""

    def __init__(self):
        self.yaw = self.pitch = self.roll = 0.0

    def calibrate(self, seconds=0):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def recenter(self):
        self.yaw = 0.0

    def get(self):
        return self.yaw, self.pitch, self.roll


if __name__ == "__main__":
    t = HeadTracker()
    print("Calibrating - keep the sensor still...")
    t.calibrate()
    t.start()
    try:
        while True:
            y, p, r = t.get()
            print(f"yaw {y:7.1f}   pitch {p:7.1f}   roll {r:7.1f}", end="\r")
            time.sleep(0.05)
    except KeyboardInterrupt:
        t.stop()
        print()
