// Little Computer 3b ISA

// 16 bit address space (byte-addressable)
// little endian

// 16 bit PC, 8x 16 bit registers 0-7
// 3x condition registers: N, Z, P
// 16 bit PSR

// regs: PC MPR PSR CC

program: line+

line: (instruction | directive | -WS) -COMMENT? eol

instruction: LABEL? OPCODE (operand ("," operand)* )?

directive: LABEL? D_OP D_OPERAND?


OPCODE: "JSRR" | "LSHF" | "RSHFL" | "RSHFA" | "TRAP"
       | "ADD" | "AND" | "BRx" | "JMP" | "JSR"
       | "LDB" | "LDW" | "LEA" | "NOT" | "RET"
       | "RTI" | "STB" | "STW" | "XOR" | "HALT"

operand: LABEL | REGISTER | int

D_OP: "." ("ORIG" | "FILL" | "BLKW" | "STRINGZ" "END")

D_OPERAND: int | STRING

int: HEX | DEC | BIN

REGISTER: "R" (/[0-7]/)

COMMENT: /;[^\n]*/

LABEL: /[a-f][\w\d]*/


HEX: /x([0-9a-f]+)/
DEC: /#(-?[0-9]+)/
BIN: /b([01]+)/

STRING: /"([^"\\\x00-\x1F]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"/
