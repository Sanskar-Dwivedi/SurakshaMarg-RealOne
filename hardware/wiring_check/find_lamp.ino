/*
 * find_lamp - which breadboard pin has the working LED?
 *
 * The on-board LED on GPIO2 is held LOW throughout. That matters: it is the
 * armed heartbeat, it runs whenever the board is powered, and on this board it
 * is green - so every previous answer about "green" may have been describing
 * the module rather than the breadboard. With it off, anything that lights is
 * definitely on the breadboard.
 *
 * Each candidate is then held HIGH for four seconds, alone, with two seconds
 * of darkness between so the boundaries are unmistakable.
 */

const int CAND[]   = {26, 27, 14};
const char *NAME[] = {"GPIO26", "GPIO27", "GPIO14"};
const int N = 3;
const int ONBOARD = 2;

void setup() {
  Serial.begin(115200);
  delay(400);
  pinMode(ONBOARD, OUTPUT);
  digitalWrite(ONBOARD, LOW);           // stays off for the whole test
  for (int i = 0; i < N; i++) { pinMode(CAND[i], OUTPUT); digitalWrite(CAND[i], LOW); }
  Serial.println();
  Serial.println("find_lamp - on-board LED is OFF for this test");
  Serial.println("each pin is held HIGH alone for 4 s, 2 s dark between");
}

void loop() {
  for (int i = 0; i < N; i++) {
    Serial.printf(">>> %s HIGH now\n", NAME[i]);
    digitalWrite(CAND[i], HIGH);
    delay(4000);
    digitalWrite(CAND[i], LOW);
    Serial.println("    (dark)");
    delay(2000);
  }
}
