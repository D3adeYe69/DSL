from dataclasses import dataclass
from typing import List, Union
from lexer import Lexer, Token, TokenType

@dataclass
class ComponentDeclaration:
    type: str
    name: str
    value: float
    unit: str

@dataclass
class Connection:
    components: List[str]
    nodes: List[str]

@dataclass
class SimulationCommand:
    type: str
    parameters: List[Union[float, str]]

@dataclass
class SimulationBlock:
    commands: List[SimulationCommand]

@dataclass
class Subcircuit:
    name: str
    components: List[ComponentDeclaration]
    connections: List[Connection]
    simulations: List[SimulationBlock]

@dataclass
class Program:
    components: List[ComponentDeclaration]
    connections: List[Connection]
    simulations: List[SimulationBlock]
    subcircuits: List[Subcircuit]

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token = None
        self.token_index = -1
        self.advance()

    def advance(self):
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        else:
            self.current_token = Token(TokenType.EOF, None)

    def consume(self, token_type, value=None):
        if self.current_token.type == token_type:
            if value is None or self.current_token.value == value:
                token = self.current_token
                self.advance()
                return token
        raise SyntaxError(f"Expected {token_type} {value if value else ''}, got {self.current_token}")

    def parse(self):
        components = []
        connections = []
        simulations = []
        subcircuits = []

        while self.current_token.type != TokenType.EOF:
            if self.current_token.type == TokenType.COMPONENT:
                components.append(self.parse_component())
            elif self.current_token.value == "Connect":
                connections.append(self.parse_connection())
            elif self.current_token.value == "Simulate":
                simulations.append(self.parse_simulation())
            elif self.current_token.value == "Subcircuit":
                subcircuits.append(self.parse_subcircuit())
            else:
                raise SyntaxError(f"Unexpected token: {self.current_token}")

        return Program(components, connections, simulations, subcircuits)

    def parse_component(self):
        component_type = self.consume(TokenType.COMPONENT).value
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.SYMBOL, "(")
        value = float(self.consume(TokenType.NUMBER).value)
        unit = self.consume(TokenType.UNIT).value
        self.consume(TokenType.SYMBOL, ")")
        self.consume(TokenType.SYMBOL, ";")
        return ComponentDeclaration(component_type, name, value, unit)

    def parse_connection(self):
        self.consume(TokenType.CONNECT)
        self.consume(TokenType.SYMBOL, "(")
        components = []
        nodes = []
        components.append(self.consume(TokenType.IDENTIFIER).value)
        self.consume(TokenType.SYMBOL, ".")
        nodes.append(self.consume(TokenType.IDENTIFIER).value)

        while self.current_token.value == ",":
            self.consume(TokenType.SYMBOL, ",")
            components.append(self.consume(TokenType.IDENTIFIER).value)
            self.consume(TokenType.SYMBOL, ".")
            nodes.append(self.consume(TokenType.IDENTIFIER).value)

        self.consume(TokenType.SYMBOL, ")")
        self.consume(TokenType.SYMBOL, ";")
        return Connection(components, nodes)

    def parse_simulation(self):
        self.consume(TokenType.SIMULATE)
        self.consume(TokenType.SYMBOL, "{")
        commands = []

        while self.current_token.value != "}":
            sim_type = self.consume(TokenType.KEYWORD).value
            params = []
            if self.current_token.value == "(":
                self.consume(TokenType.SYMBOL, "(")
                if self.current_token.type == TokenType.NUMBER:
                    params.append(float(self.consume(TokenType.NUMBER).value))
                else:
                    params.append(self.consume(TokenType.KEYWORD).value)

                while self.current_token.value == ",":
                    self.consume(TokenType.SYMBOL, ",")
                    if self.current_token.type == TokenType.NUMBER:
                        params.append(float(self.consume(TokenType.NUMBER).value))
                    else:
                        params.append(self.consume(TokenType.KEYWORD).value)

                self.consume(TokenType.SYMBOL, ")")

            self.consume(TokenType.SYMBOL, ";")
            commands.append(SimulationCommand(sim_type, params))

        self.consume(TokenType.SYMBOL, "}")
        return SimulationBlock(commands)

# Example Usage
if __name__ == "__main__":
    source = """
    Resistor R1(10 ohm);
    Capacitor C1(1 uF);
    Connect(R1.positive, C1.negative);
    Simulate { dc; transient(0, 10, 0.1); }
    """

    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print(ast)

def format_ast(program: Program, indent=0):
    space = " " * indent
    result = f"\n{space}Formatted Program:\n"

    if program.components:
        result += f"{space}  Components:\n"
        for component in program.components:
            result += f"{space}    - {component.type} {component.name} ({component.value} {component.unit})\n"

    if program.connections:
        result += f"{space}  Connections:\n"
        for connection in program.connections:
            result += f"{space}    - {', '.join(connection.components)} -> {', '.join(connection.nodes)}\n"

    if program.simulations:
        result += f"{space}  Simulations:\n"
        for sim in program.simulations:
            for cmd in sim.commands:
                params = ", ".join(map(str, cmd.parameters))
                result += f"{space}    - {cmd.type}({params})\n"

    if program.subcircuits:
        result += f"{space}  Subcircuits:\n"
        for sub in program.subcircuits:
            result += f"{space}    - {sub.name}:\n"
            result += format_ast(sub, indent + 2)

    return result

# Print the formatted output
print(format_ast(ast))
