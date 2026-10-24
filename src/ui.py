import os
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import time


class TrackerUI(ctk.CTk):
    def __init__(self, app_controller):
        super().__init__()
        self.controller = app_controller

        # Window settings
        self.title("MapleEXP Tracker")
        self.geometry("460x650")
        self.minsize(420, 520)

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

        # Always on top
        self.always_on_top = True
        self.attributes("-topmost", True)

        # Build UI layout
        self._build_header()
        self._build_current_exp_card()
        self._build_rolling_windows_card()
        self._build_session_card()
        self._build_preview_card()
        self._build_controls()

        # Update loop interval (100ms for smooth UI updates)
        self.after(100, self._on_ui_tick)

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(12, 6))

        # Title & Version
        title_label = ctk.CTkLabel(
            header_frame,
            text="🍁 MapleEXP Tracker",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(side="left")

        # Topmost & Opacity Controls
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
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
        self.status_frame = ctk.CTkFrame(self, fg_color="#2b2d31", corner_radius=6, height=26)
        self.status_frame.pack(fill="x", padx=16, pady=4)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="● Searching for MapleStory window...",
            font=ctk.CTkFont(size=11),
            text_color="#e5a93c"
        )
        self.status_label.pack(pady=3, padx=10)

    def _build_current_exp_card(self):
        card = ctk.CTkFrame(self, fg_color="#1e1f22", corner_radius=10)
        card.pack(fill="x", padx=16, pady=6)

        # Subtitle
        ctk.CTkLabel(
            card,
            text="CURRENT EXPERIENCE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(anchor="w", padx=14, pady=(10, 0))

        # Big EXP numbers row
        exp_row = ctk.CTkFrame(card, fg_color="transparent")
        exp_row.pack(fill="x", padx=14, pady=(2, 4))

        self.exp_val_label = ctk.CTkLabel(
            exp_row,
            text="0 EXP",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffffff"
        )
        self.exp_val_label.pack(side="left")

        self.exp_pct_label = ctk.CTkLabel(
            exp_row,
            text="[ 0.00% ]",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#a8e61d"  # Maple lime-green
        )
        self.exp_pct_label.pack(side="left", padx=10)

        # Progress bar
        self.exp_progress = ctk.CTkProgressBar(
            card,
            height=14,
            corner_radius=4,
            progress_color="#c8e616",  # Maple yellow-lime
            fg_color="#383a40"
        )
        self.exp_progress.pack(fill="x", padx=14, pady=6)
        self.exp_progress.set(0.0)

        # Sub-stats (ETA & Level-ups)
        info_row = ctk.CTkFrame(card, fg_color="transparent")
        info_row.pack(fill="x", padx=14, pady=(0, 10))

        self.eta_label = ctk.CTkLabel(
            info_row,
            text="⏳ Level Up ETA: --",
            font=ctk.CTkFont(size=12),
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

    def _build_rolling_windows_card(self):
        card = ctk.CTkFrame(self, fg_color="#1e1f22", corner_radius=10)
        card.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            card,
            text="ROLLING EXPERIENCE GAINED",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        # Table Grid Headers
        header_grid = ctk.CTkFrame(card, fg_color="#2b2d31", corner_radius=4)
        header_grid.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(header_grid, text="Window", font=ctk.CTkFont(size=11, weight="bold"), width=70, anchor="w").grid(row=0, column=0, padx=8, pady=4)
        ctk.CTkLabel(header_grid, text="EXP Gained", font=ctk.CTkFont(size=11, weight="bold"), width=110, anchor="e").grid(row=0, column=1, padx=6, pady=4)
        ctk.CTkLabel(header_grid, text="% Gained", font=ctk.CTkFont(size=11, weight="bold"), width=80, anchor="e").grid(row=0, column=2, padx=6, pady=4)
        ctk.CTkLabel(header_grid, text="Rate / Hour", font=ctk.CTkFont(size=11, weight="bold"), width=110, anchor="e").grid(row=0, column=3, padx=8, pady=4)

        # Windows definitions
        self.window_keys = [
            ("1m", 60, "Past 1 min"),
            ("5m", 300, "Past 5 min"),
            ("10m", 600, "Past 10 min"),
            ("30m", 1800, "Past 30 min"),
            ("1h", 3600, "Past 1 hour"),
        ]

        self.window_labels = {}
        for idx, (key, sec, label_text) in enumerate(self.window_keys):
            row_frame = ctk.CTkFrame(card, fg_color="transparent" if idx % 2 == 0 else "#232428", corner_radius=3)
            row_frame.pack(fill="x", padx=12, pady=1)

            lbl_name = ctk.CTkLabel(row_frame, text=key, font=ctk.CTkFont(size=12, weight="bold"), width=70, anchor="w", text_color="#58a6ff")
            lbl_name.grid(row=0, column=0, padx=8, pady=3)

            lbl_exp = ctk.CTkLabel(row_frame, text="+0", font=ctk.CTkFont(size=12), width=110, anchor="e", text_color="#ffffff")
            lbl_exp.grid(row=0, column=1, padx=6, pady=3)

            lbl_pct = ctk.CTkLabel(row_frame, text="+0.00%", font=ctk.CTkFont(size=12), width=80, anchor="e", text_color="#a8e61d")
            lbl_pct.grid(row=0, column=2, padx=6, pady=3)

            lbl_rate = ctk.CTkLabel(row_frame, text="0 /hr", font=ctk.CTkFont(size=12), width=110, anchor="e", text_color="#e0e0e0")
            lbl_rate.grid(row=0, column=3, padx=8, pady=3)

            self.window_labels[key] = {
                'exp': lbl_exp,
                'pct': lbl_pct,
                'rate': lbl_rate,
                'seconds': sec
            }

        # Extra padding bottom
        ctk.CTkFrame(card, fg_color="transparent", height=6).pack()

    def _build_session_card(self):
        card = ctk.CTkFrame(self, fg_color="#1e1f22", corner_radius=10)
        card.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            card,
            text="SESSION OVERVIEW",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(anchor="w", padx=14, pady=(8, 4))

        stats_grid = ctk.CTkFrame(card, fg_color="transparent")
        stats_grid.pack(fill="x", padx=14, pady=(0, 8))

        # Col 1: Duration & Total Gain
        self.session_time_label = ctk.CTkLabel(
            stats_grid,
            text="⏱ Duration: 00:00:00",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.session_time_label.grid(row=0, column=0, sticky="w", pady=2)

        self.session_gain_label = ctk.CTkLabel(
            stats_grid,
            text="🌟 Total Gain: +0 (+0.00%)",
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color="#ffffff"
        )
        self.session_gain_label.grid(row=1, column=0, sticky="w", pady=2)

        # Col 2: Average Rate
        self.session_rate_label = ctk.CTkLabel(
            stats_grid,
            text="⚡ Avg Rate: 0 EXP/hr",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="e",
            text_color="#f2c94c"
        )
        self.session_rate_label.grid(row=0, column=1, sticky="e", padx=(40, 0), pady=2)

        self.session_pct_rate_label = ctk.CTkLabel(
            stats_grid,
            text="(+0.00% / hr)",
            font=ctk.CTkFont(size=11),
            anchor="e",
            text_color="#a8e61d"
        )
        self.session_pct_rate_label.grid(row=1, column=1, sticky="e", padx=(40, 0), pady=2)

    def _build_preview_card(self):
        """Collapsible preview showing what the tracker sees."""
        self.preview_frame = ctk.CTkFrame(self, fg_color="#1e1f22", corner_radius=10)
        
        top_row = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(8, 4))
        
        ctk.CTkLabel(
            top_row,
            text="DETECTION PREVIEW (LIVE)",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#8a8d95"
        ).pack(side="left")

        self.preview_img_label = ctk.CTkLabel(self.preview_frame, text="No preview available")
        self.preview_img_label.pack(padx=14, pady=(2, 8))

        self.preview_shown = False

    def _build_controls(self):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(8, 12))

        self.reset_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Reset Session",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#c0392b",
            hover_color="#962d22",
            height=32,
            command=self._on_reset_clicked
        )
        self.reset_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.pause_btn = ctk.CTkButton(
            btn_frame,
            text="⏸ Pause",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#34495e",
            hover_color="#2c3e50",
            height=32,
            command=self._toggle_pause
        )
        self.pause_btn.pack(side="left", expand=True, fill="x", padx=4)

        self.preview_toggle_btn = ctk.CTkButton(
            btn_frame,
            text="👁 Preview",
            font=ctk.CTkFont(size=12),
            fg_color="#2b2d31",
            hover_color="#3b3e45",
            height=32,
            width=80,
            command=self._toggle_preview
        )
        self.preview_toggle_btn.pack(side="left", padx=(4, 0))

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
            self.preview_frame.pack(fill="x", padx=16, pady=4, after=self.status_frame)
            self.preview_toggle_btn.configure(fg_color="#1f538d")
            self.geometry("460x730")
        else:
            self.preview_frame.pack_forget()
            self.preview_toggle_btn.configure(fg_color="#2b2d31")
            self.geometry("460x650")

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

    def _on_ui_tick(self):
        """Pulls latest state from controller and updates UI labels."""
        data = self.controller.get_latest_state()

        # Update status badge
        status = data.get('status', 'NOT_FOUND')
        details = data.get('details', '')
        if status == 'LOCKED':
            self.status_label.configure(
                text=f"● Locked: MapleStory ({details})",
                text_color="#43b581"  # Discord/Maple green
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

        # Update current exp and percentage
        current_exp = data.get('current_exp', 0)
        current_pct = data.get('current_pct', 0.0)
        bar_pct = data.get('bar_pct')

        self.exp_val_label.configure(text=f"{current_exp:,} EXP")
        self.exp_pct_label.configure(text=f"[ {current_pct:.2f}% ]")

        # Smooth progress bar
        display_pct = current_pct if current_pct is not None else (bar_pct if bar_pct is not None else 0.0)
        self.exp_progress.set(min(1.0, max(0.0, display_pct / 100.0)))

        # ETA and level-up info
        eta_sec = data.get('eta_seconds')
        self.eta_label.configure(text=f"⏳ Level Up ETA: {self._format_time(eta_sec)}")
        self.lvlup_label.configure(text=f"Level-ups: {data.get('level_ups', 0)}")

        # Update rolling windows
        windows = data.get('windows', {})
        for key, info in self.window_labels.items():
            wdata = windows.get(key, {})
            g_exp = wdata.get('gained_exp', 0)
            g_pct = wdata.get('gained_pct', 0.0)
            r_hr = wdata.get('exp_rate_hr', 0)

            sign = "+" if g_exp >= 0 else ""
            info['exp'].configure(text=f"{sign}{g_exp:,}")
            info['pct'].configure(text=f"{sign}{g_pct:.2f}%")
            info['rate'].configure(text=f"{r_hr:,} /hr")

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

        # Update live preview image if enabled
        if self.preview_shown and 'crop_bgr' in data and data['crop_bgr'] is not None:
            try:
                crop = data['crop_bgr']
                # Resize preview for display (e.g. 2x)
                disp_w = min(400, crop.shape[1] * 2)
                disp_h = max(20, crop.shape[0] * 2)
                resized = cv2.resize(crop, (disp_w, disp_h), interpolation=cv2.INTER_NEAREST)
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(disp_w, disp_h))
                self.preview_img_label.configure(image=ctk_img, text="")
            except Exception:
                pass

        # Schedule next tick
        self.after(100, self._on_ui_tick)
