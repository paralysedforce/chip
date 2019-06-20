"""
A Chip-8 Emulator written in Python
"""

from __future__ import print_function, division
import pdb
import numpy as np
from pyglet.window import key


# Decorator to defer evaluation of instructions
def instruction(func, *args, **kwargs):
    def wrapper(*args, **kwargs):
        def internal_wrapper():
            return func(*args, **kwargs)
        internal_wrapper.__name__ = func.__name__[1:] +' '+ kwargs.get('mode', '')

        return internal_wrapper

    return wrapper


class Chip(object):
    DEBUG = False

    PC_OFFSET = 0x200
    SCREEN_WIDTH = 64
    SCREEN_HEIGHT = 32
    KEY_INPUTS = { 
            key._1: 0x1, key._2: 0x2, key._3: 0x3, key._4: 0xc,
            key.Q: 0x4, key.W: 0x5, key.E: 0x6, key.R: 0xd,
            key.A: 0x7, key.S: 0x8, key.D: 0x9, key.F: 0xe,
            key.Z: 0xa, key.X: 0x0, key.C: 0xB, key.V: 0xf}

    def __init__(self):
        self.display_buffer = np.zeros((Chip.SCREEN_WIDTH, Chip.SCREEN_HEIGHT), dtype=np.uint8)

        self.key_inputs = np.zeros(16, dtype=np.uint8)
        self.memory = np.zeros(4096, dtype=np.uint8)
        # General purpose registers
        self.registers = np.zeros(16, dtype=np.uint8)

        # Timing registers
        self.sound_timer = np.uint8(0)
        self.delay_timer = np.uint8(0)

        # Special 16-bit registers
        self.index = np.uint16(0)
        self.pc = np.uint16(Chip.PC_OFFSET) # Loaded with offset of code into memory

        # Program stack
        self.stack = []

        self.opcode_map = self._construct_opcode_map()
        self.fonts = self._construct_fonts()

        # Additional flags for convenience
        self.should_draw = False
        self.has_exit = False

