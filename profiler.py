import yapl
from sasm.plugins.regvm.parser import program
from pyinstrument import Profiler

prof = Profiler(interval=0.0001)
parse = yapl.parse_string(program)

code = """
reset:
    ld [$x] #0b00100010
    xor $x $a
    cmp [$x]
    psh $r5
loop:
    inc $y
    jmp loop
; this is a comment
fizz: .asciiz "Fizz"
buzz: .asciiz "Buzz"
n: .byte 0xfa
"""

def test():
    prof.start()
    print(parse(code))
    prof.stop()
    prof.open_in_browser()

if __name__ == "__main__":
    test()
