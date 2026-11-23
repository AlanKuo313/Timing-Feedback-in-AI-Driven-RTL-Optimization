# Timing Feedback for AI-Assisted RTL Optimization

## Research question
Does providing fine-grained *critical-path feedback* to an LLM yield greater **formally equivalent, mapped timing improvements** than (A) RTL alone or (B) RTL plus aggregate timing?

### What is implemented
- Four registered Verilog benchmark modules: 16-bit adder, unsigned comparator, highest-priority encoder, and population counter.
- Optional manual carry-select adder candidate for verification and timing-flow smoke tests (NOT part of A/B/C results).
- Automated Yosys + ABC technology mapping with the **same Liberty library** for original designs and candidates.
- OpenSTA-based constrained setup timing analysis and mapped standard-cell area reporting.
- EQY formal equivalence verification **before candidate timing is counted**.
- Standardized prompts for Conditions A (RTL), B (aggregate timing), C (detailed path feedback).
- Optional OpenAI Responses API script to obtain candidate Verilog; manual LLM use is also supported.
- Result records, CSV summary, regression/unit tests, and draft documents.

**Important:** The package contains NO fabricated timing or PPA numbers. It has not been verified using an installed EDA toolchain in the authoring environment. Python unit tests are separate from formal verification. Inspect and run all steps on your machine before using results in a submission.

## Setup: Windows with WSL Ubuntu

First, in **Administrator PowerShell**:

```powershell
wsl --install -d Ubuntu
```

In the new Ubuntu terminal, place and unzip this package under your Ubuntu home folder (avoid Windows paths if possible). To install Yosys/Icarus:

```bash
sudo apt update
sudo apt install -y yosys iverilog curl python3
```

Install OpenSTA (`sta`) and EQY (`eqy`) using OSS CAD Suite or your Linux distribution's packages; exact availability depends on platform. Recommended OSS CAD Suite: https://github.com/YosysHQ/oss-cad-suite-build (ensure its `bin` directory is on PATH). Confirm:

```bash
python3 scripts/project.py doctor
which yosys sta eqy iverilog
```

Fetch the research-grade Nangate45 timing library:

```bash
bash scripts/get_nangate45.sh
```

The download is ~6 MB and hosted by OpenROAD Flow Scripts. Review the library's license before redistribution. **No Liberty library is bundled.** Record its specific revision and checksum before beginning official experiments.

## Exact first steps

```bash
# 1. Verify the Python driver (no hardware tools needed)
python3 -m unittest discover -s tests -v

# 2. Optional: basic RTL simulation (requires iverilog)
bash scripts/run_smoke.sh

# 3. Create genuine mapped baseline results (requires yosys + sta + Liberty)
python3 scripts/project.py baseline --design adder16

# 4. Generate A/B/C prompts based on the actual adder timing report
python3 scripts/project.py prompts --design adder16
```

Read `generated/prompts/adder16/A.txt` etc. To manually generate a candidate, send one prompt to the **same LLM/version and same configuration** for each condition and save the complete Verilog module as a `.v` file (do not modify the prompt by hand between conditions). Track model ID and generation settings. Save two independent attempts for each condition.

```bash
# 5. Evaluate a manual carry-select example first (formal checking + mapped timing).
# This is a TOOL SMOKE TEST, not part of formal LLM results.
# Use condition A only for labeling the smoke test; do not mix with results CSV.
# See docs/EXPERIMENT_PROTOCOL.md for safe smoke-test commands.

# 6. Measure an actual LLM candidate after saving it to a file
python3 scripts/project.py evaluate \
  --design adder16 --condition A --trial 1 \
  --candidate generated/candidates/adder16/A/trial1.v \
  --model YOUR_EXACT_MODEL_ID

# 7. Summarize everything
python3 scripts/project.py summary
```

The evaluation command performs EQY first. If equivalence isn't proved, the candidate is **not** assigned measured timing as a valid optimization. Detailed logs are saved under `results/trials/`.

### Optional API candidate generation

Uses an external **billable** OpenAI Responses API request. No API request runs automatically, and ChatGPT subscription access doesn't imply API credit.

```bash
export OPENAI_API_KEY='your_API_key'
python3 scripts/generate_with_openai.py --design adder16 --condition A --trial 1 --model YOUR_API_MODEL_ID
```

Repeat for conditions B/C and trials. Do not print or commit your API key. The script writes Verilog plus model/usage metadata; you must then run the evaluation command.

## Metrics and fairness

- **Worst setup slack** (may be positive): directly comparable under fixed constraints.
- **WNS**: `min(0, worst setup slack)`; if all candidates have positive slack, compare raw worst slack instead of clipped WNS.
- **Area**: sum of mapped standard-cell areas from Yosys, not routed die area.
- **Successful candidate**: formal equivalence proven, worst setup slack strictly improved, area increase no more than a pre-registered 10% limit. Sensitivity analysis can change this limit, but it must be disclosed.
- Keep model/temperature/instructions/trials consistent, use the same RTL, timing library, mapping constraints, clock period, software versions and report parsing across A/B/C.
- OpenSTA is **pre-layout** analysis. No placement/routing, congestion, clock-tree or physical wire parasitics are modeled.
- The provided 0.50 ns clock, 0.02 ns uncertainty, and 0.05 ns IO constraints are experimental starting points; inspect that the critical path is genuinely constrained. Adjust only before trials, document adjustment, and regenerate all baselines.

## Directory guide

```text
rtl/                      four original designs
examples/                 manually authored known architectural candidate
config/experiment.json    experimental parameters
config/lib/               add the external Liberty file here
scripts/project.py        baseline -> prompts -> evaluate -> summary
scripts/generate_with_openai.py  optional billable LLM generation
scripts/run_smoke.sh      Icarus simulation of all four designs and manual adder example
testbench/                 HDL simulation testbench
tests/                     Python driver unit tests
generated/prompts/         A/B/C prompts AFTER baseline measurements
generated/candidates/      AI-generated Verilog candidates
results/                   real logs and result tables after run
docs/                      scope, protocol and progress-report drafts
```

## Not yet implemented

- No EDA toolchain installed in this workspace when the project was authored; hardware flow outputs have **not yet been produced**.
- No live LLM experiments or API calls were executed, so A/B/C comparisons cannot be claimed as observed.
- No manufacturing-level physical-design estimates, power measurements, or full sequential retiming equivalence.

For the academic submission, verify every claimed result, document division of work, report null results, include tool versions and the exact Liberty checksum, and replace any placeholder text in the draft report.

## Sources

- Yosys: https://github.com/YosysHQ/yosys
- OpenSTA: https://opensta.readthedocs.io/en/latest/Examples/
- EQY: https://yosyshq.readthedocs.io/projects/eqy/en/latest/
- Nangate45: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/tree/master/flow/platforms/nangate45
- OpenAI Responses API (optional): https://platform.openai.com/docs/api-reference/responses
