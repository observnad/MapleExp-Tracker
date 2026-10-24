import ctypes
from ctypes import wintypes
import threading
import numpy as np

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Try importing modern Windows Graphics Capture API
try:
    from windows_capture import WindowsCapture, CaptureControl
    HAS_WGC = True
except ImportError:
    HAS_WGC = False


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD)
    ]


class WGCWorker:
    """Background worker utilizing Windows.Graphics.Capture to capture hardware/DWM frames even if occluded."""
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.latest_frame = None
        self.lock = threading.Lock()
        self.running = True
        self.ctrl = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        def on_frame(frame, ctrl: CaptureControl):
            self.ctrl = ctrl
            if not self.running:
                ctrl.stop()
                return
            with self.lock:
                self.latest_frame = frame.frame_buffer.copy()

        def on_closed():
            pass

        try:
            cap = WindowsCapture(
                cursor_capture=False,
                window_hwnd=self.hwnd
            )
            cap.frame_handler = on_frame
            cap.closed_handler = on_closed
            cap.start()
        except Exception:
            pass

    def get_frame(self):
        with self.lock:
            return self.latest_frame

    def stop(self):
        self.running = False
        if self.ctrl:
            try:
                self.ctrl.stop()
            except Exception:
                pass


class WindowCapture:
    def __init__(self, target_class="MapleStoryClass", target_title="MapleStory"):
        self.target_class = target_class
        self.target_title = target_title
        self.last_hwnd = None
        self.wgc_worker = None
        self._ensure_desktop()

    def _ensure_desktop(self):
        try:
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x1FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

    def find_window(self):
        """Locates the MapleStory window handle and manages WGC worker."""
        self._ensure_desktop()
        
        # 1. Direct class + title lookup
        hwnd = user32.FindWindowW(self.target_class, self.target_title)
        if not (hwnd and user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd)):
            # 2. Lookup by class only
            hwnd = user32.FindWindowW(self.target_class, None)
        if not (hwnd and user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd)):
            # 3. Lookup by title only
            hwnd = user32.FindWindowW(None, self.target_title)
        if not (hwnd and user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd)):
            # 4. Enumerate desktop windows
            matched_hwnd = None
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            def enum_cb(h, lp):
                nonlocal matched_hwnd
                if user32.IsWindowVisible(h):
                    length = user32.GetWindowTextLengthW(h)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(h, buf, length + 1)
                        title = buf.value.lower()
                        if "maplestory" in title and not ("tracker" in title or "chrome" in title):
                            matched_hwnd = h
                            return False
                return True

            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
            hwnd = matched_hwnd

        if hwnd != self.last_hwnd:
            self.last_hwnd = hwnd
            if self.wgc_worker:
                self.wgc_worker.stop()
                self.wgc_worker = None
            if hwnd and HAS_WGC:
                self.wgc_worker = WGCWorker(hwnd)

        return hwnd

    def get_client_geometry(self, hwnd):
        """Returns (width, height, screen_x, screen_y, is_minimized)."""
        crect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(crect))
        width = crect.right - crect.left
        height = crect.bottom - crect.top

        pt = wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))

        is_minimized = (width <= 0 or height <= 0 or pt.x < -10000 or pt.y < -10000)
        return width, height, pt.x, pt.y, is_minimized

    def capture_roi(self, hwnd, bottom_ratio=0.28):
        """
        Captures the bottom portion of the MapleStory window.
        Uses Windows.Graphics.Capture (works even when occluded by other windows),
        falling back to GDI BitBlt if WGC is unavailable.
        """
        width, height, screen_x, screen_y, is_minimized = self.get_client_geometry(hwnd)
        if is_minimized or width < 100 or height < 100:
            return None, 0, 0, 0

        # Method 1: Windows.Graphics.Capture (Works through overlapping windows!)
        if self.wgc_worker:
            wgc_frame = self.wgc_worker.get_frame()
            if wgc_frame is not None and wgc_frame.shape[0] > 100 and wgc_frame.shape[1] > 100:
                fh, fw, _ = wgc_frame.shape
                roi_h = max(30, int(fh * bottom_ratio))
                roi_crop = wgc_frame[fh - roi_h:fh, :, :3]  # Drop alpha channel
                roi_y_offset = fh - roi_h
                return roi_crop, fw, fh, roi_y_offset

        # Method 2: Fallback to GDI Screen BitBlt
        roi_h = max(30, int(height * bottom_ratio))
        roi_y_screen = screen_y + (height - roi_h)
        roi_x_screen = screen_x
        roi_y_offset = height - roi_h

        hdc_screen = user32.GetDC(0)
        if not hdc_screen:
            return None, 0, 0, 0

        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, width, roi_h)
        gdi32.SelectObject(hdc_mem, hbm)

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -roi_h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer = ctypes.create_string_buffer(width * roi_h * 4)
        SRCCOPY = 0x00CC0020
        success = gdi32.BitBlt(hdc_mem, 0, 0, width, roi_h, hdc_screen, roi_x_screen, roi_y_screen, SRCCOPY)
        if success:
            gdi32.GetDIBits(hdc_mem, hbm, 0, roi_h, buffer, ctypes.byref(bmi), 0)

        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

        if not success:
            return None, width, height, 0

        arr = np.frombuffer(buffer, dtype=np.uint8).reshape((roi_h, width, 4))
        bgr = arr[:, :, :3]
        return bgr, width, height, roi_y_offset
