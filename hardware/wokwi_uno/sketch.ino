/*
 * GauKavach - bench governor, Arduino Uno / Tinkercad Circuits
 * ------------------------------------------------------------
 * A hardware mirror of src/gaukavach/welfare.py. The point of this rig is NOT
 * to deter an animal - it cannot, and it is not trying to. The point is that
 * every veto in the software governor is enforced again, independently, by a
 * microcontroller that does not trust the host.
 *
 * That is the demo: two layers that must BOTH agree before a transducer is
 * energised, and either of which can stop it alone.
 *
 * WHAT THIS RIG HONESTLY DEMONSTRATES
 *   - distance gating and the out-of-range escalation path
 *   - absolute vetoes: person present, non-target animal present
 *   - herd-size veto above 3 grouped animals
 *   - the 6 s maximum-activation watchdog
 *   - the enforced quiet period between exposures
 *   - the per-animal daily exposure budget and its do-not-emit latch
 *   - a hard E-stop that cuts the emitter independently of all logic
 *
 * WHAT IT DOES NOT DEMONSTRATE
 *   - any acoustic performance whatsoever. Arduino tone() is a hard-gated
 *     square wave, which is exactly the waveform our own spectrum analysis
 *     says NOT to radiate (it splatters broadband energy into the audible
 *     band). The ESP32 sketch in ../wokwi_esp32 ramps the envelope properly.
 *   - any decibel level. Without a calibrated ultrasonic microphone, any SPL
 *     claim about this rig is fabricated.
 *   - anything about cattle. If your transducer is a 40 kHz ranging element,
 *     note that 40 kHz is ABOVE the 35 kHz cattle audiogram endpoint, so it is
 *     the wrong part for deterrence and is standing in for the signal chain.
 *
 * Distances are desk-scaled: DESK_SCALE cm on the bench represents 1 m of
 * field range, so a 1 m desk covers the full ~35 m approach.
 */

/* ------------- distance source -------------
 * Set to 1 to replace the HC-SR04 with a second potentiometer on A1.
 *
 * Worth considering for a live demo. A knob you turn is far easier to drive in
 * front of an audience than a sensor slider, it removes the fiddliest part of
 * the build, and the governor cannot tell the difference - it only ever sees a
 * distance in metres. The trade is honesty about what you are showing: with
 * this set, say "the distance input is a knob", because it is.
 */
#define DISTANCE_FROM_POT 0

/* ---------------- pins ---------------- */
const uint8_t PIN_TRIG      = 9;   // HC-SR04 trigger
const uint8_t PIN_ECHO      = 10;  // HC-SR04 echo
const uint8_t PIN_EMIT      = 11;  // emitter drive (via 220R + transistor)

const uint8_t LED_PERMIT    = 5;   // green
const uint8_t LED_REFUSE    = 6;   // red
const uint8_t LED_ESCALATE  = 7;   // amber
const uint8_t LED_ARMED     = 8;   // blue heartbeat

const uint8_t BTN_PERSON    = 2;   // person in the exposure cone
const uint8_t BTN_NONTARGET = 3;   // dog / goat / horse in the cone
const uint8_t BTN_ESTOP     = 4;   // latching emergency stop
const uint8_t POT_GROUP     = A0;  // how many animals are grouped
const uint8_t POT_DISTANCE  = A1;  // only used when DISTANCE_FROM_POT is 1

/* ------------- governor limits -------------
 * These mirror src/gaukavach/evidence.py. Keep them in sync by hand, or the
 * hardware and the software stop being two views of the same rule set.
 */
const uint16_t CARRIER_HZ         = 25000;  // inside the documented 22-30 kHz band
const uint8_t  MAX_GROUP          = 3;      // max_herd_size_for_emission
const uint32_t MAX_ACTIVATION_MS  = 6000;   // max_activation_s
const uint32_t MIN_SILENCE_MS     = 20000;  // min_silence_s
const uint32_t DAILY_BUDGET_MS    = 120000; // daily_exposure_budget_s
const uint32_t ESCALATE_AFTER_MS  = 25000;  // escalation_timeout_s
const uint8_t  MAX_ATTEMPTS       = 3;

/* Live demos cannot wait 20 s between bursts, so the long timers are divided
 * by this and the true values are printed at boot - the compression is stated,
 * not hidden. Set to 4, not 10: at 10x, escalation fires 2.5 s after detection,
 * which is quicker than you can reach for a button, so every veto you try to
 * demonstrate has already gone to amber. Verified in the simulator. */
const uint16_t DEMO_SPEED = 4;

