# Wiring

Companion to [`hardware/schematic.svg`](../hardware/schematic.svg). The schematic
is the picture; this page is the thing you build from and check against.

![Schematic](../hardware/schematic.svg)

Target hardware is a **carrier board** — prototype board first, then a custom
PCB. Breadboarding is development-lab only.

## Power topology

This is the least obvious part of the design, so it comes first.

The buck converter's **only output is a USB-C socket**. There are no terminals
or pads on it. So 5 V reaches the carrier board through the dev board:

```
J1 12V ──────────────▶ U1 buck ─[USB-C cable]─▶ dev board USB-C
                                                      │
                                       dev board 5V pin (= VBUS)
                                                      │
                                    ┌─────────────────┴─────────────────┐
                                 Fan 1 pin 2                       Fan 2 pin 2
```

The dev board's two `5V` header pins and both USB-C VBUS lines are one net.
Fans tap that net at the header pins.

Two consequences worth understanding before you build:

**Fan power depends on the MCU board.** Pull or kill the dev board and the fans
lose power. This is a deliberate accepted trade for wiring simplicity, but note
the interaction: with no PWM signal a Noctua 4-pin fan runs at **full speed**
(the input is pulled up internally, per the Intel 4-wire spec). So a hung MCU
that still has power gives you full-blast cooling — the safe failure — whereas a
dead MCU board gives you no cooling at all.

**One power source at a time.** The buck and either USB-C port feed the same
net. Do not have the buck connected while a computer is plugged into the other
USB port. With OTA configured you rarely need USB after the first flash, so
this is mostly a bench-discipline rule.

## Nets

| Net        | Carries                    | Members                                                                 |
| ---------- | -------------------------- | ----------------------------------------------------------------------- |
| `+12V_IN`  | radio supply, unregulated  | J1 `+` → U1 `IN+`                                                        |
| `+5V`      | 5.00 V, via USB-C          | U1 USB-C → dev board VBUS → dev board `5V` pins → Fan 1 pin 2, Fan 2 pin 2 |
| `+3V3`     | dev board onboard regulator| dev board `3V3` → DS18B20 red, R1, R2, R3                               |
| `GND`      | common return              | J1 `−`, U1 `IN−`, dev board `GND`, DS18B20 black, Fan 1 pin 1, Fan 2 pin 1 |
| `1W_DATA`  | DS18B20 1-Wire bus         | `GPIO6` ↔ DS18B20 yellow, R1 to `+3V3`                                  |
| `TACH1/2`  | fan speed, open-collector  | `GPIO19` ↔ Fan 1 pin 3 (R2 to `+3V3`); `GPIO21` ↔ Fan 2 pin 3 (R3)       |
| `PWM1/2`   | 25 kHz fan control         | `GPIO18` → Fan 1 pin 4; `GPIO20` → Fan 2 pin 4                          |

`GND` is one net throughout. On the schematic the input-side and output-side
segments are drawn without a wire between them — the path runs through U1 and
the USB-C cable, and drawing it would mean crossing every signal line on the
board. They are the same net.

## Connection table

Build from this. Each row is one wire.

### Power in (12 V side)

| From     | To       | Notes                              |
| -------- | -------- | ---------------------------------- |
| J1 `+`   | U1 `IN+` | 12 V nominal from the radio supply |
| J1 `−`   | U1 `IN−` | `GND`                               |

Two wires, no components. **This is deliberate**: the box is fed from a battery
or a bench supply, and surge and reverse-polarity handling live at the source —
a bench supply current-limits, and a battery feed through polarised Powerpoles
cannot be reversed at the connector.

Don't add protection components here. The one thing to note is that the
assumption travels with the supply: if this module is ever fed from something
unprotected, it needs revisiting.

### 5 V side

| From                | To                  | Notes                                            |
| ------------------- | ------------------- | ------------------------------------------------- |
| U1 USB-C            | dev board USB-C     | USB-C cable. Either port works; the CH343 port leaves the native port free for JTAG |
| dev board `5V` pin  | Fan 1 pin 2         | yellow on the Noctua connector                    |
| dev board `5V` pin  | Fan 2 pin 2         | omit if running single-fan                        |
| dev board `GND` pin | Fan 1 pin 1         | black                                             |
| dev board `GND` pin | Fan 2 pin 1         |                                                   |

No bulk or decoupling capacitors on this rail. The dev board has its own input
decoupling, and 4-pin PWM fans don't chop their supply current — the PWM line
drives the fan's internal commutation, so there's little for a bulk cap to do.

### Signals

