"""Verification harness for the RISC-V assembler and simulator.

Two oracles:
  * encoding conformance: every instruction the assembler emits is compared,
    bit for bit, with LLVM's RISC-V assembler (llvm-mc -triple=riscv32);
  * differential execution: random programs are run on the project simulator
    and on the Unicorn CPU emulator (QEMU-derived) from the same initial state,
    and all 32 registers plus the 4 KB data region are compared at the halt.
Execution uses LLVM's encodings as the simulator's input, so an execution
divergence is a simulator bug and an encoding mismatch is an assembler bug;
the two cannot be confused.
"""
