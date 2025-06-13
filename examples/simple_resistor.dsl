# Simple resistor circuit with voltage source
VoltageSource V1(value=5 V);
Resistor R1(resistance=1 kohm);

# Connect components
Connect(V1.positive, R1.positive);
Connect(R1.negative, ground);
Connect(V1.negative, ground);

# Run DC analysis
Simulate {
    dc;
    plot(V(R1.positive), V(R1.negative));
};
