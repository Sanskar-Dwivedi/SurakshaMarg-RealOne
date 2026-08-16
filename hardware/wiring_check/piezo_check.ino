/*
 * piezo_check - is the emitter wired, and can you hear what it actually emits?
 *
 * Two different questions, and confusing them wastes an evening.
 *
 * Part one sweeps 500 Hz to 4 kHz. That is squarely inside human hearing, so
 * if the GPIO25 chain is intact it is unmissable. This tests the WIRING.
 *
 * Part two plays the real carrier, 25 kHz, for three seconds. Most adults
 * cannot hear anything above about 17 kHz, so silence here is the expected
 * result and not a fault. This tests your EARS, not the rig.
 *
 * A piezo that passes part one and is silent in part two is working exactly as
 * designed. The carrier is meant to be inaudible; the LED and the serial log
 * are what tell you emission is happening.
 */

const int PIN_EMIT = 25;

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("piezo_check");
  Serial.println("==================================================");

  Serial.println("PART 1 - audible sweep, 500 Hz to 4 kHz, 5 seconds.");
  Serial.println("         Hearing this means GPIO25 is wired correctly.");
  ledcAttach(PIN_EMIT, 1000, 8);
  for (int pass = 0; pass < 2; pass++) {
    for (int f = 500; f <= 4000; f += 20) {
      ledcWriteTone(PIN_EMIT, f);
      delay(14);
    }
  }
  ledcWriteTone(PIN_EMIT, 0);
  delay(800);

  Serial.println();
  Serial.println("PART 2 - the real carrier, 25 kHz, 3 seconds.");
  Serial.println("         Silence here is CORRECT. It is above hearing.");
  ledcWriteTone(PIN_EMIT, 25000);
  delay(3000);
  ledcWriteTone(PIN_EMIT, 0);
  ledcDetach(PIN_EMIT);

  Serial.println();
  Serial.println("Heard part 1, not part 2  -> wired, and behaving as designed.");
  Serial.println("Heard neither             -> check 220R and the piezo legs.");
  Serial.println("Heard both                -> your hearing is better than most.");
}

void loop() { delay(1000); }
