ACSource V1(1 V);
Resistor R1(100 ohm);
Capacitor C1(1 uF);
Connect(V1.positive, R1.positive);
Connect(R1.negative, C1.positive);
Connect(C1.negative, V1.negative);
Simulate { ac; };
