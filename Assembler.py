import sys


if __name__ == "__main__":
    input_file_path = sys.argv[1]
    output_file_path = sys.argv[2]



register_dict = {
   "zero": "00000",
   "ra": "00001",
   "sp": "00010",
   "gp": "00011",
   "tp": "00100",
   "t0": "00101",
    "t1": "00110",
    "t2": "00111",
    "s0": "01000",
    "s1": "01001",

    "a0": "01010",
    "a1": "01011",
    "a2": "01100",  
    "a3": "01101",
    "a4": "01110",
    "a5": "01111",
    "a6": "10000",
    "a7": "10001",
    "s2": "10010",  
    "s3": "10011",
    "s4": "10100",
    "s5": "10101",
    "s6": "10110",
    "s7": "10111",
    "s8": "11000",
    "s9": "11001",
    "s10": "11010",
    "s11": "11011",
    "t3": "11100",  
    "t4": "11101",
    "t5": "11110",
    "t6": "11111",
}

r_type = {'add':"000", 'sub':"000", 'sll':"001",'slt':"010", 'sltu':"011", 'xor':"100", 'srl':"101", 'or':"110", 'and':"111"}
#Funct7 is all zero except in sub which is 0100000
#Opcode is 0110011

i_type = {"lw": ["0000011","010"], 
          "addi": ["0010011","000"], 
          "sltiu": ["0010011","011"], 
          "jalr":["1100111","000"]}

s_type = {"sw": ["0100011", "010"]}

b_type = {"beq": "000", "bne": "001", "blt": "100", "bge":"101", "bltu": "110", "bgeu": "111"}
#opcode for all is 110001

u_type = {"lui":"0110111", "auipc":"0010111"}
#No funct3 required

j_type = {"jal": "1101111"}
#no funct3

bonus = {"mul": "000", "rst": "001", "halt": "010", "rvrs": "011"}
#opcode: 1111111

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


def imm_to_bin(a, no_of_bits):
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


f = open(input_file_path,"r")
read = f.readlines()
labels = {}
lines = 0
is_hault = False
hault_no = 0
for j in read:
    if ":" in j:
        index = j.index(":")
        labels[j[:index]]= lines
        read[lines] = j[index+2:]
    lines += 1
    if "beq zero,zero,0" in read[lines-1]:
        is_hault = True
        hault_no +=1


