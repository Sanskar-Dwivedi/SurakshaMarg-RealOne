/*
 * Minimal Arduino / ESP32 stubs, enough to type-check a sketch on a desktop
 * compiler with no toolchain installed.
 *
 * This exists because a broken sketch was shipped once: the ESP32 code used the
 * Arduino-ESP32 core 2.x LEDC API, Wokwi builds against core 3.x, and the first
 * anyone knew about it was a build failure in the simulator. A syntax-only
 * compile against both core APIs catches that class of mistake in under a
 * second, so it now runs in the test suite.
 *
 * Scope: this proves the sketch COMPILES. It does not prove it behaves. The
 * behavioural rules are asserted against evidence.py in
 * test_firmware_consistency.py.
 *
 * Define FAKE_CORE3 to expose the core 3.x LEDC API instead of 2.x.
 */
#pragma once
#include <cstdint>
#include <cstdio>
#include <cmath>

#define PI 3.1415926535897932384626433832795
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2

/* Analogue pin aliases (AVR) */
#define A0 14
#define A1 15
#define A2 16
#define A3 17
#define A4 18
#define A5 19

typedef uint8_t byte;

class __FlashStringHelper;
#define F(x) (reinterpret_cast<const __FlashStringHelper *>(x))

inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int digitalRead(int) { return 1; }
inline int analogRead(int) { return 0; }
inline unsigned long millis() { return 0; }
inline void delay(unsigned long) {}
inline void delayMicroseconds(unsigned long) {}
inline unsigned long pulseIn(int, int, unsigned long) { return 0; }
template <typename T> inline T constrain(T x, T lo, T hi) {
  return x < lo ? lo : (x > hi ? hi : x);
}
template <typename T> inline T max(T a, T b) { return a > b ? a : b; }
template <typename T> inline T min(T a, T b) { return a < b ? a : b; }
inline long map(long x, long a, long b, long c, long d) {
  return (x - a) * (d - c) / (b - a) + c;
}
inline void tone(int, unsigned int) {}
inline void noTone(int) {}

/* Serial takes anything printable, including F() strings and (value, digits). */
struct SerialT {
  void begin(long) {}
  void println() {}
  template <class T> void println(T) {}
  template <class T> void println(T, int) {}
  template <class T> void print(T) {}
  template <class T> void print(T, int) {}
  template <class... A> void printf(const char *, A...) {}
  int available() { return 0; }
  int read() { return -1; }
};
inline SerialT Serial;

/* LEDC: expose only the API of the core we are pretending to be, so a sketch
 * that calls the wrong one fails here exactly as it would in the simulator. */
#if defined(FAKE_CORE3)
  #define ESP_ARDUINO_VERSION_MAJOR 3
  inline bool ledcAttach(uint8_t, uint32_t, uint8_t) { return true; }
  inline void ledcWrite(uint8_t, uint32_t) {}
#else
  #define ESP_ARDUINO_VERSION_MAJOR 2
  inline void ledcSetup(uint8_t, uint32_t, uint8_t) {}
  inline void ledcAttachPin(uint8_t, uint8_t) {}
  inline void ledcWrite(uint8_t, uint32_t) {}
#endif
