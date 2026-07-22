#!/usr/bin/env python3
"""
Measure the centers of the 3 compartments, using the calibration data in
scale_config.json.

LEGACY: this targets the old firmware that streamed raw per-load-cell values
(`L1=.. | L2=.. | L3=.. | L4=..`). The current firmware calibrates on-device
and streams `DATA,w1,w2,w3,total` instead -- see hardware/README.md.
"""
import serial, re, time, json, glob
import numpy as np
from pathlib import Path

BAUD = 9600
CONFIG_FILE = "scale_config.json"
SAMPLES = 25

LINE_PATTERN = re.compile(
    r'L1=(-?\d+)\s*\|\s*L2=(-?\d+)\s*\|\s*L3=(-?\d+)\s*\|\s*L4=(-?\d+)'
)


def find_arduino():
    for p in ["/dev/ttyACM*", "/dev/ttyUSB*"]:
        ports = glob.glob(p)
        if ports:
            return ports[0]
    raise RuntimeError("Arduino not found")


def read_one(ser):
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        m = LINE_PATTERN.search(line)
        if m:
            return np.array([int(m.group(i)) for i in range(1, 5)], dtype=float)


def read_average(ser, n=SAMPLES):
    print(f"  sampling", end='', flush=True)
    frames = [read_one(ser) for _ in range(n)]
    for _ in range(n):
        print(".", end='', flush=True)
    print(" done")
    return np.mean(frames, axis=0)


def main():
    # load calibration
    if not Path(CONFIG_FILE).exists():
        print(f"Error: {CONFIG_FILE} not found")
        print("Run python3 calibrate.py first")
        return

    cfg = json.loads(Path(CONFIG_FILE).read_text())
    CELL_POS = np.array(cfg["cell_positions_mm"])
    CELL_ZEROS = np.array(cfg["cell_zeros_L"])
    TOTAL_FACTOR = cfg["total_factor"]
    KNOWN = cfg["known_weight_g"]

    print(f"Calibration loaded: total_factor={TOTAL_FACTOR:.2f}")
    print(f"           zero=[{CELL_ZEROS[0]:.0f}, {CELL_ZEROS[1]:.0f}, "
          f"{CELL_ZEROS[2]:.0f}, {CELL_ZEROS[3]:.0f}]\n")

    port = find_arduino()
    print(f"Connecting to Arduino: {port}")
    ser = serial.Serial(port, BAUD, timeout=2)
    time.sleep(2)
    ser.reset_input_buffer()

    print("\nPrepare:")
    print("  1. Rotate the 3-compartment plate into a Y layout:")
    print("     - compartment 1 at 12 o'clock (away from you)")
    print("     - compartment 2 at 8 o'clock (lower left)")
    print("     - compartment 3 at 4 o'clock (lower right)")
    print("  2. Tape 1/2/3 labels on the rim of the plate")
    input("\nReady? Press Enter...")

    labels = [
        "compartment 1 (12 o'clock)",
        "compartment 2 (8 o'clock)",
        "compartment 3 (4 o'clock)",
    ]
    compartments = []

    for lbl in labels:
        while True:
            print(f"\n{'='*60}\n  Measuring {lbl}\n{'='*60}")
            input(f"  Place the iPhone ({KNOWN} g) at the center of {lbl}, press Enter...")
            time.sleep(1)
            ser.reset_input_buffer()

            L = read_average(ser)
            delta = L - CELL_ZEROS
            total_delta = delta.sum()

            if abs(total_delta) < 500:
                print("  WARNING: reading too small, the phone may not be placed well, retry")
                continue

            cog_x = np.dot(CELL_POS[:, 0], delta) / total_delta
            cog_y = np.dot(CELL_POS[:, 1], delta) / total_delta
            weight = total_delta / TOTAL_FACTOR

            print(f"  weight: {weight:.1f} g  (expected ~{KNOWN} g, error {weight-KNOWN:+.1f} g)")
            print(f"  center: ({cog_x:.1f}, {cog_y:.1f}) mm")

            if abs(weight - KNOWN) > 20:
                if input("  error is large, accept? (y/n): ").lower() != 'y':
                    continue

            compartments.append((float(cog_x), float(cog_y)))
            break

    cfg["compartment_centers_mm"] = [list(c) for c in compartments]
    cfg["compartment_labels"] = labels
    Path(CONFIG_FILE).write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False))

    print(f"\n{'='*60}\nDone!\n{'='*60}")
    for lbl, (x, y) in zip(labels, compartments):
        print(f"  {lbl}: ({x:>6.1f}, {y:>6.1f}) mm")

    # geometry sanity check
    p = [np.array(c) for c in compartments]
    d12 = np.linalg.norm(p[0] - p[1])
    d13 = np.linalg.norm(p[0] - p[2])
    d23 = np.linalg.norm(p[1] - p[2])
    print(f"\nthree sides: {d12:.0f} / {d13:.0f} / {d23:.0f} mm")
    if max(d12, d13, d23) - min(d12, d13, d23) < 20:
        print("  Y geometry looks reasonable")
    else:
        print("  WARNING: sides differ a lot, check the plate is seated straight")

    ser.close()


if __name__ == "__main__":
    main()
