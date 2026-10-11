"""Random program generator for the project's RV32I subset.

Programs use numeric branch offsets (no labels), end with the project's halt
line, keep every load and store inside the 4 KB data region, and keep every
branch target inside the program. Loops use a reserved counter register that
the loop body never writes, so every loop terminates. The bonus instructions
(mul, rst, halt, rvrs) are non-standard and are not generated.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .project import ABI, HALT

R_OPS = ["add", "sub", "sll", "slt", "sltu", "xor", "srl", "or", "and"]
I_OPS = ["addi", "sltiu"]
B_OPS = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]

# registers the generator may write freely
GP = ["t0", "t1", "t2", "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "s2", "s3", "s4"]
BASE = "s11"      # holds 0x00010000 after the prologue
CNT = ["t5", "t6"]  # loop counters, never written by loop bodies
SCRATCH = "t4"    # auipc target for jalr


@dataclass
class Program:
    lines: list[str]
    seed: int

    @property
    def source(self) -> str:
        return "\n".join(self.lines) + "\n"

    @property
    def halt_index(self) -> int:
        return len(self.lines) - 1


class Gen:
    def __init__(self, seed: int, n: int = 24):
        self.rng = random.Random(seed)
        self.seed = seed
        self.n = n

    def reg(self) -> str:
        return self.rng.choice(GP)

    def src(self) -> str:
        return self.rng.choice(GP + ["zero", "sp", BASE])

    def imm12(self) -> int:
        return self.rng.choice([0, 1, -1, 2, 7, -8, 100, -100, 2047, -2048, self.rng.randint(-2048, 2047)])

    def arith(self) -> str:
        k = self.rng.random()
        if k < 0.45:
            op = self.rng.choice(R_OPS)
            return f"{op} {self.reg()},{self.src()},{self.src()}"
        if k < 0.75:
            op = self.rng.choice(I_OPS)
            return f"{op} {self.reg()},{self.src()},{self.imm12()}"
        if k < 0.85:
            v = self.rng.choice([0x1000, 0x7FFFF000, -0x80000000, 0x12345000, 0xFFFFF000 - (1 << 32), 0x10000])
            return f"lui {self.reg()},{v}"
        if k < 0.93:
            off = 4 * self.rng.randint(0, 511)
            return f"sw {self.reg()},{off}({BASE})"
        off = 4 * self.rng.randint(0, 511)
        return f"lw {self.reg()},{off}({BASE})"

    def generate(self) -> Program:
        rng = self.rng
        body: list[str] = []
        # prologue: data base and a few initial values, including negatives
        body.append(f"lui {BASE},65536")
        for r in rng.sample(GP, 4):
            body.append(f"addi {r},zero,{self.imm12()}")
        while len(body) < self.n:
            k = rng.random()
            if k < 0.70:
                body.append(self.arith())
            elif k < 0.85:
                # forward branch over 1..3 instructions
                skip = rng.randint(1, 3)
                op = rng.choice(B_OPS)
                body.append(f"{op} {self.src()},{self.src()},{4 * (skip + 1)}")
                for _ in range(skip):
                    body.append(self.arith())
            elif k < 0.95:
                # bounded loop: cnt = trips; body; addi cnt,cnt,-1; bne cnt,zero,back
                cnt = rng.choice(CNT)
                trips = rng.randint(1, 6)
                blen = rng.randint(1, 3)
                body.append(f"addi {cnt},zero,{trips}")
                for _ in range(blen):
                    body.append(self.arith())
                body.append(f"addi {cnt},{cnt},-1")
                body.append(f"bne {cnt},zero,{-4 * (blen + 1)}")
            else:
                # auipc + jalr skipping one instruction: target = pc(auipc) + 12
                body.append(f"auipc {SCRATCH},0")
                body.append(f"jalr ra,{SCRATCH},12")
                body.append(self.arith())
        # occasionally a jal over one instruction
        if rng.random() < 0.5:
            body.append("jal ra,8")
            body.append(self.arith())
        body.append(HALT)
        return Program(body, self.seed)


def program(seed: int, n: int = 24) -> Program:
    return Gen(seed, n).generate()
