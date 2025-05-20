from flask import Flask, render_template, jsonify, request
import json
from main import draw_circuit
from lexer import Lexer
from parser import Parser
from ast_nodes import Program, ComponentDeclaration, Connection, ComponentTerminal, Subcircuit
import os

app = Flask(__name__)

class InteractiveVisualizer:
    def __init__(self):
        self.components = []
        self.connections = []
        self.subcircuits = []
        self.component_map = {}
        self.node_map = {}
        
    def add_component(self, component):
        comp_dict = {
            'id': getattr(component, 'name', ''),
            'type': getattr(component, 'type', ''),
            'value': getattr(component, 'value', 0),
            'unit': getattr(component, 'unit', ''),
            'position': {'x': 0, 'y': 0}
        }
        self.components.append(comp_dict)
        self.component_map[comp_dict['id']] = comp_dict
        
    def add_subcircuit_instance(self, name, type_, pins):
        self.subcircuits.append({
            'id': name,
            'type': type_,
            'pins': pins,
            'position': {'x': 0, 'y': 0}
        })
        
    def add_connection(self, from_comp, from_term, to_comp, to_term):
        self.connections.append({
            'from': from_comp,
            'from_term': from_term,
            'to': to_comp,
            'to_term': to_term
        })
        
    def add_connection_to_node(self, from_comp, from_term, node):
        self.connections.append({
            'from': from_comp,
            'from_term': from_term,
            'to': node,
            'to_term': 'node'
        })
        
    def generate_layout(self):
        # Place subcircuits and components in a row
        x = 200
        for subckt in self.subcircuits:
            subckt['position']['x'] = x
            subckt['position']['y'] = 150
            x += 300
        for comp in self.components:
            comp['position']['x'] = x
            comp['position']['y'] = 150
            x += 300
        # Place nodes at the bottom
        node_names = set()
        for conn in self.connections:
            if conn['to_term'] == 'node':
                node_names.add(conn['to'])
        node_x = {node: 200 + i * 200 for i, node in enumerate(node_names)}
        node_y = 350
        self.node_map = {node: {'x': x, 'y': node_y} for node, x in node_x.items()}
        
    def to_json(self):
        return {
            'components': self.components,
            'subcircuits': self.subcircuits,
            'connections': self.connections,
            'nodes': self.node_map
        }

def get_subcircuit_pins(subckt: Subcircuit):
    # Find all node names used in Connect inside the subcircuit that are not component terminals
    pins = set()
    for conn in subckt.connections:
        for ep in conn.endpoints:
            if isinstance(ep, str) and ep not in ('ground',):
                pins.add(ep)
    # Always include 'ground' if used
    for conn in subckt.connections:
        for ep in conn.endpoints:
            if isinstance(ep, str) and ep == 'ground':
                pins.add('ground')
    return list(pins)

@app.route('/')
def index():
    try:
        with open('circuit.dsl', encoding='utf-8') as f:
            dsl_code = f.read()
    except Exception:
        dsl_code = ''
    return render_template('circuit.html', dsl_code=dsl_code)

@app.route('/parse-dsl', methods=['POST'])
def parse_dsl():
    code = request.json.get('code', '')
    tokens = Lexer(code).tokenize()
    program = Parser(tokens).parse()
    visualizer = InteractiveVisualizer()
    # Map subcircuit name to Subcircuit object
    subckt_defs = {sub.name: sub for sub in program.subcircuits}
    # Add subcircuit instances and regular components
    for comp in program.components:
        if comp.type in subckt_defs:
            pins = get_subcircuit_pins(subckt_defs[comp.type])
            visualizer.add_subcircuit_instance(comp.name, comp.type, pins)
        else:
            visualizer.add_component(comp)
    # Add connections
    for conn in program.connections:
        endpoints = conn.endpoints
        if len(endpoints) == 2:
            ep1, ep2 = endpoints
            # If endpoint is subcircuit pin, connect to subcircuit instance and pin
            def parse_ep(ep):
                if isinstance(ep, ComponentTerminal):
                    # If hierarchical (e.g., D1.input), treat as (D1, input)
                    if '.' in ep.component:
                        parts = ep.component.split('.')
                        return parts[0], parts[-1]  # (instance, pin)
                    else:
                        return ep.component, ep.terminal
                else:
                    return ep, 'node'
            from_comp, from_term = parse_ep(ep1)
            to_comp, to_term = parse_ep(ep2)
            visualizer.add_connection(from_comp, from_term, to_comp, to_term)
    visualizer.generate_layout()
    return jsonify(visualizer.to_json())

@app.route('/generate-dsl', methods=['POST'])
def generate_dsl():
    data = request.json
    lines = []
    for comp in data.get('components', []):
        lines.append(f"{comp['type']} {comp['id']}({comp['value']} {comp['unit']});")
    for subckt in data.get('subcircuits', []):
        lines.append(f"{subckt['type']} {subckt['id']};")
    for conn in data.get('connections', []):
        if conn['to_term'] == 'node':
            lines.append(f"Connect({conn['from']}.{conn['from_term']}, {conn['to']});")
        else:
            lines.append(f"Connect({conn['from']}.{conn['from_term']}, {conn['to']}.{conn['to_term']});")
    code = '\n'.join(lines)
    return jsonify({'code': code})

if __name__ == '__main__':
    app.run(debug=True) 