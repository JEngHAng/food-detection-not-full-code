#!/usr/bin/env python3
"""
test_loadcell.py — ทดสอบ Load Cell + HX711
Library: hx711==1.1.2.x  (pip install hx711)
Wiring:  DT  → GPIO 5 (Pin 29)
         SCK → GPIO 6 (Pin 31)
"""

import time
import sys
import statistics

# ── ปรับ pin ตาม wiring ของคุณ ──────────────────────────────
DT_PIN  = 5   # GPIO Data
SCK_PIN = 6   # GPIO Clock
# ─────────────────────────────────────────────────────────────

try:
    from hx711 import HX711
    print("[OK] import hx711 สำเร็จ")
except ImportError as e:
    print(f"[ERROR] import hx711 ไม่ได้: {e}")
    print("ติดตั้งด้วย: pip install hx711")
    sys.exit(1)


# ─── Helper: get_raw_data() คืน list → เราหาค่าเฉลี่ยเอง ─────
def read_mean(hx, n=5):
    """อ่าน n รอบ คืนค่าเฉลี่ย หรือ None ถ้าอ่านไม่ได้"""
    samples = []
    for _ in range(n):
        data = hx.get_raw_data()      # คืน list หรือ False
        if data is not False and data:
            samples.extend(data)
        time.sleep(0.05)
    if not samples:
        return None
    # ตัด outlier ด้วย IQR
    if len(samples) >= 6:
        s = sorted(samples)
        q1, q3 = s[len(s)//4], s[3*len(s)//4]
        iqr = q3 - q1
        samples = [x for x in samples if q1 - 1.5*iqr <= x <= q3 + 1.5*iqr]
    return statistics.mean(samples) if samples else None


# ════════════════════════════════════════════════════════════════
# STEP 1 — เชื่อมต่อ HX711
# ════════════════════════════════════════════════════════════════
print("\n" + "="*50)
print("STEP 1: เชื่อมต่อ HX711")
print("="*50)

try:
    hx = HX711(dout_pin=DT_PIN, pd_sck_pin=SCK_PIN)
    print(f"[OK] HX711 object สำเร็จ  (DT={DT_PIN}, SCK={SCK_PIN})")
except Exception as e:
    print(f"[FAIL] สร้าง HX711 ไม่ได้: {e}")
    sys.exit(1)

try:
    hx.reset()
    print("[OK] HX711 reset สำเร็จ")
except Exception as e:
    print(f"[WARN] reset: {e}")


# ════════════════════════════════════════════════════════════════
# STEP 2 — อ่านค่า Raw ดิบ (ไม่มีน้ำหนัก)
# ════════════════════════════════════════════════════════════════
print("\n" + "="*50)
print("STEP 2: อ่านค่า Raw (ยังไม่ calibrate)")
print("="*50)
print("ถอดของทุกอย่างออกจาก load cell แล้วกด Enter...")
input()

print("กำลังอ่านค่า 10 ครั้ง...")
samples_no_load = []
for i in range(10):
    val = read_mean(hx, n=3)
    if val is not None:
        samples_no_load.append(val)
        print(f"  [{i+1:02d}] raw = {val:.1f}")
    else:
        print(f"  [{i+1:02d}] อ่านค่าไม่ได้")
    time.sleep(0.2)

if not samples_no_load:
    print("\n[ERROR] อ่านค่าไม่ได้เลย")
    print("  • ตรวจสอบ DT_PIN / SCK_PIN — ลองสลับกัน")
    print("  • ตรวจ power: ควรใช้ 5V")
    print("  • ตรวจ jumper wire ว่า loose ไหม")
    sys.exit(1)

zero_raw = statistics.mean(samples_no_load)
spread   = max(samples_no_load) - min(samples_no_load)
print(f"\n✓ Zero raw (เฉลี่ย) : {zero_raw:.1f}")
print(f"  Spread (max-min)  : {spread:.1f}  ", end="")
if spread < 5000:
    print("← สัญญาณนิ่งดี ✓")
elif spread < 20000:
    print("← พอใช้ได้ (noise เล็กน้อย)")
else:
    print("← noise สูง — ตรวจ power supply / shielding")


# ════════════════════════════════════════════════════════════════
# STEP 3 — Zero / Tare
# ════════════════════════════════════════════════════════════════
print("\n" + "="*50)
print("STEP 3: Zero / Tare")
print("="*50)

try:
    err = hx.zero(readings=30)
    if err:
        print(f"[WARN] zero() คืน error — ใช้ค่า manual offset แทน")
    else:
        print("[OK] Tare / Zero สำเร็จ")
except Exception as e:
    print(f"[WARN] zero(): {e} — ข้ามไป")


# ════════════════════════════════════════════════════════════════
# STEP 4 — Calibration
# ════════════════════════════════════════════════════════════════
print("\n" + "="*50)
print("STEP 4: Calibration (หา Scale Factor)")
print("="*50)

scale_factor = None
try:
    known_str = input("น้ำหนักอ้างอิง (กรัม) เช่น 100, 200, 500  [Enter=ข้าม]: ").strip()
    known_weight = float(known_str) if known_str else None
except ValueError:
    known_weight = None

if known_weight:
    input(f"\nวาง {known_weight}g บน load cell แล้วกด Enter...")
    print("กำลังอ่านค่า 10 ครั้ง...")

    cal_samples = []
    for i in range(10):
        val = read_mean(hx, n=3)
        if val is not None:
            cal_samples.append(val)
            print(f"  [{i+1:02d}] raw = {val:.1f}")
        time.sleep(0.2)

    if cal_samples:
        cal_raw = statistics.mean(cal_samples)
        scale_factor = (cal_raw - zero_raw) / known_weight
        print(f"\n✓ cal_raw      = {cal_raw:.1f}")
        print(f"✓ zero_raw     = {zero_raw:.1f}")
        print(f"✓ scale_factor = {scale_factor:.4f}")
        try:
            hx.set_scale_ratio(scale_factor)
        except:
            pass
    else:
        print("[FAIL] อ่านค่า calibration ไม่ได้")
else:
    print("[SKIP] ข้าม calibration")


# ════════════════════════════════════════════════════════════════
# STEP 5 — Live Reading
# ════════════════════════════════════════════════════════════════
print("\n" + "="*50)
print("STEP 5: Live Reading  (Ctrl+C เพื่อหยุด)")
print("="*50)
print("ลองวาง/เอาของออก ดูค่าเปลี่ยนแปลง\n")

try:
    while True:
        raw = read_mean(hx, n=3)
        if raw is None:
            print("  [ERR] อ่านค่าไม่ได้")
            time.sleep(1)
            continue

        if scale_factor:
            gram = (raw - zero_raw) / scale_factor
            print(f"  น้ำหนัก: {gram:8.2f} g   (raw: {int(raw)})")
        else:
            print(f"  Raw: {int(raw)}")
        time.sleep(0.5)

except KeyboardInterrupt:
    pass


# ════════════════════════════════════════════════════════════════
# สรุปผล
# ════════════════════════════════════════════════════════════════
print("\n" + "="*50)
print("สรุปผลการทดสอบ")
print("="*50)
print(f"  ✓ HX711 เชื่อมต่อ : ใช้งานได้")
print(f"  ✓ DT pin          : GPIO {DT_PIN}")
print(f"  ✓ SCK pin         : GPIO {SCK_PIN}")
print(f"  ✓ Zero raw        : {zero_raw:.1f}")
if scale_factor:
    print(f"  ✓ Scale factor    : {scale_factor:.4f}")
    print(f"\n── copy ค่านี้ไปใส่ใน food_detection ──────────")
    print(f"  LOADCELL_DT_PIN       = {DT_PIN}")
    print(f"  LOADCELL_SCK_PIN      = {SCK_PIN}")
    print(f"  LOADCELL_ZERO_RAW     = {zero_raw:.1f}")
    print(f"  LOADCELL_SCALE_FACTOR = {scale_factor:.4f}")
    print(f"────────────────────────────────────────────────")
else:
    print(f"\n  (ยังไม่ได้ calibrate — รันใหม่แล้วใส่น้ำหนักใน STEP 4)")

print("\nเสร็จสิ้น ✓")
