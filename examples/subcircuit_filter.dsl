# Define a bandpass filter subcircuit
Subcircuit BandpassFilter(input, output) {
    Resistor R1(resistance=100 ohm);
    Resistor R2(resistance=200 ohm);
    Capacitor C1(capacitance=1 uF);
    Capacitor C2(capacitance=2 uF);
    Inductor L1(inductance=10 mH);

    # First stage
    Connect(input, R1.positive);
    Connect(R1.negative, C1.positive);
    Connect(C1.negative, L1.positive);
    Connect(L1.negative, output);

    # Second stage
    Connect(C1.negative, R2.positive);
    Connect(R2.negative, C2.positive);
    Connect(C2.negative, output);
};

# Create input source
ACSource V1(frequency=1 kHz, amplitude=1 V);

# Create filter instance with named parameters
BandpassFilter input=in1 output=out1;

# Connect the filter
Connect(V1.positive, in1);
Connect(out1, ground);
Connect(V1.negative, ground);

# Run AC analysis
Simulate {
    ac(dec, 10, 1 Hz, 1 MHz);
    plot(V(in1), V(out1));
};
