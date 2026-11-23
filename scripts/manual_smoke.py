#!/usr/bin/env python3
"""Check a HAND-WRITTEN alternative adder; deliberately excluded from A/B/C trial dataset."""
from pathlib import Path
from project import ROOT, baseline_metrics, eqy_check, measure


def main():
    design = "adder16"
    candidate = ROOT / "examples/adder16_carry_select.v"
    location = ROOT / "results/manual/carry_select_smoke"
    if not (ROOT / "results/baseline/adder16/metrics.json").exists():
        raise SystemExit("Run python3 scripts/project.py baseline --design adder16 first.")
    verdict = eqy_check(design, candidate, location)
    if verdict != "PASS":
        raise SystemExit(f"Manual adder equivalence not proved ({verdict}); inspect {location}/eqy.log")
    baseline = baseline_metrics(design)
    measured = measure(design, candidate, location / "measurement")
    print("Manual candidate: equivalence PASS")
    print("Manual candidate: worst slack", measured["worst_slack_ns"])
    print("Original baseline: worst slack", baseline["worst_slack_ns"])
    print("Manual candidate: mapped area", measured["area"])
    print("NOT included in experimental A/B/C comparison.")


if __name__ == "__main__":
    main()
