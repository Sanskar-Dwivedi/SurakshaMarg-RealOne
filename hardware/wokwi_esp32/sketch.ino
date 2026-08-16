/*
 * GauKavach - bench governor, ESP32
 * ---------------------------------
 * Same rule set as the Uno sketch, plus the one thing an Uno physically
 * cannot do: a RAMPED burst envelope.
 *
 * Arduino tone() emits a hard-gated square wave. Our own spectrum analysis
 * (gaukavach spectrum) says that is the wrong waveform: the rectangular gate
 * splatters broadband switching energy into the audible band, so the device
 * clicks at every activation even though the carrier is ultrasonic. OSHA
 * documents exactly this failure mode.
 *
 * The ESP32's LEDC peripheral gives independent control of frequency and duty,
 * so the duty cycle can be ramped up and down with a raised-cosine profile.
 * That is the hardware expression of emitter.py's _raised_cosine_envelope().
 *
 * Honest scope, unchanged from the Uno sketch:
 *   - no calibrated microphone is attached, so this rig makes NO dB claim
 *   - duty ramping shapes the drive envelope; it is not a substitute for
 *     measuring the acoustic output of a real transducer
 *   - a 40 kHz ranging element is the wrong part (above the 35 kHz cattle
 *     audiogram endpoint) and stands in for the signal chain only
 *
 * Board: ESP32 Dev Module.
 *
 * The LEDC API changed between Arduino-ESP32 core 2.x and 3.x: ledcSetup() and
 * ledcAttachPin() were removed, and ledcWrite() now takes a PIN rather than a
 * channel. Wokwi ships core 3.x, most local Arduino IDE installs are still on
 * 2.x, so the two wrappers below pick the right one at compile time. Nothing
 * else in the sketch has to care.
 */

/* ---------------- pins ---------------- */
const int PIN_TRIG      = 13;
const int PIN_ECHO      = 39;   // VN. NOT 12: GPIO12 is a strapping pin (MTDI)
const int PIN_EMIT      = 25;   // LEDC output -> 220R -> transistor -> transducer

const int LED_PERMIT    = 26;   // green
const int LED_REFUSE    = 27;   // red
const int LED_ESCALATE  = 14;   // amber
const int LED_ARMED     = 2;    // on-board blue

const int BTN_PERSON    = 32;
const int BTN_NONTARGET = 33;
const int BTN_ESTOP     = 35;   // input-only pin, needs an external pull-up

/* Pin choices avoid the ESP32 strapping pins 0, 2, 5, 12 and 15, which are
 * sampled at reset. GPIO2 is the exception: it is the on-board LED, driven as
 * an output only, which is the standard and safe use of it. */
const int POT_GROUP     = 34;   // ADC1, input-only

/* ---------------- LEDC ---------------- */
const int      LEDC_CH   = 0;
const int      LEDC_RES  = 8;          // 8-bit duty, 0..255
const uint32_t CARRIER_HZ = 25000;     // inside the documented 22-30 kHz band
const uint8_t  DUTY_PEAK = 128;        // 50% = maximum drive for a square carrier
const uint16_t RAMP_MS   = 25;         // raised-cosine rise and fall

/* ------------- governor limits, mirroring evidence.py ------------- */
const uint8_t  MAX_GROUP         = 3;
const uint32_t MAX_ACTIVATION_MS = 6000;
const uint32_t MIN_SILENCE_MS    = 20000;
const uint32_t DAILY_BUDGET_MS   = 120000;
const uint32_t ESCALATE_AFTER_MS = 25000;
const uint8_t  MAX_ATTEMPTS      = 3;
/* Live demos cannot wait 20 s between bursts, so the long timers are divided
 * by this and the true values are printed at boot - the compression is stated,
 * not hidden. Set to 4, not 10: at 10x, escalation fires 2.5 s after detection,
 * which is quicker than you can reach for a button, so every veto you try to
 * demonstrate has already gone to amber. Verified in the simulator. */
const uint16_t DEMO_SPEED        = 4;

const float DESK_SCALE  = 2.8;    // cm on the bench per metre of field range
const float RANGE_MAX_M = 42.8;
const float LINE_M      = 12.0;

enum State { IDLE, TRACKING, EMITTING, COOLDOWN, ESCALATED, INHIBITED };
State state = IDLE;

