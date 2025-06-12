import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    IDENTIFIER = auto()
    NUMBER = auto()
    COMPONENT = auto()
    CONNECT = auto()
    SUBCIRCUIT = auto()
    SIMULATE = auto()
    SYMBOL = auto()
    OPERATOR = auto()
    LAW = auto()
    WIRE = auto()
    GROUND = auto()
    NODE = auto()
    NET = auto()
    UNIT_PREFIX = auto()
    UNIT_BASE = auto()
    UNIT = auto()  # Combined unit token
    KEYWORD = auto()
    COMMENT_SINGLE = auto()
    COMMENT_BLOCK = auto()
    STRING = auto()  # For string literals
    EOF = auto()

# Token regex specification
TOKEN_SPECIFICATION = [
    # Language keywords and component types
    ('COMPONENT', r'\b(?:Resistor|Capacitor|Inductor|VoltageSource|CurrentSource|Ammeter|Diode|BJT|MOSFET|OpAmp)\b'),
    ('WIRE', r'\bWire\b'),
    ('CONNECT', r'\bConnect\b'),
    ('SUBCIRCUIT', r'\bSubcircuit\b'),
    ('SIMULATE', r'\bSimulate\b'),
    ('LAW', r'\b(?:OhmLaw|KCL|KVL)\b'),
    ('GROUND', r'\bground\b'),
    ('NODE', r'\bnode\b'),
    ('NET', r'\bNet\b'),
    
    # Extended keywords including paramSweep and analysis types
    ('KEYWORD', r'\b(?:dc|transient|ac|noise|monte|paramSweep|sweep|analysis|plot|print|save|include|lib|model|param|if|else|for|while|def|return|import|from|as)\b'),
    
    # Units with proper separation of prefix and base
    ('UNIT', r'\b(?:[munpfakMGTPE])?(?:Ohm|ohm|F|H|V|A|Hz|S|W|C|T|N|lx|Bq|Gy|Sv|kat|m|g|s|K|mol|cd)\b'),
    
    # Numbers with scientific notation and units
    ('NUMBER', r'\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?(?:[munpfakMGTPE])?(?:[A-Za-z]+)?'),
    
    # String literals
    ('STRING', r'"(?:[^"\\]|\\.)*"'),
    ('STRING', r"'(?:[^'\\]|\\.)*'"),
    
    # Identifiers (after keywords to avoid conflicts)
    ('IDENTIFIER', r'[A-Za-z_][A-Za-z0-9_]*'),
    
    # Extended operators
    ('OPERATOR', r'[+\-*/=<>!&|^%]|==|!=|<=|>=|&&|\|\||<<|>>|\*\*'),
    
    # Symbols and delimiters
    ('SYMBOL', r'[(),;{}\[\]\.:]'),
    
    # Comments
    ('COMMENT_SINGLE', r'//[^\n]*'),
    ('COMMENT_BLOCK', r'/\*[\s\S]*?\*/'),
    
    # Skip whitespace
    ('SKIP', r'[ \t\r\n]+'),
    
    # Catch-all for unrecognized characters
    ('MISMATCH', r'.'),
]

# Build master regex
_master_regex = '|'.join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION)
_token_re = re.compile(_master_regex)

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    
    def __str__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"

class LexerError(Exception):
    """Custom exception for lexer errors"""
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}, Column {column}: {message}")

