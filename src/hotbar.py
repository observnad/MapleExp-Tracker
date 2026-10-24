import base64
import cv2
import numpy as np

# Base64 encoded PNG of the bottom metallic frame border of the 3x4 quickslot hotbar (147x8 at 1.0x scale)
# Located at y=104 inside the 147x112 box. This frame border NEVER changes regardless of items placed in cells!
FRAME_BOTTOM_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAJMAAAAICAIAAAByJlrCAAACqklEQVRIDe3BQYtVdRzH4c/3f2aYmWtQ"
    "tEmzwqhF9B5a9A6iEKIgxKXQrvfSMgTbhIi0adXbkBYFEtbkJgp1kpzz+3TOuXNnzh276TLB54n6wYef"
    "Pjhsi8Xea6+e7Vr7bf/Oz7d/vP3TD0BVqUyqihk1CTOtNVaSMGmt8RSqSmVSVcyoSZhprbGShElrjadQ"
    "VSqTqmJGTcJMa42VJExaazxJValMqooZNQkzrTVWkjBprTG58NY7b1x4+5Vz56vqzq93/fs+5NsbX+fR"
    "o0cfXfzswWEDFovd8+fOdq2xIqMwkoFAGERkSQghbKQMwhoZhZmwkczJMSGE8BREJmEQUAZhJBDCijxO"
    "IAwCiBxJGImcCMhGAcJ/EcKRvvpf9u8eHDxcbBXh5vVruXfv3sefXD447JjsLXZffunFF84smMgojEQm"
    "ISLHhDAI4V8oS2GNjMIkPIEMZBSQJRmFQQibyUBWwkiOBQRCWJE5mQkBRI4kjEROBGSjgGEQNhDC6P6D"
    "g9//+POvg4eEva1Sb16/lv39/UuXr7CBzKgkRCyrSkDp+0rSda3rEjJgJAMBi1E4TU5EEuRxSUAGIitq"
    "ldU7SNe2txokIQySsKSohX1V9YJJupYBJCFAwIhABoSRMicEEUMGYK99X8p21waAFqMwSFBOk0GCgCEk"
    "rJGJzIkRkojKjW+u5tatW8CVz79gSU4RwkpaaVVZldYAy8OqJF2SRktrCQGVIw6QOZE5gSSsC2RAAEUE"
    "A0KpBVLaWra2OiAQoAUSUPrqy6qyL7qQhEmAJI1GBoAQJglLSsJAWRPC4LAvq5DW5QgkIZwQAWUihDCSp"
    "YQ1siRrEkipeO2rL3d2dvLmme2r333Pc/97SVpr29vbOzs7l95/L7u7uzz3rLn47utRee5Zs7e39w/Vo"
    "1+iF2GY3QAAAABJRU5ErkJggg=="
)

# Secondary fallback anchor: Ctrl button (31x31)
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

