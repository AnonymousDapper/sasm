# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

# from __future__ import annotations
from array import array
from collections.abc import Callable
import inspect

from .consts import OP

from .ast import _IntegerLiteral, Directive, HexLiteral, Instruction, Label, Register, StringLiteral, SymbolTable


def roundtrip(n: int, length: int, signed = False):
    b = n.to_bytes(length, byteorder="little", signed=signed)

    return int.from_bytes(b, byteorder="little", signed=False)

class InstructionDef:
    name: str
    arity: int

    caller: Callable[..., None]

class DirectiveDef:
    name: str
    takes_param: bool

    caller: Callable[..., None]

class BytecodeCompiler:
    instruction_map: dict[str, type[InstructionDef]] = {}
    directive_map: dict[str, type[DirectiveDef]] = {}
    symtab: SymbolTable
    index: int
    buffer: array[int]



    def __init__(self, symtab: SymbolTable):
        self.index = 0
        self.buffer = array('B')

        self.symtab = symtab

    def get_bytes(self):
        return self.buffer.tobytes()

    @classmethod
    def instruction(cls, inst: type[InstructionDef]):
        name = inst.name

        if name not in cls.instruction_map:
            assert inst.arity == (len(inspect.signature(inst.caller).parameters) - 1), "Arity mismatch in instruction definition: {name}"

            cls.instruction_map[name] = inst

        else:
            raise ValueError(f"duplicate instruction definition of {name} at {inst.__name__}")


    @classmethod
    def directive(cls, defs: type[DirectiveDef]):
        name = defs.name

        if name not in cls.directive_map:
            assert int(defs.takes_param) == (len(inspect.signature(defs.caller).parameters) - 1), "Arity mismatch in directive definition: {name}"

            cls.directive_map[name] = defs

        else:
            raise ValueError(f"duplicate directive definition of {name} at {defs.__name__}")

    def grow(self, amount: int):
        assert amount > 0, "Cannot grow negative"

        expanded = bytearray(amount)

        self.buffer.extend(expanded)

    def grow_to(self, index: int):
        buf_info = self.buffer.buffer_info()
        self.grow(index  - buf_info[1])

    def write_byte(self, data: int):
        self.buffer.append(data)
        self.index += 1

    def write_bytes(self, data: bytes):
        for x in data:
            self.write_byte(x)

    def write_short(self, short: int):
        hi = (short >> 8)
        lo = short & 0xff

        self.write_byte(lo)
        self.write_byte(hi)

    def process_directive(self, name: str, param: Directive.Operand):
        if name in self.directive_map:
            defs = self.directive_map[name]

            if defs.takes_param:
                param_type: type[Directive.Operand] = tuple(map(lambda p: p.annotation, inspect.signature(defs.caller).parameters.values()))[1]

                if isinstance(param, param_type):

                    defs.caller(self, param)

                else:
                    raise TypeError(f"Type mismatch when calling directive {name}: expected {param_type}, got {type(param)}")

            elif param is None:
                defs.caller(self)

            else:
                raise TypeError(f"Arity mismatch when calling directive {name}: directive takes no parameters, got {param}")


        else:
            raise TypeError(f"Directive {name} is not implemented")

    def process_instruction(self, name: str, *params: Instruction.Operand):
        if name in self.instruction_map:
            inst = self.instruction_map[name]

            params = tuple(filter(lambda x: x is not None, params))

            if len(params) == inst.arity:
                param_types = tuple(map(lambda c: c.__class__, params))
                expected_types: tuple[type[Instruction.Operand],...] = tuple(map(lambda p: p.annotation, inspect.signature(inst.caller).parameters.values()))[1:]

                for i, (p, t) in enumerate(zip(param_types, expected_types), start=1):
                    if not issubclass(p, t):
                        raise TypeError(f"Type mismatch when calling instruction {name} at parameter {i}: expected {t}, got {p}")

                inst.caller(self, *params)

            else:
                print(params)
                raise TypeError(f"Arity mismatch when calling instruction {name}: expected {inst.arity} params, got {len(params)}")


        else:
            raise TypeError(f"Instruction {name} is not implemented")


# ----------
# Directives
# ----------

@BytecodeCompiler.directive
class OriginDirective(DirectiveDef):
    name = "ORIG"
    takes_param = True

    @staticmethod
    def caller(machine: BytecodeCompiler, location: _IntegerLiteral):
        val = location.value

        assert val > machine.index, "Cannot place data origin before current index"

        #machine.grow_to(val)

        #machine.index = val


@BytecodeCompiler.directive
class StringzDirective(DirectiveDef):
    name = "STRINGZ"
    takes_param = True

    @staticmethod
    def caller(machine: BytecodeCompiler, string: StringLiteral):
        data = bytes(string.value, "utf-8")
        machine.write_bytes(data)
        machine.write_byte(0)

        if machine.index % 2 == 1:
            machine.write_byte(0)

@BytecodeCompiler.directive
class FillDirective(DirectiveDef):
    name = "FILL"
    takes_param = True

    @staticmethod
    def caller(machine: BytecodeCompiler, item: _IntegerLiteral):
        byte_len = item.value.bit_length() // 8 + 1
        data = item.value.to_bytes(byte_len, byteorder="little", signed=False)

        machine.write_bytes(data)

@BytecodeCompiler.directive
class EndDirective(DirectiveDef):
    name = "END"
    takes_param = False
    @staticmethod
    def caller(machine: BytecodeCompiler):
        ...



# ------------
# Instructions
# ------------

@BytecodeCompiler.instruction
class LoadEffective(InstructionDef):
    name = "LEA"
    arity = 2

    @staticmethod
    def caller(machine: BytecodeCompiler, reg: Register, label: Label):
        opcode = OP.LEA << 12
        dr = (reg.index & 0x7) << 9

        absolute = machine.symtab.get(label.name)

        relative = absolute - (machine.index + 2)

        offset = roundtrip(relative >> 1, 2, True)

        op = opcode | dr | (offset & 0x1ff)

        machine.write_short(op)

@BytecodeCompiler.instruction
class Trap(InstructionDef):
    name = "TRAP"
    arity = 1

    @staticmethod
    def caller(machine: BytecodeCompiler, vector: _IntegerLiteral):
        opcode = OP.TRAP << 12

        trapvect = (vector.value) & 0xff

        op = opcode | trapvect

        machine.write_short(op)

@BytecodeCompiler.instruction
class PutsTrap(InstructionDef):
    name = "PUTS"
    arity = 0

    @staticmethod
    def caller(machine: BytecodeCompiler):
        machine.process_instruction("TRAP", HexLiteral('22'))

@BytecodeCompiler.instruction
class HaltTrap(InstructionDef):
    name = "HALT"
    arity = 0

    @staticmethod
    def caller(machine: BytecodeCompiler):
        machine.process_instruction("TRAP", HexLiteral('25'))
