from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .conformance import check_lines, random_lines
from .diffexec import compare
from .gen import program
from .reduce import reduce


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="verify")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("gen"); p.add_argument("--seed", type=int, default=1)
    p = sub.add_parser("encode", help="encoding conformance campaign")
    p.add_argument("-n", type=int, default=500); p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", default="results/encode.json")
    p = sub.add_parser("exec", help="differential execution campaign")
    p.add_argument("-n", type=int, default=200); p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", default="results/exec.json"); p.add_argument("--reduce", action="store_true")
    p = sub.add_parser("one", help="compare one program file (assembly)"); p.add_argument("path")
    a = ap.parse_args(argv)

    if a.cmd == "gen":
        sys.stdout.write(program(a.seed).source); return 0

    if a.cmd == "encode":
        lines = random_lines(a.seed, a.n)
        checked, mism = check_lines(lines)
        by_op = {}
        for m in mism:
            by_op.setdefault(m.line.split(" ")[0], []).append(m)
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump({"n": a.n, "seed": a.seed, "checked": checked, "mismatches": len(mism),
                   "by_op": {k: len(v) for k, v in by_op.items()},
                   "examples": [{"line": m.line, "project": m.project, "reference": m.reference, "note": m.note}
                                for m in mism[:60]]}, open(a.out, "w"), indent=2)
        print(f"lines {a.n}, assembled by project {checked}, mismatches {len(mism)}")
        for k, v in sorted(by_op.items(), key=lambda kv: -len(kv[1])):
            ex = v[0]
            print(f"  {k:6s} {len(v):4d}  e.g. {ex.line!r}: project {ex.project if ex.project is None else format(ex.project, '#010x')} "
                  f"reference {ex.reference if ex.reference is None else format(ex.reference, '#010x')} {ex.note}")
        return 0

    if a.cmd == "exec":
        counts = {}
        cands = []
        t0 = time.time()
        for i in range(a.n):
            prog = program(a.seed + i)
            v = compare(prog)
            counts[v.kind] = counts.get(v.kind, 0) + 1
            if v.kind in ("diverge", "sim-crash"):
                rec = {"seed": prog.seed, "kind": v.kind, "detail": v.detail, "source": prog.source}
                if a.reduce and v.kind == "diverge":
                    r = reduce(prog)
                    rec["reduced"] = r.source
                    rec["reduced_detail"] = compare(r).detail
                cands.append(rec)
            if (i + 1) % 20 == 0:
                print(f"[{i + 1}/{a.n}] {counts}", file=sys.stderr, flush=True)
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump({"n": a.n, "seed": a.seed, "counts": counts, "seconds": round(time.time() - t0, 1),
                   "candidates": cands}, open(a.out, "w"), indent=2)
        print(json.dumps(counts))
        return 0

    if a.cmd == "one":
        lines = [l.strip() for l in open(a.path) if l.strip()]
        from .gen import Program
        v = compare(Program(lines, 0))
        print(v.kind, v.detail)
        for r, s, t in v.reg_diffs:
            print(f"  {r}: sim {s:#010x} ref {t:#010x}")
        for addr, s, t in v.mem_diffs[:10]:
            print(f"  mem {addr:#010x}: sim {s:#010x} ref {t:#010x}")
        return 0
    return 1