# Pixel-exact bitmap templates for MapleStory quantity font (9px tall)
DIGIT_TEMPLATES = {
    '1': np.array([
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0]
    ], dtype=int),
    '0': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 0, 1],
        [1, 0, 1, 1, 0, 1],
        [1, 0, 1, 1, 0, 1],
        [1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '2': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 1, 1, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 1]
    ], dtype=int),
    '3': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [0, 0, 1, 1, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
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
        [1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '6': np.array([
        [0, 0, 1, 1, 1, 0],
        [0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0]
    ], dtype=int),
    '7': np.array([
        [1, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 1, 0, 0, 0, 0]
    ], dtype=int),
    '8': np.array([
        [0, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 0],
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
        [0, 1, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 1],
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
    white_mask = ((roi[:, :, 0] > 165) & (roi[:, :, 1] > 155)).astype(int)

    # Black outline verification in 31x31 cell near bottom-left
    corner = cell_bgr[20:31, 0:22]
    black_count = ((corner[:, :, 0] < 50) & (corner[:, :, 1] < 50) & (corner[:, :, 2] < 50)).sum()
    if black_count < 20 or white_mask.sum() < 7:
        return None

    matches = []
    w_roi = white_mask.shape[1]
    for x in range(0, w_roi - 2):
        for d, tmpl in DIGIT_TEMPLATES.items():
            w = tmpl.shape[1]
            if x + w <= w_roi:
                sub = white_mask[0:9, x:x+w]
                matched = np.sum((sub == 1) & (tmpl == 1))
                missed_tmpl = np.sum((sub == 0) & (tmpl == 1))
                unexplained = np.sum((sub == 1) & (tmpl == 0))

                total_tmpl = np.sum(tmpl)
                max_unexplained = 4 if d == '1' else 14
                min_ratio = 0.85 if (d != '1' and unexplained > 5) else 0.75

                if matched / total_tmpl >= min_ratio and unexplained <= max_unexplained:
                    score = matched - 0.8 * unexplained - 1.0 * missed_tmpl
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
        # Decode bottom frame template (147x8 at 1.0x scale) - immune to item changes
        raw_frame = base64.b64decode(FRAME_BOTTOM_B64)
        np_frame = np.frombuffer(raw_frame, np.uint8)
        self.frame_tmpl = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)
        self.frame_h, self.frame_w, _ = self.frame_tmpl.shape  # 8x147

        # Decode Ctrl button template as secondary fallback (31x31 at 1.0x scale)
        raw_ctrl = base64.b64decode(CTRL_BTN_B64)
        np_ctrl = np.frombuffer(raw_ctrl, np.uint8)
        self.ctrl_tmpl = cv2.imdecode(np_ctrl, cv2.IMREAD_COLOR)
        self.ctrl_h, self.ctrl_w, _ = self.ctrl_tmpl.shape  # 31x31

        # Standard grid dimensions (at 1.0x scale)
        self.grid_w = 147
        self.grid_h = 112

        # Cell slice ranges inside 147x112 box
        self.cell_cols = [(5, 36), (40, 71), (75, 106), (110, 141)]
        self.cell_rows = [(5, 36), (39, 70), (73, 104)]

        # Lock tracking
        self.is_locked = False
        self.locked_loc = (0, 0)  # (x, y) of grid top-left relative to ROI
        self.locked_scale = 1.0
        self.consecutive_misses = 0

    def reset_lock(self):
        self.is_locked = False
        self.consecutive_misses = 0

    def detect(self, roi_bgr, ui_scale=1.0):
        """
        Locates the 3x4 hotbar grid in roi_bgr, crops each cell, and reads quantities.
        Uses the hotbar window frame bottom border as the primary anchor so that
        placing/moving items on any cell never breaks hotbar detection.
        """
        if roi_bgr is None or roi_bgr.size == 0:
            return {'success': False, 'reason': 'Empty frame'}

        roi_h, roi_w, _ = roi_bgr.shape

        best_val = -1
        best_loc = (0, 0)
        best_scale = ui_scale

        # 1. Fast verification near cached location (if already locked)
        if self.is_locked and abs(ui_scale - self.locked_scale) < 0.05:
            lx, ly = self.locked_loc
            s = self.locked_scale

            # Frame bottom expected position: x = lx, y = ly + int(104 * s)
            fy = ly + int(104 * s)
            fx = lx
            search_pad = 20
            y1 = max(0, fy - search_pad)
            y2 = min(roi_h, fy + int(self.frame_h * s) + search_pad)
            x1 = max(0, fx - search_pad)
            x2 = min(roi_w, fx + int(self.frame_w * s) + search_pad)

            if y2 > y1 + 5 and x2 > x1 + 10:
                sub_roi = roi_bgr[y1:y2, x1:x2]
                stmpl = self.frame_tmpl
                if abs(s - 1.0) > 0.05:
                    sw = max(5, int(self.frame_w * s))
                    sh = max(3, int(self.frame_h * s))
                    stmpl = cv2.resize(self.frame_tmpl, (sw, sh))

                if sub_roi.shape[0] >= stmpl.shape[0] and sub_roi.shape[1] >= stmpl.shape[1]:
                    res = cv2.matchTemplate(sub_roi, stmpl, cv2.TM_CCOEFF_NORMED)
                    min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
                    if max_v >= 0.70:
                        frame_x = x1 + max_l[0]
                        frame_y = y1 + max_l[1]
                        best_val = max_v
                        best_loc = (frame_x, frame_y - int(104 * s))
                        best_scale = s

        # 2. Full scan across ROI using bottom frame anchor
        if best_val < 0.70:
            scales_to_test = [ui_scale] if abs(ui_scale - 1.0) > 0.05 else []
            scales_to_test.extend([1.0, 1.25, 1.5, 2.0, 0.8, 0.67])
            scales_to_test = list(dict.fromkeys(round(s, 2) for s in scales_to_test if s > 0))

            for s in scales_to_test:
                sw = max(5, int(self.frame_w * s))
                sh = max(3, int(self.frame_h * s))
                if sw > roi_w or sh > roi_h:
                    continue
                stmpl = cv2.resize(self.frame_tmpl, (sw, sh)) if abs(s - 1.0) > 0.02 else self.frame_tmpl
                res = cv2.matchTemplate(roi_bgr, stmpl, cv2.TM_CCOEFF_NORMED)
                min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
                if max_v > best_val:
                    best_val = max_v
                    best_scale = s
                    fx, fy = max_l
                    best_loc = (fx, fy - int(104 * s))
                    if best_val > 0.90:
                        break

        # 3. Fallback to Ctrl button template if frame bottom wasn't matched
        if best_val < 0.65:
            for s in [ui_scale, 1.0, 1.25]:
                sw = max(5, int(self.ctrl_w * s))
                sh = max(5, int(self.ctrl_h * s))
                if sw > roi_w or sh > roi_h:
                    continue
                stmpl = cv2.resize(self.ctrl_tmpl, (sw, sh)) if abs(s - 1.0) > 0.02 else self.ctrl_tmpl
                res = cv2.matchTemplate(roi_bgr, stmpl, cv2.TM_CCOEFF_NORMED)
                min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
                if max_v > best_val:
                    best_val = max_v
                    best_scale = s
                    cx, cy = max_l
                    best_loc = (cx - int(5 * s), cy - int(73 * s))
                    if best_val > 0.85:
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

        # Slice cells and parse numbers
        cells = []
        quantities = {}
        for r_idx, (r1, r2) in enumerate(self.cell_rows):
            row_cells = []
            for c_idx, (c1, c2) in enumerate(self.cell_cols):
                cell_bgr = norm_grid[r1:r2, c1:c2].copy()
                qty = parse_cell_quantity(cell_bgr)
                quantities[(r_idx, c_idx)] = qty

                row_cells.append({
                    'row': r_idx,
                    'col': c_idx,
                    'key': KEY_NAMES[r_idx][c_idx],
                    'quantity': qty,
                    'crop_bgr': cell_bgr
                })
            cells.append(row_cells)

        return {
            'success': True,
            'grid_loc': best_loc,
            'scale': best_scale,
            'confidence': best_val,
            'grid_crop_bgr': grid_crop,
            'cells': cells,
            'quantities': quantities
        }
