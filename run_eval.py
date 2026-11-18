"""Ship-gate eval: did a prompt change help, or did it just move within the agent's own noise?

Runs two versions of a classification agent on the same cases, several times each,
so we can separate a real improvement from run-to-run randomness.

Runs on your machine, with your own Anthropic key. It calls only api.anthropic.com.
It reads data/cases.json. It does not touch any other website.

  export ANTHROPIC_API_KEY=sk-...          # your key
  export ANTHROPIC_MODEL=<your model id>   # the model string your account uses
  python3 run_eval.py                      # ~230 calls, a few dollars

Output: data/results.json  (raw per-call records).
It does not resume: each run starts data/results.json fresh, overwriting the previous file
once the first progress save happens (after 10 calls).
Each record includes stop_reason, cut_off (stop_reason == "max_tokens") and tail
(last 120 characters of the reply) so truncated answers can be told apart from wrong ones.
"""
import json, os, re, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "data", "cases.json")
OUT = os.path.join(HERE, "data", "results.json")
RUNS = int(os.environ.get("EVAL_RUNS", "5"))      # repeats per version, to see the noise
TEMP = float(os.environ.get("EVAL_TEMP", "0.7"))  # nonzero so reruns actually vary
KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("ANTHROPIC_MODEL")

# Two versions of the same agent. B is the kind of tweak an engineer ships hoping to help.
SYSTEM = "You are a customs classification assistant. You classify a product under the US Harmonized Tariff Schedule (HTS)."
VERSIONS = {
    "A_base": "Give the single most appropriate 10-digit HTS code for the product below.",
    "B_change": ("Give the single most appropriate 10-digit HTS code for the product below. "
                 "Work through the General Rules of Interpretation in order (GRI 1 first) before you decide."),
}
TAIL = "\n\nEnd your reply with a final line in exactly this format:\nHTS: 0000.00.00.00"

CODE = re.compile(r"HTS:\s*(\d{4}(?:\.\d{2}){1,3})")


def call(prompt):
    body = json.dumps({
        "model": MODEL, "max_tokens": 2500,  # temperature omitted: rejected by this model (400)
        "thinking": {"type": "between_tools"},  # this model's "off" setting; no tools here, so no thinking
        "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
    return text, data.get("stop_reason")


def parse(text):
    hits = CODE.findall(text or "")
    return hits[-1] if hits else None


def main():
    if not KEY or not MODEL:
        sys.exit("Set ANTHROPIC_API_KEY and ANTHROPIC_MODEL first. "
                 "ANTHROPIC_MODEL is the model id your account uses for the API.")
    cases = json.load(open(CASES))
    results = []
    total = len(cases) * len(VERSIONS) * RUNS
    n = 0
    for run in range(1, RUNS + 1):
        for vname, vinstr in VERSIONS.items():
            for c in cases:
                prompt = f"{vinstr}\n\nProduct:\n{c['facts']}{TAIL}"
                text, stop, err = None, None, None
                for attempt in range(3):
                    try:
                        text, stop = call(prompt); break
                    except urllib.error.HTTPError as e:
                        err = f"{e.code} {e.read().decode()[:200]}"
                        time.sleep(3 * (attempt + 1))
                    except Exception as e:
                        err = str(e); time.sleep(3 * (attempt + 1))
                results.append({"run": run, "version": vname, "id": c["id"],
                                "gold_hts": c["gold_hts"], "pred_hts": parse(text),
                                "error": err, "stop_reason": stop,
                                "cut_off": stop == "max_tokens",
                                "tail": text[-120:] if text else None})
                n += 1
                if n % 10 == 0 or n == total:
                    print(f"  {n}/{total}")
                    json.dump(results, open(OUT, "w"), indent=1)  # save as we go (fresh each run; no resume)
    json.dump(results, open(OUT, "w"), indent=1)
    ok = sum(1 for r in results if r["pred_hts"])
    print(f"done. {len(results)} calls, {ok} returned a code -> {OUT}")


if __name__ == "__main__":
    main()
