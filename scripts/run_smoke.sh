#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v iverilog >/dev/null || { echo 'Install iverilog to run RTL simulations' >&2; exit 1; }
command -v vvp >/dev/null || { echo 'Install vvp to run RTL simulations' >&2; exit 1; }
mkdir -p results/smoke
for design in adder16 comparator16 priority_encoder16 popcount16; do
    iverilog -g2012 -s "tb_$design" -o "results/smoke/$design.vvp" "rtl/$design.v" "testbench/tb_$design.v"
    vvp "results/smoke/$design.vvp"
done
# Manually authored candidate, *not an A/B/C LLM trial*.
iverilog -g2012 -s tb_adder16 -o results/smoke/carry_select.vvp examples/adder16_carry_select.v testbench/tb_adder16.v
vvp results/smoke/carry_select.vvp
