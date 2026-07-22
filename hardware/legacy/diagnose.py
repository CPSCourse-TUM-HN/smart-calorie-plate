"""Live monitor of the raw L values + center-of-gravity, to see which
compartment is misbehaving.

LEGACY: this targets the old firmware that streamed raw per-load-cell values
(`L1=.. | L2=.. | L3=.. | L4=..`). The current firmware calibrates on-device
and streams `DATA,w1,w2,w3,total` instead -- see hardware/README.md.
"""
import serial, re, time, json, glob
import numpy as np
from pathlib import Path

cfg = json.loads(Path('scale_config.json').read_text())
CELL_POS = np.array(cfg['cell_positions_mm'])
CELL_ZEROS = np.array(cfg['cell_zeros_L'])
TF = cfg['total_factor']

port = glob.glob('/dev/ttyACM*')[0]
ser = serial.Serial(port, 9600, timeout=2)
time.sleep(2)
ser.reset_input_buffer()

pat = re.compile(r'L1=(-?\d+).*L2=(-?\d+).*L3=(-?\d+).*L4=(-?\d+)')

print("Live monitor - Ctrl+C to stop")
print("Move the phone around, watch the 4-channel deltas and COG\n")
print(f"{'dL1':>7} {'dL2':>7} {'dL3':>7} {'dL4':>7} | {'W':>6}g {'X':>6} {'Y':>6}")
print("-" * 65)

try:
    while True:
        line = ser.readline().decode('utf-8', errors='ignore')
        m = pat.search(line)
        if not m: continue
        L = np.array([int(m.group(i)) for i in range(1, 5)], dtype=float)
        d = L - CELL_ZEROS
        tot = d.sum()
        if abs(tot) < 200:
            print(f"{d[0]:>7.0f} {d[1]:>7.0f} {d[2]:>7.0f} {d[3]:>7.0f} | (empty plate)")
            continue
        cog_x = np.dot(CELL_POS[:, 0], d) / tot
        cog_y = np.dot(CELL_POS[:, 1], d) / tot
        w = tot / TF

        # mark direction of each channel with + / - / 0
        signs = ["+" if x > 500 else ("-" if x < -500 else "0") for x in d]
        marker = "".join(signs)
        print(f"{d[0]:>7.0f} {d[1]:>7.0f} {d[2]:>7.0f} {d[3]:>7.0f} | "
              f"{w:>6.1f} {cog_x:>6.0f} {cog_y:>6.0f}  [{marker}]")
except KeyboardInterrupt:
    ser.close()
    print("\nStopped")
