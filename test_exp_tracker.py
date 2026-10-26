import time
import unittest
from src.tracker import ExpTracker, ExpSample


class TestExpTracker(unittest.TestCase):
    def test_normal_grinding(self):
        tracker = ExpTracker()
        # Start at 10,000 EXP (35.0%)
        tracker.add_sample(10000, 35.00, 35.0)
        self.assertEqual(tracker.total_gained_exp, 0)

        # Gain 50 EXP per second for 5 seconds
        for i in range(1, 6):
            tracker.add_sample(10000 + i * 50, 35.00 + i * 0.05, 35.0 + i * 0.05)

        self.assertEqual(tracker.total_gained_exp, 250)
        self.assertAlmostEqual(tracker.total_gained_pct, 0.25, places=2)

    def test_black_screen_multi_frame_dropout(self):
        tracker = ExpTracker()
        tracker.add_sample(10000, 35.00, 35.0)
        tracker.add_sample(10050, 35.05, 35.05)

        # Screen goes black during map transition (lasts 3 seconds reading 0 EXP)
        tracker.add_sample(0, 0.0, None)
        tracker.add_sample(0, 0.0, None)
        tracker.add_sample(0, 0.0, None)

        # Screen returns! EXP is 10060 (player gained 10 exp right before/after portal)
        tracker.add_sample(10060, 35.06, 35.06)
        tracker.add_sample(10110, 35.11, 35.11)

        # Total gained EXP should be 10,110 - 10,000 = 110 EXP, NOT 10,000+!
        self.assertEqual(tracker.total_gained_exp, 110)
        self.assertAlmostEqual(tracker.total_gained_pct, 0.11, places=2)

        # Window gain should also be clean
        w1 = tracker.get_window_gain(60)
        self.assertEqual(w1['gained_exp'], 110)

    def test_transient_ocr_spike(self):
        tracker = ExpTracker()
        tracker.add_sample(10000, 35.00, 35.0)
        tracker.add_sample(10050, 35.05, 35.05)

        # OCR glitch inserts an extra digit: reads 100,500 instead of 10,050 (+90,450 fake gain)
        tracker.add_sample(100500, 35.05, 35.05)

        # Next frame: OCR reads correct value 10,100
        tracker.add_sample(10100, 35.10, 35.10)
        tracker.add_sample(10150, 35.15, 35.15)

        self.assertEqual(tracker.total_gained_exp, 150)
        w1 = tracker.get_window_gain(60)
        self.assertEqual(w1['gained_exp'], 150)

    def test_multi_frame_spike_sanitization(self):
        tracker = ExpTracker()
        now = time.time()
        # A 2-frame spike that made it into history
        s0 = ExpSample(now - 8, 10000, 35.0, 35.0)
        s1 = ExpSample(now - 6, 10050, 35.05, 35.05, delta_exp=50, delta_pct=0.05)
        s2 = ExpSample(now - 4, 150000, 35.05, 35.05, delta_exp=139950, delta_pct=0.0)
        s3 = ExpSample(now - 2, 10100, 35.10, 35.10, delta_exp=0, delta_pct=0.05)

        tracker.history.extend([s0, s1, s2, s3])
        tracker.last_sample = s3
        tracker.session_start_time = now - 8
        tracker.total_gained_exp = 50 + 139950
        tracker.total_gained_pct = 0.10

        anomalies = tracker.sanitize_history()
        self.assertGreaterEqual(anomalies, 1)
        self.assertEqual(tracker.total_gained_exp, 100)

    def test_retroactive_sanitization_of_corrupted_history(self):
        tracker = ExpTracker()
        now = time.time()
        s0 = ExpSample(now - 10, 10000, 35.0, 35.0, delta_exp=0, delta_pct=0.0)
        s1 = ExpSample(now - 8, 10050, 35.05, 35.05, delta_exp=50, delta_pct=0.05)
        # Glitch sample: jumped to 500,000
        s2 = ExpSample(now - 6, 500000, 35.05, 35.05, delta_exp=489950, delta_pct=0.0)
        # Reverted back to 10,100
        s3 = ExpSample(now - 4, 10100, 35.10, 35.10, delta_exp=0, delta_pct=0.05)
        s4 = ExpSample(now - 2, 10150, 35.15, 35.15, delta_exp=50, delta_pct=0.05)

        tracker.history.extend([s0, s1, s2, s3, s4])
        tracker.total_gained_exp = 50 + 489950 + 50
        tracker.total_gained_pct = 0.15
        tracker.last_sample = s4
        tracker.session_start_time = now - 10

        # Retroactively sanitize!
        anomalies = tracker.sanitize_history()
        self.assertGreaterEqual(anomalies, 1)
        self.assertEqual(tracker.total_gained_exp, 150)

    def test_legitimate_level_up(self):
        tracker = ExpTracker()
        tracker.add_sample(995000, 99.50, 99.50)
        tracker.add_sample(999000, 99.90, 99.90)

        # Level up! EXP resets to 500 [0.05%]
        tracker.add_sample(500, 0.05, 0.05)
        # Next frame confirms level up
        tracker.add_sample(1000, 0.10, 0.10)

        self.assertEqual(tracker.level_ups, 1)
        self.assertGreater(tracker.total_gained_exp, 1500)

    def test_character_death(self):
        tracker = ExpTracker()
        tracker.add_sample(100000, 50.00, 50.00)
        tracker.add_sample(100500, 50.25, 50.25)

        # Character dies! Loses 10% EXP (down to 40.25%)
        tracker.add_sample(80500, 40.25, 40.25)
        # Subsequent hunting continues
        tracker.add_sample(80600, 40.30, 40.30)

        # Total gain should only be 500 + 100 = 600, death loss shouldn't count as negative or fake level up
        self.assertEqual(tracker.total_gained_exp, 600)
        self.assertEqual(tracker.level_ups, 0)

    def test_optical_divergence_rejected(self):
        tracker = ExpTracker()
        tracker.add_sample(10000, 35.00, 35.00)
        # OCR reads 80% but graphical bar fill is 35% -> rejected immediately
        tracker.add_sample(25000, 80.00, 35.00)
        # Total gained exp should still be 0
        self.assertEqual(tracker.total_gained_exp, 0)


if __name__ == '__main__':
    unittest.main()
