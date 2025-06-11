from typing import List
from lexer import Token, TokenType
from ast_nodes import (
    ComponentDeclaration,
    ComponentTerminal,
    Connection,
    ASTNetDecl,
    SubcircuitDecl,
    SubcircuitInstance,
    DCCommand,
    ACCommand,
    TransientCommand,
    ParamSweepCommand,
    SimulationBlock,
    Program,
)

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
        components: List[ComponentDeclaration]       = []
        connections: List[Connection]                = []
        simulations: List[SimulationBlock]           = []
        subckt_defs: List[SubcircuitDecl]            = []
        subckt_insts: List[SubcircuitInstance]       = []
        nets: List[ASTNetDecl]                       = []

        while self.current.type != TokenType.EOF:
            if self.current.type == TokenType.NET:
                nets.append(self.parse_net_decl())

            elif self.current.type == TokenType.COMPONENT:
                components.append(self.parse_component())

            elif self.current.type == TokenType.CONNECT:
                connections.append(self.parse_connection())

            elif self.current.type == TokenType.SIMULATE:
                simulations.append(self.parse_simulation())

            elif self.current.type == TokenType.SUBCIRCUIT:
                subckt_defs.append(self.parse_subcircuit())

            elif self.current.type == TokenType.IDENTIFIER:
                subckt_insts.append(self.parse_subcircuit_inst())

            else:
                raise SyntaxError(
                    f"Unexpected token {self.current.value!r} "
                    f"at line {self.current.line}, column {self.current.column}"
                )

        return Program(
            components,
            connections,
            simulations,
            subckt_defs,
            subckt_insts,
            nets,
        )

    def parse_net_decl(self) -> ASTNetDecl:
        self.consume(TokenType.NET)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, ';')
        return ASTNetDecl(name)

    def parse_component(self) -> ComponentDeclaration:
        ctype = self.consume(TokenType.COMPONENT).value
        name  = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, '(')

        params = []
        while True:
            if self.current.type == TokenType.NUMBER:
                num = float(self.consume(TokenType.NUMBER).value)
                unit = None
                if self.current.type == TokenType.UNIT:
                    unit = self.consume(TokenType.UNIT).value
                params.append((None, (num, unit)))

            elif self.current.type == TokenType.IDENTIFIER:
                key = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.OPERATOR, '=')
                if self.current.type == TokenType.NUMBER:
                    num = float(self.consume(TokenType.NUMBER).value)
                    unit = None
                    if self.current.type == TokenType.UNIT:
                        unit = self.consume(TokenType.UNIT).value
                    params.append((key, (num, unit)))
                else:
                    val = self.consume(TokenType.IDENTIFIER).value
                    params.append((key, val))

            else:
                break

            if self.current.value == ',':
                self.consume(TokenType.SYMBOL, ',')
            else:
                break

        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        return ComponentDeclaration(ctype, name, params)

    def parse_connection(self) -> Connection:
        self.consume(TokenType.CONNECT)
        self.consume(TokenType.SYMBOL, '(')
        endpoints = []

        while True:
            if self.current.type == TokenType.GROUND:
                endpoints.append("ground")
                self.advance()

            elif self.current.type == TokenType.IDENTIFIER:
                look = self.tokens[self.index + 1]
                if look.value == '.':
                    parts = [self.consume(TokenType.IDENTIFIER).value]
                    while self.current.value == '.':
                        self.consume(TokenType.SYMBOL, '.')
                        parts.append(self.consume(TokenType.IDENTIFIER).value)
                    comp = '.'.join(parts[:-1])
                    term = parts[-1]
                    endpoints.append(ComponentTerminal(comp, term))
                else:
                    endpoints.append(self.consume(TokenType.IDENTIFIER).value)
            else:
                raise SyntaxError(f"Unexpected endpoint {self.current.value!r}")

            if self.current.value == ',':
                self.consume(TokenType.SYMBOL, ',')
            else:
                break

        self.consume(TokenType.SYMBOL, ')')
        self.consume(TokenType.SYMBOL, ';')
        return Connection(endpoints)

    def parse_simulation(self) -> SimulationBlock:
        self.consume(TokenType.SIMULATE)
        self.consume(TokenType.SYMBOL, '{')
        commands = []

        while self.current.value != '}':
            kw = self.consume(TokenType.KEYWORD).value

            if kw == 'dc':
                self.consume(TokenType.SYMBOL, ';')
                commands.append(DCCommand())

            elif kw == 'ac':
                self.consume(TokenType.SYMBOL, '(')
                f0 = float(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ',')
                f1 = float(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ',')
                pts = int(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ')')
                self.consume(TokenType.SYMBOL, ';')
                commands.append(ACCommand(f0, f1, pts))

            elif kw == 'transient':
                self.consume(TokenType.SYMBOL, '(')
                t_stop = float(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ',')
                dt     = float(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ')')
                self.consume(TokenType.SYMBOL, ';')
                commands.append(TransientCommand(t_stop, dt))

            elif kw == 'paramSweep':
                self.consume(TokenType.SYMBOL, '(')
                pname = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.SYMBOL, ',')
                s0    = float(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ',')
                s1    = float(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ',')
                n     = int(self.consume(TokenType.NUMBER).value)
                self.consume(TokenType.SYMBOL, ')')
                self.consume(TokenType.SYMBOL, ';')
                commands.append(ParamSweepCommand(pname, s0, s1, n))

            else:
                raise SyntaxError(f"Unknown simulation keyword {kw!r}")

        self.consume(TokenType.SYMBOL, '}')
        if self.current.value == ';':
            self.consume(TokenType.SYMBOL, ';')
        return SimulationBlock(commands)

    def parse_subcircuit(self) -> SubcircuitDecl:
        self.consume(TokenType.SUBCIRCUIT)
        name = self.consume(TokenType.IDENTIFIER).value

        # optional parameter list
        param_names: List[str] = []
        if self.current.value == '(':
            self.consume(TokenType.SYMBOL, '(')
            while True:
                param_names.append(self.consume(TokenType.IDENTIFIER).value)
                if self.current.value == ',':
                    self.consume(TokenType.SYMBOL, ',')
                    continue
                break
            self.consume(TokenType.SYMBOL, ')')

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
        return SubcircuitDecl(name, param_names, comps, conns, sims)

    def parse_subcircuit_inst(self) -> SubcircuitInstance:
        type_name     = self.consume(TokenType.IDENTIFIER).value
        instance_name = self.consume(TokenType.IDENTIFIER).value

        params = []
        if self.current.value == '(':
            self.consume(TokenType.SYMBOL, '(')
            while True:
                if self.current.type == TokenType.NUMBER:
                    num = float(self.consume(TokenType.NUMBER).value)
                    unit = None
                    if self.current.type == TokenType.UNIT:
                        unit = self.consume(TokenType.UNIT).value
                    params.append((None, (num, unit)))
                elif self.current.type == TokenType.IDENTIFIER:
                    params.append(self.consume(TokenType.IDENTIFIER).value)
                else:
                    break

                if self.current.value == ',':
                    self.consume(TokenType.SYMBOL, ',')
                    continue
                break
            self.consume(TokenType.SYMBOL, ')')

        self.consume(TokenType.SYMBOL, ';')
        return SubcircuitInstance(type_name, instance_name, params)
