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
 * ARDUINO IDE SETTINGS
 *   Tools > Board            ESP32 Arduino > ESP32 Dev Module
 *   Tools > Upload Speed     921600  (drop to 115200 if uploads fail)
 *   Tools > Port             whatever COM port appears when the board is plugged in
 *   No libraries to install: everything used here ships with the ESP32 core.
 * If the port never appears, it is the CP2102 / CH340 USB-serial driver, not
 * the sketch. If upload stalls at "Connecting...", hold BOOT while it starts.
 *
 * The LEDC API changed between Arduino-ESP32 core 2.x and 3.x: ledcSetup() and
 * ledcAttachPin() were removed, and ledcWrite() now takes a PIN rather than a
 * channel. Both Wokwi and this machine's IDE are on core 3.x; the wrappers
 * below still cover 2.x so the sketch survives an older install elsewhere.
 *
 * REAL HARDWARE vs THE SIMULATOR
 * A simulator hands you a clean sensor reading, a clean ADC and a bounce-free
 * button. A breadboard hands you none of those, and each one has a specific
 * way of ruining a live demo, so each is conditioned below: see 'input
 * conditioning'. The governor logic itself is untouched - the whole point is
 * that the rules are the same everywhere they are stated.
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

/* ------------- what is actually fitted -------------
 * Set to 0 when no potentiometer is on the board.
 *
 * This matters more than it looks. GPIO34 is input-only with no internal pull
 * anywhere in the silicon, so an unfitted pot does not read zero - it floats,
 * and the governor sees a herd size that wanders between 1 and 8 on its own.
 * Every refusal it then produces is real, correctly reasoned, and based on a
 * number nobody chose. That is the worst failure this rig can have, because
 * it looks exactly like the system working.
 *
 * With HAVE_POT 0 the pin is never read. Group size comes from the serial
 * console instead: type g5 and press enter. Say so when you demo it.
 */
#define HAVE_POT 0

/* Set to 0 when the E-stop button is not fitted, or is wired in a way that
 * reads permanently closed. Two legs on the same side of a tactile switch are
 * already joined inside it, so that mistake grounds the pin forever and the
 * governor is inhibited from the moment it boots.
 *
 * Turning this off does NOT remove the emergency stop - the console 'e'
 * command still latches it, and every other veto is untouched. It removes a
 * pin that is lying. But the rig must then never be described as having a
 * wired safety interlock, so it says so at boot, every boot. */
#define HAVE_ESTOP 0

/* Set to 0 when no HC-SR04 is fitted or it returns no echo. Distance then
 * comes from the console: type d80 for 80 cm. The governor cannot tell the
 * difference, because it only ever sees a distance - which is exactly why you
 * have to say out loud that the distance input is being typed.
 *
 * Now 1: on 5 V from VIN through a rail, with the 1k/2k divider restored, the
 * module answers 344 of 355 pings across 16-105 cm. It had been silent on 3.3 V
 * while still holding ECHO low - powered enough to drive the line, not enough
 * to fire the transmitter. Distance is sensed again; only the group size and
 * the emergency stop remain typed. */
#define HAVE_SENSOR 1

/* Set to 1 when only two of the three status LEDs work. Measured on this
 * board: GPIO26 and GPIO14 drive lamps, GPIO27 drives nothing. Rather than
 * lose a state, escalation blinks the stop lamp instead of owning a colour.
 * The reference build is still three lamps; this is one rig's reality. */
#define TWO_LAMP_MODE 1

/* Set to 1 when exactly one status LED works. Measured on this board: GPIO14
 * lights, GPIO26 and GPIO27 do not.
 *
 * One lamp still carries three states, by rate rather than by colour: solid
 * while emitting, a slow pulse while refusing, a fast flutter once it has
 * given up and asked for a human. Dark means nothing is there.
 *
 * Solid-for-emitting is the right way round. This lamp is off almost all of
 * the time, and that is the argument, not a limitation of it. */
