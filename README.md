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
Connect(C1.negative, ground);
Connect(V1.negative, ground);

Simulate {
    dc;
};
```

Write this code in the web interface and click "Visualize" to see the circuit diagram.



