# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

from sasm.assembler import Assembler
from sasm.ast import AstNode
from sasm.exceptions import AssemblerException


from .ast import BinLiteral, CharLiteral, DecLiteral, Directive, HexLiteral, Instruction, Label, OctLiteral, Pointer, Program, LabelDef, ReferenceHandler, Register, StringLiteral, WeakPointer
from .bytecode import BytecodeCompiler


class UnknownNodeException(AssemblerException): ...


class RegVmAssembler(Assembler):
	def __init__(self, root: Program):
		self.program = root
		self.compiler = BytecodeCompiler()

	def run(self):
		for node in self.program.lines:
			self.visit(node)

	def visit(self, node: AstNode):
		fn = getattr(self, f"visit_{node.__class__.__name__}", None)

		if fn:
			return fn(node)

		else:
			raise UnknownNodeException(node.__class__.__name__)

	def visit_HexLiteral(self, node: HexLiteral):
		return node

	def visit_DecLiteral(self, node: DecLiteral):
		return node

	def visit_OctLiteral(self, node: OctLiteral):
		return node

	def visit_BinLiteral(self, node: BinLiteral):
		return node

	def visit_CharLiteral(self, node: CharLiteral):
		return node

	def visit_StringLiteral(self, node: StringLiteral):
		return node

	def visit_ReferenceHandler(self, node: ReferenceHandler):
		return node

	def visit_Pointer(self, node: Pointer):
		return node

	def visit_WeakPointer(self, node: WeakPointer):
		return node

	def visit_Register(self, node: Register):
		return node

	def visit_Label(self, node: Label):
		return self.compiler.get_label(node)


	def visit_LabelDef(self, node: LabelDef):
		self.compiler.define_label(node)

	def visit_Instruction(self, node: Instruction):
		opcode = self.compiler.check_instruction(node)
		params = [self.visit(p) for p in node.params]

		self.compiler.write_instruction(opcode, *params)

	def visit_Directive(self, node: Directive):
		if self.compiler.check_directive(node):
			params = [self.visit(p) for p in node.params]

			self.compiler.write_directive(node.name, *params)
