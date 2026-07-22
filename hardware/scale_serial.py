"""Serial link to the Arduino scale -- the authoritative weighing interface.

This matches the protocol in arduino/smart_calorie_plate/smart_calorie_plate.ino:

  Arduino -> Jetson   DATA,weight1,weight2,weight3,totalWeight   (grams, calibrated on-device)
                      plus status lines: "Tare completed.", "Nutrition received: ...", etc.
  Jetson  -> Arduino  NUTRI,kcal,protein,carbs,fat               (shown on the OLED)
                      t / T                                       (manual tare, 5 s countdown)

The per-compartment grams are already calibrated inside the firmware
(C1_*/C2_*/C3_* coefficients), so there is nothing to calibrate here -- we
just read the numbers it sends.

Run directly to stream weights (replaces the old weigh_via_usb.py):
    python3 scale_serial.py
"""
import glob
import re
import time

import serial

BAUD = 9600

# DATA,weight1,weight2,weight3,totalWeight  (integers, printed with 0 decimals)
DATA_PATTERN = re.compile(
    r'DATA,\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)'
)


def find_port() -> str:
    for pattern in ["/dev/ttyACM*", "/dev/ttyUSB*"]:
        ports = glob.glob(pattern)
        if ports:
            return ports[0]
    raise RuntimeError("Arduino not found, check the USB connection")


class ScaleSerial:
    """Thin wrapper around the Arduino serial link."""

    def __init__(self, port: str | None = None, baud: int = BAUD):
        self.port = port or find_port()
        self.ser = serial.Serial(self.port, baud, timeout=1)
        time.sleep(2)  # let the Arduino reboot on connect and finish setup()
        self.ser.reset_input_buffer()
        # latest per-compartment weights and total (grams)
        self.weights = [0.0, 0.0, 0.0]
        self.total = 0.0

    def read_line(self) -> str:
        return self.ser.readline().decode("utf-8", errors="ignore").strip()

    def poll(self) -> dict | None:
        """Read one line. Returns a dict on a DATA line, else None (and prints
        any status/info line so it is not swallowed silently)."""
        line = self.read_line()
        if not line:
            return None
        m = DATA_PATTERN.search(line)
        if not m:
            print(f"[arduino] {line}")
            return None
        self.weights = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
        self.total = float(m.group(4))
        return {"weights": self.weights, "total": self.total}

    def read_latest(self, drain: int = 20) -> dict:
        """Drain buffered lines and return the most recent weights, so callers
        get a fresh reading rather than a stale buffered one."""
        latest = {"weights": self.weights, "total": self.total}
        for _ in range(drain):
            if self.ser.in_waiting <= 0:
                break
            r = self.poll()
            if r:
                latest = r
        return latest

    def send_nutrition(self, kcal: float, protein: float, carbs: float, fat: float) -> None:
        """Push nutrition to the OLED: NUTRI,kcal,protein,carbs,fat"""
        msg = f"NUTRI,{kcal:.0f},{protein:.0f},{carbs:.0f},{fat:.0f}\n"
        self.ser.write(msg.encode("utf-8"))

    def tare(self) -> None:
        """Trigger a manual tare (Arduino counts down 5 s, then zeros)."""
        self.ser.write(b"t\n")

    def close(self) -> None:
        self.ser.close()


def main():
    scale = ScaleSerial()
    print(f"Connecting to {scale.port}")
    print("Ready! Press Ctrl+C to stop.\n")
    try:
        while True:
            r = scale.poll()
            if r:
                w = r["weights"]
                print(f"[{time.strftime('%H:%M:%S')}] "
                      f"C1={w[0]:>6.0f} C2={w[1]:>6.0f} C3={w[2]:>6.0f}  "
                      f"total={r['total']:>6.0f} g")
    except KeyboardInterrupt:
        print("\nStopped by user")
        scale.close()


if __name__ == "__main__":
    main()
