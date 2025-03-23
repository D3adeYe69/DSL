import re
from enum import Enum, auto

class TokenType(Enum):
    IDENTIFIER = auto()
    NUMBER = auto()
    COMPONENT = auto()
    CONNECT = auto()
    SUBCIRCUIT = auto()
    SIMULATE = auto()
    CONDITIONAL = auto()
    LOOP = auto()
    OPERATOR = auto()
    SYMBOL = auto()
    UNIT = auto()
    KEYWORD = auto()
    EOF = auto()

TOKEN_REGEX = [
    (TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z0-9_]*'),
    (TokenType.NUMBER, r'\d+(\.\d+)?([eE][+-]?\d+)?'),
    (TokenType.COMPONENT, r'Resistor|Capacitor|Inductor|VoltageSource|CurrentSource'),
    (TokenType.CONNECT, r'Connect'),
    (TokenType.SUBCIRCUIT, r'Subcircuit'),
    (TokenType.SIMULATE, r'Simulate'),
    (TokenType.CONDITIONAL, r'If|Else'),
    (TokenType.LOOP, r'For'),
    (TokenType.UNIT, r'ohm|uF|mH|V|A'),
    (TokenType.OPERATOR, r'='),
    (TokenType.SYMBOL, r'[();{},.]'),
    (TokenType.KEYWORD, r'from|to|step|dc|transient|ac'),
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
        code = self.source_code.strip()  # Remove leading/trailing whitespace
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
                raise SyntaxError(f'Unexpected token: {repr(code[:10])}...')  # Show first 10 chars
        self.tokens.append(Token(TokenType.EOF, None))
        return self.tokens


# Example Usage
if __name__ == "__main__":
    source = """
    Resistor R1(10 ohm);
    Connect(R1.positive, V1);
    Simulate { dc; transient(0, 10, 0.1); }
    """
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    for token in tokens:
        print(token)