| MCU pin  | Side  | To                  | Passive             | Notes                |
| -------- | ----- | ------------------- | ------------------- | --------------------- |
| `GPIO6`  | Left  | DS18B20 yellow      | R1 4.7 kΩ to `+3V3` | 1-Wire data           |
| `GPIO18` | Right | Fan 1 pin 4 (blue)  | —                   | LEDC PWM, 25 kHz      |
| `GPIO19` | Right | Fan 1 pin 3 (green) | R2 10 kΩ to `+3V3`  | tach, open-collector  |
| `GPIO20` | Right | Fan 2 pin 4 (blue)  | —                   | LEDC PWM, 25 kHz      |
| `GPIO21` | Right | Fan 2 pin 3 (green) | R3 10 kΩ to `+3V3`  | tach, open-collector  |
| `3V3`    | Left  | DS18B20 red         | —                   | also feeds R1/R2/R3   |
| `GND`    | Either| DS18B20 black       | —                   |                       |

> **R1, R2 and R3 all go to `+3V3`, never to `+5V`.** The fan's tach transistor
> only pulls low — the pull-up alone sets the high level, so a pull-up on the
> 5 V rail puts 5 V onto a 3.3 V GPIO whose absolute maximum is 3.6 V. The fan
> still appears to work and the only symptom is a tach that reads a flat
> `0.00 RPM`, so this fails silently. Check the resistor's upper end lands on
> the dev board's `3V3` pin before first power-up.

R1, R2 and R3 all live on the carrier board next to the dev board, not out at
the sensor or fan. At these cable lengths the pull-up position makes no
measurable difference, and keeping them on the board means the probe and fans
are plain pluggable assemblies with no components buried in a cable run.

## Carrier board connectors

Pick pitches that are integer multiples of **2.54 mm**. A 3.5 mm terminal block
will not fit 0.1" protoboard, and you lose the property that the protoboard
footprint and the PCB footprint are identical.

| For          | Use                                              | Why                                        |
| ------------ | ------------------------------------------------ | ------------------------------------------ |
| Fans (×2)    | 4-pin PC fan header, 2.54 mm, THT (Molex 47053-1000 or equivalent) | The fan already has the mating half — keyed, no crimping |
| DS18B20      | 3-position screw or push-in terminal, 2.54 or 5.08 mm | Each conductor lands individually, so the varying lead colours can't cause a reversal |
| 12 V in      | 2-position screw terminal, 5.08 mm, or a Powerpole pigtail | 5.08 mm is exactly 2× the grid            |
| Dev board    | 2× 15-pin female headers                         | Socket it — keeps the MCU field-replaceable |

> **Silkscreen the fan headers `5V FANS ONLY`.** They are physically identical
> to 12 V motherboard fan headers. A 12 V fan in your board merely runs slow,
> but your 5 V fan in a real 12 V header is destroyed instantly. Label the fan
> pigtails too — the fan is the part that wanders off.

A 3-pin fan connector also mates with a 4-pin header (PWM simply unconnected),
if you ever want to fall back to voltage-controlled fans.

## Connector pinouts

