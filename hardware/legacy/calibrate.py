#!/usr/bin/env python3
"""
Scale calibration -- done entirely on the Python side, so it does not depend
on the Arduino's tare being reliable.

  Step 1: record the empty-plate zero point
  Step 2: use an iPhone (206 g) to measure the scale factor
  Step 3: verify the empty plate reads back ~0

LEGACY: this targets the old firmware that streamed raw per-load-cell values
(`L1=.. | L2=.. | L3=.. | L4=..`). The current firmware calibrates on-device
(the C1_*/C2_*/C3_* coefficients in the .ino) and streams `DATA,w1,w2,w3,total`
instead, so this script is kept only for reference -- see hardware/README.md.
"""
import serial, re, time, json, glob
import numpy as np
from pathlib import Path

CELL_POS = [
    [ 40,  -62.5],  # Cell 1
    [ 62.5, -40],   # Cell 2
    [-40,   62.5],  # Cell 3
    [-62.5,  40],   # Cell 4
]
KNOWN_WEIGHT_G = 206.0  # iPhone 14 Pro
BAUD = 9600
CONFIG_FILE = "scale_config.json"

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


def read_stable(ser, n=50, stability_thr=1000):
    print(f"  sampling {n} frames", end='', flush=True)
    frames = []
    for _ in range(n):
        frames.append(read_one(ser))
        print(".", end='', flush=True)
    print(" done")
    frames = np.array(frames)
    means = frames.mean(axis=0)
    stds = frames.std(axis=0)
    print(f"  4-channel means: {means[0]:.0f}  {means[1]:.0f}  "
          f"{means[2]:.0f}  {means[3]:.0f}")
    print(f"  max noise: +/-{stds.max():.0f}")
    if stds.max() > stability_thr:
        print(f"  WARNING: noisy (>{stability_thr}), data may be unstable")
        return means, False
    return means, True


def countdown(sec, msg):
    for i in range(sec, 0, -1):
        print(f"\r  {msg} {i}s...  ", end='', flush=True)
        time.sleep(1)
    print()


def main():
    port = find_arduino()
    print(f"Connecting to Arduino: {port}\n")
    ser = serial.Serial(port, BAUD, timeout=2)
    time.sleep(2)
    ser.reset_input_buffer()

    # ===== Step 1: empty-plate zero =====
    print("="*60)
    print("  Step 1/3 . Empty-plate zero calibration")
    print("="*60)
    print("\nPrepare:")
    print("  - Place the 3-compartment plate on the load platform")
    print("  - Put nothing else on the scale")
    print("  - Do not touch the rig, let it settle for 5 s")
    input("\nReady? Press Enter...")
    countdown(5, "waiting for the device to settle")
    ser.reset_input_buffer()

    zero_L, stable = read_stable(ser, n=50)
    if not stable and input("  data unstable, force continue? (y/n): ").lower() != 'y':
        return
    print(f"\nEmpty-plate zero recorded")

    # ===== Step 2: scale factor =====
    print("\n" + "="*60)
    print(f"  Step 2/3 . Calibrate factor with the iPhone ({KNOWN_WEIGHT_G} g)")
    print("="*60)
    print(f"\nPlease:")
    print(f"  - Lay the iPhone flat in the *center* of the plate (any cell is fine, just centered)")
    print(f"  - Do not rest your hand on it")
    input("\nReady? Press Enter...")
    countdown(3, "waiting for the device to settle")
    ser.reset_input_buffer()

    with_L, stable = read_stable(ser, n=30)
    if not stable and input("  data unstable, force continue? (y/n): ").lower() != 'y':
        return

    # compute factor
    delta = with_L - zero_L
    total_delta = delta.sum()
    total_factor = total_delta / KNOWN_WEIGHT_G

    print(f"\nCompute:")
    print(f"  delta sum = {total_delta:.0f}")
    print(f"  total_factor = {total_delta:.0f} / {KNOWN_WEIGHT_G} = {total_factor:.2f}")
    if abs(total_factor) < 50 or abs(total_factor) > 500:
        print(f"  WARNING: factor looks off! usually between -100 and -200")
    else:
        print(f"  factor looks reasonable")

    # ===== Step 3: verify empty plate =====
    print("\n" + "="*60)
    print("  Step 3/3 . Verify -- remove the phone, it should read back ~0")
    print("="*60)
    input(f"\nRemove the iPhone, press Enter to verify...")
    countdown(3, "waiting to settle")
    ser.reset_input_buffer()

    check, _ = read_stable(ser, n=20)
    check_delta = check - zero_L
    check_weight = check_delta.sum() / total_factor
    print(f"\n  verification reading: {check_weight:.1f} g")

    if abs(check_weight) < 5:
        print("  Perfect! calibration succeeded")
    elif abs(check_weight) < 15:
        print("  slight offset, probably drift, usable")
    else:
        print(f"  large offset, recommend re-running calibration")

    # save
    config = json.loads(Path(CONFIG_FILE).read_text()) \
             if Path(CONFIG_FILE).exists() else {}
    config.update({
        "cell_positions_mm": CELL_POS,
        "cell_zeros_L": zero_L.tolist(),
        "total_factor": float(total_factor),
        "known_weight_g": KNOWN_WEIGHT_G,
        "calibrated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    Path(CONFIG_FILE).write_text(
        json.dumps(config, indent=2, ensure_ascii=False))
    print(f"\nSaved to {CONFIG_FILE}")
    print(f"\nNext: python3 measure_compartments.py")
    ser.close()


if __name__ == "__main__":
    main()
