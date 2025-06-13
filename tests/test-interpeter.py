import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

import unittest
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

class TestInterpreter(unittest.TestCase):
    def setUp(self):
        self.interpreter = None

    def test_simple_circuit(self):
        source = """
        VoltageSource V1(value=9, unit=V);
        Resistor R1(value=1000, unit=ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        netlist = self.interpreter.generate_netlist()
        
        # Check that the netlist was generated
        self.assertIsNotNone(netlist)
        self.assertTrue(len(netlist) > 0)
        
        # Check for voltage source
        v1_lines = [line for line in netlist if line.startswith('V1')]
        self.assertTrue(len(v1_lines) > 0)
        self.assertTrue(any('9V' in line for line in v1_lines))
        
        # Check for resistor
        r1_lines = [line for line in netlist if line.startswith('R1')]
        self.assertTrue(len(r1_lines) > 0)
        self.assertTrue(any('1k' in line for line in r1_lines))

    def test_series_circuit(self):
        source = """
        VoltageSource V1(value=9, unit=V);
        Resistor R1(value=1000, unit=ohm);
        Resistor R2(value=2000, unit=ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, R2.positive);
        Connect(R2.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        netlist = self.interpreter.generate_netlist()
        
        # Check that the netlist was generated
        self.assertIsNotNone(netlist)
        self.assertTrue(len(netlist) > 0)
        
        # Check for voltage source
        v1_lines = [line for line in netlist if line.startswith('V1')]
        self.assertTrue(len(v1_lines) > 0)
        self.assertTrue(any('9V' in line for line in v1_lines))
        
        # Check for resistors
        r1_lines = [line for line in netlist if line.startswith('R1')]
        r2_lines = [line for line in netlist if line.startswith('R2')]
        self.assertTrue(len(r1_lines) > 0)
        self.assertTrue(len(r2_lines) > 0)
        self.assertTrue(any('1k' in line for line in r1_lines))
        self.assertTrue(any('2k' in line for line in r2_lines))

    def test_parallel_circuit(self):
        source = """
        VoltageSource V1(value=9, unit=V);
        Resistor R1(value=1000, unit=ohm);
        Resistor R2(value=2000, unit=ohm);
        Connect(V1.positive, R1.positive);
        Connect(V1.positive, R2.positive);
        Connect(R1.negative, V1.negative);
        Connect(R2.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        netlist = self.interpreter.generate_netlist()
        
        # Check that the netlist was generated
        self.assertIsNotNone(netlist)
        self.assertTrue(len(netlist) > 0)
        
        # Check for voltage source
        v1_lines = [line for line in netlist if line.startswith('V1')]
        self.assertTrue(len(v1_lines) > 0)
        self.assertTrue(any('9V' in line for line in v1_lines))
        
        # Check for resistors
        r1_lines = [line for line in netlist if line.startswith('R1')]
        r2_lines = [line for line in netlist if line.startswith('R2')]
        self.assertTrue(len(r1_lines) > 0)
        self.assertTrue(len(r2_lines) > 0)
        self.assertTrue(any('1k' in line for line in r1_lines))
        self.assertTrue(any('2k' in line for line in r2_lines))

    def test_ground_connection(self):
        source = """
        VoltageSource V1(value=9, unit=V);
        Resistor R1(value=1000, unit=ohm);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, GND);
        Connect(V1.negative, GND);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        netlist = self.interpreter.generate_netlist()
        
        # Check that the netlist was generated
        self.assertIsNotNone(netlist)
        self.assertTrue(len(netlist) > 0)
        
        # Check for voltage source
        v1_lines = [line for line in netlist if line.startswith('V1')]
        self.assertTrue(len(v1_lines) > 0)
        self.assertTrue(any('9V' in line for line in v1_lines))
        
        # Check for resistor
        r1_lines = [line for line in netlist if line.startswith('R1')]
        self.assertTrue(len(r1_lines) > 0)
        self.assertTrue(any('1k' in line for line in r1_lines))
        
        # Check for ground connections
        gnd_lines = [line for line in netlist if 'GND' in line]
        self.assertTrue(len(gnd_lines) > 0)

    def test_invalid_connection(self):
        source = """
        Resistor R1(value=1000, unit=ohm);
        Connect(R1.positive, R1.positive);  // Invalid self-connection
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        with self.assertRaises(Exception):
            self.interpreter.generate_netlist()

    def test_floating_component(self):
        source = """
        Resistor R1(value=1000, unit=ohm);  // No connections
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        with self.assertRaises(Exception):
            self.interpreter.generate_netlist()

    def test_short_circuit(self):
        source = """
        VoltageSource V1(value=9, unit=V);
        Connect(V1.positive, V1.negative);  // Short circuit
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        with self.assertRaises(Exception):
            self.interpreter.generate_netlist()

    def test_complex_circuit(self):
        source = """
        VoltageSource V1(value=9, unit=V);
        Resistor R1(value=1000, unit=ohm);
        Resistor R2(value=2000, unit=ohm);
        Capacitor C1(value=1e-6, unit=F);
        Connect(V1.positive, R1.positive);
        Connect(R1.negative, R2.positive);
        Connect(R2.negative, C1.positive);
        Connect(C1.negative, V1.negative);
        analysis main_analysis { dc; };
        """
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        self.interpreter = Interpreter(program)
        netlist = self.interpreter.generate_netlist()
        
        # Check that the netlist was generated
        self.assertIsNotNone(netlist)
        self.assertTrue(len(netlist) > 0)
        
        # Check for voltage source
        v1_lines = [line for line in netlist if line.startswith('V1')]
        self.assertTrue(len(v1_lines) > 0)
        self.assertTrue(any('9V' in line for line in v1_lines))
        
        # Check for resistors
        r1_lines = [line for line in netlist if line.startswith('R1')]
        r2_lines = [line for line in netlist if line.startswith('R2')]
        self.assertTrue(len(r1_lines) > 0)
        self.assertTrue(len(r2_lines) > 0)
        self.assertTrue(any('1k' in line for line in r1_lines))
        self.assertTrue(any('2k' in line for line in r2_lines))
        
        # Check for capacitor
        c1_lines = [line for line in netlist if line.startswith('C1')]
        self.assertTrue(len(c1_lines) > 0)
        self.assertTrue(any('1u' in line for line in c1_lines))

if __name__ == '__main__':
    unittest.main()
