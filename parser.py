from typing import List, Dict, Union, Optional
from lexer import Token, TokenType
from ast_nodes import (
    # Expression nodes
    ExpressionNode,
    Literal,
    Identifier,
    BinaryOp,
    UnaryOp,
    FunctionCall,
    ArrayLiteral,
    
    # Component and connection nodes
    ComponentDeclaration,
    SubcircuitInstance,
    Terminal,
    Node,
    Connection,
    
    # Simulation nodes
    DCAnalysis,
    ACAnalysis,
    TransientAnalysis,
    NoiseAnalysis,
    MonteCarloAnalysis,
    ParametricAnalysis,
    PlotCommand,
    AnalysisBlock,
    
    # Structure nodes
    Port,
    Subcircuit,
    VariableDeclaration,
    ImportStatement,
    Program,
    
    # Helper functions
    create_node_with_location,
    SourceLocation,
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

    def consume(self, ttype: TokenType, value: str = None) -> Token:
        if self.current.type == ttype and (value is None or self.current.value == value):
            tok = self.current
            self.advance()
            return tok
        
        expected = f"{ttype.name}"
        if value:
            expected += f" '{value}'"
        
        raise ParserError(
            f"Expected {expected}, got {self.current.type.name} '{self.current.value}'",
            self.current
        )

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
                # Could be subcircuit instance or variable assignment
                if self.peek().type == TokenType.IDENTIFIER:
                    # Pattern: TypeName instanceName - subcircuit instance
                    subcircuit_instances.append(self.parse_subcircuit_instance())
                elif self.peek().type == TokenType.OPERATOR and self.peek().value == "=":
                    # Pattern: varName = value - variable assignment
                    variables.append(self.parse_variable_assignment())
                else:
                    raise ParserError(f"Unexpected identifier pattern", self.current)

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
        if self.current.type == TokenType.NUMBER:
            value_str = self.consume(TokenType.NUMBER).value
            # Handle different number formats
            if '.' in value_str or 'e' in value_str.lower():
                value = float(value_str)
            else:
                value = int(value_str)
            
            unit = None
            if self.current.type == TokenType.UNIT:
                unit = self.consume(TokenType.UNIT).value
            
            return self.create_node(Literal, value=value, unit=unit)
        
        elif self.current.type == TokenType.STRING:
            value = self.consume(TokenType.STRING).value
            # Remove quotes
            value = value[1:-1]
            return self.create_node(Literal, value=value)
        
        elif self.current.type == TokenType.IDENTIFIER:
            name = self.consume(TokenType.IDENTIFIER).value
            
            # Check for function call
            if self.current.type == TokenType.SYMBOL and self.current.value == "(":
                self.consume(TokenType.SYMBOL, "(")
                args = []
                
                while self.current.type != TokenType.SYMBOL or self.current.value != ")":
                    args.append(self.parse_expression())
                    if self.current.type == TokenType.SYMBOL and self.current.value == ",":
                        self.consume(TokenType.SYMBOL, ",")
                    elif self.current.type == TokenType.SYMBOL and self.current.value == ")":
                        break
                    else:
                        raise ParserError("Expected ',' or ')' in function call", self.current)
                
                self.consume(TokenType.SYMBOL, ")")
                return self.create_node(FunctionCall, name=name, args=args)
            else:
                return self.create_node(Identifier, name=name)
        
        elif self.current.type == TokenType.SYMBOL and self.current.value == "(":
            self.consume(TokenType.SYMBOL, "(")
            expr = self.parse_expression()
            self.consume(TokenType.SYMBOL, ")")
            return expr
        
        elif self.current.type == TokenType.SYMBOL and self.current.value == "[":
            # Array literal
            self.consume(TokenType.SYMBOL, "[")
            elements = []
            
            while self.current.type != TokenType.SYMBOL or self.current.value != "]":
                elements.append(self.parse_expression())
                if self.current.type == TokenType.SYMBOL and self.current.value == ",":
                    self.consume(TokenType.SYMBOL, ",")
                elif self.current.type == TokenType.SYMBOL and self.current.value == "]":
                    break
                else:
                    raise ParserError("Expected ',' or ']' in array literal", self.current)
            
            self.consume(TokenType.SYMBOL, "]")
            return self.create_node(ArrayLiteral, elements=elements)
        
        else:
            raise ParserError(f"Unexpected token in expression: '{self.current.value}'", self.current)

    def parse_component(self) -> ComponentDeclaration:
        ctype = self.consume(TokenType.COMPONENT).value
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, '(')

        positional_params = []
        named_params = {}

        while self.current.type != TokenType.SYMBOL or self.current.value != ')':
            # Check if this is a named parameter
            if (self.current.type == TokenType.IDENTIFIER and 
                self.peek().type == TokenType.OPERATOR and 
                self.peek().value == '='):
                
                # Named parameter
                key = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.OPERATOR, '=')
                value = self.parse_expression()
                named_params[key] = value
            else:
                # Positional parameter
                if named_params:
                    raise ParserError("Positional parameters cannot follow named parameters", self.current)
                value = self.parse_expression()
                positional_params.append(value)

            if self.current.type == TokenType.SYMBOL and self.current.value == ',':
                self.consume(TokenType.SYMBOL, ',')
            elif self.current.type == TokenType.SYMBOL and self.current.value == ')':
                break
            else:
                raise ParserError("Expected ',' or ')' in component parameters", self.current)

        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(
            ComponentDeclaration,
            type_name=ctype,
            instance_name=name,
            positional_params=positional_params,
            named_params=named_params
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
        
        # Optional analysis block name
        name = "default"
        if self.current.type == TokenType.IDENTIFIER:
            name = self.consume(TokenType.IDENTIFIER).value
        
        self.consume(TokenType.SYMBOL, '{')
        simulations = []
        plots = []

        while self.current.type != TokenType.SYMBOL or self.current.value != '}':
            if self.current.type == TokenType.KEYWORD:
                kw = self.current.value
                
                if kw == 'dc':
                    simulations.append(self.parse_dc_analysis())
                elif kw == 'ac':
                    simulations.append(self.parse_ac_analysis())
                elif kw == 'transient':
                    simulations.append(self.parse_transient_analysis())
                elif kw == 'noise':
                    simulations.append(self.parse_noise_analysis())
                elif kw == 'paramSweep':
                    simulations.append(self.parse_parametric_analysis())
                elif kw == 'plot':
                    plots.append(self.parse_plot_command())
                else:
                    raise ParserError(f"Unknown analysis keyword: '{kw}'", self.current)
            else:
                raise ParserError(f"Expected analysis command, got '{self.current.value}'", self.current)

        self.consume(TokenType.SYMBOL, '}')
        if self.current.type == TokenType.SYMBOL and self.current.value == ';':
            self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(AnalysisBlock, name=name, simulations=simulations, plots=plots)

    def parse_dc_analysis(self) -> DCAnalysis:
        self.consume(TokenType.KEYWORD, 'dc')
        
        # Check for sweep parameters
        sweep_variable = None
        start_value = None
        stop_value = None
        step_value = None
        
        if self.current.type == TokenType.SYMBOL and self.current.value == '(':
            self.consume(TokenType.SYMBOL, '(')
            sweep_variable = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.SYMBOL, ',')
            start_value = self.parse_expression()
            self.consume(TokenType.SYMBOL, ',')
            stop_value = self.parse_expression()
            self.consume(TokenType.SYMBOL, ',')
            step_value = self.parse_expression()
            self.consume(TokenType.SYMBOL, ')')
        
        self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(
            DCAnalysis,
            sweep_variable=sweep_variable,
            start_value=start_value,
            stop_value=stop_value,
            step_value=step_value
        )

    def parse_ac_analysis(self) -> ACAnalysis:
        self.consume(TokenType.KEYWORD, 'ac')
        self.consume(TokenType.SYMBOL, '(')
        
        # Default to decade sweep
        analysis_type = "dec"
        if self.current.type == TokenType.IDENTIFIER:
            analysis_type = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.SYMBOL, ',')
        
        # Points specification
        points = int(self.parse_expression().value) if hasattr(self.parse_expression(), 'value') else 10
        self.consume(TokenType.SYMBOL, ',')
        
        start_frequency = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        stop_frequency = self.parse_expression()
        
        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        
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
        self.consume(TokenType.SYMBOL, ';')
        
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
        self.consume(TokenType.SYMBOL, ';')
        
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
        
        # This is a wrapper around another analysis
        # For now, assume it's a simple parameter sweep
        parameter_name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, ',')
        start_value = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        stop_value = self.parse_expression()
        self.consume(TokenType.SYMBOL, ',')
        step_value = self.parse_expression()
        
        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        
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
                    raise ParserError("Subcircuit instances require named parameters", self.current)

                if self.current.type == TokenType.SYMBOL and self.current.value == ',':
                    self.consume(TokenType.SYMBOL, ',')
                elif self.current.type == TokenType.SYMBOL and self.current.value == ')':
                    break
                else:
                    raise ParserError("Expected ',' or ')' in subcircuit instance", self.current)

            self.consume(TokenType.SYMBOL, ')')

        self.consume(TokenType.SYMBOL, ';')
        
        return self.create_node(
            SubcircuitInstance,
            subcircuit_name=subcircuit_name,
            instance_name=instance_name,
            port_connections=port_connections,
            parameter_overrides=parameter_overrides
        )
