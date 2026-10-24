import time
from src.app import AppController

ctrl = AppController()
print("Waiting 3.0 seconds for background worker to sample MapleStory...")
time.sleep(3.0)

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

assert hb.get("found") == True, "Expected Hotbar to be detected"
assert hb.get("monitored_qty") == 49, f"Expected 49 items in cell (2, 3), got {hb.get('monitored_qty')}"

# Test setting threshold to 50 (> 49)
ctrl.set_min_threshold(50)
state_alert = ctrl.get_latest_state()
assert state_alert["hotbar"]["alert_triggered"] == True, "Expected alert_triggered True when threshold=50"

# Test resetting threshold to 20 (< 49)
ctrl.set_min_threshold(20)
state_norm = ctrl.get_latest_state()
assert state_norm["hotbar"]["alert_triggered"] == False, "Expected alert_triggered False when threshold=20"

print("\n>>> LIVE MAPLESTORY EXP & HOTBAR ALERT INTEGRATION TEST PASSED 100%! <<<")
