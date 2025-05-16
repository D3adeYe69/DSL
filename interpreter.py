from typing import Dict, List
from ast_nodes import *

class Interpreter:
    def __init__(self, program: Program):
        self.program = program
        self.node_counter = 1
        self.node_name_to_id: Dict[str, int] = {}
        self.terminal_map: Dict[str, Dict[str, int]] = {}

    def build_node_mapping(self):
        for conn in self.program.connections:
            endpoints = conn.endpoints
            # ground has node 0
            if any(ep == 'ground' for ep in endpoints):
                nid = 0
            else:
                literals = [ep for ep in endpoints if isinstance(ep, str) and ep != 'ground']
                nid = None
                for name in literals:
                    if name in self.node_name_to_id:
                        nid = self.node_name_to_id[name]
                        break
                if nid is None:
                    nid = self.node_counter
                    self.node_counter += 1
                for name in literals:
                    self.node_name_to_id[name] = nid
            for ep in endpoints:
                if isinstance(ep, ComponentTerminal):
                    self.terminal_map.setdefault(ep.component, {})[ep.terminal] = nid

    def generate_netlist(self) -> List[str]:
        self.build_node_mapping()
        lines: List[str] = []
        for comp in self.program.components:
            term_map = self.terminal_map.get(comp.name, {})
            n_plus  = term_map.get('positive', 0)
            n_minus = term_map.get('negative', 0)
            lines.append(f"{comp.name} {n_plus} {n_minus} {comp.value}{comp.unit}")
        for sub in self.program.subcircuits:
            lines.append(f".SUBCKT {sub.name}")
            subprog = Program(sub.components, sub.connections, sub.simulations, [])
            sub_interp = Interpreter(subprog)
            for line in sub_interp.generate_netlist():
                lines.append(f"  {line}")
            lines.append(f".ENDS {sub.name}")
        for sim in self.program.simulations:
            for cmd in sim.commands:
                lines.append(self._format_sim(cmd))
        return lines

    def _format_sim(self, cmd: SimulationCommand) -> str:
        typ = cmd.type.lower()
        if typ == 'dc':
            return '.OP'
        if typ == 'transient':
            start, stop, step = cmd.parameters
            return f".TRAN {step} {stop} {start}"
        if typ == 'ac':
            params = ' '.join(str(p) for p in cmd.parameters)
            return f".AC {params}"
        return f".{cmd.type.upper()} {' '.join(str(p) for p in cmd.parameters)}"

    def run(self):
        for line in self.generate_netlist():
            print(line)
