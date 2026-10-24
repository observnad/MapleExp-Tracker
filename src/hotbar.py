import base64
import cv2
import numpy as np

CTRL_BTN_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAB8AAAAfCAIAAACQzIFuAAAEYUlEQVRIDa3BsYrkRgKA4b8wHDPM3kKZ"
    "Np10YvkOpcfJyBgMAsM8Qm/gSGCQnkCoEkVKquh9ASlSPHqE7kQOheTMgQLVGrOJ8SHB3jYzLBjd0py4"
    "G9iwv0/sf/jx5/an9/9+t/twx/W8/csZEF/97e9/ffn5Z2/+6KaR6/n686/+/PIL8Y9/fvPZmz+6aayz"
    "1+enR567u7k9Pz2yuru5lS9esprfvzs/PbK6u7mVL15y0Vtb17XwpNNNY529Pj89hoeM56okDw8ZqyrJ"
    "d5stq7f/+j08ZKyqJN9ttqx6a4UnnW4aqyQPDxnQtAOrwHe5aNoBCHy3SnKeCw9Z0w5A4LtVku82W1a9"
    "tcKTTjeNVZKHh6xpByDwXaBpByDwXaBpByDwXT6laQcg8N0qyXebLaveWuFJp5vGKsnDQ9a0AxD4Lv+n"
    "aQdWge827QAEvtu0AxD4btMOQOC7VZLvNltWvbXCk043jVWSh4esaQcg8N0qybkIDxnQtAMQ+C7QtAOr"
    "wHeBph2AwHerJN9ttqx6a4UnnW4aqyQPD1nTDkDguzzXtAMQ+C7QtAMQ+C6rph2AwHerJN9ttqx6a4Un"
    "nW4aqyQPD1nTDkDgu0DTDkDgu0DTDkDgu0DTDkDgu1WSA+Eha9oBCHy3SvLdZsuqt1Z40ummsUry8JAB"
    "TTuwCnyXi6YdgMB3gaYdgMB3qyQHwkPWtAMQ+G6V5LvNllVvrfCk001jnb0+Pz2Gh4znqiQPDxmfUiU5"
    "EB4yVlWS7zZbVr21wpNON40nU87v352fHnnu7ub2/PTIp9zd3ALnp0dWdze38sVLVr21wpNON40nU3Jt"
    "vbXCk043jSdTcm29tcKTTjeNJ1Nybb21wpNON40nU3JtvbXCk043jSdTcm29tcKTTjeNJ1Nybb21wpNO"
    "N40nU3JtvbXCk043jSdTcm29tcKTTjeNJ1MC8zwDUkpg/oj/kSClBOZ5BqSUXMwfgeS/pJTAPM9Syt5a"
    "4Umnm8aTKe08RzoFSmUk7HXKc7UyM0Q6BUplJMwQ6ZSLMlZRoUtlgEintTJ2noUnnW4aa2X2OhVCAMuy"
    "lMrERi3LIoQAlmURQhSpjnQqhACWZTGxSgsthOCiiNKo0OpVrB8KIcRRF721wpNON42lMpFOWZXKAJFO"
    "S2WASKelMkCkU1bqVawfilIZR0rAznOkU0AI8ZBqKWVvrfCk001jqUykUyEEsCxLqQwQ6bRUBoh0WioD"
    "RDoVQgDLsqhXsX4oTKzkRzDPc1RoIcSyLKUyjpS9tcKTTjeNtTJ7ndbKAHud1soAe53WygB7ndbKAHud"
    "1soAe52WysRGLcvCRRmrqNClMrFRy7LUyth5Fp50umk8mfJexUddAPcqPuoCuFfxURfAvYqPugDuVXzU"
    "BXCv4qMugHsVc/GQ6ldGHXUB3Kv4qIveWuFJp5vGkym5tt5a8e1333/45dduGk+m5Hp6a+u6Fvsffnz7"
    "25sPv/y63++5nrqu//zyi/8A9uRSw+9xqAYAAAAASUVORK5CYII="
)

KEY_NAMES = [
    ["1", "2", "3", "4"],
    ["Shift", "Ins", "Hm", "Pup"],
    ["Ctrl", "Del", "End", "Pdn"]
]

