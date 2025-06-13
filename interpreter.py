from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass
from ast_nodes import (
    Program, ComponentDeclaration, SubcircuitInstance, Terminal, Node,
    Connection, MacroDefinition, MacroInvocation, Subcircuit, SimulationNode,
    AnalysisBlock, DCAnalysis, ACAnalysis, TransientAnalysis, NoiseAnalysis,
    MonteCarloAnalysis, ParametricAnalysis, ExpressionNode, Literal, Identifier,
    BinaryOp, UnaryOp, FunctionCall, ArrayLiteral, ASTNode, ForLoop
)
import re
import copy


@dataclass
class InterpreterContext:
    """Context for interpreter state - supports nested scopes"""

    variables: Dict[str, Any]
    parent: Optional['InterpreterContext'] = None

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        elif self.parent:
            return self.parent.get(name)
        else:
            raise NameError(f"Undefined variable: {name}")

    def set(self, name: str, value: Any):
        self.variables[name] = value


@dataclass
class NetlistNode:
    """Represents a circuit node with metadata"""

    id: int
    name: Optional[str] = None
    is_ground: bool = False
    voltage: Optional[float] = None  # For analysis results

    def __str__(self):
        return "0" if self.is_ground else str(self.id)


class UnitConversionVisitor:
    """Visitor to convert units and annotate literals with SI values"""

    UNIT_MULTIPLIERS = {
        'f': 1e-15,
        'p': 1e-12,
        'n': 1e-9,
        'u': 1e-6,
        'μ': 1e-6,
        'm': 1e-3,
        'k': 1e3,
        'K': 1e3,
        'M': 1e6,
        'G': 1e9,
        'T': 1e12,
    }

    def visit_program(self, program: Program):
        """Visit all nodes in the program"""
        for var_decl in program.variables:
            self.visit_expression(var_decl.value)

        for component in program.components:
            self.visit_component(component)

        for connection in program.connections:
            self.visit_connection(connection)

        for macro in program.macros:
            self.visit_macro(macro)

        for subckt in program.subcircuits:
            self.visit_subcircuit(subckt)

        for analysis in program.analyses:
            self.visit_analysis(analysis)

    def visit_component(self, comp: ComponentDeclaration):
        """Visit component parameters"""
        for param in comp.positional_params:
            self.visit_expression(param)

        for param in comp.named_params.values():
            self.visit_expression(param)

        if isinstance(comp, SubcircuitInstance):
            for arg in comp.arguments:
                self.visit_expression(arg)

    def visit_connection(self, conn: Connection):
        """Visit connection (no expressions typically)"""
        pass

    def visit_macro(self, macro: MacroDefinition):
        """Visit macro body"""
        for node in macro.body:
            if isinstance(node, ComponentDeclaration):
                self.visit_component(node)
            elif isinstance(node, Connection):
                self.visit_connection(node)

    def visit_subcircuit(self, subckt: Subcircuit):
        """Visit subcircuit contents"""
        for comp in subckt.components:
            self.visit_component(comp)

        for conn in subckt.connections:
            self.visit_connection(conn)

        for inner_subckt in subckt.inner_subcircuits:
            self.visit_subcircuit(inner_subckt)

    def visit_analysis(self, analysis: AnalysisBlock):
        """Visit analysis simulations"""
        for sim in analysis.simulations:
            self.visit_simulation(sim)

    def visit_expression(self, expr: ExpressionNode):
        """Visit and convert expression nodes"""
        if isinstance(expr, Literal):
            self.convert_literal(expr)
        elif isinstance(expr, BinaryOp):
            self.visit_expression(expr.left)
            self.visit_expression(expr.right)
        elif isinstance(expr, UnaryOp):
            self.visit_expression(expr.operand)
        elif isinstance(expr, FunctionCall):
            for arg in expr.args:
                self.visit_expression(arg)
        elif isinstance(expr, ArrayLiteral):
            for elem in expr.elements:
                self.visit_expression(elem)

    def convert_literal(self, literal: Literal):
        """Convert literal value and store SI value in annotations"""
        if isinstance(literal.value, (int, float)):
            literal.annotations['si_value'] = float(literal.value)
            return

        if isinstance(literal.value, str):
            # Try to parse as number with unit
            match = re.match(r'^(-?\d*\.?\d+)([a-zA-Z]*)$', literal.value.strip())
            if match:
                number_part, unit_part = match.groups()
                base_value = float(number_part)

                # Apply unit multipliers
                if unit_part and unit_part[0] in self.UNIT_MULTIPLIERS:
                    base_value *= self.UNIT_MULTIPLIERS[unit_part[0]]

                literal.annotations['si_value'] = base_value
                literal.annotations['original_unit'] = unit_part
            else:
                # Keep as string
                literal.annotations['si_value'] = literal.value


