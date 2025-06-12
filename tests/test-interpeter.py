import unittest
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

class TestInterpreter(unittest.TestCase):
    def setUp(self):
        self.interpreter = None

    def test_simple_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, V1.negative);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        self.interpreter.run()
        
        # Check node mapping
        self.assertIn('V1', self.interpreter.terminal_map)
        self.assertIn('R1', self.interpreter.terminal_map)
        self.assertEqual(len(self.interpreter.terminal_map['V1']), 2)  # positive and negative terminals
        self.assertEqual(len(self.interpreter.terminal_map['R1']), 2)  # positive and negative terminals

    def test_parallel_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Resistor R2(200 ohm);
        Connect(V1.positive, R1.positive);
        Connect(V1.positive, R2.positive);
        Connect(R1.negative, V1.negative);
        Connect(R2.negative, V1.negative);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        self.interpreter.run()
        
        # Check node mapping
        self.assertIn('V1', self.interpreter.terminal_map)
        self.assertIn('R1', self.interpreter.terminal_map)
        self.assertIn('R2', self.interpreter.terminal_map)
        
        # Check that R1 and R2 share the same nodes
        r1_nodes = set(self.interpreter.terminal_map['R1'].values())
        r2_nodes = set(self.interpreter.terminal_map['R2'].values())
        self.assertEqual(len(r1_nodes.intersection(r2_nodes)), 2)  # Both terminals should be connected

    def test_series_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Resistor R2(200 ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, R2.positive);
        Connect(R2.negative, V1.negative);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        self.interpreter.run()
        
        # Check node mapping
        self.assertIn('V1', self.interpreter.terminal_map)
        self.assertIn('R1', self.interpreter.terminal_map)
        self.assertIn('R2', self.interpreter.terminal_map)
        
        # Check that R1 and R2 share one node
        r1_nodes = set(self.interpreter.terminal_map['R1'].values())
        r2_nodes = set(self.interpreter.terminal_map['R2'].values())
        self.assertEqual(len(r1_nodes.intersection(r2_nodes)), 1)  # One terminal should be connected

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
        self.interpreter = Interpreter(program)
        self.interpreter.run()
        
        # Check that ground is node 0
        self.assertEqual(self.interpreter.terminal_map['V1']['negative'], 0)
        self.assertEqual(self.interpreter.terminal_map['R1']['negative'], 0)

    def test_invalid_connection(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Connect(V1.positive, R1.invalid);  # Invalid terminal
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        with self.assertRaises(Exception):
            self.interpreter.run()

    def test_floating_component(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);  # Not connected
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        with self.assertRaises(Exception):
            self.interpreter.run()

    def test_short_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Connect(V1.positive, V1.negative);  # Short circuit
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        with self.assertRaises(Exception):
            self.interpreter.run()

    def test_complex_circuit(self):
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
        self.interpreter = Interpreter(program)
        self.interpreter.run()
        
        # Check node mapping
        self.assertIn('V1', self.interpreter.terminal_map)
        self.assertIn('R1', self.interpreter.terminal_map)
        self.assertIn('R2', self.interpreter.terminal_map)
        self.assertIn('R3', self.interpreter.terminal_map)
        self.assertIn('C1', self.interpreter.terminal_map)
        
        # Check series connections
        r1_nodes = set(self.interpreter.terminal_map['R1'].values())
        r2_nodes = set(self.interpreter.terminal_map['R2'].values())
        r3_nodes = set(self.interpreter.terminal_map['R3'].values())
        c1_nodes = set(self.interpreter.terminal_map['C1'].values())
        
        self.assertEqual(len(r1_nodes.intersection(r2_nodes)), 1)
        self.assertEqual(len(r2_nodes.intersection(r3_nodes)), 1)
        self.assertEqual(len(r3_nodes.intersection(c1_nodes)), 1)

if __name__ == '__main__':
    unittest.main()
