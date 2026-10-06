# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

# pyright: reportImplicitOverride=false
# pyright: reportMissingTypeStubs=false

from collections.abc import Generator, Iterable
from typing import Any, cast
import yapl

from yapl import Parser, eof, regex, regex_captures, string_
from yapl.functional import F, Some, flatten, head, Nothing

from .ast import (
    BinLiteral,
    CharLiteral,
    DecLiteral,
    Directive,
    HexLiteral,
    Instruction,
    LabelHandler,
    OctLiteral,
    OffsetFn,
    Pointer,
    WeakPointer,
    Register,
    StringLiteral,
    ReferenceHandler,
    LabelDef,
    Program
)


eol = yapl.end_of_line()
ws = regex(r"[ \r\t]*").named("whitespace")
comment = regex(r";[^\n]*").named("comment")


def sym(s: str) -> Parser[str, str]:
    return cast(Parser[str, str], string_(s) << ws)


def lexeme[T](p: Parser[str, T]) -> Parser[str, T]:
    return p << ws


def cap1(r: str, n: int) -> Parser[str, str]:
    return lexeme(regex_captures(r, n)).with_(
        head  # pyright: ignore[reportReturnType, reportArgumentType]
    )


iconst = (
    cap1(r"0?[xX]([\da-fA-F]+)", 1).with_(HexLiteral).named("hex literal")
    | cap1(r"0?[oO]([0-7]+)", 1).with_(OctLiteral).named("octal literal")
    | cap1(r"0?[bB]([0-1]+)", 1).with_(BinLiteral).named("binary literal")
    | cap1(r"(0|[1-9]\d*)", 1).with_(DecLiteral).named("decimal literal")
)

string_const = lexeme(
    regex(r'"((?:[^"\\\x00-\x1F]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*)"')
).with_(StringLiteral).named("string literal")

char = lexeme(regex(r"'([^\'\\\x00-\x1F]|\\[\'\\/bfnrt]|\\x[0-9a-fA-F]{2})'")).with_(
    CharLiteral
).named("char literal")


def _reg(i: int, n: str):
    return sym(f"${n}").as_(Register(n, i))


register = (
    _reg(0, "r0")
    | _reg(1, "r1")
    | _reg(2, "r2")
    | _reg(3, "r3")
    | _reg(4, "r4")
    | _reg(5, "r5")
    | _reg(6, "r6")
    | _reg(7, "r7")
    | _reg(8, "a")
    | _reg(9, "x")
    | _reg(10, "y")
    | _reg(11, "sp")
).named("register specifier")

label_name = lexeme(regex(r"[_a-z]\w*")).with_(LabelHandler.from_name).named("label")


pointer_op: Parser[str, OffsetFn] = (
    (
        sym("+")
        | sym("-")
        | sym("*")
        | sym("%")
        | sym("<<")
        | sym(">>")
        | sym("&")
        | sym("^")
        | sym("|")
    )
    .named("pointer operator")
    .with_(lambda v: cast(OffsetFn, v))
)

immediate = string_("#") >> iconst  # pyright: ignore[reportUnknownVariableType]


pointer_term = (  # pyright: ignore[reportUnknownVariableType]
    immediate | register | iconst.with_(WeakPointer) | label_name
).named("pointer term")



memref = (
    sym("[")
    >> (
        pointer_term.expect(sym("]"))
        | (
            (pointer_term & pointer_op & pointer_term)
            @ ReferenceHandler
        )
    )
    << sym("]")
).with_(Pointer).named("memory reference")

label = lexeme(label_name << string_(":")).with_(LabelDef.define)

opcode = lexeme(
    regex(r"ld|inc|cmp|jne|sub|call")
).named("instruction mnemonic")

operand = pointer_term | label_name | memref | char  # pyright: ignore[reportUnknownVariableType]

instruction = (opcode & operand[:]) @ Instruction

directive_operand = label_name | iconst | char | string_const

directive_name = lexeme(string_(".") >> regex(r"org|asciiz|space|byte"))

directive = (directive_name & directive_operand[:]) @ Directive

term = (instruction | directive | label) << ~lexeme(comment) << eol

empty_line = (comment | ws).as_(Nothing) << eol

line = ws >> (label | term).with_(Some) | empty_line

program = (line[:]).filter_option().with_(Program) << eof()
