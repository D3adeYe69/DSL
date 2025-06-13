import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

import unittest
from lexer import Lexer, Token, TokenType

class TestLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = None

    def test_basic_tokens(self):
        source = "Resistor R1(1k ohm);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.COMPONENT, "Resistor", 1, 1),
            Token(TokenType.IDENTIFIER, "R1", 1, 10),
            Token(TokenType.SYMBOL, "(", 1, 12),
            Token(TokenType.NUMBER, "1", 1, 13),
            Token(TokenType.UNIT, "kohm", 1, 14),
            Token(TokenType.SYMBOL, ")", 1, 18),
            Token(TokenType.SYMBOL, ";", 1, 19),
            Token(TokenType.EOF, "", 1, 20)
        ]
        
        self.assertEqual(tokens, expected)

    def test_voltage_source(self):
        source = "VoltageSource V1(9 V);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.COMPONENT, "VoltageSource", 1, 1),
            Token(TokenType.IDENTIFIER, "V1", 1, 14),
            Token(TokenType.SYMBOL, "(", 1, 16),
            Token(TokenType.NUMBER, "9", 1, 17),
            Token(TokenType.UNIT, "V", 1, 19),
            Token(TokenType.SYMBOL, ")", 1, 20),
            Token(TokenType.SYMBOL, ";", 1, 21),
            Token(TokenType.EOF, "", 1, 22)
        ]
        
        self.assertEqual(tokens, expected)

    def test_connection(self):
        source = "Connect(V1.positive, R1.positive);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.KEYWORD, "Connect", 1, 1),
            Token(TokenType.SYMBOL, "(", 1, 7),
            Token(TokenType.IDENTIFIER, "V1", 1, 8),
            Token(TokenType.SYMBOL, ".", 1, 10),
            Token(TokenType.IDENTIFIER, "positive", 1, 11),
            Token(TokenType.SYMBOL, ",", 1, 18),
            Token(TokenType.IDENTIFIER, "R1", 1, 20),
            Token(TokenType.SYMBOL, ".", 1, 22),
            Token(TokenType.IDENTIFIER, "positive", 1, 23),
            Token(TokenType.SYMBOL, ")", 1, 30),
            Token(TokenType.SYMBOL, ";", 1, 31),
            Token(TokenType.EOF, "", 1, 32)
        ]
        
        self.assertEqual(tokens, expected)

    def test_analysis(self):
        source = "analysis main_analysis { dc; };"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.KEYWORD, "analysis", 1, 1),
            Token(TokenType.IDENTIFIER, "main_analysis", 1, 9),
            Token(TokenType.SYMBOL, "{", 1, 22),
            Token(TokenType.KEYWORD, "dc", 1, 24),
            Token(TokenType.SYMBOL, ";", 1, 26),
            Token(TokenType.SYMBOL, "}", 1, 28),
            Token(TokenType.SYMBOL, ";", 1, 29),
            Token(TokenType.EOF, "", 1, 30)
        ]
        
        self.assertEqual(tokens, expected)

    def test_ground_connection(self):
        source = "Connect(V1.negative, GND);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.KEYWORD, "Connect", 1, 1),
            Token(TokenType.SYMBOL, "(", 1, 7),
            Token(TokenType.IDENTIFIER, "V1", 1, 8),
            Token(TokenType.SYMBOL, ".", 1, 10),
            Token(TokenType.IDENTIFIER, "negative", 1, 11),
            Token(TokenType.SYMBOL, ",", 1, 18),
            Token(TokenType.GROUND, "GND", 1, 20),
            Token(TokenType.SYMBOL, ")", 1, 23),
            Token(TokenType.SYMBOL, ";", 1, 24),
            Token(TokenType.EOF, "", 1, 25)
        ]
        
        self.assertEqual(tokens, expected)

    def test_comments(self):
        source = "// This is a comment\nResistor R1(1k ohm);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.COMPONENT, "Resistor", 2, 1),
            Token(TokenType.IDENTIFIER, "R1", 2, 10),
            Token(TokenType.SYMBOL, "(", 2, 12),
            Token(TokenType.NUMBER, "1", 2, 13),
            Token(TokenType.UNIT, "kohm", 2, 14),
            Token(TokenType.SYMBOL, ")", 2, 18),
            Token(TokenType.SYMBOL, ";", 2, 19),
            Token(TokenType.EOF, "", 2, 20)
        ]
        
        self.assertEqual(tokens, expected)

    def test_invalid_token(self):
        source = "Resistor R1(@1k ohm);"  # Invalid character @
        self.lexer = Lexer(source)
        with self.assertRaises(Exception):
            self.lexer.tokenize()

if __name__ == '__main__':
    unittest.main()
