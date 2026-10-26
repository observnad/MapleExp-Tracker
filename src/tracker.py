import time
from collections import deque


class ExpSample:
    def __init__(self, timestamp, exp_val, exp_pct, bar_pct=None, delta_exp=0, delta_pct=0.0,
                 is_outlier=False, is_level_up=False):
        self.timestamp = timestamp
        self.exp_val = exp_val
        self.exp_pct = exp_pct
        self.bar_pct = bar_pct
        self.delta_exp = delta_exp
        self.delta_pct = delta_pct
        self.is_outlier = is_outlier
        self.is_level_up = is_level_up


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
        self.anomalies_corrected = 0

        # Multi-frame drop immunity state: (anchor_sample, [buffered_drop_samples], timeout_start)
        self._drop_state = None

        # Pending spike buffer for sudden unfeasible jumps: (spike_sample, prev_sample, d_exp, d_pct)
        self._pending_spike = None

        # Pending level-up buffer: (cand_sample, prev_sample, est_d_exp, est_d_pct)
        self._pending_lvl = None

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
        self.anomalies_corrected = 0
        self._drop_state = None
        self._pending_spike = None
        self._pending_lvl = None

    def _commit_sample(self, sample, delta_exp, delta_pct, is_level_up=False):
        if is_level_up:
            self.level_ups += 1
            sample.is_level_up = True
        if delta_exp > 0:
            self.total_gained_exp += delta_exp
        if delta_pct > 0:
            self.total_gained_pct += delta_pct

        sample.delta_exp = delta_exp
        sample.delta_pct = delta_pct

        self.last_sample = sample
        self.history.append(sample)

        # Prune old samples beyond max history cutoff
        cutoff = sample.timestamp - self.max_history_seconds
        while self.history and self.history[0].timestamp < cutoff:
            self.history.popleft()

    def add_sample(self, exp_val, exp_pct, bar_pct=None):
        """Records a new EXP observation with multi-frame dropout immunity & spike gating."""
        if self.is_paused or exp_val is None:
            return

        # Optical bar inconsistency check: if both text pct and graphical bar pct are detected,
        # reject wild divergences (> 25%) as transient OCR noise
        if exp_pct is not None and bar_pct is not None and abs(exp_pct - bar_pct) > 25.0:
            return

        now = time.time()
        sample = ExpSample(now, exp_val, exp_pct, bar_pct)

        # Initialize session on first valid non-zero sample
        if self.session_start_time is None:
            # If the very first sample is 0 while exp_pct is missing, wait for real data
            if exp_val == 0 and (exp_pct is None or exp_pct == 0.0) and bar_pct is None:
                return
            self.session_start_time = now
            self.session_initial_exp = exp_val
            self.session_initial_pct = exp_pct if exp_pct is not None else 0.0
            sample.delta_exp = 0
            sample.delta_pct = 0.0
            self.last_sample = sample
            self.history.append(sample)
            return

        # 1. Resolve pending level-up buffer
        if self._pending_lvl is not None:
            cand_sample, anchor_prev, est_d_exp, est_d_pct = self._pending_lvl
            self._pending_lvl = None

            # Check if this new sample reverted back near anchor_prev (meaning it was not a level up)
            reverted = (exp_val >= anchor_prev.exp_val * 0.95 and
                        (anchor_prev.exp_pct is None or exp_pct is None or exp_pct >= anchor_prev.exp_pct - 2.0))
            if reverted:
                # Glitch artifact confirmed: discard cand_sample completely
                self.anomalies_corrected += 1
                prev = anchor_prev
                d_exp = exp_val - prev.exp_val
                d_pct = (exp_pct - prev.exp_pct) if (exp_pct is not None and prev.exp_pct is not None) else 0.0
                if d_exp >= 0:
                    self._commit_sample(sample, d_exp, d_pct, False)
                return
            else:
                # Level up confirmed!
                self._commit_sample(cand_sample, est_d_exp, est_d_pct, True)
                prev = cand_sample
                d_exp = exp_val - prev.exp_val
                d_pct = (exp_pct - prev.exp_pct) if (exp_pct is not None and prev.exp_pct is not None) else 0.0
                if d_exp >= 0:
                    self._commit_sample(sample, d_exp, d_pct, False)
                return

        # 2. Resolve multi-frame drop state (black screen / portal transition immunity)
        if self._drop_state is not None:
            anchor_sample, drop_samples, timeout_start = self._drop_state

            # Did current sample return near the pre-drop anchor baseline?
            val_ok = (exp_val >= anchor_sample.exp_val * 0.95 or exp_val >= anchor_sample.exp_val - 100)
            pct_ok = (anchor_sample.exp_pct is None or exp_pct is None or exp_pct >= anchor_sample.exp_pct - 2.0)

            if val_ok and pct_ok:
                # Screen transition complete! Current reading is back at real baseline.
                # All drop_samples were transition artifacts: discard them completely!
                self.anomalies_corrected += len(drop_samples)
                self._drop_state = None

                # Process current sample against the pre-drop anchor baseline
                d_exp = max(0, exp_val - anchor_sample.exp_val)
                d_pct = max(0.0, (exp_pct - anchor_sample.exp_pct)) if (exp_pct is not None and anchor_sample.exp_pct is not None) else 0.0
                self._commit_sample(sample, d_exp, d_pct, False)
                self.sanitize_history()
                return

            # Still in drop state: buffer for up to 10 seconds or 10 frames
            if now - timeout_start < 10.0 and len(drop_samples) < 10:
                drop_samples.append(sample)
                return
            else:
                # Drop timed out (> 10s sustained lower EXP): real relog / character switch
                self._drop_state = None
                sample.delta_exp = 0
                sample.delta_pct = 0.0
                self.last_sample = sample
                self.history.append(sample)
                self.sanitize_history()
                return

        # 3. Resolve pending spike buffer (unfeasible sudden jump verification)
        if self._pending_spike is not None:
            spike_sample, prev_sample, spike_d_exp, spike_d_pct = self._pending_spike
            self._pending_spike = None

            # Check if this new sample dropped back down near prev_sample baseline
            reverted = (exp_val <= prev_sample.exp_val * 1.05 and
                        (prev_sample.exp_pct is None or exp_pct is None or exp_pct <= prev_sample.exp_pct + 1.0))

            if reverted:
                # The spike was an OCR glitch! Discard spike_sample completely.
                self.anomalies_corrected += 1
                d_exp = max(0, exp_val - prev_sample.exp_val)
                d_pct = max(0.0, (exp_pct - prev_sample.exp_pct)) if (exp_pct is not None and prev_sample.exp_pct is not None) else 0.0
                self._commit_sample(sample, d_exp, d_pct, False)
                self.sanitize_history()
                return
            else:
                # The spike stayed high (legitimate massive quest reward or boss kill)
                self._commit_sample(spike_sample, spike_d_exp, spike_d_pct, False)
                d_exp = max(0, exp_val - spike_sample.exp_val)
                d_pct = max(0.0, (exp_pct - spike_sample.exp_pct)) if (exp_pct is not None and spike_sample.exp_pct is not None) else 0.0
                self._commit_sample(sample, d_exp, d_pct, False)
                self.sanitize_history()
                return

        # Check for change since last sample
        prev = self.last_sample
        if prev is not None:
            delta_exp = exp_val - prev.exp_val
            delta_pct = (exp_pct - prev.exp_pct) if (exp_pct is not None and prev.exp_pct is not None) else 0.0

            if delta_exp < 0:
                # In MapleStory, you cannot level up unless previous percentage was near 100% (>= 80%).
                # And after leveling up, the new percentage resets to low (<= 25%).
                is_legit_lvl = (prev.exp_pct is not None and prev.exp_pct >= 80.0 and
                                exp_pct is not None and exp_pct <= 25.0)

                if is_legit_lvl:
                    # Estimate remaining exp of previous level
                    if prev.exp_pct > 0:
                        est_max = int(prev.exp_val / (prev.exp_pct / 100.0))
                        gained_before_lvl = max(0, est_max - prev.exp_val)
                        est_d_exp = gained_before_lvl + exp_val
                        est_d_pct = (100.0 - prev.exp_pct) + (exp_pct if exp_pct else 0.0)
                    else:
                        est_d_exp = exp_val
                        est_d_pct = exp_pct if exp_pct else 0.0

                    # Buffer for 1-frame confirmation so transient drops never fake a level-up
                    self._pending_lvl = (sample, prev, est_d_exp, est_d_pct)
                    return

                # Check if it was legitimate character death
                # MapleStory death penalty loses 5% to 10% EXP (between 2% and 15% drop).
                is_death = (prev.exp_pct is not None and exp_pct is not None and
                            2.0 <= (prev.exp_pct - exp_pct) <= 15.0 and
                            exp_val > 0)
                if is_death:
                    # Character died: update current EXP baseline without counting fake level-up or gain
                    sample.delta_exp = 0
                    sample.delta_pct = 0.0
                    self.last_sample = sample
                    self.history.append(sample)
                    return

                # Sudden drop that is neither a level-up nor death (e.g. portal transition, OCR drop to 0):
                # Start multi-frame drop immunity state holding anchor = prev
                self._drop_state = (prev, [sample], now)
                return

            # Check if this instantaneous positive jump is physically unfeasible:
            # (e.g. jump > 50,000 EXP AND > 25% of baseline when baseline > 5,000, or delta_pct > 8.0% in 1s)
            is_suspicious_spike = (
                (prev.exp_val > 5000 and delta_exp > 50000 and delta_exp > prev.exp_val * 0.25) or
                (delta_pct > 8.0)
            )
            if is_suspicious_spike:
                # Buffer for 1-frame confirmation so transient OCR digit insertions never skyrocket rates
                self._pending_spike = (sample, prev, delta_exp, delta_pct)
                return

            # Normal progression (delta_exp >= 0)
            self._commit_sample(sample, delta_exp, delta_pct, False)
            self.sanitize_history()
            return

        sample.delta_exp = 0
        sample.delta_pct = 0.0
        self.last_sample = sample
        self.history.append(sample)

        # Prune old samples
        cutoff = now - self.max_history_seconds
        while self.history and self.history[0].timestamp < cutoff:
            self.history.popleft()

    def sanitize_history(self):
        """
        Retroactively inspects history to detect and eliminate:
        1. Transient spikes: samples that jumped up and later reverted.
        2. Transient dips: samples that dropped down and later returned.
        3. Wild OCR digit insertions / physically unfeasible deltas.
        Recomputes total_gained_exp and total_gained_pct.
        Returns the number of anomalous samples corrected.
        """
        if len(self.history) < 3:
            return 0

        history_list = list(self.history)
        n = len(history_list)
        anomalies_found = 0

        # Pass 1: Scan for transient spikes (S[i] >> S[i-1] and S[i+k] returns to baseline)
        for i in range(1, n - 1):
            s_curr = history_list[i]
            if getattr(s_curr, 'is_outlier', False):
                continue

            s_prev = None
            for p in range(i - 1, -1, -1):
                if not getattr(history_list[p], 'is_outlier', False):
                    s_prev = history_list[p]
                    break
            if s_prev is None:
                continue

            d_val = s_curr.exp_val - s_prev.exp_val
            d_pct = (s_curr.exp_pct - s_prev.exp_pct) if (s_curr.exp_pct is not None and s_prev.exp_pct is not None) else 0.0

            # Spike condition: significantly higher than baseline
            is_spike = (
                (s_prev.exp_val > 5000 and d_val > 30000 and d_val > s_prev.exp_val * 0.20) or
                (d_pct > 6.0 and not getattr(s_curr, 'is_level_up', False)) or
                (d_val > 5000000)
            )

            if is_spike:
                # Look ahead up to 8 samples (approx 8 seconds)
                reverted = False
                for k in range(i + 1, min(n, i + 9)):
                    s_ahead = history_list[k]
                    if getattr(s_ahead, 'is_outlier', False):
                        continue
                    # Check if s_ahead returned near s_prev baseline
                    if s_ahead.exp_val <= s_prev.exp_val * 1.05 and (s_prev.exp_pct is None or s_ahead.exp_pct is None or s_ahead.exp_pct <= s_prev.exp_pct + 1.5):
                        reverted = True
                        break

                if reverted:
                    s_curr.is_outlier = True
                    s_curr.delta_exp = 0
                    s_curr.delta_pct = 0.0
                    anomalies_found += 1

        # Pass 2: Scan for transient dips (S[i] << S[i-1] and S[i+k] recovers)
        for i in range(1, n - 1):
            s_curr = history_list[i]
            if getattr(s_curr, 'is_outlier', False):
                continue

            s_prev = None
            for p in range(i - 1, -1, -1):
                if not getattr(history_list[p], 'is_outlier', False):
                    s_prev = history_list[p]
                    break
            if s_prev is None:
                continue

            d_val = s_curr.exp_val - s_prev.exp_val
            is_legit_lvl = (s_prev.exp_pct is not None and s_prev.exp_pct >= 80.0 and
                            s_curr.exp_pct is not None and s_curr.exp_pct <= 25.0)

            if d_val < 0 and not is_legit_lvl:
                # Look ahead up to 10 samples for recovery
                recovered = False
                for k in range(i + 1, min(n, i + 11)):
                    s_ahead = history_list[k]
                    if getattr(s_ahead, 'is_outlier', False):
                        continue
                    if s_ahead.exp_val >= s_prev.exp_val * 0.95 or s_ahead.exp_val >= s_prev.exp_val - 100:
                        recovered = True
                        break

                if recovered:
                    s_curr.is_outlier = True
                    s_curr.delta_exp = 0
                    s_curr.delta_pct = 0.0
                    anomalies_found += 1

        # Recompute totals and deltas if any anomaly was detected
        if anomalies_found > 0:
            self.anomalies_corrected += anomalies_found
            self._recalculate_totals_from_history()

        return anomalies_found

    def _recalculate_totals_from_history(self):
        """Recomputes total_gained_exp, total_gained_pct, and level_ups strictly from clean samples."""
        new_total_exp = 0
        new_total_pct = 0.0
        new_level_ups = 0
        last_valid = None

        for s in self.history:
            if getattr(s, 'is_outlier', False):
                s.delta_exp = 0
                s.delta_pct = 0.0
                continue

            if last_valid is None:
                s.delta_exp = 0
                s.delta_pct = 0.0
                last_valid = s
                continue

            if getattr(s, 'is_level_up', False):
                new_level_ups += 1
            else:
                d_exp = max(0, s.exp_val - last_valid.exp_val)
                d_pct = max(0.0, (s.exp_pct - last_valid.exp_pct)) if (s.exp_pct is not None and last_valid.exp_pct is not None) else 0.0
                s.delta_exp = d_exp
                s.delta_pct = round(d_pct, 2)

            if s.delta_exp > 0:
                new_total_exp += s.delta_exp
            if s.delta_pct > 0:
                new_total_pct += s.delta_pct

            last_valid = s

        self.total_gained_exp = new_total_exp
        self.total_gained_pct = round(new_total_pct, 2)
        self.level_ups = new_level_ups

    def get_window_gain(self, window_seconds, num_slices=128):
        """
        Calculates the EXP and percentage gained within the last `window_seconds`,
        along with a 128-slice rolling EXP graph distribution.
        Retroactively sanitizes history to ensure unfeasible spikes/dips are purged.
        """
        self.sanitize_history()

        empty_slices = [0.0] * num_slices
        slice_sec = window_seconds / num_slices if num_slices > 0 else 1.0

        # Filter clean (non-outlier) samples
        clean_samples = [s for s in self.history if not getattr(s, 'is_outlier', False)]
        if len(clean_samples) < 2:
            return {
                'gained_exp': 0,
                'gained_pct': 0.0,
                'exp_rate_hr': 0,
                'pct_rate_hr': 0.0,
                'data_duration': 0,
                'slices': empty_slices,
                'slice_duration': round(slice_sec, 2),
                'max_slice': 0.0,
                'avg_slice': 0.0
            }

        now = time.time()
        target_time = now - window_seconds

        # Find the sample closest to target_time
        base_sample = None
        for s in clean_samples:
            if s.timestamp >= target_time:
                base_sample = s
                break

        if base_sample is None:
            base_sample = clean_samples[0]

        curr = clean_samples[-1]
        elapsed = curr.timestamp - base_sample.timestamp

        gained_exp = 0
        gained_pct = 0.0

        try:
            start_idx = clean_samples.index(base_sample)
        except ValueError:
            start_idx = 0

        for i in range(start_idx, len(clean_samples) - 1):
            s1 = clean_samples[i]
            s2 = clean_samples[i + 1]
            d_exp = getattr(s2, 'delta_exp', None)
            d_pct = getattr(s2, 'delta_pct', None)

            if d_exp is None or d_pct is None:
                d_exp = s2.exp_val - s1.exp_val
                d_pct = (s2.exp_pct - s1.exp_pct) if (s2.exp_pct is not None and s1.exp_pct is not None) else 0.0

                if d_exp < 0 and (s1.exp_pct is not None and s1.exp_pct >= 80.0 and (s2.exp_pct is None or s2.exp_pct <= 25.0)):
                    # Legitimate level up in window
                    if s1.exp_pct is not None and s1.exp_pct > 0:
                        est_max = int(s1.exp_val / (s1.exp_pct / 100.0))
                        d_exp = max(0, est_max - s1.exp_val) + s2.exp_val
                        d_pct = (100.0 - s1.exp_pct) + (s2.exp_pct if s2.exp_pct else 0.0)
                    else:
                        d_exp = s2.exp_val
                        d_pct = s2.exp_pct if s2.exp_pct else 0.0
                elif d_exp < 0:
                    d_exp = 0
                    d_pct = 0.0

            if d_exp > 0:
                gained_exp += d_exp
            if d_pct > 0:
                gained_pct += d_pct

        # Hourly rate projection (with dampening for very short windows to prevent multiplier explosion)
        effective_elapsed = max(3.0, elapsed)
        rate_multiplier = 3600.0 / effective_elapsed
        raw_exp_rate_hr = int(round(gained_exp * rate_multiplier))
        raw_pct_rate_hr = round(gained_pct * rate_multiplier, 2)

        # Sanity capping: project no higher than 2 billion EXP/hr or 2000%/hr
        exp_rate_hr = min(2000000000, raw_exp_rate_hr)
        pct_rate_hr = min(2000.0, raw_pct_rate_hr)

        # Compute 128 slices for rolling graph (EXP gained per 1/128 window slice)
        slices = [0.0] * num_slices
        t_start = now - window_seconds
        delta_t = window_seconds / num_slices if num_slices > 0 else 1.0

        scan_start = max(0, start_idx - 1)
        for i in range(scan_start, len(clean_samples) - 1):
            s1 = clean_samples[i]
            s2 = clean_samples[i + 1]
            t1, t2 = s1.timestamp, s2.timestamp
            d_exp = getattr(s2, 'delta_exp', None)
            if d_exp is None:
                d_exp = max(0, s2.exp_val - s1.exp_val)

            if d_exp <= 0 or t2 <= t_start or t1 >= now or t2 <= t1:
                continue

            eff_t1 = max(t1, t_start)
            eff_t2 = min(t2, now)
            rate = d_exp / (t2 - t1)

            k_start = max(0, min(num_slices - 1, int((eff_t1 - t_start) / delta_t)))
            k_end = max(0, min(num_slices - 1, int((eff_t2 - t_start) / delta_t)))

            for k in range(k_start, k_end + 1):
                slice_t1 = t_start + k * delta_t
                slice_t2 = slice_t1 + delta_t
                overlap = max(0.0, min(eff_t2, slice_t2) - max(eff_t1, slice_t1))
                slices[k] += rate * overlap

        rounded_slices = [round(x, 1) for x in slices]
        max_slice = round(max(slices) if slices else 0.0, 1)
        avg_slice = round((sum(slices) / num_slices) if slices else 0.0, 1)

        return {
            'gained_exp': gained_exp,
            'gained_pct': round(gained_pct, 2),
            'exp_rate_hr': exp_rate_hr,
            'pct_rate_hr': pct_rate_hr,
            'data_duration': int(elapsed),
            'slices': rounded_slices,
            'slice_duration': round(slice_sec, 2),
            'max_slice': max_slice,
            'avg_slice': avg_slice
        }

    def get_session_stats(self):
        """Returns comprehensive session metrics and ETA."""
        self.sanitize_history()

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
                'level_ups': 0,
                'anomalies_corrected': 0
            }

        now = time.time()
        duration = max(1.0, now - self.session_start_time)
        effective_duration = max(3.0, duration)
        rate_mult = 3600.0 / effective_duration

        session_rate_hr = min(2000000000, int(round(self.total_gained_exp * rate_mult)))
        session_pct_rate_hr = min(2000.0, round(self.total_gained_pct * rate_mult, 2))

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
            'level_ups': self.level_ups,
            'anomalies_corrected': self.anomalies_corrected
        }
