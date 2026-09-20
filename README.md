# Radio Case Fan Controller

ESP32 + ESPHome temperature-controlled fan module for cooling enclosed radio
equipment cases (initial target: the ICOM IC-2730A compact organizer, reusable
for other go-box modules). Supports one Noctua 5V PWM fan (outbound only,
passive intake) or two (matched outbound + inbound), switchable in software.

## Status

Breadboard prototype phase. Not yet packaged into an enclosure.

## Hardware on hand

- ESP-WROOM-32 dev board (ESP32-S, 38-pin)
- HiLetgo DS18B20 waterproof temperature probe (1-Wire, stainless steel, 1m)
- Noctua NF-A4x20 5V PWM fan(s)
- UMLIFE AC/DC-to-DC buck converter, adjustable 2.5–35V output, 2A, wide input
  (5–30V AC/DC / 5–48V DC) — set output to 5.0V

## Pinout (ESP-WROOM-32)

| Signal                | GPIO   | Notes                                            |
| --------------------- | ------ | ------------------------------------------------ |
| DS18B20 data (1-Wire) | GPIO4  | 4.7kΩ pull-up to 3.3V between data and VCC       |
| Fan 1 (outbound) PWM  | GPIO25 | Hardware LEDC output, 25kHz per Noctua PWM spec  |
| Fan 1 tach            | GPIO26 | Open-collector; 10kΩ pull-up to **3.3V**, not 5V |
| Fan 2 (inbound) PWM   | GPIO27 | Hardware LEDC output, 25kHz                      |
| Fan 2 tach            | GPIO32 | Open-collector; 10kΩ pull-up to **3.3V**, not 5V |

Pins chosen to avoid ESP32 boot-strapping pins (0, 2, 12, 15) and input-only
pins (34–39).

## Power wiring

- Radio supply (12V nominal, wide tolerance) → reverse-polarity protection
  (series diode or P-MOSFET) → buck converter input
- Buck converter output trimmed to **5.0V** → ESP32 `5V`/`VIN` pin (onboard
  regulator drops to 3.3V for the MCU) and both fans' 5V pins, in parallel
- Common ground across buck converter output, ESP32, and both fans
- The buck converter module itself has no advertised input protection —
  don't rely on it for reverse-polarity or surge handling; add that upstream

## Fan PWM/tach notes

- Noctua 4-pin fans expect ~25kHz on the PWM control line; ESP32's hardware
  `LEDC` peripheral hits this natively (this is why ESP32 over ESP8266 for
  this module — ESP8266's software PWM can't cleanly reach 25kHz and tends
  to produce audible whine)
- Tach line is open-collector: it only pulls low, never drives high, so a
  simple pull-up to 3.3V is safe — no level shifting needed
- Fans report 2 tach pulses per revolution; the ESPHome config's
  `pulse_counter` filter accounts for this

## Software

`icom-2730a-fan-controller.yaml` — ESPHome config. Key behavior:

- DS18B20 reading drives a linear PWM ramp between a configurable min/max
  temperature (exposed as tunable `number` entities, not hardcoded)
- "Dual Fan Mode" switch: on = both fans run the same curve; off = only
  Fan 1 (outbound) runs, Fan 2 output held at 0% for passive-intake mode
- Fallback WiFi AP + local API so the module stays controllable if the
  field WiFi network isn't up

### First flash

1. Copy `secrets.yaml.example` to `secrets.yaml` and fill in your values
2. Flash and check the boot log for the DS18B20's actual 1-Wire address,
   then replace the placeholder `address:` in the YAML
3. Confirm fan curve thresholds via Home Assistant or the ESPHome web UI
   before buttoning up the enclosure

## Repo layout

```
/esphome/icom-2730a-fan-controller.yaml   # this file, moved under /esphome
/esphome/secrets.yaml.example
/hardware/                                 # OpenSCAD enclosure, schematic (TBD)
/docs/
  wiring.md                                # this README's wiring section, expanded
  bom.md
README.md
.gitignore
```

## TODO

- [ ] Confirm DS18B20 address after first flash
- [ ] Bench-test fan curve against actual enclosure thermal load
- [ ] Add reverse-polarity/TVS protection circuit on buck converter input
- [ ] Design enclosure (OpenSCAD) once breadboard behavior is validated
- [ ] Consider stall detection (tach == 0 while PWM > 0) as a fault alert
