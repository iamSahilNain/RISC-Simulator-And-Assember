import sys

if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]

# Initialize registers
registers = {f'x{i}': 0 for i in range(32)}
registers['x2'] = 256  # Initialize stack pointer

register_mapping = [
    'x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7',
    'x8', 'x9', 'x10', 'x11', 'x12', 'x13', 'x14', 'x15',
    'x16', 'x17', 'x18', 'x19', 'x20', 'x21', 'x22', 'x23',
    'x24', 'x25', 'x26', 'x27', 'x28', 'x29', 'x30', 'x31'
]

# Initialize memory (4KB)
memory = {}
for i in range(0x00010000, 0x00011000, 4):
    memory[hex(i)] = 0

def registers_reset():
    global registers
    registers = {f'x{i}': 0 for i in range(32)}
    registers['x2'] = 256  # Reset stack pointer

def set_register(reg, value):
    # x0 is hardwired to 0
    if reg != 'x0':
        registers[reg] = value & 0xFFFFFFFF  # Ensure 32-bit value

def get_register(reg):
    return registers[reg]

def unsigned_b2d(binary_str):
    return int(binary_str, 2)

def tows_complement(binary):
    ones_complement = ''
    for i in binary:
        if i=='1':
            ones_complement += '0'
        else:
            ones_complement += '1'

    result = ''
    carry = True
    for i in ones_complement[::-1]:
        if i == '0' and carry:
            result = '1' + result
            carry = False
        elif i == '1' and carry:
            result = '0' + result
        else:
            result = i + result

    return result


def dec_to_bin(a, no_of_bits):
    n = abs(int(a))
    binary = ''
    while n:
        binary = str(n % 2) + binary
        n //= 2
        
    length = no_of_bits - len(binary)
    final = length * '0'
    binary1 = final + binary

    if int(a) < 0:
        binary1= tows_complement(binary1)
        
    return binary1 

def twos_complement_to_decimal(binary_str):
    is_negative = binary_str[0] == '1'

    if is_negative:
        binary_str = ''.join('1' if bit == '0' else '0' for bit in binary_str)
        binary_str = bin(int(binary_str, 2) + 1)[2:]  # Remove '0b' prefix from the result

    decimal_value = int(binary_str, 2)

    if is_negative:
        decimal_value = -decimal_value

    return decimal_value

def sign_extend(binary_str):
    if binary_str[0] == '1':
        return '1' * (32 - len(binary_str)) + binary_str
    else:
        return '0' * (32 - len(binary_str)) + binary_str


def print_registers(pc):
    # Print PC in both hex and decimal
    file.write(f"PC = {pc} (0x{pc:08x})\n")
    
    # Register name mapping
    reg_names = {
        'x0': 'zero', 'x1': 'ra', 'x2': 'sp', 'x3': 'gp', 'x4': 'tp',
        'x5': 't0', 'x6': 't1', 'x7': 't2', 'x8': 's0', 'x9': 's1',
        'x10': 'a0', 'x11': 'a1', 'x12': 'a2', 'x13': 'a3', 'x14': 'a4',
        'x15': 'a5', 'x16': 'a6', 'x17': 'a7', 'x18': 's2', 'x19': 's3',
        'x20': 's4', 'x21': 's5', 'x22': 's6', 'x23': 's7', 'x24': 's8',
        'x25': 's9', 'x26': 's10', 'x27': 's11', 'x28': 't3', 'x29': 't4',
        'x30': 't5', 'x31': 't6'
    }
    
    # Print only non-zero registers with their names
    for reg in register_mapping:
        value = registers[reg]
        if value != 0 or reg == 'x0':  # Always print x0 (zero) register
            reg_name = reg_names[reg]
            # Print in both decimal and hex format
            file.write(f"{reg_name:4} = {value:4} (0x{value & 0xFFFFFFFF:08x})\n")
    
    file.write("\n")


def i_type(opcode, rd, funct3, rs1, imm, pc):
    if opcode == "0000011":  # lw
        loc = hex(get_register(rs1) + imm)
        set_register(rd, memory[loc])
        
    elif opcode == "0010011" and funct3=="000":  # addi
        set_register(rd, get_register(rs1) + imm)
        
    elif opcode == "1100111" and funct3=="000":  # jalr
        set_register(rd, pc + 4)
        pc_str = dec_to_bin(pc, 32)
        pc_str = pc_str[:-1] + "0"
        pc = twos_complement_to_decimal(pc_str)
        pc = pc + imm   
        
    elif opcode == "0010011" and funct3=="011":  # sltiu
        n1 = twos_complement_to_decimal(str(get_register(rs1)))
        n1 = unsigned_b2d(str(n1))    
        if n1 < imm:
            set_register(rd, 1)
        else:
            set_register(rd, 0)

    if(opcode != "1100111"):
        pc = pc + 4

    return pc      
        


