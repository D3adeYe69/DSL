import unittest
from lexer import Lexer
from parser import Parser
from ast_nodes import Component, Connection, Simulation

class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = None

    def test_component_parsing(self):
        source = "Resistor R1(100 ohm);"
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        program = self.parser.parse()
        
        self.assertEqual(len(program.components), 1)
        comp = program.components[0]
        self.assertEqual(comp.type, "Resistor")
        self.assertEqual(comp.name, "R1")
        self.assertEqual(comp.value, "100")
        self.assertEqual(comp.unit, "ohm")

    def test_multiple_components(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Capacitor C1(1 uF);
        """
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        program = self.parser.parse()
        
        self.assertEqual(len(program.components), 3)
        self.assertEqual(program.components[0].type, "VoltageSource")
        self.assertEqual(program.components[1].type, "Resistor")
        self.assertEqual(program.components[2].type, "Capacitor")

    def test_connection_parsing(self):
        source = "Connect(V1.positive, R1.positive);"
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        program = self.parser.parse()
        
        self.assertEqual(len(program.connections), 1)
        conn = program.connections[0]
        self.assertEqual(conn.endpoints[0].component, "V1")
        self.assertEqual(conn.endpoints[0].terminal, "positive")
        self.assertEqual(conn.endpoints[1].component, "R1")
        self.assertEqual(conn.endpoints[1].terminal, "positive")

    def test_simulation_parsing(self):
        source = "Simulate { dc; };"
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        program = self.parser.parse()
        
        self.assertIsInstance(program.simulation, Simulation)
        self.assertEqual(program.simulation.type, "dc")

    def test_complete_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(100 ohm);
        Capacitor C1(1 uF);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, C1.positive);
        Connect(C1.negative, V1.negative);
        Simulate { dc; };
        """
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        program = self.parser.parse()
        
        self.assertEqual(len(program.components), 3)
        self.assertEqual(len(program.connections), 3)
        self.assertIsInstance(program.simulation, Simulation)

    def test_invalid_syntax(self):
        source = "Resistor R1(100 ohm"  # Missing semicolon
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        with self.assertRaises(Exception):
            self.parser.parse()

    def test_invalid_component(self):
        source = "InvalidComponent C1(1 V);"
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        with self.assertRaises(Exception):
            self.parser.parse()

    def test_invalid_connection(self):
        source = "Connect(V1.positive);"  # Missing second endpoint
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        with self.assertRaises(Exception):
            self.parser.parse()

    def test_invalid_simulation(self):
        source = "Simulate { invalid; };"  # Invalid simulation type
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        with self.assertRaises(Exception):
            self.parser.parse()

    def test_component_redefinition(self):
        source = """
        Resistor R1(100 ohm);
        Resistor R1(200 ohm);  # Redefinition
        """
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        with self.assertRaises(Exception):
            self.parser.parse()

    def test_ground_connection(self):
        source = "Connect(V1.negative, ground);"
        tokens = Lexer(source).tokenize()
        self.parser = Parser(tokens)
        program = self.parser.parse()
        
        self.assertEqual(len(program.connections), 1)
        conn = program.connections[0]
        self.assertEqual(conn.endpoints[0].component, "V1")
        self.assertEqual(conn.endpoints[0].terminal, "negative")
        self.assertEqual(conn.endpoints[1], "ground")

if __name__ == '__main__':
    unittest.main()