/* Bench geometry */
const float DESK_SCALE   = 2.8;   // cm on the desk per metre of field range
const float RANGE_MAX_M  = 42.8;  // acoustic envelope at 22 kHz, from acoustics.py
const float LINE_M       = 12.0;  // carriageway edge

enum State { IDLE, TRACKING, EMITTING, COOLDOWN, ESCALATED, INHIBITED };
State state = IDLE;

uint32_t emitStartedAt = 0;
uint32_t lastEmissionEnd = 0;
uint32_t exposureUsedMs = 0;
uint32_t incidentStart = 0;
uint8_t  attempts = 0;
bool     doNotEmit = false;
bool     estopLatched = false;
uint32_t lastBeat = 0;
uint32_t lastPrint = 0;

uint32_t scaled(uint32_t ms) { return ms / DEMO_SPEED; }

void setup() {
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_EMIT, OUTPUT);
  pinMode(LED_PERMIT, OUTPUT);
  pinMode(LED_REFUSE, OUTPUT);
  pinMode(LED_ESCALATE, OUTPUT);
  pinMode(LED_ARMED, OUTPUT);
  pinMode(BTN_PERSON, INPUT_PULLUP);
  pinMode(BTN_NONTARGET, INPUT_PULLUP);
  pinMode(BTN_ESTOP, INPUT_PULLUP);

  Serial.begin(9600);
  Serial.println(F("GauKavach bench governor"));
  Serial.println(F("========================================"));
  Serial.print(F("carrier            ")); Serial.print(CARRIER_HZ); Serial.println(F(" Hz"));
  Serial.print(F("max activation     ")); Serial.print(MAX_ACTIVATION_MS / 1000.0, 1);
  Serial.print(F(" s  (demo ")); Serial.print(scaled(MAX_ACTIVATION_MS) / 1000.0, 1); Serial.println(F(" s)"));
  Serial.print(F("quiet period       ")); Serial.print(MIN_SILENCE_MS / 1000.0, 1);
  Serial.print(F(" s  (demo ")); Serial.print(scaled(MIN_SILENCE_MS) / 1000.0, 1); Serial.println(F(" s)"));
  Serial.print(F("daily budget       ")); Serial.print(DAILY_BUDGET_MS / 1000.0, 1);
  Serial.print(F(" s  (demo ")); Serial.print(scaled(DAILY_BUDGET_MS) / 1000.0, 1); Serial.println(F(" s)"));
  Serial.print(F("max group          ")); Serial.println(MAX_GROUP);
  Serial.println(F("timers compressed for the demo; shipped values shown first"));
  Serial.println(F("NO calibrated mic attached: this rig makes no dB claim"));
#if DISTANCE_FROM_POT
  Serial.println(F("distance source   POT on A1 (no HC-SR04 fitted)"));
#else
  Serial.println(F("distance source   HC-SR04 on D9/D10"));
#endif
  Serial.println();
}

/* Range in cm. Returns -1 when nothing is detected, so a missing echo never
 * reads as "animal is right here" - that would be the dangerous failure
 * direction, and it is the one a naive implementation gets wrong. */
float readRangeCm() {
#if DISTANCE_FROM_POT
  /* Knob fully anti-clockwise = far away, fully clockwise = at the road edge.
   * Above 190 cm we report "nothing there" so the idle path still gets tested. */
  int raw = analogRead(POT_DISTANCE);
  float cm = 200.0 - (raw / 1023.0) * 190.0;
  return (cm > 190.0) ? -1.0 : cm;
#else
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 25000UL);
  if (us == 0) return -1.0;
  return us / 58.0;
#endif
}

void allLeds(bool permit, bool refuse, bool esc) {
  digitalWrite(LED_PERMIT, permit);
  digitalWrite(LED_REFUSE, refuse);
  digitalWrite(LED_ESCALATE, esc);
}

void stopEmitting(const __FlashStringHelper *why) {
  noTone(PIN_EMIT);
  digitalWrite(PIN_EMIT, LOW);
  if (state == EMITTING) {
    uint32_t dur = millis() - emitStartedAt;
    exposureUsedMs += dur;
    lastEmissionEnd = millis();
    Serial.print(F("  emission ended after "));
    Serial.print(dur); Serial.print(F(" ms - "));
    Serial.println(why);
    if (exposureUsedMs >= scaled(DAILY_BUDGET_MS)) {
      doNotEmit = true;
      Serial.println(F("  DAILY EXPOSURE BUDGET EXHAUSTED -> do-not-emit latched"));
    }
  }
}

