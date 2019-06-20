import numpy as np
from chip import Chip
import pdb
import re

MAX_BREAKPOINTS = 10

class Debugger(object):
    recognized_commands = 'sbrpc'

    def __init__(self, emu):
        self.emu = emu
        self.breakpoints = np.zeros(MAX_BREAKPOINTS)
        self.last_command = None

    def set_breakpoint(self, line):
        for i in range(MAX_BREAKPOINTS):
            if self.breakpoints[i] == 0:
                try:
                    self.breakpoints[i] = int(line,16)
                except ValueError:
                    print("Invalid line number.")
                    return
                print("Breakpoint " + str(i) + " set at " + str(line))
                return
        print("Breakpoint not set. Delete an existing breakpoint to continue.")

    def remove_breakpoint(self, i):
        try:
            i = int(i)
            if self.breakpoints[i]:
                self.breakpoints[i] = 0
        except IndexError:
            print("Enter a number between 0 and " + MAX_BREAKPOINTS)

    def continue_to_breakpoint(self):
        if all(self.breakpoints == 0):
            print("No breakpoints. Cannot continue.")
            return
        while self.emu.pc not in self.breakpoints:
            self.emu.cycle()
        emu._print_instruction()

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
            print(self.emu.registers)

        if component == 'i':
            print(self.emu.index)

        if component == 's':
            print(self.emu.stack)

        if component == 'd':
            print(self.emu.display_buffer)


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
                self.process_command(*self.last_command)

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
                pdb.set_trace()

        except IndexError:
            print("Invalid command")


    def step(self):
        self.emu.cycle()
        self.emu._print_instruction()


np.set_printoptions(threshold=np.nan)
emu = Chip()
debugger = Debugger(emu)

def main():
    filename = "roms/test_opcode.ch8"
    emu.load(filename)
    print("Debugging " + filename)

    debugger.repl()

if __name__ == '__main__':
    main()
