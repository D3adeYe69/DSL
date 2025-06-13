import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Dict

class TokenType(Enum):
    # Component types
    RESISTOR = 'RESISTOR'
    CAPACITOR = 'CAPACITOR'
    INDUCTOR = 'INDUCTOR'
    VOLTAGE_SOURCE = 'VOLTAGE_SOURCE'
    CURRENT_SOURCE = 'CURRENT_SOURCE'
    AC_SOURCE = 'AC_SOURCE'
    AMMETER = 'AMMETER'
    
    # Keywords
    CONNECT = 'CONNECT'
    SUBCIRCUIT = 'SUBCIRCUIT'
    SIMULATE = 'SIMULATE'
    GROUND = 'GROUND'
    
    # Other tokens
    IDENTIFIER = 'IDENTIFIER'
    NUMBER = 'NUMBER'
    SYMBOL = 'SYMBOL'
    OPERATOR = 'OPERATOR'
    UNIT = 'UNIT'
    KEYWORD = 'KEYWORD'
    COMMENT_SINGLE = 'COMMENT_SINGLE'
    COMMENT_BLOCK = 'COMMENT_BLOCK'
    STRING = 'STRING'
    EOF = 'EOF'

# Token regex specification
TOKEN_SPECIFICATION = [
    # Component types
    ('RESISTOR', r'\bResistor\b'),
    ('CAPACITOR', r'\bCapacitor\b'),
    ('INDUCTOR', r'\bInductor\b'),
    ('VOLTAGE_SOURCE', r'\bVoltageSource\b'),
    ('CURRENT_SOURCE', r'\bCurrentSource\b'),
    ('AC_SOURCE', r'\bACSource\b'),
    ('AMMETER', r'\bAmmeter\b'),
    
    # Keywords
    ('CONNECT', r'\bConnect\b'),
    ('SUBCIRCUIT', r'\bSubcircuit\b'),
    ('SIMULATE', r'\bSimulate\b'),
    ('GROUND', r'\bground\b'),
    
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
    
    # Comments (both # and // style)
    ('COMMENT_SINGLE', r'//[^\n]*|#[^\n]*'),
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
    type: str
    value: str
    line: int
    column: int

class LexerError(Exception):
    """Custom exception for lexer errors"""
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}, Column {column}: {message}")

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.current_char = self.text[0] if text else None
        self.line = 1
        self.column = 1
        self.tokens = []
        
        # Component type mapping
        self.component_types = {
            'VOLTAGE_SOURCE': ['value', 'frequency', 'amplitude', 'phase'],
            'CURRENT_SOURCE': ['value', 'frequency', 'amplitude', 'phase'],
            'RESISTOR': ['resistance'],
            'CAPACITOR': ['capacitance'],
            'INDUCTOR': ['inductance'],
            'AC_SOURCE': ['frequency', 'amplitude', 'phase'],
            'DC_SOURCE': ['value'],
            'DIODE': ['model'],
            'TRANSISTOR': ['model'],
            'OPAMP': ['model']
        }
        
        # Units with proper separation of prefix and base
        self.unit_types = {
            'value': ['V', 'A'],
            'resistance': ['ohm', 'kohm', 'Mohm'],
            'capacitance': ['F', 'nF', 'uF', 'pF'],
            'inductance': ['H', 'mH', 'uH', 'nH'],
            'frequency': ['Hz', 'kHz', 'MHz', 'GHz'],
            'time': ['s', 'ms', 'us', 'ns']
        }
        
        # Keywords
        self.keywords = {
            'SUBCIRCUIT': 'SUBCIRCUIT',
            'CONNECT': 'CONNECT',
            'SIMULATE': 'SIMULATE',
            'DC': 'DC',
            'AC': 'AC',
            'TRANSIENT': 'TRANSIENT',
            'NOISE': 'NOISE',
            'MONTE_CARLO': 'MONTE_CARLO',
            'PARAMETRIC': 'PARAMETRIC',
            'PLOT': 'PLOT'
        }
    
    def error(self, message: str):
        raise Exception(f'Error: Line {self.line}, Column {self.column}: {message}')

    def advance(self):
        self.pos += 1
        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
            self.column += 1
        else:
            self.current_char = None

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            if self.current_char == '\n':
                self.line += 1
                self.column = 1
            self.advance()

    def skip_comment(self):
        while self.current_char is not None and self.current_char != '\n':
            self.advance()
        if self.current_char == '\n':
            self.line += 1
            self.column = 1
            self.advance()

    def number(self):
        result = ''
        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '.'):
            result += self.current_char
            self.advance()
        return Token('NUMBER', result, self.line, self.column - len(result))

    def id(self):
        result = ''
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_' or self.current_char == '.'):
            result += self.current_char
            self.advance()
        return Token('ID', result, self.line, self.column - len(result))

    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            if self.current_char == '#':
                self.skip_comment()
                continue

            if self.current_char.isdigit():
                return self.number()

            if self.current_char.isalpha() or self.current_char == '_':
                id_str = self.id().value
                if id_str in self.component_types:
                    return Token(id_str, id_str, self.line, self.column - len(id_str))
                elif id_str in self.keywords:
                    return Token(self.keywords[id_str], id_str, self.line, self.column - len(id_str))
                else:
                    return Token('ID', id_str, self.line, self.column - len(id_str))

            if self.current_char == '(':
                self.advance()
                return Token('LPAREN', '(', self.line, self.column - 1)

            if self.current_char == ')':
                self.advance()
                return Token('RPAREN', ')', self.line, self.column - 1)

            if self.current_char == '{':
                self.advance()
                return Token('LBRACE', '{', self.line, self.column - 1)

            if self.current_char == '}':
                self.advance()
                return Token('RBRACE', '}', self.line, self.column - 1)

            if self.current_char == ';':
                self.advance()
                return Token('SEMICOLON', ';', self.line, self.column - 1)

            if self.current_char == ',':
                self.advance()
                return Token('COMMA', ',', self.line, self.column - 1)

            if self.current_char == '=':
                self.advance()
                return Token('EQUALS', '=', self.line, self.column - 1)

            self.error(f'Invalid character: {self.current_char}')

        return Token('EOF', '', self.line, self.column)

    def tokenize(self):
        while True:
            token = self.get_next_token()
            self.tokens.append(token)
            if token.type == 'EOF':
                break
        return self.tokens

# Utility functions for working with tokens
def is_component_type(token: Token) -> bool:
    """Check if token represents a component type"""
    return token.type in ['VOLTAGE_SOURCE', 'CURRENT_SOURCE', 'RESISTOR', 'CAPACITOR', 'INDUCTOR', 'AC_SOURCE', 'DC_SOURCE', 'DIODE', 'TRANSISTOR', 'OPAMP']

def is_keyword(token: Token, keyword: str) -> bool:
    """Check if token represents a keyword"""
    return token.type == keyword

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
