"""Run the project's own Assembler.py and Simulator.py and parse their output."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSEMBLER = os.path.join(ROOT, "Assembler.py")
SIMULATOR = os.path.join(ROOT, "Simulator.py")

ABI = ["zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
       "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"]
ABI_INDEX = {name: i for i, name in enumerate(ABI)}
HALT = "beq zero,zero,0"
HALT_WORD = 0x00000063
DATA_BASE = 0x00010000
DATA_WORDS = 1024


@dataclass
class AsmResult:
    ok: bool
    words: list[int] = field(default_factory=list)
    message: str = ""


@dataclass
class SimResult:
    status: str                       # "halted" | "timeout" | "crash"
    regs: list[int] = field(default_factory=lambda: [0] * 32)
    mem: list[int] = field(default_factory=lambda: [0] * DATA_WORDS)
    pc: int = 0
    detail: str = ""


def assemble(source: str, timeout: float = 20.0) -> AsmResult:
    with tempfile.TemporaryDirectory(prefix="rv_asm_") as wd:
        src = os.path.join(wd, "in.s")
        out = os.path.join(wd, "out.mc")
        with open(src, "w") as f:
            f.write(source if source.endswith("\n") else source + "\n")
        try:
            p = subprocess.run([sys.executable, ASSEMBLER, src, out], capture_output=True, text=True,
                               timeout=timeout, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return AsmResult(False, message="assembler timeout")
        text = (p.stdout or "") + (p.stderr or "")
        if "ERROR" in text or p.returncode != 0 or not os.path.exists(out):
            return AsmResult(False, message=text.strip()[-500:] or f"exit {p.returncode}")
        words = []
        with open(out) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if len(line) != 32 or set(line) - {"0", "1"}:
                    return AsmResult(False, message=f"bad output line: {line!r}")
                words.append(int(line, 2))
        return AsmResult(True, words=words)


def words_to_mc(words: list[int]) -> str:
    return "\n".join(format(w & 0xFFFFFFFF, "032b") for w in words) + "\n"


_REG_LINE = re.compile(r"^\s*([a-z0-9]+)\s*=\s*-?\d+\s*\(0x([0-9a-f]{8})\)\s*$")
_PC_LINE = re.compile(r"^PC = (\d+) \(0x[0-9a-f]{8}\)")
_MEM_LINE = re.compile(r"^0x([0-9a-fA-F]+):0b([01]{32})$")


def simulate(words: list[int], timeout: float = 10.0) -> SimResult:
    with tempfile.TemporaryDirectory(prefix="rv_sim_") as wd:
        mc = os.path.join(wd, "in.mc")
        out = os.path.join(wd, "out.txt")
        with open(mc, "w") as f:
            f.write(words_to_mc(words))
        try:
            p = subprocess.run([sys.executable, SIMULATOR, mc, out], capture_output=True, text=True,
                               timeout=timeout, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return SimResult("timeout")
        if p.returncode != 0:
            return SimResult("crash", detail=(p.stderr or "")[-800:])
        if not os.path.exists(out):
            return SimResult("crash", detail="no output file")
        return parse_trace(open(out).read())


def parse_trace(text: str) -> SimResult:
    res = SimResult("halted")
    if "Final Register State:" not in text:
        return SimResult("crash", detail="no final state in trace")
    final = text.split("Final Register State:", 1)[1]
    regs_part, _, mem_part = final.partition("Memory State:")
    for line in regs_part.splitlines():
        m = _PC_LINE.match(line)
        if m:
            res.pc = int(m.group(1))
            continue
        m = _REG_LINE.match(line)
        if m and m.group(1) in ABI_INDEX:
            res.regs[ABI_INDEX[m.group(1)]] = int(m.group(2), 16)
    for line in mem_part.splitlines():
        m = _MEM_LINE.match(line.strip())
        if m:
            addr = int(m.group(1), 16)
            idx = (addr - DATA_BASE) // 4
            if 0 <= idx < DATA_WORDS:
                res.mem[idx] = int(m.group(2), 2)
    return res
