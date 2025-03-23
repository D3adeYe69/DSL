# Circuit+- DSL

Circuit+- is a domain-specific language (DSL) designed for modeling and simulating electrical circuits. It allows users to define components, establish connections, and run simulations using a simple and readable syntax.

## Features
- Define circuit components such as resistors, capacitors, inductors, voltage sources, and current sources.
- Establish connections between components.
- Create reusable subcircuits.
- Perform DC, AC, and transient analysis.
- Support for conditional and iterative structures.

## Example Code
```circuit+
Resistor R1(10 ohm);
VoltageSource V1(5 V);
Connect(R1.positive, V1);

Simulate {
    dc;
    transient(0, 10, 0.1);
}
```

## Lexer Implementation
The Circuit+- lexer is implemented in Python and is responsible for tokenizing the DSL code before parsing. It recognizes:
- Identifiers (component names, labels)
- Numbers (integer, floating-point, scientific notation)
- Operators and symbols
- Keywords (component types, simulation commands, control structures)

## Getting Started
### Requirements
- Python 3.10 or later

### Running the Lexer
1. Clone this repository:
   ```sh
   git clone https://github.com/your-repo/circuit-plus-minus.git
   cd DSL
   ```
2. Run the lexer with a sample code:
   ```sh
   python Lexer.py 
   ```



