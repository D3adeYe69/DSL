import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
import json
import math
from typing import Dict, List, Tuple, Set, Optional
from lexer import Lexer
from parser import Parser
from ast_nodes import (
    Program, ComponentDeclaration, SubcircuitInstance, Connection, 
    Terminal, Node, Subcircuit, VisualizationVisitor, ValidationVisitor,
    SimulationNode, AnalysisBlock, VariableDeclaration
)

app = Flask(__name__)

class EnhancedVisualizationVisitor(VisualizationVisitor):
    """Extended visualization visitor with better layout and error handling"""
    
    def __init__(self):
        super().__init__()
        self.variables = {}
        self.simulation_blocks = []
        self.errors = []
        self.warnings = []
        self.node_positions = {}
        self.layout_grid = {}
    
    def visit_Program(self, program: Program):
        """Enhanced program visitor with validation"""
        try:
            # First, validate the program
            validator = ValidationVisitor()
            validator.visit(program)
            self.errors.extend(validator.errors)
            self.warnings.extend(validator.warnings)
            
            # Collect variables
            for var in program.variables:
                self.visit_VariableDeclaration(var)
            
            # Collect subcircuit definitions
            for subckt in program.subcircuits:
                self.subcircuit_defs[subckt.name] = subckt
            
            # Process components and instances
            for comp in program.components:
                self.visit_ComponentDeclaration(comp)
            
            for inst in program.subcircuit_instances:
                self.visit_SubcircuitInstance(inst)
                
            for conn in program.connections:
                self.visit_Connection(conn)
            
            # Process simulation blocks
            for analysis in program.analyses:
                self.visit_AnalysisBlock(analysis)
                
        except Exception as e:
            self.errors.append(f"Error processing program: {str(e)}")
    
    def visit_VariableDeclaration(self, node: VariableDeclaration):
        """Collect variable declarations for parameter resolution"""
        self.variables[node.name] = {
            'value': node.value,
            'is_constant': node.is_constant,
            'unit': node.unit
        }
    
    def visit_AnalysisBlock(self, node: AnalysisBlock):
        """Process simulation and analysis blocks"""
        analysis_data = {
            'name': node.name,
            'simulations': [],
            'plots': []
        }
        
        for sim in node.simulations:
            sim_data = self._process_simulation(sim)
            if sim_data:
                analysis_data['simulations'].append(sim_data)
        
        for plot in node.plots:
            plot_data = {
                'variables': plot.variables,
                'type': plot.plot_type,
                'options': plot.options
            }
            analysis_data['plots'].append(plot_data)
        
        self.simulation_blocks.append(analysis_data)
    
    def _process_simulation(self, sim: SimulationNode) -> Optional[Dict]:
        """Process different types of simulation commands"""
        sim_type = type(sim).__name__
        
        if sim_type == 'DCAnalysis':
            return {
                'type': 'dc',
                'sweep_variable': sim.sweep_variable,
                'start': self._evaluate_expression(sim.start_value) if sim.start_value else None,
                'stop': self._evaluate_expression(sim.stop_value) if sim.stop_value else None,
                'step': self._evaluate_expression(sim.step_value) if sim.step_value else None,
                'options': sim.options
            }
        elif sim_type == 'ACAnalysis':
            return {
                'type': 'ac',
                'analysis_type': sim.analysis_type,
                'points': sim.points_per_decade or sim.total_points,
                'start_freq': self._evaluate_expression(sim.start_frequency),
                'stop_freq': self._evaluate_expression(sim.stop_frequency),
                'options': sim.options
            }
        elif sim_type == 'TransientAnalysis':
            return {
                'type': 'transient',
                'step_time': self._evaluate_expression(sim.step_time),
                'stop_time': self._evaluate_expression(sim.stop_time),
                'start_time': self._evaluate_expression(sim.start_time) if sim.start_time else 0,
                'options': sim.options
            }
        
        return None
    
    def _evaluate_expression(self, expr) -> Optional[float]:
        """Simple expression evaluation for visualization"""
        if not expr:
            return None
        
        from ..ast_nodes import Literal, Identifier
        
        if isinstance(expr, Literal):
            if isinstance(expr.value, (int, float)):
                return float(expr.value)
        elif isinstance(expr, Identifier):
            # Look up variable
            if expr.name in self.variables:
                var_value = self.variables[expr.name]['value']
                return self._evaluate_expression(var_value)
        
        return None

