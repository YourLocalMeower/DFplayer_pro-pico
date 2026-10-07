# dfplayer_pro – MicroPython driver for DFPlayer Pro (DF1201S)

## !!THIS WAS MADE USING AI!!

MicroPython port of the Arduino library [DFRobot_DF1201S](https://github.com/DFRobot/DFRobot_DF1201S),
tuned for the Raspberry Pi Pico (RP2040). It talks to the module over UART using the AT protocol
(115200 baud, 8N1, commands end with `\r\n`). Only built-in modules (`machine`, `time`) are used.

## Files

| File | Description |
|---|---|
| `dfplayer_pro.py` | The driver (`DFPlayerPro`, `PlayMode`, `Function`, exceptions) |
| `example_dfplayer_pro.py` | Plug-and-play demo of almost every method |

## Wiring (UART0)

| DFPlayer Pro | Raspberry Pi Pico |
|---|---|
| VCC | 3V3 (pin 36) or VBUS 5 V (pin 40) |
| GND | GND (e.g. pin 3 or 38) |
| RX | GP0 – UART0 TX (pin 1) |
| TX | GP1 – UART0 RX (pin 2) |

- TX and RX are crossed.
- Connect a speaker (up to 3 W) to SPK+ / SPK–. Use a 5 V supply for louder playback.
- Copy MP3 files to the module through its own USB port (it appears as a disk drive).

## Quick start

1. Copy `dfplayer_pro.py` and `example_dfplayer_pro.py` to the Pico.
2. Run the example, or use the driver directly:

```python
from machine import UART, Pin
from dfplayer_pro import DFPlayerPro, PlayMode

player = DFPlayerPro(UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1)))
# or simply: player = DFPlayerPro()   # defaults to UART0, GP0/GP1, 115200

if player.begin():
    player.set_vol(15)
    player.set_play_mode(PlayMode.ALLCYCLE)
    player.play_file_num(1)
    print(player.get_file_name(), player.get_cur_time(), "/", player.get_total_time())
```

## Constructor

```python
DFPlayerPro(uart=None, tx=0, rx=1, baudrate=115200, uart_id=0,
            timeout_ms=1500, raise_errors=False)
```

- `uart` – existing `machine.UART`; if `None`, one is created from `uart_id`, `tx`, `rx`, `baudrate`.
- `timeout_ms` – default reply timeout per command.
- `raise_errors` – `False`: methods return `False`/`None` and set `last_error`.
  `True`: raise `DFPlayerError` / `DFPlayerTimeout`.

## API

Constants: `Function.MUSIC`, `Function.UFDISK`;
`PlayMode.SINGLECYCLE`, `ALLCYCLE`, `SINGLE`, `RANDOM`, `FOLDER`, `ERROR`.

| Method | Arduino equivalent | Returns |
|---|---|---|
| `begin()` / `init()` | `begin` | bool |
| `is_playing(interval=1.0)` | `isPlaying` | bool |
| `set_baud_rate(baud)` | `setBaudRate` | bool (power-cycle needed) |
| `set_play_mode(mode)` / `get_play_mode()` / `play_mode` | `setPlayMode` / `getPlayMode` | bool / `PlayMode` |
| `set_led(on)` | `setLED` | bool |
| `set_prompt(on)` | `setPrompt` | bool |
| `set_vol(0-30)` / `get_vol()` / `volume` | `setVol` / `getVol` | bool / int |
| `switch_function(function)` | `switchFunction` | bool |
| `next()` / `last()` | `next` / `last` | bool |
| `start()` / `pause()` | `start` / `pause` | bool |
| `del_cur_file()` | `delCurFile` | bool |
| `play_spec_file(path)` | `playSpecFile` | bool |
| `play_file_num(num)` | `playFileNum` | bool |
| `get_cur_file_number()` | `getCurFileNumber` | int / None |
| `get_total_file()` | `getTotalFile` | int / None |
| `get_cur_time()` / `get_total_time()` | `getCurTime` / `getTotalTime` | seconds / None |
| `get_file_name()` | `getFileName` | str / None |
| `enable_amp()` / `disable_amp()` | `enableAMP` / `disableAMP` | bool |
| `fast_forward(s)` / `fast_reverse(s)` | `fastForward` / `fastReverse` | bool |
| `set_play_time(s)` | `setPlayTime` | bool |

## Notes

- `start()` / `pause()` use the module's `PLAY=PP` toggle, tracked by an internal flag (like `pauseFlag`
  in the Arduino library). If the module starts playing on its own after power-up, call `is_playing()`
  once to resync.
- Most commands only work in `Function.MUSIC`; otherwise they return `False` and set `last_error`.
- `get_file_name()` decodes the module's UTF-16LE reply manually (MicroPython has no such codec).
- `switch_function()` blocks for ~1.5 s while the module reconfigures.
- `del_cur_file()` permanently deletes the file from the module.
- The driver was written by AI from the Arduino source and the AT protocol and has not been tested on hardware;
  adjust timeouts if your module is slow to answer.
