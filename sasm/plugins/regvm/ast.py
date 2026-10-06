# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

# pyright: reportImplicitOverride=false

from ast import literal_eval
from typing import Callable, Literal


from sasm.exceptions import ParserException
from sasm.ast import AstNode

class LabelCountException(ParserException): ...

__all__ = (
    "HexLiteral",
    "DecLiteral",
    "OctLiteral",
    "BinLiteral",
    "CharLiteral",
    "FloatLiteral",
    "StringLiteral",
    "Pointer",
    "WeakPointer",
    "Register",
    "Label",
    "LabelHandler",
    "Directive",
    "Instruction",
)


type ImmediateParam = _IntegerLiteral | Label

type DirectiveParam = ImmediateParam | StringLiteral

type InstructionParam = ImmediateParam | ReferenceHandler

type OffsetOperand = _IntegerLiteral | Register | WeakPointer | Label

type OffsetFn = Literal["+"] | Literal["-"] | Literal["*"] | Literal["%"] | Literal[
    "<<"
] | Literal[">>"] | Literal["&"] | Literal["^"] | Literal["|"]

type RefType = _IntegerLiteral | WeakPointer | Register | ReferenceHandler

RADIX_FMT_MAP = {
    16: "x",
    10: "d",
    8: "o",
    2: "b",
    # 0: 'c' # omitted
}


PointerOperators: dict[OffsetFn, Callable[[int, int], int]] = {
    "+": lambda l, r: l + r,
    "-": lambda l, r: l - r,
    "*": lambda l, r: l * r,
    "%": lambda l, r: l % r,
    "<<": lambda l, r: l << r,
    ">>": lambda l, r: l >> r,
    "&": lambda l, r: l & r,
    "^": lambda l, r: l ^ r,
    "|": lambda l, r: l | r
}


# ---------------------
# Literal Handlers
# ---------------------


class _Literal[T](AstNode):
    __slots__ = ("value",)
    value: str

    def __init__(self, value: str):
        self.value = value

    def get_source(self):
        return self.value

    def __repr__(self):
        return f"<literal {self}>"

    def __resolve__(self) -> T:
        return NotImplemented


class _IntegerLiteral(_Literal[int]):
    __slots__ = ("base", "value")
    base: int  # pyright: ignore[reportUninitializedInstanceVariable]

    def __init__(self, value: str):
        assert type(value) is str
        super().__init__(value)

    def __init_subclass__(cls: type["_IntegerLiteral"], base: int):
        cls.base = base

    def resolve(self):
        return int(self.value, self.base)

    def __repr__(self):
        return f"{self.resolve():#{RADIX_FMT_MAP[self.base]}}"


class HexLiteral(_IntegerLiteral, base=16):
    __slots__ = ("base", "value")


class DecLiteral(_IntegerLiteral, base=10):
    __slots__ = ("base", "value")


class OctLiteral(_IntegerLiteral, base=8):
    __slots__ = ("base", "value")


class BinLiteral(_IntegerLiteral, base=2):
    __slots__ = ("base", "value")


class CharLiteral(_IntegerLiteral, base=0):
    __slots__ = ("base", "value")

    def resolve(self):
        literal = literal_eval(self.value)  # pyright: ignore[reportAny]
        assert isinstance(literal, str)
        return ord(literal)

    def __repr__(self):
        return f"{self.resolve():c}".encode("unicode_escape").decode("utf-8)")


class FloatLiteral(_Literal[float]):
    __slots__ = ("value",)

    def __init__(self, value: str):
        assert type(value) is str and value.lower() not in (
            "nan",
            "-nan",
            "inf",
            "-inf",
        )

        super().__init__(value)

    def resolve(self):
        return float(self.value)

    def __repr__(self):
        return f"{self.value:g}"


