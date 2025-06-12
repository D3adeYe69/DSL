VoltageSource V1(9 V);
Resistor R1(100 ohm);
Connect(V1.positive, R1.positive);
Connect(R1.negative, V1.negative);
Simulate { dc; };
