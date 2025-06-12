ACSource V1(1 V);
Resistor R1(100 ohm);
Resistor R2(200 ohm);
Capacitor C1(1 uF);
Capacitor C2(2 uF);
Inductor L1(10 mH);

# First stage
Connect(V1.positive, R1.positive);
Connect(R1.negative, C1.positive);
Connect(C1.negative, L1.positive);
Connect(L1.negative, V1.negative);

# Second stage
Connect(C1.negative, R2.positive);
Connect(R2.negative, C2.positive);
Connect(C2.negative, V1.negative);

Simulate { ac; };
