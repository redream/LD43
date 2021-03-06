import pyglet
import sys
import random
from drawable import Drawable
from grass_tile import GrassTile
from goat import Goat
from text_box import TextBox
from pyglet import image
from dungeon_template import DungeonTemplate
from dungeon_tile import DungeonTile
from dungeon_entry import DungeonEntry
from inventory import Inventory
from character import Character
from water_gem import WaterGem
from fire_gem import FireGem
from earth_gem import EarthGem
from item import Item
import copy
from pyglet.window import key

class World(Drawable):

  HEIGHT = [12, 32]
  WIDTH = [12, 32]

  GROUPS_PER_TILE = 32

  OVERWORLD = 0
  DUNGEON = 1

  TITLE = 0
  INTRO = 1
  USE_SEEDS = 2
  USED_SEEDS = 3
  ENCOUNTER = 4
  ENCOUNTER_TEXT = 5
  SACRIFICING = 6
  SACRIFICING_TEXT = 7
  FREE_ROAM = 8
  SKULLS_FOUND = 9
  TITLE_COMPLETE = 10

  def __init__(self, game):
    super().__init__(game)
    self.game = game
    self.state = self.OVERWORLD
    self.progression = self.TITLE

    self.inventory = None
    self.tiles = [[], []]
    self.entities = [[], []]
    self.groups = [[pyglet.graphics.OrderedGroup(self.HEIGHT[j] * self.GROUPS_PER_TILE - i) for i in range((self.HEIGHT[j]+1)*self.GROUPS_PER_TILE)] for j in range(2)]

    self.dungeon_entry = None
    self.skulls_collected = False
    self.has_init = [False, False]

    self.sacrifice_mode = False
    self.hud_group = pyglet.graphics.OrderedGroup(self.HEIGHT[self.DUNGEON] * self.GROUPS_PER_TILE + 1)
    self.textbox = TextBox(game, 10, 10, self.hud_group, 200, 60)
    self.hud_element = True

    self.title_i = self.init_sprite('title.png', self.hud_group)

    self.sprites[self.title_i].scale_x = 4
    self.sprites[self.title_i].scale_y = 4
    self.sprites_rel[self.title_i] = (self.game.camera.x, self.game.camera.y)
    self.title_label = pyglet.text.Label('SPACE to begin', font_size=7, x=10, y=10, color=(255,255,255,255))

    self.character = Character(game, 6, 6, self.group_for(1))
    self.game.camera.target = self.character

    #self.inventory = Inventory(self.game, self.game.camera.width / self.game.camera.zoom - Inventory.WIDTH - 10, 10, self.hud_group)

    self.last_hover = None
    self.hover_dt = 0
    self.first_dungeon_visit = True
    self.progression_dt = 0
    self.move_to = None

    self.state_dt = 0

  def group_for(self, ty, layer=None):
    if layer is None:
      layer = self.state

    if layer is self.DUNGEON:
      off = self.game.dungeon_offset / self.game.TILE_WIDTH
      if ty > off - 20:
        ty -= off

    if ty < 0 or ty >= len(self.groups[layer]):
      return self.groups[layer][0]

    return self.groups[layer][int((ty+1) // 0.03215)]

  def tile_at(self, tx, ty, layer=0):
    if tx < 0 or tx >= self.WIDTH[layer] or ty < 0 or ty >= self.HEIGHT[layer]:
      return False
    tx = int(tx)
    ty = int(ty)
    return self.tiles[layer][ty*self.WIDTH[layer] + tx]

  def move_to_dungeon(self):
    self.progression = self.FREE_ROAM
    self.state = self.DUNGEON
    tx, ty = self.WIDTH[self.DUNGEON] // 2 + 2.5, self.HEIGHT[self.DUNGEON] // 2 + 2.5
    self.character.tx = tx + self.game.dungeon_offset / self.game.TILE_WIDTH + 0.92
    self.character.ty = ty + self.game.dungeon_offset / self.game.TILE_HEIGHT + 0.9
    self.character.x = tx * self.game.TILE_WIDTH
    self.character.y = ty * self.game.TILE_HEIGHT
    self.character.vx, self.character.vy = 0, 0
    self.game.camera.move_to_target()

  def move_to_overworld(self):
    if self.skulls_collected and self.progression == self.FREE_ROAM:
      self.progression = self.SKULLS_FOUND
      self.textbox.text = ["Oh! You found my goat skull. I knew I left it somewhere!",
                           "Farewell stranger. Your days of sacrificing goats is over."]
      self.textbox.faces = [2, 2]
    else:
      self.progression = self.FREE_ROAM

    self.state = self.OVERWORLD
    for i in range(len(self.tiles[self.DUNGEON])):
      tile = self.tiles[self.DUNGEON][i]
      if tile is not None:
        tile.delete()

    self.tiles[self.DUNGEON] = []
    self.has_init[self.DUNGEON] = False
    tx = self.dungeon_entry.tx if self.dungeon_entry else 5
    ty = self.dungeon_entry.ty + 1 if self.dungeon_entry else 5
    self.character.tx = tx
    self.character.ty = ty
    self.character.x = tx * self.game.TILE_WIDTH
    self.character.y = ty * self.game.TILE_HEIGHT
    self.game.camera.move_to_target()

  def update(self, dt):
    Drawable.handle_deletion(self.entities[self.state])
    self.state_dt += dt

    if self.move_to == self.DUNGEON:
      self.move_to_dungeon()
      self.move_to = None
      self.state_dt = 0
    elif self.move_to == self.OVERWORLD:
      self.move_to_overworld()
      self.move_to = None
      self.state_dt = 0

    if self.character.health <= 0:
      self.move_to_overworld()
      self.character.health = 8
      self.textbox.text = ["That was close! I've saved you this time, but don't test your luck."]
      self.textbox.faces = [2]

    if self.progression == self.SKULLS_FOUND and len(self.textbox.text) == 0:
      self.progression = self.TITLE_COMPLETE
      self.sprites[self.title_i].visible = True
      self.sprites_rel[self.title_i] = (self.character.x - 30, self.character.y - 80)
      self.need_pos_update = True

    if self.progression == self.TITLE and self.game.keys[key.SPACE]:
      self.sprites[self.title_i].visible = False
      self.progression = self.INTRO
      self.textbox.text = ["It's another sunny day in your hometown.",
                           "Your uncle Jim has left you to look after his goat farm.",
                           "Choose the grass seeds and LEFT CLICK to use."]

    if self.progression == self.USED_SEEDS and self.textbox and len(self.textbox.text) == 0:
      self.progression_dt += dt
      if self.progression_dt > 8:
        self.progression_dt = 0
        self.progression = self.ENCOUNTER

    if self.progression == self.ENCOUNTER:
      if self.dungeon_entry is None and self.character.ty > 2 and self.character.tx > 1 and self.character.tx + 2 < self.WIDTH[self.OVERWORLD] and self.character.ty + 1 < self.HEIGHT[self.OVERWORLD]:
        self.dungeon_entry = DungeonEntry(self.game, self.character.tx+1, self.character.ty-1, self.group_for(self.character.ty-1))

      if self.dungeon_entry and self.dungeon_entry.progress == 3 and self.dungeon_entry.char_dt >= 2:
        self.progression = self.ENCOUNTER_TEXT
        self.textbox.text = ["MORTAL! What are you doing on my grounds?!",
                             "!!!",
                             "I.. this is my uncle's property! I'm sorry!",
                             "Ah. I see. Well, since it isn't your fault, I have a deal for you.",
                             "I need to sacrifice a goat. In exchange, I will give you rewards beyond your wildest dreams.",
                             "What? I can't. That would be cruel!",
                             "LEFT CLICK a goat to choose a sacrifice."]

        self.textbox.faces = [2, 1, 1, 2, 2, 1, None]

    if self.progression == self.ENCOUNTER_TEXT and self.textbox and len(self.textbox.text) == 0:
      self.progression = self.SACRIFICING
      self.sacrifice_mode = True

    if self.progression == self.INTRO and self.textbox and len(self.textbox.text) == 0:
      self.progression = self.USE_SEEDS
      self.inventory = Inventory(self.game, self.game.camera.width / self.game.camera.zoom - Inventory.WIDTH - 10, 10, self.hud_group)

    if self.progression == self.SACRIFICING_TEXT and self.textbox and len(self.textbox.text) == 2:
      self.game.camera.target = self.character

    if self.progression == self.SACRIFICING_TEXT and self.textbox and len(self.textbox.text) == 0:
      self.inventory.add_item(WaterGem(self.game, 25))
      self.textbox.text = ["How strange. Maybe I should check out that crevice.."]
      self.textbox.faces = [1]
      self.dungeon_entry.remove_character = True
      self.progression = self.FREE_ROAM

    #if self.progression == self.FREE_ROAM and self.state == self.OVERWORLD:
    #  self.progression_dt += dt
    #  if self.progression_dt > 5:
    #    self.progression_dt = 0

    if not self.has_init[self.OVERWORLD] and self.state == self.OVERWORLD:
      for i in range(random.randint(10, 30)):
        tx = (random.random() * self.WIDTH[self.OVERWORLD] - 1) + 1
        ty = (random.random() * self.HEIGHT[self.OVERWORLD] - 1) + 1
        self.entities[self.OVERWORLD].append(Goat(self.game, tx, ty, self.group_for(ty)))

      for ty in range(self.HEIGHT[self.OVERWORLD]):
        for tx in range(self.WIDTH[self.OVERWORLD]):
          self.tiles[self.OVERWORLD].append(GrassTile(self.game, tx, ty, self.group_for(ty+1)))
      self.has_init[self.OVERWORLD] = True

    if not self.has_init[self.DUNGEON] and self.state == self.DUNGEON:
      rooms = image.load('sprites/dungeon_rooms.png')
      raw_image = rooms.get_image_data()
      img_format = 'RGB'
      pitch = raw_image.width * len(img_format)
      pixels = raw_image.get_data(img_format, pitch)
      room_width = DungeonTemplate.WIDTH
      room_height = DungeonTemplate.HEIGHT
      dungeon_templates = []
      for i in range(raw_image.width // room_width):
        room_pixels = []
        for j in range(room_height):
          for ii in range(room_width):
            room_pixels.append(tuple([int(pixels[p + len(img_format) * (j * raw_image.width + i*room_width + ii)]) for p in range(len(img_format))]))

        for rot in range(4):
          if rot > 0:
            room_pixels_temp = []
            for y in range(room_height):
              for x in range(room_width):
                # 90 degrees rotation CW
                j = x * room_width + (room_height - y - 1)
                room_pixels_temp.append(room_pixels[j])
            room_pixels = room_pixels_temp
          template = DungeonTemplate(self.game, copy.copy(room_pixels), i, i == 0)
          dungeon_templates.append(template)

      room_instances = [copy.copy(dungeon_templates[0])]
      tx, ty = self.WIDTH[self.DUNGEON] // 2, self.HEIGHT[self.DUNGEON] // 2
      room_instances[0].tx = tx
      room_instances[0].ty = ty
      if self.first_dungeon_visit:
        room_instances[0].can_spawn_entity = False
        room_instances[0].clear_chest_spawns()
        room_instances[0].set_chest_spawn(1, 3, True)
        self.first_dungeon_visit = False
      exits_uncovered = [(tx, ty)]
      occupied = [(tx, ty)]

      while len(exits_uncovered) > 0:
        random.shuffle(dungeon_templates)
        tx, ty = exits_uncovered.pop(0)
        for instance in room_instances:
          if (instance.tx, instance.ty) == (tx, ty):
            missed_exits = instance.exit_walls()
            missed_walls = [len(missed_exits[i]) > 0 for i in range(4)]
            for (ix, iy) in instance.exits:
              if not missed_walls[instance.exit_wall_index(ix, iy)]:
                continue

              for template in dungeon_templates:
                if template.i == instance.i:
                  continue

                found_match = False
                new_coords = False
                for (ex, ey) in template.exits:
                  if ix == 0 and ey == iy and ex == room_width - 1:
                    found_match = (-1, 0)
                  elif iy == 0 and ex == ix and ey == room_height - 1:
                    found_match = (0, -1)
                  elif ix == room_width - 1 and ey == iy and ex == 0:
                    found_match = (1, 0)
                  elif iy == room_height - 1 and ex == ix and ey == 0:
                    found_match = (0, 1)

                  if found_match:
                    new_coords = (tx + found_match[0] * room_width, ty + found_match[1] * room_height)
                    if new_coords in occupied:
                      found_match = False
                    else:
                      break
                if found_match:
                  break

              if found_match and new_coords:
                new_instance = copy.copy(template)
                new_instance.tx, new_instance.ty = new_coords
                if new_instance.tx >= 0 and new_instance.tx + 5 < self.WIDTH[self.DUNGEON] and new_instance.ty >= 0 and new_instance.ty + 5 < self.HEIGHT[self.DUNGEON]:
                  room_instances.append(new_instance)
                  exits_uncovered.append(new_coords)
                  occupied.append(new_coords)
                  dungeon_templates.remove(template)
                  missed_walls[instance.exit_wall_index(ix, iy)] = False
                  missed_exits[instance.exit_wall_index(ix, iy)].remove((ix, iy))
                  new_instance.exits.remove((ex, ey))

                found_match = False
                new_coords = False

            for i in range(len(missed_exits)):
              for ix, iy in missed_exits[i]:
                instance.remove_exit(ix, iy)

      temp_tiles = [None for _ in range(self.HEIGHT[self.DUNGEON]) for _ in range(self.WIDTH[self.DUNGEON])]
      count = 0
      for instance in room_instances:
        for x in range(room_width):
          for y in range(room_height):
            tx = x + instance.tx
            ty = y + instance.ty
            j = ty*self.WIDTH[self.DUNGEON] + tx
            i = y*room_width + x
            temp_tiles[j] = DungeonTile(self.game, tx, ty, self.group_for(ty, self.DUNGEON), instance.tile_types[i])
            temp_tiles[j].can_spawn_entity = instance.can_spawn_entity

      self.tiles[self.DUNGEON] = temp_tiles

      for tile in self.tiles[self.DUNGEON]:
        if tile:
          tile.init_tile()

      self.has_init[self.DUNGEON] = True
      self.change_state(self.DUNGEON)

    if self.last_hover:
      self.hover_dt += dt

    if self.last_hover and self.hover_dt >= 0.05 and self.sacrifice_mode and self.state == self.OVERWORLD:
      mouse_hover = self.update_hover()

      self.hover_dt = 0
      self.last_hover = None
      self.game.cursor = self.game.window.CURSOR_HAND if mouse_hover else self.game.window.CURSOR_DEFAULT

    for drawable in self.tiles[self.state] + self.entities[self.state] + [self.textbox, self.inventory, self.character, self.dungeon_entry]:
      if drawable:
        drawable.update(dt)

    super().update(dt)

  def update_hover(self):
    mouse_hover = False

    for entity in self.entities[self.OVERWORLD]:
      entity.hovered = entity.mouse_in_bounds(*self.last_hover)
      mouse_hover = entity.hovered
      if mouse_hover:
        break

    return mouse_hover

  def on_click(self, x, y):
    if self.inventory is not None:
      tx = x / self.game.TILE_WIDTH
      ty = y / self.game.TILE_HEIGHT

      selected = self.inventory.selected_spell()
      if selected is not None:
        selected.fire(tx, ty, self.character)

      selected = self.inventory.selected_item()
      if selected and selected.name == 'Grass Seeds':
        self.character.spawn_seeds(tx, ty)

        self.inventory.remove_item(Item.GRASS_SEEDS)

        if self.state == self.OVERWORLD:
          tile = self.tile_at(tx, ty)
          if isinstance(tile, GrassTile):
            for i in range(3):
              tile.spawn_grass(True, tx, ty)
            if self.progression == self.USE_SEEDS:
              self.progression = self.USED_SEEDS
              self.textbox.text = ["It's so relaxing! Boy, what a wonderful day.",
                                   "Maybe I should plant some more seeds.",
                                   "Use WASD to move.",]
              self.textbox.faces = [1, 1, None]
        return

    if not self.sacrifice_mode:
      return

    self.last_hover = (x, y)
    self.update_hover()
    for entity in self.entities[self.OVERWORLD]:
      if entity.hovered and isinstance(entity, Goat):
        entity.spawn_flames()
        entity.dying = True

        if self.progression == self.SACRIFICING:
          self.game.camera.target = entity

        self.sacrifice_mode = False
        self.game.cursor = self.game.window.CURSOR_DEFAULT

        if self.progression == self.FREE_ROAM:
          gems = [WaterGem, EarthGem, FireGem]
          for i in range(len(gems)):
            gem = gems[i]
            count = random.randint(0, max(self.game.world.character.level*5-i*2+2,0))
            if count > 0:
              self.inventory.add_item(gem(self.game, count))

        if self.progression == self.SACRIFICING:
          self.progression = self.SACRIFICING_TEXT
          self.textbox.text = ["Well, you got what you wanted.",
                               "I never wanted to sacrifice a goat!",
                               "Here is your reward. If you sacrifice more goats, I will reward you again.",
                               "I must go now!"]
          self.textbox.faces = [2, 1, 2, 2]

        break


  def on_mouse_motion(self, x, y, dx, dy):
    self.last_hover = (x, y)

  def change_state(self, state):
    self.state = state
    other_state = 1 - state

  def draw(self, hud=False):
    for drawable in self.tiles[self.state] + self.entities[self.state] + [self.textbox, self.inventory, self.character, self.dungeon_entry]:
      if drawable and drawable.hud_element == hud:
        drawable.draw()

    if self.progression == self.TITLE:
      self.title_label.draw()
    super().draw()