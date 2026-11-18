import json, random, statistics as st

R = [r for r in json.load(open("data/results.json")) if r.get("pred_hts")]
H = lambda c: c[:4] if c else None
S = lambda c: c[:6] if c else None
ids = sorted({r["id"] for r in R})
runs = sorted({r["run"] for r in R})
N = len(ids)

def perrun(version, grade):
    key = H if grade == "heading" else S
    out = []
    for run in runs:
        rr = [r for r in R if r["version"] == version and r["run"] == run]
        out.append(sum(key(r["pred_hts"]) == key(r["gold_hts"]) for r in rr) / len(ids) * 100)
    return out

def case_acc(version, grade):
    key = H if grade == "heading" else S
    return {c: sum(key(r["pred_hts"]) == key(r["gold_hts"])
                   for r in R if r["version"] == version and r["id"] == c) / len(runs)
            for c in ids}

def noise_floor(grade):
    d = []
    for v in ("A_base", "B_change"):
        pr = perrun(v, grade)
        d += [abs(pr[i] - pr[j]) for i in range(len(pr)) for j in range(i + 1, len(pr))]
    return st.median(d), max(d)

def bootstrap(grade, seed=7, iters=10000):
    a, b = case_acc("A_base", grade), case_acc("B_change", grade)
    d = [b[c] - a[c] for c in ids]
    random.seed(seed)
    means = sorted(sum(random.choice(d) for _ in ids) / len(ids) * 100 for _ in range(iters))
    return sum(d) / len(d) * 100, means[int(iters * 0.025)], means[int(iters * 0.975)], sum(x <= 0 for x in means) / iters

print(f"cases: {N}   runs: {len(runs)}   calls: {len(R)}")
for grade in ("heading", "subheading"):
    A, B = perrun("A_base", grade), perrun("B_change", grade)
    gap, lo, hi, pw = bootstrap(grade)
    nm, nx = noise_floor(grade)
    ca_a, ca_b = case_acc("A_base", grade), case_acc("B_change", grade)
    print(f"\n[{grade}]")
    print(f"  A per-run {[round(x,1) for x in A]}  mean {sum(A)/len(A):.1f}")
    print(f"  B per-run {[round(x,1) for x in B]}  mean {sum(B)/len(B):.1f}")
    print(f"  gap +{gap:.1f}   95% CI {lo:.1f} to {hi:.1f}   P(B<=A) {pw:.2f}")
    print(f"  noise floor median {nm:.1f}, max {nx:.1f}")
    print(f"  flips across runs: A {sum(0<ca_a[c]<1 for c in ids)}, B {sum(0<ca_b[c]<1 for c in ids)} of {N}")
    print(f"  A worst run {round(min(A)/100*N)}/{N}   B best run {round(max(B)/100*N)}/{N}")
