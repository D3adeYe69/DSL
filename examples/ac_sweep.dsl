# AC sweep analysis example
ACSource S1(frequency=50 Hz, amplitude=5 V);
Resistor R1(resistance=100 ohm);
Capacitor C1(capacitance=100 nF);

# Connect components
Connect(S1.positive, R1.positive);
Connect(S1.negative, ground);
Connect(R1.negative, C1.positive);
Connect(C1.negative, ground);

# Run AC analysis
Simulate {
    ac(dec, 10, 1 Hz, 1 MHz);
    plot(V(R1.positive), V(R1.negative));
};

