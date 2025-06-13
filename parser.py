from typing import List, Dict, Union, Optional, Any
from lexer import Token, TokenType,UnitParser
from ast_nodes import (
    # Base classes
    ASTNode, ExpressionNode,
    
    # Expression nodes
    Literal, Identifier, BinaryOp, UnaryOp, FunctionCall, ArrayLiteral,
    
    # Component and connection nodes
    ComponentDeclaration, SubcircuitInstance, Terminal, Node, Connection,
    
    # Simulation nodes
    SimulationNode, DCAnalysis, ACAnalysis, TransientAnalysis,
    NoiseAnalysis, MonteCarloAnalysis, ParametricAnalysis,
    PlotCommand, AnalysisBlock,
    
    # Structure nodes
    Port, Subcircuit, VariableDeclaration, ImportStatement,
    MacroDefinition, MacroInvocation, Program,
    
    # Helper functions
    create_node_with_location, SourceLocation
)

class ParserError(Exception):
    """Parser-specific exception with location info"""
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Line {token.line}, Column {token.column}: {message}")

class Parser:
    def __init__(self, tokens: List[Token], filename: str = "<input>"):
        self.tokens = tokens
        self.filename = filename
        self.index = -1
        self.current: Token = None
        self.advance()

    def advance(self):
        self.index += 1
        if self.index < len(self.tokens):
            self.current = self.tokens[self.index]
        else:
            self.current = Token(TokenType.EOF, '', -1, -1)

    def peek(self, offset: int = 1) -> Token:
        """Look ahead at tokens without consuming them"""
        peek_index = self.index + offset
        if peek_index < len(self.tokens):
            return self.tokens[peek_index]
        return Token(TokenType.EOF, '', -1, -1)

    def consume(self, token_type: TokenType, message: str = None) -> Token:
        """Consume a token of the expected type"""
        if self.current.type == token_type:
            token = self.current
            self.advance()
            return token
        
        if message is None:
            message = f"Expected {token_type.name}, got {self.current.type.name}"
        raise ParserError(message, self.current)

    def create_node(self, node_class, **kwargs):
        """Helper to create AST nodes with source location"""
        return create_node_with_location(
            node_class, 
            self.filename, 
            self.current.line, 
            self.current.column,
            1,
            **kwargs
        )

    def parse(self) -> Program:
        imports: List[ImportStatement] = []
        variables: List[VariableDeclaration] = []
        components: List[ComponentDeclaration] = []
        subcircuit_instances: List[SubcircuitInstance] = []
        subcircuits: List[Subcircuit] = []
        connections: List[Connection] = []
        analyses: List[AnalysisBlock] = []

        # Define known component types
        COMPONENT_TYPES = {
            'Resistor', 'Capacitor', 'Inductor',
            'VoltageSource', 'CurrentSource', 'ACSource', 'DCSource',
            'Ammeter', 'Voltmeter', 'Ohmmeter',
            'Diode', 'BJT', 'MOSFET', 'OpAmp',
            'Ground', 'Node'
        }

        while self.current.type != TokenType.EOF:
            if self.current.type == TokenType.KEYWORD and self.current.value == "import":
                imports.append(self.parse_import())
            
            elif self.current.type == TokenType.KEYWORD and self.current.value == "param":
                variables.append(self.parse_variable_declaration())

            elif self.current.type == TokenType.COMPONENT:
                components.append(self.parse_component())

            elif self.current.type == TokenType.CONNECT:
                connections.append(self.parse_connection())

            elif self.current.type == TokenType.SIMULATE:
                analyses.append(self.parse_analysis_block())

            elif self.current.type == TokenType.SUBCIRCUIT:
                subcircuits.append(self.parse_subcircuit())

            elif self.current.type == TokenType.IDENTIFIER:
                # Look ahead to determine if this is a component or subcircuit
                if self.peek().type == TokenType.IDENTIFIER:
                    # Check if the first identifier is a known component type
                    if self.current.value in COMPONENT_TYPES:
                        components.append(self.parse_component())
                    else:
                        # Assume it's a subcircuit instance
                        subcircuit_instances.append(self.parse_subcircuit_instance())
                elif self.peek().type == TokenType.OPERATOR and self.peek().value == "=":
                    # Pattern: varName = value - variable assignment
                    variables.append(self.parse_variable_assignment())
                else:
                    raise ParserError(f"Unexpected identifier pattern: {self.current.value}", self.current)

            else:
                raise ParserError(f"Unexpected token '{self.current.value}'", self.current)

        return self.create_node(
            Program,
            imports=imports,
            variables=variables,
            components=components,
            subcircuit_instances=subcircuit_instances,
            subcircuits=subcircuits,
            connections=connections,
            analyses=analyses
        )

    def parse_import(self) -> ImportStatement:
        self.consume(TokenType.KEYWORD, "import")
        module_name = self.consume(TokenType.IDENTIFIER).value
        
        items = None
        alias = None
        
        if self.current.type == TokenType.KEYWORD and self.current.value == "from":
            # Handle "from module import item1, item2"
            # Note: This is reverse of typical syntax, adjust as needed
            pass
        elif self.current.type == TokenType.KEYWORD and self.current.value == "as":
            self.consume(TokenType.KEYWORD, "as")
            alias = self.consume(TokenType.IDENTIFIER).value
        
        self.consume(TokenType.SYMBOL, ';')
        return self.create_node(ImportStatement, module_name=module_name, items=items, alias=alias)

    def parse_variable_declaration(self) -> VariableDeclaration:
        self.consume(TokenType.KEYWORD, "param")
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.OPERATOR, "=")
        value = self.parse_expression()
        
        unit = None
        if self.current.type == TokenType.UNIT:
            unit = self.consume(TokenType.UNIT).value
        
        self.consume(TokenType.SYMBOL, ';')
        return self.create_node(VariableDeclaration, name=name, value=value, is_constant=True, unit=unit)

    def parse_variable_assignment(self) -> VariableDeclaration:
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.OPERATOR, "=")
        value = self.parse_expression()
        self.consume(TokenType.SYMBOL, ';')
        return self.create_node(VariableDeclaration, name=name, value=value, is_constant=False)

    def parse_expression(self) -> ExpressionNode:
        """Parse expressions with proper precedence"""
        return self.parse_or_expression()

    def parse_or_expression(self) -> ExpressionNode:
        left = self.parse_and_expression()
        
        while self.current.type == TokenType.OPERATOR and self.current.value in ["||", "|"]:
            op = self.consume(TokenType.OPERATOR).value
            right = self.parse_and_expression()
            left = self.create_node(BinaryOp, left=left, op=op, right=right)
        
        return left

    def parse_and_expression(self) -> ExpressionNode:
        left = self.parse_equality_expression()
        
        while self.current.type == TokenType.OPERATOR and self.current.value in ["&&", "&"]:
            op = self.consume(TokenType.OPERATOR).value
            right = self.parse_equality_expression()
            left = self.create_node(BinaryOp, left=left, op=op, right=right)
        
        return left

    def parse_equality_expression(self) -> ExpressionNode:
        left = self.parse_relational_expression()
        
        while self.current.type == TokenType.OPERATOR and self.current.value in ["==", "!="]:
            op = self.consume(TokenType.OPERATOR).value
            right = self.parse_relational_expression()
            left = self.create_node(BinaryOp, left=left, op=op, right=right)
        
        return left

    def parse_relational_expression(self) -> ExpressionNode:
        left = self.parse_additive_expression()
        
        while self.current.type == TokenType.OPERATOR and self.current.value in ["<", ">", "<=", ">="]:
            op = self.consume(TokenType.OPERATOR).value
            right = self.parse_additive_expression()
            left = self.create_node(BinaryOp, left=left, op=op, right=right)
        
        return left

    def parse_additive_expression(self) -> ExpressionNode:
        left = self.parse_multiplicative_expression()
        
        while self.current.type == TokenType.OPERATOR and self.current.value in ["+", "-"]:
            op = self.consume(TokenType.OPERATOR).value
            right = self.parse_multiplicative_expression()
            left = self.create_node(BinaryOp, left=left, op=op, right=right)
        
        return left

    def parse_multiplicative_expression(self) -> ExpressionNode:
        left = self.parse_power_expression()
        
        while self.current.type == TokenType.OPERATOR and self.current.value in ["*", "/", "%"]:
            op = self.consume(TokenType.OPERATOR).value
            right = self.parse_power_expression()
            left = self.create_node(BinaryOp, left=left, op=op, right=right)
        
        return left

    def parse_power_expression(self) -> ExpressionNode:
        left = self.parse_unary_expression()
        
        if self.current.type == TokenType.OPERATOR and self.current.value == "**":
            op = self.consume(TokenType.OPERATOR).value
            right = self.parse_power_expression()  # Right associative
            left = self.create_node(BinaryOp, left=left, op=op, right=right)
        
        return left

    def parse_unary_expression(self) -> ExpressionNode:
        if self.current.type == TokenType.OPERATOR and self.current.value in ["-", "+", "!"]:
            op = self.consume(TokenType.OPERATOR).value
            operand = self.parse_unary_expression()
            return self.create_node(UnaryOp, op=op, operand=operand)
        
        return self.parse_primary_expression()

    def parse_primary_expression(self) -> ExpressionNode:
        """Parse a primary expression"""
        # Numbers
        if self.current.type == TokenType.NUMBER:
            value = float(self.current.value)
            self.advance()
            
            # Check for unit after number
            if self.current.type == TokenType.UNIT:
                unit = self.current.value
                self.advance()
                return self.create_node(Literal, value=value, unit=unit)
            return self.create_node(Literal, value=value)
        
        # Units
        if self.current.type == TokenType.UNIT:
            value = self.current.value
            self.advance()
            return self.create_node(Literal, value=value)
        
        # Strings
        if self.current.type == TokenType.STRING:
            value = self.current.value
            self.advance()
            return self.create_node(Literal, value=value)
        
        # Identifiers
        if self.current.type == TokenType.IDENTIFIER:
            name = self.current.value
            self.advance()
            return self.create_node(Identifier, name=name)
        
        # Parenthesized expressions
        if self.current.type == TokenType.SYMBOL and self.current.value == '(':
            self.advance()
            expr = self.parse_expression()
            self.consume(TokenType.SYMBOL, ")")
            return expr
        
        # Boolean literals
        if self.current.type == TokenType.BOOLEAN:
            value = self.current.value == 'true'
            self.advance()
            return self.create_node(Literal, value=1.0 if value else 0.0)
        
        # Ground reference
        if self.current.type == TokenType.GROUND:
            value = self.current.value
            self.advance()
            return self.create_node(Identifier, name=value)
        
        raise ParserError(f"Unexpected token in expression: '{self.current.value}'", self.current)

    def parse_component_declaration(self) -> ComponentDeclaration:
        """Parse a component declaration with enhanced parameter handling"""
        # Get component type
        if self.current.type not in [
            TokenType.RESISTOR, TokenType.CAPACITOR, TokenType.INDUCTOR,
            TokenType.VOLTAGE_SOURCE, TokenType.CURRENT_SOURCE, TokenType.AC_SOURCE,
            TokenType.AMMETER
        ]:
            raise ParserError(f"Expected component type, got {self.current.type}", self.current)
        
        type_name = self.current.value
        self.advance()
        
        # Get instance name
        if self.current.type != TokenType.IDENTIFIER:
            raise ParserError(f"Expected component name, got {self.current.type}", self.current)
        instance_name = self.current.value
        self.advance()
        
        # Parse parameters
        positional_params = []
        named_params = {}
        
        if self.current.type == TokenType.SYMBOL and self.current.value == '(':
            self.advance()
            
            # Parse parameters until closing parenthesis
            while self.current.type != TokenType.SYMBOL or self.current.value != ')':
                if self.current.type == TokenType.IDENTIFIER:
                    # Named parameter
                    param_name = self.current.value
                    self.advance()
                    
                    if self.current.type != TokenType.SYMBOL or self.current.value != '=':
                        raise ParserError("Expected '=' after parameter name", self.current)
                    self.advance()
                    
                    param_value = self.parse_expression()
                    named_params[param_name] = param_value
                else:
                    # Positional parameter
                    param_value = self.parse_expression()
                    positional_params.append(param_value)
                
                # Check for comma or closing parenthesis
                if self.current.type == TokenType.SYMBOL:
                    if self.current.value == ')':
                        break
                    elif self.current.value == ',':
                        self.advance()
                    else:
                        raise ParserError("Expected ',' or ')'", self.current)
            
            self.advance()  # Consume closing parenthesis
        
        # Add semicolon
        if self.current.type != TokenType.SYMBOL or self.current.value != ';':
            raise ParserError("Expected ';' after component declaration", self.current)
        self.advance()
        
        # Create component with proper terminals
        terminals = None
        if type_name in ['VoltageSource', 'CurrentSource', 'ACSource']:
            terminals = ['positive', 'negative']
        elif type_name in ['Resistor', 'Capacitor', 'Inductor']:
            terminals = ['positive', 'negative']
        elif type_name == 'Ammeter':
            terminals = ['positive', 'negative']
        
        return self.create_node(
            ComponentDeclaration,
            type_name=type_name,
            instance_name=instance_name,
            positional_params=positional_params,
            named_params=named_params,
            terminals=terminals
        )

    def parse_connection(self) -> Connection:
        self.consume(TokenType.CONNECT)
        self.consume(TokenType.SYMBOL, '(')
        endpoints = []

        while self.current.type != TokenType.SYMBOL or self.current.value != ')':
            if self.current.type == TokenType.GROUND:
                endpoints.append(Node("ground", is_ground=True))
                self.advance()
            
            elif self.current.type == TokenType.IDENTIFIER:
                # Check if this is a terminal reference (component.terminal)
                if self.peek().type == TokenType.SYMBOL and self.peek().value == '.':
                    comp_name = self.consume(TokenType.IDENTIFIER).value
                    self.consume(TokenType.SYMBOL, '.')
                    term_name = self.consume(TokenType.IDENTIFIER).value
                    endpoints.append(Terminal(comp_name, term_name))
                else:
                    # Simple node name
                    node_name = self.consume(TokenType.IDENTIFIER).value
                    endpoints.append(Node(node_name))
            else:
                raise ParserError(f"Unexpected endpoint type: '{self.current.value}'", self.current)

            if self.current.type == TokenType.SYMBOL and self.current.value == ',':
                self.consume(TokenType.SYMBOL, ',')
            elif self.current.type == TokenType.SYMBOL and self.current.value == ')':
                break
            else:
                raise ParserError("Expected ',' or ')' in connection", self.current)

        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        return self.create_node(Connection, endpoints=endpoints)

    def parse_analysis_block(self) -> AnalysisBlock:
        self.consume(TokenType.SIMULATE)
        self.consume(TokenType.SYMBOL, '{')
        
        simulations = []
        plots = []
        while self.current.type != TokenType.SYMBOL or self.current.value != '}':
            if self.current.type == TokenType.KEYWORD:
                analysis_type = self.current.value
                if analysis_type == 'dc':
                    simulations.append(self.parse_dc_analysis())
                elif analysis_type == 'ac':
                    simulations.append(self.parse_ac_analysis())
                elif analysis_type == 'transient':
                    simulations.append(self.parse_transient_analysis())
                elif analysis_type == 'noise':
                    simulations.append(self.parse_noise_analysis())
                elif analysis_type == 'paramSweep':
                    simulations.append(self.parse_parametric_analysis())
                else:
                    raise ParserError(f"Unknown analysis type: {analysis_type}", self.current)
            else:
                raise ParserError("Expected analysis type keyword", self.current)
            
            # Check for semicolon after each analysis
            if self.current.type == TokenType.SYMBOL and self.current.value == ';':
                self.consume(TokenType.SYMBOL, ';')
        
        self.consume(TokenType.SYMBOL, '}')
        self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(AnalysisBlock, name="main", simulations=simulations, plots=plots)

    def parse_dc_analysis(self) -> DCAnalysis:
        self.consume(TokenType.KEYWORD, 'dc')
        return self.create_node(DCAnalysis)

    def parse_ac_analysis(self) -> ACAnalysis:
        self.consume(TokenType.KEYWORD, 'ac')
        self.consume(TokenType.SYMBOL, '(')
        
        # Parse analysis type (dec, oct, or lin)
        analysis_type = "dec"  # Default to decade sweep
        if self.current.type == TokenType.IDENTIFIER:
            analysis_type = self.consume(TokenType.IDENTIFIER).value
            if analysis_type not in ["dec", "oct", "lin"]:
                raise ParserError(f"Invalid AC analysis type: {analysis_type}. Must be 'dec', 'oct', or 'lin'", self.current)
            self.consume(TokenType.SYMBOL, ',')
        
        # Parse number of points
        points = 10  # Default number of points
        if self.current.type == TokenType.NUMBER:
            points = int(self.parse_expression().value)
            self.consume(TokenType.SYMBOL, ',')
        
        # Parse frequency range
        start_frequency = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        stop_frequency = self.parse_expression()
        
        self.consume(TokenType.SYMBOL, ')')
        
        return self.create_node(
            ACAnalysis,
            analysis_type=analysis_type,
            points_per_decade=points if analysis_type in ["dec", "oct"] else None,
            total_points=points if analysis_type == "lin" else None,
            start_frequency=start_frequency,
            stop_frequency=stop_frequency
        )

    def parse_transient_analysis(self) -> TransientAnalysis:
        self.consume(TokenType.KEYWORD, 'transient')
        self.consume(TokenType.SYMBOL, '(')
        
        step_time = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        stop_time = self.parse_expression()
        
        start_time = None
        if self.current.type == TokenType.SYMBOL and self.current.value == ',':
            self.consume(TokenType.SYMBOL, ',')
            start_time = self.parse_expression()
        
        self.consume(TokenType.SYMBOL, ')')
        
        return self.create_node(
            TransientAnalysis,
            step_time=step_time,
            stop_time=stop_time,
            start_time=start_time
        )

    def parse_noise_analysis(self) -> NoiseAnalysis:
        self.consume(TokenType.KEYWORD, 'noise')
        self.consume(TokenType.SYMBOL, '(')
        
        output_node = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, ',')
        input_source = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, ',')
        
        analysis_type = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, ',')
        points = int(self.parse_expression().value)
        self.consume(TokenType.SYMBOL, ',')
        
        start_frequency = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        stop_frequency = self.parse_expression()
        
        self.consume(TokenType.SYMBOL, ')')
        
        return self.create_node(
            NoiseAnalysis,
            output_node=output_node,
            input_source=input_source,
            analysis_type=analysis_type,
            points_per_decade=points if analysis_type in ["dec", "oct"] else None,
            total_points=points if analysis_type == "lin" else None,
            start_frequency=start_frequency,
            stop_frequency=stop_frequency
        )

    def parse_parametric_analysis(self) -> ParametricAnalysis:
        self.consume(TokenType.KEYWORD, 'paramSweep')
        self.consume(TokenType.SYMBOL, '(')
        
        parameter_name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, ',')
        start_value = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        stop_value = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        step_value = self.parse_expression()
        
        self.consume(TokenType.SYMBOL, ')')
        
        # Create a default DC analysis as the base
        base_analysis = self.create_node(DCAnalysis)
        
        return self.create_node(
            ParametricAnalysis,
            base_analysis=base_analysis,
            parameter_name=parameter_name,
            start_value=start_value,
            stop_value=stop_value,
            step_value=step_value
        )

    def parse_plot_command(self) -> PlotCommand:
        self.consume(TokenType.KEYWORD, 'plot')
        self.consume(TokenType.SYMBOL, '(')
        
        variables = []
        while self.current.type != TokenType.SYMBOL or self.current.value != ')':
            variables.append(self.consume(TokenType.IDENTIFIER).value)
            if self.current.type == TokenType.SYMBOL and self.current.value == ',':
                self.consume(TokenType.SYMBOL, ',')
            elif self.current.type == TokenType.SYMBOL and self.current.value == ')':
                break
            else:
                raise ParserError("Expected ',' or ')' in plot command", self.current)
        
        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(PlotCommand, variables=variables)

    def parse_subcircuit(self) -> Subcircuit:
        self.consume(TokenType.SUBCIRCUIT)
        name = self.consume(TokenType.IDENTIFIER).value

        # Parse port list
        ports = []
        if self.current.type == TokenType.SYMBOL and self.current.value == '(':
            self.consume(TokenType.SYMBOL, '(')
            while self.current.type != TokenType.SYMBOL or self.current.value != ')':
                port_name = self.consume(TokenType.IDENTIFIER).value
                # Default to input direction, could be extended
                port = self.create_node(Port, name=port_name, direction="inout")
                ports.append(port)
                
                if self.current.type == TokenType.SYMBOL and self.current.value == ',':
                    self.consume(TokenType.SYMBOL, ',')
                elif self.current.type == TokenType.SYMBOL and self.current.value == ')':
                    break
                
            self.consume(TokenType.SYMBOL, ')')

        self.consume(TokenType.SYMBOL, '{')
        
        components = []
        subcircuit_instances = []
        connections = []
        
        while self.current.type != TokenType.SYMBOL or self.current.value != '}':
            if self.current.type == TokenType.COMPONENT:
                components.append(self.parse_component())
            elif self.current.type == TokenType.CONNECT:
                connections.append(self.parse_connection())
            elif self.current.type == TokenType.IDENTIFIER:
                subcircuit_instances.append(self.parse_subcircuit_instance())
            else:
                raise ParserError(f"Unexpected token in subcircuit: '{self.current.value}'", self.current)
        
        self.consume(TokenType.SYMBOL, '}')
        self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(
            Subcircuit,
            name=name,
            ports=ports,
            components=components,
            subcircuit_instances=subcircuit_instances,
            connections=connections
        )

    def parse_subcircuit_instance(self) -> SubcircuitInstance:
        subcircuit_name = self.consume(TokenType.IDENTIFIER).value
        instance_name = self.consume(TokenType.IDENTIFIER).value

        port_connections = {}
        parameter_overrides = {}

        if self.current.type == TokenType.SYMBOL and self.current.value == '(':
            self.consume(TokenType.SYMBOL, '(')
            
            while self.current.type != TokenType.SYMBOL or self.current.value != ')':
                if (self.current.type == TokenType.IDENTIFIER and 
                    self.peek().type == TokenType.OPERATOR and 
                    self.peek().value == '='):
                    # Named parameter or port connection
                    key = self.consume(TokenType.IDENTIFIER).value
                    self.consume(TokenType.OPERATOR, '=')
                    
                    if self.current.type == TokenType.IDENTIFIER:
                        # Port connection
                        port_connections[key] = self.consume(TokenType.IDENTIFIER).value
                    else:
                        # Parameter override
                        parameter_overrides[key] = self.parse_expression()
                else:
                    # Provide a more helpful error message
                    if self.current.type == TokenType.IDENTIFIER:
                        raise ParserError(
                            f"Subcircuit '{subcircuit_name}' requires named parameters. "
                            f"Instead of '{self.current.value}', use 'paramName={self.current.value}'",
                            self.current
                        )
                    else:
                        raise ParserError(
                            f"Subcircuit '{subcircuit_name}' requires named parameters in the format 'paramName=value'",
                            self.current
                        )

                if self.current.type == TokenType.SYMBOL and self.current.value == ',':
                    self.consume(TokenType.SYMBOL, ',')
                elif self.current.type == TokenType.SYMBOL and self.current.value == ')':
                    break
                else:
                    raise ParserError(
                        f"Expected ',' or ')' in subcircuit '{subcircuit_name}' instance parameters",
                        self.current
                    )

            self.consume(TokenType.SYMBOL, ')')

        self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(
            SubcircuitInstance,
            subcircuit_name=subcircuit_name,
            instance_name=instance_name,
            port_connections=port_connections,
            parameter_overrides=parameter_overrides
        )
