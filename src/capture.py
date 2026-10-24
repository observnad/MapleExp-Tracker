import ctypes
from ctypes import wintypes
import numpy as np

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Structs for GDI BitBlt
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


class WindowCapture:
    def __init__(self, target_class="MapleStoryClass", target_title="MapleStory"):
        self.target_class = target_class
        self.target_title = target_title
        self.last_hwnd = None
        self._ensure_desktop()

    def _ensure_desktop(self):
        """Ensures the thread can access the interactive default desktop if needed."""
        try:
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x1FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

    def find_window(self):
        """Locates the MapleStory window handle."""
        self._ensure_desktop()
        
        # 1. Direct class + title lookup
        hwnd = user32.FindWindowW(self.target_class, self.target_title)
        if hwnd and user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
            self.last_hwnd = hwnd
            return hwnd

        # 2. Lookup by class only
        hwnd = user32.FindWindowW(self.target_class, None)
        if hwnd and user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
            self.last_hwnd = hwnd
            return hwnd

        # 3. Lookup by title only
        hwnd = user32.FindWindowW(None, self.target_title)
        if hwnd and user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
            self.last_hwnd = hwnd
            return hwnd

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
        if matched_hwnd:
            self.last_hwnd = matched_hwnd
            return matched_hwnd

        self.last_hwnd = None
        return None

    def get_client_geometry(self, hwnd):
        """Returns (width, height, screen_x, screen_y, is_minimized)."""
        crect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(crect))
        width = crect.right - crect.left
        height = crect.bottom - crect.top

        pt = wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))

        # Check if minimized
        is_minimized = (width <= 0 or height <= 0 or pt.x < -10000 or pt.y < -10000)
        return width, height, pt.x, pt.y, is_minimized

    def capture_roi(self, hwnd, bottom_ratio=0.28):
        """
        Captures the bottom portion of the MapleStory window.
        Returns:
            (image_bgr_np, width, height, roi_y_offset_in_client)
            or (None, 0, 0, 0) if failed/minimized.
        """
        width, height, screen_x, screen_y, is_minimized = self.get_client_geometry(hwnd)
        if is_minimized or width < 100 or height < 100:
            return None, 0, 0, 0

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
        bmi.biHeight = -roi_h  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer = ctypes.create_string_buffer(width * roi_h * 4)

        # BitBlt from screen
        SRCCOPY = 0x00CC0020
        success = gdi32.BitBlt(hdc_mem, 0, 0, width, roi_h, hdc_screen, roi_x_screen, roi_y_screen, SRCCOPY)
        if success:
            gdi32.GetDIBits(hdc_mem, hbm, 0, roi_h, buffer, ctypes.byref(bmi), 0)

        # Cleanup GDI objects
        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

        if not success:
            return None, width, height, 0

        # Convert to numpy array (BGR format for OpenCV)
        arr = np.frombuffer(buffer, dtype=np.uint8).reshape((roi_h, width, 4))
        bgr = arr[:, :, :3]
        return bgr, width, height, roi_y_offset
