from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional, Any, Set
from abc import ABC, abstractmethod
from enum import Enum

# Base classes for better type safety and extensibility
class ASTNode(ABC):
    """Base class for all AST nodes with common functionality"""
    def __init__(self):
        self.source_location: Optional['SourceLocation'] = None
        self.annotations: Dict[str, Any] = {}
    
    def add_annotation(self, key: str, value: Any):
        """Add metadata/annotations for tooling support"""
        self.annotations[key] = value
    
    def set_source_location(self, filename: str, line: int, column: int, length: int = 1):
        """Helper to set source location - should be called by parser"""
        self.source_location = SourceLocation(filename, line, column, length)

@dataclass
class SourceLocation:
    """Track source position for better error reporting"""
    filename: str
    line: int
    column: int
    length: int = 1

# Expression system with proper hierarchy
class ExpressionNode(ASTNode):
    """Base for all expressions"""
    pass

@dataclass
class Literal(ExpressionNode):
    value: Union[int, float, str, bool]
    unit: Optional[str] = None  # For unit checking: "10uF", "1kΩ"
    
    def __post_init__(self):
        super().__init__()

@dataclass
class Identifier(ExpressionNode):
    name: str
    
    def __post_init__(self):
        super().__init__()

@dataclass 
class BinaryOp(ExpressionNode):
    left: ExpressionNode
    op: str  # +, -, *, /, **, ||, &&, etc.
    right: ExpressionNode
    
    def __post_init__(self):
        super().__init__()

@dataclass
class UnaryOp(ExpressionNode):
    op: str  # -, !, sqrt, sin, etc.
    operand: ExpressionNode
    
    def __post_init__(self):
        super().__init__()

@dataclass
class FunctionCall(ExpressionNode):
    name: str
    args: List[ExpressionNode]
    
    def __post_init__(self):
        super().__init__()

@dataclass
class ArrayLiteral(ExpressionNode):
    """For parameter arrays: [1, 2, 3] or frequency sweeps"""
    elements: List[ExpressionNode]
    
    def __post_init__(self):
        super().__init__()

# Enhanced component system
@dataclass
class Parameter:
    """Structured parameter with validation metadata"""
    name: str
    value: ExpressionNode
    is_required: bool = True
    default_value: Optional[ExpressionNode] = None
    unit_constraint: Optional[str] = None  # "voltage", "current", "frequency"

@dataclass
class ComponentDeclaration(ASTNode):
    """Declaration of primitive components (R, C, L, transistors, etc.)"""
    type_name: str  # Consistent field name for visualizer
    instance_name: str  # Consistent field name for visualizer
    # Support both positional and named parameters
    positional_params: List[ExpressionNode] = field(default_factory=list)
    named_params: Dict[str, ExpressionNode] = field(default_factory=dict)
    # Terminal definitions for multi-terminal components
    terminals: Optional[List[str]] = None
    # Component-specific attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()
    
    # Backward compatibility properties for existing code
    @property
    def name(self) -> str:
        """Backward compatibility - use instance_name instead"""
        return self.instance_name
    
    @property
    def type(self) -> str:
        """Backward compatibility - use type_name instead"""
        return self.type_name
    
    # Helper methods for visualization
    def get_primary_value(self) -> Optional[Union[int, float]]:
        """Extract primary numeric value for visualization"""
        if self.positional_params:
            first_param = self.positional_params[0]
            if isinstance(first_param, Literal) and isinstance(first_param.value, (int, float)):
                return first_param.value
        return None
    
    def get_primary_unit(self) -> Optional[str]:
        """Extract primary unit for visualization"""
        if self.positional_params:
            first_param = self.positional_params[0]
            if isinstance(first_param, Literal):
                return first_param.unit
        return None

