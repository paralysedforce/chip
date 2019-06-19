import sys
import argparse
from chip import Chip

import pyglet
from pyglet.window import key, FPSDisplay

################################
#     Pyglet functions         #
################################

chip = Chip()
window = pyglet.window.Window()
fps_display = FPSDisplay(window)

@window.event
def on_draw():
    window.clear()
    draw(chip.display_buffer)
    fps_display.draw()

@window.event
def on_key_press(symbol, modifiers):
    try: 
        key_index = Chip.KEY_INPUTS[symbol]
        chip.key_inputs[key_index] = 1
        print(key_index)
    except KeyError:
        pass

@window.event
def on_key_release(symbol, modifiers):
    try:
        key_index = Chip.KEY_INPUTS[symbol]
        chip.key_inputs[key_index] = 0
    except KeyError:
        pass

def update(dt):
    chip.update()
    chip.should_draw = False

def draw(grid):
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if grid[i, j]:
                x = int(window.width * i / grid.shape[0])
                y = int(window.height * j / grid.shape[1])
                dx = int(window.width / grid.shape[0])
                dy = int(window.height / grid.shape[1])
                draw_rect(x, y, dx, dy)

def draw_rect(x, y, dx, dy):
    pyglet.graphics.draw_indexed(4, pyglet.gl.GL_TRIANGLES,
            [0, 1, 2, 2, 3, 0],
                ('v2i', (x, y,
                    x+dx, y,
                    x+dx, y+dy,
                    x, y+dy)))

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='Location of CHIP-8 ROM')
parser.add_argument('-d', '--debug', help='debug mode', action='store_true')
args = parser.parse_args()
Chip.DEBUG = args.debug

pyglet.clock.schedule_interval(update, 1/20.)
chip.load(args.filename)
pyglet.app.run()
