#include "HX711.h"
#include <SPI.h>
#include <U8g2lib.h>
#include <math.h>

// ============================================================
// OLED Configuration
// ============================================================

#define OLED_RES A0
#define OLED_DC  A1
#define OLED_CS  A2
#define OLED_CLK D13
#define OLED_DIN D12

U8G2_SH1106_128X64_NONAME_F_4W_SW_SPI u8g2(
    U8G2_R0,
    OLED_CLK,
    OLED_DIN,
    OLED_CS,
    OLED_DC,
    OLED_RES
);

// ============================================================
// HX711 Configuration
// ============================================================

HX711 scale1;
HX711 scale2;
HX711 scale3;
HX711 scale4;

#define SCK1 D4
#define DT1  D5

#define SCK2 D6
#define DT2  D7

#define SCK3 D8
#define DT3  D9

#define SCK4 D10
#define DT4  D11

// ============================================================
// Measurement Settings
// ============================================================

const float COMP_DEADBAND_G = 8.0;
const float ROUND_STEP_G = 1.0;

const long NO_LOAD_SUM_THRESHOLD = 2500;

const int READ_SAMPLES = 5;
const int TARE_SAMPLES = 30;

// ============================================================
// Calibration Coefficients
// ============================================================

// Compartment 1
const float C1_BIAS = 1.543484;
const float C1_L1 = 0.00105945;
const float C1_L2 = -0.00344200;
const float C1_L3 = -0.00806599;
const float C1_L4 = 0.00407197;

// Compartment 2
const float C2_BIAS = 3.404343;
const float C2_L1 = -0.00057355;
const float C2_L2 = 0.00049802;
const float C2_L3 = -0.00092570;
const float C2_L4 = -0.00450848;

// Compartment 3
const float C3_BIAS = 3.554572;
const float C3_L1 = -0.00116855;
const float C3_L2 = -0.00512425;
const float C3_L3 = -0.00029842;
const float C3_L4 = -0.00078442;

// ============================================================
// HX711 Runtime Variables
// ============================================================

long zero1 = 0;
long zero2 = 0;
long zero3 = 0;
long zero4 = 0;

long lastRaw1 = 0;
long lastRaw2 = 0;
long lastRaw3 = 0;
long lastRaw4 = 0;

// ============================================================
// Nutrition Data Received from Jetson
// ============================================================

float nKcal = 0.0;
float nProtein = 0.0;
float nCarbs = 0.0;
float nFat = 0.0;

bool hasNutrition = false;

String serialBuffer = "";

// ============================================================
// HX711 Helper Functions
// ============================================================

bool waitUntilReady(HX711 &scale, unsigned long timeoutMs) {
    unsigned long startTime = millis();

    while (!scale.is_ready()) {
        if (millis() - startTime > timeoutMs) {
            return false;
        }

        delay(1);
    }

    return true;
}

long readRawValue(HX711 &scale, long &lastRawValue, int samples) {
    if (waitUntilReady(scale, 800)) {
        lastRawValue = scale.read_average(samples);
    }

    return lastRawValue;
}

float roundToStep(float value, float step) {
    return round(value / step) * step;
}

float cleanWeight(float weight) {
    if (fabs(weight) < COMP_DEADBAND_G) {
        return 0.0;
    }

    if (weight < 0.0) {
        return 0.0;
    }

    return roundToStep(weight, ROUND_STEP_G);
}

// ============================================================
// Tare Function
// ============================================================

void tareAllScales() {
    zero1 = readRawValue(scale1, lastRaw1, TARE_SAMPLES);
    zero2 = readRawValue(scale2, lastRaw2, TARE_SAMPLES);
    zero3 = readRawValue(scale3, lastRaw3, TARE_SAMPLES);
    zero4 = readRawValue(scale4, lastRaw4, TARE_SAMPLES);

    // Return to weight display mode after taring.
    hasNutrition = false;

    Serial.println("Tare completed.");
}

// ============================================================
// OLED Functions
// ============================================================

void showMessage(const char *line1, const char *line2) {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);

    u8g2.setCursor(0, 16);
    u8g2.print(line1);

    u8g2.setCursor(0, 34);
    u8g2.print(line2);

    u8g2.sendBuffer();
}

void showWeightData(
    float compartment1,
    float compartment2,
    float compartment3,
    float totalWeight
) {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);

    u8g2.setCursor(0, 12);
    u8g2.print("C1: ");
    u8g2.print(compartment1, 0);
    u8g2.print(" g");

    u8g2.setCursor(0, 26);
    u8g2.print("C2: ");
    u8g2.print(compartment2, 0);
    u8g2.print(" g");

    u8g2.setCursor(0, 40);
    u8g2.print("C3: ");
    u8g2.print(compartment3, 0);
    u8g2.print(" g");

    u8g2.setCursor(0, 58);
    u8g2.print("Total: ");
    u8g2.print(totalWeight, 0);
    u8g2.print(" g");

    u8g2.sendBuffer();
}

void showNutritionData() {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);

    u8g2.setCursor(0, 12);
    u8g2.print("Kcal: ");
    u8g2.print(nKcal, 0);

    u8g2.setCursor(0, 26);
    u8g2.print("Protein: ");
    u8g2.print(nProtein, 0);
    u8g2.print(" g");

    u8g2.setCursor(0, 40);
    u8g2.print("Carbs: ");
    u8g2.print(nCarbs, 0);
    u8g2.print(" g");

    u8g2.setCursor(0, 58);
    u8g2.print("Fat: ");
    u8g2.print(nFat, 0);
    u8g2.print(" g");

    u8g2.sendBuffer();
}