count = 0
output = []
for i in read:
    if(hault_no > 1):
        print("ERROR: More than 1 haults present")
        break

    if(not is_hault):
        print("ERROR: No Hault Present")
        break

    words = i.split()

    if(len(words)!=2 and len(words)!=0):
        print("ERROR: Invalid Instruction")
        break

    i_list = []
    for word in words:
        i_list.extend(word.split(","))

    if (i_list == []):
        count += 1
        continue

    if '(' in i_list[-1]:
        inst = i_list[-1].split("(")
        i_list[2] = inst[1][0:-1]
        i_list.append(inst[0])

    
    #R Type instructions
    if i_list[0] in r_type:
        if len(i_list)!= 4:
            print(f"ERROR: in line {count+1}")
            break

        if(i_list[1] not in register_dict or i_list[2] not in register_dict or i_list[3] not in register_dict):
            print("ERROR: registers not defined")
            break
        
        
        if i_list[0] == "sub":
            binary = ""
            binary += "0100000" + register_dict[i_list[3]]+ register_dict[i_list[2]]+ r_type[i_list[0]] + register_dict[i_list[1]]+"0110011"
            output.append(binary)

        else:
            binary = ""
            binary += "0000000" + register_dict[i_list[3]]+ register_dict[i_list[2]]+ r_type[i_list[0]] + register_dict[i_list[1]]+"0110011"
            output.append(binary)

    
    #I Type
    elif i_list[0] in i_type:

        if len(i_list)!= 4:
            print(f"ERROR: in line {count+1}")
            break

        given_value=int(i_list[3])
        if(given_value<-2**11 or given_value> 2**11-1):
            print("ERROR:the immediate value is out of bounds")
            break

        if(i_list[1] not in register_dict or i_list[2] not in register_dict ):
            print("ERROR: registers not defined")
            break
          
        binary = imm_to_bin(int(i_list[3]),12)

        s = binary + register_dict[i_list[2]] + i_type[i_list[0]][1] + register_dict[i_list[1]] + i_type[i_list[0]][0]
        output.append(s)

    #S Type
    elif i_list[0] in s_type:

        if len(i_list)!= 4:
            print(f"ERROR: in line {count+1}")
            break

        if(int(i_list[3])<-2**11 or int(i_list[3])> 2**11-1):
            print("ERROR:the immediate value is out of bounds")
            break

        if(i_list[1] not in register_dict or i_list[2] not in register_dict):
            print("ERROR: registers not defined")
            break


        binary = imm_to_bin(int(i_list[3]),12)
        s = binary[0:7]+register_dict[i_list[1]]+register_dict[i_list[2]]+s_type[i_list[0]][1]+binary[7:13]+ "0100011"
        output.append(s)

    
    #B Type
    elif i_list[0] in b_type:

        if len(i_list)!= 4:
            print(f"ERROR: in line {count+1}")
            break

        lab = -1
        try:
            i_list[3] = int(i_list[3])

        except ValueError:
            i_list[3] = i_list[3]


        if(type(i_list[3])==str):
            if(i_list[3] in labels):
                lab =(labels[i_list[3]]-count)*4
            else:
                print(f"ERROR on line {count+1}: No such Label Found {i_list[3]}")
                break


        elif type(i_list[3]==int):
            lab = i_list[3]
        
        if(lab<-2**12 or lab> 2**12-1):
            print(f"ERROR on line {count+1}:the immediate value is out of bounds")
            break
           
        if(i_list[1] not in register_dict or i_list[2] not in register_dict):
            print("ERROR: registers not defined")
            break
        
        binary=imm_to_bin(lab,13)
        s=binary=binary[0]+binary[2:8]+register_dict[i_list[2]]+register_dict[i_list[1]]+b_type[i_list[0]]+binary[8:12]+binary[1]+"1100011"        
        output.append(s)    

    #U TYPE
    elif i_list[0] in u_type:

        if len(i_list)!= 3:
            print(f"ERROR: in line {count+1}")
            break

        given_value=int(i_list[2])
        if(given_value<-2**31 or given_value> 2**31-1):
            print(f"ERROR on line {count+1}:the immediate value is out of bounds")
            break

        if(i_list[1] not in register_dict):
                     print("ERROR: registers not defined")
                     break
        
        imm=imm_to_bin(int(i_list[2]),32)
        s=imm[0:20]+register_dict[i_list[1]]+u_type[i_list[0]]
        output.append(s)
        
    # J TYPE
    elif i_list[0] in j_type:

        if len(i_list)!= 3:
            print(f"ERROR: in line {count+1}")
            break

        lab = -1
        try:
            i_list[2] = int(i_list[2])

        except ValueError:
            i_list[2] = i_list[2]


        if(type(i_list[2])==str):
            if(i_list[2] in labels):
                lab =(labels[i_list[2]]-count)*4
            else:
                print(f"ERROR on line {count+1}: No such Label Found {i_list[2]}")
                break


        elif type(i_list[2]==int):
            lab = i_list[2]
        
        if(lab<-2**20 or lab> 2**20-1):
            print(f"ERROR on line {count+1}:the immediate value is out of bounds")
            break


        if(given_value<-2**20 or given_value> 2**20-1):
            print(f"ERROR on line {count+1}:the immediate value is out of bounds")
            break
           
        if(i_list[1] not in register_dict):
            print("ERROR: registers not defined")
            break


        imm=imm_to_bin(int(i_list[2]),21)
        s=imm[1]+imm[10:20]+imm[10]+imm[2:10]+register_dict[i_list[1]]+"1101111"
        output.append(s)

    elif i_list[0] in bonus:
        s = ""
        if i_list[0] == 'mul':
            s = "0000000" + register_dict[i_list[3]] + register_dict[i_list[2]] + bonus[i_list[0]] +  register_dict[i_list[1]] + "1111111"

        elif i_list[0] == 'rst' or i_list[0] == 'halt':
            funct3 = bonus[i_list[0]]
            s = "0000000" + "00000" + "00000" + funct3 + "00000" + "1111111"

        elif i_list[0] == "rvrs":
            s = "0000000" + "00000" + register_dict[i_list[2]] +  bonus[i_list[0]] + register_dict[i_list[1]] + "1111111"
    else:
        print("ERROR: Invalid Instruction")
        break        

    count += 1


   
if (count == lines):
    with open(output_file_path, 'w') as f:
        for item in output:
            f.write(item + '\n')
   
    
    
f.close()
