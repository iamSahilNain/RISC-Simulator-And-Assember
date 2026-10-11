"""Run a program on the Unicorn RISC-V 32 emulator (the reference CPU)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .project import DATA_BASE, DATA_WORDS

CODE_BASE = 0x0
CODE_SIZE = 0x1000
DATA_SIZE = DATA_WORDS * 4
SP_INIT = 256


@dataclass
class EmuResult:
    status: str                      # "halted" | "limit" | "fault"
    regs: list[int] = field(default_factory=lambda: [0] * 32)
    mem: list[int] = field(default_factory=lambda: [0] * DATA_WORDS)
    pc: int = 0
    detail: str = ""


def run(words: list[int], halt_index: int, max_insns: int = 200_000, timeout_us: int = 5_000_000) -> EmuResult:
    from unicorn import Uc, UC_ARCH_RISCV, UC_MODE_RISCV32, UcError
    from unicorn.riscv_const import UC_RISCV_REG_PC, UC_RISCV_REG_X0

    code = b"".join((w & 0xFFFFFFFF).to_bytes(4, "little") for w in words)
    if len(code) > CODE_SIZE:
        return EmuResult("fault", detail="program too large")
    mu = Uc(UC_ARCH_RISCV, UC_MODE_RISCV32)
    mu.mem_map(CODE_BASE, CODE_SIZE)
    mu.mem_map(DATA_BASE, DATA_SIZE)
    mu.mem_write(CODE_BASE, code)
    mu.reg_write(UC_RISCV_REG_X0 + 2, SP_INIT)
    halt_addr = CODE_BASE + 4 * halt_index
    res = EmuResult("halted")
    try:
        mu.emu_start(CODE_BASE, halt_addr, timeout=timeout_us, count=max_insns)
    except UcError as e:
        res.status = "fault"
        res.detail = str(e)
    pc = mu.reg_read(UC_RISCV_REG_PC)
    res.pc = pc
    if res.status == "halted" and pc != halt_addr:
        res.status = "limit"
    res.regs = [mu.reg_read(UC_RISCV_REG_X0 + i) & 0xFFFFFFFF for i in range(32)]
    raw = mu.mem_read(DATA_BASE, DATA_SIZE)
    res.mem = [int.from_bytes(raw[4 * i:4 * i + 4], "little") for i in range(DATA_WORDS)]
    return res
