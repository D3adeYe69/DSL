# Basic components with named parameters
VoltageSource V1(value=5 V);
Resistor R1(resistance=1 kohm);
Capacitor C1(capacitance=100 uF);

# More components with named parameters
VoltageSource V2(value=10 V);
Resistor R2(resistance=2 kohm);
Capacitor C2(capacitance=200 uF);

# Define a simple RC filter subcircuit
Subcircuit RCFilter(input, output) {
    Resistor R(resistance=1 kohm);
    Capacitor C(capacitance=100 uF);
    
    Connect(input, R.positive);
    Connect(R.negative, C.positive);
    Connect(C.negative, output);
};

# Use the subcircuit with named parameters
RCFilter input=in1 output=out1;

# Connect components
Connect(V1.positive, R1.positive);
Connect(R1.negative, C1.positive);
Connect(C1.negative, ground);
Connect(V1.negative, ground);

# Connect subcircuit
Connect(V2.positive, in1);
Connect(out1, ground);
Connect(V2.negative, ground);

# Run both DC and AC analysis
Simulate {
    dc;
    plot(V(R1.positive), V(R1.negative));
    
    ac(dec, 10, 1 Hz, 1 MHz);
    plot(V(in1), V(out1));
};
