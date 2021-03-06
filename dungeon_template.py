import pyglet
import sys
import random
from drawable import Drawable

class DungeonTemplate:

  EMPTY = 0
  FLOOR = 1
  WALL = 2
  CHEST = 3
  CHEST_STARTER = 4
  EXIT = 5

  WIDTH = 5
  HEIGHT = 5

  def __init__(self, game, pixels, i, exit=False):
    self.game = game
    self.pixels = pixels
    self.exits = []
    self.tile_types = []
    self.tile_type_cache = False
    self.exits_covered = False
    self.can_spawn_entity = True
    self.i = i

    self.tx = 0
    self.ty = 0
    for y in range(self.HEIGHT):
      for x in range(self.WIDTH):
        self.tile_types.append(self.type_at(x, y))
        if x == 0 or y == 0 or x == self.WIDTH-1 or y == self.HEIGHT-1:
          if self.is_floor(x, y):
            self.exits.append((x, y))

    if exit:
      self.tile_types[3*self.WIDTH+3] = self.EXIT

    self.tile_type_cache = True

  def set_chest_spawn(self, x, y, starter=False):
    self.tile_types[y*self.WIDTH+x] = self.CHEST_STARTER if starter else self.CHEST

  def clear_chest_spawns(self):
    for y in range(self.HEIGHT):
      for x in range(self.WIDTH):
        i = y*self.WIDTH+x
        if self.tile_types[i] == self.CHEST:
          self.tile_types[i] = self.FLOOR

  def exit_walls(self):
    exit_walls = [[],[],[],[]]
    for x, y in self.exits:
      exit_walls[self.exit_wall_index(x, y)].append((x, y))

    return exit_walls

  def exit_wall_index(self, x, y):
    if y == self.HEIGHT-1:
      return 0
    elif y == 0:
      return 2
    elif x == self.WIDTH-1:
      return 1
    else:
      return 3

  def remove_exit(self, x, y):
    if (x, y) in self.exits:
      self.exits.remove((x, y))
      self.tile_types[y*self.WIDTH+x] = self.WALL

  def pixel_at(self, x, y):
    return self.pixels[y*self.WIDTH + x]

  def type_at(self, x, y):
    if self.tile_type_cache:
      return self.tile_types[y*self.WIDTH + x]

    if self.is_floor(x, y):
      return self.FLOOR

    if self.is_wall(x, y):
      return self.WALL

    if self.is_chest(x, y):
      return self.CHEST

    return self.EMPTY

  def is_floor(self, x, y):
    return self.pixel_at(x,y) == (255, 255, 255)

  def is_wall(self, x, y):
    return self.pixel_at(x,y) == (255, 0, 0)

  def is_empty(self, x, y):
    return self.pixel_at(x,y) == (0, 0, 0)

  def is_chest(self, x, y):
    return self.pixel_at(x,y) == (0, 0, 255)