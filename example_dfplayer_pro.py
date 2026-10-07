"""Demo of dfplayer_pro.py on Raspberry Pi Pico (UART1: GP4=TX, GP5=RX)."""
from machine import UART, Pin
import time
from dfplayer_pro import DFPlayerPro, PlayMode, Function

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))
player = DFPlayerPro(uart)

print("Init...")
while not player.begin():
    print("  no answer, check wiring:", player.last_error)
    time.sleep(1)
print("DFPlayer Pro OK")

print("Function MUSIC:", player.switch_function(Function.MUSIC))
print("LED off:", player.set_led(False))
print("Prompt tone off:", player.set_prompt(False))
print("Enable AMP:", player.enable_amp())

print("Set volume 15:", player.set_vol(15), "-> get:", player.get_vol())
print("Volume (property):", player.volume)

print("Set mode ALLCYCLE:", player.set_play_mode(PlayMode.ALLCYCLE),
      "-> get:", player.play_mode)

print("Total files:", player.get_total_file())

print("Play file #1:", player.play_file_num(1))
time.sleep(2)
print("Current file no.:", player.get_cur_file_number())
print("File name:", player.get_file_name())
print("Time: %s / %s s" % (player.get_cur_time(), player.get_total_time()))
print("is_playing:", player.is_playing())

print("Fast forward 10 s:", player.fast_forward(10))
time.sleep(2)
print("Fast reverse 5 s:", player.fast_reverse(5))
time.sleep(2)
print("Set time to 3 s:", player.set_play_time(3))
time.sleep(2)

print("Pause:", player.pause())
time.sleep(2)
print("Start:", player.start())
time.sleep(2)

print("Next:", player.next())
time.sleep(3)
print("Now playing:", player.get_file_name())
print("Last:", player.last())
time.sleep(3)

# Play by path (adjust to a file existing on your module):
# print("Play path:", player.play_spec_file("/music/test.mp3"))
# print("Delete current file:", player.del_cur_file())   # destructive!
# print("Set baud:", player.set_baud_rate(115200))       # needs power cycle
# print("UFDISK mode:", player.switch_function(Function.UFDISK))

print("Pause and disable AMP:", player.pause(), player.disable_amp())
print("Done. last_error =", player.last_error)