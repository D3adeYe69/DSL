from typing import Dict, Set, List, Union, Literal
from ast_nodes import (
    Program, ComponentDeclaration, Connection, SimulationNode,
    DCAnalysis, ACAnalysis, TransientAnalysis, NoiseAnalysis,
    MonteCarloAnalysis, ParametricAnalysis, AnalysisBlock
)

class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    def __init__(self, program: Program):
        self.program = program
        self.components: Dict[str, ComponentDeclaration] = {}
        self.valid_units = {
            'V': ['VoltageSource', 'ACSource'],
            'A': ['CurrentSource'],
            'ohm': ['Resistor'],
            'F': ['Capacitor'],
            'H': ['Inductor'],
            'Hz': ['ACSource']
        }
        self.valid_simulation_types = {'dc', 'ac', 'transient'}
        
        # Component parameter requirements
        self.required_params = {
            'ACSource': ['frequency', 'amplitude'],
            'VoltageSource': ['value'],
            'CurrentSource': ['value'],
            'Resistor': ['resistance'],
            'Capacitor': ['capacitance'],
            'Inductor': ['inductance']
        }

    def analyze(self):
        # First pass: collect all component declarations
        for component in self.program.components:
            self._check_component(component)
            if component.instance_name in self.components:
                raise SemanticError(f"Component '{component.instance_name}' is already defined")
            self.components[component.instance_name] = component

        # Second pass: check connections and simulation
        has_simulation = False
        for connection in self.program.connections:
            self._check_connection(connection)

        # Check analyses
        for analysis in self.program.analyses:
            has_simulation = True
            self._check_simulation(analysis)

        if not has_simulation:
            raise SemanticError("Circuit must include a simulation command")

    def _check_component(self, component: ComponentDeclaration):
        # Check component type
        valid_types = {
            'Resistor', 'Capacitor', 'Inductor', 'VoltageSource', 
            'CurrentSource', 'ACSource', 'Ammeter'
        }
        if component.type_name not in valid_types:
            raise SemanticError(f"Invalid component type: {component.type_name}")
        
        # Check required parameters
        if component.type_name in self.required_params:
            required = self.required_params[component.type_name]
            for param in required:
                if param not in component.named_params:
                    raise SemanticError(f"Missing required parameter '{param}' for {component.type_name} {component.instance_name}")
        
        # Check parameter values and units
        for param_name, param_value in component.named_params.items():
            if isinstance(param_value, Literal):
                # Check units for ACSource
                if component.type_name == 'ACSource':
                    if param_name == 'frequency' and param_value.unit != 'Hz':
                        raise SemanticError(f"Frequency must be in Hz for {component.instance_name}")
                    elif param_name == 'amplitude' and param_value.unit != 'V':
                        raise SemanticError(f"Amplitude must be in V for {component.instance_name}")
                # Check units for other components
                elif component.type_name in self.valid_units:
                    if param_value.unit and param_value.unit not in self.valid_units:
                        raise SemanticError(f"Invalid unit '{param_value.unit}' for {component.type_name} {component.instance_name}")

        # Check unit validity
        if component.type_name not in self.valid_units:
            raise SemanticError(f"Invalid component type: {component.type_name}")
        
        # Check unit if present in named parameters
        if 'unit' in component.named_params:
            unit = component.named_params['unit']
            if isinstance(unit, str) and unit not in self.valid_units[component.type_name]:
                raise SemanticError(f"Invalid unit '{unit}' for component type {component.type_name}")

    def _check_connection(self, connection: Connection):
        # Check if components exist
        for endpoint in connection.endpoints:
            if isinstance(endpoint, str) and endpoint.lower() != 'ground':
                if endpoint not in self.components:
                    raise SemanticError(f"Undefined component: {endpoint}")

        # Check if terminals are valid
        for endpoint in connection.endpoints:
            if isinstance(endpoint, str) and endpoint.lower() != 'ground':
                component = self.components[endpoint]
                if not any(terminal in ['positive', 'negative'] for terminal in component.terminals or []):
                    raise SemanticError(f"Invalid terminal for component {endpoint}")

    def _check_simulation(self, simulation: Union[SimulationNode, AnalysisBlock]):
        if isinstance(simulation, AnalysisBlock):
            for sim in simulation.simulations:
                self._check_simulation(sim)
            return

        if isinstance(simulation, DCAnalysis):
            # DC analysis has no additional parameters to check
            pass
        elif isinstance(simulation, ACAnalysis):
            # Check AC analysis parameters
            if simulation.analysis_type not in ['dec', 'oct', 'lin']:
                raise SemanticError(f"Invalid AC analysis type: {simulation.analysis_type}")
            if simulation.analysis_type in ['dec', 'oct'] and simulation.points_per_decade <= 0:
                raise SemanticError("Points per decade/octave must be positive")
            if simulation.analysis_type == 'lin' and simulation.total_points <= 0:
                raise SemanticError("Total points must be positive")
        elif isinstance(simulation, TransientAnalysis):
            # Check transient analysis parameters
            if simulation.step_time <= 0:
                raise SemanticError("Step time must be positive")
            if simulation.stop_time <= 0:
                raise SemanticError("Stop time must be positive")
            if simulation.start_time is not None and simulation.start_time < 0:
                raise SemanticError("Start time cannot be negative")
        elif isinstance(simulation, NoiseAnalysis):
            # Check noise analysis parameters
            if simulation.analysis_type not in ['dec', 'oct', 'lin']:
                raise SemanticError(f"Invalid noise analysis type: {simulation.analysis_type}")
            if simulation.output_node not in self.components:
                raise SemanticError(f"Output node '{simulation.output_node}' not found")
            if simulation.input_source not in self.components:
                raise SemanticError(f"Input source '{simulation.input_source}' not found")
        elif isinstance(simulation, ParametricAnalysis):
            # Check parametric analysis parameters
            if simulation.parameter_name not in self.components:
                raise SemanticError(f"Parameter '{simulation.parameter_name}' not found")
            if simulation.step_value is not None and simulation.step_value <= 0:
                raise SemanticError("Step value must be positive")
            if simulation.points is not None and simulation.points <= 0:
                raise SemanticError("Number of points must be positive")
