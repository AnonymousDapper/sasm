# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

#from __future__ import annotations

import inspect
from itertools import count
from typing import Callable, Protocol

from .ast import BinLiteral, DecLiteral, Directive, HexLiteral, Instruction, Label, _IntegerLiteral, InstructionParam, LabelDef, OctLiteral, Pointer, Register, DirectiveParam, StringLiteral


class InstructionDef:
	Name: str
	Arity: int
	Variants: dict[tuple[type[InstructionParam],...], int]

class DirectiveDef:
	Name: str
	Arity: int
	Types: tuple[type[DirectiveParam],...]
	Caller: Callable[..., None]

class BytecodeCompiler:
	instruction_map: dict[str, type[InstructionDef]] = {}
	directive_map: dict[str, type[DirectiveDef]] = {}
	label_map: dict[str, int] = {}
	unresolved_label_map: set[str] = set()

	def __init__(self):
		self.index_iter = iter(count())
		self.index = next(self.index_iter)
		self.buffer = []
		self.buffer_len = 0

	@classmethod
	def instruction(cls, def_: type[InstructionDef]) -> None:
		name = def_.Name

		if name not in cls.instruction_map:
			assert len(def_.Variants) > 0, "Instruction definition must have at least one variant"
			assert all(len(v) == def_.Arity for v in def_.Variants.keys())

			cls.instruction_map[name] = def_

		else:
			raise ValueError(f"duplicate instruction definition of {name} at {def_.__name__}")

	@classmethod
	def directive(cls, def_: type[DirectiveDef]):
		name = def_.Name

		if name not in cls.directive_map:
			params: tuple[type[DirectiveParam], ...] = tuple(map(lambda p: p.annotation, list(inspect.signature(def_.Caller).parameters.values())[1:]))

			def_.Types = params

			cls.directive_map[name] = def_

		else:
			raise ValueError(f"duplicate directive definition of {name} at {def_.__name__}")


	def advance(self):
		self.index = next(self.index_iter)
		return self.index

	def advance_to(self, index: int):
		assert index > self.index, "Cannot advance backwards"

		self.index_iter = iter(count(index))
		self.advance()

	def grow_to(self, size: int):
		assert size > self.buffer_len, "Cannot grow by a negative amount"

		self.grow(size - self.buffer_len)

	def grow(self, amount: int):
		assert amount > 0, "Cannot grow by less than 1"

		self.buffer += bytearray(amount)
		self.buffer_len = len(self.buffer)

	def define_label(self, label: LabelDef):
		print("Label:", f"{label.name}")
		if label.name in self.label_map:
			raise ValueError(f"duplicate label definition of {label} at index {self.index}")

		self.label_map[label.name] = self.index

		if label.name in self.unresolved_label_map:
			for (i, b) in enumerate(self.buffer):
				if b == label.name:
					self.buffer[i] = self.index

			self.unresolved_label_map.remove(label.name)

	def get_label(self, label: Label):
		print(f"Get label: {label.name}:{label.id} [{self.label_map.get(label.name)}]")
		if label.name in self.label_map:
			return self.label_map[label.name]

		else:
			self.unresolved_label_map.add(label.name)
			return label.name

	def check_instruction(self, inst: Instruction):
		if inst.name in self.instruction_map:
			inst_def = self.instruction_map[inst.name]

			if inst_def.Arity == len(inst.params):
				params = tuple(map(lambda c: c.__class__, inst.params))
				for (ts, opcode) in inst_def.Variants.items():
					if all(issubclass(p, t) for (p, t) in zip(params, ts)):
						return opcode

				raise TypeError(f"Instruction {inst.name} has no implemention for {params}")

			else:
				raise TypeError(f"Invalid arity for instruction {inst.name}: expected {inst_def.Arity}, got {len(inst.params)}")

		else:
			raise TypeError(f"Instruction {inst.name} not implemented")

	def write_instruction(self, opcode: int, *params):
		print("Instruction:", opcode, params)
		inst_length = 1 + len(params)
		if (self.index + inst_length) >= self.buffer_len:
			self.grow(inst_length)

		for _ in range(inst_length):
			self.advance()

	def check_directive(self, dir_: Directive):
		if dir_.name in self.directive_map:
			dir_def = self.directive_map[dir_.name]

			if dir_def.Arity == len(dir_.params):
				params = tuple(map(lambda c: c.__class__, dir_.params))
				if all(issubclass(p, t) for (p,t) in zip(params, dir_def.Types)):
					return True

				else:
					raise TypeError(f"Directive {dir_def.Name} has no implementation for {params}")

			else:
				raise TypeError(f"Invalid arity for directive {dir_def.Name}: expected {dir_def.Arity}, got {len(dir_.params)}")

		else:
			raise TypeError(f"Directive {dir_.name} not implemented")

	def write_directive(self, name: str, *params):
		print("Directive:", name, params)

		dir_def = self.directive_map[name]
		dir_def.Caller(self, *params)


	def write_byte(self, data: int):
		if self.index == self.buffer_len:
			self.grow(1)

		self.buffer[self.index] = data
		self.advance()

	def write_bytes(self, data: bytes):
		self.grow(len(data))

		for x in data:
			self.write_byte(x)

# -----------------------
# Instruction Definitions
# -----------------------

@BytecodeCompiler.instruction
class LoadInst(InstructionDef):
	Name = "ld"
	Arity = 2
	Variants = {
		(Register, Label): 0x40,
		(Register, _IntegerLiteral): 0x41,
		(Register, Pointer): 0x42,
		(Register, Register): 0x43
	}

@BytecodeCompiler.instruction
class IncrementInst(InstructionDef):
	Name = "inc"
	Arity = 1
	Variants = {
		(Register,): 0x50
	}

@BytecodeCompiler.instruction
class CompareInst(InstructionDef):
	Name = "cmp"
	Arity = 1
	Variants = {
		(Register,): 0x60,
		(_IntegerLiteral,): 0x61,
		(Pointer,): 0x62
	}

@BytecodeCompiler.instruction
class JumpNotEqualInst(InstructionDef):
	Name = "jne"
	Arity = 1
	Variants = {
		(Label,): 0x5a
	}

@BytecodeCompiler.instruction
class SubtractInst(InstructionDef):
	Name = "sub"
	Arity = 2
	Variants = {
		(Register, Register): 0x70
	}

@BytecodeCompiler.instruction
class CallInst(InstructionDef):
	Name = "call"
	Arity = 1
	Variants = {
		(_IntegerLiteral,): 0xff,
	}



# -------------------------
# Directive Implementations
# -------------------------
@BytecodeCompiler.directive
class OrgDirective(DirectiveDef):
	Name = "org"
	Arity = 1

	@staticmethod
	def Caller(machine: BytecodeCompiler, location: _IntegerLiteral):
		val = location.resolve()

		assert val > machine.index, "Cannot .org before compiler index"

		machine.grow_to(val)
		machine.advance_to(val)


@BytecodeCompiler.directive
class AsciizDirective(DirectiveDef):
	Name = "asciiz"
	Arity = 1

	@staticmethod
	def Caller(machine: BytecodeCompiler, data: StringLiteral):
		machine.write_bytes(data.resolve())

@BytecodeCompiler.directive
class ByteDirective(DirectiveDef):
	Name = "byte"
	Arity = 1

	@staticmethod
	def Caller(machine: BytecodeCompiler, data: _IntegerLiteral):
		machine.write_byte(data.resolve())
