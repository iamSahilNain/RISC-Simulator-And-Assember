from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import tempfile
import sys
import subprocess
from io import StringIO
import time

app = Flask(__name__)
CORS(app)

# Example RISC-V programs
EXAMPLE_PROGRAMS = {
    'addition': '''addi a0,zero,5
addi a1,zero,3
add a2,a0,a1
beq zero,zero,0''',
    
    'multiplication': '''addi a0,zero,4
addi a1,zero,3
add a2,zero,zero
add t0,zero,zero
beq a1,zero,end
loop:
add a2,a2,a0
addi t0,t0,1
bne t0,a1,loop
end:
beq zero,zero,0''',

    'fibonacci': '''addi a0,zero,1
addi a1,zero,1
addi t0,zero,5
addi t1,zero,1
beq t0,t1,end
loop:
add a2,a1,a0
add a0,zero,a1
add a1,zero,a2
addi t1,t1,1
bne t1,t0,loop
end:
beq zero,zero,0'''
}

# Machine code to assembly mapping
OPCODE_MAP = {
    "0110011": "R-type",
    "0010011": "I-type",
    "0000011": "Load",
    "0100011": "Store",
    "1100011": "Branch",
    "1101111": "JAL",
    "1100111": "JALR",
    "0110111": "LUI",
    "0010111": "AUIPC"
}

R_TYPE_FUNCT3 = {
    "000": {"0000000": "add", "0100000": "sub"},
    "001": {"0000000": "sll"},
    "010": {"0000000": "slt"},
    "011": {"0000000": "sltu"},
    "100": {"0000000": "xor"},
    "101": {"0000000": "srl"},
    "110": {"0000000": "or"},
    "111": {"0000000": "and"}
}

I_TYPE_FUNCT3 = {
    "000": "addi",
    "010": "slti",
    "011": "sltiu",
    "100": "xori",
    "110": "ori",
    "111": "andi",
    "001": "slli",
    "101": "srli"
}

REGISTER_MAP = {
    "00000": "zero",
    "00001": "ra",
    "00010": "sp",
    "00011": "gp",
    "00100": "tp",
    "00101": "t0",
    "00110": "t1",
    "00111": "t2",
    "01000": "s0",
    "01001": "s1",
    "01010": "a0",
    "01011": "a1",
    "01100": "a2",
    "01101": "a3",
    "01110": "a4",
    "01111": "a5",
    "10000": "a6",
    "10001": "a7",
    "10010": "s2",
    "10011": "s3",
    "10100": "s4",
    "10101": "s5",
    "10110": "s6",
    "10111": "s7",
    "11000": "s8",
    "11001": "s9",
    "11010": "s10",
    "11011": "s11",
    "11100": "t3",
    "11101": "t4",
    "11110": "t5",
    "11111": "t6"
}

def decode_machine_code(machine_code):
    """Convert machine code to assembly."""
    try:
        # Remove any whitespace and 0b prefix
        machine_code = machine_code.replace("0b", "").replace(" ", "")
        if len(machine_code) != 32:
            return None

        opcode = machine_code[-7:]
        rd = machine_code[-12:-7]
        funct3 = machine_code[-15:-12]
        rs1 = machine_code[-20:-15]
        rs2 = machine_code[-25:-20]
        funct7 = machine_code[-32:-25]

        if opcode not in OPCODE_MAP:
            return None

        # R-type instruction
        if opcode == "0110011":
            if funct3 in R_TYPE_FUNCT3 and funct7 in R_TYPE_FUNCT3[funct3]:
                instr = R_TYPE_FUNCT3[funct3][funct7]
                return f"{instr} {REGISTER_MAP[rd]},{REGISTER_MAP[rs1]},{REGISTER_MAP[rs2]}"

        # I-type instruction
        elif opcode == "0010011":
            if funct3 in I_TYPE_FUNCT3:
                instr = I_TYPE_FUNCT3[funct3]
                imm = int(machine_code[:12], 2)
                if machine_code[0] == "1":  # Handle negative numbers
                    imm = imm - 4096
                return f"{instr} {REGISTER_MAP[rd]},{REGISTER_MAP[rs1]},{imm}"

        # B-type instruction (branches)
        elif opcode == "1100011":
            # B-type immediate: imm[12|10:5|4:1|11] = bits [0|1:7|20:24|24]
            imm12 = machine_code[0]
            imm10_5 = machine_code[1:7]
            rs2 = machine_code[7:12]
            rs1 = machine_code[12:17]
            funct3 = machine_code[17:20]
            imm4_1 = machine_code[20:24]
            imm11 = machine_code[24]
            # Immediate is sign-extended
            imm = int(imm12 + imm11 + imm10_5 + imm4_1 + "0", 2)
            if imm12 == "1":
                imm -= (1 << 13)
            branch_map = {
                "000": "beq",
                "001": "bne",
                "100": "blt",
                "101": "bge",
                "110": "bltu",
                "111": "bgeu"
            }
            if funct3 in branch_map:
                instr = branch_map[funct3]
                return f"{instr} {REGISTER_MAP[rs1]},{REGISTER_MAP[rs2]},{imm}"

        return None
    except Exception:
        return None

