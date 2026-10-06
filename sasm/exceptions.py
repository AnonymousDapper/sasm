# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper


class SASMException(Exception): ...

class LexerException(SASMException): ...

class ParserException(SASMException): ...

class AssemblerException(SASMException): ...