#define ONE_LAMP_MODE 0
#if TWO_LAMP_MODE || ONE_LAMP_MODE
/* Measured with count_lamp, each pin blinking its own number: the red lamp
 * answers on GPIO27 and the green on GPIO14. GPIO26 has nothing attached.
 *
 * Worth recording why that was not obvious. The first mapping was taken while
 * GPIO26 and GPIO27 were shorted together in one breadboard column, so driving
 * either lit the single LED that existed, and GPIO26 looked like the red lamp.
 * Once the short was fixed the reading was stale, and every later test drove a
 * pin with nothing on it. Measurements taken through a fault do not survive
 * the fix. */
const int LAMP_GO   = 14;      // green: permitted
const int LAMP_STOP = 27;      // red: refused, and blinking for escalated
const int LAMP_ONE  = 14;
#endif

/* A third lamp for one refusal in particular: the target is out of acoustic
 * range. Set to 0 if nothing is wired to GPIO26.
 *
 * Worth its own light because it is the one refusal that is about geometry
 * rather than about the animal. Lit, the three lamps read as a map - red too
 * close, green in range, this one too far - so moving a hand through the
 * detection cone tells the whole spatial story without a word of narration.
 *
 * The other four refusals share the red lamp. They are about who or what is
 * there, not where. */
#define FAR_LAMP_MODE 1
const int LAMP_FAR = 26;
bool farRefusal = false;

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
 * demonstrate has already gone to amber. Verified in the simulator.
 *
 * Lowered from 4 to 2 after watching someone use it. Compression shortens the
 * permitted burst as much as the waiting, and the burst is the only part that
 * is visible - at 4x it lasted 1.5 s and the rig looked like it only ever
 * refused. At 2x it is three seconds, which reads. The waits grow too, but
 * nobody is watching those. */
const uint16_t DEMO_SPEED        = 2;

/* One centimetre on the bench is one metre of field range. Chosen for the
 * demo rather than derived: at the old 2.8 the permit band sat between 34 and
 * 120 cm, which is a metre of desk and further than anyone naturally holds a
 * hand, so the rig looked like it only ever refused. At 1.0 the whole thing
 * fits inside arm's reach and the arithmetic is something you can say out loud
 * while it happens. */
const float DESK_SCALE  = 1.0;    // cm on the bench per metre of field range

/* Beyond this the bench sees nothing at all, rather than seeing something and
 * refusing it for being out of range. Without it a wall across the room is a
 * permanent detection the governor keeps declining, and the log fills with
 * refusals nobody caused. */
const float SEEN_MAX_CM = 70.0;
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
float pingOnceCm();
void selfCheck();
void consoleHelp();
void consoleTick();
void consoleRun(char *, uint8_t);

/* ---------------- input conditioning ----------------
 *
 * Three noise sources, three specific demo failures:
 *
 *   button bounce   -> one glitch on a jumper latches the E-stop and the
 *                      emitter is dead for the rest of the presentation
 *   ADC noise       -> ESP32 ADC1 wanders by tens of counts while nothing
 *                      moves; the group-size threshold is an integer boundary,
 *                      so a still potentiometer flips PERMITTED / REFUSED
 *   sonar outliers  -> a real HC-SR04 throws a bad ping regularly, off soft
 *                      surfaces or while the previous burst is still ringing;
 *                      one of those reads as 'target lost' and resets the run
 *
 * None of this changes a single governor rule. It only stops the inputs from
 * lying to the rules.
 */

// A pin must agree with itself on this many consecutive passes to be believed.
const uint8_t DEBOUNCE_PASSES = 4;
const uint8_t GROUP_PASSES    = 3;
const uint8_t ADC_SAMPLES     = 16;
const uint8_t PING_GAP_MS     = 10;   // let the previous burst die down
const uint8_t CONSOLE_IDLE_MS = 80;   // dispatch a command with no terminator

const uint8_t B_PERSON = 0, B_NONTARGET = 1, B_ESTOP = 2, B_COUNT = 3;
int     btnPin[B_COUNT];
bool    btnStable[B_COUNT]    = {false, false, false};
bool    btnCandidate[B_COUNT] = {false, false, false};
uint8_t btnAgree[B_COUNT]     = {0, 0, 0};