@app.route('/')
def index():
    return render_template('index.html', examples=EXAMPLE_PROGRAMS)

@app.route('/assemble', methods=['POST'])
def assemble():
    input_file = None
    output_file = None
    error_output = None
    try:
        assembly_code = request.json.get('code', '').strip()
        if not assembly_code:
            return jsonify({'error': 'No assembly code provided'}), 400

        # Check if input might be machine code (support multiple lines)
        if all(c in '01 b\n' for c in assembly_code):
            lines = [line.strip().replace("0b", "").replace(" ", "") for line in assembly_code.splitlines() if line.strip()]
            decoded_lines = [dl for line in lines if len(line) == 32 for dl in [decode_machine_code(line)] if dl is not None]
            print(f"[DEBUG] Decoded lines: {decoded_lines}")  # Debug print
            if decoded_lines:
                return jsonify({
                    'machine_code': assembly_code,
                    'assembly_code': "\n".join(decoded_lines),
                    'message': 'Successfully translated machine code to assembly'
                })
            else:
                return jsonify({'error': 'No valid 32-bit machine code lines found.'}), 400
        
        # Ensure code ends with a halt instruction
        if 'beq zero,zero,0' not in assembly_code:
            assembly_code += '\nbeq zero,zero,0'
        
        # Create temporary directory to work in
        temp_dir = tempfile.mkdtemp()
        try:
            # Create input and output files in the temp directory
            input_file = os.path.join(temp_dir, 'input.s')
            output_file = os.path.join(temp_dir, 'output.mc')
            
            # Write assembly code to input file
            with open(input_file, 'w') as f:
                f.write(assembly_code)
            
            # Capture stdout and stderr
            process = subprocess.Popen(
                ['python3', 'Assembler.py', input_file, output_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete with a timeout
            try:
                stdout, stderr = process.communicate(timeout=5)
                error_output = stdout + stderr
            except subprocess.TimeoutExpired:
                process.kill()
                return jsonify({'error': 'Assembler timed out'}), 500
            
            # Check if there were any errors
            if "ERROR:" in error_output or process.returncode != 0:
                return jsonify({'error': error_output.strip() or 'Assembly failed'}), 400
            
            # Check if output file exists and has content
            if not os.path.exists(output_file):
                return jsonify({'error': 'Assembler failed to create output file'}), 500
                
            # Read machine code
            try:
                with open(output_file, 'r') as f:
                    machine_code = f.read().strip()
                    if not machine_code:
                        return jsonify({'error': 'Assembler produced empty output'}), 400
                    return jsonify({'machine_code': machine_code})
            except Exception as e:
                return jsonify({'error': f'Failed to read assembler output: {str(e)}'}), 500
                
        finally:
            # Clean up temporary directory and its contents
            try:
                if os.path.exists(input_file):
                    os.unlink(input_file)
                if os.path.exists(output_file):
                    os.unlink(output_file)
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Cleanup error: {str(e)}")
            
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/simulate', methods=['POST'])
def simulate():
    input_file = None
    output_file = None
    error_output = None
    try:
        machine_code = request.json.get('code', '').strip()
        if not machine_code:
            return jsonify({'error': 'No machine code provided'}), 400
            
        # Create temporary directory to work in
        temp_dir = tempfile.mkdtemp()
        try:
            # Create input and output files in the temp directory
            input_file = os.path.join(temp_dir, 'input.mc')
            output_file = os.path.join(temp_dir, 'output.txt')
            
            # Write machine code to input file
            with open(input_file, 'w') as f:
                f.write(machine_code)
            
            # Capture stdout and stderr
            process = subprocess.Popen(
                ['python3', 'Simulator.py', input_file, output_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete with a timeout
            try:
                stdout, stderr = process.communicate(timeout=5)
                error_output = stdout + stderr
            except subprocess.TimeoutExpired:
                process.kill()
                return jsonify({'error': 'Simulator timed out'}), 500
            
            # Check if there were any errors
            if "ERROR:" in error_output or process.returncode != 0:
                return jsonify({'error': error_output.strip() or 'Simulation failed'}), 400
            
            # Check if output file exists and has content
            if not os.path.exists(output_file):
                return jsonify({'error': 'Simulator failed to create output file'}), 500
                
            # Read simulation output
            try:
                with open(output_file, 'r') as f:
                    simulation_output = f.read().strip()
                    if not simulation_output:
                        return jsonify({'error': 'Simulator produced empty output'}), 400
                    return jsonify({'output': simulation_output})
            except Exception as e:
                return jsonify({'error': f'Failed to read simulator output: {str(e)}'}), 500
                
        finally:
            # Clean up temporary directory and its contents
            try:
                if os.path.exists(input_file):
                    os.unlink(input_file)
                if os.path.exists(output_file):
                    os.unlink(output_file)
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Cleanup error: {str(e)}")
            
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    # Get port from environment variable or default to 5001
    port = int(os.environ.get('PORT', 5001))
    # In production, debug should be False
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug) 