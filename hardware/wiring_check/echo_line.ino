/*
 * echo_line - is anything driving the ECHO pin?
 *
 * A powered HC-SR04 actively holds ECHO low between pings. An unconnected
 * GPIO39 has no internal pull anywhere in the silicon, so it floats and
 * wanders with whatever is nearby.
 *
 * Sampling the pin thousands of times therefore separates two failures that
 * look identical from a ping count of zero:
 *
 *   rock-solid LOW  -> the wire is connected and the sensor is powered, so the
 *                      fault is upstream: TRIG, or the module not transmitting
 *                      at 3.3 V
 *   wandering       -> nothing is driving the pin; the ECHO wire is not
 *                      actually reaching it
 *
 * GPIO13 is left alone here. No trigger is sent, on purpose - this is a
 * question about the wire, not about the sensor's reply.
 */

const int PIN_ECHO = 39;      // VN
const int PIN_TRIG = 13;

void setup() {
  Serial.begin(115200);
  delay(400);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_TRIG, OUTPUT);
  digitalWrite(PIN_TRIG, LOW);      // deliberately silent
  Serial.println();
  Serial.println("echo_line - watching GPIO39 with no trigger sent");

  uint32_t highs = 0, flips = 0, n = 0;
  int prev = digitalRead(PIN_ECHO);
  /* Yield periodically. A three second tight loop starves the ESP32's idle
   * task and the watchdog reboots the chip mid-measurement, which prints the
   * verdict over and over and reads exactly like a hardware fault. It was not
   * one; it was this loop. */
  uint32_t end = millis() + 3000;
  while (millis() < end) {
    for (int k = 0; k < 200; k++) {
      int v = digitalRead(PIN_ECHO);
      n++;
      if (v) highs++;
      if (v != prev) flips++;
      prev = v;
    }
    delay(1);
  }

  Serial.printf("samples %lu   high %lu (%.1f%%)   transitions %lu\n",
                (unsigned long)n, (unsigned long)highs,
                100.0 * highs / n, (unsigned long)flips);
  if (flips < 20 && highs * 100 / n < 2) {
    Serial.println("VERDICT: held LOW. Something is driving the pin - the ECHO");
    Serial.println("         wire is connected and the sensor has power. The");
    Serial.println("         fault is TRIG, or the module will not transmit at 3.3 V.");
  } else {
    Serial.println("VERDICT: floating. Nothing is driving GPIO39 - the ECHO wire");
    Serial.println("         is not reaching the pin, or the sensor has no power.");
  }
}

void loop() { delay(1000); }
