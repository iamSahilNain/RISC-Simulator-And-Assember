"""Differential execution: project simulator versus Unicorn on the same encoding."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import emu, llvm
from .conformance import to_reference_syntax
from .gen import Program
from .project import ABI, DATA_BASE, simulate


@dataclass
class Verdict:
    kind: str          # "agree" | "diverge" | "sim-crash" | "sim-timeout" | "ref-fault" | "ref-limit" | "both-limit" | "encode-error"
    detail: str = ""
    reg_diffs: list[tuple[str, int, int]] = field(default_factory=list)
    mem_diffs: list[tuple[int, int, int]] = field(default_factory=list)


def encode_program(prog: Program) -> list[int] | None:
    words = llvm.encode([to_reference_syntax(l) for l in prog.lines])
    if any(w is None for w in words):
        return None
    return [w for w in words if w is not None]


def compare(prog: Program, sim_timeout: float = 10.0) -> Verdict:
    words = encode_program(prog)
    if words is None:
        return Verdict("encode-error", "llvm-mc rejected a generated line")
    ref = emu.run(words, prog.halt_index)
    sim = simulate(words, timeout=sim_timeout)
    if ref.status == "fault":
        return Verdict("ref-fault", ref.detail)
    if ref.status == "limit" and sim.status == "timeout":
        return Verdict("both-limit")
    if sim.status == "crash":
        return Verdict("sim-crash", sim.detail[-300:])
    if sim.status == "timeout":
        return Verdict("diverge", "simulator did not halt but the reference did")
    if ref.status == "limit":
        return Verdict("diverge", "reference did not halt but the simulator did")
    v = Verdict("agree")
    for i in range(1, 32):
        if sim.regs[i] != ref.regs[i]:
            v.reg_diffs.append((ABI[i], sim.regs[i], ref.regs[i]))
    for i, (a, b) in enumerate(zip(sim.mem, ref.mem)):
        if a != b:
            v.mem_diffs.append((DATA_BASE + 4 * i, a, b))
    if v.reg_diffs or v.mem_diffs:
        v.kind = "diverge"
        v.detail = ", ".join(f"{r}: sim {s:#010x} ref {t:#010x}" for r, s, t in v.reg_diffs[:4])
        if v.mem_diffs:
            v.detail += f"; {len(v.mem_diffs)} memory words differ"
    return v
