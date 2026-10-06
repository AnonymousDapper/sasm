# The MIT License (MIT)

# Copyright (c) 2025 AnonymousDapper

from .ast import AstNode
from .exceptions import AssemblerException


class UnknownNodeException(AssemblerException): ...

class AstTransformer:
    def visit(self, node: AstNode):
        fn = getattr(self, f"visit_{node.__class__.__name__}", None)

        if fn:
            return fn(node)

        else:
            if getattr(self, "visit_Unknown", False):
                return node
            else:
                raise UnknownNodeException(node.__class__.__name__)


class Assembler:
    ...
