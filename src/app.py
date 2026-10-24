import ctypes
import threading
import time
import cv2
import numpy as np

from src.capture import WindowCapture
from src.detector import ExpDetector
from src.hotbar import HotbarDetector
from src.tracker import ExpTracker
from src.ui import TrackerUI


def enable_high_dpi_awareness():
    """Enables per-monitor DPI awareness on Windows so screen coordinates match real pixels."""
    try:
        # Per monitor v2 DPI awareness
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        try:
            # Fallback to per-monitor DPI awareness
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


class AppController:
    def __init__(self):
        self.capture = WindowCapture()
        self.detector = ExpDetector()
        self.tracker = ExpTracker()
        self.hotbar_detector = HotbarDetector()

        self._lock = threading.Lock()
        self._is_running = True
        self._is_paused = False

        # Per-cell alert configuration: (row, col) -> {'threshold': int, 'enabled': bool}
        self.cell_alerts = {}
        for r in range(3):
            for c in range(4):
                self.cell_alerts[(r, c)] = {
                    'threshold': 20,
                    'enabled': False
                }
        # Default: enable monitoring on (2, 3) (Pdn / orange 49) with threshold 20
        self.cell_alerts[(2, 3)] = {'threshold': 20, 'enabled': True}
        self.monitored_cell = (2, 3)
        self.previous_quantities = {}

        self.latest_state = {
            'status': 'SEARCHING',
            'details': '',
            'current_exp': 0,
            'current_pct': 0.0,
            'bar_pct': None,
            'windows': {},
            'session_duration': 0,
            'total_gained_exp': 0,
            'total_gained_pct': 0.0,
            'session_rate_hr': 0,
            'session_pct_rate_hr': 0.0,
            'eta_seconds': None,
            'level_ups': 0,
            'crop_bgr': None,
            'hotbar': {
                'found': False,
                'grid_crop_bgr': None,
                'cells': None,
                'quantities': {},
                'monitored_cell': (2, 3),
                'monitored_qty': None,
                'cell_alerts': {k: dict(v) for k, v in self.cell_alerts.items()},
                'alert_triggered_cells': [],
                'alert_triggered': False
            }
        }

        # Background worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def set_monitored_cell(self, row: int, col: int):
        with self._lock:
            self.monitored_cell = (row, col)
            self._update_alert_status()

    def set_cell_threshold(self, row: int, col: int, threshold: int):
        with self._lock:
            if (row, col) not in self.cell_alerts:
                self.cell_alerts[(row, col)] = {'threshold': 20, 'enabled': False}
            self.cell_alerts[(row, col)]['threshold'] = max(0, int(threshold))
            self._update_alert_status()

    def set_cell_alert_enabled(self, row: int, col: int, enabled: bool):
        with self._lock:
            if (row, col) not in self.cell_alerts:
                self.cell_alerts[(row, col)] = {'threshold': 20, 'enabled': False}
            self.cell_alerts[(row, col)]['enabled'] = bool(enabled)
            self._update_alert_status()

    # Backwards-compatible shortcuts for current monitored cell
    def set_min_threshold(self, threshold: int):
        r, c = self.monitored_cell
        self.set_cell_threshold(r, c, threshold)

    def set_alert_enabled(self, enabled: bool):
        r, c = self.monitored_cell
        self.set_cell_alert_enabled(r, c, enabled)

    def _update_alert_status(self):
        hotbar = self.latest_state.get('hotbar', {})
        hotbar['cell_alerts'] = {k: dict(v) for k, v in self.cell_alerts.items()}
        hotbar['monitored_cell'] = self.monitored_cell

        # If hotbar is not found / detected, do not trigger alerts
        if not hotbar.get('found', False):
            hotbar['alert_triggered'] = False
            hotbar['alert_triggered_cells'] = []
            hotbar['monitored_qty'] = None
            return

        quantities = hotbar.get('quantities', {})
        hotbar['monitored_qty'] = quantities.get(self.monitored_cell)

        alert_triggered_cells = []
        for cell_coord, cfg in self.cell_alerts.items():
            if not cfg.get('enabled', False):
                continue
            thresh = cfg.get('threshold', 20)
            qty = quantities.get(cell_coord)
            effective_qty = 0 if qty is None else qty
            if effective_qty < thresh:
                alert_triggered_cells.append({
                    'cell': cell_coord,
                    'qty': effective_qty,
                    'threshold': thresh
                })

        is_any_alert = (len(alert_triggered_cells) > 0)
        hotbar['alert_triggered_cells'] = alert_triggered_cells
        hotbar['alert_triggered'] = is_any_alert

    def toggle_pause(self):
        with self._lock:
            self._is_paused = not self._is_paused
            self.tracker.is_paused = self._is_paused
            return self._is_paused

    def reset_tracker(self):
        with self._lock:
            self.tracker.reset()
            self.detector.reset_lock()

    def get_latest_state(self):
        with self._lock:
            return dict(self.latest_state)

    def _worker_loop(self):
        """Continuously captures and analyzes MapleStory at 1 Hz."""
        while self._is_running:
            start_t = time.time()

            if self._is_paused:
                with self._lock:
                    self.latest_state['status'] = 'PAUSED'
                time.sleep(0.5)
                continue

            hwnd = self.capture.find_window()
            if not hwnd:
                with self._lock:
                    self.latest_state['status'] = 'NOT_FOUND'
                    self.latest_state['details'] = 'MapleStory not found'
                time.sleep(1.0)
                continue

            # Capture bottom ROI
            roi_bgr, client_w, client_h, _ = self.capture.capture_roi(hwnd, bottom_ratio=0.28)
            if roi_bgr is None:
                with self._lock:
                    self.latest_state['status'] = 'MINIMIZED'
                    self.latest_state['details'] = 'Window minimized'
                time.sleep(1.0)
                continue

            # Detect black frame / dark map transition screen (portal loading)
            if float(np.mean(roi_bgr)) < 25.0 or int(np.max(roi_bgr)) < 50:
                with self._lock:
                    if self.latest_state['status'] == 'LOCKED':
                        self.latest_state['details'] = 'Map transition (screen black)...'
                time.sleep(0.4)
                continue

            # Detect EXP bar and text
            res = self.detector.detect(roi_bgr, client_w, client_h)

            # Detect Hotbar (3x4 grid)
            ui_scale = res.get('scale', 1.0) if res.get('success') else 1.0
            hotbar_res = self.hotbar_detector.detect(roi_bgr, ui_scale=ui_scale)

            if res.get('success'):
                exp_val = res['exp_value']
                exp_pct = res['exp_pct']
                bar_pct = res.get('bar_pct')

                # Feed tracker
                self.tracker.add_sample(exp_val, exp_pct, bar_pct)

                # Query stats
                session_stats = self.tracker.get_session_stats()
                windows = {
                    '1m': self.tracker.get_window_gain(60),
                    '5m': self.tracker.get_window_gain(300),
                    '10m': self.tracker.get_window_gain(600),
                    '30m': self.tracker.get_window_gain(1800),
                    '1h': self.tracker.get_window_gain(3600),
                }

                scale_str = f"{res.get('scale', 1.0):.1f}x"
                with self._lock:
                    self.latest_state['status'] = 'LOCKED'
                    self.latest_state['details'] = f"{client_w}x{client_h} @ {scale_str}"
                    self.latest_state['current_exp'] = exp_val
                    self.latest_state['current_pct'] = exp_pct if exp_pct is not None else 0.0
                    self.latest_state['bar_pct'] = bar_pct
                    self.latest_state['windows'] = windows
                    self.latest_state['session_duration'] = session_stats['session_duration']
                    self.latest_state['total_gained_exp'] = session_stats['total_gained_exp']
                    self.latest_state['total_gained_pct'] = session_stats['total_gained_pct']
                    self.latest_state['session_rate_hr'] = session_stats['session_rate_hr']
                    self.latest_state['session_pct_rate_hr'] = session_stats['session_pct_rate_hr']
                    self.latest_state['eta_seconds'] = session_stats['eta_seconds']
                    self.latest_state['level_ups'] = session_stats['level_ups']
                    self.latest_state['crop_bgr'] = res.get('crop_bgr')
            else:
                with self._lock:
                    if self.latest_state['status'] != 'LOCKED':
                        self.latest_state['status'] = 'SEARCHING'
                        self.latest_state['details'] = res.get('reason', 'Locating EXP bar...')

            # Update hotbar detection and alert state
            with self._lock:
                if hotbar_res.get('success'):
                    quantities = hotbar_res['quantities']
                    for k, v in quantities.items():
                        if v is not None:
                            self.previous_quantities[k] = v

                    self.latest_state['hotbar']['found'] = True
                    self.latest_state['hotbar']['grid_crop_bgr'] = hotbar_res['grid_crop_bgr']
                    self.latest_state['hotbar']['cells'] = hotbar_res['cells']
                    self.latest_state['hotbar']['quantities'] = quantities
                    self._update_alert_status()
                else:
                    self.latest_state['hotbar']['found'] = False
                    self.latest_state['hotbar']['alert_triggered'] = False

            # 1 Hz sampling rate (sleep remaining time of the 1-second interval)
            elapsed = time.time() - start_t
            sleep_t = max(0.2, 1.0 - elapsed)
            time.sleep(sleep_t)


def main():
    enable_high_dpi_awareness()
    controller = AppController()
    ui = TrackerUI(controller)
    ui.mainloop()


if __name__ == "__main__":
    main()
