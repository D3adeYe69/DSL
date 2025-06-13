import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

import unittest
from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer, SemanticError
from ast_nodes import Program

class TestSemanticAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = None

    def test_valid_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        self.analyzer.analyze()  # Should not raise any errors

    def test_duplicate_component(self):
        source = """
        Resistor R1(1k ohm);
        Resistor R1(2k ohm);  // Duplicate component
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(SemanticError) as context:
            self.analyzer.analyze()
        self.assertIn("already defined", str(context.exception))

    def test_invalid_unit(self):
        source = """
        Resistor R1(1k V);  // Invalid unit for resistor
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(SemanticError) as context:
            self.analyzer.analyze()
        self.assertIn("invalid unit", str(context.exception).lower())

    def test_invalid_simulation_type(self):
        source = """
        Resistor R1(1k ohm);
        analysis main_analysis { invalid; };  // Invalid simulation type
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(SemanticError) as context:
            self.analyzer.analyze()
        self.assertIn("invalid simulation", str(context.exception).lower())

    def test_invalid_connection(self):
        source = """
        Resistor R1(1k ohm);
        Connect(R1.positive, R1.positive);  // Invalid self-connection
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(SemanticError) as context:
            self.analyzer.analyze()
        self.assertIn("invalid connection", str(context.exception).lower())

    def test_undefined_component(self):
        source = """
        Connect(R1.positive, V1.positive);  // Undefined components
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(SemanticError) as context:
            self.analyzer.analyze()
        self.assertIn("undefined", str(context.exception).lower())

    def test_missing_simulation(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, V1.negative);
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(SemanticError) as context:
            self.analyzer.analyze()
        self.assertIn("must include a simulation", str(context.exception).lower())

    def test_invalid_terminal(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Connect(V1.invalid, R1.positive);  // Invalid terminal
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(SemanticError) as context:
            self.analyzer.analyze()
        self.assertIn("invalid terminal", str(context.exception).lower())

if __name__ == '__main__':
    unittest.main()
