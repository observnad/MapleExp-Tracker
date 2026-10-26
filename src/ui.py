import os
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import time
import numpy as np

KEY_NAMES = [
    ["1", "2", "3", "4"],
    ["Shift", "Ins", "Hm", "Pup"],
    ["Ctrl", "Del", "End", "Pdn"]
]


class TrackerUI(ctk.CTk):
    def __init__(self, app_controller):
        super().__init__()
        self.controller = app_controller

        # Window settings
        self.title("MapleEXP Tracker & Hotbar Alert")
        self.geometry("490x840")
        self.minsize(450, 600)

        # Set window icon if available
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__) + '/..'))
        icon_path = os.path.join(base_dir, 'icon.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Configure theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        # Theme Colors
        self.COLOR_BG_NORMAL = "#141517"
        self.COLOR_BG_ALERT = "#381212"
        self.COLOR_CARD_NORMAL = "#1e1f22"
        self.COLOR_CARD_ALERT = "#4d1919"
        self.COLOR_STATUS_NORMAL = "#2b2d31"
        self.COLOR_STATUS_ALERT = "#661d1d"

        self.is_currently_red_alert = False

        # Always on top
        self.always_on_top = True
        self.attributes("-topmost", True)

        # UI state for hotbar
        self.selected_cell = (2, 3)  # default: Pdn (orange 49)
        self.grid_buttons = {}
        self.cell_cached_images = {}
        self.cell_cached_hashes = {}
        self.cell_cached_borders = {}
        self.all_card_frames = []

        # UI state for rolling EXP graphs
        self.selected_graph_window = "5m"
        self.hover_slice_idx = None
        self.sparkline_canvases = {}
        self.window_labels = {}
        self.window_row_frames = {}
        self.window_sec_lookup = {"1m": 60, "5m": 300, "10m": 600, "30m": 1800, "1h": 3600}

        # Build UI layout
        self._build_header()
        self._build_alert_banner()

        # Tab View separating EXP Tracker and Hotbar Alert Settings
        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        self.TAB_EXP = "📈 EXP Tracker"
        self.TAB_HOTBAR = "🎒 Hotbar Settings"
        self.tab_exp = self.tabview.add(self.TAB_EXP)
        self.tab_hotbar = self.tabview.add(self.TAB_HOTBAR)

        # Scrollable content frames so neither tab overflows regardless of resolution
        self.exp_content_frame = ctk.CTkScrollableFrame(self.tab_exp, fg_color="transparent")
        self.exp_content_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.hotbar_content_frame = ctk.CTkScrollableFrame(self.tab_hotbar, fg_color="transparent")
        self.hotbar_content_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Build cards on their respective tabs
        self._build_current_exp_card(self.exp_content_frame)
        self._build_rolling_windows_card(self.exp_content_frame)
        self._build_session_card(self.exp_content_frame)
        self._build_preview_card(self.exp_content_frame)

        self._build_hotbar_card(self.hotbar_content_frame)

        # Bottom fixed controls
        self._build_controls()

        # Update loop interval (100ms for smooth UI updates)
        self.after(100, self._on_ui_tick)

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=16, pady=(10, 4))

        # Title & Version
        title_label = ctk.CTkLabel(
            self.header_frame,
            text="🍁 MapleEXP Tracker",
            font=ctk.CTkFont(size=17, weight="bold")
        )
        title_label.pack(side="left")

        # Topmost Controls
        controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls_frame.pack(side="right")

        self.pin_btn = ctk.CTkButton(
            controls_frame,
            text="📌 On Top",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#1f538d",
            command=self._toggle_always_on_top
        )
        self.pin_btn.pack(side="left", padx=4)

        # Status badge
        self.status_frame = ctk.CTkFrame(self, fg_color=self.COLOR_STATUS_NORMAL, corner_radius=6, height=26)
        self.status_frame.pack(fill="x", padx=16, pady=3)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="● Searching for MapleStory window...",
            font=ctk.CTkFont(size=11),
            text_color="#e5a93c"
        )
        self.status_label.pack(pady=3, padx=10)

    def _build_alert_banner(self):
        """Top prominent alert banner displayed when item quantity drops below threshold."""
        self.alert_banner = ctk.CTkFrame(self, fg_color="#8b1c1c", corner_radius=6)
        self.alert_banner_label = ctk.CTkLabel(
            self.alert_banner,
            text="🚨 LOW ITEM WARNING: Quantity dropped below threshold!",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff"
        )
        self.alert_banner_label.pack(pady=4, padx=10)
        # Not packed initially; shown dynamically when alert triggers

    def _build_hotbar_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD_NORMAL, corner_radius=10)
        card.pack(fill="x", padx=4, pady=4)
        self.hotbar_card = card
        self.all_card_frames.append(card)

        # Header row
        hdr_row = ctk.CTkFrame(card, fg_color="transparent")
        hdr_row.pack(fill="x", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            hdr_row,
            text="🎒 HOTBAR ITEM ALERT (3x4 GRID)",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(side="left")

        self.hotbar_status_pill = ctk.CTkLabel(
            hdr_row,
            text="● HOTBAR DETECTED",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#43b581"
        )
        self.hotbar_status_pill.pack(side="right")

        body_frame = ctk.CTkFrame(card, fg_color="transparent")
        body_frame.pack(fill="x", padx=12, pady=(0, 10))

        # Simulated 3x4 Grid on Left
        self.grid_container = ctk.CTkFrame(body_frame, fg_color="#18191c", corner_radius=8)
        self.grid_container.pack(side="left", padx=(0, 12), pady=2)

        for r in range(3):
            for c in range(4):
                key_text = KEY_NAMES[r][c]
                is_selected = (r == self.selected_cell[0] and c == self.selected_cell[1])

                btn = ctk.CTkButton(
                    self.grid_container,
                    text=key_text,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    width=42,
                    height=42,
                    corner_radius=4,
                    border_width=2 if is_selected else 1,
                    border_color="#f1c40f" if is_selected else "#383a40",
                    fg_color="#2b2d31",
                    hover_color="#3b3e45",
                    command=lambda row=r, col=c: self._on_cell_clicked(row, col)
                )
                btn.grid(row=r, column=c, padx=3, pady=3)
                self.grid_buttons[(r, c)] = btn

        # Alert Configuration Panel on Right
        ctrl_frame = ctk.CTkFrame(body_frame, fg_color="transparent")
        ctrl_frame.pack(side="left", fill="both", expand=True)

        self.lbl_selected_target = ctk.CTkLabel(
            ctrl_frame,
            text="🎯 Key: Pdn [Row 2, Col 3]",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.lbl_selected_target.pack(anchor="w", pady=(0, 1))

        # Current quantity row
        qty_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        qty_row.pack(fill="x", pady=1)

        ctk.CTkLabel(
            qty_row,
            text="Current Qty: ",
            font=ctk.CTkFont(size=11),
            text_color="#8a8d95"
        ).pack(side="left")

        self.lbl_current_qty = ctk.CTkLabel(
            qty_row,
            text="--",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f2c94c"
        )
        self.lbl_current_qty.pack(side="left")

        # Threshold configuration label
        ctk.CTkLabel(
            ctrl_frame,
            text="Alert when drops below:",
            font=ctk.CTkFont(size=10),
            text_color="#8a8d95"
        ).pack(anchor="w", pady=(3, 1))

        # Threshold input stepper
        thresh_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        thresh_row.pack(fill="x", pady=2)

        self.btn_dec = ctk.CTkButton(
            thresh_row,
            text="-",
            width=26,
            height=26,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#34495e",
            hover_color="#2c3e50",
            command=lambda: self._adjust_threshold(-5)
        )
        self.btn_dec.pack(side="left", padx=(0, 3))

        self.entry_threshold = ctk.CTkEntry(
            thresh_row,
            width=50,
            height=26,
            font=ctk.CTkFont(size=12, weight="bold"),
            justify="center"
        )
        self.entry_threshold.pack(side="left", padx=2)
        self.entry_threshold.insert(0, "20")
        self.entry_threshold.bind("<Return>", self._on_threshold_entry_changed)
        self.entry_threshold.bind("<FocusOut>", self._on_threshold_entry_changed)

        self.btn_inc = ctk.CTkButton(
            thresh_row,
            text="+",
            width=26,
            height=26,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#34495e",
            hover_color="#2c3e50",
            command=lambda: self._adjust_threshold(+5)
        )
        self.btn_inc.pack(side="left", padx=3)

        # Preset threshold quick buttons
        preset_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        preset_row.pack(fill="x", pady=2)
        for p in [10, 20, 50, 100]:
            btn_p = ctk.CTkButton(
                preset_row,
                text=str(p),
                width=32,
                height=20,
                font=ctk.CTkFont(size=10),
                fg_color="#2b2d31",
                hover_color="#3b3e45",
                command=lambda val=p: self._set_preset_threshold(val)
            )
            btn_p.pack(side="left", padx=1)

        # Toggle Switch
        self.switch_alert = ctk.CTkSwitch(
            ctrl_frame,
            text="Red Alert Active",
            font=ctk.CTkFont(size=11),
            height=20,
            command=self._on_alert_toggle
        )
        self.switch_alert.pack(anchor="w", pady=(4, 0))
        self.switch_alert.select()

        # Active Alerts Summary panel
        summary_frame = ctk.CTkFrame(card, fg_color="#18191c", corner_radius=6)
        summary_frame.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(
            summary_frame,
            text="ACTIVE ALERTS OVERVIEW:",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        self.lbl_active_alerts_summary = ctk.CTkLabel(
            summary_frame,
            text="● Pdn: Alert when quantity < 20",
            font=ctk.CTkFont(size=11),
            text_color="#dbdee1",
            justify="left"
        )
        self.lbl_active_alerts_summary.pack(anchor="w", padx=10, pady=(0, 6))

    def _build_current_exp_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD_NORMAL, corner_radius=10)
        card.pack(fill="x", padx=4, pady=4)
        self.exp_card = card
        self.all_card_frames.append(card)

        # Subtitle
        ctk.CTkLabel(
            card,
            text="CURRENT EXPERIENCE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(anchor="w", padx=14, pady=(8, 0))

        # Big EXP numbers row
        exp_row = ctk.CTkFrame(card, fg_color="transparent")
        exp_row.pack(fill="x", padx=14, pady=(2, 2))

        self.exp_val_label = ctk.CTkLabel(
            exp_row,
            text="0 EXP",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ffffff"
        )
        self.exp_val_label.pack(side="left")

        self.exp_pct_label = ctk.CTkLabel(
            exp_row,
            text="[ 0.00% ]",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#a8e61d"  # Maple lime-green
        )
        self.exp_pct_label.pack(side="left", padx=10)

        # Progress bar
        self.exp_progress = ctk.CTkProgressBar(
            card,
            height=12,
            corner_radius=4,
            progress_color="#c8e616",  # Maple yellow-lime
            fg_color="#383a40"
        )
        self.exp_progress.pack(fill="x", padx=14, pady=4)
        self.exp_progress.set(0.0)

        # Sub-stats (ETA & Level-ups)
        info_row = ctk.CTkFrame(card, fg_color="transparent")
        info_row.pack(fill="x", padx=14, pady=(0, 8))

        self.eta_label = ctk.CTkLabel(
            info_row,
            text="⏳ Level Up ETA: --",
            font=ctk.CTkFont(size=11),
            text_color="#dbdee1"
        )
        self.eta_label.pack(side="left")

        self.lvlup_label = ctk.CTkLabel(
            info_row,
            text="Level-ups: 0",
            font=ctk.CTkFont(size=11),
            text_color="#949ba4"
        )
        self.lvlup_label.pack(side="right")

    def _build_rolling_windows_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD_NORMAL, corner_radius=10)
        card.pack(fill="x", padx=4, pady=4)
        self.windows_card = card
        self.all_card_frames.append(card)

        # Title row
        title_row = ctk.CTkFrame(card, fg_color="transparent")
        title_row.pack(fill="x", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            title_row,
            text="ROLLING EXPERIENCE GAINED",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(side="left")

        self.lbl_graph_badge = ctk.CTkLabel(
            title_row,
            text="📊 128 SLICES / WINDOW",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#58a6ff"
        )
        self.lbl_graph_badge.pack(side="right")

        # Table Grid Headers
        header_grid = ctk.CTkFrame(card, fg_color="#2b2d31", corner_radius=4)
        header_grid.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(header_grid, text="Window", font=ctk.CTkFont(size=11, weight="bold"), width=48, anchor="w").grid(row=0, column=0, padx=4, pady=3)
        ctk.CTkLabel(header_grid, text="Trend (128 slices)", font=ctk.CTkFont(size=11, weight="bold"), width=88, anchor="center").grid(row=0, column=1, padx=4, pady=3)
        ctk.CTkLabel(header_grid, text="EXP Gained", font=ctk.CTkFont(size=11, weight="bold"), width=78, anchor="e").grid(row=0, column=2, padx=4, pady=3)
        ctk.CTkLabel(header_grid, text="% Gained", font=ctk.CTkFont(size=11, weight="bold"), width=60, anchor="e").grid(row=0, column=3, padx=4, pady=3)
        ctk.CTkLabel(header_grid, text="Rate / Hour", font=ctk.CTkFont(size=11, weight="bold"), width=80, anchor="e").grid(row=0, column=4, padx=4, pady=3)

        self.window_keys = [
            ("1m", 60, "Past 1 min"),
            ("5m", 300, "Past 5 min"),
            ("10m", 600, "Past 10 min"),
            ("30m", 1800, "Past 30 min"),
            ("1h", 3600, "Past 1 hour"),
        ]

        self.window_labels = {}
        self.sparkline_canvases = {}
        self.window_row_frames = {}

        for idx, (key, sec, label_text) in enumerate(self.window_keys):
            row_frame = ctk.CTkFrame(card, fg_color="transparent" if idx % 2 == 0 else "#232428", corner_radius=3)
            row_frame.pack(fill="x", padx=12, pady=1)
            self.window_row_frames[key] = row_frame

            lbl_name = ctk.CTkLabel(row_frame, text=key, font=ctk.CTkFont(size=11, weight="bold"), width=48, anchor="w", text_color="#58a6ff", cursor="hand2")
            lbl_name.grid(row=0, column=0, padx=4, pady=2)

            # 128-slice mini sparkline canvas
            spark_canvas = tk.Canvas(
                row_frame,
                width=88,
                height=20,
                bg="#18191c",
                highlightthickness=1,
                highlightbackground="#2b2d31",
                cursor="hand2"
            )
            spark_canvas.grid(row=0, column=1, padx=4, pady=2)
            self.sparkline_canvases[key] = spark_canvas

            lbl_exp = ctk.CTkLabel(row_frame, text="+0", font=ctk.CTkFont(size=11), width=78, anchor="e", text_color="#ffffff", cursor="hand2")
            lbl_exp.grid(row=0, column=2, padx=4, pady=2)

            lbl_pct = ctk.CTkLabel(row_frame, text="+0.00%", font=ctk.CTkFont(size=11), width=60, anchor="e", text_color="#a8e61d", cursor="hand2")
            lbl_pct.grid(row=0, column=3, padx=4, pady=2)

            lbl_rate = ctk.CTkLabel(row_frame, text="0 /hr", font=ctk.CTkFont(size=11), width=80, anchor="e", text_color="#e0e0e0", cursor="hand2")
            lbl_rate.grid(row=0, column=4, padx=4, pady=2)

            # Clicking any element in the row switches the detailed graph window
            for widget in (row_frame, lbl_name, spark_canvas, lbl_exp, lbl_pct, lbl_rate):
                widget.bind("<Button-1>", lambda event, k=key: self._select_graph_window(k))

            self.window_labels[key] = {
                'exp': lbl_exp,
                'pct': lbl_pct,
                'rate': lbl_rate,
                'seconds': sec
            }

        # Separator for Detailed Graph Section
        sep = ctk.CTkFrame(card, fg_color="#2b2d31", height=1)
        sep.pack(fill="x", padx=14, pady=(8, 6))

        # Window selection segmented button row
        seg_row = ctk.CTkFrame(card, fg_color="transparent")
        seg_row.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            seg_row,
            text="Detailed Graph Window:",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(side="left", padx=(2, 8))

        self.graph_window_seg = ctk.CTkSegmentedButton(
            seg_row,
            values=["1m", "5m", "10m", "30m", "1h"],
            font=ctk.CTkFont(size=10, weight="bold"),
            height=22,
            command=self._on_graph_seg_changed
        )
        self.graph_window_seg.pack(side="right")
        self.graph_window_seg.set(self.selected_graph_window)

        # Detailed Graph Header & Slice Info
        det_hdr = ctk.CTkFrame(card, fg_color="transparent")
        det_hdr.pack(fill="x", padx=14, pady=(2, 2))

        self.lbl_graph_title = ctk.CTkLabel(
            det_hdr,
            text="📈 EXP Per 1/128 Slice (5m Window)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#58a6ff"
        )
        self.lbl_graph_title.pack(side="left")

        self.lbl_graph_slice_info = ctk.CTkLabel(
            det_hdr,
            text="128 slices · 2.34s each",
            font=ctk.CTkFont(size=10),
            text_color="#8a8d95"
        )
        self.lbl_graph_slice_info.pack(side="right")

        # Stats summary row (Peak, Average, Window Total)
        stats_strip = ctk.CTkFrame(card, fg_color="#18191c", corner_radius=6)
        stats_strip.pack(fill="x", padx=12, pady=2)

        self.lbl_graph_peak = ctk.CTkLabel(
            stats_strip,
            text="Peak: +0 EXP",
            font=ctk.CTkFont(size=10),
            text_color="#f2c94c"
        )
        self.lbl_graph_peak.pack(side="left", padx=8, pady=3)

        self.lbl_graph_avg = ctk.CTkLabel(
            stats_strip,
            text="Avg: 0.0 EXP/slice",
            font=ctk.CTkFont(size=10),
            text_color="#dbdee1"
        )
        self.lbl_graph_avg.pack(side="left", padx=8, pady=3)

        self.lbl_graph_total = ctk.CTkLabel(
            stats_strip,
            text="Total: +0 EXP",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#a8e61d"
        )
        self.lbl_graph_total.pack(side="right", padx=8, pady=3)

        # Detailed Canvas (Interactive 128 Slices Line Graph)
        self.graph_canvas = tk.Canvas(
            card,
            bg="#18191c",
            height=125,
            highlightthickness=1,
            highlightbackground="#2b2d31",
            cursor="crosshair"
        )
        self.graph_canvas.pack(fill="x", padx=12, pady=(4, 2))

        self.graph_canvas.bind("<Configure>", self._on_graph_canvas_configure)
        self.graph_canvas.bind("<Motion>", self._on_graph_canvas_hover)
        self.graph_canvas.bind("<Leave>", self._on_graph_canvas_leave)

        # Hover tooltip/info label below canvas
        self.lbl_graph_hover_info = ctk.CTkLabel(
            card,
            text="Hover over the graph to inspect individual 1/128 slices",
            font=ctk.CTkFont(size=10),
            text_color="#8a8d95"
        )
        self.lbl_graph_hover_info.pack(padx=14, pady=(2, 6))

    def _select_graph_window(self, win_key):
        """Switches the active detailed graph window."""
        self.selected_graph_window = win_key
        self.graph_window_seg.set(win_key)
        self._update_graph_header_labels()
        self._draw_detailed_graph()

    def _on_graph_seg_changed(self, value):
        self.selected_graph_window = value
        self._update_graph_header_labels()
        self._draw_detailed_graph()

    def _update_graph_header_labels(self):
        win_key = self.selected_graph_window
        win_sec = self.window_sec_lookup.get(win_key, 300)
        slice_sec = win_sec / 128.0
        self.lbl_graph_title.configure(text=f"📈 EXP Per 1/128 Slice ({win_key} Window)")
        self.lbl_graph_slice_info.configure(text=f"128 slices · {slice_sec:.2f}s each")

    def _format_graph_time(self, seconds):
        seconds = int(round(seconds))
        if seconds >= 3600:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h}h {m}m" if m > 0 else f"{h}h"
        elif seconds >= 60:
            m = seconds // 60
            s = seconds % 60
            return f"{m}m {s}s" if s > 0 else f"{m}m"
        else:
            return f"{seconds}s"

    def _on_graph_canvas_configure(self, event=None):
        self._draw_detailed_graph()

    def _on_graph_canvas_hover(self, event):
        canvas = self.graph_canvas
        w = canvas.winfo_width()
        pad_l, pad_r = 40, 15
        pw = max(10, w - pad_l - pad_r)

        rel_x = event.x - pad_l
        if 0 <= rel_x <= pw:
            slice_idx = int(round((rel_x / pw) * 127))
            slice_idx = max(0, min(127, slice_idx))
            self.hover_slice_idx = slice_idx

            data = self.controller.get_latest_state()
            windows = data.get('windows', {})
            win_key = self.selected_graph_window
            wdata = windows.get(win_key, {})
            slices = wdata.get('slices', [])
            win_sec = self.window_sec_lookup.get(win_key, 300)
            slice_sec = win_sec / 128.0

            time_ago = (127 - slice_idx) * slice_sec
            val = slices[slice_idx] if slice_idx < len(slices) else 0.0

            time_str = "Now" if slice_idx == 127 else f"-{self._format_graph_time(time_ago)} ago"
            self.lbl_graph_hover_info.configure(
                text=f"🎯 Slice #{slice_idx + 1}/128 ({time_str}): +{val:,.1f} EXP",
                text_color="#f1c40f"
            )
            self._draw_detailed_graph()
        else:
            self._on_graph_canvas_leave()

    def _on_graph_canvas_leave(self, event=None):
        if self.hover_slice_idx is not None:
            self.hover_slice_idx = None
            self.lbl_graph_hover_info.configure(
                text="Hover over the graph to inspect individual 1/128 slices",
                text_color="#8a8d95"
            )
            self._draw_detailed_graph()

    def _draw_sparkline(self, canvas, slices):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10:
            w = 88
        if h < 10:
            h = 20

        pad_x = 2
        pad_y = 2
        pw = w - 2 * pad_x
        ph = h - 2 * pad_y

        n = len(slices)
        if n < 2:
            return

        max_val = max(slices) if slices else 0.0
        if max_val <= 0:
            y = h - pad_y
            canvas.create_line(pad_x, y, pad_x + pw, y, fill="#2a2d33", width=1)
            return

        coords = []
        for i, val in enumerate(slices):
            x = pad_x + (i / (n - 1)) * pw
            y = h - pad_y - (val / max_val) * ph
            coords.extend([x, y])

        poly = [pad_x, h - pad_y] + coords + [pad_x + pw, h - pad_y]
        canvas.create_polygon(*poly, fill="#162c42", outline="")
        canvas.create_line(*coords, fill="#58a6ff", width=1)

    def _draw_detailed_graph(self):
        canvas = self.graph_canvas
        canvas.delete("all")

        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 50:
            w = 420
        if h < 50:
            h = 125

        pad_l, pad_r, pad_t, pad_b = 40, 15, 14, 22
        pw = max(10, w - pad_l - pad_r)
        ph = max(10, h - pad_t - pad_b)

        data = self.controller.get_latest_state()
        windows = data.get("windows", {})
        win_key = self.selected_graph_window
        wdata = windows.get(win_key, {})
        slices = wdata.get("slices", [0.0] * 128)
        win_sec = self.window_sec_lookup.get(win_key, 300)

        max_val = max(slices) if slices else 0.0
        n = len(slices)

        # Background horizontal grid lines
        grid_steps = [(0.0, "0"), (0.5, f"+{int(round(max_val * 0.5)):,}"), (1.0, f"+{int(round(max_val)):,}")] if max_val > 0 else [(0.0, "0"), (0.5, ""), (1.0, "")]
        for ratio, lbl in grid_steps:
            y = pad_t + ph * (1.0 - ratio)
            canvas.create_line(pad_l, y, pad_l + pw, y, fill="#25282e", dash=(2, 4))
            if lbl:
                canvas.create_text(pad_l - 4, y, text=lbl, fill="#72767d", anchor="e", font=("Segoe UI", 8))

        # Vertical time marker grid lines
        t_marks = [
            (0.0, f"-{win_key}"),
            (0.25, ""),
            (0.5, f"-{self._format_graph_time(win_sec // 2)}"),
            (0.75, ""),
            (1.0, "Now")
        ]
        for ratio, t_lbl in t_marks:
            x = pad_l + ratio * pw
            canvas.create_line(x, pad_t, x, pad_t + ph, fill="#23262b", dash=(2, 4))
            if t_lbl:
                canvas.create_text(x, pad_t + ph + 9, text=t_lbl, fill="#8a8d95", anchor="center", font=("Segoe UI", 8))

        if max_val <= 0 or n < 2:
            y_base = pad_t + ph
            canvas.create_line(pad_l, y_base, pad_l + pw, y_base, fill="#2a2d33", width=1)
            canvas.create_text(pad_l + pw / 2, pad_t + ph / 2, text="No EXP gained in this window yet", fill="#4f545c", font=("Segoe UI", 9, "italic"))
            return

        coords = []
        for i, val in enumerate(slices):
            x = pad_l + (i / (n - 1)) * pw
            y = pad_t + ph * (1.0 - (val / max_val))
            coords.extend([x, y])

        # Shaded gradient area under line
        poly = [pad_l, pad_t + ph] + coords + [pad_l + pw, pad_t + ph]
        canvas.create_polygon(*poly, fill="#162a3f", outline="")

        # Line graph
        canvas.create_line(*coords, fill="#58a6ff", width=2)

        # Hover crosshair & dot
        if self.hover_slice_idx is not None and 0 <= self.hover_slice_idx < n:
            k = self.hover_slice_idx
            hx = pad_l + (k / (n - 1)) * pw
            h_val = slices[k]
            hy = pad_t + ph * (1.0 - (h_val / max_val))

            canvas.create_line(hx, pad_t, hx, pad_t + ph, fill="#f1c40f", dash=(3, 3), width=1)
            canvas.create_oval(hx - 4, hy - 4, hx + 4, hy + 4, fill="#f1c40f", outline="#ffffff", width=1)

    def _update_hotbar_summary_label(self, hotbar_data):
        cell_alerts = hotbar_data.get('cell_alerts', {})
        active = []
        for (r, c), cfg in sorted(cell_alerts.items()):
            if cfg.get('enabled', False):
                kname = KEY_NAMES[r][c]
                th = cfg.get('threshold', 20)
                active.append(f"Key {kname} (< {th})")

        if active:
            self.lbl_active_alerts_summary.configure(
                text="Active Alerts: " + " · ".join(active),
                text_color="#dbdee1"
            )
        else:
            self.lbl_active_alerts_summary.configure(
                text="No active alerts. Select a key above and enable 'Red Alert Active'.",
                text_color="#72767d"
            )

    def _build_session_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD_NORMAL, corner_radius=10)
        card.pack(fill="x", padx=4, pady=4)
        self.session_card = card
        self.all_card_frames.append(card)

        ctk.CTkLabel(
            card,
            text="SESSION OVERVIEW",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(anchor="w", padx=14, pady=(6, 2))

        stats_grid = ctk.CTkFrame(card, fg_color="transparent")
        stats_grid.pack(fill="x", padx=14, pady=(0, 6))

        self.session_time_label = ctk.CTkLabel(
            stats_grid,
            text="⏱ Duration: 00:00:00",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.session_time_label.grid(row=0, column=0, sticky="w", pady=1)

        self.session_gain_label = ctk.CTkLabel(
            stats_grid,
            text="🌟 Total Gain: +0 (+0.00%)",
            font=ctk.CTkFont(size=11),
            anchor="w",
            text_color="#ffffff"
        )
        self.session_gain_label.grid(row=1, column=0, sticky="w", pady=1)

        self.session_rate_label = ctk.CTkLabel(
            stats_grid,
            text="⚡ Avg Rate: 0 EXP/hr",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="e",
            text_color="#f2c94c"
        )
        self.session_rate_label.grid(row=0, column=1, sticky="e", padx=(30, 0), pady=1)

        self.session_pct_rate_label = ctk.CTkLabel(
            stats_grid,
            text="(+0.00% / hr)",
            font=ctk.CTkFont(size=10),
            anchor="e",
            text_color="#a8e61d"
        )
        self.session_pct_rate_label.grid(row=1, column=1, sticky="e", padx=(30, 0), pady=1)

    def _build_preview_card(self, parent):
        self.preview_frame = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD_NORMAL, corner_radius=10)
        self.all_card_frames.append(self.preview_frame)

        top_row = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(6, 2))

        ctk.CTkLabel(
            top_row,
            text="DETECTION PREVIEW (LIVE)",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(side="left")

        self.preview_img_label = ctk.CTkLabel(self.preview_frame, text="No preview available")
        self.preview_img_label.pack(padx=14, pady=(2, 6))

        self.preview_shown = False

    def _build_controls(self):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(4, 10))

        self.reset_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Reset Session",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#c0392b",
            hover_color="#962d22",
            height=30,
            command=self._on_reset_clicked
        )
        self.reset_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.pause_btn = ctk.CTkButton(
            btn_frame,
            text="⏸ Pause",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#34495e",
            hover_color="#2c3e50",
            height=30,
            command=self._toggle_pause
        )
        self.pause_btn.pack(side="left", expand=True, fill="x", padx=4)

        self.preview_toggle_btn = ctk.CTkButton(
            btn_frame,
            text="👁 Preview",
            font=ctk.CTkFont(size=12),
            fg_color="#2b2d31",
            hover_color="#3b3e45",
            height=30,
            width=80,
            command=self._toggle_preview
        )
        self.preview_toggle_btn.pack(side="left", padx=(4, 0))

    def _set_theme_color(self, is_alert):
        """Switches the app background and cards between normal dark and warning red."""
        if is_alert == self.is_currently_red_alert:
            return
        self.is_currently_red_alert = is_alert

        bg = self.COLOR_BG_ALERT if is_alert else self.COLOR_BG_NORMAL
        card_bg = self.COLOR_CARD_ALERT if is_alert else self.COLOR_CARD_NORMAL
        status_bg = self.COLOR_STATUS_ALERT if is_alert else self.COLOR_STATUS_NORMAL

        self.configure(fg_color=bg)
        self.status_frame.configure(fg_color=status_bg)

        for card in self.all_card_frames:
            try:
                card.configure(fg_color=card_bg)
            except Exception:
                pass

        if is_alert:
            # Show alert banner under status frame
            self.alert_banner.pack(fill="x", padx=16, pady=(0, 4), after=self.status_frame)
            self.hotbar_status_pill.configure(
                text="⚠️ LOW QUANTITY ALERT!",
                text_color="#ff7675"
            )
            try:
                self.tabview._segmented_button._buttons_dict[self.TAB_HOTBAR].configure(text="🚨 Hotbar Alert!")
            except Exception:
                pass
        else:
            self.alert_banner.pack_forget()
            self.hotbar_status_pill.configure(
                text="● HOTBAR DETECTED",
                text_color="#43b581"
            )
            try:
                self.tabview._segmented_button._buttons_dict[self.TAB_HOTBAR].configure(text=self.TAB_HOTBAR)
            except Exception:
                pass

    def _on_cell_clicked(self, row, col):
        """Handles selecting one of the 3x4 grid cells."""
        self.selected_cell = (row, col)
        self.controller.set_monitored_cell(row, col)

        # Retrieve this cell's individual alert settings
        data = self.controller.get_latest_state()
        hotbar_data = data.get('hotbar', {})
        cell_alerts = hotbar_data.get('cell_alerts', {})
        cfg = cell_alerts.get((row, col), {'threshold': 20, 'enabled': False})
        triggered_coords = {t['cell'] for t in hotbar_data.get('alert_triggered_cells', [])}

        # Update button borders
        for (r, c), btn in self.grid_buttons.items():
            if (r, c) in triggered_coords:
                target_border = (2, "#e74c3c")
            elif (r, c) == self.selected_cell:
                target_border = (2, "#f1c40f")
            elif cell_alerts.get((r, c), {}).get('enabled', False):
                target_border = (2, "#3498db")
            else:
                target_border = (1, "#383a40")

            if self.cell_cached_borders.get((r, c)) != target_border:
                btn.configure(border_width=target_border[0], border_color=target_border[1])
                self.cell_cached_borders[(r, c)] = target_border

        key_name = KEY_NAMES[row][col]
        self.lbl_selected_target.configure(text=f"🎯 Key: {key_name} [Row {row}, Col {col}]")

        # Update threshold entry and switch for this cell
        self.entry_threshold.delete(0, "end")
        self.entry_threshold.insert(0, str(cfg.get('threshold', 20)))

        if cfg.get('enabled', False):
            self.switch_alert.select()
        else:
            self.switch_alert.deselect()

        # Update current quantity label
        quantities = hotbar_data.get('quantities', {})
        qty = quantities.get((row, col))
        self.lbl_current_qty.configure(text=str(qty) if qty is not None else "--")

    def _adjust_threshold(self, delta):
        try:
            curr = int(self.entry_threshold.get().strip())
        except ValueError:
            curr = 20
        new_val = max(0, curr + delta)
        self.entry_threshold.delete(0, "end")
        self.entry_threshold.insert(0, str(new_val))
        r, c = self.selected_cell
        self.controller.set_cell_threshold(r, c, new_val)

    def _set_preset_threshold(self, val):
        self.entry_threshold.delete(0, "end")
        self.entry_threshold.insert(0, str(val))
        r, c = self.selected_cell
        self.controller.set_cell_threshold(r, c, val)

    def _on_threshold_entry_changed(self, event=None):
        try:
            val = int(self.entry_threshold.get().strip())
            r, c = self.selected_cell
            self.controller.set_cell_threshold(r, c, val)
        except ValueError:
            pass

    def _on_alert_toggle(self):
        enabled = (self.switch_alert.get() == 1)
        r, c = self.selected_cell
        self.controller.set_cell_alert_enabled(r, c, enabled)

    def _toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.attributes("-topmost", self.always_on_top)
        self.pin_btn.configure(
            fg_color="#1f538d" if self.always_on_top else "#383a40",
            text="📌 On Top" if self.always_on_top else "📌 Off"
        )

    def _toggle_pause(self):
        is_paused = self.controller.toggle_pause()
        self.pause_btn.configure(
            text="▶ Resume" if is_paused else "⏸ Pause",
            fg_color="#27ae60" if is_paused else "#34495e"
        )

    def _toggle_preview(self):
        self.preview_shown = not self.preview_shown
        if self.preview_shown:
            self.preview_frame.pack(fill="x", padx=4, pady=4)
            self.preview_toggle_btn.configure(fg_color="#1f538d")
        else:
            self.preview_frame.pack_forget()
            self.preview_toggle_btn.configure(fg_color="#2b2d31")

    def _on_reset_clicked(self):
        self.controller.reset_tracker()

    def _format_time(self, seconds):
        if seconds is None or seconds <= 0:
            return "--"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"

    def _format_duration(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _create_crisp_cell_image(self, crop_bgr, target_size=(38, 38)):
        """
        Transforms a low-res or high-res game cell crop into a razor-sharp,
        supersampled CTkImage that preserves pixel art proportions without
        jagged aliasing or high-DPI scaling blur.
        """
        if crop_bgr is None or crop_bgr.size == 0:
            return None

        h, w = crop_bgr.shape[:2]
        tw, th = target_size
        hi_w, hi_h = tw * 4, th * 4  # 4x supersampled resolution (152x152)

        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        pil_raw = Image.fromarray(rgb)

        if w >= hi_w and h >= hi_h:
            hi_res = pil_raw.resize((hi_w, hi_h), Image.Resampling.LANCZOS)
        else:
            # Upscale by integer factor with nearest-neighbor first so pixels remain square,
            # then downsample to the 4x canvas using Lanczos. This eliminates non-uniform
            # pixel doubling (jitter) while giving clean, anti-aliased subpixel edges.
            scale_factor = max(4, int(np.ceil(hi_w / max(1, min(w, h)))) + 1)
            nn_large = pil_raw.resize((w * scale_factor, h * scale_factor), Image.Resampling.NEAREST)
            hi_res = nn_large.resize((hi_w, hi_h), Image.Resampling.LANCZOS)

        return ctk.CTkImage(light_image=hi_res, dark_image=hi_res, size=(tw, th))

    def _on_ui_tick(self):
        """Pulls latest state from controller and updates UI widgets."""
        data = self.controller.get_latest_state()

        # Update status badge
        status = data.get('status', 'NOT_FOUND')
        details = data.get('details', '')
        hotbar_data = data.get('hotbar', {})
        is_alert = hotbar_data.get('alert_triggered', False)
        triggered_cells = hotbar_data.get('alert_triggered_cells', [])
        triggered_coords = {t['cell'] for t in triggered_cells}
        cell_alerts = hotbar_data.get('cell_alerts', {})

        # Apply red theme if alert is triggered
        self._set_theme_color(is_alert)

        if is_alert:
            # Format message for all triggered items
            triggered_msgs = []
            for t in triggered_cells:
                r, c = t['cell']
                k = KEY_NAMES[r][c]
                q = t['qty']
                th = t['threshold']
                triggered_msgs.append(f"{k} ({q} < {th})")

            summary_str = ", ".join(triggered_msgs)
            self.alert_banner_label.configure(
                text=f"🚨 LOW ITEM WARNING: {summary_str}!"
            )
            self.status_label.configure(
                text=f"🚨 ALERT: Low Item Quantity: {summary_str}!",
                text_color="#ff7675"
            )
        elif status == 'LOCKED':
            self.status_label.configure(
                text=f"● Locked: MapleStory ({details})",
                text_color="#43b581"
            )
        elif status == 'PAUSED':
            self.status_label.configure(
                text="● Tracking Paused",
                text_color="#8a8d95"
            )
        elif status == 'MINIMIZED':
            self.status_label.configure(
                text="● MapleStory is Minimized",
                text_color="#e5a93c"
            )
        else:
            self.status_label.configure(
                text="● Searching for MapleStory Window...",
                text_color="#e5a93c"
            )

        # Update EXP statistics
        current_exp = data.get('current_exp', 0)
        current_pct = data.get('current_pct', 0.0)
        bar_pct = data.get('bar_pct')

        self.exp_val_label.configure(text=f"{current_exp:,} EXP")
        self.exp_pct_label.configure(text=f"[ {current_pct:.2f}% ]")

        display_pct = current_pct if current_pct is not None else (bar_pct if bar_pct is not None else 0.0)
        self.exp_progress.set(min(1.0, max(0.0, display_pct / 100.0)))

        eta_sec = data.get('eta_seconds')
        self.eta_label.configure(text=f"⏳ Level Up ETA: {self._format_time(eta_sec)}")
        level_ups = data.get('level_ups', 0)
        anomalies = data.get('anomalies_corrected', 0)
        if anomalies > 0:
            self.lvlup_label.configure(text=f"Level-ups: {level_ups} (🛡️ {anomalies} filtered)")
        else:
            self.lvlup_label.configure(text=f"Level-ups: {level_ups}")

        # Update rolling windows
        windows = data.get('windows', {})
        for key, info in self.window_labels.items():
            wdata = windows.get(key, {})
            g_exp = wdata.get('gained_exp', 0)
            g_pct = wdata.get('gained_pct', 0.0)
            r_hr = wdata.get('exp_rate_hr', 0)
            slices = wdata.get('slices', [])

            sign = "+" if g_exp >= 0 else ""
            info['exp'].configure(text=f"{sign}{g_exp:,}")
            info['pct'].configure(text=f"{sign}{g_pct:.2f}%")
            info['rate'].configure(text=f"{r_hr:,} /hr")

            # Draw sparkline on this row
            spark_canvas = self.sparkline_canvases.get(key)
            if spark_canvas:
                self._draw_sparkline(spark_canvas, slices)

        # Update detailed rolling graph metrics and render
        sel_wdata = windows.get(self.selected_graph_window, {})
        sel_tot_exp = sel_wdata.get('gained_exp', 0)
        sel_max_slice = sel_wdata.get('max_slice', 0.0)
        sel_avg_slice = sel_wdata.get('avg_slice', 0.0)

        sign = "+" if sel_tot_exp >= 0 else ""
        self.lbl_graph_total.configure(text=f"Total: {sign}{sel_tot_exp:,} EXP")
        self.lbl_graph_peak.configure(text=f"Peak: +{sel_max_slice:,.1f} EXP")
        self.lbl_graph_avg.configure(text=f"Avg: {sel_avg_slice:,.1f} EXP/slice")

        if self.hover_slice_idx is None:
            self._draw_detailed_graph()

        # Update active alerts summary on hotbar tab
        self._update_hotbar_summary_label(hotbar_data)

        # Update session overview
        duration = data.get('session_duration', 0)
        tot_exp = data.get('total_gained_exp', 0)
        tot_pct = data.get('total_gained_pct', 0.0)
        sess_rate = data.get('session_rate_hr', 0)
        sess_pct_rate = data.get('session_pct_rate_hr', 0.0)

        self.session_time_label.configure(text=f"⏱ Duration: {self._format_duration(duration)}")
        sign = "+" if tot_exp >= 0 else ""
        self.session_gain_label.configure(text=f"🌟 Total Gain: {sign}{tot_exp:,} ({sign}{tot_pct:.2f}%)")
        self.session_rate_label.configure(text=f"⚡ Avg Rate: {sess_rate:,} EXP/hr")
        self.session_pct_rate_label.configure(text=f"({sign}{sess_pct_rate:.2f}% / hr)")

        # Update Simulated Hotbar 3x4 Grid
        if hotbar_data.get('found') and hotbar_data.get('cells'):
            cells = hotbar_data['cells']
            quantities = hotbar_data.get('quantities', {})

            # Update selected item quantity label
            mon_qty = quantities.get(self.selected_cell)
            self.lbl_current_qty.configure(text=str(mon_qty) if mon_qty is not None else "--")

            # Update each cell button in the 3x4 grid
            for r in range(3):
                for c in range(4):
                    btn = self.grid_buttons.get((r, c))
                    if not btn:
                        continue
                    cell_info = cells[r][c]
                    crop_bgr = cell_info.get('crop_bgr')
                    if crop_bgr is not None and crop_bgr.size > 0:
                        crop_hash = hash(crop_bgr.tobytes())
                        if self.cell_cached_hashes.get((r, c)) != crop_hash:
                            try:
                                ctk_img = self._create_crisp_cell_image(crop_bgr, target_size=(38, 38))
                                if ctk_img is not None:
                                    btn.configure(image=ctk_img, text="")
                                    self.cell_cached_images[(r, c)] = ctk_img
                                    self.cell_cached_hashes[(r, c)] = crop_hash
                            except Exception:
                                pass

                    # Highlight border
                    if (r, c) in triggered_coords:
                        target_border = (2, "#e74c3c")
                    elif (r, c) == self.selected_cell:
                        target_border = (2, "#f1c40f")
                    elif cell_alerts.get((r, c), {}).get('enabled', False):
                        target_border = (2, "#3498db")
                    else:
                        target_border = (1, "#383a40")

                    if self.cell_cached_borders.get((r, c)) != target_border:
                        btn.configure(border_width=target_border[0], border_color=target_border[1])
                        self.cell_cached_borders[(r, c)] = target_border

        # Update live preview image if enabled
        if self.preview_shown and 'crop_bgr' in data and data['crop_bgr'] is not None:
            try:
                crop = data['crop_bgr']
                disp_w = min(400, crop.shape[1] * 2)
                disp_h = max(20, crop.shape[0] * 2)
                preview_hi = cv2.resize(crop, (disp_w * 2, disp_h * 2), interpolation=cv2.INTER_NEAREST)
                rgb = cv2.cvtColor(preview_hi, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(disp_w, disp_h))
                self.preview_img_label.configure(image=ctk_img, text="")
            except Exception:
                pass

        # Schedule next tick
        self.after(100, self._on_ui_tick)