class SmartLayoutEngine:
    """Advanced layout engine for circuit visualization"""
    
    def __init__(self, components: List[Dict], subcircuit_instances: List[Dict], 
                 connections: List[Dict], grid_size: int = 100):
        self.components = components
        self.subcircuit_instances = subcircuit_instances
        self.connections = connections
        self.grid_size = grid_size
        self.positions = {}
        self.node_clusters = {}
        
    def generate_layout(self) -> Dict:
        """Generate intelligent layout using force-directed approach"""
        all_elements = self.components + self.subcircuit_instances
        
        # Initialize positions
        self._initialize_positions(all_elements)
        
        # Build connection graph
        connection_graph = self._build_connection_graph()
        
        # Apply force-directed layout
        self._apply_force_directed_layout(all_elements, connection_graph)
        
        # Generate node positions
        node_positions = self._generate_node_positions()
        
        return {
            'components': self.components,
            'subcircuit_instances': self.subcircuit_instances,
            'connections': self.connections,
            'nodes': node_positions
        }
    
    def _initialize_positions(self, elements: List[Dict]):
        """Initialize positions in a grid pattern"""
        cols = math.ceil(math.sqrt(len(elements)))
        for i, element in enumerate(elements):
            row = i // cols
            col = i % cols
            element['position'] = {
                'x': col * self.grid_size * 3 + 200,
                'y': row * self.grid_size * 2 + 150
            }
    
    def _build_connection_graph(self) -> Dict[str, Set[str]]:
        """Build graph of connections between components"""
        graph = {}
        
        for conn in self.connections:
            from_comp = self._get_component_from_endpoint(conn['from'])
            to_comp = self._get_component_from_endpoint(conn['to'])
            
            if from_comp and to_comp and from_comp != to_comp:
                if from_comp not in graph:
                    graph[from_comp] = set()
                if to_comp not in graph:
                    graph[to_comp] = set()
                
                graph[from_comp].add(to_comp)
                graph[to_comp].add(from_comp)
        
        return graph
    
    def _get_component_from_endpoint(self, endpoint: Dict) -> Optional[str]:
        """Extract component name from connection endpoint"""
        if endpoint['type'] == 'terminal':
            return endpoint['component']
        return None
    
    def _apply_force_directed_layout(self, elements: List[Dict], graph: Dict[str, Set[str]]):
        """Apply force-directed algorithm for better positioning"""
        # Simple spring-force algorithm
        for iteration in range(50):  # Limited iterations for performance
            forces = {}
            
            # Calculate forces
            for element in elements:
                element_id = element['id']
                forces[element_id] = {'x': 0, 'y': 0}
                
                # Repulsive forces from other elements
                for other in elements:
                    if other['id'] != element_id:
                        dx = element['position']['x'] - other['position']['x']
                        dy = element['position']['y'] - other['position']['y']
                        distance = max(math.sqrt(dx*dx + dy*dy), 1)
                        
                        # Repulsive force
                        force = 10000 / (distance * distance)
                        forces[element_id]['x'] += force * dx / distance
                        forces[element_id]['y'] += force * dy / distance
                
                # Attractive forces from connected elements
                if element_id in graph:
                    for connected_id in graph[element_id]:
                        connected_element = next((e for e in elements if e['id'] == connected_id), None)
                        if connected_element:
                            dx = connected_element['position']['x'] - element['position']['x']
                            dy = connected_element['position']['y'] - element['position']['y']
                            distance = max(math.sqrt(dx*dx + dy*dy), 1)
                            
                            # Attractive force
                            force = distance / 100
                            forces[element_id]['x'] += force * dx / distance
                            forces[element_id]['y'] += force * dy / distance
            
            # Apply forces with damping
            damping = 0.1
            for element in elements:
                element_id = element['id']
                element['position']['x'] += forces[element_id]['x'] * damping
                element['position']['y'] += forces[element_id]['y'] * damping
                
                # Keep elements within reasonable bounds
                element['position']['x'] = max(50, min(element['position']['x'], 1500))
                element['position']['y'] = max(50, min(element['position']['y'], 800))
    
    def _generate_node_positions(self) -> Dict[str, Dict]:
        """Generate positions for circuit nodes"""
        node_connections = {}
        
        # Group connections by node
        for conn in self.connections:
            for endpoint in [conn['from'], conn['to']]:
                if endpoint['type'] == 'node':
                    node_name = endpoint['node']
                    if node_name not in node_connections:
                        node_connections[node_name] = []
                    node_connections[node_name].append(conn)
        
        # Position nodes based on connected components
        node_positions = {}
        for node_name, connections in node_connections.items():
            # Find average position of connected components
            total_x, total_y, count = 0, 0, 0
            
            for conn in connections:
                for endpoint in [conn['from'], conn['to']]:
                    if endpoint['type'] == 'terminal':
                        comp_id = endpoint['component']
                        # Find component position
                        all_elements = self.components + self.subcircuit_instances
                        comp = next((e for e in all_elements if e['id'] == comp_id), None)
                        if comp:
                            total_x += comp['position']['x']
                            total_y += comp['position']['y']
                            count += 1
            
            if count > 0:
                node_positions[node_name] = {
                    'x': total_x / count,
                    'y': total_y / count + 50  # Offset slightly below components
                }
            else:
                # Default position for orphaned nodes
                node_positions[node_name] = {'x': 100, 'y': 400}
        
        return node_positions

