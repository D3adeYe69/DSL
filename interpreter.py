# interpreter.py
from typing import Dict
from ast_nodes import (
    Program, ComponentDeclaration, ComponentTerminal,
    Connection, SimulationBlock, Subcircuit
)
class Interpreter:
    def __init__(self, program: Program):
        self.program = program
        self.node_counter = 1
        self.node_name_to_id: Dict[str,int] = {}
        self.terminal_map: Dict[str, Dict[str,int]] = {}
        # inline any subcircuit instances
        self._expand_instances()

    def _expand_instances(self):
        for inst in self.program.instances:
            sub = next((s for s in self.program.subcircuits if s.name == inst.subckt_name), None)
            if sub is None:
                raise ValueError(f"Unknown subcircuit '{inst.subckt_name}'")
            # clone components
            for comp in sub.components:
                cloned = ComponentDeclaration(
                    type=comp.type,
                    name=f"{inst.instance_name}.{comp.name}",
                    value=comp.value,
                    unit=comp.unit
                )
                self.program.components.append(cloned)
            # clone connections
            for conn in sub.connections:
                new_eps = []
                for ep in conn.endpoints:
                    if isinstance(ep, ComponentTerminal):
                        new_eps.append(
                            ComponentTerminal(
                                component=f"{inst.instance_name}.{ep.component}",
                                terminal=ep.terminal
                            )
                        )
                    else:
                        # literal node or ground: leave as-is
                        new_eps.append(ep)
                self.program.connections.append(Connection(new_eps))
            # simulations inside subcircuits could be dropped or merged if desired

    def build_node_mapping(self):
        for conn in self.program.connections:
            # ground has node 0
            if any(ep == 'ground' for ep in conn.endpoints):
                nid = 0
            else:
                literals = [ep for ep in conn.endpoints if isinstance(ep,str) and ep!='ground']
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
            for ep in conn.endpoints:
                if isinstance(ep, ComponentTerminal):
                    self.terminal_map.setdefault(ep.component, {})[ep.terminal] = nid

    def generate_netlist(self) -> str:
        self.build_node_mapping()
        lines = []
        for comp in self.program.components:
            term_map = self.terminal_map.get(comp.name, {})
            n_plus  = term_map.get('positive', 0)
            n_minus = term_map.get('negative', 0)
            lines.append(f"{comp.name} {n_plus} {n_minus} {comp.value}{comp.unit}")
        for sim in self.program.simulations:
            for cmd in sim.commands:
                lines.append(self._format_sim(cmd))
        return "\n".join(lines)

    def _format_sim(self, cmd):
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
        print(self.generate_netlist())
