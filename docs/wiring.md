# Wiring

Companion to [`hardware/schematic.svg`](../hardware/schematic.svg). The schematic
is the picture; this page is the thing you build from and check against.

![Schematic](../hardware/schematic.svg)

## Nets

Seven nets total. Everything in the module is one of these.

| Net        | Carries                    | Members                                                                 |
| ---------- | -------------------------- | ----------------------------------------------------------------------- |
| `+12V_IN`  | radio supply, unregulated  | J1 `+` → D1 anode; D1 cathode → D2, C1 `+`, U1 `IN+`                     |
| `+5V`      | regulated, 5.00 V          | U1 `OUT+` → ESP32 `5V/VIN`, C3 `+`, Fan 1 pin 2, Fan 2 pin 2, C2 `+`     |
| `+3V3`     | ESP32 onboard regulator    | ESP32 `3V3` → DS18B20 red, R1, R2, R3                                    |
| `GND`      | common return              | J1 `−`, D2, C1 `−`, U1 `IN−`/`OUT−`, ESP32 `GND`, C2/C3 `−`, DS18B20 black, Fan 1 pin 1, Fan 2 pin 1 |
| `1W_DATA`  | DS18B20 1-Wire bus         | ESP32 `GPIO4` ↔ DS18B20 yellow, R1 to `+3V3`                             |
| `TACH1/2`  | fan speed, open-collector  | ESP32 `GPIO26` ↔ Fan 1 pin 3 (R2 to `+3V3`); `GPIO32` ↔ Fan 2 pin 3 (R3) |
| `PWM1/2`   | 25 kHz fan control         | ESP32 `GPIO25` → Fan 1 pin 4; `GPIO27` → Fan 2 pin 4                     |

## Connection table

Build from this. Each row is one wire.

### Power in

| From          | To            | Notes                                              |
| ------------- | ------------- | -------------------------------------------------- |
| J1 `+`        | D1 anode      | 12 V nominal from the radio supply                 |
| D1 cathode    | U1 `IN+`      | D2 and C1 `+` also land on this node               |
| D2 (either)   | `GND`         | bidirectional TVS, orientation doesn't matter      |
| C1 `−`        | `GND`         | electrolytic — `+` goes to the D1 cathode node     |
| J1 `−`        | `GND`         |                                                     |
| U1 `IN−`      | `GND`         |                                                     |

D1 / D2 / C1 are the protection stage and are **not on the breadboard yet**
(dashed on the schematic). Until they exist, reversing J1 destroys U1 and the
ESP32. For bench work, feed the breadboard from a current-limited supply.

### 5 V distribution

| From      | To               | Notes                                                    |
| --------- | ---------------- | -------------------------------------------------------- |
| U1 `OUT+` | ESP32 `5V`/`VIN` | trim U1 to 5.00 V **before** this wire goes in           |
| U1 `OUT+` | Fan 1 pin 2      | yellow on the Noctua connector                           |
| U1 `OUT+` | Fan 2 pin 2      | omit if running single-fan                               |
| U1 `OUT−` | ESP32 `GND`      | star point — see the grounding note below                |
| U1 `OUT−` | Fan 1 pin 1      | black                                                    |
| U1 `OUT−` | Fan 2 pin 1      |                                                           |
| C3        | across `+5V`/`GND` at the ESP32 | 10 µF, keep the leads short             |
| C2        | across `+5V`/`GND` at the fans  | 100 µF, damps fan start-up inrush       |

### Signals

| ESP32 pin | To                  | Passive                     | Notes                                      |
| --------- | ------------------- | --------------------------- | ------------------------------------------- |
| `GPIO4`   | DS18B20 yellow      | R1 4.7 kΩ to `+3V3`         | 1-Wire data; R1 sits at the probe end       |
| `GPIO25`  | Fan 1 pin 4 (blue)  | —                           | LEDC PWM, 25 kHz                            |
| `GPIO26`  | Fan 1 pin 3 (green) | R2 10 kΩ to `+3V3`          | tach, open-collector                        |
| `GPIO27`  | Fan 2 pin 4 (blue)  | —                           | LEDC PWM, 25 kHz                            |
| `GPIO32`  | Fan 2 pin 3 (green) | R3 10 kΩ to `+3V3`          | tach, open-collector                        |
| `3V3`     | DS18B20 red         | —                           | also feeds R1 / R2 / R3                     |
| `GND`     | DS18B20 black       | —                           |                                              |

## Connector pinouts

