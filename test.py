from array import array


from yapl import StringParserInput, is_ok

from sasm.plugins.lc3.vm import LC3Vm
from sasm.plugins.lc3.parser import program

from sasm.plugins.lc3.assembler import LC3Assembler

code = """
; Demo LC3-b print program

.ORIG x3000
LEA R0, MSG
PUTS
HALT

MSG: .STRINGZ "Hello, World!\\n"
BYTE: .FILL #5
.END
"""

instructions = [
    0b0011_0000, 0b0001_100_0, # ADD R4, R0, x8
    0b0001_0010, 0b1101_000_1, # RSHFL R0, R4, #4
    0b0010_0101, 0b1111_000_0, # TRAP x25
]

# buf = array('B', instructions)
# program = buf.tobytes()
# print(f"Bytecode: {instructions}\n")

# if __name__ == "__main__":
#     vm = LC3Vm(debug=True, state_dump=True)
#     vm.load_user_program(program)

#     vm.run()

if __name__ == "__main__":
    print(f"\033[103;37;1mParsing:\033[0m\n{code}\n")

    i = StringParserInput(code)

    result = program.run(i)

    if is_ok(result):
        print("\033[102;37;1mParse OK\033[0m\n\033[105;37;1mLabels:\033[0m")
        assembler = LC3Assembler()

        assembler.assemble(result.unwrap().item)

        user_prog = assembler.get_bytes()

        print(f"\033[102;37;1mCompile OK\033[0m\n\033[103;37;1mBytecode:\033[0m\n{list(user_prog)}\n")

        vm = LC3Vm(debug = True)

        vm.load_user_program(user_prog)

        print("\033[105;37;1mVM Output:\033[0m")

        vm.run()

    else:
        result.unwrap_err().print_err()
