# parser.py
from typing import List
from ast_nodes import (
    ComponentDeclaration, ComponentTerminal, Connection,
    SimulationCommand, SimulationBlock, Subcircuit,
    Program, SubcircuitInstance
)
from lexer import Token, TokenType

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.index = -1
        self.current: Token = None
        self.advance()

    def advance(self):
        self.index += 1
        self.current = (
            self.tokens[self.index]
            if self.index < len(self.tokens)
            else Token(TokenType.EOF, '', -1, -1)
        )

    def consume(self, ttype: TokenType, value: str = None) -> Token:
        if self.current.type == ttype and (value is None or self.current.value == value):
            tok = self.current
            self.advance()
            return tok
        raise SyntaxError(
            f"Expected {ttype.name}{' '+value if value else ''}, "
            f"got {self.current.value!r} at line {self.current.line}, col {self.current.column}"
        )

    def parse(self) -> Program:
        components, connections, simulations, subcircuits, instances = [], [], [], [], []
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
                # subcircuit instantiation: e.g. OpAmp U1;
                subckt_name   = self.consume(TokenType.IDENTIFIER).value
                instance_name = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.SYMBOL, ';')
                instances.append(SubcircuitInstance(subckt_name, instance_name))
            else:
                raise SyntaxError(
                    f"Unexpected token {self.current.value!r} "
                    f"at line {self.current.line}, col {self.current.column}"
                )
        return Program(components, connections, simulations, subcircuits, instances)

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
            if self.current.type == TokenType.IDENTIFIER \
               and self.tokens[self.index+1].value == '.':
                comp = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.SYMBOL, '.')
                term = self.consume(TokenType.IDENTIFIER).value
                endpoints.append(ComponentTerminal(comp, term))
            else:
                endpoints.append(self.current.value)
                self.advance()
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

        cmds: List[SimulationCommand] = []
        while self.current.value != '}':
            stype = self.consume(TokenType.KEYWORD).value
            params: List[Union[float,str]] = []
            # if there's a parameter list
            if self.current.value == '(':
                self.consume(TokenType.SYMBOL, '(')
                # keep reading params until we hit ')'
                while self.current.value != ')':
                    if self.current.type == TokenType.NUMBER:
                        params.append(float(self.consume(TokenType.NUMBER).value))
                    else:
                        params.append(self.consume(TokenType.KEYWORD).value)
                    # optionally eat a comma, but don’t require it
                    if self.current.value == ',':
                        self.consume(TokenType.SYMBOL, ',')
                    # if it's neither comma nor ')', we loop again and grab the next token
                self.consume(TokenType.SYMBOL, ')')
            self.consume(TokenType.SYMBOL, ';')
            cmds.append(SimulationCommand(stype, params))
        # closing brace
        self.consume(TokenType.SYMBOL, '}')
        # optional semicolon after block
        if self.current.type == TokenType.SYMBOL and self.current.value == ';':
            self.consume(TokenType.SYMBOL, ';')
        return SimulationBlock(cmds)


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
                raise SyntaxError(f"Unexpected token {self.current.value!r}")
        self.consume(TokenType.SYMBOL, '}')
        self.consume(TokenType.SYMBOL, ';')
        return Subcircuit(name, comps, conns, sims)
