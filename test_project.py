import unittest
import analysis

class AnalysisTests(unittest.TestCase):
    def test_recovers_known_effect(self):
        result = analysis.estimate_did(analysis.make_demo_panel())
        self.assertLess(result["effect"], -2.5)
        self.assertGreater(result["effect"], -3.8)
        self.assertLess(result["ci_low"], result["ci_high"])

    def test_event_study_and_placebo(self):
        panel = analysis.make_demo_panel()
        events = analysis.event_study(panel)
        placebo = analysis.placebo_test(panel)
        self.assertIn(-1, events["relative_month"].tolist())
        self.assertEqual(events.loc[events["relative_month"] == -1, "effect"].iloc[0], 0)
        self.assertGreater(placebo["p_value"], 0.01)

    def test_panel_validation(self):
        quality = analysis.validate_panel(analysis.make_demo_panel())
        self.assertTrue(quality["balanced_panel"])

if __name__ == "__main__":
    unittest.main()