@dataclass
class SubcircuitInstance(ASTNode):
    """Instance of a user-defined subcircuit - separate from ComponentDeclaration"""
    subcircuit_name: str  # Name of the subcircuit definition
    instance_name: str    # Name of this instance
    # Port connections (subcircuit_port -> circuit_node mapping)
    port_connections: Dict[str, Union[str, 'Terminal', 'Node']] = field(default_factory=dict)
    # Parameter overrides
    parameter_overrides: Dict[str, ExpressionNode] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()
    
    # Consistent naming for visualizer compatibility
    @property
    def type_name(self) -> str:
        """Type name for consistency with ComponentDeclaration"""
        return self.subcircuit_name

# Connection system with better terminal handling - IMPROVED FOR VISUALIZATION
@dataclass
class Terminal:
    """Represents a connection point - structured for proper parsing"""
    component_name: str
    terminal_name: str
    
    def __str__(self):
        return f"{self.component_name}.{self.terminal_name}"
    
    def __eq__(self, other):
        if isinstance(other, Terminal):
            return self.component_name == other.component_name and self.terminal_name == other.terminal_name
        return False
    
    def __hash__(self):
        return hash((self.component_name, self.terminal_name))

@dataclass 
class Node:
    """Represents a circuit node/net - structured for proper parsing"""
    name: str
    is_ground: bool = False
    
    def __str__(self):
        return "GND" if self.is_ground else self.name
    
    def __eq__(self, other):
        if isinstance(other, Node):
            return self.name == other.name and self.is_ground == other.is_ground
        return False
    
    def __hash__(self):
        return hash((self.name, self.is_ground))

@dataclass
class Connection(ASTNode):
    """Enhanced connection with validation support - IMPROVED FOR VISUALIZATION"""
    endpoints: List[Union[Terminal, Node, str]]  # Structured endpoints, not just strings
    net_name: Optional[str] = None  # Optional explicit net naming
    attributes: Dict[str, Any] = field(default_factory=dict)  # For routing hints, etc.
    
    def __post_init__(self):
        super().__init__()
    
    def get_structured_endpoints(self) -> List[Union[Terminal, Node]]:
        """Convert string endpoints to structured objects for visualization"""
        result = []
        for ep in self.endpoints:
            if isinstance(ep, (Terminal, Node)):
                result.append(ep)
            elif isinstance(ep, str):
                # Parse string endpoints into structured objects
                if ep.lower() in ('ground', 'gnd', '0'):
                    result.append(Node('ground', is_ground=True))
                elif '.' in ep:
                    # Component terminal: "R1.1" -> Terminal("R1", "1")
                    parts = ep.split('.', 1)
                    if len(parts) == 2:
                        result.append(Terminal(parts[0], parts[1]))
                    else:
                        result.append(Node(ep))
                else:
                    # Regular node name
                    result.append(Node(ep))
            else:
                # Handle other types by converting to string
                result.append(Node(str(ep)))
        return result

# Macro and control flow support
@dataclass
class MacroDefinition(ASTNode):
    name: str
    parameters: List[str]
    body: List[ASTNode]  # Can contain any statements
    
    def __post_init__(self):
        super().__init__()

@dataclass
class MacroInvocation(ASTNode):
    name: str
    arguments: List[ExpressionNode]
    
    def __post_init__(self):
        super().__init__()

@dataclass
class ForLoop(ASTNode):
    """For generating repeated structures"""
    variable: str
    iterable: ExpressionNode  # range(), array, etc.
    body: List[ASTNode]
    
    def __post_init__(self):
        super().__init__()

@dataclass
class ConditionalBlock(ASTNode):
    """If/else for conditional circuit generation"""
    condition: ExpressionNode
    then_block: List[ASTNode]
    else_block: Optional[List[ASTNode]] = None
    
    def __post_init__(self):
        super().__init__()

# Specific simulation command classes instead of generic SimulationCommand
class SimulationNode(ASTNode):
    """Base class for all simulation commands"""
    pass