void loop() {
  uint32_t now = millis();

  /* ---- E-stop is checked first and latches. Nothing clears it but a reset. */
  if (digitalRead(BTN_ESTOP) == LOW) estopLatched = true;
  if (estopLatched) {
    stopEmitting(F("E-STOP"));
    state = INHIBITED;
    allLeds(false, true, false);
    digitalWrite(LED_ARMED, LOW);
    if (now - lastPrint > 1000) {
      Serial.println(F("E-STOP LATCHED - emitter dead until reset"));
      lastPrint = now;
    }
    return;
  }

  /* armed heartbeat */
  if (now - lastBeat > 900) { lastBeat = now; digitalWrite(LED_ARMED, !digitalRead(LED_ARMED)); }

  /* ---- perception stand-ins ---- */
  float cm = readRangeCm();
  bool  seen = (cm > 0 && cm < 200);
  float metres = seen ? (cm / DESK_SCALE) : 999.0;
  bool  person    = (digitalRead(BTN_PERSON) == LOW);
  bool  nonTarget = (digitalRead(BTN_NONTARGET) == LOW);
  uint8_t group   = map(analogRead(POT_GROUP), 0, 1023, 1, 8);

  /* ---- watchdog: hard stop regardless of anything else ---- */
  if (state == EMITTING && (now - emitStartedAt) >= scaled(MAX_ACTIVATION_MS)) {
    stopEmitting(F("WATCHDOG max activation"));
    state = COOLDOWN;
  }

  if (!seen) {
    if (state == EMITTING) stopEmitting(F("target lost"));
    if (state != INHIBITED) state = IDLE;
    attempts = 0; incidentStart = 0;
    allLeds(false, false, false);
    return;
  }

  if (incidentStart == 0) {
    incidentStart = now;
    Serial.print(F("DETECTION at ")); Serial.print(metres, 1); Serial.println(F(" m (scaled)"));
  }

  /* ---- adjudicate. Order mirrors welfare.Governor.request() ---- */
  const __FlashStringHelper *deny = NULL;

  if (doNotEmit)                       deny = F("animal is on the do-not-emit list");
  else if (person)                     deny = F("a person is inside the exposure cone");
  else if (nonTarget)                  deny = F("a non-target species is inside the cone");
  else if (group > MAX_GROUP)          deny = F("group large enough that a startle could cascade");
  else if (metres > RANGE_MAX_M)       deny = F("beyond the acoustic envelope");
  else if (metres <= LINE_M)           deny = F("already at the carriageway - fleeing would cross it");
  else if (attempts >= MAX_ATTEMPTS)   deny = F("attempt cap reached");
  else if (state == COOLDOWN &&
           (now - lastEmissionEnd) < scaled(MIN_SILENCE_MS))
                                       deny = F("enforced quiet period");

  /* escalation: give up rather than get louder */
  bool timedOut = (now - incidentStart) > scaled(ESCALATE_AFTER_MS);
  if (state != EMITTING && (attempts >= MAX_ATTEMPTS || timedOut)) {
    if (state != ESCALATED) {
      stopEmitting(F("escalating"));
      Serial.println(F("  ESCALATED -> traffic warning + human dispatch"));
      Serial.println(F("  (acoustic cues are not stock-proof; the system stops)"));
      state = ESCALATED;
    }
    allLeds(false, false, true);
    return;
  }

  if (deny != NULL) {
    if (state == EMITTING) stopEmitting(deny);
    state = (state == COOLDOWN) ? COOLDOWN : TRACKING;
    allLeds(false, true, false);
    if (now - lastPrint > 800) {
      Serial.print(F("REFUSED @ ")); Serial.print(metres, 1);
      Serial.print(F(" m  group=")); Serial.print(group);
      Serial.print(F("  -> ")); Serial.println(deny);
      lastPrint = now;
    }
    return;
  }

  /* ---- permitted ---- */
  if (state != EMITTING) {
    state = EMITTING;
    emitStartedAt = now;
    attempts++;
    tone(PIN_EMIT, CARRIER_HZ);
    Serial.print(F("PERMITTED @ ")); Serial.print(metres, 1);
    Serial.print(F(" m  attempt ")); Serial.print(attempts);
    Serial.print(F("/")); Serial.print(MAX_ATTEMPTS);
    Serial.print(F("  carrier ")); Serial.print(CARRIER_HZ / 1000.0, 1);
    Serial.println(F(" kHz"));
    Serial.print(F("  budget used ")); Serial.print(exposureUsedMs);
    Serial.print(F(" / ")); Serial.print(scaled(DAILY_BUDGET_MS)); Serial.println(F(" ms"));
  }
  allLeds(true, false, false);
}
