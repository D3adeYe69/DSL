import re
from enum import Enum, auto

class TokenType(Enum):
    IDENTIFIER = auto()
    NUMBER = auto()
    COMPONENT = auto()
    CONNECT = auto()
    SUBCIRCUIT = auto()
    SIMULATE = auto()
    SYMBOL = auto()
    UNIT = auto()
    KEYWORD = auto()
    EOF = auto()

TOKEN_REGEX = [
    (TokenType.COMPONENT, r'Resistor|Capacitor|Inductor|VoltageSource|CurrentSource'),
    (TokenType.CONNECT, r'Connect'),
    (TokenType.SUBCIRCUIT, r'Subcircuit'),
    (TokenType.SIMULATE, r'Simulate'),
    (TokenType.KEYWORD, r'dc|transient|ac'),
    (TokenType.UNIT, r'ohm|uF|mH|V|A'),
    (TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z0-9_]*'),
    (TokenType.NUMBER, r'\d+(\.\d+)?([eE][+-]?\d+)?'),
    (TokenType.SYMBOL, r'[();{},.]'),
]

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f'Token({self.type}, {repr(self.value)})'

class Lexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens = []
        self.position = 0

    def tokenize(self):
        code = self.source_code.strip()
        while code:
            match = None
            for token_type, regex in TOKEN_REGEX:
                pattern = re.compile(r'^' + regex)
                match = pattern.match(code)
                if match:
                    value = match.group(0)
                    self.tokens.append(Token(token_type, value))
                    code = code[len(value):].lstrip()
                    break
            if not match:
                raise SyntaxError(f'Unexpected token: {repr(code[:10])}...')
        self.tokens.append(Token(TokenType.EOF, None))
        return self.tokens
