"""Minimise a divergent program by deleting instructions (ddmin over lines).

Numeric branch and jump offsets are recomputed so that every surviving branch
still targets the instruction it targeted before, or the next survivor.
"""
from __future__ import annotations

from .diffexec import compare
from .gen import Program
from .project import HALT

_BR = {"beq", "bne", "blt", "bge", "bltu", "bgeu", "jal"}


def _retarget(lines: list[str], keep: list[int]) -> list[str]:
    """Return the kept lines with branch offsets fixed for the new indices."""
    n = len(lines)
    targets = {}
    for i, l in enumerate(lines):
        op = l.split(" ")[0]
        if op in _BR:
            off = int(l.rsplit(",", 1)[1])
            targets[i] = i + off // 4
    keep_set = sorted(keep)
    new_index = {old: new for new, old in enumerate(keep_set)}

    def nearest(t: int) -> int:
        for k in keep_set:
            if k >= t:
                return new_index[k]
        return new_index[keep_set[-1]]

    out = []
    for old in keep_set:
        l = lines[old]
        if old in targets:
            t = targets[old]
            if 0 <= t < n:
                nt = nearest(t)
                head = l.rsplit(",", 1)[0]
                l = f"{head},{4 * (nt - new_index[old])}"
        out.append(l)
    return out


def interesting(prog: Program) -> bool:
    return compare(prog).kind == "diverge"


def reduce(prog: Program, max_rounds: int = 50) -> Program:
    lines = list(prog.lines)
    assert lines[-1] == HALT
    chunk = max(1, (len(lines) - 1) // 2)
    rounds = 0
    while chunk >= 1 and rounds < max_rounds:
        rounds += 1
        i = 0
        progressed = False
        while i < len(lines) - 1:
            drop = set(range(i, min(i + chunk, len(lines) - 1)))
            keep = [k for k in range(len(lines)) if k not in drop]
            cand = Program(_retarget(lines, keep), prog.seed)
            if len(cand.lines) >= 2 and interesting(cand):
                lines = cand.lines
                progressed = True
            else:
                i += chunk
        if not progressed:
            chunk //= 2
    return Program(lines, prog.seed)
