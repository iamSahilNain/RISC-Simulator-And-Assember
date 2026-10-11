"""The harness must be proven against planted bugs, not only against passing runs."""
import pytest

from verify import diffexec, llvm
from verify.conformance import check_lines
from verify.diffexec import compare
from verify.emu import run as emu_run
from verify.gen import Program, program
from verify.project import HALT, SimResult, assemble, parse_trace, simulate

pytestmark = pytest.mark.skipif(llvm.llvm_mc_path() is None, reason="llvm-mc not installed")

STRAIGHT = ["addi a0,zero,5", "addi a1,zero,3", "add a2,a0,a1", HALT]


def test_reference_encoder_agrees_with_project_on_sample():
    checked, mism = check_lines(STRAIGHT[:-1])
    assert checked == 3 and mism == [], mism


def test_planted_encoding_bug_is_reported(monkeypatch):
    real = llvm.encode
    monkeypatch.setattr(llvm, "encode", lambda lines, timeout=30.0: [w ^ 1 if w is not None else None for w in real(lines, timeout)])
    checked, mism = check_lines(STRAIGHT[:-1])
    assert len(mism) == 3


def test_unicorn_runs_sample():
    words = llvm.encode(STRAIGHT)
    r = emu_run(words, 3)
    assert r.status == "halted" and r.regs[10] == 5 and r.regs[11] == 3 and r.regs[12] == 8 and r.regs[2] == 256


def test_project_simulator_runs_sample():
    words = llvm.encode(STRAIGHT)
    s = simulate(words)
    assert s.status == "halted" and s.regs[12] == 8


def test_compare_agrees_on_sample():
    assert compare(Program(STRAIGHT, 0)).kind == "agree"


def test_planted_simulator_bug_is_detected(monkeypatch):
    real = diffexec.simulate

    def bad(words, timeout=10.0):
        r = real(words, timeout)
        r.regs[12] ^= 0x10  # corrupt a2
        return r
    monkeypatch.setattr(diffexec, "simulate", bad)
    v = compare(Program(STRAIGHT, 0))
    assert v.kind == "diverge" and v.reg_diffs[0][0] == "a2"


def test_planted_memory_bug_is_detected(monkeypatch):
    real = diffexec.simulate

    def bad(words, timeout=10.0):
        r = real(words, timeout)
        r.mem[7] = 0xDEADBEEF
        return r
    monkeypatch.setattr(diffexec, "simulate", bad)
    v = compare(Program(STRAIGHT, 0))
    assert v.kind == "diverge" and v.mem_diffs and v.mem_diffs[0][0] == 0x10000 + 28


def test_trace_parser_reads_hex_not_decimal():
    text = ("Final Register State:\n-----\nPC = 12 (0x0000000c)\nzero =    0 (0x00000000)\n"
            "a0   = 4294967295 (0xffffffff)\n\nMemory State:\n-----\n0x00010004:0b00000000000000000000000000000111\n")
    r = parse_trace(text)
    assert r.pc == 12 and r.regs[10] == 0xFFFFFFFF and r.mem[1] == 7


@pytest.mark.parametrize("seed", range(1, 11))
def test_generated_programs_are_accepted_by_reference(seed):
    p = program(seed)
    words = diffexec.encode_program(p)
    assert words is not None and len(words) == len(p.lines)
    r = emu_run(words, p.halt_index)
    assert r.status == "halted", (r.status, r.detail)
