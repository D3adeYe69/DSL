import unittest
from lexer import Lexer, Token, TokenType

class TestLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = None

    def test_basic_tokens(self):
        source = "Resistor R1(100 ohm);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.IDENTIFIER, "Resistor"),
            Token(TokenType.IDENTIFIER, "R1"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.NUMBER, "100"),
            Token(TokenType.IDENTIFIER, "ohm"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.SEMICOLON, ";")
        ]
        
        self.assertEqual(tokens, expected)

    def test_voltage_source(self):
        source = "VoltageSource V1(9 V);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.IDENTIFIER, "VoltageSource"),
            Token(TokenType.IDENTIFIER, "V1"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.NUMBER, "9"),
            Token(TokenType.IDENTIFIER, "V"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.SEMICOLON, ";")
        ]
        
        self.assertEqual(tokens, expected)

    def test_connection(self):
        source = "Connect(V1.positive, R1.positive);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.IDENTIFIER, "Connect"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.IDENTIFIER, "V1"),
            Token(TokenType.DOT, "."),
            Token(TokenType.IDENTIFIER, "positive"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENTIFIER, "R1"),
            Token(TokenType.DOT, "."),
            Token(TokenType.IDENTIFIER, "positive"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.SEMICOLON, ";")
        ]
        
        self.assertEqual(tokens, expected)

    def test_simulation(self):
        source = "Simulate { dc; };"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.IDENTIFIER, "Simulate"),
            Token(TokenType.LBRACE, "{"),
            Token(TokenType.IDENTIFIER, "dc"),
            Token(TokenType.SEMICOLON, ";"),
            Token(TokenType.RBRACE, "}"),
            Token(TokenType.SEMICOLON, ";")
        ]
        
        self.assertEqual(tokens, expected)

    def test_complex_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Capacitor C1(1 uF);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, C1.positive);
        Connect(C1.negative, V1.negative);
        Simulate { dc; };
        """
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        # Check first few tokens to ensure basic structure
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "VoltageSource")
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].value, "V1")

    def test_invalid_tokens(self):
        source = "Resistor R1(@100 ohm);"  # Invalid character @
        self.lexer = Lexer(source)
        with self.assertRaises(Exception):
            self.lexer.tokenize()

    def test_whitespace_handling(self):
        source = "Resistor    R1(   100    ohm   )   ;"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.IDENTIFIER, "Resistor"),
            Token(TokenType.IDENTIFIER, "R1"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.NUMBER, "100"),
            Token(TokenType.IDENTIFIER, "ohm"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.SEMICOLON, ";")
        ]
        
        self.assertEqual(tokens, expected)

    def test_numbers(self):
        source = "Resistor R1(1.5e-3 ohm);"
        self.lexer = Lexer(source)
        tokens = self.lexer.tokenize()
        
        expected = [
            Token(TokenType.IDENTIFIER, "Resistor"),
            Token(TokenType.IDENTIFIER, "R1"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.NUMBER, "1.5e-3"),
            Token(TokenType.IDENTIFIER, "ohm"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.SEMICOLON, ";")
        ]
        
        self.assertEqual(tokens, expected)

if __name__ == '__main__':
    unittest.main()
