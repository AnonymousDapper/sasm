# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

from sasm.assembler import Assembler, AstTransformer
from sasm.ast import AstNode

from yapl.functional import is_some

from .bytecode import BytecodeCompiler

from .ast import _IntegerLiteral, Directive, Instruction, Program, StringLiteral, SymbolTable, LabelledProgram


class SymbolTableTransformer(AstTransformer):
    def __init__(self, table: SymbolTable, program: LabelledProgram):
        self.table = table
        self.program = program
        self.index = 0

    def calculate_term_size(self, term: Instruction | Directive):
        match term:
            case Instruction(_, _):
                return 2

            case Directive(name, param):
                return self.visit_Directive(term)

    def process(self, program: Program):
        for term in program.lines:
            if is_some(term.label):
                self.table.add(term.label.unwrap().name, self.index)

            self.program.add_line(term.item)

            width = self.calculate_term_size(term.item)

            self.index += width


    def visit_Directive(self, node: Directive):
        match node.name:
            case "BLKW":
                if isinstance(node.param, _IntegerLiteral):
                    return node.param.value

                raise TypeError(f"Invalid operand for directive {node.name}: {node.param.__class__.__name__} ({node.param!r})")

            case "STRINGZ":
                if isinstance(node.param, StringLiteral):
                    length = len(node.param.value) + 1

                    return length + (length % 2)

                raise TypeError(f"Invalid operand for directive {node.name}: {node.param.__class__.__name__} ({node.param!r})")

            case "FILL":
                if isinstance(node.param, _IntegerLiteral):
                    return node.param.value.bit_length() // 8

                raise TypeError(f"Invalid operand for directive {node.name}: {node.param.__class__.__name__} ({node.param!r})")

            case "ORIG":
                if isinstance(node.param, _IntegerLiteral):
                    self.index = node.param.value
                    return 0

                raise TypeError(f"Invalid operand for directive {node.name}: {node.param.__class__.__name__} ({node.param!r})")

            case "END":
                if node.param is None:
                    return 0
                raise TypeError(f"Invalid operand for directive {node.name}: {node.param.__class__.__name__} ({node.param!r})")

            case _:
                raise ValueError(f"Unknown directive: {node.name}")





class LC3Assembler(Assembler):
    def __init__(self):
        self.pass_one_result = LabelledProgram()
        self.symbol_table = SymbolTable()
        self.compiler = BytecodeCompiler(self.symbol_table)

    def assemble(self, root: Program):
        pass_one_transformer = SymbolTableTransformer(self.symbol_table, self.pass_one_result)

        pass_one_transformer.process(root)


        self.symbol_table.dump_symbols()

        for inst in self.pass_one_result.lines:
            match inst:
                case Directive(name, param):
                    self.compiler.process_directive(name, param)

                case Instruction(name, params):
                    self.compiler.process_instruction(name, *params)

    def get_bytes(self):
        return self.compiler.get_bytes()
