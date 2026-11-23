#!/usr/bin/env python3
"""Optional OpenAI Responses API generation. Requires OPENAI_API_KEY and an API-enabled model.

Cost is incurred by this script when called; check pricing first. Never run in a loop
unintentionally. The script DOES NOT certify correctness of any generated design.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def extract_text(response):
    text = []
    for item in response.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                text.append(part.get("text", ""))
    return "\n".join(text).strip()


def strip_fences(text):
    match = re.fullmatch(r"\s*```(?:verilog|systemverilog|sv|v)?\s*\n(.*?)\n```\s*", text, re.I | re.S)
    return match.group(1).strip() if match else text.strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--design", choices=["adder16", "comparator16", "priority_encoder16", "popcount16"], required=True)
    p.add_argument("--condition", choices=list("ABC"), required=True)
    p.add_argument("--trial", type=int, required=True)
    p.add_argument("--model", required=True, help="Exact model ID; keep identical across all A/B/C trials")
    args = p.parse_args()
    if args.trial < 1:
        p.error("--trial must be positive")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        p.error("Set OPENAI_API_KEY to your API key")
    prompt_file = ROOT / "generated/prompts" / args.design / f"{args.condition}.txt"
    if not prompt_file.is_file():
        p.error(f"Missing prompt: {prompt_file}. Run project.py prompts first.")
    output_dir = ROOT / "generated/candidates" / args.design / args.condition
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = output_dir / f"trial{args.trial}.v"
    metadata = output_dir / f"trial{args.trial}.json"
    if candidate.exists() or metadata.exists():
        p.error("Trial output already exists; use a new trial number (avoid accidental billing)")
    prompt = prompt_file.read_text()
    payload = json.dumps({"model": args.model, "input": prompt}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    print("Sending one API request (this may be billed)...")
    try:
        with urllib.request.urlopen(request, timeout=180) as handle:
            data = json.loads(handle.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"API error HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:700]}") from exc
    text = strip_fences(extract_text(data))
    if "module " not in text or "endmodule" not in text:
        raise SystemExit("Response was not clearly Verilog; nothing saved. Check model/output.")
    candidate.write_text(text + "\n")
    metadata.write_text(json.dumps({
        "model": args.model, "condition": args.condition, "trial": args.trial,
        "design": args.design, "response_id": data.get("id"),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "usage": data.get("usage"),
    }, indent=2) + "\n")
    print(f"Candidate written: {candidate.relative_to(ROOT)}")
    print("IMPORTANT: still run EQY and OpenSTA via project.py evaluate")


if __name__ == "__main__":
    main()