class Lexer:
    def __init__(self, code: str, filename: str = "<input>"):
        self.code = code
        self.filename = filename
    
    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        line = 1
        col = 1
        pos = 0
        
        for mo in _token_re.finditer(self.code):
            kind = mo.lastgroup
            value = mo.group()
            start = mo.start()
            
            # Calculate line and column position
            segment = self.code[pos:start]
            newlines = segment.count('\n')
            if newlines > 0:
                line += newlines
                col = start - segment.rfind('\n')
            else:
                col += len(segment)
            
            # Skip whitespace and comments
            if kind in ('SKIP', 'COMMENT_SINGLE', 'COMMENT_BLOCK'):
                pos = mo.end()
                continue
            
            # Handle unrecognized tokens
            if kind == 'MISMATCH':
                raise LexerError(f"Unexpected character {value!r}", line, col)
            
            # Create token
            try:
                token_type = TokenType[kind]
            except KeyError:
                raise LexerError(f"Unknown token type {kind}", line, col)
            
            # Post-process certain tokens
            if kind == 'NUMBER':
                # Separate number from unit if present
                token = self._process_number_token(token_type, value, line, col)
                if isinstance(token, list):
                    tokens.extend(token)
                else:
                    tokens.append(token)
            else:
                tokens.append(Token(token_type, value, line, col))
            
            pos = mo.end()
            col += len(value)
        
        # Add EOF token
        tokens.append(Token(TokenType.EOF, '', line, col))
        return tokens
    
    def _process_number_token(self, token_type: TokenType, value: str, line: int, col: int) -> List[Token]:
        """Process number tokens that may have embedded units"""
        # Try to separate number from unit
        number_pattern = r'^(\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?)([munpfakMGTPE])?([A-Za-z]+)?$'
        match = re.match(number_pattern, value)
        
        if match:
            number_part, prefix, unit_part = match.groups()
            tokens = [Token(TokenType.NUMBER, number_part, line, col)]
            
            if prefix and unit_part:
                # Has both prefix and unit
                tokens.append(Token(TokenType.UNIT, prefix + unit_part, line, col + len(number_part)))
            elif unit_part:
                # Has unit without prefix
                tokens.append(Token(TokenType.UNIT, unit_part, line, col + len(number_part)))
            elif prefix:
                # Has prefix without unit (unusual, treat as identifier)
                tokens.append(Token(TokenType.IDENTIFIER, prefix, line, col + len(number_part)))
            
            return tokens
        else:
            # Fallback to original token
            return [Token(token_type, value, line, col)]

# Utility functions for working with tokens
def is_component_type(token: Token) -> bool:
    """Check if token represents a component type"""
    return token.type == TokenType.COMPONENT

def is_keyword(token: Token, keyword: str) -> bool:
    """Check if token is a specific keyword"""
    return token.type == TokenType.KEYWORD and token.value == keyword

def is_operator(token: Token, operator: str) -> bool:
    """Check if token is a specific operator"""
    return token.type == TokenType.OPERATOR and token.value == operator

def is_symbol(token: Token, symbol: str) -> bool:
    """Check if token is a specific symbol"""
    return token.type == TokenType.SYMBOL and token.value == symbol

# Enhanced unit parsing
class UnitParser:
    """Helper class for parsing and validating units"""
    
    PREFIXES = {
        'E': 1e18, 'P': 1e15, 'T': 1e12, 'G': 1e9, 'M': 1e6, 'k': 1e3,
        'm': 1e-3, 'u': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15, 'a': 1e-18
    }
    
    BASE_UNITS = {
        # Electrical
        'V': 'voltage', 'A': 'current', 'Ohm': 'resistance', 'ohm': 'resistance',
        'F': 'capacitance', 'H': 'inductance', 'S': 'conductance', 'W': 'power',
        'Hz': 'frequency', 'C': 'charge',
        # Physical
        'm': 'length', 'g': 'mass', 's': 'time', 'K': 'temperature',
        'mol': 'amount', 'cd': 'luminosity'
    }
    
    @classmethod
    def parse_unit(cls, unit_str: str) -> tuple[float, str]:
        """Parse unit string into multiplier and base unit"""
        if not unit_str:
            return 1.0, ""
        
        # Try to split prefix from base unit
        for prefix, multiplier in cls.PREFIXES.items():
            if unit_str.startswith(prefix):
                base_unit = unit_str[len(prefix):]
                if base_unit in cls.BASE_UNITS:
                    return multiplier, cls.BASE_UNITS[base_unit]
        
        # No prefix found, check if it's a base unit
        if unit_str in cls.BASE_UNITS:
            return 1.0, cls.BASE_UNITS[unit_str]
        
        # Unknown unit
        return 1.0, unit_str

# Example usage and testing
if __name__ == "__main__":
    # Test the lexer with sample code
    sample_code = """
    // Sample circuit description
    Resistor R1(1.2kOhm, node1, node2);
    Capacitor C1(10uF, node2, ground);
    
    Connect(node1, VCC);
    
    Subcircuit amplifier {
        // Amplifier implementation
    }
    
    Simulate dc {
        paramSweep VCC 0V 5V 0.1V;
    }
    """
    
    lexer = Lexer(sample_code, "test.cir")
    try:
        tokens = lexer.tokenize()
        for token in tokens[:20]:  # Show first 20 tokens
            print(token)
    except LexerError as e:
        print(f"Lexer error: {e}")
