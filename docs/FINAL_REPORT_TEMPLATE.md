# Final Report Template — DO NOT SUBMIT WITH EMPTY/INVENTED RESULTS

## Title
Evaluating the Impact of Fine-Grained Timing Feedback on AI-Assisted RTL Optimization

## 1. Research question
Does critical-path feedback improve formally equivalent, pre-layout RTL timing
beyond code-only and aggregate timing feedback?

## 2. Experimental setup
- Exact RTL benchmark source/parameterization: [list, cite any sources]
- Exact tool versions and platform: [fill]
- Liberty cell library file/revision/SHA-256: [fill]
- Clock period, input/output delay, clock uncertainty: [fill]
- Model version and prompt-generation settings: [fill]
- Number of candidates per condition: [fill]
- Equivalence procedure: EQY + SAT, describe settings and any timeouts.

## 3. Results
Insert `results/results.csv` and `results/summary.md` generated after REAL trials.

### Table 1 — Per-design results
| Design | Baseline slack | Best A delta | Best B delta | Best C delta | Equivalent A/B/C | Area changes |
|---|---|---|---|---|---|---|
| adder16 | TBD | TBD | TBD | TBD | TBD | TBD |
| comparator16 | TBD | TBD | TBD | TBD | TBD | TBD |
| priority_encoder16 | TBD | TBD | TBD | TBD | TBD | TBD |
| popcount16 | TBD | TBD | TBD | TBD | TBD | TBD |

## 4. Analysis
Discuss how feedback level affected outcomes, not just how many lines changed.
Investigate whether ABC erased proposed structural changes, using mapped
netlist and cell results where possible. Note changes in critical path.

## 5. Limitations
Small module set, limited trial count, pre-layout timing vs. routed-chip PPA,
possible library/constraint sensitivity, and verification-solver timeouts.

## 6. Conclusion
Answer the research question even if Condition C provided no advantage.
Do not claim AI beats ABC or that detailed timing is universally better.

## 7. Reproducibility appendix
Exact source, code hash, prompt text, candidate code, logs, output tables.
