import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
from src.app import AppController

print("=== Starting Live MapleStory EXP & Hotbar Integration Test ===")
ctrl = AppController()
ctrl.set_monitored_cell(2, 3) # Monitored cell = oranges (2, 3)
ctrl.set_cell_alert_enabled(2, 3, True)

print("Waiting 3.5 seconds for background worker to sample MapleStory...")
time.sleep(3.5)

state = ctrl.get_latest_state()
print("State Status:", state["status"])
print("State Details:", state["details"])
print("Current EXP:", state["current_exp"])
print("Current %:", state["current_pct"])
print("Bar %:", state["bar_pct"])
print("Session Stats - Gained:", state["total_gained_exp"], "Duration:", state["session_duration"])
print("Windows:", list(state["windows"].keys()))

hb = state.get("hotbar", {})
print("\n--- Hotbar Detection ---")
print("Hotbar Found:", hb.get("found"))
print("Monitored Cell (2, 3) Qty:", hb.get("monitored_qty"))
print("Quantities:", hb.get("quantities"))
print("Alert Triggered:", hb.get("alert_triggered"))

assert hb.get("found") is True, "Expected Hotbar to be detected"
qty_23 = hb.get("monitored_qty")
assert qty_23 is not None and qty_23 > 0, f"Expected positive quantity in cell (2, 3), got {qty_23}"

# 1. Test setting safe threshold (< qty_23) -> alert should be False
ctrl.set_cell_threshold(2, 3, qty_23 - 5)
time.sleep(1.2)
st_safe = ctrl.get_latest_state()
print(f"Safe threshold test ({qty_23 - 5}): alert_triggered = {st_safe['hotbar']['alert_triggered']}")
assert st_safe["hotbar"]["alert_triggered"] is False

# 2. Test setting high threshold (> qty_23) -> alert should be True
ctrl.set_cell_threshold(2, 3, qty_23 + 10)
time.sleep(1.2)
st_alert = ctrl.get_latest_state()
print(f"High threshold test ({qty_23 + 10}): alert_triggered = {st_alert['hotbar']['alert_triggered']}")
assert st_alert["hotbar"]["alert_triggered"] is True
assert len(st_alert["hotbar"]["alert_triggered_cells"]) >= 1

# 3. Test resetting threshold back to safe value
ctrl.set_cell_threshold(2, 3, 20)
time.sleep(1.2)
st_reset = ctrl.get_latest_state()
print("Reset threshold test (20): alert_triggered =", st_reset["hotbar"]["alert_triggered"])
assert st_reset["hotbar"]["alert_triggered"] is False

print("\n>>> LIVE MAPLESTORY EXP & HOTBAR ALERT INTEGRATION TEST PASSED 100%! <<<")