class EnhancedInteractiveVisualizer:
    """Enhanced visualizer with better error handling and features"""
    
    def __init__(self):
        self.visitor = EnhancedVisualizationVisitor()
        self.layout_engine = None
        
    def process_program(self, program: Program) -> Dict:
        """Process AST program and generate visualization data"""
        self.visitor.visit(program)
        
        # Create layout engine
        self.layout_engine = SmartLayoutEngine(
            self.visitor.components,
            self.visitor.subcircuit_instances,
            self.visitor.connections
        )
        
        # Generate layout
        layout_data = self.layout_engine.generate_layout()
        
        # Add additional metadata
        result = {
            **layout_data,
            'variables': self.visitor.variables,
            'simulation_blocks': self.visitor.simulation_blocks,
            'subcircuit_definitions': {
                name: {
                    'ports': subckt.get_port_names(),
                    'parameters': [p.name for p in subckt.parameters]
                }
                for name, subckt in self.visitor.subcircuit_defs.items()
            },
            'errors': self.visitor.errors,
            'warnings': self.visitor.warnings
        }
        
        return result

@app.route('/')
def index():
    """Serve the main circuit editor page"""
    try:
        with open('circuit.dsl', encoding='utf-8') as f:
            dsl_code = f.read()
    except FileNotFoundError:
        dsl_code = '''// Example circuit
R R1 (1kΩ);
C C1 (100nF);
L L1 (10mH);

Connect R1.1 VCC;
Connect R1.2 C1.1;
Connect C1.2 GND;

// DC Analysis
analysis main_analysis {
    dc_sweep VCC 0 5 0.1;
    plot v(R1.2);
}
'''
    except Exception as e:
        dsl_code = f'// Error loading circuit.dsl: {str(e)}'
    
    return render_template('circuit.html', dsl_code=dsl_code)

