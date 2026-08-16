/*
 * sensor_watch - a long, forgiving look at the HC-SR04.
 *
 * parts_check pings twenty times in four seconds, which is not long enough for
 * anyone to read the instruction and get a hand in front of the sensor. This
 * runs for a minute and reports continuously, so the operator can move around
 * while it watches.
 *
 * It also distinguishes the two failures that look identical in a single
 * reading: nothing wired at all (never any echo) versus wired but out of range
 * (echoes that are all long). Only the first is a wiring problem.
 */

const int PIN_TRIG = 13;
const int PIN_ECHO = 39;      // VN

float pingCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 30000UL);
  return us == 0 ? -1.0f : us / 58.0f;
}

void setup() {
  Serial.begin(115200);
  delay(400);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  Serial.println();
  Serial.println("sensor_watch - 60 s of pings, move your hand about");
  Serial.println("VCC on 3V3, GND on the rail, TRIG=13, ECHO straight to VN");
  Serial.println("---------------------------------------------------------");
}

void loop() {
  static int total = 0, good = 0;
  static float lo = 9999, hi = -1;

  float cm = pingCm();
  total++;
  if (cm > 0) { good++; if (cm < lo) lo = cm; if (cm > hi) hi = cm; }

  if (total % 5 == 0) {
    Serial.printf("%3d pings  %3d returned  ", total, good);
    if (good) Serial.printf("range %.0f - %.0f cm  last %s\n", lo, hi,
                            cm > 0 ? String(cm, 0).c_str() : "-");
    else      Serial.println("no echo at all yet");
  }
  delay(120);
}