@dataclass
class DCAnalysis(SimulationNode):
    """DC operating point and sweep analysis"""
    # For DC sweep: sweep_var, start, stop, step
    sweep_variable: Optional[str] = None
    start_value: Optional[ExpressionNode] = None
    stop_value: Optional[ExpressionNode] = None
    step_value: Optional[ExpressionNode] = None
    # Analysis options
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()

@dataclass
class ACAnalysis(SimulationNode):
    """AC small-signal analysis"""
    analysis_type: str  # "lin", "dec", "oct"
    start_frequency: ExpressionNode
    stop_frequency: ExpressionNode
    points_per_decade: Optional[int] = None  # for dec/oct
    total_points: Optional[int] = None       # for lin
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()

@dataclass
class TransientAnalysis(SimulationNode):
    """Time-domain transient analysis"""
    step_time: ExpressionNode
    stop_time: ExpressionNode
    start_time: Optional[ExpressionNode] = None  # Default 0
    max_step: Optional[ExpressionNode] = None
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()

@dataclass
class NoiseAnalysis(SimulationNode):
    """Noise analysis"""
    output_node: str
    input_source: str
    analysis_type: str  # "lin", "dec", "oct"
    start_frequency: ExpressionNode
    stop_frequency: ExpressionNode
    reference_node: Optional[str] = None
    points_per_decade: Optional[int] = None
    total_points: Optional[int] = None
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()

@dataclass
class MonteCarloAnalysis(SimulationNode):
    """Monte Carlo statistical analysis"""
    base_analysis: SimulationNode  # Nested analysis to run multiple times
    iterations: int
    variation_model: str  # "gaussian", "uniform", etc.
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()

@dataclass
class ParametricAnalysis(SimulationNode):
    """Parametric sweep analysis"""
    base_analysis: SimulationNode  # Analysis to repeat with different parameters
    parameter_name: str
    start_value: ExpressionNode
    stop_value: ExpressionNode
    step_value: Optional[ExpressionNode] = None
    points: Optional[int] = None  # Alternative to step_value
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()

@dataclass
class PlotCommand(ASTNode):
    """Separate plot commands from simulation"""
    variables: List[str]
    plot_type: str = "linear"  # linear, log, smith, etc.
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__()

@dataclass
class AnalysisBlock(ASTNode):
    """Group related simulation and plot commands"""
    name: str
    simulations: List[SimulationNode]  # Now uses specific simulation types
    plots: List[PlotCommand]
    
    def __post_init__(self):
        super().__init__()

# Enhanced subcircuit support
@dataclass
class Port(ASTNode):
    """Subcircuit interface definition"""
    name: str
    direction: str  # "input", "output", "inout"
    signal_type: str = "analog"  # analog, digital, mixed
    
    def __post_init__(self):
        super().__init__()

@dataclass
class Subcircuit(ASTNode):
    """Subcircuit definition (template)"""
    name: str
    ports: List[Port]  # Explicit interface
    parameters: List[Parameter] = field(default_factory=list)  # Subcircuit parameters
    components: List[ComponentDeclaration] = field(default_factory=list)
    subcircuit_instances: List[SubcircuitInstance] = field(default_factory=list)  # Instances of other subcircuits
    connections: List[Connection] = field(default_factory=list)
    inner_subcircuits: List['Subcircuit'] = field(default_factory=list)  # Nested subcircuit definitions
    
    def __post_init__(self):
        super().__init__()
    
    def get_port_names(self) -> List[str]:
        """Extract port names for visualization"""
        return [port.name for port in self.ports]
    
    def get_all_node_names(self) -> set[str]:
        """Extract all node names used in this subcircuit for pin inference"""
        nodes = set()
        for conn in self.connections:
            for endpoint in conn.get_structured_endpoints():
                if isinstance(endpoint, Node):
                    nodes.add(endpoint.name)
        return nodes

