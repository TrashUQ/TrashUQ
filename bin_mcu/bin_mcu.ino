/*
 * TrashNet — STM32U585 MCU firmware
 *
 * Responsibilities:
 *   - PIR detection → send PIR_TRIG to MPU
 *   - LED PWM control (on command from MPU)
 *   - Servo lid control (on command from MPU)
 *
 * Serial command set (MPU → MCU):
 *   LED_ON
 *   LED_OFF
 *   LID_OPEN
 *   LID_CLOSE
 *
 * Serial events (MCU → MPU):
 *   PIR_TRIG
 *   LID_OPENED
 *   LID_CLOSED
 */

#include <Servo.h>

// ── Pin assignments ──────────────────────────────────────────────────────────
static constexpr int PIN_PIR   = 2;
static constexpr int PIN_LED   = 9;   // PWM-capable
static constexpr int PIN_SERVO = 10;  // PWM-capable

// ── Servo angles (tune for your physical bin) ────────────────────────────────
static constexpr int SERVO_CLOSED_DEG = 10;
static constexpr int SERVO_OPEN_DEG   = 95;

// ── Constants ────────────────────────────────────────────────────────────────
static constexpr unsigned long PIR_HOLD_MS = 2000;
static constexpr int           SERIAL_BAUD = 115200;

// ── Globals ──────────────────────────────────────────────────────────────────
static unsigned long lastPirTrig = 0;
static Servo lidServo;

// ── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_LED, OUTPUT);
  analogWrite(PIN_LED, 0);

  lidServo.attach(PIN_SERVO);
  lidServo.write(SERVO_CLOSED_DEG);
}

// ── Loop ─────────────────────────────────────────────────────────────────────
void loop() {
  pollPIR();
  pollSerial();
}

// ── PIR ──────────────────────────────────────────────────────────────────────
void pollPIR() {
  if (digitalRead(PIN_PIR) == HIGH) {
    unsigned long now = millis();
    if (now - lastPirTrig > PIR_HOLD_MS) {
      lastPirTrig = now;
      Serial.println("PIR_TRIG");
    }
  }
}

// ── Serial command parser ─────────────────────────────────────────────────────
void pollSerial() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();

  if (line == "LED_ON") {
    analogWrite(PIN_LED, 255);
  } else if (line == "LED_OFF") {
    analogWrite(PIN_LED, 0);
  } else if (line == "LID_OPEN") {
    lidServo.write(SERVO_OPEN_DEG);
    Serial.println("LID_OPENED");
  } else if (line == "LID_CLOSE") {
    lidServo.write(SERVO_CLOSED_DEG);
    Serial.println("LID_CLOSED");
  }
}
