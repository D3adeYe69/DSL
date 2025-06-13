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
    ('NUMBER', r'\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?'),
    
    # String literals (both single and double quotes)
    ('STRING', r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''),
    
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
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []
    
    def tokenize(self) -> List[Token]:
        """Tokenize the input code into a list of tokens"""
        tokens: List[Token] = []
        pos = 0
        
        for mo in _token_re.finditer(self.code):
            kind = mo.lastgroup
            value = mo.group()
            start = mo.start()
            
            # Calculate line and column position
            segment = self.code[pos:start]
            newlines = segment.count('\n')
            if newlines > 0:
                self.line += newlines
                self.column = start - segment.rfind('\n')
            else:
                self.column = start - pos + 1
            
            # Skip whitespace and comments
            if kind in ('SKIP', 'COMMENT_SINGLE', 'COMMENT_BLOCK'):
                pos = mo.end()
                continue
            
            # Handle unrecognized tokens
            if kind == 'MISMATCH':
                raise LexerError(f"Unexpected character {value!r}", self.line, self.column)
            
            # Create token
            try:
                token_type = TokenType[kind]
            except KeyError:
                raise LexerError(f"Unknown token type {kind}", self.line, self.column)
            
            # Post-process certain tokens
            if kind == 'NUMBER':
                # Process number token
                tokens.append(Token(token_type, value, self.line, self.column))
                
                # Look ahead for unit
                next_pos = mo.end()
                if next_pos < len(self.code):
                    next_match = _token_re.match(self.code, next_pos)
                    if next_match and next_match.lastgroup == 'UNIT':
                        unit_value = next_match.group()
                        tokens.append(Token(TokenType.UNIT, unit_value, self.line, self.column + len(value)))
                        pos = next_match.end()
                        continue
            else:
                tokens.append(Token(token_type, value, self.line, self.column))
            
            pos = mo.end()
        
        # Add EOF token
        tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return tokens

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
        'm': 1e-3, 'u': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15, 'a': 1e-18,
        'k': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12, 'P': 1e15, 'E': 1e18
    }
    
    BASE_UNITS = {
        'ohm': 'Ω', 'F': 'F', 'H': 'H', 'V': 'V', 'A': 'A', 'Hz': 'Hz',
        'S': 'S', 'W': 'W', 'C': 'C', 'T': 'T', 'N': 'N', 'lx': 'lx',
        'Bq': 'Bq', 'Gy': 'Gy', 'Sv': 'Sv', 'kat': 'kat', 'm': 'm',
        'g': 'g', 's': 's', 'K': 'K', 'mol': 'mol', 'cd': 'cd'
    }
    
    @classmethod
    def parse_unit(cls, unit_str: str) -> tuple[float, str]:
        """Parse a unit string into a multiplier and base unit"""
        if not unit_str:
            return 1.0, None
            
        # Check for prefix
        prefix = unit_str[0] if unit_str[0] in cls.PREFIXES else None
        if prefix:
            unit_str = unit_str[1:]
            
        # Check for base unit
        if unit_str in cls.BASE_UNITS:
            multiplier = cls.PREFIXES.get(prefix, 1.0)
            return multiplier, unit_str
            
        return 1.0, None
