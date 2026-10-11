# RISC-V Assembler & Simulator — Implementation Reference

A web-based RISC-V (RV32I subset) assembler and simulator. Users write assembly in a
browser editor, the backend assembles it to 32-bit binary machine code and simulates
execution, returning a register/memory trace. There is also a reverse path that
disassembles pasted machine code back to assembly.

## System overview

```
Browser (templates/index.html)
  │  POST /assemble  { code: "<assembly or machine code>" }
  │  POST /simulate  { code: "<machine code>" }
  ▼
Flask app (app.py)
  │  writes temp files, spawns subprocesses (5s timeout each)
  ├──► python3 Assembler.py <input.s> <output.mc>     assembly → binary strings
  └──► python3 Simulator.py <input.mc> <output.txt>   binary strings → execution trace
```

The three Python components communicate **only through files and stdout text** — there
are no shared modules or imports between them. Machine code is represented throughout
as 32-character ASCII strings of `0`/`1`, one instruction per line (not actual binary).

---

## 1. Assembler (`Assembler.py`)

A single top-level script (no functions/classes for the encoding logic). Invoked as
`python3 Assembler.py <input.s> <output.mc>`.

### Supported instruction set

| Type | Instructions | Encoding notes |
|------|--------------|----------------|
| R | `add sub sll slt sltu xor srl or and` | opcode `0110011`; funct7 `0100000` for sub, else zeros |
| I | `lw addi sltiu jalr` | per-instruction opcode+funct3 table |
| S | `sw` | opcode `0100011` |
| B | `beq bne blt bge bltu bgeu` | opcode `1100011`; label or numeric offset |
| U | `lui auipc` | opcodes `0110111` / `0010111` |
| J | `jal` | opcode `1101111`; label or numeric offset |
| Bonus (non-standard) | `mul rst halt rvrs` | custom opcode `1111111`, funct3 000/001/010/011 |

### Syntax rules (strict)

- Exactly one space between mnemonic and operands; operands comma-separated with **no
  spaces** (`add a0,a1,a2`). Any other whitespace split → "Invalid Instruction".
- Only ABI register names (`zero, ra, sp, gp, tp, t0-t6, s0-s11, a0-a7`), mapped to
  5-bit codes via `register_dict`.
- Load/store memory operand syntax `lw rd,imm(rs)` is handled by splitting on `(`.
- Labels must be on the **same line** as an instruction: `label: instr ...`. A first
  pass records `labels[name] = line_number` and strips the label prefix.
- The program must contain **exactly one** "virtual halt": the literal line
  `beq zero,zero,0`. Zero halts or more than one is a hard error.

### Pipeline

1. **Pass 1** — read all lines; build `labels` dict; count halts.
2. **Pass 2** — per line: tokenize, dispatch on mnemonic to the matching type block,
   validate operand count / register names / immediate ranges, build the 32-bit binary
   string, append to `output`.
3. Branch/jump label offsets are computed as `(labels[target] - current_line) * 4`
   (PC-relative, in bytes).
