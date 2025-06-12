# Circuit DSL Project

## Overview
This project provides a domain-specific language (DSL) for describing and simulating electronic circuits, with a web and CLI interface, visualization, and robust testing.

## Project Background
The idea behind this project is to create a simple, intuitive language for describing electronic circuits. By using a DSL, users can define circuits in a human-readable format, which is then parsed, analyzed, and visualized. This project includes a lexer, parser, semantic analyzer, and interpreter to process the DSL code, along with a web interface and CLI for user interaction. The goal is to make circuit design and simulation accessible to both beginners and experts.

## Project Structure
- **lexer.py**: Implements the lexical analyzer, which tokenizes the input DSL code into tokens for further processing.
- **parser.py**: Contains the parser that converts tokens into an Abstract Syntax Tree (AST), representing the structure of the circuit.
- **semantic.py**: Performs semantic analysis on the AST to ensure the circuit is valid and well-formed.
- **interpreter.py**: Executes the AST to simulate the circuit and generate output.
- **main.py**: The entry point for the CLI, handling command-line arguments and orchestrating the lexer, parser, semantic analyzer, and interpreter.
- **cli.py**: Provides a web server interface for interacting with the DSL, allowing users to input circuit definitions and view results.
- **ast_nodes.py**: Defines the AST node classes used by the parser and interpreter.
- **examples/**: Contains sample DSL files for testing and demonstration.
- **tests/**: Houses unit tests for the lexer, parser, semantic analyzer, and interpreter.
- **web/**: Contains web-related files for the interactive visualization.

## Usage

### CLI
To compile and visualize a circuit from a DSL file:

```sh
python3 main.py examples/simple_resistor.dsl output.png
```

### Web Interface
To run the web server:

```sh
python3 cli.py --port 8000
```
Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Logging
All errors and important events are logged using Python's `logging` module. You can adjust the logging level in `main.py` and `cli.py`.

## Testing
Run all tests with:

```sh
python3 -m unittest discover tests
```

## Code Quality
- The codebase uses logging instead of print statements for all diagnostics and errors.
- All exceptions are handled gracefully and logged.
- The code is formatted and linted for readability and maintainability.

## Contributing
- Please ensure all new code is tested and documented.
- Run a linter (e.g., `flake8`, `pylint`) and formatter (e.g., `black`) before submitting a pull request.
- Add docstrings to all public classes and functions.

## License
MIT License

# Circuit+- DSL

A simple domain-specific language for modeling and visualizing electrical circuits.

## Quick Start

### Requirements
- Python 3.10 or later
- Flask

### Installation

1. Clone and setup:
   ```sh
   git clone https://github.com/D3adeYe69/DSL
   cd DSL
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # OR
   source .venv/bin/activate  # On Linux/Mac
   pip install flask
   ```

2. Run the visualization:
   ```sh
   python interactive_visualization.py
   ```

3. Open your browser and go to:
   ```
   http://localhost:5000
   ```

## Example Circuit

Here's a simple RC circuit example:
```
VoltageSource V1(5 V);
Resistor R1(1 kOhm);
Capacitor C1(100 uF);

Connect(V1.positive, R1.positive);
Connect(R1.negative, C1.positive);
Connect(C1.negative, V1.negative, ground);

Simulate {
    dc;
};
```

Write this code in the web interface and click "Visualize" to see the circuit diagram.

.node-text {
  font-size: 14px;
  text-anchor: middle;
  dominant-baseline: middle;
}