@app.route('/parse-dsl', methods=['POST'])
def parse_dsl():
    """Parse DSL code and return visualization data"""
    code = request.json.get('code', '')
    
    if not code.strip():
        return jsonify({'error': 'Empty code provided', 'type': 'ValidationError'}), 400
    
    try:
        # Tokenize
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        if not tokens:
            return jsonify({'error': 'No valid tokens found', 'type': 'LexerError'}), 400
        
        # Parse
        parser = Parser(tokens)
        program = parser.parse()
        
        if not program:
            return jsonify({'error': 'Failed to parse program', 'type': 'ParserError'}), 400
        
        # Visualize
        visualizer = EnhancedInteractiveVisualizer()
        result = visualizer.process_program(program)
        
        return jsonify(result)
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Provide more helpful error messages
        if 'token' in error_msg.lower():
            error_type = 'SyntaxError'
        elif 'parse' in error_msg.lower():
            error_type = 'ParseError'
        
        return jsonify({
            'error': error_msg,
            'type': error_type,
            'components': [],
            'subcircuit_instances': [],
            'connections': [],
            'nodes': {}
        }), 400

@app.route('/generate-dsl', methods=['POST'])
def generate_dsl():
    """Generate DSL code from visualization data"""
    try:
        data = request.json
        lines = []
        
        # Add header comment
        lines.append("// Generated circuit")
        lines.append("")
        
        # Generate component declarations
        for comp in data.get('components', []):
            value_str = ""
            if comp.get('value') and comp.get('unit'):
                value_str = f" ({comp['value']}{comp['unit']})"
            elif comp.get('value'):
                value_str = f" ({comp['value']})"
            
            lines.append(f"{comp['type']} {comp['id']}{value_str};")
        
        # Generate subcircuit instances
        for subckt in data.get('subcircuit_instances', []):
            lines.append(f"{subckt['type']} {subckt['id']};")
        
        if data.get('components') or data.get('subcircuit_instances'):
            lines.append("")
        
        # Generate connections
        for conn in data.get('connections', []):
            from_ep = conn['from']
            to_ep = conn['to']
            
            def format_endpoint(ep):
                if ep['type'] == 'terminal':
                    return f"{ep['component']}.{ep['terminal']}"
                elif ep['type'] == 'node':
                    if ep.get('is_ground'):
                        return "GND"
                    return ep['node']
                return "unknown"
            
            from_str = format_endpoint(from_ep)
            to_str = format_endpoint(to_ep)
            
            if from_str != "unknown" and to_str != "unknown":
                lines.append(f"Connect {from_str} {to_str};")
        
        # Add simulation blocks if present
        if data.get('simulation_blocks'):
            lines.append("")
            for sim_block in data['simulation_blocks']:
                lines.append(f"analysis {sim_block['name']} {{")
                for sim in sim_block.get('simulations', []):
                    if sim['type'] == 'dc':
                        if sim.get('sweep_variable'):
                            lines.append(f"    dc_sweep {sim['sweep_variable']} {sim.get('start', 0)} {sim.get('stop', 1)} {sim.get('step', 0.1)};")
                        else:
                            lines.append("    dc_analysis;")
                    elif sim['type'] == 'ac':
                        lines.append(f"    ac_analysis {sim['analysis_type']} {sim.get('points', 100)} {sim.get('start_freq', '1Hz')} {sim.get('stop_freq', '1MHz')};")
                    elif sim['type'] == 'transient':
                        lines.append(f"    transient_analysis {sim.get('step_time', '1ms')} {sim.get('stop_time', '1s')};")
                
                for plot in sim_block.get('plots', []):
                    vars_str = ' '.join(plot['variables'])
                    lines.append(f"    plot {vars_str};")
                
                lines.append("}")
        
        return jsonify({'dsl': "\n".join(lines)})
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate DSL: {str(e)}'}), 400

@app.route('/validate-dsl', methods=['POST'])
def validate_dsl():
    """Validate DSL code without full parsing"""
    code = request.json.get('code', '')
    
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        program = parser.parse()
        
        # Run validation
        validator = ValidationVisitor()
        validator.visit(program)
        
        return jsonify({
            'valid': len(validator.errors) == 0,
            'errors': validator.errors,
            'warnings': validator.warnings
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [str(e)],
            'warnings': []
        })

@app.route('/export-netlist', methods=['POST'])
def export_netlist():
    """Export circuit as SPICE netlist"""
    # This would require a separate netlist generation visitor
    return jsonify({'error': 'Netlist export not implemented yet'}), 501

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)