/*
 * GauKavach - pin probe
 * ---------------------
 * Answers one question without a human looking at anything: are any two of the
 * output pins electrically the same node?
 *
 * That fault is invisible from the firmware's side. The governor drives GPIO26
 * and GPIO27 at different times, quite correctly, and if a jumper puts them in
 * one breadboard column they light the same LED and a third LED never lights
 * at all. Every log line is right; the board is still wrong.
 *
 * HOW IT WORKS
 * Drive one pin HIGH and hold the others as inputs with the internal pull-down
 * enabled. A pull-down is about 45 kOhm, so anything joining two pins - a
 * shared column, or two 220 Ohm resistors meeting at one LED anode - wins
 * against it easily and the reading comes back HIGH. Genuinely separate pins
 * stay LOW because nothing is driving them.
 *
 * Then the drive is inverted as a control: if a pin reads HIGH while the
 * driver is LOW, the reading was never about the driver, and the pair is
 * reported as inconclusive rather than quietly counted as connected.
 */

const int PINS[] = {26, 27, 14, 25};
const char *NAMES[] = {"GPIO26 permit", "GPIO27 refuse", "GPIO14 escalate",
                       "GPIO25 emitter"};
const int N = 4;

void allInputs() {
  for (int i = 0; i < N; i++) pinMode(PINS[i], INPUT_PULLDOWN);
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println("GauKavach pin probe");
  Serial.println("===================================================");
  Serial.println("Testing whether any two output pins are the same node.");
  Serial.println();

  bool anyShort = false;

  for (int a = 0; a < N; a++) {
    allInputs();
    pinMode(PINS[a], OUTPUT);

    for (int b = 0; b < N; b++) {
      if (a == b) continue;

      digitalWrite(PINS[a], HIGH);
      delay(6);
      bool high = digitalRead(PINS[b]);

      digitalWrite(PINS[a], LOW);
      delay(6);
      bool low = digitalRead(PINS[b]);

      if (high && !low) {
        Serial.printf("  SHORTED   %s  and  %s  are the same node\n",
                      NAMES[a], NAMES[b]);
        anyShort = true;
      } else if (high && low) {
        Serial.printf("  ?         %s reads high whatever %s does\n",
                      NAMES[b], NAMES[a]);
      }
    }
    digitalWrite(PINS[a], LOW);
  }

  allInputs();
  if (!anyShort) {
    Serial.println("  CLEAR     no two pins are joined; each drives its own chain");
  }
  Serial.println();
  Serial.println("done");
}

void loop() {
  delay(1000);
}
