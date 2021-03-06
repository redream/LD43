import pyglet
pyglet.options['debug_gl'] = False
from pyglet.gl import *
from pyglet.graphics import Batch
from pyglet.image.atlas import TextureBin
from pyglet.window import mouse
from camera import Camera
from world import World
import sys
import cProfile
import math
from pyglet.window import key

#glEnable(GL_DEPTH_TEST)
#glEnable(GL_BLEND)
#glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
#glEnable(GL_ALPHA_TEST)
#glAlphaFunc(GL_GREATER, .1)
glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

class Game:
  bin = TextureBin()
  bin_loaded = {}

  batch = Batch()
  hud_batch = Batch()

  TILE_HEIGHT = 32
  TILE_WIDTH = 32

  CHEST_XP = 5
  KILL_XP = 5

  def __init__(self):
    self.entity_count = 0
    self.cull_sprites = []
    self.dungeon_offset = self.TILE_WIDTH * 512
    self.window = pyglet.window.Window()
    self.camera = Camera(self)
    self.keys = key.KeyStateHandler()
    self.window.push_handlers(self.keys)
    self.world = World(self)
    self.cursor = self.window.CURSOR_DEFAULT
    self.set_cursor = None

  def aabb_intersects(self, hitbox1, hitbox2):
    xa1, ya1, xb1, yb1 = hitbox1
    xa2, ya2, xb2, yb2 = hitbox2

    xt = xa1 < xb2 and xb1 > xa2
    yt = ya1 < yb2 and yb1 > ya2

    return xt and yt

game = Game()
fps_display = pyglet.clock.ClockDisplay()

def main():
  pyglet.app.run()

def update(dt):
  game.camera.update(dt)
  game.world.update(dt)
  if game.set_cursor != game.cursor:
    game.window.set_mouse_cursor(game.window.get_system_mouse_cursor(game.cursor))
    game.set_cursor = game.cursor

pyglet.clock.schedule_interval(update, 1.0/60.0)
pyglet.clock.set_fps_limit(60)

def transform_mouse_coords(x, y, hud=False):
  if hud:
    x /= game.camera.hud_zoom
    y /= game.camera.hud_zoom
    return x, y

  x -= game.camera.width // 2
  y -= game.camera.height // 2
  x /= game.camera.zoom
  y /= game.camera.zoom
  x += game.camera.x
  y += game.camera.y
  return x, y

@game.window.event
def on_mouse_motion(x, y, dx, dy):
  gx, gy = transform_mouse_coords(x, y)
  hx, hy = transform_mouse_coords(x, y, True)
  if game.world.inventory:
    game.world.inventory.on_mouse_motion(hx, hy, dx, dy)
  game.world.on_mouse_motion(gx, gy, dx, dy)

@game.window.event
def on_mouse_press(x, y, button, modifiers):
  if button == mouse.RIGHT:
    if game.world.inventory:
      game.world.inventory.on_right_click(x,y)
  if button == mouse.LEFT:
    gx, gy = transform_mouse_coords(x, y)
    hx, hy = transform_mouse_coords(x, y, True)

    if game.world.inventory:
      if not game.world.inventory.on_click(hx, hy):
        game.world.on_click(gx, gy)
        game.world.inventory.selected_i = None
    else:
      game.world.on_click(gx, gy)


@game.window.event
def on_draw():
  game.window.clear()
  game.camera.apply()
  game.world.draw()
  game.batch.draw()
  game.camera.apply_hud()
  game.hud_batch.draw()
  game.world.draw(True)
  #fps_display.draw()

if __name__ == '__main__':
  main()#cProfile.run('main()')