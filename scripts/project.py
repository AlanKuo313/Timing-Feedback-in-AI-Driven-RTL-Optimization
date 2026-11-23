#!/usr/bin/env python3
"""Reproducible synthesis/timing/formal A-B-C experiment orchestration.

No measured results are bundled. Requires external EDA executables for hardware evaluation.
The Python stdlib is sufficient to run the driver and its tests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DESIGNS = {
    "adder16": {"inputs": ["a*", "b*"], "outputs": ["sum*"]},
    "comparator16": {"inputs": ["a*", "b*"], "outputs": ["greater", "equal"]},
    "priority_encoder16": {"inputs": ["req*"], "outputs": ["valid", "index*"]},
    "popcount16": {"inputs": ["bits*"], "outputs": ["count*"]},
}
CSV_FIELDS = [
    "design", "condition", "trial", "model", "candidate_sha256", "equivalence",
    "status", "worst_slack_ns", "wns_ns", "critical_path_delay_ns", "area",
    "baseline_worst_slack_ns", "baseline_area", "delta_slack_ns",
    "area_change_pct", "success", "error", "candidate_path",
]


def config():
    return json.loads((ROOT / "config/experiment.json").read_text())


def library_path(cfg):
    value = os.environ.get("LIBERTY_FILE", cfg["liberty_path"])
    lib = Path(value).expanduser()
    if not lib.is_absolute():
        lib = ROOT / lib
    if not lib.is_file():
        raise RuntimeError(
            f"Liberty file not found: {lib}\n"
            "Run 'bash scripts/get_nangate45.sh' or set LIBERTY_FILE."
        )
    return lib.resolve()


def require_command(program):
    path = shutil.which(program)
    if not path:
        raise RuntimeError(f"Command '{program}' not found in PATH. See README.md installation steps.")
    return path


def execute(args, log_path, cwd=ROOT, timeout=240):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cp = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out: {' '.join(map(str, args))}") from exc
    log_path.write_text(cp.stdout + "\n[STDERR]\n" + cp.stderr)
    if cp.returncode:
        raise RuntimeError(f"Command failed (exit {cp.returncode}): {' '.join(map(str,args))}\nLog: {log_path}")
    return cp.stdout + "\n" + cp.stderr


def path_for_script(p):
    p = Path(p).resolve()
    if '"' in str(p) or '\n' in str(p):
        raise ValueError("Paths containing quotes/newlines are unsupported")
    return f'"{p.as_posix()}"'


def parse_area(yosys_log):
    # Yosys 'stat -liberty' reports mapped cell area, not routed physical area.
    patterns = [
        r"Chip area for (?:top )?module[^\n]*?:\s*([\d.]+)",
        r"Chip area:\s*([\d.]+)",
    ]
    for pat in patterns:
        hits = re.findall(pat, yosys_log, flags=re.I)
        if hits:
            return float(hits[-1])
    return None


def parse_timing(sta_report):
    # This is worst *setup* slack, which may be positive. Clipped WNS is <= 0.
    m = re.search(r"worst\s+slack(?:\s+max)?\s+([-+]?\d+(?:\.\d+)?)", sta_report, re.I)
    if not m:
        m = re.search(r"slack\s*\((?:MET|VIOLATED)\)\s*([-+]?\d+(?:\.\d+)?)", sta_report, re.I)
    if not m:
        raise RuntimeError("OpenSTA did not return a numeric max/setup slack; check timing constraints and logs.")
    slack = float(m.group(1))
    if not math.isfinite(slack):
        raise RuntimeError("Non-finite slack from timing tool")
    delay = (re.search(r"([-+]?\d+(?:\.\d+)?)\s+data arrival time", sta_report, re.I)
             or re.search(r"data arrival time\s+([-+]?\d+(?:\.\d+)?)", sta_report, re.I))
    start = re.search(r"Startpoint:\s*(.+)", sta_report, re.I)
    end = re.search(r"Endpoint:\s*(.+)", sta_report, re.I)
    # Negative slack is failure; some researchers refer to the raw worst slack
    # as WNS. Report both to remove ambiguity.
    return {
        "worst_slack_ns": slack,
        "wns_ns": min(0.0, slack),
        "critical_path_delay_ns": float(delay.group(1)) if delay else None,
        "critical_startpoint": start.group(1).strip() if start else None,
        "critical_endpoint": end.group(1).strip() if end else None,
    }


def yosys_script(src, top, lib, netlist):
    return "\n".join([
        f"read_verilog {path_for_script(src)}",
        f"hierarchy -check -top {top}",
        f"synth -top {top} -noabc",
        f"read_liberty -lib {path_for_script(lib)}",
        f"dfflibmap -liberty {path_for_script(lib)}",
        f"abc -liberty {path_for_script(lib)}",
        "clean",
        f"write_verilog -noattr -noexpr -simple-lhs {path_for_script(netlist)}",
        f"stat -liberty {path_for_script(lib)}",
        "",
    ])


def opensta_script(design, lib, netlist, cfg):
    specs = DESIGNS[design]
    lines = [
        f"read_liberty {path_for_script(lib)}",
        f"read_verilog {path_for_script(netlist)}",
        f"link_design {design}",
        f"create_clock -name core_clk -period {cfg['clock_period_ns']} [get_ports clk]",
        f"set_clock_uncertainty {cfg['clock_uncertainty_ns']} [get_clocks core_clk]",
    ]
    # Explicit port patterns avoid accidentally applying data delay to the clock.
    for port in specs["inputs"]:
        lines.append(f"set_input_delay -clock core_clk {cfg['io_delay_ns']} [get_ports {{{port}}}]")
    for port in specs["outputs"]:
        lines.append(f"set_output_delay -clock core_clk {cfg['io_delay_ns']} [get_ports {{{port}}}]")
    lines.extend([
        "report_checks -path_delay max -group_count 5 -fields {slew cap fanout}",
        "report_worst_slack",
        "exit",
    ])
    return "\n".join(lines) + "\n"


def measure(design, src, location):
    cfg = config()
    lib = library_path(cfg)
    yosys = require_command("yosys")
    sta = shutil.which("sta") or shutil.which("opensta")
    if not sta:
        raise RuntimeError("OpenSTA executable 'sta' or 'opensta' not found in PATH.")
    location.mkdir(parents=True, exist_ok=True)
    netlist = location / "mapped.v"
    ys = location / "synth.ys"
    ys.write_text(yosys_script(src, design, lib, netlist))
    synth_log = execute([yosys, "-s", str(ys)], location / "yosys.log")
    if not netlist.is_file():
        raise RuntimeError("Yosys did not produce a mapped Verilog netlist")
    area = parse_area(synth_log)
    if area is None:
        raise RuntimeError("Could not parse mapped cell area; inspect yosys.log")
    sta_script = location / "timing.tcl"
    sta_script.write_text(opensta_script(design, lib, netlist, cfg))
    report = execute([sta, str(sta_script)], location / "timing.log")
    if re.search(r"(^|\n)\s*(?:Error:|STA-\d+.*error)", report, flags=re.I):
        raise RuntimeError("OpenSTA reported an error; inspect timing.log")
    timings = parse_timing(report)
    if timings["critical_startpoint"] is None or timings["critical_endpoint"] is None:
        raise RuntimeError("No constrained critical path was reported: inspect timing.log")
    result = {**timings, "area": area, "library_path": str(lib),
              "clock_period_ns": cfg["clock_period_ns"],
              "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    (location / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def do_baseline(args):
    designs = [args.design] if args.design != "all" else config()["designs"]
    for design in designs:
        original = ROOT / "rtl" / f"{design}.v"
        print(f"Measuring {design} baseline...")
        m = measure(design, original, ROOT / "results/baseline" / design)
        print(f"  worst setup slack={m['worst_slack_ns']} ns; area={m['area']}")


def baseline_metrics(design):
    f = ROOT / "results/baseline" / design / "metrics.json"
    if not f.exists():
        raise RuntimeError(f"Missing baseline for {design}. Run 'baseline --design {design}' first.")
    return json.loads(f.read_text())


def common_prompt(design, source):
    return textwrap.dedent(f"""\
        You are optimizing a synthesizable Verilog module for setup timing after
        mapping with Yosys/ABC to a fixed standard-cell library. Return ONLY
        complete Verilog source code, with the same top-level module name {design}.

        Requirements for ALL conditions:
        - Preserve every port, width, polarity, function and exact cycle latency.
        - No added pipeline stages, retiming, clock gating or interface changes.
        - No black boxes, latches, pragmas that bypass synthesis, or test-only hacks.
        - Prefer meaningful architectural transformations (carry structure,
          comparison architecture, balancing selection/count networks) over
          cosmetic refactoring. ABC may normalize superficial code changes.
        - Do not assume the transformation is better: final judgment comes
          from formal equivalence and mapped timing/area measurements.
        - Output a SINGLE entire Verilog module with no Markdown fences.

        ORIGINAL VERILOG:
        {source.strip()}
        """)


def prompt_for(design, condition):
    if design not in DESIGNS or condition not in "ABC" or len(condition) != 1:
        raise ValueError("Unsupported design/condition")
    src = (ROOT / "rtl" / f"{design}.v").read_text()
    base = common_prompt(design, src)
    if condition == "A":
        return base + "\nCONDITION A: Use only source code above. No measured feedback is provided.\n"
    metrics = baseline_metrics(design)
    summary = (f"\nBASELINE AGGREGATE FEEDBACK:\n"
               f"Worst setup slack: {metrics['worst_slack_ns']} ns\n"
               f"Worst negative slack (clipped to <= 0): {metrics['wns_ns']} ns\n"
               f"Critical-path arrival time: {metrics['critical_path_delay_ns']} ns\n")
    if condition == "B":
        return base + summary + "\nCONDITION B: Only the above aggregate metrics are supplied.\n"
    report_path = ROOT / "results/baseline" / design / "timing.log"
    report = report_path.read_text()
    # Keep first timing path detail and tool context, not every potential path.
    section = report.split("Startpoint:", 1)
    if len(section) < 2:
        raise RuntimeError("Critical path not found in timing report; cannot create C prompt")
    detail = "Startpoint:" + section[1].split("Startpoint:", 1)[0]
    detail = "\n".join(detail.splitlines()[:100])
    return (base + summary + "\nFINE-GRAINED CRITICAL-PATH FEEDBACK:\n" + detail
            + "\n\nCONDITION C: Identify the structural cause of this measured critical path.\n")


def do_prompts(args):
    designs = [args.design] if args.design != "all" else config()["designs"]
    for design in designs:
        for condition in "ABC":
            path = ROOT / "generated/prompts" / design / f"{condition}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(prompt_for(design, condition))
            print(path.relative_to(ROOT))


def eqy_check(design, candidate, location):
    eqy = require_command("eqy")
    gold = ROOT / "rtl" / f"{design}.v"
    location.mkdir(parents=True, exist_ok=True)
    file = location / "equivalence.eqy"
    file.write_text(textwrap.dedent(f"""\
        [options]
        splitnets on

        [gold]
        read_verilog {path_for_script(gold)}
        prep -top {design}

        [gate]
        read_verilog {path_for_script(candidate)}
        prep -top {design}

        [strategy simple]
        use sat
        depth 10
        """))
    # Running EQY from the location keeps its work dir isolated per trial.
    try:
        cp = subprocess.run([eqy, str(file)], cwd=location, capture_output=True,
                            text=True, timeout=300)
    except subprocess.TimeoutExpired:
        (location / "eqy.log").write_text("Formal equivalence timed out after 300s\n")
        return "UNPROVEN"
    log = cp.stdout + "\n[STDERR]\n" + cp.stderr
    (location / "eqy.log").write_text(log)
    return "PASS" if cp.returncode == 0 and "Successfully proved designs equivalent" in log else "UNPROVEN"


def safe_candidate(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise RuntimeError(f"Candidate not found: {p}")
    if p.suffix.lower() not in {".v", ".sv"}:
        raise RuntimeError("Candidate must be a Verilog .v/.sv file")
    return p


def do_evaluate(args):
    if args.design not in DESIGNS:
        raise RuntimeError("Unknown design")
    if args.trial < 1:
        raise RuntimeError("Trial numbers must be >= 1")
    candidate = safe_candidate(args.candidate)
    base = baseline_metrics(args.design)
    trial_id = f"{args.design}_{args.condition}_trial{args.trial}"
    location = ROOT / "results" / "trials" / trial_id
    record_path = location / "record.json"
    if record_path.exists() and not args.overwrite:
        raise RuntimeError(f"Trial already recorded: {record_path}. Use --overwrite to rerun.")
    location.mkdir(parents=True, exist_ok=True)
    record = dict.fromkeys(CSV_FIELDS)
    record.update({"design": args.design, "condition": args.condition,
                   "trial": args.trial, "model": args.model or "manual-unknown",
                   "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                   "candidate_path": str(candidate), "baseline_worst_slack_ns": base["worst_slack_ns"],
                   "baseline_area": base["area"], "success": False, "status": "UNPROVEN"})
    try:
        equivalent = eqy_check(args.design, candidate, location)
        record["equivalence"] = equivalent
        if equivalent != "PASS":
            record["error"] = "Equivalence was not proved. Examine eqy.log; do not count as valid."
        else:
            metrics = measure(args.design, candidate, location / "measurement")
            record.update({k: metrics[k] for k in (
                "worst_slack_ns", "wns_ns", "critical_path_delay_ns", "area")})
            record["delta_slack_ns"] = round(metrics["worst_slack_ns"] - base["worst_slack_ns"], 8)
            record["area_change_pct"] = round((metrics["area"] / base["area"] - 1) * 100, 5)
            record["success"] = (record["delta_slack_ns"] > 0
                                 and record["area_change_pct"] <= config()["max_area_increase_pct"])
            record["status"] = "VALID"
    except RuntimeError as exc:
        record["error"] = str(exc)
        record["status"] = "ERROR"
        print(f"WARNING: {exc}", file=sys.stderr)
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    do_summary(None)
    print(f"Saved {record_path.relative_to(ROOT)}: {record['status']}; success={record['success']}")


def do_summary(_args):
    rows = []
    for file in sorted((ROOT / "results/trials").glob("*/record.json")):
        rows.append(json.loads(file.read_text()))
    outfile = ROOT / "results/results.csv"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in CSV_FIELDS})
    groups = defaultdict(list)
    for row in rows:
        groups[(row["design"], row["condition"])].append(row)
    lines = ["# Experimental results (generated from actual trial records)", "",
             "All trial results originate from the `evaluate` command. Blank = not measured.", "",
             "| Design | Condition | Trials | EQY passes | Valid improvements | Best delta slack (ns) |",
             "|---|---|---:|---:|---:|---:|"]
    for (design, condition), records in sorted(groups.items()):
        good = [r for r in records if r.get("status") == "VALID"]
        wins = [r for r in good if r.get("success")]
        best = max((r["delta_slack_ns"] for r in good), default=None)
        lines.append(f"| {design} | {condition} | {len(records)} | {len(good)} | {len(wins)} | "
                     f"{best if best is not None else '—'} |")
    if not rows:
        lines.append("| No trials yet | — | 0 | 0 | 0 | — |")
    lines += ["", "WNS is `min(0, worst setup slack)`; delta is computed using the raw worst slack.",
              "Success means equivalent, delta worst slack > 0, and area overhead within the configured budget.",
              "These are mapped cell estimates and pre-layout timing, not post-route PPA.", ""]
    (ROOT / "results/summary.md").write_text("\n".join(lines))
    print(f"Wrote {outfile.relative_to(ROOT)} and results/summary.md ({len(rows)} trials)")


def do_doctor(_args):
    print("EDA dependencies:")
    for cmd in ("yosys", "sta", "opensta", "eqy", "iverilog", "python3"):
        print(f"  {cmd:12} {shutil.which(cmd) or 'NOT INSTALLED'}")
    try:
        print("Liberty:       ", library_path(config()))
    except RuntimeError as exc:
        print("Liberty:        NOT INSTALLED (run get_nangate45.sh)")
    print("Python stdlib:  ready")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("baseline", help="Map and time original RTL with fixed library")
    b.add_argument("--design", choices=["all", *DESIGNS], default="all")
    b.set_defaults(fn=do_baseline)
    c = sub.add_parser("prompts", help="Create A/B/C prompts from REAL baselines")
    c.add_argument("--design", choices=["all", *DESIGNS], default="all")
    c.set_defaults(fn=do_prompts)
    e = sub.add_parser("evaluate", help="Formal check then map/time one LLM candidate")
    e.add_argument("--design", choices=DESIGNS, required=True)
    e.add_argument("--condition", choices=list("ABC"), required=True)
    e.add_argument("--trial", type=int, required=True)
    e.add_argument("--candidate", required=True)
    e.add_argument("--model", help="Record the exact LLM model for reproducibility")
    e.add_argument("--overwrite", action="store_true")
    e.set_defaults(fn=do_evaluate)
    s = sub.add_parser("summary", help="Regenerate comparison CSV and Markdown from trial records")
    s.set_defaults(fn=do_summary)
    d = sub.add_parser("doctor", help="Report available tools and library")
    d.set_defaults(fn=do_doctor)
    args = p.parse_args()
    try:
        args.fn(args)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