# Top-level program structure
@dataclass
class ImportStatement(ASTNode):
    """Import external libraries/models"""
    module_name: str
    items: Optional[List[str]] = None  # Specific items to import
    alias: Optional[str] = None
    
    def __post_init__(self):
        super().__init__()

@dataclass
class VariableDeclaration(ASTNode):
    """Global variable/parameter declarations"""
    name: str
    value: ExpressionNode
    is_constant: bool = False
    unit: Optional[str] = None
    
    def __post_init__(self):
        super().__init__()

@dataclass
class Program(ASTNode):
    """Root AST node with better organization - IMPROVED FOR VISUALIZATION"""
    imports: List[ImportStatement] = field(default_factory=list)
    variables: List[VariableDeclaration] = field(default_factory=list)
    macros: List[MacroDefinition] = field(default_factory=list)
    subcircuits: List[Subcircuit] = field(default_factory=list)
    components: List[ComponentDeclaration] = field(default_factory=list)  # Regular components
    subcircuit_instances: List[SubcircuitInstance] = field(default_factory=list)  # SEPARATE from components
    connections: List[Connection] = field(default_factory=list)
    analyses: List[AnalysisBlock] = field(default_factory=list)
    
    def __post_init__(self):
        super().__init__()
    
    def get_subcircuit_by_name(self, name: str) -> Optional[Subcircuit]:
        """Helper method for visualization to find subcircuit definitions"""
        for subckt in self.subcircuits:
            if subckt.name == name:
                return subckt
        return None

# Visitor pattern for AST traversal
class ASTVisitor(ABC):
    """Base visitor for AST processing passes"""
    
    def visit(self, node: ASTNode) -> Any:
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: ASTNode) -> Any:
        """Default visitor - override for specific node types"""
        pass

