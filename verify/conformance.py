"""Encoding conformance: project assembler versus llvm-mc, one instruction at a time.

The project's `lui`/`auipc` take a 32-bit value whose top 20 bits are used, while
the standard syntax takes the 20-bit immediate itself; the reference line is
rewritten accordingly so that only the encoding is compared, not the syntax.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import llvm
from .gen import B_OPS, I_OPS, R_OPS
from .project import ABI, HALT, assemble


@dataclass
class Mismatch:
    line: str
    project: int | None
    reference: int | None
    note: str = ""


def to_reference_syntax(line: str) -> str:
    op, _, rest = line.partition(" ")
    if op in ("lui", "auipc"):
        rd, val = rest.split(",")
        imm20 = (int(val) >> 12) & 0xFFFFF
        return f"{op} {rd},{imm20}"
    return line


def random_lines(seed: int, n: int) -> list[str]:
    rng = random.Random(seed)
    regs = ABI
    lines = []
    for _ in range(n):
        k = rng.random()
        if k < 0.3:
            lines.append(f"{rng.choice(R_OPS)} {rng.choice(regs)},{rng.choice(regs)},{rng.choice(regs)}")
        elif k < 0.5:
            lines.append(f"{rng.choice(I_OPS + ['jalr'])} {rng.choice(regs)},{rng.choice(regs)},{rng.randint(-2048, 2047)}")
        elif k < 0.6:
            lines.append(f"lw {rng.choice(regs)},{rng.randint(-2048, 2047)}({rng.choice(regs)})")
        elif k < 0.7:
            lines.append(f"sw {rng.choice(regs)},{rng.randint(-2048, 2047)}({rng.choice(regs)})")
        elif k < 0.85:
            lines.append(f"{rng.choice(B_OPS)} {rng.choice(regs)},{rng.choice(regs)},{2 * rng.randint(-2048, 2047)}")
        elif k < 0.93:
            lines.append(f"{rng.choice(['lui', 'auipc'])} {rng.choice(regs)},{rng.randint(-2**31, 2**31 - 1)}")
        else:
            lines.append(f"jal {rng.choice(regs)},{2 * rng.randint(-2**19, 2**19 - 1)}")
    return lines


def check_lines(lines: list[str]) -> tuple[int, list[Mismatch]]:
    """Assemble each line alone (plus the halt) with the project, encode with llvm-mc, compare."""
    ref = llvm.encode([to_reference_syntax(l) for l in lines])
    mismatches = []
    checked = 0
    for line, r in zip(lines, ref):
        a = assemble(line + "\n" + HALT + "\n")
        p = a.words[0] if a.ok and len(a.words) == 2 else None
        if a.ok and len(a.words) != 2:
            mismatches.append(Mismatch(line, None, r, f"project emitted {len(a.words) - 1} words for one instruction"))
            continue
        if not a.ok:
            mismatches.append(Mismatch(line, None, r, f"project rejected: {a.message[:120]}"))
            continue
        checked += 1
        if r is None:
            mismatches.append(Mismatch(line, p, None, "llvm-mc rejected the line"))
        elif p != r:
            mismatches.append(Mismatch(line, p, r))
    return checked, mismatches