bool pressed(uint8_t i) {
  bool raw = (digitalRead(btnPin[i]) == LOW);      // press-to-ground
  if (raw != btnCandidate[i]) { btnCandidate[i] = raw; btnAgree[i] = 0; }
  else if (btnAgree[i] < DEBOUNCE_PASSES) { btnAgree[i]++; }
  if (btnAgree[i] >= DEBOUNCE_PASSES) btnStable[i] = btnCandidate[i];
  return btnStable[i];
}

uint8_t groupStable = 1;
uint8_t groupTyped  = 1;        // used when no pot is fitted

uint8_t readGroup() {
#if !HAVE_POT
  return groupTyped;
#else
  uint32_t acc = 0;
  for (uint8_t i = 0; i < ADC_SAMPLES; i++) acc += analogRead(POT_GROUP);
  long    span = map((long)(acc / ADC_SAMPLES), 0L, 4095L, 1L, 8L);
  uint8_t want = (uint8_t)constrain(span, 1L, 8L);

  static uint8_t candidate = 1, agree = 0;
  if (want != candidate) { candidate = want; agree = 0; }
  else if (agree < GROUP_PASSES) { agree++; }
  if (agree >= GROUP_PASSES) groupStable = candidate;
  return groupStable;
#endif
}

/* ---------------- serial console ----------------
 *
 * Every physical input has a keyboard equivalent, for two reasons. A rig gets
 * built with parts that did not arrive, and a rig gets demonstrated in a room
 * where a jumper has shaken loose. Neither should cost you the argument, and
 * the argument is the refusals.
 *
 * Typing a veto is not the same claim as pressing one, so the console says
 * which it was in the log. Do not narrate a typed veto as a wired one.
 */
bool  typedPerson = false, typedNonTarget = false;
float simDistanceCm = 999.0f;   // used when no sensor is fitted

void consoleHelp() {
  Serial.println("console: g1..g8 group size | p person veto | n dog/goat veto");
  Serial.println("         e e-stop | r clear latches | ? this help");
#if !HAVE_SENSOR
  Serial.println("         d0..d400 distance in cm, e.g. d80 -> permitted");
#endif
#if !HAVE_POT
  Serial.println("         no pot fitted, so group size comes from g1..g8");
#endif
}

void consoleRun(char *line, uint8_t len) {
  char cmd = line[0];
  long arg = (len > 1) ? atol(line + 1) : -1;

  if (cmd == 'g') {
    if (arg >= 1 && arg <= 8) {
      groupTyped = (uint8_t)arg;
      Serial.printf("console: group size set to %u\n", groupTyped);
    } else {
      Serial.println("console: group size must be 1 to 8, e.g. g5");
    }
  } else if (cmd == 'd') {
    if (arg >= 0 && arg <= 400) {
      simDistanceCm = (float)arg;
      Serial.printf("console: distance set to %ld cm (%.1f m scaled)\n",
                    arg, arg / DESK_SCALE);
    } else {
      Serial.println("console: distance must be 0 to 400 cm, e.g. d80");
    }
  } else if (cmd == 'p') {
    typedPerson = !typedPerson;
    Serial.printf("console: PERSON veto %s (typed, not wired)\n",
                  typedPerson ? "on" : "off");
  } else if (cmd == 'n') {
    typedNonTarget = !typedNonTarget;
    Serial.printf("console: DOG/GOAT veto %s (typed, not wired)\n",
                  typedNonTarget ? "on" : "off");
  } else if (cmd == 'e') {
    estopLatched = true;
    Serial.println("console: E-STOP asserted");
  } else if (cmd == 'r') {
    /* Clear the typed vetoes too.
     *
     * They are toggles, so anything driving this console - a person or the web
     * page - has no way to read their state, only to flip them. A reset that
     * leaves them set means the driver's model and the board disagree from the
     * first command onward, and every later toggle stays inverted. Reset has
     * to mean reset, or it is just another source of drift. */
    estopLatched = false;
    doNotEmit = false;
    typedPerson = false;
    typedNonTarget = false;
    exposureUsedMs = 0;
    state = IDLE;
    attempts = 0;
    incidentStart = 0;
    Serial.println("console: latches cleared");
  } else if (cmd == '?') {
    consoleHelp();
  } else {
    Serial.printf("console: unknown command '%s', try ?\n", line);
  }
}

