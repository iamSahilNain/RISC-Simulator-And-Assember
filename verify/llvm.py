"""Encode instructions with LLVM's RISC-V assembler (the reference encoder)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess

_CANDIDATES = ["/opt/homebrew/opt/llvm/bin/llvm-mc", "/usr/local/opt/llvm/bin/llvm-mc"]


def llvm_mc_path() -> str | None:
    env = os.environ.get("LLVM_MC")
    if env and os.path.exists(env):
        return env
    for c in _CANDIDATES:
        if os.path.exists(c):
            return c
    return shutil.which("llvm-mc")


_ENC = re.compile(r"encoding:\s*\[([0-9a-fx, ]+)\]")


def encode(lines: list[str], timeout: float = 30.0) -> list[int | None]:
    """Return one 32-bit word per input line (None where llvm-mc rejected the line).

    All lines go to llvm-mc in one call; if the count of encodings does not match
    (some line was rejected), fall back to one call per line.
    """
    mc = llvm_mc_path()
    if not mc:
        raise RuntimeError("llvm-mc not found; brew install llvm or set LLVM_MC")
    if not lines:
        return []
    p = subprocess.run([mc, "-triple=riscv32", "-show-encoding"], input="\n".join(lines) + "\n",
                       capture_output=True, text=True, timeout=timeout)
    encs = _ENC.findall(p.stdout or "")
    if p.returncode == 0 and len(encs) == len(lines):
        return [_word(e) for e in encs]
    out: list[int | None] = []
    for line in lines:
        q = subprocess.run([mc, "-triple=riscv32", "-show-encoding"], input=line + "\n",
                           capture_output=True, text=True, timeout=timeout)
        m = _ENC.search(q.stdout or "")
        out.append(_word(m.group(1)) if (q.returncode == 0 and m) else None)
    return out


def _word(enc: str) -> int | None:
    bs = [int(x.strip(), 16) for x in enc.split(",")]
    if len(bs) != 4:
        return None
    return bs[0] | (bs[1] << 8) | (bs[2] << 16) | (bs[3] << 24)
