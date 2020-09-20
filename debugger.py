import numpy as np
import pdb
import argparse
from chip import Chip
from sys import maxsize
import re

class Debugger(object):
    recognized_commands = 'sbrpchqdf'

    def __init__(self, emu):
        self.emu = emu
        self.breakpoints = {}
        self.last_command = None
        self.last_breakpoint = 0

    def set_breakpoint(self, line):
        try:
            self.breakpoints[self.last_breakpoint] = int(line, 16)
        except ValueError:
            print("Invalid breakpoint not set")
        else:
            self.last_breakpoint += 1
            print("Breakpoint {num} set at line {line}".format(
                num=self.last_breakpoint,
                line=line))

    def remove_breakpoint(self, i):
        if i in self.breakpoints:
            del self.breakpoints[i]
            print("Breakpoint {0} deleted".format(i))
        else:
            print("No breakpoint found")

    def continue_to_breakpoint(self):
        while self.emu.pc not in self.breakpoints:
            self.emu.cycle()
            self.wait_for_input()
        emu._print_instruction()

    def wait_for_input(self):
        while self.emu.wait_for_input:
            print("Enter a key between 0 and 15")
            key = input('>')
            base = 16 if 'x' in key else 10
            try:
                key = int(key, base)
                self.emu.key_inputs[key] = 1
                self.emu.wait_for_input = False
            except:
                print("Did not understand")
            

    def continue_to_frame(self):
        while self.emu.memory[self.emu.pc] >> 4 != 0xd:
            self.emu.cycle()
            self.wait_for_input()

        # Cycle past the drw 
        self.emu.cycle()
        self.draw_display_buffer()


    def display(self, component, specification):
        if component == 'm':
            if specification is None:
                print(self.emu.memory)

            elif specification == 'i':
                print(self.emu.memory[self.emu.index])

            elif '+' in specification:
                start, length = specification.split('+')
                base = 16 if 'x' in start else 10

                start, length = int(start, base), int(length, base)
                print(self.emu.memory[start:start+length])

            elif bool(re.search(specification, '\d+')):
                print(self.emu.memory[int(specification)])
            
            elif bool(re.search(specification, '0x\d+')):
                print(self.emu.memory[int(specification, 16)])

        if component == 'r':
            if specification:
                base = 16 if 'x' in specification else 10
                print(self.emu.registers[int(specification, base)])
            else:
                print(self.emu.registers)

        if component == 'i':
            print(self.emu.index)

        if component == 's':
            print(self.emu.stack)

        if component == 'k':
            print(self.emu.key_inputs)

        if component == 'b':
            print("Breakpoints:")
            for i in self.breakpoints:
                print("{0} - {1:#06x}".format(i, self.breakpoints[i]))

    def repl(self):
        while True:
            cmd = input("> ").split()
            try:
                if cmd[0] in Debugger.recognized_commands:
                    self.process_command(*cmd)
                    self.last_command = cmd

                    if cmd[0] == 'q':
                       return 

            except IndexError:
                if self.last_command: 
                    self.process_command(*self.last_command)

    def draw_display_buffer(self):
        rows = "-" * (Chip.SCREEN_WIDTH + 2)+"\n"
        for y in range(Chip.SCREEN_HEIGHT - 1, -1, -1):
            row = "|"
            for x in range(Chip.SCREEN_WIDTH):
                if self.emu.display_buffer[x, y]: row += "▓"
                else: row += "░"
            row += "|\n"
            rows += row
        rows += "-" * (Chip.SCREEN_WIDTH + 2)
        print(rows)

    def print_help(self):
        print("\n".join([
                "h                  - Help",
                "q                  - Quit from debugger",
                "s                  - Step forward one instruction",
                "b [line]           - Set breakpoint at line",
                "r [breakpoint num] - Remove breakpoint",
                "c                  - Continue to next breakpoint",
                "f                  - Continue to next frame update",
                "d                  - Draw the display buffer",
                "p m                - Print memory",
                "p m [start]+[len]  - Print memory from starting address",
                "p m i              - Print memory at index",
                "p r [reg]          - Print a single register",
                "p r                - Print all registers",
                "p i                - Print index register",
                "p s                - Print stack",
                "p b                - Print current breakpoints",
                "p k                - Print key buffer"
            ]))

    def process_command(self, *cmd):
        try:
            if cmd[0] == 's':
                self.step()

            elif cmd[0] == 'b':
                self.set_breakpoint(cmd[1])

            elif cmd[0] == 'r':
                self.remove_breakpoint(cmd[1])

            elif cmd[0] == 'p':
                if len(cmd) > 2:
                    self.display(cmd[1], cmd[2])
                else:
                    self.display(cmd[1], None)

            elif cmd[0] == 'c':
                self.continue_to_breakpoint()

            elif cmd[0] == 'd':
                self.draw_display_buffer()

            elif cmd[0] == 'h':
                self.print_help()

            elif cmd[0] == 'f':
                self.continue_to_frame()

        except IndexError:
            print("Invalid command")

        except KeyboardInterrupt:
            return



    def step(self):
        self.emu.cycle()
        self.emu._print_instruction()


np.set_printoptions(threshold=maxsize)
emu = Chip()
debugger = Debugger(emu)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='Location of CHIP-8 ROM')
    args = parser.parse_args()
    filename = args.filename
    
    emu.load(filename)
    print("Debugging " + filename)
    print("Press 'h' to see commands")

    debugger.repl()

if __name__ == '__main__':
    main()
