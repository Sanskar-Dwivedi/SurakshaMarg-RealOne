/*
 * GauKavach - wiring check
 * ------------------------
 * Not the product. A diagnostic you flash ONCE after building the rig, to find
 * out which parts of it are actually connected, before the governor's logic
 * gets a chance to hide the answer.
 *
 * The governor is deliberately hard to read when something is miswired: it is
 * a state machine full of refusals, so a floating input or a dead sensor just
 * looks like a refusal, and every refusal looks deliberate. This sketch has no
 * logic at all. It prints what each pin reads, once every 500 ms, and walks the
 * outputs in a fixed order so you can watch them.
 *
 * Pin map is identical to gaukavach_esp32.ino. A test enforces that.
 *
 * WHAT TO LOOK FOR
 *   ESTOP    should read HIGH when the button is up. If it reads LOW with
 *            nothing pressed, the 10k pull-up to 3V3 is missing, is on the
 *            wrong node, or the button is wired with two legs on the same
 *            side of the switch (which is a permanent short to ground).
 *   PERSON   should read HIGH at rest; these two use the internal pull-up, so
 *   NONTGT   HIGH here proves nothing about your wiring - LOW when pressed does.
 *   POT      should sweep 0 -> 4095 as you turn the knob. Stuck at 0 or 4095
 *            means an outer leg is not connected. Jittering by a few counts is
 *            normal and the real firmware filters it.
 *   ECHO     should track your hand. -1 means no echo came back at all: check
 *            VCC is on VIN/5V, and that TRIG and ECHO are not swapped.
 *   LEDs     each lights for 600 ms in turn: green, red, amber. One that never
 *            lights is usually reversed, not broken.
 */

const int PIN_TRIG      = 13;
const int PIN_ECHO      = 39;   // VN
const int PIN_EMIT      = 25;

const int LED_PERMIT    = 26;   // green
const int LED_REFUSE    = 27;   // red
const int LED_ESCALATE  = 14;   // amber
const int LED_ARMED     = 2;    // on-board blue

const int BTN_PERSON    = 32;
const int BTN_NONTARGET = 33;
const int BTN_ESTOP     = 35;   // input-only, needs the external 10k

const int POT_GROUP     = 34;

const int LEDS[3] = {LED_PERMIT, LED_REFUSE, LED_ESCALATE};
const char *LED_NAME[3] = {"green", "red", "amber"};

// Walking the LEDs proves none of them are reversed, but it is also the only
// thing on this rig that moves, so it reads as "the demo" to anyone watching.
// Turn it off once you have seen all three light.
const bool WALK_LEDS = false;

uint8_t step = 0;
uint32_t lastStep = 0;

void setup() {
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  for (int i = 0; i < 3; i++) pinMode(LEDS[i], OUTPUT);
  pinMode(LED_ARMED, OUTPUT);
  pinMode(BTN_PERSON, INPUT_PULLUP);
  pinMode(BTN_NONTARGET, INPUT_PULLUP);
  pinMode(BTN_ESTOP, INPUT);          // no internal pull-up exists on GPIO35

  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("GauKavach WIRING CHECK - not the governor, just the pins");
  Serial.println("=========================================================");
  Serial.println("ESTOP must read HIGH at rest. LOW at rest = missing 10k pull-up.");
  Serial.println("POT should sweep 0..4095. ECHO -1 means no echo returned.");
  Serial.println();
}

float pingCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 25000UL);
  return us == 0 ? -1.0f : us / 58.0f;
}

void loop() {
  uint32_t now = millis();

  // walk the outputs so a reversed LED is visible rather than inferred
  if (now - lastStep > 600) {
    lastStep = now;
    step = (step + 1) % 4;
    for (int i = 0; i < 3; i++) digitalWrite(LEDS[i], WALK_LEDS && step == i);
    digitalWrite(LED_ARMED, WALK_LEDS && step == 3);
    if (WALK_LEDS && step == 3) { tone(PIN_EMIT, 2000, 120); }
  }

  float cm = pingCm();
  int raw = analogRead(POT_GROUP);

  Serial.printf("ESTOP=%-4s PERSON=%-4s NONTGT=%-4s POT=%4d ECHO=%6.1f cm  LED=%s\n",
                digitalRead(BTN_ESTOP) ? "HIGH" : "LOW",
                digitalRead(BTN_PERSON) ? "HIGH" : "LOW",
                digitalRead(BTN_NONTARGET) ? "HIGH" : "LOW",
                raw, cm,
                step < 3 ? LED_NAME[step] : "armed+beep");
  delay(500);
}
