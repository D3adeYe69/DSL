import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

import unittest
from lexer import Lexer
from parser import Parser
from ast_nodes import (
    Program,
    ComponentDeclaration,
    Connection,
    AnalysisBlock,
    DCAnalysis,
    Terminal,
    Node,
    Literal,
    Identifier
)

class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = None

    def test_simple_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        
        # Check program structure
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.components), 2)
        self.assertEqual(len(program.connections), 2)
        self.assertEqual(len(program.analyses), 1)
        
        # Check components
        v1 = program.components[0]
        self.assertIsInstance(v1, ComponentDeclaration)
        self.assertEqual(v1.type_name, "VoltageSource")
        self.assertEqual(v1.instance_name, "V1")
        self.assertEqual(len(v1.positional_params), 1)
        self.assertIsInstance(v1.positional_params[0], Literal)
        self.assertEqual(v1.positional_params[0].value, 9)
        self.assertEqual(v1.positional_params[0].unit, "V")
        
        r1 = program.components[1]
        self.assertIsInstance(r1, ComponentDeclaration)
        self.assertEqual(r1.type_name, "Resistor")
        self.assertEqual(r1.instance_name, "R1")
        self.assertEqual(len(r1.positional_params), 1)
        self.assertIsInstance(r1.positional_params[0], Literal)
        self.assertEqual(r1.positional_params[0].value, 1000)  # 1k ohm
        self.assertEqual(r1.positional_params[0].unit, "ohm")
        
        # Check connections
        conn1 = program.connections[0]
        self.assertIsInstance(conn1, Connection)
        self.assertEqual(len(conn1.endpoints), 2)
        self.assertIsInstance(conn1.endpoints[0], Terminal)
        self.assertEqual(conn1.endpoints[0].component_name, "V1")
        self.assertEqual(conn1.endpoints[0].terminal_name, "positive")
        self.assertIsInstance(conn1.endpoints[1], Terminal)
        self.assertEqual(conn1.endpoints[1].component_name, "R1")
        self.assertEqual(conn1.endpoints[1].terminal_name, "positive")
        
        # Check analysis
        analysis = program.analyses[0]
        self.assertIsInstance(analysis, AnalysisBlock)
        self.assertEqual(analysis.name, "main_analysis")
        self.assertEqual(len(analysis.simulations), 1)
        self.assertIsInstance(analysis.simulations[0], DCAnalysis)

    def test_series_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Resistor R2(2k ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, R2.positive);
        Connect(R2.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.components), 3)
        self.assertEqual(len(program.connections), 3)
        
        # Check components
        components = {comp.instance_name: comp for comp in program.components}
        self.assertIn("V1", components)
        self.assertIn("R1", components)
        self.assertIn("R2", components)
        
        # Check connections
        self.assertEqual(len(program.connections), 3)
        for conn in program.connections:
            self.assertIsInstance(conn, Connection)
            self.assertEqual(len(conn.endpoints), 2)

    def test_parallel_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Resistor R2(2k ohm);
        Connect(V1.positive, R1.positive);
        Connect(V1.positive, R2.positive);
        Connect(R1.negative, V1.negative);
        Connect(R2.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.components), 3)
        self.assertEqual(len(program.connections), 4)
        
        # Check components
        components = {comp.instance_name: comp for comp in program.components}
        self.assertIn("V1", components)
        self.assertIn("R1", components)
        self.assertIn("R2", components)
        
        # Check connections
        self.assertEqual(len(program.connections), 4)
        for conn in program.connections:
            self.assertIsInstance(conn, Connection)
            self.assertEqual(len(conn.endpoints), 2)

    def test_ground_connection(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, GND);
        Connect(V1.negative, GND);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.components), 2)
        self.assertEqual(len(program.connections), 3)
        
        # Check ground connections
        for conn in program.connections:
            if any(isinstance(ep, Node) and ep.is_ground for ep in conn.endpoints):
                self.assertTrue(any(isinstance(ep, Node) and ep.is_ground for ep in conn.endpoints))

    def test_invalid_connection(self):
        source = """
        Resistor R1(1k ohm);
        Connect(R1.positive, R1.positive);  // Invalid self-connection
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        with self.assertRaises(Exception):
            Parser(tokens).parse()

    def test_floating_component(self):
        source = """
        Resistor R1(1k ohm);  // No connections
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.components), 1)
        self.assertEqual(len(program.connections), 0)

    def test_short_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Connect(V1.positive, V1.negative);  // Short circuit
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.components), 1)
        self.assertEqual(len(program.connections), 1)

    def test_complex_circuit(self):
        source = """
        VoltageSource V1(9 V);
        Resistor R1(1k ohm);
        Resistor R2(2k ohm);
        Capacitor C1(1u F);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, R2.positive);
        Connect(R2.negative, C1.positive);
        Connect(C1.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.components), 4)
        self.assertEqual(len(program.connections), 4)
        
        # Check components
        components = {comp.instance_name: comp for comp in program.components}
        self.assertIn("V1", components)
        self.assertIn("R1", components)
        self.assertIn("R2", components)
        self.assertIn("C1", components)
        
        # Check connections
        self.assertEqual(len(program.connections), 4)
        for conn in program.connections:
            self.assertIsInstance(conn, Connection)
            self.assertEqual(len(conn.endpoints), 2)

if __name__ == '__main__':
    unittest.main()