class ValidationVisitor:
    """Visitor to perform semantic validation before interpretation"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.component_names: Set[str] = set()
        self.net_names: Set[str] = set()
        self.macro_names: Set[str] = set()
        self.subcircuit_names: Set[str] = set()
        self.variables: Set[str] = set()

    def add_error(self, message: str, node: Optional[ASTNode] = None):
        """Add error with optional source location"""
        if node and node.source_location:
            loc = node.source_location
            self.errors.append(f"{loc.filename}:{loc.line}:{loc.column}: {message}")
        else:
            self.errors.append(message)

    def add_warning(self, message: str, node: Optional[ASTNode] = None):
        """Add warning with optional source location"""
        if node and node.source_location:
            loc = node.source_location
            self.warnings.append(f"{loc.filename}:{loc.line}:{loc.column}: Warning: {message}")
        else:
            self.warnings.append(f"Warning: {message}")

    def validate_program(self, program: Program) -> bool:
        """Validate entire program, return True if no errors"""
        # First pass: collect all definitions
        for var_decl in program.variables:
            if var_decl.name in self.variables:
                self.add_error(f"Duplicate variable definition: {var_decl.name}", var_decl)
            self.variables.add(var_decl.name)

        for macro in program.macros:
            if macro.name in self.macro_names:
                self.add_error(f"Duplicate macro definition: {macro.name}", macro)
            self.macro_names.add(macro.name)

        for subckt in program.subcircuits:
            if subckt.name in self.subcircuit_names:
                self.add_error(f"Duplicate subcircuit definition: {subckt.name}", subckt)
            self.subcircuit_names.add(subckt.name)

        # Second pass: validate references and usage
        for component in program.components:
            self.validate_component(component)

        for connection in program.connections:
            self.validate_connection(connection)

        for macro in program.macros:
            self.validate_macro(macro)

        for subckt in program.subcircuits:
            self.validate_subcircuit(subckt)

        for analysis in program.analyses:
            self.validate_analysis(analysis)

        return len(self.errors) == 0

    def validate_component(self, comp: ComponentDeclaration):
        """Validate component declaration"""
        if comp.instance_name in self.component_names:
            self.add_error(f"Duplicate component name: {comp.instance_name}", comp)
        self.component_names.add(comp.instance_name)

        # Validate component type exists (for subcircuit instances)
        if isinstance(comp, SubcircuitInstance):
            if comp.type_name not in self.subcircuit_names:
                self.add_error(f"Undefined subcircuit type: {comp.type_name}", comp)

        # Validate parameter expressions
        for param in comp.positional_params:
            self.validate_expression(param)

        for param in comp.named_params.values():
            self.validate_expression(param)

    def validate_connection(self, conn: Connection):
        """Validate connection"""
        if conn.net_name:
            self.net_names.add(conn.net_name)

        # Check for valid endpoints
        for endpoint in conn.endpoints:
            if isinstance(endpoint, Terminal):
                if endpoint.component_name not in self.component_names:
                    self.add_warning(
                        f"Connection references undefined component: {endpoint.component_name}",
                        conn,
                    )

    def validate_macro(self, macro: MacroDefinition):
        """Validate macro definition"""
        # Create temporary context for macro validation
        old_components = self.component_names.copy()

        for node in macro.body:
            if isinstance(node, ComponentDeclaration):
                self.validate_component(node)
            elif isinstance(node, Connection):
                self.validate_connection(node)

        # Restore component names (macro components are local)
        self.component_names = old_components

    def validate_subcircuit(self, subckt: Subcircuit):
        """Validate subcircuit definition"""
        # Create temporary context for subcircuit validation
        old_components = self.component_names.copy()
        old_nets = self.net_names.copy()

        for comp in subckt.components:
            self.validate_component(comp)

        for conn in subckt.connections:
            self.validate_connection(conn)

        for inner_subckt in subckt.inner_subcircuits:
            self.validate_subcircuit(inner_subckt)

        # Restore context
        self.component_names = old_components
        self.net_names = old_nets

    def validate_analysis(self, analysis: AnalysisBlock):
        """Validate analysis block"""
        for sim in analysis.simulations:
            self.validate_simulation(sim)

    def validate_expression(self, expr: ExpressionNode):
        """Validate expression references"""
        if isinstance(expr, Identifier):
            if expr.name not in self.variables:
                self.add_error(f"Undefined variable: {expr.name}", expr)
        elif isinstance(expr, BinaryOp):
            self.validate_expression(expr.left)
            self.validate_expression(expr.right)
        elif isinstance(expr, UnaryOp):
            self.validate_expression(expr.operand)
        elif isinstance(expr, FunctionCall):
            # Could validate function existence here
            for arg in expr.args:
                self.validate_expression(arg)
        elif isinstance(expr, ArrayLiteral):
            for elem in expr.elements:
                self.validate_expression(elem)


class SubcircuitFlattener:
    """Visitor to flatten subcircuit instances into the main netlist"""

    def __init__(self, subcircuits: Dict[str, Subcircuit]):
        self.subcircuits = subcircuits
        self.instance_counter = 0

    def flatten_program(self, program: Program) -> Program:
        """Flatten all subcircuit instances in the program"""
        flattened_components = []
        flattened_connections = []

        for component in program.components:
            if isinstance(component, SubcircuitInstance):
                # Flatten this subcircuit instance
                flat_comps, flat_conns = self.flatten_subcircuit_instance(component)
                flattened_components.extend(flat_comps)
                flattened_connections.extend(flat_conns)
            else:
                flattened_components.append(component)

        # Add original connections
        flattened_connections.extend(program.connections)

        return Program(
            variables=program.variables,
            components=flattened_components,
            connections=flattened_connections,
            macros=program.macros,
            subcircuits=program.subcircuits,
            analyses=program.analyses,
        )

    def flatten_subcircuit_instance(
        self, instance: SubcircuitInstance
    ) -> tuple[List[ComponentDeclaration], List[Connection]]:
        """Flatten a single subcircuit instance"""
        if instance.type_name not in self.subcircuits:
            return [], []

        subckt = self.subcircuits[instance.type_name]
        self.instance_counter += 1
        prefix = f"{instance.instance_name}_"

        # Create name mapping for ports
        port_mapping = {}
        for i, port in enumerate(subckt.ports):
            if i < len(instance.port_connections):
                port_mapping[port.name] = instance.port_connections[i]
            else:
                port_mapping[port.name] = f"{prefix}UNCONNECTED_{i}"

        # Flatten components with name prefixing
        flat_components = []
        for comp in subckt.components:
            new_comp = copy.deepcopy(comp)
            new_comp.instance_name = f"{prefix}{comp.instance_name}"

            # Recursively flatten nested subcircuit instances
            if isinstance(new_comp, SubcircuitInstance):
                nested_comps, nested_conns = self.flatten_subcircuit_instance(new_comp)
                flat_components.extend(nested_comps)
                # Handle nested connections separately
            else:
                flat_components.append(new_comp)

        # Flatten connections with name mapping
        flat_connections = []
        for conn in subckt.connections:
            new_conn = copy.deepcopy(conn)

            # Update net name
            if new_conn.net_name and new_conn.net_name in port_mapping:
                new_conn.net_name = port_mapping[new_conn.net_name]
            elif new_conn.net_name:
                new_conn.net_name = f"{prefix}{new_conn.net_name}"

            # Update endpoints
            for i, endpoint in enumerate(new_conn.endpoints):
                if isinstance(endpoint, Terminal):
                    new_endpoint = copy.deepcopy(endpoint)
                    new_endpoint.component_name = f"{prefix}{endpoint.component_name}"
                    new_conn.endpoints[i] = new_endpoint
                elif isinstance(endpoint, str) and endpoint in port_mapping:
                    new_conn.endpoints[i] = port_mapping[endpoint]
                elif isinstance(endpoint, str) and endpoint not in ['ground', 'gnd', '0']:
                    new_conn.endpoints[i] = f"{prefix}{endpoint}"

            flat_connections.append(new_conn)

        return flat_components, flat_connections


class Interpreter:
    def __init__(self, program: Program):
        self.program = program
        self.context = InterpreterContext({})
        self.node_counter = 1
        self.nodes: Dict[str, NetlistNode] = {}
        self.terminal_connections: Dict[str, Dict[str, NetlistNode]] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Initialize ground node
        self.nodes['ground'] = NetlistNode(0, 'ground', is_ground=True)
        self.nodes['gnd'] = self.nodes['ground']  # Common alias
        self.nodes['0'] = self.nodes['ground']  # SPICE convention

    def add_error(self, message: str, node: Optional[ASTNode] = None):
        """Add error with optional source location"""
        if node and node.source_location:
            loc = node.source_location
            self.errors.append(f"{loc.filename}:{loc.line}:{loc.column}: {message}")
        else:
            self.errors.append(message)

    def add_warning(self, message: str, node: Optional[ASTNode] = None):
        """Add warning with optional source location"""
        if node and node.source_location:
            loc = node.source_location
            self.warnings.append(f"{loc.filename}:{loc.line}:{loc.column}: Warning: {message}")
        else:
            self.warnings.append(f"Warning: {message}")

    def evaluate_expression(self, expr: ExpressionNode) -> Any:
        """Evaluate expressions using SI values from annotations"""
        if isinstance(expr, Literal):
            # Use pre-computed SI value if available
            if 'si_value' in expr.annotations:
                return expr.annotations['si_value']
            return expr.value

        elif isinstance(expr, Identifier):
            try:
                return self.context.get(expr.name)
            except NameError:
                self.add_error(f"Undefined identifier: {expr.name}", expr)
                return 0

        elif isinstance(expr, BinaryOp):
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)
            return self._apply_binary_op(expr.op, left, right, expr)

        elif isinstance(expr, UnaryOp):
            operand = self.evaluate_expression(expr.operand)
            return self._apply_unary_op(expr.op, operand, expr)

        elif isinstance(expr, FunctionCall):
            args = [self.evaluate_expression(arg) for arg in expr.args]
            return self._call_function(expr.name, args, expr)

        elif isinstance(expr, ArrayLiteral):
            return [self.evaluate_expression(elem) for elem in expr.elements]

        else:
            self.add_error(f"Unknown expression type: {type(expr)}", expr)
            return 0

    def _apply_binary_op(self, op: str, left: Any, right: Any, node: ASTNode) -> Any:
        """Apply binary operations with type checking"""
        try:
            if op == '+':
                return left + right
            elif op == '-':
                return left - right
            elif op == '*':
                return left * right
            elif op == '/':
                if right == 0:
                    self.add_error("Division by zero", node)
                    return float('inf')
                return left / right
            elif op == '**' or op == '^':
                return left**right
            elif op == '||':  # Parallel resistance
                if left == 0 or right == 0:
                    return 0
                return (left * right) / (left + right)
            elif op == '&&':
                return left and right
            elif op == '==':
                return left == right
            elif op == '!=':
                return left != right
            elif op == '<':
                return left < right
            elif op == '>':
                return left > right
            elif op == '<=':
                return left <= right
            elif op == '>=':
                return left >= right
            else:
                self.add_error(f"Unknown binary operator: {op}", node)
                return 0
        except Exception as e:
            self.add_error(f"Error in binary operation: {e}", node)
            return 0

    def _apply_unary_op(self, op: str, operand: Any, node: ASTNode) -> Any:
        """Apply unary operations"""
        try:
            if op == '-':
                return -operand
            elif op == '+':
                return +operand
            elif op == '!':
                return not operand
            elif op == 'sqrt':
                return operand**0.5
            elif op == 'abs':
                return abs(operand)
            else:
                self.add_error(f"Unknown unary operator: {op}", node)
                return operand
        except Exception as e:
            self.add_error(f"Error in unary operation: {e}", node)
            return operand

    def _call_function(self, name: str, args: List[Any], node: ASTNode) -> Any:
        """Built-in function calls"""
        import math

        try:
            if name == 'sin':
                return math.sin(args[0])
            elif name == 'cos':
                return math.cos(args[0])
            elif name == 'tan':
                return math.tan(args[0])
            elif name == 'log':
                return math.log(args[0])
            elif name == 'log10':
                return math.log10(args[0])
            elif name == 'exp':
                return math.exp(args[0])
            elif name == 'sqrt':
                return math.sqrt(args[0])
            elif name == 'abs':
                return abs(args[0])
            elif name == 'min':
                return min(args)
            elif name == 'max':
                return max(args)
            elif name == 'range':
                if len(args) == 1:
                    return list(range(int(args[0])))
                elif len(args) == 2:
                    return list(range(int(args[0]), int(args[1])))
                elif len(args) == 3:
                    return list(range(int(args[0]), int(args[1]), int(args[2])))
            else:
                self.add_error(f"Unknown function: {name}", node)
                return 0
        except Exception as e:
            self.add_error(f"Error calling function {name}: {e}", node)
            return 0

    def process_variables(self):
        """Process global variable declarations"""
        for var_decl in self.program.variables:
            value = self.evaluate_expression(var_decl.value)
            self.context.set(var_decl.name, value)

    def expand_macros(self) -> List[ASTNode]:
        """Expand macro invocations into concrete AST nodes"""
        expanded_nodes = []

        # Build macro definition map
        macro_defs = {macro.name: macro for macro in self.program.macros}

        def expand_node_list(nodes: List[ASTNode]) -> List[ASTNode]:
            result = []
            for node in nodes:
                if isinstance(node, MacroInvocation):
                    if node.name in macro_defs:
                        macro_def = macro_defs[node.name]
                        # Create new context for macro expansion
                        macro_context = InterpreterContext({}, self.context)

                        # Bind arguments to parameters
                        for param, arg in zip(macro_def.parameters, node.arguments):
                            arg_value = self.evaluate_expression(arg)
                            macro_context.set(param, arg_value)

                        # Temporarily switch context
                        old_context = self.context
                        self.context = macro_context

                        # Expand macro body
                        expanded_body = expand_node_list(macro_def.body)
                        result.extend(expanded_body)

                        # Restore context
                        self.context = old_context
                    else:
                        self.add_error(f"Undefined macro: {node.name}", node)
                elif isinstance(node, ForLoop):
                    # Expand for loops
                    iterable = self.evaluate_expression(node.iterable)
                    if isinstance(iterable, list):
                        for value in iterable:
                            loop_context = InterpreterContext({}, self.context)
                            loop_context.set(node.variable, value)

                            old_context = self.context
                            self.context = loop_context

                            expanded_body = expand_node_list(node.body)
                            result.extend(expanded_body)

                            self.context = old_context
                    else:
                        self.add_error(f"For loop iterable must be a list", node)
                else:
                    result.append(node)
            return result

        # Expand components
        all_components = []
        all_components.extend(self.program.components)
        for macro_inv in [n for n in self.program.components if isinstance(n, MacroInvocation)]:
            all_components.remove(macro_inv)

        expanded_components = expand_node_list(all_components)
        return expanded_components

    def build_connectivity(self, components: List[ComponentDeclaration]):
        """Build node connectivity map with enhanced terminal handling"""
        # Process connections
        for conn in self.program.connections:
            node_id = None
            node_name = conn.net_name

            # Check if any endpoint is ground
            is_ground_connection = any(
                (isinstance(ep, str) and ep.lower() in ['ground', 'gnd', '0'])
                or (isinstance(ep, Node) and ep.is_ground)
                for ep in conn.endpoints
            )

            if is_ground_connection:
                target_node = self.nodes['ground']
            else:
                # Find or create node
                if node_name and node_name in self.nodes:
                    target_node = self.nodes[node_name]
                else:
                    # Look for existing node from string endpoints
                    string_endpoints = [
                        ep
                        for ep in conn.endpoints
                        if isinstance(ep, str) and ep not in ['ground', 'gnd', '0']
                    ]
                    existing_node = None
                    for ep_name in string_endpoints:
                        if ep_name in self.nodes:
                            existing_node = self.nodes[ep_name]
                            break

                    if existing_node:
                        target_node = existing_node
                    else:
                        # Create new node
                        target_node = NetlistNode(self.node_counter, node_name)
                        self.node_counter += 1
                        if node_name:
                            self.nodes[node_name] = target_node

            # Connect all endpoints to this node
            for endpoint in conn.endpoints:
                if isinstance(endpoint, Terminal):
                    # Component terminal
                    if endpoint.component_name not in self.terminal_connections:
                        self.terminal_connections[endpoint.component_name] = {}
                    self.terminal_connections[endpoint.component_name][
                        endpoint.terminal_name
                    ] = target_node
                elif isinstance(endpoint, str) and endpoint not in ['ground', 'gnd', '0']:
                    # Named node
                    self.nodes[endpoint] = target_node

    def format_component(self, comp: ComponentDeclaration) -> Optional[str]:
        """Format component with parameter evaluation"""
        # Evaluate parameters
        param_values = []
        # Handle positional parameters
        for param in comp.positional_params:
            value = self.evaluate_expression(param)
            param_values.append(str(value))
        
        # Handle named parameters (convert to positional for SPICE)
        named_param_str = ""
        for name, expr in comp.named_params.items():
            value = self.evaluate_expression(expr)
            named_param_str += f" {name}={value}"
        
        # Get terminal connections
        terminals = self.terminal_connections.get(comp.instance_name, {})
        
        # Component-specific formatting
        comp_type = comp.type_name.lower()
        
        if comp_type in ['r', 'resistor']:
            n1 = terminals.get('1', terminals.get('positive', self.nodes['ground']))
            n2 = terminals.get('2', terminals.get('negative', self.nodes['ground']))
            value = param_values[0] if param_values else "1k"
            return f"{comp.instance_name} {n1} {n2} {value}{named_param_str}"
        
        elif comp_type in ['c', 'capacitor']:
            n1 = terminals.get('1', terminals.get('positive', self.nodes['ground']))
            n2 = terminals.get('2', terminals.get('negative', self.nodes['ground']))
            value = param_values[0] if param_values else "1u"
            return f"{comp.instance_name} {n1} {n2} {value}{named_param_str}"
        
        elif comp_type in ['l', 'inductor']:
            n1 = terminals.get('1', terminals.get('positive', self.nodes['ground']))
            n2 = terminals.get('2', terminals.get('negative', self.nodes['ground']))
            value = param_values[0] if param_values else "1m"
            return f"{comp.instance_name} {n1} {n2} {value}{named_param_str}"
        
        elif comp_type in ['v', 'vsource', 'voltage_source']:
            n_pos = terminals.get('1', terminals.get('positive', self.nodes['ground']))
            n_neg = terminals.get('2', terminals.get('negative', self.nodes['ground']))
            
            # Handle different voltage source types
            if len(param_values) == 1:
                # DC voltage source
                dc_value = param_values[0]
                return f"{comp.instance_name} {n_pos} {n_neg} DC {dc_value}{named_param_str}"
            elif len(param_values) >= 2:
                # AC voltage source with DC and AC components
                dc_value = param_values[0]
                ac_value = param_values[1]
                return f"{comp.instance_name} {n_pos} {n_neg} DC {dc_value} AC {ac_value}{named_param_str}"
            else:
                # Default DC voltage
                return f"{comp.instance_name} {n_pos} {n_neg} DC 1{named_param_str}"
        
        elif comp_type in ['i', 'isource', 'current_source']:
            n_pos = terminals.get('1', terminals.get('positive', self.nodes['ground']))
            n_neg = terminals.get('2', terminals.get('negative', self.nodes['ground']))
            
            if len(param_values) == 1:
                # DC current source
                dc_value = param_values[0]
                return f"{comp.instance_name} {n_pos} {n_neg} DC {dc_value}{named_param_str}"
            elif len(param_values) >= 2:
                # AC current source with DC and AC components
                dc_value = param_values[0]
                ac_value = param_values[1]
                return f"{comp.instance_name} {n_pos} {n_neg} DC {dc_value} AC {ac_value}{named_param_str}"
            else:
                # Default DC current
                return f"{comp.instance_name} {n_pos} {n_neg} DC 1m{named_param_str}"
        
        elif comp_type in ['d', 'diode']:
            n_anode = terminals.get('1', terminals.get('anode', self.nodes['ground']))
            n_cathode = terminals.get('2', terminals.get('cathode', self.nodes['ground']))
            model = param_values[0] if param_values else "DIODE_DEFAULT"
            return f"{comp.instance_name} {n_anode} {n_cathode} {model}{named_param_str}"
        
        elif comp_type in ['q', 'bjt', 'transistor']:
            # BJT: collector, base, emitter (+ optional substrate)
            n_c = terminals.get('1', terminals.get('collector', self.nodes['ground']))
            n_b = terminals.get('2', terminals.get('base', self.nodes['ground']))
            n_e = terminals.get('3', terminals.get('emitter', self.nodes['ground']))
            n_s = terminals.get('4', terminals.get('substrate', self.nodes['ground']))
            
            model = param_values[0] if param_values else "BJT_DEFAULT"
            if n_s != self.nodes['ground']:
                return f"{comp.instance_name} {n_c} {n_b} {n_e} {n_s} {model}{named_param_str}"
            else:
                return f"{comp.instance_name} {n_c} {n_b} {n_e} {model}{named_param_str}"
        
        elif comp_type in ['m', 'mosfet']:
            # MOSFET: drain, gate, source, bulk/substrate
            n_d = terminals.get('1', terminals.get('drain', self.nodes['ground']))
            n_g = terminals.get('2', terminals.get('gate', self.nodes['ground']))
            n_s = terminals.get('3', terminals.get('source', self.nodes['ground']))
            n_b = terminals.get('4', terminals.get('bulk', terminals.get('substrate', n_s)))
            
            model = param_values[0] if param_values else "MOSFET_DEFAULT"
            return f"{comp.instance_name} {n_d} {n_g} {n_s} {n_b} {model}{named_param_str}"
        
        elif comp_type in ['opamp', 'op_amp']:
            # Op-amp: non-inverting, inverting, output (+ optional power supplies)
            n_plus = terminals.get('1', terminals.get('non_inverting', terminals.get('+', self.nodes['ground'])))
            n_minus = terminals.get('2', terminals.get('inverting', terminals.get('-', self.nodes['ground'])))
            n_out = terminals.get('3', terminals.get('output', self.nodes['ground']))
            
            model = param_values[0] if param_values else "OPAMP_DEFAULT"
            
            # Check for power supply terminals
            n_vdd = terminals.get('vdd', terminals.get('vcc', terminals.get('vpos', None)))
            n_vss = terminals.get('vss', terminals.get('vee', terminals.get('vneg', None)))
            
            if n_vdd and n_vss:
                return f"{comp.instance_name} {n_plus} {n_minus} {n_vdd} {n_vss} {n_out} {model}{named_param_str}"
            else:
                return f"{comp.instance_name} {n_plus} {n_minus} {n_out} {model}{named_param_str}"
        
        elif comp_type in ['x', 'subcircuit', 'subckt']:
            # Subcircuit instance - get all terminal connections in order
            terminal_list = []
            for i, terminal in enumerate(comp.terminals or []):
                node = terminals.get(str(i+1), terminals.get(terminal.name, self.nodes['ground']))
                terminal_list.append(str(node))
            
            subckt_name = param_values[0] if param_values else comp.type_name
            terminals_str = " ".join(terminal_list)
            return f"{comp.instance_name} {terminals_str} {subckt_name}{named_param_str}"
        
        else:
            # Generic component - try to handle based on number of terminals
            terminal_list = []
            for i in range(len(terminals)):
                node = terminals.get(str(i+1), self.nodes['ground'])
                terminal_list.append(str(node))
            
            if not terminal_list:
                # Default to 2-terminal if no terminals specified
                terminal_list = [str(self.nodes['ground']), str(self.nodes['ground'])]
            
            terminals_str = " ".join(terminal_list)
            params_str = " ".join(param_values) if param_values else ""
            
            return f"{comp.instance_name} {terminals_str} {params_str}{named_param_str}"

    def generate_netlist(self) -> List[str]:
        """Generate SPICE netlist with comprehensive error checking"""
        lines = []
        
        # Process variables first
        self.process_variables()
        
        # Expand macros
        expanded_nodes = self.expand_macros()
        
        # Build connectivity
        self.build_connectivity(self.program.components)
        
        # Format components
        for comp in self.program.components:
            try:
                line = self.format_component(comp)
                if line:
                    lines.append(line)
            except Exception as e:
                self.add_error(f"Error formatting component {comp.instance_name}: {e}", comp)
        
        # Add subcircuit instances
        for subckt in self.program.subcircuit_instances:
            try:
                line = self.format_component(subckt)
                if line:
                    lines.append(line)
            except Exception as e:
                self.add_error(f"Error formatting subcircuit {subckt.instance_name}: {e}", subckt)
        
        return lines
