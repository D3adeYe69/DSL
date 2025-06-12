import unittest
from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer

class TestSemanticAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = None

    def test_valid_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, V1.negative);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        self.analyzer.analyze()  # Should not raise any exceptions

    def test_duplicate_component(self):
        source = """
        VoltageSource V1(9 V);
        VoltageSource V1(12 V);  # Duplicate component
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(Exception):
            self.analyzer.analyze()

    def test_invalid_unit(self):
        source = """
        Resistor R1(100 invalid);  # Invalid unit
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(Exception):
            self.analyzer.analyze()

    def test_invalid_simulation_type(self):
        source = """
        VoltageSource V1(9 V);
        Simulate { invalid; };  # Invalid simulation type
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(Exception):
            self.analyzer.analyze()

    def test_missing_simulation(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, V1.negative);
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(Exception):
            self.analyzer.analyze()

    def test_invalid_connection(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Connect(V1.positive, R1.invalid);  # Invalid terminal
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(Exception):
            self.analyzer.analyze()

    def test_undefined_component(self):
        source = """
        Connect(V1.positive, R1.positive);  # Undefined components
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(Exception):
            self.analyzer.analyze()

    def test_valid_component_values(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Capacitor C1(1 uF);
        Inductor L1(10 mH);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        self.analyzer.analyze()  # Should not raise any exceptions

    def test_invalid_component_value(self):
        source = """
        Resistor R1(-100 ohm);  # Negative value
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        with self.assertRaises(Exception):
            self.analyzer.analyze()

    def test_complex_valid_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Resistor R2(200 ohm);
        Resistor R3(300 ohm);
        Capacitor C1(1 uF);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, R2.positive);
        Connect(R2.negative, R3.positive);
        Connect(R3.negative, C1.positive);
        Connect(C1.negative, V1.negative);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        self.analyzer.analyze()  # Should not raise any exceptions

    def test_ground_connection(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, ground);
        Connect(V1.negative, ground);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.analyzer = SemanticAnalyzer(program)
        self.analyzer.analyze()  # Should not raise any exceptions

if __name__ == '__main__':
    unittest.main()
