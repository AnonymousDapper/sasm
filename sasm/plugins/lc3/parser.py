# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper


import re

from yapl import Parser, end_of_line, eof, pure, regex, regex_captures, seq, string_
from yapl.functional import Err, Nothing, Ok, Some, head
from yapl.parser import Fail, ParseResult, ParserInput, Succeed

from .ast import (
    BinLiteral,
    BranchMode,
    DecLiteral,
    Directive,
    HexLiteral,
    Instruction,
    Label,
    Program,
    Register,
    StringLiteral,
    Term,
)

RE_FLAG = re.ASCII | re.IGNORECASE

RE_WS = re.compile(r"[ \t]*")
RE_COMMENT = re.compile(r";[^\n]*")

RE_LABEL = re.compile(r"[a-z][\w\d]*", RE_FLAG)

RE_HEXLIT = re.compile(r"x([0-9a-f]+)", RE_FLAG)
RE_DECLIT = re.compile(r"#(-?[0-9]+)", RE_FLAG)
RE_BINLIT = re.compile(r"b([01]+)", RE_FLAG)

RE_DATALIT = re.compile(r"\d+", RE_FLAG)

RE_STRING = re.compile(
    r'"((?:[^"\\\x00-\x1F]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*)"', RE_FLAG
)

# Helpers
# -------


def append[S, T](seq: Parser[S, list[T]], a: Parser[S, T]):
    def inner(xs: ParserInput[S]) -> ParseResult[S, list[T]]:
        match seq.run(xs):
            case Ok(v):
                match a.run(xs):
                    case Ok(v2):
                        return Succeed(v.item + [v2.item], xs)

                    case Err(e2):
                        return Fail(a.get_label(), "parser failed in `append`", xs)

            case Err(e):
                return Fail(seq.get_label(), "parser failed in `append`", xs)

    return Parser(inner, f"{seq.get_label()} APPEND {a.get_label()}")


eol = end_of_line()
ws = regex(RE_WS).named("whitespace")
comment = regex(RE_COMMENT).named("comment")


def lexeme[T](p: Parser[str, T]) -> Parser[str, T]:
    return p << ws


def sym(s: str) -> Parser[str, str]:
    return string_(s) << ws


def cap1(pat: str | re.Pattern[str], n: int) -> Parser[str, str]:
    return lexeme(regex_captures(pat, n)).with_(head)


def reg(i: int, n: str):
    return sym(n).as_(Register(n, i)).named(n)


# Primitives
# ----------

iconst = (
    cap1(RE_HEXLIT, 1).with_(HexLiteral).named("hex literal")
    | cap1(RE_DECLIT, 1).with_(DecLiteral).named("decimal literal")
    | cap1(RE_BINLIT, 1).with_(BinLiteral).named("binary literal")
)

dataconst = lexeme(regex(RE_DATALIT)).with_(DecLiteral).named("decimal integer")

string_const = cap1(RE_STRING, 1).with_(StringLiteral).named("string literal")


label = lexeme(regex(RE_LABEL)).with_(Label).named("label identifier")


register = (
    reg(0, "R0")
    | reg(1, "R1")
    | reg(2, "R2")
    | reg(3, "R3")
    | reg(4, "R4")
    | reg(5, "R5")
    | reg(6, "R6")
    | reg(7, "R7")
).named("register specifier")

# Directives
# ----------

d_orig = sym("ORIG") & iconst

d_fill = sym("FILL") & iconst

d_blkw = sym("BLKW") & dataconst

d_stringz = sym("STRINGZ") & string_const

d_end = sym("END") & pure(None)

directive = string_(".") >> (d_orig | d_fill | d_blkw | d_stringz | d_end) @ Directive


# Instructions
# ------------
branch_mode = regex("n|z|p|zp|np|nz|nzp").with_(BranchMode)


i_add = (
    sym("ADD") & (register << sym(",")) & (register << sym(",")) & (register | iconst)
)

i_and = (
    sym("AND") & (register << sym(",")) & (register << sym(",")) & (register | iconst)
)

i_brx = lexeme(string_("BR") & ~branch_mode) & label

i_jmp = sym("JMP") & register

i_ret = sym("RET") & pure(None)

i_jsr = sym("JSR") & label

i_jsrr = sym("JSRR") & register

i_ldb = sym("LDB") & (register << sym(",")) & (register << sym(",")) & iconst

i_ldw = sym("LDW") & (register << sym(",")) & (register << sym(",")) & iconst

i_lea = sym("LEA") & (register << sym(",")) & label

i_not = sym("NOT") & register & register

i_rti = sym("RTI") & pure(None)

i_lshf = sym("LSHF") & (register << sym(",")) & (register << sym(",")) & iconst

i_rshfl = sym("RSHFL") & (register << sym(",")) & (register << sym(",")) & iconst

i_rshfa = sym("RSHFA") & (register << sym(",")) & (register << sym(",")) & iconst

i_stb = sym("STB") & (register << sym(",")) & (register << sym(",")) & iconst

i_stw = sym("STW") & (register << sym(",")) & (register << sym(",")) & iconst

i_trap = sym("TRAP") & iconst

i_xor = (
    sym("XOR") & (register << sym(",")) & (register << sym(",")) & (register | iconst)
)

trap_getc = sym("GETC") & pure(None)

trap_out = sym("OUT") & pure(None)

trap_puts = sym("PUTS") & pure(None)

trap_in = sym("IN") & pure(None)

trap_halt = sym("HALT") & pure(None)


instruction = (
    i_add
    | i_and
    | i_brx
    | i_jmp
    | i_ret
    | i_jsr
    | i_jsrr
    | i_ldb
    | i_ldw
    | i_lea
    | i_not
    | i_rti
    | i_lshf
    | i_rshfl
    | i_rshfa
    | i_stb
    | i_stw
    | i_trap
    | i_xor
    | trap_getc
    | trap_out
    | trap_puts
    | trap_in
    | trap_halt
) @ Instruction

term = (((label.with_(Some) << sym(":")) | ws.as_(Nothing)) & (instruction | directive)) @ Term

line = ~term << ~comment

program = (
    append((line << eol)[:], (line << ~eol)).filter_option().with_(Program) << eof()
)

# TODO:
# label definitions
# comments
# empty lines
# preceding whitespace
# program