DIGIT_TEMPLATES = {
    '1': np.array([
        [0, 1, 0, 0],
        [1, 1, 1, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0]
    ], dtype=int),
    '0': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '2': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 0, 1],
        [0, 1, 1, 1, 0, 1],
        [0, 1, 0, 0, 1, 0],
        [0, 0, 1, 1, 0, 1],
        [0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 1]
    ], dtype=int),
    '3': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '4': np.array([
        [0, 1, 1, 0, 1, 0],
        [0, 1, 0, 1, 1, 0],
        [0, 0, 1, 0, 1, 0],
        [0, 1, 0, 0, 1, 0],
        [1, 0, 0, 0, 1, 0],
        [1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1, 0]
    ], dtype=int),
    '5': np.array([
        [1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '6': np.array([
        [0, 0, 1, 1, 1, 0],
        [0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '7': np.array([
        [1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0]
    ], dtype=int),
    '8': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '9': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int)
}


def parse_cell_quantity(cell_bgr):
    """
    Extracts the item count / quantity number from a 31x31 quickslot cell.
    Returns integer value or None if no quantity exists in the cell.
    """
    if cell_bgr is None or cell_bgr.shape[0] < 31 or cell_bgr.shape[1] < 31:
        return None

    # Number region: y: 21..30 (9 rows), x: 0..24
    roi = cell_bgr[21:30, 0:24]
    white_mask = ((roi[:, :, 0] > 170) & (roi[:, :, 1] > 160)).astype(int)

    # Black outline verification in 31x31 cell near bottom-left
    corner = cell_bgr[20:31, 0:22]
    black_count = ((corner[:, :, 0] < 50) & (corner[:, :, 1] < 50) & (corner[:, :, 2] < 50)).sum()
    if black_count < 45 or white_mask.sum() < 8:
        return None

    matches = []
    w_roi = white_mask.shape[1]
    for x in range(0, w_roi - 3):
        for d, tmpl in DIGIT_TEMPLATES.items():
            w = tmpl.shape[1]
            if x + w <= w_roi:
                sub = white_mask[0:9, x:x+w]
                matched = np.sum((sub == 1) & (tmpl == 1))
                missed_tmpl = np.sum((sub == 0) & (tmpl == 1))
                unexplained = np.sum((sub == 1) & (tmpl == 0))

                total_tmpl = np.sum(tmpl)
                if matched / total_tmpl >= 0.75 and unexplained <= 3:
                    score = matched - 1.5 * unexplained - 1.0 * missed_tmpl
                    matches.append((x, d, score, w))

    if not matches:
        return None

    # Greedy non-overlapping selection by highest score
    matches.sort(key=lambda m: m[2], reverse=True)
    selected = []
    for x, d, score, w in matches:
        overlap = False
        for sx, sd, sscore, sw in selected:
            if max(x, sx) < min(x + w, sx + sw):
                overlap = True
                break
        if not overlap:
            selected.append((x, d, score, w))

    # Sort left to right
    selected.sort(key=lambda m: m[0])
    num_str = ''.join(d for x, d, score, w in selected)
    try:
        return int(num_str) if num_str else None
    except Exception:
        return None


class HotbarDetector:
    def __init__(self):
        # Decode Ctrl button template
        raw_png = base64.b64decode(CTRL_BTN_B64)
        np_arr = np.frombuffer(raw_png, np.uint8)
        self.ctrl_tmpl = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        self.tmpl_h, self.tmpl_w, _ = self.ctrl_tmpl.shape # 31x31

        # Standard grid dimensions (at 1.0x scale)
        self.grid_w = 147
        self.grid_h = 112

        # Cell slice ranges inside 147x112 box
        self.cell_cols = [(5, 36), (40, 71), (75, 106), (110, 141)]
        self.cell_rows = [(5, 36), (39, 70), (73, 104)]

        # Lock tracking
        self.is_locked = False
        self.locked_loc = (0, 0) # (x, y) of grid top-left relative to ROI
        self.locked_scale = 1.0
        self.consecutive_misses = 0

    def reset_lock(self):
        self.is_locked = False
        self.consecutive_misses = 0

    def detect(self, roi_bgr, ui_scale=1.0):
        """
        Locates the 3x4 hotbar grid in roi_bgr, crops each cell, and reads quantities.
        Returns a dictionary with detection results.
        """
        if roi_bgr is None or roi_bgr.size == 0:
            return {'success': False, 'reason': 'Empty frame'}

        roi_h, roi_w, _ = roi_bgr.shape

        # Search scales: test near ui_scale first, fallback to multiple scales
        best_val = -1
        best_loc = (0, 0)
        best_scale = ui_scale

        if self.is_locked and abs(ui_scale - self.locked_scale) < 0.05:
            # Fast verification near cached location
            lx, ly = self.locked_loc
            ctrl_x = lx + int(5 * self.locked_scale)
            ctrl_y = ly + int(73 * self.locked_scale)
            search_pad = 25
            y1 = max(0, ctrl_y - search_pad)
            y2 = min(roi_h, ctrl_y + int(self.tmpl_h * self.locked_scale) + search_pad)
            x1 = max(0, ctrl_x - search_pad)
            x2 = min(roi_w, ctrl_x + int(self.tmpl_w * self.locked_scale) + search_pad)

            if y2 > y1 + 10 and x2 > x1 + 10:
                sub_roi = roi_bgr[y1:y2, x1:x2]
                stmpl = self.ctrl_tmpl
                if abs(self.locked_scale - 1.0) > 0.05:
                    sw = max(5, int(self.tmpl_w * self.locked_scale))
                    sh = max(5, int(self.tmpl_h * self.locked_scale))
                    stmpl = cv2.resize(self.ctrl_tmpl, (sw, sh))

                if sub_roi.shape[0] >= stmpl.shape[0] and sub_roi.shape[1] >= stmpl.shape[1]:
                    res = cv2.matchTemplate(sub_roi, stmpl, cv2.TM_CCOEFF_NORMED)
                    min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
                    if max_v >= 0.70:
                        ctrl_pt = (x1 + max_l[0], y1 + max_l[1])
                        best_val = max_v
                        best_loc = (ctrl_pt[0] - int(5 * self.locked_scale), ctrl_pt[1] - int(73 * self.locked_scale))
                        best_scale = self.locked_scale

        # Full scan if not found or not locked
        if best_val < 0.70:
            scales_to_test = [ui_scale] if abs(ui_scale - 1.0) > 0.05 else []
            scales_to_test.extend([1.0, 1.25, 1.5, 2.0, 0.8, 0.67])
            # Filter unique
            scales_to_test = list(dict.fromkeys(round(s, 2) for s in scales_to_test if s > 0))

            for s in scales_to_test:
                sw = max(5, int(self.tmpl_w * s))
                sh = max(5, int(self.tmpl_h * s))
                if sw > roi_w or sh > roi_h:
                    continue
                stmpl = cv2.resize(self.ctrl_tmpl, (sw, sh)) if abs(s - 1.0) > 0.02 else self.ctrl_tmpl
                res = cv2.matchTemplate(roi_bgr, stmpl, cv2.TM_CCOEFF_NORMED)
                min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
                if max_v > best_val:
                    best_val = max_v
                    best_scale = s
                    ctrl_x, ctrl_y = max_l
                    best_loc = (ctrl_x - int(5 * s), ctrl_y - int(73 * s))
                    if best_val > 0.90:
                        break

        if best_val < 0.65:
            self.consecutive_misses += 1
            if self.consecutive_misses > 3:
                self.is_locked = False
            return {'success': False, 'reason': f'Hotbar not found (score {best_val:.2f})'}

        self.is_locked = True
        self.locked_loc = best_loc
        self.locked_scale = best_scale
        self.consecutive_misses = 0

        grid_x, grid_y = best_loc
        scaled_w = int(self.grid_w * best_scale)
        scaled_h = int(self.grid_h * best_scale)

        # Boundary checks
        if grid_x < 0 or grid_y < 0 or grid_x + scaled_w > roi_w or grid_y + scaled_h > roi_h:
            return {'success': False, 'reason': 'Hotbar out of frame bounds'}

        grid_crop = roi_bgr[grid_y:grid_y + scaled_h, grid_x:grid_x + scaled_w]
        if abs(best_scale - 1.0) > 0.05:
            norm_grid = cv2.resize(grid_crop, (self.grid_w, self.grid_h), interpolation=cv2.INTER_AREA if best_scale > 1.0 else cv2.INTER_LINEAR)
        else:
            norm_grid = grid_crop

        # Extract 12 cells and read quantities
        cells_data = []
        quantities = {}

        for r in range(3):
            row_data = []
            y1, y2 = self.cell_rows[r]
            for c in range(4):
                x1, x2 = self.cell_cols[c]
                cell_crop = norm_grid[y1:y2, x1:x2].copy()
                qty = parse_cell_quantity(cell_crop)
                key_name = KEY_NAMES[r][c]
                row_data.append({
                    'row': r,
                    'col': c,
                    'key': key_name,
                    'quantity': qty,
                    'crop_bgr': cell_crop
                })
                quantities[(r, c)] = qty
            cells_data.append(row_data)

        return {
            'success': True,
            'grid_crop_bgr': norm_grid,
            'cells': cells_data,
            'quantities': quantities,
            'scale': best_scale,
            'pos': best_loc,
            'conf': best_val
        }
