# Raspberry Pi DIY VR Headset

Snow goggles + VR lenses + a small HDMI screen + Raspberry Pi + MPU-6050 gyro.

## Parts
- Raspberry Pi 4 or 5 (3B+ works, just slower)
- 5.5"–6" HDMI LCD, 1080p or 1440p
- A pair of VR lenses (~40–45 mm focal length) — buy these, homemade ones are blurry
- MPU-6050 gyro/accelerometer module
- 4 female-to-female jumper wires
- Snow goggles + cardboard/foam to hold the screen ~4–5 cm behind the lenses

## Wiring (MPU-6050 → Pi)
| MPU-6050 | Pi pin |
|----------|--------|
| VCC | 1 (3.3V) |
| GND | 6 (GND) |
| SDA | 3 (GPIO2) |
| SCL | 5 (GPIO3) |

Mount the sensor flat on top of the goggles, chip up, **Y arrow pointing forward**.

## Setup on the Pi
```bash
sudo raspi-config          # Interface Options -> I2C -> Enable, then reboot
sudo apt install -y python3-pygame python3-smbus2 i2c-tools
i2cdetect -y 1             # should show 68 — that's the gyro
```

## Run
```bash
python3 head_tracker.py    # step 1: check the gyro (prints yaw/pitch/roll)
python3 vr_demo.py         # step 2: put the headset on
python3 vr_demo.py --fake --windowed   # test on any computer with the mouse
```
Keep the headset still for the first 2 seconds (it calibrates).

Keys: **C** recenter, **+/-** eye spacing, **Esc** quit.

## Tuning
- Something moves the wrong way → flip its sign in `AXIS_SIGNS` in `head_tracker.py`.
- View slowly spins sideways → yaw drift (the MPU-6050 has no compass); press **C**.
  Upgrade to a BNO085 for drift-free tracking.
- Double vision → adjust the screen distance, then **+/-** for eye spacing.
- Objects look too big/small → change `FOV_DEG` in `vr_demo.py`.