**Noctua 4-pin** (looking into the fan's connector, tab down):

| Pin | Colour | Function | Goes to                          |
| --- | ------ | -------- | --------------------------------- |
| 1   | black  | GND      | `GND`                             |
| 2   | yellow | +5 V     | `+5V`                             |
| 3   | green  | tach     | GPIO26 / GPIO32, pulled to +3.3 V |
| 4   | blue   | PWM in   | GPIO25 / GPIO27                   |

**DS18B20 waterproof probe**: red = VDD, yellow = data, black = GND. Some
batches ship red/white/black — white is then the data line. Meter it before you
trust the colours.

## Which side of the board

On a typical ESP32 DevKitC v4 38-pin, with the USB connector at the bottom:

- **Left header**: `3V3`, `GPIO32`, `GPIO25`, `GPIO26`, `GPIO27`, `GND`, `5V`
- **Right header**: `GPIO4`

So everything except the DS18B20 data line lands on one side of the board. The
schematic groups pins by function instead, so its pin order does not match the
physical header — go by pin name, and verify against your board's silkscreen,
since clone layouts vary.

## Grounding

Star-ground at `U1 OUT−`. Run separate returns from there to the ESP32 and to
each fan rather than daisy-chaining fan current through the ESP32's `GND` pin —
a fan's start-up surge across shared ground wire shows up as a rail dip at the
MCU, and on a breadboard the contact resistance makes that worse than it sounds.

## Bring-up order

1. With nothing connected to `OUT+`, power U1 and trim its pot until a meter
   reads 5.00 V. Do this first, every time — these modules ship set anywhere in
   their range, and 35 V into the ESP32's `5V` pin ends the session.
2. Power down. Wire `OUT+`/`OUT−` to the ESP32 only. Power up, confirm the board
   enumerates and the 3V3 pin reads ~3.3 V.
3. Add the DS18B20 and R1. Flash, and read the boot log for the 1-Wire address.
4. Add Fan 1, R2, C2. Confirm PWM response and a plausible RPM reading.
5. Add Fan 2 and R3 if running dual-fan.

## Bill of materials — electrical

| Ref       | Part                               | Qty | Notes                                     |
| --------- | ---------------------------------- | --- | ----------------------------------------- |
| U1        | adjustable buck converter, 2 A     | 1   | UMLIFE module on hand; set to 5.00 V      |
| U2        | ESP-WROOM-32 DevKitC, 38-pin       | 1   |                                            |
| —         | DS18B20 waterproof probe, 1 m      | 1   | HiLetgo                                    |
| Fan 1/2   | Noctua NF-A4x20 5V PWM             | 1–2 | Fan 2 optional                             |
| R1        | 4.7 kΩ resistor                    | 1   | 1-Wire pull-up                             |
| R2, R3    | 10 kΩ resistor                     | 1–2 | tach pull-ups, one per fan                 |
| C1        | 100 µF / 50 V electrolytic         | 1   | protection stage, TODO                     |
| C2        | 100 µF / 16 V electrolytic         | 1   | 5 V bulk at the fans                       |
| C3        | 10 µF ceramic or electrolytic      | 1   | 5 V decoupling at the ESP32                |
| D1        | SS34 Schottky, 3 A                 | 1   | reverse-polarity, TODO                     |
| D2        | SMBJ15CA bidirectional TVS         | 1   | surge clamp, TODO                          |
| J1        | 2-pos screw terminal / Powerpole   | 1   | supply entry                               |

Current budget: ESP32 ~250 mA average with Wi-Fi up, ~500 mA on transmit peaks,
plus roughly 120 mA per fan at full speed — call it 0.8 A worst case against
U1's 2 A rating.

## Gotchas

- **Never pull a tach line up to +5 V.** The fan's tach transistor only pulls
  low; the pull-up sets the high level, and a 5 V pull-up puts 5 V straight onto
  a GPIO. R2/R3 go to `+3V3`.
- The ESPHome config also sets `INPUT_PULLUP` on the tach pins. That's belt and
  braces — the internal pull-up is ~45 kΩ, weak enough that a long fan lead can
  round the edge off. Keep the external 10 kΩ parts.
- PWM is driven push-pull at 3.3 V from the ESP32's LEDC peripheral. Noctua's
  5 V PWM fans accept a 3.3 V control signal, so no level shifter is needed.
- Fan behaviour below ~20 % duty is not specified by the 4-wire standard. The
  config's `min_duty` default of 30 % exists for this reason. Separately, at 0 %
  duty some Noctua fans coast at minimum RPM rather than stopping — if Fan 2
  keeps turning in single-fan mode, that's why, and cutting its +5 V is the
  only reliable way to stop it.
- The buck module has no advertised input protection of its own. Don't count on
  it for reverse polarity or surges; that's what D1/D2 are for.
