# Experimental Protocol: Register Before Running Official Trials

## Hypothesis
Detailed critical-path feedback (Condition C) increases the frequency and magnitude
of *equivalent* RTL timing improvements compared with code-only (A) and aggregate
feedback (B) under matched synthesis/timing conditions.

## Scope
Four small synthesizable designs, 3 conditions per design, 2 independent
attempts per condition, total 24 AI-generated candidates. All candidate RTL must
preserve exact module ports, widths and cycle latency. No retiming or latency
changes. This is pre-layout timing, not physical design.

## Before LLM experiments

1. Choose the Nangate45 typical Liberty file (or another fixed compatible library).
   Record the exact commit/revision and SHA-256 hash of the file:
   `sha256sum config/lib/NangateOpenCellLibrary_typical.lib`
2. Freeze `config/experiment.json` and record tool versions:
   `yosys -V`, `sta -version` or `sta -help`, `eqy --version` (use equivalent flags
   accepted by your installed versions).
3. Run `python3 -m unittest discover -s tests -v`.
4. Run `bash scripts/run_smoke.sh` for the original and hand-written alternate
   adder. This checks simulated arithmetic behavior, but NOT sequential formal proof.
5. Generate real baseline mapped results:
   `python3 scripts/project.py baseline --design all`.
6. Test the full formal/timing stack on the manually written alternate adder:
   `python3 scripts/manual_smoke.py`. This MUST NOT be counted as an A/B/C result.
7. Inspect each `results/baseline/<design>/timing.log` and verify constrained
   startpoint and endpoint and believable mapped area. Failures must be fixed
   BEFORE comparing LLM conditions.
8. Generate actual prompts: `python3 scripts/project.py prompts --design all`.
   Prompts for B/C must not be fabricated and must be based on measured baselines.

## Run the controlled experiment

- For each of the four designs and all three conditions A/B/C, generate TWO
  independent candidate Verilog modules with one consistent LLM model/version.
- Recommended schedule: interleave A/B/C attempts per design to avoid
  chronological bias; prevent one trial's output from influencing another.
- Freeze generation settings and request only complete RTL, not an explanation.
  The prompt generator ensures the task instructions are identical.
- Save AI responses to `generated/candidates/DESIGN/CONDITION/trialN.v`.
- Optional: the Responses API script generates one candidate per invocation,
  using a billable external API call and `OPENAI_API_KEY`.
- Check formally, synthesize, and record with:

  ```bash
  python3 scripts/project.py evaluate --design adder16 --condition A \
    --trial 1 --candidate generated/candidates/adder16/A/trial1.v \
    --model YOUR_EXACT_MODEL_ID
  ```

- Inspect trial logs. Equivalence PASS is compulsory for valid timing.
- Failed proofs and malformed code remain in the dataset; never discard them
  or secretly replace them with successful attempts.

## Metrics

- Primary: worst setup slack (ns), relative to the original mapped design.
- WNS (clipped): min(0, worst setup slack). Both are saved because designs
  that already meet timing can improve positive slack while WNS stays zero.
- Secondary: critical-path data arrival time, cell area, EQY proof rate,
  valid improvement rate, area overhead, attempts per improvement.
- Pre-register a 10% mapped-area increase budget. Success means equivalence
  PASS + positive improvement in raw worst setup slack + area overhead <=10%.
- Report every candidate, plus per-design maxima and success rates, not only
  the single best result.

## Threats to validity

- ABC may optimize away the RTL transformations: no gain is a legitimate result.
- Synthesized timing with ideal/interpreted interconnect is not routed chip
  timing; pre-layout results cannot be presented as post-placement PPA.
- A common prompt without timing feedback can still discover architecture
  changes from model knowledge. This is intentional for a clean A/B/C comparison.
- Small sample size: interpret differences descriptively, avoid claiming
  statistically generalizable superiority.
- Equivalence solver may time out. UNPROVEN is not PASS, but is not automatically
  functional incorrectness either. Count and describe separately.
- Freeze parameters before comparing trials; if tool/library/constraints change,
  rerun ALL baselines and candidates so results remain comparable.

## Before handing in

- Confirm both teammates independently reviewed verifiability.
- Cite the RTL design source if it is not originally written by the team.
- Include exact versions, environment, prompt strings, generation settings,
  EQY logs and a real results table.
- Explain which architectural transformations (e.g. adder carry selection)
  survived or were removed by ABC mapping, if you can establish this from netlists.
- Clearly report any incomplete tasks rather than inventing measurements.
