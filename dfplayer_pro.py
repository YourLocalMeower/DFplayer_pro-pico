"""MicroPython driver for DFRobot DFPlayer Pro (DF1201S) over UART (AT protocol).

Port of the Arduino library DFRobot_DF1201S, tuned for Raspberry Pi Pico.
"""
from machine import UART, Pin
import time


class DFPlayerError(Exception):
    """Module returned an unexpected / error response."""


class DFPlayerTimeout(DFPlayerError):
    """No (complete) response within the timeout."""


class Function:
    MUSIC = 1   # music mode
    UFDISK = 2  # USB slave (disk) mode


class PlayMode:
    SINGLECYCLE = 1  # repeat one
    ALLCYCLE = 2     # repeat all
    SINGLE = 3       # play one, stop
    RANDOM = 4
    FOLDER = 5       # repeat folder
    ERROR = 6        # returned when the reply cannot be parsed


class DFPlayerPro:
    """Driver for DFPlayer Pro.

    Args:
        uart: ready machine.UART object, or None to create one from pins.
        tx, rx: pin numbers used when uart is None (default UART1, GP4/GP5).
        baudrate: baud rate for a newly created UART.
        timeout_ms: default timeout for a command reply.
        raise_errors: True -> raise DFPlayerError/Timeout,
                      False -> methods return False/None and keep err in last_error.
    """

    def __init__(self, uart=None, tx=4, rx=5, baudrate=115200, uart_id=1,
                 timeout_ms=1500, raise_errors=False):
        if uart is None:
            uart = UART(uart_id, baudrate=baudrate, tx=Pin(tx), rx=Pin(rx))
        self._uart = uart
        self.timeout_ms = timeout_ms
        self.raise_errors = raise_errors
        self.last_error = None
        self._function = Function.MUSIC
        self._playing = False  # tracks the PLAY=PP toggle (like pauseFlag)

    # ------------------------------------------------------------ low level
    def _fail(self, exc):
        self.last_error = str(exc)
        if self.raise_errors:
            raise exc
        return None

    def _flush(self):
        while self._uart.any():
            self._uart.read()

    def _read(self, timeout_ms=None, utf16=False):
        """Read until CRLF (for utf16: CRLF aligned to a 2-byte boundary)."""
        end = time.ticks_add(time.ticks_ms(), timeout_ms or self.timeout_ms)
        buf = bytearray()
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            if self._uart.any():
                buf.extend(self._uart.read())
                if buf.endswith(b"\r\n") and (not utf16 or len(buf) % 2 == 0):
                    return bytes(buf)
            else:
                time.sleep_ms(2)
        raise DFPlayerTimeout("timeout, got %r" % bytes(buf))

    def _send(self, cmd=None, param=None):
        s = "AT"
        if cmd:
            s += "+" + cmd
        if param is not None:
            s += "=" + str(param)
        self._flush()
        self._uart.write(s + "\r\n")

    def _ack(self, cmd=None, param=None, timeout_ms=None):
        """Send command, expect OK. Returns True/False (or raises)."""
        try:
            self._send(cmd, param)
            resp = self._read(timeout_ms)
            if resp.startswith(b"OK"):
                self.last_error = None
                return True
            raise DFPlayerError("unexpected reply %r" % resp)
        except DFPlayerError as e:
            self._fail(e)
            return False

    @staticmethod
    def _int(data):
        """First run of digits in bytes -> int (None if absent)."""
        n, found = 0, False
        for b in data:
            if 48 <= b <= 57:
                n, found = n * 10 + b - 48, True
            elif found:
                break
        return n if found else None

    def _query(self, cmd, param):
        """Send query, return int from reply or None."""
        try:
            self._send(cmd, param)
            val = self._int(self._read())
            if val is None:
                raise DFPlayerError("no number in reply")
            self.last_error = None
            return val
        except DFPlayerError as e:
            return self._fail(e)

    def _music_only(self):
        if self._function != Function.MUSIC:
            self._fail(DFPlayerError("command requires MUSIC function"))
            return False
        return True

    # ------------------------------------------------------------- general
    def begin(self, retries=3):
        """Check communication with `AT`. Returns True when module answers OK."""
        for _ in range(retries):
            if self._ack():
                self._playing = False
                return True
            time.sleep_ms(200)
        return False

    init = begin

    def set_baud_rate(self, baud):
        """Set baud rate (9600..115200); needs module power cycle to apply."""
        return self._ack("BAUDRATE", baud)

    def set_led(self, on):
        """Indicator LED on/off (stored in module)."""
        return self._ack("LED", "ON" if on else "OFF")

    def set_prompt(self, on):
        """Prompt tone on/off (stored in module)."""
        return self._ack("PROMPT", "ON" if on else "OFF")

    def switch_function(self, function):
        """Switch Function.MUSIC / Function.UFDISK (module needs ~1.5 s)."""
        self._playing = False
        if self._ack("FUNCTION", function):
            self._function = function
            time.sleep_ms(1500)
            return True
        return False

    # -------------------------------------------------------------- volume
    def set_vol(self, vol):
        """Volume 0-30."""
        if not 0 <= vol <= 30:
            self._fail(ValueError("volume must be 0-30"))
            return False
        return self._ack("VOL", vol)

    def get_vol(self):
        """Return volume (int) or None."""
        return self._query("VOL", "?")

    volume = property(get_vol, set_vol)

    # ----------------------------------------------------------- play mode
    def set_play_mode(self, mode):
        """Set PlayMode.* (MUSIC function only)."""
        if not self._music_only():
            return False
        return self._ack("PLAYMODE", mode)

    def get_play_mode(self):
        """Return PlayMode.* (PlayMode.ERROR on failure)."""
        v = self._query("PLAYMODE", "?")
        return v if v in (1, 2, 3, 4, 5) else PlayMode.ERROR

    play_mode = property(get_play_mode, set_play_mode)

    # ------------------------------------------------------------ transport
    def next(self):
        if not self._music_only():
            return False
        ok = self._ack("PLAY", "NEXT")
        self._playing = ok or self._playing
        return ok

    def last(self):
        if not self._music_only():
            return False
        ok = self._ack("PLAY", "LAST")
        self._playing = ok or self._playing
        return ok

    def start(self):
        """Play/resume. Returns False if already playing (PP is a toggle)."""
        if self._playing:
            return False
        if self._ack("PLAY", "PP"):
            self._playing = True
            return True
        return False

    def pause(self):
        """Pause. Returns False if not playing."""
        if not self._playing:
            return False
        if self._ack("PLAY", "PP"):
            self._playing = False
            return True
        return False

    def is_playing(self, interval=1.0):
        """Check if time advances over `interval` s; refreshes internal state."""
        t = self.get_cur_time()
        time.sleep_ms(int(interval * 1000))
        t2 = self.get_cur_time()
        self._playing = t is not None and t2 is not None and t2 != t
        return self._playing

    def del_cur_file(self):
        """Delete currently playing file."""
        if not self._music_only():
            return False
        self._playing = False
        return self._ack("DEL")

    def play_spec_file(self, path):
        """Play file by path, e.g. '/music/song.mp3'."""
        if not self._music_only():
            return False
        ok = self._ack("PLAYFILE", path)
        self._playing = ok or self._playing
        return ok

    def play_file_num(self, num):
        """Play file by number (order copied to disk)."""
        if not self._music_only():
            return False
        ok = self._ack("PLAYNUM", num)
        self._playing = ok or self._playing
        return ok

    # ---------------------------------------------------------------- time
    def _time_cmd(self, param):
        if not self._music_only():
            return False
        self.start()  # module ignores TIME while paused (as in Arduino lib)
        return self._ack("TIME", param)

    def fast_forward(self, seconds):
        return self._time_cmd("+%d" % seconds)

    def fast_reverse(self, seconds):
        return self._time_cmd("-%d" % seconds)

    def set_play_time(self, seconds):
        """Jump to absolute position in seconds."""
        return self._time_cmd(seconds)

    # --------------------------------------------------------------- query
    def get_cur_file_number(self):
        return self._query("QUERY", 1) if self._music_only() else None

    def get_total_file(self):
        return self._query("QUERY", 2) if self._music_only() else None

    def get_cur_time(self):
        return self._query("QUERY", 3) if self._music_only() else None

    def get_total_time(self):
        return self._query("QUERY", 4) if self._music_only() else None

    def get_file_name(self):
        """Name of current file (module sends UTF-16LE). None on error."""
        if not self._music_only():
            return None
        try:
            self._send("QUERY", 5)
            raw = self._read(utf16=True)
        except DFPlayerError as e:
            return self._fail(e)
        name = ""
        for i in range(0, len(raw) - 1, 2):
            code = raw[i] | (raw[i + 1] << 8)
            if code == 0x0A0D:
                break
            name += chr(code)
        return name

    # ----------------------------------------------------------------- amp
    def enable_amp(self):
        return self._music_only() and self._ack("AMP", "ON")

    def disable_amp(self):
        return self._music_only() and self._ack("AMP", "OFF")