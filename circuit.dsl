VoltageSource V1(5 V);
Resistor     R1(1 kOhm);
Capacitor    C1(100 uF);

Connect(V1.positive, R1.positive);
Connect(R1.negative, C1.positive);
Connect(C1.negative, ground);
Connect(V1.negative, ground);
Simulate
{
dc;}