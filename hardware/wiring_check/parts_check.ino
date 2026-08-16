/*
 * parts_check - are the piezo and the HC-SR04 actually there?
 *
 * These two are the parts the demo was made to work without, on the evidence
 * that the sensor returned nothing. That evidence was taken in one sitting and
 * never retaken, and the piezo was never tested at all - so neither is
 * genuinely known to be dead. This settles both.
 *
 * The sensor is tried on 5 V wiring as designed. If it answers, the firmware
 * flag can go back on and the demo gets a real hand-waving detector instead of
 * a typed number, which is worth a great deal in front of an audience.
 */

const int PIN_TRIG = 13;
const int PIN_ECHO = 39;      // VN
const int PIN_EMIT = 25;

float pingCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 25000UL);
  return us == 0 ? -1.0f : us / 58.0f;
}

void setup() {
  Serial.begin(115200);
  delay(400);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  Serial.println();
  Serial.println("parts_check");
  Serial.println("=========================================");

  // ---- piezo: audible sweep, so a working one cannot be missed
  Serial.println("PIEZO: sweeping 500 Hz -> 4 kHz for 4 s. Listen.");
  ledcAttach(PIN_EMIT, 1000, 8);
  for (int f = 500; f <= 4000; f += 25) {
    ledcWriteTone(PIN_EMIT, f);
    delay(25);
  }
  ledcWriteTone(PIN_EMIT, 0);
  ledcDetach(PIN_EMIT);
  Serial.println("PIEZO: done. Audible = wired. Silent = check GPIO25 chain.");
  Serial.println();

  Serial.println("SENSOR: 20 pings over 4 s. Put your hand 20-80 cm away.");
}

void loop() {
  static int good = 0, total = 0;
  if (total < 20) {
    float cm = pingCm();
    total++;
    if (cm > 0) good++;
    Serial.printf("  ping %2d: %s\n", total,
                  cm > 0 ? String(cm, 1).c_str() : "no echo");
    delay(200);
    if (total == 20) {
      Serial.println();
      Serial.printf("SENSOR: %d of 20 returned\n", good);
      Serial.println(good > 10 ? "SENSOR: WORKS - set HAVE_SENSOR 1"
                               : "SENSOR: check VCC on VIN/5V, TRIG=13, ECHO via divider to VN");
    }
  } else {
    delay(1000);
  }
}
