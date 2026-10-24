import time
from src.app import AppController

ctrl = AppController()
print("Waiting 2.5 seconds for background worker to sample...")
time.sleep(2.5)

state = ctrl.get_latest_state()
print("State Status:", state["status"])
print("State Details:", state["details"])
print("Current EXP:", state["current_exp"])
print("Current %:", state["current_pct"])
print("Bar %:", state["bar_pct"])
print("Session Stats - Gained:", state["total_gained_exp"], "Duration:", state["session_duration"])
print("Windows:", list(state["windows"].keys()))

assert state["status"] == "LOCKED", f"Expected LOCKED, got {state['status']}"
assert state["current_exp"] == 10869, f"Expected 10869, got {state['current_exp']}"
assert state["current_pct"] == 37.51, f"Expected 37.51, got {state['current_pct']}"
print("\n>>> LIVE MAPLESTORY INTEGRATION TEST PASSED 100%! <<<")