**Noctua 4-pin** (looking into the fan's connector, tab down):

| Pin | Colour | Function | Goes to                          |
| --- | ------ | -------- | --------------------------------- |
| 1   | black  | GND      | `GND`                             |
| 2   | yellow | +5 V     | dev board `5V` pin                |
| 3   | green  | tach     | GPIO19 / GPIO21, pulled to +3.3 V |
| 4   | blue   | PWM in   | GPIO18 / GPIO20                   |

**DS18B20 waterproof probe**: red = VDD, yellow = data, black = GND. Some
batches ship red/white/black — white is then the data line. Meter it before you
trust the colours.

## The dev board

A third-party ESP32-C6-WROOM-1 board, **2×15 headers**, with two USB-C ports
(one behind a CH343 USB-UART bridge, one native ESP32-C6 USB/JTAG), BOOT and
RST buttons, and an addressable RGB LED on GPIO8.

Header map, top to bottom with the USB connectors at the bottom:

| Left (15)                                            | Right (15)                                             |
| ---------------------------------------------------- | ------------------------------------------------------ |
| RST, 3V3, GND, 4, 5, **6**, 7, 0, 1, 8, 10, 11, 12, 13, 5V | GND, 2, 3, TX, RX, 15, 23, 22, **21, 20, 19, 18**, 9, GND, 5V |

This board brings out **all 23 usable GPIOs** on the module (0–13, 15, 18–23,
plus TX/RX = GPIO16/17), so nothing is omitted.

The split across sides is deliberate: the four fan signals sit together on the
right, and the 1-Wire probe is on the left — the 25 kHz PWM edges are the
noisiest thing on the board and the 1-Wire bus, pulled up through 4.7 kΩ over a
metre of cable, is the most susceptible.

The schematic groups pins by function rather than physical position, so its pin
order does not match the header — go by pin name.

**Do not use** GPIO4, 5, 8, 9 or 15 (strapping; 8 drives the RGB LED, 9 is the
BOOT button, 15 has no internal pull resistor), GPIO12/13 (native USB) or
GPIO16/17 (UART0 to the CH343). GPIO14 is not broken out and GPIO24–30 are the
SPI flash bus.

## Carrier board layout

The right-hand column reads, bottom-up: `5V, GND, 9, 18, 19, 20, 21`. Every
signal both fan headers need — PWM, tach, +5 V and ground — is one contiguous
run at the **bottom-right corner**. Put both fan headers there and all the fan
wiring stays in one compact zone with no runs under the board.

GPIO6 for the probe is on the left side, well away from it, so the noise
separation falls out of the physical layout rather than needing thought.

Two practical notes:

- A 4×6 cm protoboard is tight once the dev board is placed. The buck converter
  is a module in its own right and will likely need to live off-board, with only
  the USB-C cable arriving at the carrier.
- Socket the dev board on female headers rather than soldering it through.

## Grounding

Star-ground at the dev board's `GND` pins — that is where `GND` reaches the
carrier board, since the buck's return arrives through the USB-C cable.
Run separate returns from there to each fan rather than daisy-chaining one fan's
return through the other.

## Bring-up order

1. With nothing plugged into it, power U1 and confirm its USB-C output reads
   **5.00 V** on a meter. Do this first, every time — an adjustable module can
   ship set anywhere in its range, and feeding the dev board's USB-C port from a
   mis-set buck ends the session.
2. Power down. Connect the USB-C cable to the dev board only. Power up, confirm
   the board enumerates and the `3V3` pin reads ~3.3 V.
3. Add the DS18B20 and R1. Flash, and confirm the probe enumerates in the boot
   log. The config deliberately pins no address — the sole device on the bus is
   selected automatically, so the firmware is portable across builds.
   **Unplug the buck while flashing over USB** — one source at a time.
4. Add Fan 1 and R2. Confirm PWM response and a plausible RPM reading.
5. Add Fan 2 and R3 if running dual-fan.

## Bill of materials — electrical

| Ref       | Part                                  | Qty | Notes                                      |
| --------- | ------------------------------------- | --- | ------------------------------------------ |
| U1        | 12 V → 5 V buck converter, USB-C out  | 1   | any module ≥1 A; no specific part required |
| U2        | ESP32-C6-WROOM-1 dev board, 2×15      | 1   | socket it, don't solder down               |
| —         | DS18B20 waterproof probe, 1 m         | 1   | HiLetgo                                     |
| Fan 1/2   | Noctua NF-A4x20 5V PWM                | 1–2 | 0.1 A / 0.5 W each; Fan 2 optional          |
| J2, J3    | 4-pin fan header, 2.54 mm THT         | 2   | Molex 47053-1000 or equivalent              |
| J4        | 3-pos terminal block, 2.54 / 5.08 mm  | 1   | DS18B20 probe                               |
| J1        | 2-pos screw terminal / Powerpole      | 1   | 12 V supply entry                           |
| —         | 2× 15-pin female header               | 1 set | dev board socket                          |
| R1        | 4.7 kΩ resistor                       | 1   | 1-Wire pull-up                              |
| R2, R3    | 10 kΩ resistor                        | 1–2 | tach pull-ups, one per fan                  |

Current budget: each fan is **0.1 A / 0.5 W** (Noctua spec). The C6 module draws
on the order of 100 mA average with Wi-Fi up and a few hundred mA on transmit
peaks. Call it 0.55 A worst case — trivial for a USB-C connection, and well
inside any 2 A buck.

## Gotchas

- **Never pull a tach line up to +5 V.** The fan's tach transistor only pulls
  low; the pull-up sets the high level, and a 5 V pull-up puts 5 V straight onto
  a GPIO. R2/R3 go to `+3V3`.
- **Never plug a 5 V Noctua into a 12 V fan header.** It is destroyed instantly.
  The connector gives you no protection — it's the same part either way.
- **No PWM signal means full speed**, not stopped. If you probe or disconnect
  a PWM line with the fan powered, expect it to spin up.
- `reboot_timeout` in the `wifi:` block is set to `0s`. The ESPHome default is
  15 min, which reboots the device when WiFi is absent — undesirable here, since
  cooling stops while the board reboots. Cooling should not depend on the
  network.
- The ESPHome config also sets `INPUT_PULLUP` on the tach pins. That's belt and
  braces — the internal pull-up is ~45 kΩ, weak enough that a long fan lead can
  round the edge off. Keep the external 10 kΩ parts.
- PWM is driven push-pull at 3.3 V from the C6's LEDC peripheral. Noctua's 5 V
  PWM fans accept a 3.3 V control signal, so no level shifter is needed.
- Fan behaviour below ~20 % duty is not specified by the 4-wire standard. The
  config's `min_duty` default of 30 % exists for this reason. **The NF-A4x20 5V
  PWM does stop at 0 % duty** — verified on the bench, so single-fan mode really
  does leave Fan 2 stationary rather than idling.
- **If a fan runs constantly and its RPM reads a flat `0.00`, suspect PWM and
  tach swapped.** With the PWM line open the fan's internal pull-up holds it at
  100 %, and the pulse counter sits on a static line with no edges — so the fan
  appears to run at a "low level" (a 40 mm Noctua is only ~18 dB(A) flat out)
  and never responds to duty changes. Verify by **wire colour, not pin number**:
  blue is PWM, green is tach. Pin numbering is exactly what's in doubt when this
  happens.
