# pallet-ship-gate

Is a change to an AI agent a real improvement, or did it land inside the agent's own run-to-run noise?

`index.html` is a one-page write-up. It runs two versions of the same customs-classification agent five times each on the same 22 cases, then compares the gain from the change against how much each version disagrees with itself between reruns. Every point drawn on the page is one of the 220 real calls in `data/results.json`.

Headline result, graded on the 4-digit tariff heading: Version A averages 36.4%, Version B 40.9%. The gap is +4.5 points, but each version swings 9 to 14 points between reruns of identical input, and a paired bootstrap 95% interval on the gap runs from -2.7 to +13.6. It crosses zero, so this change would not clear the gate.

## Data

- `data/cases.json`: 22 classification cases built from revised rulings published in the 2026 CBP Customs Bulletins. Each case keeps the product description as the input and the final tariff code as the gold answer.
- `data/results.json`: one record per call (version, run, predicted code, gold code, stop reason, last 120 characters of the reply).

The text the agent sees contains no ruling numbers. The `id` field is the original ruling number, kept so every gold answer can be checked against its bulletin. Two product descriptions still name a brand (H330361, H314018).

One case was dropped after the run: H328910's description names its own answer heading, so it was correct by construction.

## Reproduce

Requires Python 3 and nothing else (standard library only). The script calls only `api.anthropic.com`.

```sh
export ANTHROPIC_API_KEY=...        # your own key, read from the environment
export ANTHROPIC_MODEL=...          # the model id to evaluate
python3 run_eval.py                 # 22 cases x 2 versions x 5 runs = 220 calls
```

It overwrites `data/results.json` with fresh results. Sampling is left at the model's default, so a rerun will not match these numbers exactly. That variation is the point.

## Notes

Independent research on public CBP documents. Not affiliated with or endorsed by U.S. Customs and Border Protection. Small and single: 22 cases, one frontier model, one task family. It sizes an effect; it does not certify an agent.
