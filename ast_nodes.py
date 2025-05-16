from dataclasses import dataclass
from typing import List, Union

@dataclass
class ComponentDeclaration:
    type: str
    name: str
    value: float
    unit: str

@dataclass
class ComponentTerminal:
    component: str
    terminal: str

@dataclass
class Connection:
    endpoints: List[Union[ComponentTerminal, str]]  # component terminal or literal node/ground

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
