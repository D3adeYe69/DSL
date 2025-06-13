    def visit_SubcircuitInstance(self, node: SubcircuitInstance):
        # Find the subcircuit definition
        subcircuit_def = None
        for subcircuit in self.current_scope.subcircuits:
            if subcircuit.name == node.subcircuit_name:
                subcircuit_def = subcircuit
                break
        
        if not subcircuit_def:
            self.errors.append(f"Undefined subcircuit '{node.subcircuit_name}'")
            return

        # Validate port connections
        for port_name, connection in node.port_connections.items():
            if not any(port.name == port_name for port in subcircuit_def.ports):
                self.errors.append(
                    f"Port '{port_name}' not found in subcircuit '{node.subcircuit_name}'. "
                    f"Available ports: {', '.join(p.name for p in subcircuit_def.ports)}"
                )

        # Validate parameter overrides
        for param_name, value in node.parameter_overrides.items():
            # Check if parameter exists in subcircuit
            if not any(p.name == param_name for p in subcircuit_def.parameters):
                self.errors.append(
                    f"Parameter '{param_name}' not found in subcircuit '{node.subcircuit_name}'. "
                    f"Available parameters: {', '.join(p.name for p in subcircuit_def.parameters)}"
                )
            else:
                # Visit the parameter value expression
                self.visit(value)

        # Visit all components and connections in the subcircuit
        for component in subcircuit_def.components:
            self.visit(component)
        for connection in subcircuit_def.connections:
            self.visit(connection) 