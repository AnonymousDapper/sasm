# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

REG_COUNT = 8

MEMORY_SIZE = 1 << 16

STACK_REG = 6


class AddressMap:
    TrapVector = (0x0000, 0x01FF)
    InterruptVector = (0x0200, 0x03FF)
    OsSuperStack = (0x0400, 0x2FFF)
    UserSpace = (0x3000, 0xFDFF)
    DeviceRegister = (0xFE00, 0xFFFF)


class OP:
    BR = 0x0
    ADD = 0x1
    LDB = 0x2
    STB = 0x3
    JSR = 0x4
    AND = 0x5
    LDW = 0x6
    STW = 0x7
    RTI = 0x8
    XOR = 0x9
    # unused 0xa
    # unused 0xb
    JMP = 0xC
    SHF = 0xD
    LEA = 0xE
    TRAP = 0xF