uint32_t emitStartedAt = 0, lastEmissionEnd = 0, exposureUsedMs = 0;
uint32_t incidentStart = 0, lastBeat = 0, lastPrint = 0;
uint8_t  attempts = 0;
bool     doNotEmit = false, estopLatched = false, armedLed = false;

uint32_t scaled(uint32_t ms) { return ms / DEMO_SPEED; }

/* ---- LEDC portability shim: core 2.x and 3.x ----
 * ESP_ARDUINO_VERSION_MAJOR is undefined on very old cores, which the
 * preprocessor treats as 0, so the 2.x branch is the safe default. */
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
static inline void emitAttach()            { ledcAttach(PIN_EMIT, CARRIER_HZ, LEDC_RES); }
static inline void emitDuty(uint32_t duty) { ledcWrite(PIN_EMIT, duty); }
#else
static inline void emitAttach() {
  ledcSetup(LEDC_CH, CARRIER_HZ, LEDC_RES);
  ledcAttachPin(PIN_EMIT, LEDC_CH);
}
static inline void emitDuty(uint32_t duty) { ledcWrite(LEDC_CH, duty); }
#endif

void emitStop();

void setup() {
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(LED_PERMIT, OUTPUT);
  pinMode(LED_REFUSE, OUTPUT);
  pinMode(LED_ESCALATE, OUTPUT);
  pinMode(LED_ARMED, OUTPUT);
  pinMode(BTN_PERSON, INPUT_PULLUP);
  pinMode(BTN_NONTARGET, INPUT_PULLUP);
  pinMode(BTN_ESTOP, INPUT);        // GPIO35 has no internal pull-up: add 10k to 3V3

  emitAttach();
  emitDuty(0);

  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("GauKavach bench governor - ESP32");
  Serial.println("========================================");
  Serial.printf("carrier          %lu Hz, %d-bit duty, raised-cosine %d ms ramp\n",
                (unsigned long)CARRIER_HZ, LEDC_RES, RAMP_MS);
  Serial.printf("max activation   %.1f s   (demo %.1f s)\n",
                MAX_ACTIVATION_MS / 1000.0, scaled(MAX_ACTIVATION_MS) / 1000.0);
  Serial.printf("quiet period     %.1f s   (demo %.1f s)\n",
                MIN_SILENCE_MS / 1000.0, scaled(MIN_SILENCE_MS) / 1000.0);
  Serial.printf("daily budget     %.1f s   (demo %.1f s)\n",
                DAILY_BUDGET_MS / 1000.0, scaled(DAILY_BUDGET_MS) / 1000.0);
  Serial.printf("max group        %d\n", MAX_GROUP);
  Serial.println("timers compressed for the demo; shipped values shown first");
  Serial.println("NO calibrated mic attached: this rig makes no dB claim");
  Serial.println();
}

/* Raised-cosine rise. Blocking for RAMP_MS, which is acceptable here because
 * nothing else needs servicing during a 25 ms envelope, and it keeps the shape
 * identical to emitter.py rather than approximated by a scheduler. */
void emitStart() {
  for (uint16_t t = 0; t <= RAMP_MS; t++) {
    float x = (float)t / RAMP_MS;                 // 0..1
    float e = 0.5f * (1.0f - cosf(PI * x));       // raised cosine
    emitDuty((uint32_t)(DUTY_PEAK * e));
    delay(1);
  }
  emitDuty(DUTY_PEAK);
}

void emitFade() {
  for (uint16_t t = 0; t <= RAMP_MS; t++) {
    float x = (float)t / RAMP_MS;
    float e = 0.5f * (1.0f + cosf(PI * x));       // mirror of the rise
    emitDuty((uint32_t)(DUTY_PEAK * e));
    delay(1);
  }
  emitDuty(0);
}

void emitStop(const char *why) {
  if (state == EMITTING) {
    emitFade();
    uint32_t dur = millis() - emitStartedAt;
    exposureUsedMs += dur;
    lastEmissionEnd = millis();
    Serial.printf("  emission ended after %lu ms - %s\n", (unsigned long)dur, why);
    if (exposureUsedMs >= scaled(DAILY_BUDGET_MS)) {
      doNotEmit = true;
      Serial.println("  DAILY EXPOSURE BUDGET EXHAUSTED -> do-not-emit latched");
    }
  }
  emitDuty(0);
}

float readRangeCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 25000UL);
  if (us == 0) return -1.0f;            // no echo != "animal is adjacent"
  return us / 58.0f;
}

void leds(bool p, bool r, bool e) {
  digitalWrite(LED_PERMIT, p);
  digitalWrite(LED_REFUSE, r);
  digitalWrite(LED_ESCALATE, e);
}

void loop() {
  uint32_t now = millis();

  if (digitalRead(BTN_ESTOP) == LOW) estopLatched = true;
  if (estopLatched) {
    emitStop("E-STOP");
    state = INHIBITED;
    leds(false, true, false);
    digitalWrite(LED_ARMED, LOW);
    if (now - lastPrint > 1000) {
      Serial.println("E-STOP LATCHED - emitter dead until reset");
      lastPrint = now;
    }
    return;
  }

  if (now - lastBeat > 900) { lastBeat = now; armedLed = !armedLed; digitalWrite(LED_ARMED, armedLed); }

  float cm = readRangeCm();
  bool  seen = (cm > 0 && cm < 200);
  float metres = seen ? (cm / DESK_SCALE) : 999.0f;
  bool  person    = (digitalRead(BTN_PERSON) == LOW);
  bool  nonTarget = (digitalRead(BTN_NONTARGET) == LOW);
  uint8_t group   = map(analogRead(POT_GROUP), 0, 4095, 1, 8);

  if (state == EMITTING && (now - emitStartedAt) >= scaled(MAX_ACTIVATION_MS)) {
    emitStop("WATCHDOG max activation");
    state = COOLDOWN;
  }

  if (!seen) {
    if (state == EMITTING) emitStop("target lost");
    if (state != INHIBITED) state = IDLE;
    attempts = 0; incidentStart = 0;
    leds(false, false, false);
    return;
  }

  if (incidentStart == 0) {
    incidentStart = now;
    Serial.printf("DETECTION at %.1f m (scaled)\n", metres);
  }

  const char *deny = nullptr;
  if (doNotEmit)                     deny = "animal is on the do-not-emit list";
  else if (person)                   deny = "a person is inside the exposure cone";
  else if (nonTarget)                deny = "a non-target species is inside the cone";
  else if (group > MAX_GROUP)        deny = "group large enough that a startle could cascade";
  else if (metres > RANGE_MAX_M)     deny = "beyond the acoustic envelope";
  else if (metres <= LINE_M)         deny = "already at the carriageway - fleeing would cross it";
  else if (state == COOLDOWN &&
           (now - lastEmissionEnd) < scaled(MIN_SILENCE_MS))
                                     deny = "enforced quiet period";

  bool timedOut = (now - incidentStart) > scaled(ESCALATE_AFTER_MS);
  if (state != EMITTING && (attempts >= MAX_ATTEMPTS || timedOut)) {
    if (state != ESCALATED) {
      emitStop("escalating");
      Serial.println("  ESCALATED -> traffic warning + human dispatch");
      Serial.println("  (acoustic cues are not stock-proof; the system stops)");
      state = ESCALATED;
    }
    leds(false, false, true);
    return;
  }

  if (deny != nullptr) {
    if (state == EMITTING) emitStop(deny);
    state = (state == COOLDOWN) ? COOLDOWN : TRACKING;
    leds(false, true, false);
    if (now - lastPrint > 800) {
      Serial.printf("REFUSED @ %.1f m  group=%d  -> %s\n", metres, group, deny);
      lastPrint = now;
    }
    return;
  }

  if (state != EMITTING) {
    state = EMITTING;
    emitStartedAt = millis();
    attempts++;
    Serial.printf("PERMITTED @ %.1f m  attempt %d/%d  carrier %.1f kHz  ramped %d ms\n",
                  metres, attempts, MAX_ATTEMPTS, CARRIER_HZ / 1000.0, RAMP_MS);
    Serial.printf("  budget used %lu / %lu ms\n",
                  (unsigned long)exposureUsedMs, (unsigned long)scaled(DAILY_BUDGET_MS));
    emitStart();
  }
  leds(true, false, false);
}
