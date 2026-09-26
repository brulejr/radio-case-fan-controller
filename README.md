# Radio Case Fan Controller

ESP32 + ESPHome temperature-controlled fan module for cooling enclosed radio
equipment cases (initial target: the ICOM IC-2730A compact organizer, reusable
for other go-box modules). Supports one Noctua 5V PWM fan (outbound only,
passive intake) or two (matched outbound + inbound), switchable in software.

## Status

Breadboard prototype phase in the lab. The finished unit is a **carrier board**
— prototype board first, then a custom PCB — not a breadboard.

## Hardware on hand

- ESP32-C6-WROOM-1 dev board (RISC-V, 2×15 headers, dual USB-C)
- HiLetgo DS18B20 waterproof temperature probe (1-Wire, stainless steel, 1m)
- Noctua NF-A4x20 5V PWM fan(s)
- Buck converter with a **USB-C output** — exact part TBC, see `docs/wiring.md`

## Schematic

[`hardware/schematic.svg`](hardware/schematic.svg) — full electrical diagram.
[`docs/wiring.md`](docs/wiring.md) has the net-by-net connection table, the
connector pinouts, the BOM, and the order to bring the board up in.

[![Schematic](hardware/schematic.svg)](hardware/schematic.svg)

## Pinout (ESP32-C6-WROOM-1 dev board)

| Signal                | GPIO   | Side   | Notes                                            |
| --------------------- | ------ | ------ | ------------------------------------------------ |
| DS18B20 data (1-Wire) | GPIO6  | Left   | 4.7kΩ pull-up to 3.3V between data and VCC       |
| Fan 1 (outbound) PWM  | GPIO18 | Right  | Hardware LEDC output, 25kHz per Noctua PWM spec  |
| Fan 1 tach            | GPIO19 | Right  | Open-collector; 10kΩ pull-up to **3.3V**, not 5V |
| Fan 2 (inbound) PWM   | GPIO20 | Right  | Hardware LEDC output, 25kHz                      |
| Fan 2 tach            | GPIO21 | Right  | Open-collector; 10kΩ pull-up to **3.3V**, not 5V |

Pins chosen to avoid the C6 strapping pins (4, 5, 8, 9, 15 — 8 also drives the
onboard RGB LED, 9 is the BOOT button, 15 has no internal pull), the USB
Serial/JTAG pair (12, 13), and the UART0 pins wired to the USB bridge (16, 17).
GPIO14 is not broken out, and GPIO24–30 are consumed by the SPI flash bus.

The four fan signals sit as a contiguous block on the right header while the
1-Wire probe is on the left, putting it on the physically opposite side of the
board from the 25kHz PWM edges. Spare after this: GPIO0, 1, 2, 3, 7, 10, 11,
22, 23.

## Power wiring

- Radio supply (12V nominal, wide tolerance) → buck converter input, direct.
  No protection components by design — the box is fed from a battery or bench
  supply, which handle surge and reverse polarity at the source
- The buck's only output is **USB-C**, so 5V reaches the board through a USB-C
  cable into one of the dev board's two ports
- Both fans take 5V and GND from the dev board's header pins — so **fan power
  depends on the dev board**. See the power topology section of
  [`docs/wiring.md`](docs/wiring.md) for what that implies
- **One power source at a time**: the buck and both USB-C ports share a net.
  Don't leave the buck connected while a computer is plugged in
- No bulk or decoupling caps on the 5V rail; 4-pin PWM fans don't chop their
  supply current, and the dev board has its own input decoupling

## Fan PWM/tach notes

- Noctua 4-pin fans expect ~25kHz on the PWM control line; the ESP32-C6's
  hardware `LEDC` peripheral hits this natively at ~11-bit resolution (this is
  why an ESP32-class part over an ESP8266 — ESP8266's software PWM can't
  cleanly reach 25kHz and tends to produce audible whine)
- Tach line is open-collector: it only pulls low, never drives high, so a
  simple pull-up to 3.3V is safe — no level shifting needed
- Fans report 2 tach pulses per revolution; the ESPHome config's
  `pulse_counter` filter accounts for this
- **No PWM signal means full speed**, not stopped — the fan pulls its control
  input high internally. Expect a spin-up if you unplug a PWM line while the
  fan is powered
- Each fan draws 0.1A / 0.5W at full speed (Noctua spec)

## Software

`icom2370a-fan-controller.yaml` — ESPHome config. Key behavior:

- DS18B20 reading drives a linear PWM ramp between a configurable min/max
  temperature (exposed as tunable `number` entities, not hardcoded)
- "Dual Fan Mode" switch: on = both fans run the same curve; off = only
  Fan 1 (outbound) runs, Fan 2 output held at 0% for passive-intake mode
- Fallback WiFi AP + local API so the module stays controllable if the
  field WiFi network isn't up
- Local web UI at `http://<device-ip>/` for the sensors, fan-curve numbers and
  Dual Fan Mode switch, with its assets embedded in flash so it works with no
  internet. Needs `web_server_username` / `web_server_password` in `secrets.yaml`

### First flash

1. Copy `secrets.yaml.example` to `secrets.yaml` and fill in your values
2. Flash. The boot log lists the 1-Wire devices found on GPIO6; confirm the
   probe enumerates. No address needs configuring — see the note in the YAML
3. Confirm fan curve thresholds via Home Assistant or the ESPHome web UI
   before buttoning up the enclosure

## Repo layout

```
/esphome/icom2370a-fan-controller.yaml    # ESPHome config
/esphome/secrets.yaml.example
/hardware/schematic.svg                    # schematic / wiring diagram
/docs/wiring.md                            # net list, connection table, BOM, bring-up order
README.md
.gitignore
```

Still to come under `/hardware/`: the OpenSCAD enclosure.

## TODO

- [ ] Bench-test fan curve against actual enclosure thermal load
- [ ] Design enclosure (OpenSCAD) once breadboard behavior is validated
- [ ] Consider stall detection (tach == 0 while PWM > 0) as a fault alert
