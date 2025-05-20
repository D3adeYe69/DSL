from typing import List
from lexer import Token, TokenType
from ast_nodes import ComponentDeclaration, ComponentTerminal, Connection, SimulationCommand, SimulationBlock, Subcircuit, Program

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.index = -1
        self.current: Token = None
        self.advance()

    def advance(self):
        self.index += 1
        if self.index < len(self.tokens):
            self.current = self.tokens[self.index]
        else:
            # EOF sentinel (line/col not really used for EOF)
            self.current = Token(TokenType.EOF, '', -1, -1)

    def consume(self, ttype: TokenType, value: str = None) -> Token:
        if self.current.type == ttype and (value is None or self.current.value == value):
            tok = self.current
            self.advance()
            return tok
        raise SyntaxError(
            f"Expected {ttype.name}{' '+value if value else ''}, got {self.current.value!r} "
            f"at line {self.current.line}, column {self.current.column}"
        )

    def parse(self) -> Program:
        components, connections, simulations, subcircuits = [], [], [], []
        while self.current.type != TokenType.EOF:
            if self.current.type == TokenType.COMPONENT:
                components.append(self.parse_component())
            elif self.current.type == TokenType.CONNECT:
                connections.append(self.parse_connection())
            elif self.current.type == TokenType.SIMULATE:
                simulations.append(self.parse_simulation())
            elif self.current.type == TokenType.SUBCIRCUIT:
                subcircuits.append(self.parse_subcircuit())
            elif self.current.type == TokenType.IDENTIFIER:
                # Parse subcircuit instantiation: SubcktName InstanceName;
                components.append(self.parse_subcircuit_instance())
            else:
                raise SyntaxError(
                    f"Unexpected token {self.current.value!r} "
                    f"at line {self.current.line}, column {self.current.column}"
                )
        return Program(components, connections, simulations, subcircuits)

    def parse_component(self) -> ComponentDeclaration:
        ctype = self.consume(TokenType.COMPONENT).value
        name  = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, '(')
        value = float(self.consume(TokenType.NUMBER).value)
        unit  = self.consume(TokenType.UNIT).value
        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        return ComponentDeclaration(ctype, name, value, unit)

    def parse_connection(self) -> Connection:
        self.consume(TokenType.CONNECT)
        self.consume(TokenType.SYMBOL, '(')
        endpoints = []
        while True:
            if self.current.type == TokenType.IDENTIFIER:
                # Look ahead: if next is dot, parse as terminal, else as node name
                lookahead = self.tokens[self.index + 1]
                if lookahead.value == '.':
                    # Parse hierarchical terminal
                    parts = [self.consume(TokenType.IDENTIFIER).value]
                    while self.current.value == '.':
                        self.consume(TokenType.SYMBOL, '.')
                        parts.append(self.consume(TokenType.IDENTIFIER).value)
                    if len(parts) < 2:
                        raise SyntaxError("Expected at least one dot in terminal reference")
                    comp = '.'.join(parts[:-1])
                    term = parts[-1]
                    endpoints.append(ComponentTerminal(comp, term))
                else:
                    # It's a node name
                    endpoints.append(self.consume(TokenType.IDENTIFIER).value)
            else:
                # literal node name or 'ground'
                endpoints.append(self.current.value)
                self.advance()
            # comma-separated?
            if self.current.value == ',':
                self.consume(TokenType.SYMBOL, ',')
                continue
            break
        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        return Connection(endpoints)

    def parse_simulation(self) -> SimulationBlock:
        self.consume(TokenType.SIMULATE)
        self.consume(TokenType.SYMBOL, '{')
        commands: List[SimulationCommand] = []
        while self.current.value != '}':
            stype = self.consume(TokenType.KEYWORD).value
            params = []
            if self.current.value == '(':
                self.consume(TokenType.SYMBOL, '(')
                while True:
                    if self.current.type == TokenType.NUMBER:
                        params.append(float(self.consume(TokenType.NUMBER).value))
                    else:
                        params.append(self.consume(TokenType.KEYWORD).value)
                    if self.current.value == ',':
                        self.consume(TokenType.SYMBOL, ',')
                        continue
                    break
                self.consume(TokenType.SYMBOL, ')')
            self.consume(TokenType.SYMBOL, ';')
            commands.append(SimulationCommand(stype, params))
        # closing brace
        self.consume(TokenType.SYMBOL, '}')
        # consume optional semicolon after the block
        if self.current.type == TokenType.SYMBOL and self.current.value == ';':
            self.consume(TokenType.SYMBOL, ';')
        return SimulationBlock(commands)

    def parse_subcircuit(self) -> Subcircuit:
        self.consume(TokenType.SUBCIRCUIT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, '{')
        comps, conns, sims = [], [], []
        while self.current.value != '}':
            if self.current.type == TokenType.COMPONENT:
                comps.append(self.parse_component())
            elif self.current.type == TokenType.CONNECT:
                conns.append(self.parse_connection())
            elif self.current.type == TokenType.SIMULATE:
                sims.append(self.parse_simulation())
            else:
                raise SyntaxError(
                    f"Unexpected token {self.current.value!r} "
                    f"at line {self.current.line}, column {self.current.column}"
                )
        self.consume(TokenType.SYMBOL, '}')
        self.consume(TokenType.SYMBOL, ';')
        return Subcircuit(name, comps, conns, sims)

    def parse_subcircuit_instance(self) -> ComponentDeclaration:
        subckt_type = self.consume(TokenType.IDENTIFIER).value
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, ';')
        # Use a special type or flag to indicate this is a subcircuit instance
        return ComponentDeclaration(subckt_type, name, 0, '')
