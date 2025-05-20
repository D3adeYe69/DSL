import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List

class TokenType(Enum):
    IDENTIFIER    = auto()
    NUMBER        = auto()
    COMPONENT     = auto()
    CONNECT       = auto()
    SUBCIRCUIT    = auto()
    SIMULATE      = auto()
    SYMBOL        = auto()
    OPERATOR      = auto()
    LAW           = auto()
    WIRE          = auto()
    GROUND        = auto()
    NODE          = auto()
    UNIT          = auto()
    KEYWORD       = auto()
    EOF           = auto()
# Token regex specification
TOKEN_SPECIFICATION = [
    ('COMPONENT',  r'\b(?:Resistor|Capacitor|Inductor|VoltageSource|CurrentSource|Ammeter)\b'),
    ('WIRE',       r'\bWire\b'),
    ('CONNECT',    r'\bConnect\b'),
    ('SUBCIRCUIT', r'\bSubcircuit\b'),
    ('SIMULATE',   r'\bSimulate\b'),
    ('LAW',        r'\b(?:OhmLaw|KCL|KVL)\b'),
    ('GROUND',     r'\bground\b'),
    ('NODE',       r'\bnode\b'),
    ('KEYWORD',    r'\b(?:dc|transient|ac)\b'),
    ('UNIT',       r'\b(?:ohm|uF|mH|V|A|mA|kOhm)\b'),
    ('NUMBER',     r'\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'),
    ('IDENTIFIER', r'[A-Za-z_][A-Za-z0-9_]*'),
    ('OPERATOR',   r'[+\-*/=]'),
    ('SYMBOL',     r'[(),;{}\.\}]'),
    ('SKIP',       r'[ \t\r\n]+'),
    ('MISMATCH',   r'.'),
]
_master_regex = '|'.join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION)
_token_re = re.compile(_master_regex)

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class Lexer:
    def __init__(self, code: str):
        self.code = code

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        line = 1
        col = 1
        pos = 0
        for mo in _token_re.finditer(self.code):
            kind = mo.lastgroup
            value = mo.group()
            start = mo.start()
            segment = self.code[pos:start]
            # update line/col based on skipped text
            newlines = segment.count('\n')
            if newlines > 0:
                line += newlines
                col = start - segment.rfind('\n')
            else:
                col += len(segment)
            if kind == 'SKIP':
                pos = mo.end()
                continue
            if kind == 'MISMATCH':
                raise SyntaxError(f"Unexpected token {value!r} at line {line}, column {col}")
            token_type = TokenType[kind]
            tokens.append(Token(token_type, value, line, col))
            pos = mo.end()
            col += len(value)
        tokens.append(Token(TokenType.EOF, '', line, col))
        return tokens
