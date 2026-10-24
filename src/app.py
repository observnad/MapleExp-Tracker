import ctypes
import threading
import time
import cv2

from src.capture import WindowCapture
from src.detector import ExpDetector
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

        self._lock = threading.Lock()
        self._is_running = True
        self._is_paused = False

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
            'crop_bgr': None
        }

        # Background worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

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

            # Detect EXP bar and text
            res = self.detector.detect(roi_bgr, client_w, client_h)

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