4. Immediates are converted with hand-rolled helpers `imm_to_bin(value, bits)` and
   `tows_complement(binary)` (manual two's-complement, string based).
5. **Error handling**: any failure `print()`s a message beginning with `ERROR:` and
   `break`s out of the loop. The output file is written **only if every line was
   processed** (`count == lines`); on error nothing is written.

### Immediate range checks

- I/S-type: −2¹¹ … 2¹¹−1
- B-type: −2¹² … 2¹²−1 (13-bit, LSB implicit 0)
- U-type: −2³¹ … 2³¹−1 (the value is converted to 32-bit and the top 20 bits are used)
- J-type: −2²⁰ … 2²⁰−1

---

## 2. Simulator (`Simulator.py`)

A single top-level script. Invoked as `python3 Simulator.py <input.mc> <output.txt>`.
Reads one 32-char binary string per line into an instruction list and interprets them.

### Machine state

- **Registers**: dict `{'x0'..'x31': 0}`; `x2` (sp) initialized to **256**.
  `set_register` masks values to 32 bits (`& 0xFFFFFFFF`) and ignores writes to `x0`.
- **Memory**: dict of 1024 words covering `0x00010000–0x00010FFC` (4 KB), keyed by
  hex-string addresses (`hex(addr)`), values are Python ints.
- **PC**: byte-addressed int starting at 0; instruction index = `pc/4`.

### Execution loop (`simulate_instructions`)

Runs while `pc/4` is inside the instruction list **and** the current instruction is not
the halt encoding (`beq zero,zero,0` = `00000000000000000000000001100011`). Each
iteration slices the 32-char string into fields by opcode class and dispatches:

- **R-type** (`0110011`): add/sub/sll/slt/sltu/xor/srl/or/and via funct3+funct7.
- **I-type** (`0000011` lw, `0010011` addi/sltiu, `1100111` jalr). `lw` reads
  `memory[hex(rs1 + imm)]`. `jalr` writes `pc+4` to rd then jumps.
- **S-type** (`0100011` sw): `memory[hex(rs1 + imm)] = rs2`.
- **B-type** (`1100011`): reassembles the scattered immediate bits, sign-extends,
  branches by `pc += imm` or falls through.
- **U-type** (`0110111` lui / `0010111` auipc): imm = top 20 bits << 12.
- **J-type** (`1101111` jal): rd = pc+4, pc += imm.
- **Bonus** (`1111111`): funct3 `000` mul, `001` reset-all-registers, `010` halt
  (breaks loop), `011` bit-reverse rs1 into rd.

### Output format (the trace file)

For every executed instruction the simulator appends:

```
Executing instruction at PC = <dec> (0x<hex>): <32-bit string>
PC = <dec> (0x<hex>)
<regname> = <dec> (0x<hex>)      ← only non-zero registers, plus x0 always
```

then a `Final Register State` section, then a `Memory State` dump of all 1024 words as
`0x000XXXXX:0b<32 bits>` lines.

---

## 3. Web backend (`app.py`)

Flask app with CORS enabled. Three routes:

### `GET /`
Renders `templates/index.html`, passing `EXAMPLE_PROGRAMS` (addition, multiplication,
fibonacci — all ending in the `beq zero,zero,0` halt).

### `POST /assemble`  — body `{ "code": str }`
1. **Machine-code sniffing**: if the input contains only `0`, `1`, spaces, `b`, and
   newlines, it is treated as machine code: each 32-bit line is run through the
   built-in **disassembler** (`decode_machine_code`) and the decoded assembly is
   returned as `{machine_code, assembly_code, message}`. The disassembler only supports
   R-type, I-type arithmetic (`addi slti sltiu xori ori andi slli srli`), and branches.
2. Otherwise: appends `beq zero,zero,0` if the halt is missing, writes the code to a
   temp dir, and runs `Assembler.py` as a subprocess (5 s timeout).
3. Errors are detected by grepping the subprocess stdout+stderr for `"ERROR:"` or a
   non-zero exit code → HTTP 400 with the message. Success → `{machine_code}`.
4. Temp files are cleaned up in a `finally` block.

### `POST /simulate`  — body `{ "code": str }`
Same temp-file/subprocess pattern, running `Simulator.py` (5 s timeout). Returns
`{output: <trace text>}` or an error.

Server config: port from `$PORT` (default 5001), debug only when
`FLASK_ENV=development`. Production uses gunicorn (`gunicorn_config.py`: port 10000,
4 workers, 120 s timeout), targeted at Render.com per the README.

---

## 4. Frontend (`templates/index.html`)

Single self-contained page (all CSS/JS inline), styled with Bootstrap 5 + a purple
gradient theme, editor = **CodeMirror 5** with `gas` mode and monokai theme (all via
CDN).

Behavior:
- **"Assemble and Run"** → `POST /assemble`; on success shows machine code, then
  automatically `POST /simulate` and shows the trace. Errors render in a status banner.
- **"Machine Code Input" toggle** switches the editor to plain-text mode and the button
  to "Translate and Run"; pasted machine code round-trips through `/assemble`'s
  disassembler path and replaces the editor content with the decoded assembly.
- **Examples dropdown** loads one of the three server-provided example programs
  (injected into the page as JSON via Jinja).

---

## 5. Repository layout

| Path | Purpose |
|------|---------|
| `Assembler.py` | assembly → machine-code script |
| `Simulator.py` | machine-code interpreter/tracer |
| `app.py` | Flask server + disassembler + example programs |
| `templates/index.html` | entire frontend |
| `requirements.txt` | flask 3.0.2, flask-cors 4.0.0, gunicorn 21.2.0 |
| `gunicorn_config.py` | production server config |
| `test.s`, `machine_code.mc`, `output.txt`, `output.log` | leftover test artifacts (committed) |
| `env/`, `__pycache__/` | a committed virtualenv and bytecode cache (should be ignored) |
