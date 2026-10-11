# Verification results

All numbers come from `python -m verify encode` and `python -m verify exec` on
11 October 2026 (macOS arm64, Python 3.12, Homebrew LLVM 22.1.2 `llvm-mc`,
Unicorn 2.x). Raw outputs are the JSON files beside this file; reduced
failing programs are in `reduced_before.json`.

## Encoding conformance (project assembler vs `llvm-mc -triple=riscv32`)

| Run | Lines | Assembled by project | Bit-exact matches | Mismatches |
|---|---|---|---|---|
| before fixes (`encode_before.json`, seed 1) | 600 | 566 | 566 | 34, all `jal` (the assembler crashed with `NameError` on every `jal`) |
| after fixes (`encode_after.json`, seed 1) | 600 | 600 | 600 | 0 |
| after fixes (`encode_after_5000.json`, seed 7) | 5,000 | 5,000 | 5,000 | 0 |

## Differential execution (project simulator vs Unicorn, same LLVM encodings)

| Run | Programs | Agree | Diverge | Simulator crash |
|---|---|---|---|---|
| before fixes (`exec_before.json`, seeds 1000+) | 120 | 27 | 29 | 64 |
| after fixes (`exec_after.json`, same seeds) | 120 | 120 | 0 | 0 |
| after fixes (`exec_after_1000.json`, seeds 5000+) | 1,000 | 1,000 | 0 | 0 |

## Bugs found, with the evidence that found them

| # | Component | Bug | Found by | Minimal case |
|---|---|---|---|---|
| 1 | Assembler | `jal` read an undefined variable (`given_value`) and crashed on every use | encoding campaign: 34 of 34 `jal` lines rejected | `jal ra,8` |
| 2 | Assembler | J-type immediate bits packed in the wrong order (`imm[1]+imm[10:20]+imm[10]+imm[2:10]`) | encoding campaign after bug 1 was fixed: every non-trivial `jal` offset mismatched `llvm-mc` | `jal ra,-118734` |
| 3 | Assembler | blank lines counted toward label offsets but emit no code, so a blank line between a branch and its label shifted the target | label regression program (`loop:` with a blank line) diverged from Unicorn | 6-line program in the README |
| 4 | Assembler | `mul`, `rst`, `halt`, `rvrs` were encoded but never appended to the output | reading, confirmed by assembling a 5-line program that produced 4 words | `mul a2,a0,a1` |
| 5 | Simulator | `sltu` and `sltiu` passed a decimal string to a binary parser: `ValueError` crash whenever the register held a digit other than 0 or 1 | 64 of 120 programs crashed | `sltiu a1,a0,-8` with `a0 = 256` |
| 6 | Simulator | `sltiu` compared against the signed immediate instead of the sign-extended value as unsigned | reduced seeds 1006, 1021, 1022, 1033 | `sltiu a1,a0,-8` with `a0 = 0` (expected 1, got 0) |
| 7 | Simulator | `jalr` ignored `rs1` and jumped to `pc + imm` | reduced seeds 1004, 1014, 1028 | `auipc t4,0` / `jalr ra,t4,12` |
| 8 | Simulator | `slt`, `blt`, `bge` compared the stored unsigned values, so negative operands compared wrongly | divergences with `ref 0xffffff9c`-style negatives | `addi a0,zero,-100` / `slt a1,a0,zero` |
| 9 | Simulator | out-of-range or unaligned `lw`/`sw` raised `KeyError` (a traceback) instead of an `ERROR:` line | reading; now exits with `ERROR:` | `lw a0,2(s11)` |

Fixes are in the commit after the baseline. Every fix was re-checked by the
same campaigns, with the same seeds, and then by the larger runs above.