def r_type(rd, funct3, rs1, rs2, funct7):
    if funct3 == "000" and funct7 == "0000000":  # add
        set_register(rd, get_register(rs1) + get_register(rs2))
        
    elif funct3 == "000" and funct7 == "0100000":  # sub
        set_register(rd, get_register(rs1) - get_register(rs2))
        
    elif funct3 == "001":  # sll
        shift_amount = abs(get_register(rs2)) & 0b11111 
        shifted_rs1 = get_register(rs1) << shift_amount
        set_register(rd, shifted_rs1)

    elif funct3 == "010":  # slt
        if get_register(rs1) < get_register(rs2):
            set_register(rd, 1)
        else:
            set_register(rd, 0)
            
    elif funct3 == "011":  # sltu
        n1 = twos_complement_to_decimal(str(get_register(rs1)))
        n2 = twos_complement_to_decimal(str(get_register(rs2)))
        n1 = unsigned_b2d(str(n1))
        n2 = unsigned_b2d(str(n2))
        if n1 < n2:
            set_register(rd, 1)
        else:
            set_register(rd, 0)
            
    elif funct3 == "100":  # xor
        set_register(rd, get_register(rs1) ^ get_register(rs2))
        
    elif funct3 == "101":  # srl
        shift_amount = abs(get_register(rs2)) & 0b11111 
        shifted_rs1 = get_register(rs1) >> shift_amount  # Changed from << to >>
        set_register(rd, shifted_rs1)
        
    elif funct3 == "110":  # or
        set_register(rd, get_register(rs1) | get_register(rs2))
        
    elif funct3 == "111":  # and
        set_register(rd, get_register(rs1) & get_register(rs2))

def u_type(opcode, rd, imm, registers, pc):
    if opcode == "0110111":  # lui
        set_register(rd, imm)
    elif opcode == "0010111":  # auipc
        set_register(rd, imm + pc)

def s_type(imm, rs1, rs2):
    loc = hex(get_register(rs1) + imm)
    memory[loc] = get_register(rs2)
    
def b_type(imm, funct3, pc, rs1, rs2):
    rs1_val = get_register(rs1)
    rs2_val = get_register(rs2)
    
    if funct3 == "000":  # beq
        branch_condition = rs1_val == rs2_val
    elif funct3 == "001":  # bne
        branch_condition = rs1_val != rs2_val
    elif funct3 == "100":  # blt
        branch_condition = rs1_val < rs2_val
    elif funct3 == "101":  # bge
        branch_condition = rs1_val >= rs2_val
    elif funct3 == "110":  # bltu
        # Convert to unsigned
        rs1_val = rs1_val & 0xFFFFFFFF
        rs2_val = rs2_val & 0xFFFFFFFF
        branch_condition = rs1_val < rs2_val
    elif funct3 == "111":  # bgeu
        # Convert to unsigned
        rs1_val = rs1_val & 0xFFFFFFFF
        rs2_val = rs2_val & 0xFFFFFFFF
        branch_condition = rs1_val >= rs2_val
    
    if branch_condition:
        pc += imm
    else:
        pc = pc + 4
        
    return pc 

def j_type(pc, imm, rd):
    set_register(rd, pc + 4)
    pc_str = dec_to_bin(pc, 32)
    pc_str = pc_str[:-1] + "0"
    pc = twos_complement_to_decimal(pc_str)
    pc = pc + imm
    return pc