# Loading data into memory
    def load(self, rom_filename):
        print('Loading...', end=' - ')
        self._load_fonts()
        self._load_rom(rom_filename)
        print('Done')

    def _load_fonts(self):
        for char in range(0x10):
            for i in range(5):
                mem_index = char * 5 + i
                self.memory[mem_index] = self.fonts[char][i]

    def _load_rom(self, rom_filename):
        with open(rom_filename, 'rb') as rom_file:
            binary = rom_file.read()
            for i in range(len(binary)):
                self.memory[i + Chip.PC_OFFSET] = binary[i]

    def cycle(self):
        opcode = self.memory[self.pc] << 8
        opcode |= self.memory[self.pc + 1]


        if Chip.DEBUG:
            self._print_instruction()
            pdb.set_trace()

        self._process_opcode(opcode)
        self.pc += 2
        self._process_output()

    def _process_opcode(self, opcode):
        try:
            self.opcode_map[opcode]()
        except KeyError:
            print("Opcode not recognized 0x{:04x}".format(opcode))
            sys.exit(0)

    def _process_output(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1

        if self.sound_timer > 0:
            self.sound_timer -= 1


    def update(self):
        while not self.should_draw:
            self.dispatch_events()
            self.cycle()
            if self.has_exit:
                break

    def dispatch_events(self):
        pass


    def _construct_fonts(self):
        # Each pre-loaded letter is 5 bytes in width
        # I can't really think of a better way to do this 
        return {
            0x0: [0xF0, 0x90, 0x90, 0x90, 0xF0],
            0x1: [0x20, 0x60, 0x20, 0x20, 0x70],
            0x2: [0xF0, 0x10, 0xF0, 0x80, 0xF0],
            0x3: [0xF0, 0x10, 0xF0, 0x10, 0xF0],
            0x4: [0x90, 0x90, 0xF0, 0x10, 0x10],
            0x5: [0xF0, 0x80, 0xF0, 0x10, 0xF0],
            0x6: [0xF0, 0x80, 0xF0, 0x90, 0xF0],
            0x7: [0xF0, 0x10, 0x20, 0x40, 0x40],
            0x8: [0xF0, 0x90, 0xF0, 0x90, 0xF0],
            0x9: [0xF0, 0x90, 0xF0, 0x10, 0xF0],
            0xA: [0xF0, 0x90, 0xF0, 0x90, 0x90],
            0xB: [0xE0, 0x90, 0xE0, 0x90, 0xE0],
            0xC: [0xF0, 0x80, 0x80, 0x80, 0xF0],
            0xD: [0xE0, 0x90, 0x90, 0x90, 0xE0],
            0xE: [0xF0, 0x80, 0xF0, 0x80, 0xF0],
            0xF: [0xF0, 0x80, 0xF0, 0x80, 0x80]
        }

    # Somebody make a pull request and tell me how to make this function
    # actually idiomatic :(
    def _construct_opcode_map(self):
        # Iterate through every single byte and populate opcode_map to be 
        #   byte -> function(void)
        opcode_map = {}


        # Use bitwise-or to implement the ISA
        #   since 0xa000 | 0xbcd = 0xabcd
        for xyz in range(0x000, 0xfff + 1):
            # Get continuous nibbles 
            x = (xyz & 0xf00) >> 8
            y = (xyz & 0x0f0) >> 4
            z =  xyz & 0x00f

            # Get continuous bytes
            xy = (xyz & 0xff0) >> 4
            yz =  xyz & 0xff

            # Begin defining the map
            # See http://devernay.free.fr/hacks/chip8/C8TECH10.HTM for specs

            # 0x0xyz instructions are ignored in emulators besides for ret and cls
            opcode_map[0x0000 | xyz] = self._sys(xyz)

            opcode_map[0x1000 | xyz] =  self._jp(xyz, mode='ABSOLUTE')
            opcode_map[0x2000 | xyz] =  self._call(xyz)
            opcode_map[0x3000 | xyz] =  self._se(x, yz, mode='BYTE')
            opcode_map[0x4000 | xyz] =  self._sne(x, yz, mode='BYTE') 

            if z == 0:
                opcode_map[0x5000 | xyz] =  self._se(x, y, mode='REGISTER')

            opcode_map[0x6000 | xyz] =  self._ld(x, yz, mode='BYTE')
            opcode_map[0x7000 | xyz] =  self._add(x, yz, mode='BYTE')

            if z == 0:
                opcode_map[0x8000 | xyz] =  self._ld(x, y, mode='REGISTER')
            elif z == 0x1:
                opcode_map[0x8000 | xyz] =  self._or(x, y)
            elif z == 0x2:
                opcode_map[0x8000 | xyz] =  self._and(x, y)
            elif z == 0x3:
                opcode_map[0x8000 | xyz] =  self._xor(x, y) 
            elif z == 0x4:
                opcode_map[0x8000 | xyz] =  self._add(x, y, mode='REGISTER')
            elif z == 0x5:
                opcode_map[0x8000 | xyz] =  self._sub(x, y)
            elif z == 0x6:
                opcode_map[0x8000 | xyz] =  self._shr(x, y)
            elif z == 0x7:
                opcode_map[0x8000 | xyz] =  self._subn(x, y) 
            elif z == 0xe:
                opcode_map[0x8000 | xyz] =  self._shl(x, y)

            if z == 0x0:
                opcode_map[0x9000 | xyz] =  self._sne(x, y, mode='REGISTER')

            opcode_map[0xa000 | xyz] =  self._ld(None, xyz, mode='INDEX')
            opcode_map[0xb000 | xyz] =  self._jp(xyz, mode='RELATIVE')
            opcode_map[0xc000 | xyz] =  self._rnd(x, yz)
            opcode_map[0xd000 | xyz] =  self._drw(x, y, z)

            if yz == 0x9e:
                opcode_map[0xe000 | xyz] =  self._skp(x)
            elif yz == 0xa1:
                opcode_map[0xe000 | xyz] =  self._sknp(x)

            if yz == 0x07:
                opcode_map[0xf000 | xyz] =  self._ld(x, None, mode='DELAY')
            elif yz == 0x0a:
                opcode_map[0xf000 | xyz] =  self._ld(x, None, mode='KEY')
            elif yz == 0x15:
                opcode_map[0xf000 | xyz] =  self._ld(None, x, mode='DELAY')
            elif yz == 0x18:
                opcode_map[0xf000 | xyz] =  self._ld(None, x, mode='SOUND')
            elif yz == 0x1e:
                opcode_map[0xf000 | xyz] =  self._add(x, None, mode='INDEX')
            elif yz == 0x29:
                opcode_map[0xf000 | xyz] =  self._ld(None, x, mode='SPRITE')
            elif yz == 0x33:
                opcode_map[0xf000 | xyz] =  self._ld(None, x, mode='BCD')
            elif yz == 0x55:
                opcode_map[0xf000 | xyz] =  self._ld(x, None,
                        mode='STORE_CONT_INDEX')

            elif yz == 0x65:
                opcode_map[0xf000 | xyz] =  self._ld(x, None,
                        mode='READ_CONT_INDEX')

        opcode_map[0x00e0] =  self._cls()
        opcode_map[0x00ee] =  self._ret()
        return opcode_map

    # Opcode implementations #
    @instruction
    def _cls(self):
        self.display_buffer = np.zeros((64, 32), dtype=np.uint8)

    @instruction
    def _ret(self):
        self.pc = self.stack.pop()

    @instruction
    def _jp(self, addr, mode=None):
        if mode == 'ABSOLUTE':
            self.pc = addr - 2
        elif mode == 'RELATIVE':
            self.pc = addr + self.registers[0] - 2
        else:
            raise ValueError('Invalid Instruction Mode')
            
    @instruction
    def _call(self, addr):
        self.stack.append(self.pc)
        self.pc = addr - 2

    @instruction
    def _se(self, val1, val2, mode=None):
        if mode == 'BYTE':
            if self.registers[val1] == val2:
                self.pc += 2
        elif mode == 'REGISTER':
            if self.registers[val1] == self.registers[val2]:
                self.pc += 2
        else:
            raise ValueError('Invalid Instruction Mode')

    @instruction
    def _sne(self, val1, val2, mode=None):
        if mode == 'BYTE':
            if self.registers[val1] != val2:
                self.pc += 2
        elif mode == 'REGISTER':
            if self.registers[val1] != self.registers[val2]:
                self.pc += 2
        else:
            raise ValueError('Invalid Instruction Mode')

    @instruction
    def _add(self, val1, val2, mode=None):
        if mode == 'BYTE':
            self.registers[val1] += val2

        elif mode == 'REGISTER':
            # Set flag if overflow
            flag_val = self.registers[val1] > 0xff - self.registers[val2]
            self._set_flag(flag_val)

            # Perform addition
            self.registers[val1] += self.registers[val2]

        elif mode == 'INDEX':
            self.index += self.registers[val1]

        else:
            raise ValueError('Invalid Instruction Mode')

    @instruction
    def _or(self, x, y):
        self.registers[x] |= self.registers[y]

    @instruction
    def _and(self, x, y):
        self.registers[x] &= self.registers[y]

    @instruction
    def _xor(self, x, y):
        self.registers[x] ^= self.registers[y]

    @instruction
    def _sub(self, x, y):
        flag_val = self.registers[x] > self.registers[y]
        self._set_flag(flag_val)
        self.registers[x] -= self.registers[y]

    @instruction
    def _shr(self, x, y):
        # Flag is set to least significant bit of Vx
        flag_val = bool(self.registers[x] & 0x01)
        self._set_flag(flag_val)

        self.registers[x] = self.registers[x] >> 1
    
    
    @instruction
    def _shl(self, x, y):
        # Flag is set to most significant bit  of Vx
        flag_val = bool(self.registers[x] & 0x80)
        self._set_flag(flag_val)

        self.registers[x] = self.registers[x] << 1

    @instruction
    def _subn(self, x, y):
        # Flag is set to NOT borrow
        flag_val = self.registers[y] > self.registers[x]
        self._set_flag(flag_val)

        self.registers[x] = self.registers[y] - self.registers[x]

    @instruction
    def _rnd(self, x, yz):
        random_byte = np.random.randint(0x00, 0x100)
        self.registers[x] = np.uint8(yz & random_byte)

    @instruction
    def _drw(self, x, y, n):
        flag_val = False

        def is_bit_set(byte, shift):
            return ((0x80 >> shift) & byte) >> (7 - shift)

        for y_offset in range(n):
            sprite_byte = self.memory[self.index + y_offset]

            for x_offset in range(8):
                x_coordinate = (self.registers[x] + x_offset) % Chip.SCREEN_WIDTH
                y_coordinate = (self.registers[y] + y_offset) % Chip.SCREEN_HEIGHT

                # Because pyglet considers (0, 0) as bottom-left
                y_coordinate = Chip.SCREEN_HEIGHT - y_coordinate - 1

                sprite_val = is_bit_set(sprite_byte, x_offset)

                if self.display_buffer[x_coordinate, y_coordinate] and sprite_val:
                    flag_val = True

                self.display_buffer[x_coordinate, y_coordinate] ^= sprite_val

        self._set_flag(flag_val)
        self.should_draw = True

    @instruction
    def _sys(self, addr):
        return
#        self.pc = addr

    @instruction
    def _skp(self, x):
        key_index = self.registers[x]
        if self.key_inputs[key_index]:
            self.pc += 2

    @instruction
    def _sknp(self, x):
        key_index = self.registers[x]
        if not self.key_inputs[key_index]:
            self.pc += 2



    @instruction
    def _ld(self, src, dest, mode=None):
        if mode == 'BYTE':
            self.registers[src] = dest
        elif mode == 'REGISTER':
            self.registers[src] = self.registers[dest]
        elif mode == 'INDEX':
            if src and not dest:
                self.registers[src] = self.index
            elif dest and not src:
                self.index = dest
            else:
                raise ValueError('Invalid Instruction Mode')
        elif mode == 'DELAY':
            self.registers[src] = self.delay_timer
        elif mode == 'SOUND':
            self.registers[src] = self.sound_timer
        elif mode == 'SPRITE':
            self.index = 5 * self.registers[dest]

        elif mode == 'BCD':
            # Store the base-10 values of dest in memory
            hundreds_addr = self.index
            tens_addr = self.index + 1
            ones_addr = self.index + 2
            val = self.registers[dest]

            hundreds_digit = val // 100
            tens_digit = (val % 100) // 10
            ones_digit = val % 10

            self.memory[hundreds_addr] = hundreds_digit
            self.memory[tens_addr] = tens_digit
            self.memory[ones_addr] = ones_digit

        elif mode == 'READ_CONT_INDEX':
            # Read registers V0 through Vx from memory starting at location I.
            for i in range(src+1):
                self.registers[i] = self.memory[self.index + i]

        elif mode == 'STORE_CONT_INDEX':
            # Store registers V0 through Vx in memory starting at location I.
            for i in range(src+1):
                self.memory[self.index + i] = self.registers[i]
        elif mode == 'KEY':
            if 1 not in self.key_inputs:
                self.pc -= 2
            else:
                self.registers[src] = np.argmax(self.key_inputs)

        else:
            raise ValueError('Invalid Instruction Mode')

    # Helper function to abstract dealing with flags
    def _set_flag(self, flag_val):
        self.registers[0xf] = np.uint8(flag_val)

    def _print_instruction(self):
        opcode = self.memory[self.pc] << 8
        opcode |= self.memory[self.pc + 1]

        print("PC: 0x{:04x}".format(self.pc))
        print("OPCODE: 0x{:04x}".format(opcode), end=' - ')
        print(self.opcode_map[opcode].__name__)