// ============================================================
// Serial Communication
// ============================================================

void parseNutritionData(const String &line) {
    // Expected format:
    // NUTRI,kcal,protein,carbs,fat

    int comma1 = line.indexOf(',');
    int comma2 = line.indexOf(',', comma1 + 1);
    int comma3 = line.indexOf(',', comma2 + 1);
    int comma4 = line.indexOf(',', comma3 + 1);

    if (
        comma1 < 0 ||
        comma2 < 0 ||
        comma3 < 0 ||
        comma4 < 0
    ) {
        return;
    }

    nKcal = line.substring(comma1 + 1, comma2).toFloat();
    nProtein = line.substring(comma2 + 1, comma3).toFloat();
    nCarbs = line.substring(comma3 + 1, comma4).toFloat();
    nFat = line.substring(comma4 + 1).toFloat();

    // Keep displaying nutrition data until the next tare.
    hasNutrition = true;

    Serial.print("Nutrition received: kcal=");
    Serial.print(nKcal);

    Serial.print(", protein=");
    Serial.print(nProtein);

    Serial.print(", carbs=");
    Serial.print(nCarbs);

    Serial.print(", fat=");
    Serial.println(nFat);
}

void handleSerialInput() {
    while (Serial.available() > 0) {
        char receivedCharacter = Serial.read();

        if (
            receivedCharacter == '\n' ||
            receivedCharacter == '\r'
        ) {
            if (serialBuffer.length() == 0) {
                continue;
            }

            if (serialBuffer.startsWith("NUTRI,")) {
                parseNutritionData(serialBuffer);
            } else if (
                serialBuffer == "t" ||
                serialBuffer == "T"
            ) {
                Serial.println("Manual tare starts in 5 seconds.");

                showMessage("Manual tare", "Wait 5 seconds");
                delay(5000);

                tareAllScales();

                showMessage("Tare completed", "System ready");
                delay(1000);
            }

            serialBuffer = "";
        } else {
            if (serialBuffer.length() < 200) {
                serialBuffer += receivedCharacter;
            }
        }
    }
}

void sendWeightDataToJetson(
    float compartment1,
    float compartment2,
    float compartment3,
    float totalWeight
) {
    // Output format:
    // DATA,weight1,weight2,weight3,totalWeight

    Serial.print("DATA,");

    Serial.print(compartment1, 0);
    Serial.print(",");

    Serial.print(compartment2, 0);
    Serial.print(",");

    Serial.print(compartment3, 0);
    Serial.print(",");

    Serial.println(totalWeight, 0);
}

// ============================================================
// Setup
// ============================================================

void setup() {
    Serial.begin(9600);
    delay(2000);

    u8g2.begin();

    scale1.begin(DT1, SCK1);
    scale2.begin(DT2, SCK2);
    scale3.begin(DT3, SCK3);
    scale4.begin(DT4, SCK4);

    scale1.set_gain(128);
    scale2.set_gain(128);
    scale3.set_gain(128);
    scale4.set_gain(128);

    Serial.println("Place the empty plate on the scale.");
    Serial.println("Tare starts in 5 seconds.");

    showMessage("Place empty plate", "Tare in 5 seconds");
    delay(5000);

    tareAllScales();

    showMessage("Weight mode", "System ready");
    delay(1000);
}

// ============================================================
// Main Loop
// ============================================================

void loop() {
    handleSerialInput();

    long raw1 = readRawValue(scale1, lastRaw1, READ_SAMPLES);
    long raw2 = readRawValue(scale2, lastRaw2, READ_SAMPLES);
    long raw3 = readRawValue(scale3, lastRaw3, READ_SAMPLES);
    long raw4 = readRawValue(scale4, lastRaw4, READ_SAMPLES);

    long delta1 = raw1 - zero1;
    long delta2 = raw2 - zero2;
    long delta3 = raw3 - zero3;
    long delta4 = raw4 - zero4;

    long totalAbsoluteDelta =
        labs(delta1) +
        labs(delta2) +
        labs(delta3) +
        labs(delta4);

    float rawWeight1;
    float rawWeight2;
    float rawWeight3;

    if (totalAbsoluteDelta < NO_LOAD_SUM_THRESHOLD) {
        rawWeight1 = 0.0;
        rawWeight2 = 0.0;
        rawWeight3 = 0.0;
    } else {
        rawWeight1 =
            C1_BIAS +
            C1_L1 * delta1 +
            C1_L2 * delta2 +
            C1_L3 * delta3 +
            C1_L4 * delta4;

        rawWeight2 =
            C2_BIAS +
            C2_L1 * delta1 +
            C2_L2 * delta2 +
            C2_L3 * delta3 +
            C2_L4 * delta4;

        rawWeight3 =
            C3_BIAS +
            C3_L1 * delta1 +
            C3_L2 * delta2 +
            C3_L3 * delta3 +
            C3_L4 * delta4;
    }

    float weight1 = cleanWeight(rawWeight1);
    float weight2 = cleanWeight(rawWeight2);
    float weight3 = cleanWeight(rawWeight3);

    float totalWeight = weight1 + weight2 + weight3;

    sendWeightDataToJetson(
        weight1,
        weight2,
        weight3,
        totalWeight
    );

    if (hasNutrition) {
        showNutritionData();
    } else {
        showWeightData(
            weight1,
            weight2,
            weight3,
            totalWeight
        );
    }

    delay(250);
}
