from typing import Dict, Set, List
from ast_nodes import *

class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    def __init__(self, program: Program):
        self.program = program
        self.components: Dict[str, Component] = {}
        self.valid_units = {
            'V': ['VoltageSource'],
            'A': ['CurrentSource'],
            'ohm': ['Resistor'],
            'F': ['Capacitor'],
            'H': ['Inductor'],
            'Hz': ['ACSource']
        }
        self.valid_simulation_types = {'dc', 'ac', 'transient'}

    def analyze(self):
        # First pass: collect all component declarations
        for stmt in self.program.statements:
            if isinstance(stmt, Component):
                self._check_component(stmt)
                if stmt.name in self.components:
                    raise SemanticError(f"Component '{stmt.name}' is already defined")
                self.components[stmt.name] = stmt

        # Second pass: check connections and simulation
        has_simulation = False
        for stmt in self.program.statements:
            if isinstance(stmt, Connection):
                self._check_connection(stmt)
            elif isinstance(stmt, Simulation):
                has_simulation = True
                self._check_simulation(stmt)

        if not has_simulation:
            raise SemanticError("Circuit must include a simulation command")

    def _check_component(self, component: Component):
        # Check component value
        if component.value <= 0:
            raise SemanticError(f"Component value must be positive: {component.name}")

        # Check unit validity
        if component.type not in self.valid_units:
            raise SemanticError(f"Invalid component type: {component.type}")
        
        if component.unit not in self.valid_units[component.type]:
            raise SemanticError(f"Invalid unit '{component.unit}' for component type {component.type}")

    def _check_connection(self, connection: Connection):
        # Check if components exist
        for endpoint in [connection.endpoint1, connection.endpoint2]:
            if endpoint.component != 'ground' and endpoint.component not in self.components:
                raise SemanticError(f"Undefined component: {endpoint.component}")

        # Check if terminals are valid
        for endpoint in [connection.endpoint1, connection.endpoint2]:
            if endpoint.component != 'ground':
                component = self.components[endpoint.component]
                if endpoint.terminal not in ['positive', 'negative']:
                    raise SemanticError(f"Invalid terminal '{endpoint.terminal}' for component {endpoint.component}")

    def _check_simulation(self, simulation: Simulation):
        if simulation.type not in self.valid_simulation_types:
            raise SemanticError(f"Invalid simulation type: {simulation.type}")

        # Check simulation parameters if present
        if simulation.parameters:
            for param in simulation.parameters:
                if not isinstance(param.value, (int, float)) or param.value <= 0:
                    raise SemanticError(f"Invalid simulation parameter value: {param.name}")
