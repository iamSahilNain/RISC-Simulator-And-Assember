# RISC-V Assembler and Simulator

A web-based RISC-V assembler and simulator that allows users to write, assemble, and simulate RISC-V assembly code through a user-friendly interface.

## Features

- Write and edit RISC-V assembly code with syntax highlighting
- Assemble RISC-V code to machine code
- Simulate execution and view register states
- Convert machine code back to assembly
- Pre-loaded example programs (Addition, Multiplication, Fibonacci)
- Real-time error feedback
- Clean and modern web interface

## Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   python app.py
   ```

4. Visit http://localhost:5001 in your browser

## Production Deployment

### Deploying to Render.com

1. Create a new account on [Render.com](https://render.com)

2. Click "New +" and select "Web Service"

3. Connect your GitHub repository

4. Fill in the following details:
   - Name: `risc-v-simulator` (or your preferred name)
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -c gunicorn_config.py app:app`

5. Click "Create Web Service"

The application will be automatically deployed and available at your Render URL.

### Environment Variables

- `PORT`: The port number (set automatically by Render)
- `FLASK_ENV`: Set to 'production' for production deployment

## License

This project is open source and available under the MIT License.

## Verification (added October 2026)

The assembler and simulator are checked against two independent references:

* **Encoding conformance.** Every instruction the assembler accepts is also
  encoded by LLVM's RISC-V assembler (`llvm-mc -triple=riscv32`) and the two
  32-bit words are compared. Any difference is an assembler bug.
* **Differential execution.** Random programs over the supported subset are
  run on this simulator and on the Unicorn CPU emulator from the same initial
  state, and all 32 registers plus the 4 KB data region are compared at the
  halt. The simulator is fed LLVM's encodings, so an execution difference is
  a simulator bug and cannot be an assembler bug.

A generator produces the programs (bounded loops, forward branches,
`auipc`/`jalr` pairs, loads and stores inside the data region, negative
values), and a delta-debugging reducer shrinks any failing program to a
minimal case. The harness is itself tested against planted bugs: a flipped
encoding bit, a corrupted register and a corrupted memory word must each be
reported (`tests/test_harness.py`).

Running it found nine bugs in the 2024 code, including a `jal` encoder that
crashed on every use, `sltu`/`sltiu` that crashed on most inputs, and `jalr`
ignoring its base register. After the fixes: 5,000 of 5,000 random
instructions encode bit-for-bit as LLVM does, and 1,000 of 1,000 random
programs end in the same state as Unicorn. Numbers, seeds and minimal cases
are in `results/README.md`.

```bash
brew install llvm && pip install unicorn pytest
python -m verify encode -n 600          # encoding conformance
python -m verify exec -n 200 --reduce   # differential execution, reduce failures
pytest -q tests
```

The `lui`/`auipc` syntax differs from the standard: this assembler takes a
32-bit value and uses its top 20 bits, the standard takes the 20-bit field.
The harness converts between the two before comparing encodings.
