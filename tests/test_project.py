"""Tests for analysis/orchestration code. These do NOT replace EDA integration tests."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE_FILE = Path(__file__).resolve().parents[1] / "scripts/project.py"
spec = importlib.util.spec_from_file_location("project_runner", MODULE_FILE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TestMeasurementParsing(unittest.TestCase):
    def test_parse_violated_critical_path(self):
        report = """Startpoint: a_reg[0]\nEndpoint: sum[0]\n    data arrival time 0.385\n slack (VIOLATED) -0.125\nworst slack max -0.125\n"""
        result = runner.parse_timing(report)
        self.assertEqual(result["worst_slack_ns"], -0.125)
        self.assertEqual(result["wns_ns"], -0.125)
        self.assertEqual(result["critical_path_delay_ns"], 0.385)
        self.assertEqual(result["critical_startpoint"], "a_reg[0]")

    def test_positive_slack_not_misreported_as_negative(self):
        result = runner.parse_timing("worst slack max 0.240\nStartpoint: ff\nEndpoint: gg")
        self.assertEqual(result["worst_slack_ns"], 0.24)
        self.assertEqual(result["wns_ns"], 0.0)

    def test_missing_slack_is_hard_error(self):
        with self.assertRaisesRegex(RuntimeError, "numeric max/setup slack"):
            runner.parse_timing("No constrained paths found")

    def test_area_report(self):
        self.assertEqual(runner.parse_area("Chip area for module '\\adder16': 98.75"), 98.75)
        self.assertIsNone(runner.parse_area("Number of wires: 11"))

    def test_synthesis_script_uses_same_library_everywhere(self):
        ys = runner.yosys_script(Path("a.v"), "adder16", Path("nangate.lib"), Path("mapped.v"))
        self.assertIn("-noabc", ys)
        self.assertIn("dfflibmap -liberty", ys)
        self.assertIn("abc -liberty", ys)
        self.assertIn("stat -liberty", ys)

    def test_sta_explicit_setup_constraints(self):
        tcl = runner.opensta_script("adder16", Path("library.lib"), Path("mapped.v"), {
            "clock_period_ns": 0.5, "clock_uncertainty_ns": 0.02, "io_delay_ns": 0.05})
        self.assertIn("create_clock -name core_clk -period 0.5", tcl)
        self.assertIn("report_worst_slack", tcl)
        self.assertIn("set_output_delay", tcl)

    def test_prompt_conditions_separate_feedback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rtl").mkdir()
            (root / "rtl/adder16.v").write_text("module adder16; endmodule")
            base = root / "results/baseline/adder16"
            base.mkdir(parents=True)
            (base / "metrics.json").write_text(json.dumps({
                "worst_slack_ns": -0.15, "wns_ns": -0.15, "critical_path_delay_ns": 0.7}))
            (base / "timing.log").write_text("Startpoint: ff_x\nEndpoint: ff_y\ncell fanout 4\nworst slack max -0.15\n")
            with patch.object(runner, "ROOT", root):
                a = runner.prompt_for("adder16", "A")
                b = runner.prompt_for("adder16", "B")
                c = runner.prompt_for("adder16", "C")
            self.assertNotIn("-0.15", a)
            self.assertIn("-0.15", b)
            self.assertNotIn("ff_x", b)
            self.assertIn("ff_x", c)
            self.assertIn("fanout", c)


if __name__ == "__main__":
    unittest.main()