void consoleTick() {
  /* Two ways a command gets here, because the Serial Monitor has a line-ending
   * dropdown and it is not the operator's job to know about it.
   *
   * Set to "New Line" it sends p\n and the newline dispatches. Set to "No Line
   * Ending" it sends a bare p and nothing follows, so a parser that waits for a
   * terminator waits forever and the console looks broken. That is a real
   * regression I shipped: character-by-character parsing handled the bare p,
   * line buffering did not.
   *
   * So: dispatch on the newline if one arrives, and otherwise on a short
   * silence. A human cannot type two commands 80 ms apart, and the monitor
   * sends a whole line in one burst, so the silence is unambiguous. */
  static char line[24];
  static uint8_t n = 0;
  static uint32_t lastChar = 0;

  while (Serial.available() > 0) {
    int c = Serial.read();
    lastChar = millis();
    if (c == '\\r') continue;
    if (c != '\\n') {
      if (n < sizeof(line) - 1) line[n++] = (char)c;
      continue;
    }
    line[n] = 0;
    uint8_t len = n;
    n = 0;
    if (len > 0) consoleRun(line, len);
  }

  if (n > 0 && (millis() - lastChar) > CONSOLE_IDLE_MS) {
    line[n] = 0;
    uint8_t len = n;
    n = 0;
    consoleRun(line, len);
  }
}

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
  btnPin[B_PERSON]    = BTN_PERSON;
  btnPin[B_NONTARGET] = BTN_NONTARGET;
  btnPin[B_ESTOP]     = BTN_ESTOP;

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
  selfCheck();
  consoleHelp();
  Serial.println();
}

/* Power-on self check.
 *
 * A governor made of refusals cannot tell you it is miswired: a floating
 * E-stop latches, a dead sensor reads as "nothing there", and both look
 * exactly like the system working correctly and declining to emit. Every
 * silent failure mode in this rig presents as a deliberate refusal, so the
 * inputs get examined once at boot, before the logic can hide behind them. */
void selfCheck() {
  Serial.println("power-on self check");

#if HAVE_ESTOP
  uint8_t lows = 0;
  for (uint8_t i = 0; i < 40; i++) {
    if (digitalRead(BTN_ESTOP) == LOW) lows++;
    delay(5);
  }
  if (lows == 0) {
    Serial.println("  E-stop input    OK, held high");
  } else if (lows == 40) {
    Serial.println("  E-stop input    STUCK LOW - button held closed, or both its "
                   "wires are on the same side of the switch");
  } else {
    Serial.printf("  E-stop input    FLOATING (%u of 40 samples low) - the 10k "
                  "pull-up to 3V3 is not connected\n", lows);
  }
#else
  const uint8_t lows = 0;
  Serial.println("  E-stop input    NOT FITTED - the wired stop is disabled; "
                 "console 'e' still latches");
#endif

#if HAVE_SENSOR
  uint8_t echoes = 0;
  for (uint8_t i = 0; i < 5; i++) {
    if (pingOnceCm() > 0) echoes++;
    delay(60);
  }
  if (echoes > 0) {
    Serial.printf("  distance sensor OK, %u of 5 pings returned\n", echoes);
  } else {
    Serial.println("  distance sensor NO ECHO - check VCC is on VIN/5V not 3V3, "
                   "and that TRIG and ECHO are not swapped");
  }
#else
  const uint8_t echoes = 1;
  Serial.println("  distance sensor NOT FITTED - distance comes from the "
                 "console, type d80");
#endif

#if !HAVE_POT
  Serial.println("  group knob      NOT FITTED - group size comes from the "
                 "console, type g5");
#else
  uint32_t acc = 0;
  for (uint8_t i = 0; i < 16; i++) acc += analogRead(POT_GROUP);
  Serial.printf("  group knob      reads %lu of 4095\n",
                (unsigned long)(acc / 16));
#endif

  if (lows > 0 || echoes == 0) {
    Serial.println("  ^ fix the above before reading anything into a refusal");
  }
#if !HAVE_ESTOP || !HAVE_SENSOR || !HAVE_POT
  Serial.println();
  Serial.println("  DECLARE THIS WHEN YOU DEMONSTRATE:");
#if !HAVE_SENSOR
  Serial.println("    the distance input is typed, not sensed");
#endif
#if !HAVE_POT
  Serial.println("    the group size is typed, not read from a knob");
#endif
#if !HAVE_ESTOP
  Serial.println("    the emergency stop is a console command, not a wired button");
#endif
#if ONE_LAMP_MODE
  Serial.println("    one lamp, not three: solid means emitting, a slow pulse "
                 "means refused, a fast flutter means it gave up");
#elif TWO_LAMP_MODE
  Serial.println("    two lamps, not three: green permits, red refuses, "
                 "red blinking is escalation");
#endif
  Serial.println("    the governor rules below are unchanged and are doing the deciding");
#endif
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

float pingOnceCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 25000UL);
  if (us == 0) return -1.0f;            // no echo != "animal is adjacent"
  return us / 58.0f;
}

