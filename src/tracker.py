import time
from collections import deque


class ExpSample:
    def __init__(self, timestamp, exp_val, exp_pct, bar_pct=None):
        self.timestamp = timestamp
        self.exp_val = exp_val
        self.exp_pct = exp_pct
        self.bar_pct = bar_pct


class ExpTracker:
    def __init__(self, max_history_seconds=3700):
        self.max_history_seconds = max_history_seconds
        self.history = deque()  # stores ExpSample
        self.session_start_time = None
        self.session_initial_exp = None
        self.session_initial_pct = None
        self.total_gained_exp = 0
        self.total_gained_pct = 0.0
        self.last_sample = None
        self.level_ups = 0
        self.is_paused = False

    def reset(self):
        """Resets all tracking statistics and begins a new session."""
        self.history.clear()
        self.session_start_time = None
        self.session_initial_exp = None
        self.session_initial_pct = None
        self.total_gained_exp = 0
        self.total_gained_pct = 0.0
        self.last_sample = None
        self.level_ups = 0

    def add_sample(self, exp_val, exp_pct, bar_pct=None):
        """Records a new EXP observation."""
        if self.is_paused or exp_val is None:
            return

        now = time.time()
        sample = ExpSample(now, exp_val, exp_pct, bar_pct)

        if self.session_start_time is None:
            self.session_start_time = now
            self.session_initial_exp = exp_val
            self.session_initial_pct = exp_pct if exp_pct is not None else 0.0
            self.last_sample = sample
            self.history.append(sample)
            return

        # Check for change since last sample
        prev = self.last_sample
        if prev is not None:
            delta_exp = exp_val - prev.exp_val
            delta_pct = (exp_pct - prev.exp_pct) if (exp_pct is not None and prev.exp_pct is not None) else 0.0

            # Level-up detection (current exp dropped significantly)
            if delta_exp < 0 and (prev.exp_pct is None or prev.exp_pct > 50.0):
                self.level_ups += 1
                # Estimate remaining exp of previous level
                if prev.exp_pct is not None and prev.exp_pct > 0:
                    est_max = int(prev.exp_val / (prev.exp_pct / 100.0))
                    gained_before_lvl = max(0, est_max - prev.exp_val)
                    delta_exp = gained_before_lvl + exp_val
                    delta_pct = (100.0 - prev.exp_pct) + (exp_pct if exp_pct else 0.0)
                else:
                    delta_exp = exp_val
                    delta_pct = exp_pct if exp_pct else 0.0

            # Only accumulate positive or zero progression
            if delta_exp > 0:
                self.total_gained_exp += delta_exp
                if delta_pct > 0:
                    self.total_gained_pct += delta_pct

        self.last_sample = sample
        self.history.append(sample)

        # Prune old samples
        cutoff = now - self.max_history_seconds
        while self.history and self.history[0].timestamp < cutoff:
            self.history.popleft()

    def get_window_gain(self, window_seconds):
        """
        Calculates the EXP and percentage gained within the last `window_seconds`.
        Returns:
            dict with gained_exp, gained_pct, exp_rate_hr, pct_rate_hr, data_duration
        """
        if len(self.history) < 2:
            return {
                'gained_exp': 0,
                'gained_pct': 0.0,
                'exp_rate_hr': 0,
                'pct_rate_hr': 0.0,
                'data_duration': 0
            }

        now = time.time()
        target_time = now - window_seconds

        # Find the sample closest to target_time
        base_sample = None
        for s in self.history:
            if s.timestamp >= target_time:
                base_sample = s
                break

        if base_sample is None:
            base_sample = self.history[0]

        curr = self.history[-1]
        elapsed = curr.timestamp - base_sample.timestamp
        if elapsed < 1.0:
            return {
                'gained_exp': 0,
                'gained_pct': 0.0,
                'exp_rate_hr': 0,
                'pct_rate_hr': 0.0,
                'data_duration': 0
            }

        # Calculate gain by walking samples from base_sample to current
        # to properly handle level-ups
        gained_exp = 0
        gained_pct = 0.0
        
        # Iterate consecutive samples
        history_list = list(self.history)
        try:
            start_idx = history_list.index(base_sample)
        except ValueError:
            start_idx = 0

        for i in range(start_idx, len(history_list) - 1):
            s1 = history_list[i]
            s2 = history_list[i + 1]
            d_exp = s2.exp_val - s1.exp_val
            d_pct = (s2.exp_pct - s1.exp_pct) if (s2.exp_pct is not None and s1.exp_pct is not None) else 0.0

            if d_exp < 0 and (s1.exp_pct is None or s1.exp_pct > 50.0):
                # Level up in window
                if s1.exp_pct is not None and s1.exp_pct > 0:
                    est_max = int(s1.exp_val / (s1.exp_pct / 100.0))
                    d_exp = max(0, est_max - s1.exp_val) + s2.exp_val
                    d_pct = (100.0 - s1.exp_pct) + (s2.exp_pct if s2.exp_pct else 0.0)
                else:
                    d_exp = s2.exp_val
                    d_pct = s2.exp_pct if s2.exp_pct else 0.0

            if d_exp > 0:
                gained_exp += d_exp
            if d_pct > 0:
                gained_pct += d_pct

        # Hourly rate projection
        rate_multiplier = 3600.0 / elapsed
        exp_rate_hr = int(round(gained_exp * rate_multiplier))
        pct_rate_hr = round(gained_pct * rate_multiplier, 2)

        return {
            'gained_exp': gained_exp,
            'gained_pct': round(gained_pct, 2),
            'exp_rate_hr': exp_rate_hr,
            'pct_rate_hr': pct_rate_hr,
            'data_duration': int(elapsed)
        }

    def get_session_stats(self):
        """Returns comprehensive session metrics and ETA."""
        if self.last_sample is None or self.session_start_time is None:
            return {
                'current_exp': 0,
                'current_pct': 0.0,
                'session_duration': 0,
                'total_gained_exp': 0,
                'total_gained_pct': 0.0,
                'session_rate_hr': 0,
                'session_pct_rate_hr': 0.0,
                'eta_seconds': None,
                'level_ups': 0
            }

        now = time.time()
        duration = max(1.0, now - self.session_start_time)
        rate_mult = 3600.0 / duration

        session_rate_hr = int(round(self.total_gained_exp * rate_mult))
        session_pct_rate_hr = round(self.total_gained_pct * rate_mult, 2)

        # ETA calculation to 100% based on recent 5m/10m rate or session rate
        eta_seconds = None
        curr_pct = self.last_sample.exp_pct
        if curr_pct is not None and curr_pct < 100.0:
            remaining_pct = 100.0 - curr_pct
            
            # Prefer 5-min or 10-min rate for more responsive ETA
            w5 = self.get_window_gain(300)
            effective_pct_rate = w5['pct_rate_hr'] if w5['pct_rate_hr'] > 0 else session_pct_rate_hr
            
            if effective_pct_rate > 0.01:
                eta_hours = remaining_pct / effective_pct_rate
                eta_seconds = int(eta_hours * 3600)

        return {
            'current_exp': self.last_sample.exp_val,
            'current_pct': self.last_sample.exp_pct if self.last_sample.exp_pct is not None else 0.0,
            'bar_pct': self.last_sample.bar_pct,
            'session_duration': int(duration),
            'total_gained_exp': self.total_gained_exp,
            'total_gained_pct': round(self.total_gained_pct, 2),
            'session_rate_hr': session_rate_hr,
            'session_pct_rate_hr': session_pct_rate_hr,
            'eta_seconds': eta_seconds,
            'level_ups': self.level_ups
        }
