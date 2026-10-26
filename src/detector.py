import base64
import cv2
import numpy as np
import re

# Base64 encoded PNG for the iconic MapleStory "EXP." logo
EXP_LOGO_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAB0AAAANCAIAAADaJ/LDAAADJklEQVQ4EXXB/0vcdRzA8edrn6YSLM1z"
    "IaaS067VkMM7XcNzmmOn2xoVdJ8Fc7U2p97IioW8/wGFg88vUQuGhPSTP8j785twWUEspn0ZfAiJENOd"
    "ztPE8NMHF7Vi3d6ZTLj9sMdDBq8MUUDAAAKGQgIGEDBsEzA8IIIxbBMwPCC9qUEEjFnNrfibm2AAAUMh"
    "ef5QY1HR3uytxT/ubAF1B+qXs1kwhm1SXFRcVV39RGkpIhgjiLzx5kVB1tdX95fta2lp4RE+Hftsb1Hx"
    "0dYX6+vrgfHx8Z6eHnYFQZDJZO7dl0i02RgQ5JUzZ4GFuZ/fPndWKcXDHMdRSgEDAwOTk5O5XM6yLN/3"
    "U6mU1poC+Xw+kUjkraKy8hAg3a+dAZZ+mes9f04pBTiOw66pqSmtdSgU8n1/bGxMKQXYtg1orQHHcYIg"
    "GBkZsSzLdd0rQ+pQUwvGyPHTryNmeWG+78JbSilARMor9gPlFU/JHulsax0dHWWX53ldJ04ee6lDaw3Y"
    "tv319W++nPo8Fot5ntd14mT0SDsY6Tz1qhhu31ro7z2vlAI8z2NHovtk0+H4jzenv/piKhaLsSMSidx/"
    "rOTggVqtNeA4ThAE6XQacF33/Q+GDjY2AdLRfRpYyS6mLl1QSlFARNq7Xl5amB9M9SmlAN/3GxsbK6pq"
    "n6ur0VpTIJ/PJxKJrbv39pWWGZC2xCkwq0vZy30XlVKAbdvsmP7+ZmV1zcbtbC6XsyyLHY7jXL02eqQ5"
    "qrUGXNfNZrNBEGQymd/v/PnMs2EMiEhrZ7eBtZXsO/2XlFKAiJQ+Wc6OkpLHP/n4w2QyCXieF4vF8vl8"
    "NBoNh8Naa8C27Rvf/bCxlgMqn66pC78g/E8OdyQEs7ay/G6qTykFeJ7HLtd10+k04Lru8PDw7Ows4Lru"
    "xMSE1hqwbRvQWgMi0tJ+XEQAaT56DGQ9t/ze5X6lFI8QiUR+/W3z2tWPkskkYNu21hqwbRvQWgMiEmvr"
    "3CNiQKLxDpB/7v5l/ft3OBzmYQ0NDYuLi77v/zQ3X1FZtbWxFo/HAd/3Q6EQMDMzA8TjceD69Le19WEM"
    "2/4D1tJM3NscvLoAAAAASUVORK5CYII="
)

# Pixel-exact bitmap templates for characters (7px height standard)
CHAR_PATTERNS = {
    '0': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    '1': ['.#', '##', '.#', '.#', '.#', '.#', '.#'],
    '2': ['.###.', '#...#', '....#', '..##.', '.#...', '#....', '#####'],
    '3': ['.###.', '#...#', '....#', '..##.', '....#', '#...#', '.###.'],
    '4': ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
    '5': ['#####', '#....', '#....', '.###.', '....#', '#...#', '.###.'],
    '6': ['.###.', '#...#', '#....', '####.', '#...#', '#...#', '.###.'],
    '7': ['#####', '....#', '....#', '....#', '...#.', '..#..', '..#..'],
    '8': ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'],
    '9': ['.###.', '#...#', '#...#', '.####', '....#', '#...#', '.###.'],
    ',': ['.#', '#.'],
    '.': ['#'],
    '[': ['##', '#.', '#.', '#.', '#.', '#.', '##'],
    ']': ['##', '.#', '.#', '.#', '.#', '.#', '##'],
    '%': ['.#....#', '#.#..#.', '.#..#..', '...#...', '..#..#.', '.#..#.#', '#....#.']
}