/* Median of three. One bad ping cannot move the answer, and the no-echo case
 * still wins when two of three agree on it - which is the behaviour we want,
 * because 'nothing there' has to stay easy to conclude. */
float readRangeCm() {
  float a = pingOnceCm(); delay(PING_GAP_MS);
  float b = pingOnceCm(); delay(PING_GAP_MS);
  float c = pingOnceCm();
  float hi = max(a, max(b, c));
  float lo = min(a, min(b, c));
  return a + b + c - hi - lo;
}

#if ONE_LAMP_MODE
/* One lamp, three states, told apart by rate. */
void leds(bool p, bool r, bool e) {
  uint32_t ms = millis();
  bool on;
  if (p)      on = true;                        // emitting: solid
  else if (e) on = ((ms / 120) % 2) == 0;       // escalated: fast flutter
  else if (r) on = ((ms / 500) % 2) == 0;       // refusing: slow pulse
  else        on = false;                       // nothing detected
  digitalWrite(LAMP_ONE, on);
}
#elif TWO_LAMP_MODE
/* Two working lamps instead of three.
 *
 * Three states, two lights, so escalation has to be distinguishable from a
 * refusal by something other than colour: it blinks. */
void leds(bool p, bool r, bool e) {
  digitalWrite(LAMP_GO, p);
  bool blink = ((millis() / 250) % 2) == 0;
  digitalWrite(LAMP_STOP, e ? blink : r);
#if FAR_LAMP_MODE
  digitalWrite(LAMP_FAR, farRefusal);
#endif
}
#else
void leds(bool p, bool r, bool e) {
  digitalWrite(LED_PERMIT, p);
  digitalWrite(LED_REFUSE, r);
  digitalWrite(LED_ESCALATE, e);
}
#endif

void loop() {
  uint32_t now = millis();

  /* Sample every input on every pass, before any early return. A debounce
   * counter that only advances while a target is present is worse than none:
   * a veto button already held down when the animal walks in would need four
   * more passes to be believed, and the governor would permit emission in the
   * gap. Safety inputs must be settled before they are needed, not after. */
  consoleTick();
  farRefusal = false;          // set below only by the out-of-range refusal
  bool person    = pressed(B_PERSON)    || typedPerson;
  bool nonTarget = pressed(B_NONTARGET) || typedNonTarget;
  uint8_t group  = readGroup();

#if HAVE_ESTOP
  if (pressed(B_ESTOP)) estopLatched = true;
#endif
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

#if HAVE_SENSOR
  float cm = readRangeCm();
#else
  float cm = simDistanceCm;
#endif
  bool  seen = (cm > 0 && cm < SEEN_MAX_CM);
  float metres = seen ? (cm / DESK_SCALE) : 999.0f;

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
  else if (metres > RANGE_MAX_M)   { deny = "beyond the acoustic envelope";
                                     farRefusal = true; }
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
