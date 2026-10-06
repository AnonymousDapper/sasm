# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper


from enum import StrEnum

from sasm.ast import AstNode
from sasm.exceptions import ParserException
from yapl.functional import Option, is_some

RADIX_FMT_MAP = {
    16: "x",
    10: "d",
    2:  "b",
}


class SyntaxException(ParserException): ...


class Literal[T](AstNode):
    __slots__ = ("value",)
    __match_args__ = ("value",)
    value: T


class _IntegerLiteral(Literal[int]):
    __slots__ = ("value", "base")
    __match_args__ = ("value",)
    value: int
    base: int

    def __init__(self, source: str):
        try:
            self.value = int(source, self.base)
        except ValueError as e:
            raise SyntaxException(
                f"invalid value {source!r} for base {self.base} integer literal"
            ) from e

    def __init_subclass__(cls, base: int):
        cls.base = base

    def __repr__(self):
        return f"{self.value:#{RADIX_FMT_MAP[self.base]}}"


class HexLiteral(_IntegerLiteral, base=16):
    __slots__ = ("value", "base")
    __match_args__ = ("value",)
    value: int
    base: int


class DecLiteral(_IntegerLiteral, base=10):
    __slots__ = ("value", "base")
    __match_args__ = ("value",)
    value: int
    base: int


class BinLiteral(_IntegerLiteral, base=2):
    __slots__ = ("value", "base")
    __match_args__ = ("value",)
    value: int
    base: int


class StringLiteral(Literal[str]):
    __slots__ = ("value",)
    __match_args__ = ("value",)
    value: str

    def __init__(self, value: str):
        try:
            self.value = bytes(value, "utf-8").decode("unicode_escape")
        except Exception as e:
            raise SyntaxException(f"malformed string '{value}'") from e

    def __repr__(self):
        return f"'{self.value.encode('unicode_escape').decode('utf-8')}'"


class Register(AstNode):
    __slots__ = ("label", "index")
    __match_args__ = ("label", "index")
    label: str
    index: int

    def __init__(self, label: str, index: int):
        assert index < 8, "Register index cannot be greater than 7"

        self.label = label
        self.index = index

    def __repr__(self):
        return f"<{self.label}:{self.index}>"


class Label(AstNode):
    __slots__ = ("name",)
    __match_args__ = ("name",)
    name: str

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"<label {self.name}>"


class LabelDef(AstNode):
    __slots__ = ("name",)
    __match_args__ = ("name",)
    name: str

    def __init__(self, name: str):
        self.name = name

    @classmethod
    def define(cls, label: Label):
        return cls(label.name)


class Directive(AstNode):
    __slots__ = ("name", "param")
    __match_args__ = ("name", "param")

    type Operand = _IntegerLiteral | StringLiteral | None

    name: str
    param: Operand

    def __init__(self, name: str, param: Operand = None):
        self.name = name
        self.param = param

    def __repr__(self):
        return f".{self.name}{f' [{self.param!r}]' if self.param is not None else ''}"


class Instruction(AstNode):
    __slots__ = ("name", "params")
    __match_args__ = ("name", "params")

    type Operand = _IntegerLiteral | Register | Label | BranchMode | None

    name: str
    params: tuple[Operand, ...]

    def __init__(self, name: str, *params: Operand):
        self.name = name
        self.params = tuple(params)

    def __repr__(self):
        params = tuple(filter(lambda x: x is not None, self.params))

        return f"{self.name}{f' ({', '.join(repr(p) for p in params)})' if len(params) > 0 else ''}"


class Term(AstNode):
    __slots__ = ("label", "item")
    __match_args__ = ("label", "item")
    label: Option[LabelDef]
    item: Instruction | Directive

    def __init__(self, label: Option[LabelDef], item: Instruction | Directive):
        self.label = label
        self.item = item

    def __repr__(self):
        label = "\t"

        if is_some(self.label):
            label = repr(self.label.unwrap())

        return f"{label} {self.item!r}"


class Program(AstNode):
    __slots__ = ("lines",)
    lines: list[Term]

    def __init__(self, lines: list[Term]):
        self.lines = lines

    def __repr__(self):
        return f"<Program {len(self.lines)} lines>"

class LabelledProgram(AstNode):
    __slots__ = ("lines",)
    lines: list[Instruction | Directive]

    def __init__(self):
        self.lines = []

    def add_line(self, item: Instruction | Directive):
        self.lines.append(item)




class BranchMode(StrEnum):
    N = "n"
    Z = "z"
    P = "p"
    Zp = "zp"
    Np = "np"
    Nz = "nz"
    Nzp = "nzp"


class SymbolTable:
    __slots__ = ("map",)
    map: dict[str, int]

    def __init__(self):
        self.map = {}

    def add(self, name: str, index: int):
        if name not in self.map:
            self.map[name] = index

        else:
            raise ValueError(f"duplicate symbol definition: {name}")

    def get(self, name: str):
        if name in self.map:
            return self.map[name]

        else:
            raise ValueError("undefined reference to {name}")

    def dump_symbols(self):
        for k,v in self.map.items():
            print(f"{k} => {v: >#6x}")

