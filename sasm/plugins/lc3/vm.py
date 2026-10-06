# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper
import sys
from array import array

from .consts import MEMORY_SIZE, OP, REG_COUNT, STACK_REG, AddressMap

USER_SLICE = slice(*AddressMap.UserSpace)
MAX_PROG_LEN = USER_SLICE.stop - USER_SLICE.start

# TODO: twos-complement representation for register values


def twoscomp(value: int, byte_len: int = 1):
    signed = (value >> ((byte_len * 8) - 1)) & 1 == 1

    return int.from_bytes(value.to_bytes(byte_len, signed=False), signed=signed)


def sext(value: int, bits: int):
    if (value >> (bits - 1)) & 1 != 0:
        value |= (2 ** (16 - bits) - 1) << bits

    return value  # twoscomp(value, 2)


class CondFlag:
    POS = 1 << 0
    ZRO = 1 << 1
    NEG = 1 << 2

    @classmethod
    def get(cls, val: int):
        match val:
            case cls.POS:
                return "POS"

            case cls.ZRO:
                return "ZRO"

            case cls.NEG:
                return "NEG"

            case _:
                return "???"


class LC3Vm:
    regs: array[int]
    memory: array[int]
    cond: int
    pc: int
    running: bool
    debug: bool
    state_dump: bool

    def __init__(self, debug: bool = False, state_dump: bool = False):
        self.regs = array("H", bytearray(REG_COUNT * 2))
        self.memory = array("B", bytearray(MEMORY_SIZE))

        self.cond = CondFlag.ZRO
        self.pc = 0
        self.priv = True

        self.running = False
        self.debug = debug
        self.state_dump = state_dump


    @property
    def psr(self):
        return (int(not self.priv) << 15) | self.cond

    @psr.setter
    def psr(self, val: int):
        self.priv = not bool(val >> 15)

        self.cond = val & 0x7

    def log(self, *v: str):
        if self.debug:
            print(*v)

    def print_state(self):
        if self.state_dump:
            reg_header_fmt = lambda i: f"R{i}".ljust(16)
            reg_header1 = map(reg_header_fmt, range(4))
            reg_header2 = map(reg_header_fmt, range(4, 8))

            reg_data_fmt = lambda n: f"{self.regs[n]:<16x}"
            reg_data1 = map(reg_data_fmt, range(4))
            reg_data2 = map(reg_data_fmt, range(4, 8))

            print(
                f"\nPC: {self.pc:#x}\nCC: {CondFlag.get(self.cond)}\nRegisters:\n\n\t"
                f"{' '.join(reg_header1)}\n\t{' '.join(reg_data1)}\n\n\t"
                f"{' '.join(reg_header2)}\n\t{' '.join(reg_data2)}\n"
            )

    def load_user_program(self, program: bytearray | bytes):
        assert (
            len(program) <= MAX_PROG_LEN
        ), "User program must be 51KiB (52,735 bytes) or less)"

        program_arr = array("B", program)

        self.memory[USER_SLICE] = program_arr
        self.pc = 0x3000
        self.priv = False

    def setcc(self, register: int):
        val = self.regs[register]

        if val == 0:
            self.cond = CondFlag.ZRO

        elif (val >> 15) != 0:
            self.cond = CondFlag.NEG

        else:
            self.cond = CondFlag.POS

    def read_u16(self, index: int):
        lo = self.memory[index]
        hi = self.memory[index + 1]

        return lo | (hi << 8)

    def write_u16(self, index: int, data: int):
        lo = data & 0xFF
        hi = (data >> 8) & 0xFF

        self.memory[index] = lo
        self.memory[index + 1] = hi

    def trap(self, vector: int):
        # TODO: implement real system calls

        match vector:
            case 0x40: # GETC
                ...

            case 0x42: # OUT
                ...

            case 0x44: # PUTS
                self.log("  (PUTs)")
                index = self.regs[0]
                char = self.memory[index]

                if self.debug:
                    sys.stdout.write("\033[104;37;1mCONSOLE >> \033[0m ")

                while char != 0:
                    sys.stdout.write(chr(char))
                    index += 1
                    char = self.memory[index]

            case 0x46: # IN
                ...

            case 0x4a:  #HALT
                self.log("  (HALT)")
                print("System halted.")
                self.running = False

            case _:
                raise RuntimeError(f"Unknown trap vector: {vector:x}")

    def run(self):
        self.print_state()
        self.running = True

        while self.running and self.pc < MEMORY_SIZE:
            self.step()

    def step(self):
        inst = self.read_u16(self.pc)
        self.pc += 2

        op = inst >> 12

        match op:
            case OP.BR:
                n = inst & (1 << 11)
                z = inst & (1 << 10)
                p = inst & (1 << 9)
                offset = inst & 0x1FF

                self.log(
                    f"BR{'n' if n else ''}{'z' if z else ''}{'p' if p else ''} x{offset:x}"
                )

                pc_offset = sext(offset, 9) << 1

                self.pc += pc_offset

                self.log(
                    f"  PC <- PC* {'+' if pc_offset > 0 else '-'} x{abs(pc_offset):x}"
                )

            case OP.ADD:
                dr = (inst >> 9) & 0x7
                sr1 = (inst >> 6) & 0x7

                src_type = inst & (1 << 5)

                if src_type:
                    src = sext(inst & 0x1F, 5)

                    self.log(f"ADD R{dr}, R{sr1}, #{src}")
                    self.log(f"  R{dr} <- R{sr1} {'+' if src > 0 else '-'} {abs(src)}")

                    self.regs[dr] = self.regs[sr1] + src

                else:
                    src = src = inst & 0x7

                    self.log(f"ADD R{dr}, R{sr1}, R{src}")
                    self.log(f"  R{dr} <- R{sr1} + R{src}")

                    self.regs[dr] = self.regs[sr1] + self.regs[src]

                self.setcc(dr)

            case OP.LDB:
                dr = (inst >> 9) & 0x7
                br = (inst >> 6) & 0x7

                offset = sext(inst & 0x3F, 6)

                self.log(f"LDB R{dr}, R{br}, x{offset:x}")
                self.log(
                    f"  R{dr} <- [R{br} {'+' if offset > 0 else '-'} x{abs(offset):x}]"
                )

                address = self.regs[br] + offset

                self.regs[dr] = sext(self.memory[address], 8)
                self.setcc(dr)

            case OP.STB:
                sr = (inst >> 9) & 0x7
                br = (inst >> 6) & 0x7

                offset = sext(inst & 0x3F, 6)

                self.log(f"STB R{sr}, R{br}, x{offset:x}")
                self.log(
                    f"  [R{br} {'+' if offset > 0 else '-'} x{abs(offset):x}] <- R{sr}.low"
                )

                self.memory[self.regs[br] + offset] = self.regs[sr] & 0xFF

            case OP.JSR:
                mode = inst & (1 << 11)

                self.regs[7] = self.pc

                if mode:
                    offset = sext(inst & 0x7FF, 11) << 1

                    self.log(f"JSR x{offset:x}")
                    self.log(
                        f"  R7 <- PC*\n  PC = PC* {'+' if offset > 0 else '-'} x{abs(offset):x}"
                    )

                else:
                    br = (inst >> 6) & 0x7

                    self.log(f"JSRR R{br}")
                    self.log(f"  R7 <- PC*\n  PC = R{br}")

                    self.pc = self.regs[br]

            case OP.AND:
                dr = (inst >> 9) & 0x7
                sr1 = (inst >> 6) & 0x7

                src_type = inst & (1 << 5)

                if src_type:
                    src = sext(inst & 0x1F, 5)

                    self.log(f"AND R{dr}, R{sr1}, #{src}")
                    self.log(f"  R{dr} <- R{sr1} & {src}")

                    self.regs[dr] = self.regs[sr1] & src

                else:
                    src = src = inst & 0x7

                    self.log(f"AND R{dr}, R{sr1}, R{src}")
                    self.log(f"  R{dr} <- R{sr1} & R{src}")

                    self.regs[dr] = self.regs[sr1] & self.regs[src]

                self.setcc(dr)

            case OP.LDW:
                dr = (inst >> 9) & 0x7
                br = (inst >> 6) & 0x7

                offset = sext(inst & 0x3F, 6) << 1

                self.log(f"LDW R{dr}, R{br}, x{offset:x}")
                self.log(
                    f"  R{dr} <- [R{br} {'+' if offset > 0 else '-'} x{abs(offset):x}]"
                )

                assert (
                    self.regs[br] & 1 == 0
                ), "LDW: base register must contain a word-aligned address (an even number)"

                address = self.regs[br] + offset

                self.regs[dr] = self.read_u16(address)

                self.setcc(dr)

            case OP.STW:
                sr = (inst >> 9) & 0x7
                br = (inst >> 6) & 0x7

                offset = sext(inst & 0x3F, 6) << 1

                self.log(f"STW R{sr}, R{br}, x{offset:x}")
                self.log(
                    f"[R{br} {'+' if offset > 0 else '-'} x{abs(offset):x}] <- R{sr}"
                )

                assert (
                    self.regs[br] & 1 == 0
                ), "STW: base register must contain a word-aligned address (an even number)"

                address = self.regs[br] + offset

                self.write_u16(address, self.regs[sr])

            case OP.RTI:
                self.log("RTI")
                assert (self.psr & (1 << 15)) == 0, "Privilege mode violation"
                self.log("  PC, PSR <- POP(2)")

                self.pc = self.read_u16(self.regs[STACK_REG])
                self.regs[STACK_REG] += 2
                temp = self.read_u16(self.regs[STACK_REG])
                self.regs[STACK_REG] += 2
                self.psr = temp

            case OP.XOR:
                dr = (inst >> 9) & 0x7
                sr1 = (inst >> 6) & 0x7
                mode = inst & (1 << 5)

                if mode:
                    data = sext(inst & 0x1F, 5)

                    self.log(f"XOR R{dr}, R{sr1}, x{data:x}")
                    self.log(f"  R{dr} <- R{sr1} ^ x{data:x}")

                    self.regs[dr] = self.regs[sr1] ^ data

                else:
                    sr2 = inst & 0x7

                    self.log(f"XOR R{dr}, R{sr1}, R{sr2}")
                    self.log(f"  R{dr} <- R{sr1} ^ R{sr2}")

                    self.regs[dr] = self.regs[sr1] ^ self.regs[sr2]

                self.setcc(dr)

            case OP.JMP:
                br = (inst >> 6) & 0x7

                self.log(f"JMP R{br}")

                assert (
                    self.regs[br] & 1
                ) == 0, "JMP: Base register must contain word-aligned address"

                self.log(f"  PC <- R{br}")

                self.pc = self.regs[br]

            case OP.SHF:
                dr = (inst >> 9) & 0x7
                sr = (inst >> 6) & 0x7
                offset = inst & 0xF

                right_switch = inst & (1 << 4)
                mode_switch = inst & (1 << 5)

                self.log(
                    f"SHF({mode_switch and 'a' or 'l'}, {right_switch and 'r' or 'l'}) R{dr}, R{sr}, x{offset:x}"
                )

                if not right_switch:
                    self.log(f"  R{dr} <- R{sr} << {offset}")
                    self.regs[dr] = (self.regs[sr] << offset) & 0xFFFF

                else:
                    self.log(f"  R{dr} <- R{sr} >> {offset}")
                    if mode_switch:
                        self.regs[dr] = self.regs[sr] >> offset

                    else:
                        mask = (2 ** (16 - offset)) - 1

                        self.regs[dr] = (self.regs[sr] >> offset) & mask

                self.setcc(dr)

            case OP.LEA:
                dr = (inst >> 9) & 7
                offset = sext(inst & 0x1FF, 9) << 1

                self.log(f"LEA R{dr}, x{offset:x}")

                self.regs[dr] = self.pc + offset
                self.setcc(dr)

                self.log(
                    f"  R{dr} <- x{self.regs[dr]:x} ({self.memory[self.regs[dr]]})"
                )

            case OP.TRAP:
                vector = inst & 0xFF

                self.regs[7] = self.pc

                self.log(f"TRAP x{vector:x}")
                self.log(f"  R7 <- PC*")

                self.trap(vector << 1)

            case _:
                raise RuntimeError(f"Invalid opcode: x{op:x}")

        self.print_state()