def simulate_instructions(instructions):
    pc = 0
    file.write("Execution Trace:\n")
    file.write("-" * 50 + "\n\n")
    
    while pc/4 < len(instructions) and instructions[int(pc/4)] != "00000000000000000000000001100011":
        inst = instructions[int(pc/4)]
        
        # Print current instruction
        file.write(f"Executing instruction at PC = {pc} (0x{pc:08x}): {inst}\n")
        
        opcode = inst[25:32]

        # R-type
        if opcode == "0110011":
            rd = register_mapping[unsigned_b2d(inst[20:25])]
            funct3 = inst[17:20]
            rs2 = register_mapping[unsigned_b2d(inst[7:12])]
            rs1 = register_mapping[unsigned_b2d(inst[12:17])]
            funct7 = inst[0:7]
            r_type(rd, funct3, rs1, rs2, funct7)
            pc += 4
            print_registers(pc)

        # U-type
        elif opcode in ["0010111", "0110111"]:  
            rd = register_mapping[unsigned_b2d(inst[20:25])]
            imm = twos_complement_to_decimal(inst[0:20] + "000000000000")
            u_type(opcode, rd, imm, registers, pc)
            pc += 4
            print_registers(pc)

        #I type
        elif opcode == "0000011" or opcode == "0010011" or opcode== "1100111":  # lw, addi, jalr
            rd = register_mapping[unsigned_b2d(inst[20:25])]
            funct3 = inst[17:20]
            rs1 = register_mapping[unsigned_b2d(inst[12:17])]
            imm = inst[0:12]
            imm = twos_complement_to_decimal(imm)
            pc = i_type(opcode, rd, funct3, rs1, imm, pc)
            print_registers(pc)

        # S type
        elif opcode == "0100011":
            imm1 = inst[0:7]  
            imm2 = inst[20:25]  
            imm = twos_complement_to_decimal(imm1 + imm2)
            rs1 = register_mapping[unsigned_b2d(inst[12:17])]
            rs2 = register_mapping[unsigned_b2d(inst[7:12])]
            pc += 4
            s_type(imm, rs1, rs2)
            print_registers(pc)

        #B Type
        elif opcode == "1100011":
            imm11 = inst[24]    # Extracting 11th bit
            imm4_1 = inst[20:24] # Extracting 1:4 bits
            funct3 = inst[17:20]
            rs1 = register_mapping[unsigned_b2d(inst[12:17])]
            rs2 = register_mapping[unsigned_b2d(inst[7:12])]
            imm10_5 = inst[1:7]
            imm12 = inst[0]
            imm0 = "0"
            imm = imm12 + imm11 + imm10_5 + imm4_1 + imm0
            imm = twos_complement_to_decimal(imm)
            pc = b_type(imm, funct3, pc, rs1, rs2)
            print_registers(pc)

        # Jtype   
        elif opcode == "1101111":
            imm_20 = inst[0]
            imm_10_1 = inst[1:11]
            imm_11 = inst[11]
            imm_19_12 = inst[12:20]
            imm = imm_20 + imm_19_12 + imm_11 + imm_10_1 + "0"
            imm = twos_complement_to_decimal(imm)
            rd = register_mapping[unsigned_b2d(inst[20:25])]
            pc = j_type(pc, imm, rd)
            print_registers(pc)

        # Special instructions
        elif opcode == "1111111":
            funct3 = inst[17:20]
            rd = register_mapping[unsigned_b2d(inst[20:25])]
            rs2 = register_mapping[unsigned_b2d(inst[7:12])]
            rs1 = register_mapping[unsigned_b2d(inst[12:17])]

            if funct3 == "000":  # mul
                set_register(rd, get_register(rs1) * get_register(rs2))
                pc += 4
                print_registers(pc)
            elif funct3 == "001":  # reset
                registers_reset()
                pc += 4
                print_registers(pc)
            elif funct3 == "010":  # halt
                break
            elif funct3 == "011":  # reverse
                temp = dec_to_bin(get_register(rs1), 32)[::-1]
                set_register(rd, twos_complement_to_decimal(temp))
                pc += 4
                print_registers(pc)

    file.write("\nFinal Register State:\n")
    file.write("-" * 50 + "\n")
    print_registers(pc)
    file.write("\nMemory State:\n")
    file.write("-" * 50 + "\n")

    return registers

instructions = []

with open(input_file, 'r') as file:
    # Read each line and strip whitespace and newlines
    instructions = [line.strip() for line in file.readlines() if line.strip()]

# Initialize output file
file = open(output_file, 'w')

# Run simulation
simulate_instructions(instructions)

# Write memory state
for hex_key, value in memory.items():
    formatted_hex_key = str(hex_key)
    new_key = formatted_hex_key[0:2] + "000" + formatted_hex_key[2:]
    binary_value = dec_to_bin(value,32)
    file.write(f"{new_key}:0b{binary_value}")
    file.write("\n")

file.close()