# Example specialized visitors
class ValidationVisitor(ASTVisitor):
    """Validate AST for common errors"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.component_types = {
            'VOLTAGE_SOURCE': ['value', 'frequency', 'amplitude', 'phase'],
            'CURRENT_SOURCE': ['value', 'frequency', 'amplitude', 'phase'],
            'RESISTOR': ['resistance'],
            'CAPACITOR': ['capacitance'],
            'INDUCTOR': ['inductance'],
            'AC_SOURCE': ['frequency', 'amplitude', 'phase'],
            'DC_SOURCE': ['value'],
            'DIODE': ['model'],
            'TRANSISTOR': ['model'],
            'OPAMP': ['model']
        }
        self.unit_types = {
            'value': ['V', 'A'],
            'resistance': ['ohm', 'kohm', 'Mohm'],
            'capacitance': ['F', 'nF', 'uF', 'pF'],
            'inductance': ['H', 'mH', 'uH', 'nH'],
            'frequency': ['Hz', 'kHz', 'MHz', 'GHz'],
            'time': ['s', 'ms', 'us', 'ns']
        }
    
    def visit_ComponentDeclaration(self, node: ComponentDeclaration):
        """Validate component declaration"""
        if node.type not in self.component_types:
            self.errors.append(f"Unknown component type: {node.type}")
            return

        # Check required parameters
        required_params = self.component_types[node.type]
        for param in required_params:
            if param not in node.parameters:
                self.errors.append(f"Missing required parameter '{param}' for {node.type} {node.name}")

        # Check parameter values and units
        for param_name, value in node.parameters.items():
            if param_name not in required_params:
                self.warnings.append(f"Unknown parameter '{param_name}' for {node.type} {node.name}")
                continue

            # Check if value has a unit
            if isinstance(value, str) and any(unit in value for unit in self.unit_types.get(param_name, [])):
                continue
            elif isinstance(value, (int, float)):
                self.warnings.append(f"Parameter '{param_name}' for {node.type} {node.name} should have a unit")
    
    def visit_SubcircuitInstance(self, node: SubcircuitInstance):
        # Validate subcircuit exists, port connections are valid, etc.
        if not node.subcircuit_name:
            self.errors.append(f"Subcircuit instance must specify subcircuit name")
    
    def visit_Connection(self, node: Connection):
        # Validate endpoint connectivity, terminal existence, etc.
        if len(node.endpoints) < 2:
            self.errors.append("Connection must have at least 2 endpoints")
    
    def _add_error(self, node: ASTNode, message: str):
        if node.source_location:
            error_msg = f"{node.source_location.filename}:{node.source_location.line}:{node.source_location.column}: {message}"
        else:
            error_msg = f"Error: {message}"
        self.errors.append(error_msg)

class VisualizationVisitor(ASTVisitor):
    """Specialized visitor for visualization data extraction"""
    
    def __init__(self):
        self.components = []
        self.subcircuit_instances = []
        self.connections = []
        self.subcircuit_defs = {}
    
    def visit_Program(self, program: Program):
        # Collect subcircuit definitions first
        for subckt in program.subcircuits:
            self.subcircuit_defs[subckt.name] = subckt
        
        # Process components and instances
        for comp in program.components:
            self.visit(comp)
        
        for inst in program.subcircuit_instances:
            self.visit(inst)
            
        for conn in program.connections:
            self.visit(conn)
    
    def visit_ComponentDeclaration(self, node: ComponentDeclaration):
        comp_data = {
            'id': node.instance_name,
            'type': node.type_name,
            'value': node.get_primary_value() or 0,
            'unit': node.get_primary_unit() or '',
            'position': {'x': 0, 'y': 0}
        }
        self.components.append(comp_data)
    
    def visit_SubcircuitInstance(self, node: SubcircuitInstance):
        # Get pin information from subcircuit definition
        subckt_def = self.subcircuit_defs.get(node.subcircuit_name)
        pins = subckt_def.get_port_names() if subckt_def else []
        
        inst_data = {
            'id': node.instance_name,
            'type': node.subcircuit_name,
            'pins': pins,
            'position': {'x': 0, 'y': 0}
        }
        self.subcircuit_instances.append(inst_data)
    
    def visit_Connection(self, node: Connection):
        structured_endpoints = node.get_structured_endpoints()
        if len(structured_endpoints) >= 2:
            ep1, ep2 = structured_endpoints[0], structured_endpoints[1]
            
            def convert_endpoint(ep):
                if isinstance(ep, Terminal):
                    return {
                        'component': ep.component_name,
                        'terminal': ep.terminal_name,
                        'type': 'terminal'
                    }
                else:  # Node
                    return {
                        'node': ep.name,
                        'is_ground': ep.is_ground,
                        'type': 'node'
                    }
            
            conn_data = {
                'from': convert_endpoint(ep1),
                'to': convert_endpoint(ep2)
            }
            self.connections.append(conn_data)

class UnitCheckingVisitor(ASTVisitor):
    """Check unit compatibility in expressions"""
    
    def visit_BinaryOp(self, node: BinaryOp):
        # Validate unit compatibility for operations
        # This would need a proper unit inference system
        pass

# Error handling
@dataclass
class ParseError(Exception):
    message: str
    location: Optional[SourceLocation] = None
    
    def __str__(self):
        if self.location:
            return f"{self.location.filename}:{self.location.line}:{self.location.column}: {self.message}"
        return self.message

# Helper function for parsers to create nodes with source location
def create_node_with_location(node_class, filename: str, line: int, column: int, length: int = 1, **kwargs):
    """Factory function to create AST nodes with source location set"""
    node = node_class(**kwargs)
    node.set_source_location(filename, line, column, length)
    return node

# Legacy compatibility classes for existing code
@dataclass
class ComponentTerminal:
    """Deprecated: use Terminal instead - kept for backward compatibility"""
    component: str
    terminal: str
    
    def __post_init__(self):
        import warnings
        warnings.warn("ComponentTerminal is deprecated, use Terminal instead", DeprecationWarning)