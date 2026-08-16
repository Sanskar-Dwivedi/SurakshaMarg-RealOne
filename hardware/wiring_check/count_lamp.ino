/*
 * count_lamp - each pin announces itself by how many times it blinks.
 *
 * Asking someone to count windows in a cycle is asking them to hold a clock in
 * their head while watching a board. Asking "how many times did it blink" is
 * something an eye does by itself. Same information, no counting of gaps.
 *
 *   GPIO26 -> 1 blink
 *   GPIO27 -> 2 blinks
 *   GPIO14 -> 3 blinks
 *
 * The on-board LED on GPIO2 is held LOW throughout, so nothing on the module
 * itself can be mistaken for a breadboard lamp.
 */

const int CAND[]   = {26, 27, 14};
const char *NAME[] = {"GPIO26", "GPIO27", "GPIO14"};
const int N = 3;
const int ONBOARD = 2;

void setup() {
  Serial.begin(115200);
  delay(400);
  pinMode(ONBOARD, OUTPUT);
  digitalWrite(ONBOARD, LOW);
  for (int i = 0; i < N; i++) { pinMode(CAND[i], OUTPUT); digitalWrite(CAND[i], LOW); }
  Serial.println();
  Serial.println("count_lamp - GPIO26 blinks once, GPIO27 twice, GPIO14 three times");
  Serial.println("on-board LED stays off; count the blinks, not the order");
}

void loop() {
  for (int i = 0; i < N; i++) {
    Serial.printf(">>> %s blinking %d time(s)\n", NAME[i], i + 1);
    for (int b = 0; b <= i; b++) {
      digitalWrite(CAND[i], HIGH);
      delay(450);
      digitalWrite(CAND[i], LOW);
      delay(450);
    }
    delay(2500);                 // a long gap so the groups never run together
  }
  Serial.println("--- repeating ---");
  delay(1500);
}
