import unittest
import analysis

class AnalysisTests(unittest.TestCase):
    def test_recovers_known_effect(self):
        result = analysis.estimate_did(analysis.make_demo_panel())
        self.assertLess(result["effect"], -2.5)
        self.assertGreater(result["effect"], -3.8)
        self.assertLess(result["ci_low"], result["ci_high"])

if __name__ == "__main__":
    unittest.main()