class ExpDetector:
    def __init__(self):
        # Decode embedded template
        raw_png = base64.b64decode(EXP_LOGO_B64)
        np_arr = np.frombuffer(raw_png, np.uint8)
        self.exp_tmpl = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        self.tmpl_h, self.tmpl_w, _ = self.exp_tmpl.shape

        # Build boolean template arrays
        self.char_tmpls = {}
        for char, pat in CHAR_PATTERNS.items():
            self.char_tmpls[char] = np.array([[c == '#' for c in row] for row in pat], dtype=bool)

        # Calibration state
        self.is_locked = False
        self.locked_scale = 1.0
        self.locked_loc = (0, 0)  # (x, y) relative to ROI
        self.locked_client_size = (0, 0)
        self.consecutive_misses = 0

    def reset_lock(self):
        self.is_locked = False
        self.consecutive_misses = 0

    def calibrate(self, roi_bgr):
        """Scans the ROI across multiple scales to locate the EXP. anchor."""
        best_val = -1
        best_scale = 1.0
        best_loc = (0, 0)

        roi_h, roi_w, _ = roi_bgr.shape
        # Test scales from 0.6x to 2.5x
        scales = np.linspace(0.6, 2.5, 39)
        for s in scales:
            sw = max(5, int(self.tmpl_w * s))
            sh = max(3, int(self.tmpl_h * s))
            if sw > roi_w or sh > roi_h:
                continue
            stmpl = cv2.resize(self.exp_tmpl, (sw, sh), interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR)
            res = cv2.matchTemplate(roi_bgr, stmpl, cv2.TM_CCOEFF_NORMED)
            min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
            if max_v > best_val:
                best_val = max_v
                best_scale = s
                best_loc = max_l

        if best_val >= 0.75:
            self.is_locked = True
            self.locked_scale = best_scale
            self.locked_loc = best_loc
            self.consecutive_misses = 0
            return True, best_loc, best_scale, best_val

        self.is_locked = False
        return False, (0, 0), 1.0, best_val

    def detect(self, roi_bgr, client_w, client_h):
        """
        Processes a frame ROI and extracts the EXP value, percentage, and bar fill.
        Returns a dict with extraction results.
        """
        if roi_bgr is None or roi_bgr.size == 0:
            return {'success': False, 'reason': 'Empty frame'}

        # Detect black frame / dark map transition screen:
        # MapleStory clears the frame or fades to black when entering portals.
        # Preserve lock position without counting as a lost track miss.
        roi_mean = float(np.mean(roi_bgr))
        roi_max = int(np.max(roi_bgr))
        roi_std = float(np.std(roi_bgr))
        if roi_mean < 30.0 or roi_max < 65 or roi_std < 12.0:
            return {'success': False, 'reason': 'Screen is black (map transition / loading)'}

        roi_h, roi_w, _ = roi_bgr.shape

        # Re-calibrate if window size changed
        if (client_w, client_h) != self.locked_client_size or not self.is_locked:
            self.locked_client_size = (client_w, client_h)
            found, loc, scale, conf = self.calibrate(roi_bgr)
            if not found:
                return {'success': False, 'reason': f'EXP bar not found (score {conf:.2f})'}
        else:
            # Fast-track: verify cached position with small search window (+- 20px)
            lx, ly = self.locked_loc
            s = self.locked_scale
            sw = max(5, int(self.tmpl_w * s))
            sh = max(3, int(self.tmpl_h * s))

            search_pad = 25
            x1 = max(0, lx - search_pad)
            y1 = max(0, ly - search_pad)
            x2 = min(roi_w, lx + sw + search_pad)
            y2 = min(roi_h, ly + sh + search_pad)

            sub_roi = roi_bgr[y1:y2, x1:x2]
            stmpl = cv2.resize(self.exp_tmpl, (sw, sh), interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR)
            
            if sub_roi.shape[0] >= sh and sub_roi.shape[1] >= sw:
                res = cv2.matchTemplate(sub_roi, stmpl, cv2.TM_CCOEFF_NORMED)
                min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
                if max_v >= 0.70:
                    self.locked_loc = (x1 + max_l[0], y1 + max_l[1])
                    self.consecutive_misses = 0
                else:
                    self.consecutive_misses += 1
            else:
                self.consecutive_misses += 1

            if self.consecutive_misses > 2:
                # Lost track, re-calibrate
                found, loc, scale, conf = self.calibrate(roi_bgr)
                if not found:
                    return {'success': False, 'reason': 'Lost track of EXP bar'}
            elif self.consecutive_misses > 0:
                # Logo match score was below threshold; do NOT run OCR on stale/dim coordinates
                return {'success': False, 'reason': 'EXP logo match below threshold'}

        exp_x, exp_y = self.locked_loc
        s = self.locked_scale

        # Crop the text line immediately following the EXP logo
        text_x = exp_x + int(self.tmpl_w * s)
        text_w = int(125 * s)
        text_h = int(14 * s)

        # Boundary checks
        if text_x + text_w > roi_w or exp_y + text_h > roi_h or exp_y < 0 or text_x < 0:
            return {'success': False, 'reason': 'Crop out of bounds'}

        text_crop = roi_bgr[exp_y:exp_y + text_h, text_x:text_x + text_w]

        # Verify text crop is sufficiently illuminated and contrasted (reject fade-out / fade-in frames)
        if float(np.mean(text_crop)) < 25.0 or int(np.max(text_crop)) < 150 or float(np.std(text_crop)) < 12.0:
            return {'success': False, 'reason': 'EXP text crop too dim or low contrast (transition)'}

        # Normalize text crop to 1.0x scale
        if abs(s - 1.0) > 0.05:
            norm_w = max(10, int(round(text_w / s)))
            norm_h = max(5, int(round(text_h / s)))
            norm_crop = cv2.resize(text_crop, (norm_w, norm_h), interpolation=cv2.INTER_AREA if s > 1.0 else cv2.INTER_LINEAR)
        else:
            norm_crop = text_crop

        # Binarize text (white & lime-green text is bright: gray > 125)
        gray = cv2.cvtColor(norm_crop, cv2.COLOR_BGR2GRAY)
        bin_img = (gray > 125).astype(np.uint8)

        # Segment characters by vertical projection (columns)
        has_pixel = np.any(bin_img > 0, axis=0)
        segments = []
        in_char = False
        start_x = 0
        for i, val in enumerate(has_pixel):
            if val and not in_char:
                in_char = True
                start_x = i
            elif not val and in_char:
                in_char = False
                segments.append((start_x, i))
        if in_char:
            segments.append((start_x, len(has_pixel)))

        def match_char(char_img):
            has_row = np.any(char_img > 0, axis=1)
            if not np.any(has_row):
                return ''
            r_start, r_end = np.where(has_row)[0][[0, -1]]
            cropped = (char_img[r_start:r_end + 1, :] > 0)
            ch, cw = cropped.shape
            best_c = '?'
            best_diff = 9999
            for c, tmpl in self.char_tmpls.items():
                th, tw = tmpl.shape
                if abs(ch - th) <= 1 and abs(cw - tw) <= 1:
                    max_h = max(ch, th)
                    max_w = max(cw, tw)
                    cp = np.zeros((max_h, max_w), dtype=bool)
                    tp = np.zeros((max_h, max_w), dtype=bool)
                    cp[:ch, :cw] = cropped
                    tp[:th, :tw] = tmpl
                    diff = np.sum(cp != tp)
                    if diff < best_diff:
                        best_diff = diff
                        best_c = c
            # Strict tolerance: legitimate MapleStory characters match with diff <= 3
            if best_diff > 3:
                return '?'
            return best_c

        recognized = []
        for s_x, e_x in segments:
            ch = match_char(bin_img[:, s_x:e_x])
            if ch == '?':
                # Unknown character or noise artifact detected
                return {'success': False, 'reason': 'Unrecognized character or noise artifact in EXP text'}
            recognized.append(ch)
            if ch == ']':
                break

        raw_str = ''.join(recognized)

        # Parse number and percentage
        # Standard format: 10,869[37.51%] or 10869[37.51%]
        exp_val = None
        exp_pct = None
        # Require opening bracket to prevent digit fusion during fading transitions
        m = re.search(r'([\d,]+)\s*\[\s*([\d\.]+)\s*\%?\s*\]?', raw_str)
        if not m:
            # Fallback only if percentage symbol is explicitly present
            m = re.search(r'([\d,]+)\s*\[?\s*([\d\.]+)\s*\%', raw_str)

        if m:
            try:
                parsed_val = int(m.group(1).replace(',', ''))
                parsed_pct = float(m.group(2))
                # Validate realistic percentage range
                if 0.0 <= parsed_pct <= 100.0 and parsed_val >= 0:
                    exp_val = parsed_val
                    exp_pct = parsed_pct
            except ValueError:
                pass

        # Measure yellow bar fill directly underneath
        bar_y = exp_y + int(14 * s)
        bar_h = int(12 * s)
        bar_w = int(140 * s)
        bar_crop = roi_bgr[bar_y:min(roi_h, bar_y + bar_h), exp_x:min(roi_w, exp_x + bar_w)]

        bar_pct = None
        if bar_crop.shape[0] >= 3 and bar_crop.shape[1] >= 20:
            mid_row = bar_crop[bar_crop.shape[0] // 2, :]
            yellow = (mid_row[:, 2] > 150) & (mid_row[:, 1] > 180) & (mid_row[:, 0] < 80)
            gray_px = (np.abs(mid_row[:, 2].astype(int) - mid_row[:, 1].astype(int)) < 20) & (mid_row[:, 0] > 130) & (mid_row[:, 0] < 230)
            y_count = np.sum(yellow)
            g_count = np.sum(gray_px)
            if y_count + g_count >= int(15 * s):
                bar_pct = round(float(y_count) / (y_count + g_count) * 100.0, 2)

        # Final verification: valid EXP value and bar presence cross-check
        bar_present = (bar_pct is not None)
        valid = (exp_val is not None) and bar_present
        if valid and exp_pct is not None:
            # If both OCR pct and graphical bar pct are detected, they must be consistent
            if abs(exp_pct - bar_pct) > 20.0:
                valid = False
        return {
            'success': valid,
            'exp_value': exp_val,
            'exp_pct': exp_pct,
            'bar_pct': bar_pct,
            'raw_text': raw_str,
            'scale': round(s, 2),
            'pos': (exp_x, exp_y),
            'crop_bgr': text_crop
        }
