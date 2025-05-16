Resistor R1(10 ohm);
Capacitor C1(1 uF);
Connect(R1.positive, C1.negative, ground);
Simulate { dc; transient(0, 10, 0.1); ac(1000); };
Subcircuit Amp {
  VoltageSource V1(5 V);
  Resistor R2(2 kOhm);
  Connect(V1.positive, R2.positive, node1);
  Simulate { dc; };
};