class StringLiteral(_Literal[bytes]):
    __slots__ = ("value",)

    def __init__(self, value: str):
        assert type(value) is str
        super().__init__(value)

    def resolve(self):
        literal = literal_eval(self.value)  # pyright: ignore[reportAny]
        assert isinstance(literal, str)
        return literal.encode("utf-8")

    def __repr__(self):
        return f"{self.resolve()}".encode("unicode_escape").decode("utf-8")


# ---------------------
# Reference Handlers
# ---------------------


class ReferenceHandler(AstNode):
    __slots__ = ("left", "right", "op")
    left: OffsetOperand
    right: OffsetOperand
    op: OffsetFn

    def __init__(self, left: OffsetOperand, op: OffsetFn, right: OffsetOperand):
        self.left = left
        self.right = right
        self.op = op

    def __repr__(self):
        return f"ref[ {self.left} {self.op} {self.right} ]"


class Pointer(ReferenceHandler):
    __slots__ = ("origin",)
    origin: RefType

    def __init__(self, origin: RefType):  # pyright: ignore[reportMissingSuperCall]
        assert isinstance(origin, RefType.__value__)

        self.origin = origin

    def __repr__(self):
        return f"ptr[ {self.origin!r} ]"


class WeakPointer(Pointer):
    __slots__ = ("origin_ref",)
    origin_ref: _IntegerLiteral

    def __init__(self, ref: _IntegerLiteral):  # pyright: ignore[reportMissingSuperCall]
        self.origin_ref = ref


    def __repr__(self):
        return f"&({self.origin_ref!r})"


class Register(ReferenceHandler):
    __slots__ = ("id", "label")
    id: int
    label: str

    def __init__(self, label: str, _id: int):  # pyright: ignore[reportMissingSuperCall]
        assert type(label) is str
        assert type(_id) is int

        self.id = _id
        self.label = label

    def get_label(self):
        return self.label

    def __repr__(self):
        return f"<reg {self.label}:{self.id}>"


# ---------------------
# Label Handler
# ---------------------


class Label(ReferenceHandler):
    __slots__ = ("name",)
    __match_args__ = ("name",)
    name: str

    def __init__(self, name: str):  # pyright: ignore[reportMissingSuperCall]
        self.name = name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"<label {self.name}>"


class LabelDef(Label):
    __slots__ = ("name",)
    __match_args__ = ("name",)

    @classmethod
    def define(cls, label: Label):
        return cls(label.name)

class LabelHandler:
    # __slots__ = ("used_names", "name_map")
    used_names: set[str] = set()
    name_map: dict[str, "Label"] = {}

    @classmethod
    def from_name(cls, name: str):
        if name in cls.used_names:
            return cls.name_map[name]

        label = Label(name)
        print(f"NEW:", label)
        cls.used_names.add(name)
        cls.name_map[name] = label

        return label


# ---------------------
# Directive Handler
# ---------------------


class Directive(AstNode):
    __slots__ = ("name", "params")
    __match_args__ = ("name", "params")

    name: str
    params: tuple[DirectiveParam]

    def __init__(self, name: str, *params):
        assert type(name) is str
        # assert all(isinstance(p, DirectiveParam.__value__) for p in params)

        self.name = name
        self.params = tuple(params)

    def __repr__(self):
        return f".{self.name}[{' '.join(repr(p) for p in self.params)}]"


# ---------------------
# Instruction Handler
# ---------------------
class Instruction(AstNode):
    __slots__ = ("name", "params")
    __match_args__ = ("name", "params")
    name: str
    params: tuple[InstructionParam]

    def __init__(self, name: str, *params):
        assert type(name) is str
        # assert all(isinstance(p, InstructionParam.__value__) for p in params)

        self.name = name
        self.params = tuple(params)

    def __repr__(self):
        return f"{self.name}[{', '.join(repr(p) for p in self.params)}]"



class Program(AstNode):
    __slots__ = ("lines",)
    lines: list[Instruction | LabelDef | Directive]

    def __init__(self, lines: list[Instruction | LabelDef | Directive]):
        self.lines = lines

    def __repr__(self):
        return f"<Program {len(self.lines)} lines>"
