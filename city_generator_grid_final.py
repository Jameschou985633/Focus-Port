"""
Hybrid procedural city generator for Blender.

City core + natural terrain fusion:
- strict occupancy grid (0 empty / 1 road / 2 building / 3 nature)
- terrain grid + height map (river, banks, paths, cliffs, platforms)
- meandering river, curved roads, irregular zoning, clustered greenery
- full base ground tiles and bright cartoon render settings
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import bpy


EMPTY = 0
ROAD = 1
BUILDING = 2
NATURE = 3

TG_GRASS = 0
TG_RIVER = 1
TG_BANK = 2
TG_PATH = 3
TG_CLIFF = 4
TG_PLATFORM = 5

DIRS = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
ORTHO = (0.0, math.pi * 0.5, math.pi, math.pi * 1.5)


@dataclass
class Config:
    seed: int = 20260404
    grid_size: int = 44
    tile_size: float = 2.0
    model_scale: float = 1.0
    height_step: float = 1.8
    river_depth: float = 0.45

    irregularity_level: str = "medium_high"
    terrain_enabled: bool = True
    height_layers_max: int = 2
    river_width_range: Tuple[int, int] = (1, 2)
    zone_noise_scale: float = 0.18
    zone_noise_strength: float = 0.22
    green_corridor_strength: float = 0.65
    perf_profile: str = "balanced"

    city_roads_root: str = r"C:\Users\86153\Downloads\asset\kenney_city-kit-roads\Models\OBJ format"
    commercial_root: str = r"C:\Users\86153\Downloads\asset\kenney_city-kit-commercial_2.1\Models\OBJ format"
    industrial_root: str = r"C:\Users\86153\Downloads\asset\kenney_city-kit-industrial_1.0\Models\OBJ format"
    suburban_root: str = r"C:\Users\86153\Downloads\asset\kenney_city-kit-suburban_20\Models\OBJ format"
    nature_root: str = r"C:\Users\86153\PycharmProjects\PythonProject2\kenney_assets\nature-kit\Models\OBJ format"


CITY_ASSETS = {
    "roads": ["road-straight", "road-crossroad", "road-bend", "road-intersection"],
    "cbd": [f"building-skyscraper-{c}" for c in "abcde"],
    "commercial": [f"building-{c}" for c in "abcdefghijklmn"],
    "residential": [f"building-type-{c}" for c in "abcdefghijklmnopqrstu"],
    "industrial": [f"building-{c}" for c in "abcdefghijklmnopqrst"],
    "industrial_details": ["chimney-large", "detail-tank"],
    "greenery": ["tree-large", "tree-small", "planter"],
}

NATURE_ASSETS = {
    "river": {
        "straight": "ground_riverStraight",
        "bend": "ground_riverBend",
        "corner": "ground_riverCorner",
        "cross": "ground_riverCross",
        "end": "ground_riverEnd",
        "split": "ground_riverSplit",
        "side": "ground_riverSide",
        "bank": "ground_riverBendBank",
        "tile": "ground_riverTile",
        "rocks": "ground_riverRocks",
    },
    "path": {
        "straight": "ground_pathStraight",
        "bend": "ground_pathBend",
        "corner": "ground_pathCorner",
        "cross": "ground_pathCross",
        "end": "ground_pathEnd",
        "split": "ground_pathSplit",
        "tile": "ground_pathTile",
        "rocks": "ground_pathRocks",
    },
    "cliff": {
        "block": "cliff_block_rock",
        "corner": "cliff_corner_rock",
        "steps": "cliff_steps_rock",
        "waterfall": "cliff_waterfall_rock",
        "waterfall_top": "cliff_waterfallTop_rock",
    },
    "platform": {"grass": "platform_grass", "stone": "platform_stone"},
    "ground": {"grass": "ground_grass"},
}


@dataclass
class Template:
    name: str
    root: bpy.types.Object


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def bresenham(a: Tuple[int, int], b: Tuple[int, int]) -> List[Tuple[int, int]]:
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    out: List[Tuple[int, int]] = []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return out


class OccupancyGrid:
    def __init__(self, size: int) -> None:
        self.size = size
        self.grid = [[0 for _ in range(size)] for _ in range(size)]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def get(self, x: int, y: int) -> Optional[int]:
        return self.grid[x][y] if self.in_bounds(x, y) else None

    def set_force(self, x: int, y: int, value: int) -> None:
        if self.in_bounds(x, y):
            self.grid[x][y] = value

    def occupy(self, x: int, y: int, value: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        if self.grid[x][y] != EMPTY:
            return False
        self.grid[x][y] = value
        return True

    def iter_cells(self) -> Iterable[Tuple[int, int]]:
        for x in range(self.size):
            for y in range(self.size):
                yield x, y


class TerrainGrid:
    def __init__(self, size: int) -> None:
        self.size = size
        self.terrain = [[TG_GRASS for _ in range(size)] for _ in range(size)]
        self.height = [[0 for _ in range(size)] for _ in range(size)]
        self.river_cells: Set[Tuple[int, int]] = set()
        self.bank_cells: Set[Tuple[int, int]] = set()
        self.curved_road_cells: Set[Tuple[int, int]] = set()
        self.path_cells: Set[Tuple[int, int]] = set()
        self.park_cells: Set[Tuple[int, int]] = set()
        self.platform_cells: Set[Tuple[int, int]] = set()
        self.cliff_edges: Dict[Tuple[int, int], Set[str]] = {}
        self.bridge_cells: Set[Tuple[int, int]] = set()
        self.waterfall_top: Optional[Tuple[int, int, str]] = None
        self.waterfall_bottom: Optional[Tuple[int, int, str]] = None

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def height_of(self, x: int, y: int) -> int:
        return self.height[x][y] if self.in_bounds(x, y) else 0

    def set_height(self, x: int, y: int, h: int, max_layers: int) -> None:
        if self.in_bounds(x, y):
            self.height[x][y] = clamp(max(self.height[x][y], h), 0, max_layers)


class SceneIO:
    def __init__(self) -> None:
        self.root = self._new_col("HYB_CITY_ROOT", bpy.context.scene.collection)
        self.templates_col = self._new_col("HYB_TEMPLATES", bpy.context.scene.collection)
        self.ground_col = self._new_col("HYB_GROUND", self.root)
        self.river_col = self._new_col("HYB_RIVER", self.root)
        self.road_col = self._new_col("HYB_ROADS", self.root)
        self.path_col = self._new_col("HYB_PATHS", self.root)
        self.cliff_col = self._new_col("HYB_CLIFFS", self.root)
        self.platform_col = self._new_col("HYB_PLATFORMS", self.root)
        self.building_col = self._new_col("HYB_BUILDINGS", self.root)
        self.green_col = self._new_col("HYB_GREENERY", self.root)
        self.lights_col = self._new_col("HYB_LIGHTS", self.root)
        self.templates_col.hide_viewport = True
        self.templates_col.hide_render = True

    def _new_col(self, name: str, parent: bpy.types.Collection) -> bpy.types.Collection:
        old = bpy.data.collections.get(name)
        if old is not None:
            self._remove_col(old)
        col = bpy.data.collections.new(name)
        parent.children.link(col)
        return col

    def _remove_col(self, col: bpy.types.Collection) -> None:
        for child in list(col.children):
            self._remove_col(child)
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        root = bpy.context.scene.collection
        if col in root.children:
            root.children.unlink(col)
        for p in bpy.data.collections:
            if col in p.children:
                p.children.unlink(col)
        bpy.data.collections.remove(col)

    def import_template(self, name: str, filepath: str) -> Template:
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)
        before = set(bpy.data.objects)
        bpy.ops.object.select_all(action="DESELECT")
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except Exception:
            bpy.ops.import_scene.obj(filepath=filepath)
        imported = [o for o in bpy.data.objects if o not in before]
        if not imported:
            raise RuntimeError(f"OBJ import failed: {filepath}")
        root = bpy.data.objects.new(f"SRC__{name}", None)
        self.templates_col.objects.link(root)
        imported_set = set(imported)
        for obj in imported:
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            self.templates_col.objects.link(obj)
            if obj.parent not in imported_set:
                obj.parent = root
                obj.matrix_parent_inverse = root.matrix_world.inverted()
        return Template(name=name, root=root)

    def _dup(self, src: bpy.types.Object, col: bpy.types.Collection, parent: Optional[bpy.types.Object]) -> bpy.types.Object:
        d = src.copy()
        if src.data:
            d.data = src.data
        d.animation_data_clear()
        col.objects.link(d)
        d.parent = parent
        d.matrix_local = src.matrix_local.copy()
        for child in src.children:
            self._dup(child, col, d)
        return d

    def instance(self, tpl: Template, col: bpy.types.Collection, loc: Tuple[float, float, float], rot_z: float, scale: float) -> bpy.types.Object:
        root = self._dup(tpl.root, col, None)
        root.location = loc
        root.rotation_euler = (0.0, 0.0, rot_z)
        root.scale = (scale, scale, scale)
        return root


class AssetLibrary:
    def __init__(self, cfg: Config, io: SceneIO, rng: random.Random) -> None:
        self.cfg = cfg
        self.io = io
        self.rng = rng
        self.templates: Dict[str, Template] = {}

    def load(self) -> None:
        all_assets: List[Tuple[str, str]] = []
        for n in CITY_ASSETS["roads"]:
            all_assets.append((n, self.cfg.city_roads_root))
        for n in CITY_ASSETS["cbd"] + CITY_ASSETS["commercial"]:
            all_assets.append((n, self.cfg.commercial_root))
        for n in CITY_ASSETS["residential"] + CITY_ASSETS["greenery"]:
            all_assets.append((n, self.cfg.suburban_root))
        for n in CITY_ASSETS["industrial"] + CITY_ASSETS["industrial_details"]:
            all_assets.append((n, self.cfg.industrial_root))
        for grp in NATURE_ASSETS.values():
            for v in grp.values():
                all_assets.append((v, self.cfg.nature_root))
        seen: Set[str] = set()
        for name, root in all_assets:
            if name in seen:
                continue
            seen.add(name)
            self.templates[name] = self.io.import_template(name, os.path.join(root, f"{name}.obj"))

    def get(self, name: str) -> Template:
        return self.templates[name]

    def pick(self, names: Sequence[str]) -> Template:
        return self.templates[self.rng.choice(list(names))]


class MaterialFactory:
    def __init__(self) -> None:
        self.cache: Dict[str, bpy.types.Material] = {}

    def get(self, key: str, color: Tuple[float, float, float], roughness: float = 0.85) -> bpy.types.Material:
        if key in self.cache:
            return self.cache[key]
        m = bpy.data.materials.new(key)
        m.use_nodes = True
        n = m.node_tree.nodes
        l = m.node_tree.links
        n.clear()
        bsdf = n.new("ShaderNodeBsdfPrincipled")
        out = n.new("ShaderNodeOutputMaterial")
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
        l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        self.cache[key] = m
        return m


class CityGeneratorHybrid:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.grid = OccupancyGrid(cfg.grid_size)
        self.terrain = TerrainGrid(cfg.grid_size)
        self.io = SceneIO()
        self.assets = AssetLibrary(cfg, self.io, self.rng)
        self.materials = MaterialFactory()
        self.center = (cfg.grid_size - 1) * 0.5
        self.zone_map: Dict[Tuple[int, int], str] = {}
        self.buildings: List[Tuple[int, int, str, float]] = []
        self.greenery_plan: List[Tuple[str, int, int, float, float, float]] = []
        self.conflicts = 0
        self.max_buildings = 580 if cfg.perf_profile == "balanced" else 900
        self.max_green_objects = 2300 if cfg.perf_profile == "balanced" else 1200

    def world(self, x: int, y: int, z: float = 0.0) -> Tuple[float, float, float]:
        return (x - self.center) * self.cfg.tile_size, (y - self.center) * self.cfg.tile_size, z

    def run(self) -> None:
        self._setup_render()
        self.assets.load()
        self._generate_river()
        self._generate_highlands()
        self._generate_curved_roads()
        self._generate_scenic_paths()
        self._zone_and_buildables()
        self._plan_buildings()
        self._plan_greenery()
        self._sync_occupancy()
        self._place_ground()
        self._place_river_path()
        self._place_cliff_platform()
        self._place_roads_and_buildings()
        self._place_greenery()
        self._run_validations()

    def _setup_render(self) -> None:
        scn = bpy.context.scene
        scn.view_settings.view_transform = "Standard"
        scn.view_settings.look = "High Contrast"
        scn.view_settings.exposure = 0.35
        if scn.world is None:
            scn.world = bpy.data.worlds.new("World")
        scn.world.use_nodes = True
        bg = scn.world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs["Color"].default_value = (0.72, 0.86, 1.0, 1.0)
            bg.inputs["Strength"].default_value = 1.25
        sun = bpy.data.lights.new("HYB_SUN", "SUN")
        sun.energy = 7.0
        sun.color = (1.0, 0.95, 0.85)
        o = bpy.data.objects.new("HYB_SUN", sun)
        o.location = (0.0, 0.0, 90.0)
        o.rotation_euler = (math.radians(52), 0.0, math.radians(32))
        self.io.lights_col.objects.link(o)
        area = bpy.data.lights.new("HYB_FILL", "AREA")
        area.energy = 9500.0
        area.color = (0.75, 0.88, 1.0)
        area.shape = "RECTANGLE"
        area.size = self.cfg.grid_size * self.cfg.tile_size * 1.2
        area.size_y = self.cfg.grid_size * self.cfg.tile_size * 1.2
        ao = bpy.data.objects.new("HYB_FILL", area)
        ao.location = (0.0, 0.0, 70.0)
        ao.rotation_euler = (math.radians(180), 0.0, 0.0)
        self.io.lights_col.objects.link(ao)

    def _zone_noise(self, x: int, y: int) -> float:
        s = self.cfg.zone_noise_scale
        a = math.sin((x + self.cfg.seed * 0.01) * s)
        b = math.cos((y - self.cfg.seed * 0.01) * s * 1.23)
        c = math.sin((x + y) * s * 0.67 + 1.7)
        return (a + b + c) / 3.0

    def _generate_river(self) -> None:
        mid = int(self.cfg.grid_size * 0.50)
        amp1 = self.cfg.grid_size * 0.13
        amp2 = self.cfg.grid_size * 0.06
        f1, f2 = 0.18, 0.43
        p1, p2 = self.rng.uniform(0.0, math.tau), self.rng.uniform(0.0, math.tau)
        centerline: Dict[int, int] = {}
        prev: Optional[Tuple[int, int]] = None
        for x in range(self.cfg.grid_size):
            y = int(
                round(
                    mid
                    + amp1 * math.sin(f1 * x + p1)
                    + amp2 * math.sin(f2 * x + p2)
                    + self.rng.uniform(-1.0, 1.0)
                )
            )
            y = clamp(y, 2, self.cfg.grid_size - 3)
            centerline[x] = y
            seg = [(x, y)] if prev is None else bresenham(prev, (x, y))
            prev = (x, y)
            for sx, sy in seg:
                w = self.rng.randint(self.cfg.river_width_range[0], self.cfg.river_width_range[1])
                for oy in range(-w, w + 1):
                    if self.terrain.in_bounds(sx, sy + oy):
                        self.terrain.river_cells.add((sx, sy + oy))

        for x, y in list(self.terrain.river_cells):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if self.terrain.in_bounds(nx, ny) and (nx, ny) not in self.terrain.river_cells:
                        self.terrain.bank_cells.add((nx, ny))

        for rx in (int(self.cfg.grid_size * 0.33), int(self.cfg.grid_size * 0.67)):
            cy = centerline.get(rx, mid)
            for oy in (-1, 0, 1):
                c = (rx, clamp(cy + oy, 0, self.cfg.grid_size - 1))
                self.terrain.river_cells.discard(c)
                self.terrain.bank_cells.add(c)
                self.terrain.bridge_cells.add(c)

    def _generate_highlands(self) -> None:
        if not self.cfg.terrain_enabled:
            return
        seeds = [
            (4, 4),
            (self.cfg.grid_size - 5, self.cfg.grid_size - 5),
            (int(self.center + self.rng.randint(-4, 4)), int(self.center + self.rng.randint(-4, 4))),
        ]
        for i, (sx, sy) in enumerate(seeds):
            outer, inner = (7, 3) if i < 2 else (6, 3)
            for x, y in self.grid.iter_cells():
                if (x, y) in self.terrain.river_cells:
                    continue
                d = math.hypot(x - sx, y - sy)
                if d <= inner:
                    self.terrain.set_height(x, y, 2, self.cfg.height_layers_max)
                elif d <= outer:
                    self.terrain.set_height(x, y, 1, self.cfg.height_layers_max)

        for x, y in self.grid.iter_cells():
            h = self.terrain.height_of(x, y)
            if h >= 2 and (x, y) not in self.terrain.river_cells:
                self.terrain.platform_cells.add((x, y))
            if h <= 0:
                continue
            drops: Set[str] = set()
            for d, (dx, dy) in DIRS.items():
                if self.terrain.height_of(x + dx, y + dy) < h:
                    drops.add(d)
            if drops:
                self.terrain.cliff_edges[(x, y)] = drops

        wf: List[Tuple[int, int, str]] = []
        for (x, y), drops in self.terrain.cliff_edges.items():
            for d in drops:
                dx, dy = DIRS[d]
                if (x + dx, y + dy) in self.terrain.river_cells:
                    wf.append((x, y, d))
        if wf:
            x, y, d = self.rng.choice(wf)
            dx, dy = DIRS[d]
            self.terrain.waterfall_top = (x, y, d)
            self.terrain.waterfall_bottom = (x + dx, y + dy, d)

    def _road_cell_allowed(self, x: int, y: int) -> bool:
        if not self.terrain.in_bounds(x, y):
            return False
        if (x, y) in self.terrain.river_cells and (x, y) not in self.terrain.bridge_cells:
            return False
        if (x, y) in self.terrain.platform_cells:
            return False
        if self.terrain.height_of(x, y) > 1:
            return False
        return True

    def _generate_curved_roads(self) -> None:
        p1, p2 = self.rng.uniform(0, math.tau), self.rng.uniform(0, math.tau)
        prev = None
        for x in range(self.cfg.grid_size):
            y = int(round(self.cfg.grid_size * 0.35 + 2.2 * math.sin(x * 0.19 + p1)))
            y = clamp(y, 1, self.cfg.grid_size - 2)
            curr = (x, y)
            seg = [curr] if prev is None else bresenham(prev, curr)
            prev = curr
            for sx, sy in seg:
                if self._road_cell_allowed(sx, sy):
                    self.terrain.curved_road_cells.add((sx, sy))

        prev = None
        for y in range(self.cfg.grid_size):
            x = int(round(self.cfg.grid_size * 0.64 + 2.0 * math.sin(y * 0.17 + p2)))
            x = clamp(x, 1, self.cfg.grid_size - 2)
            curr = (x, y)
            seg = [curr] if prev is None else bresenham(prev, curr)
            prev = curr
            for sx, sy in seg:
                if self._road_cell_allowed(sx, sy):
                    self.terrain.curved_road_cells.add((sx, sy))

        roads = list(self.terrain.curved_road_cells)
        self.rng.shuffle(roads)
        for sx, sy in roads[:18]:
            dx, dy = self.rng.choice(list(DIRS.values()))
            x, y = sx, sy
            for _ in range(self.rng.randint(5, 11)):
                x += dx
                y += dy
                if not self._road_cell_allowed(x, y):
                    break
                self.terrain.curved_road_cells.add((x, y))
        self.terrain.curved_road_cells |= self.terrain.bridge_cells

    def _generate_scenic_paths(self) -> None:
        starts = list(self.terrain.bank_cells)
        self.rng.shuffle(starts)
        starts = starts[:8]
        for sx, sy in starts:
            x, y = sx, sy
            dx, dy = self.rng.choice(list(DIRS.values()))
            for _ in range(self.rng.randint(10, 24)):
                if not self.terrain.in_bounds(x, y):
                    break
                if (x, y) not in self.terrain.river_cells and (x, y) not in self.terrain.curved_road_cells:
                    self.terrain.path_cells.add((x, y))
                options = []
                for ndx, ndy in DIRS.values():
                    nx, ny = x + ndx, y + ndy
                    if not self.terrain.in_bounds(nx, ny):
                        continue
                    if (nx, ny) in self.terrain.river_cells:
                        continue
                    score = 1.0 + (1.1 if (ndx, ndy) == (dx, dy) else 0.0) + (
                        1.3 if (nx, ny) in self.terrain.bank_cells else 0.0
                    )
                    options.append((score, nx, ny, ndx, ndy))
                if not options:
                    break
                total = sum(o[0] for o in options)
                pick = self.rng.random() * total
                acc = 0.0
                chosen = options[-1]
                for o in options:
                    acc += o[0]
                    if pick <= acc:
                        chosen = o
                        break
                x, y, dx, dy = chosen[1], chosen[2], chosen[3], chosen[4]

    def _zone_and_buildables(self) -> None:
        for x, y in self.grid.iter_cells():
            if (x, y) in self.terrain.river_cells or (x, y) in self.terrain.path_cells:
                continue
            if (x, y) in self.terrain.curved_road_cells or (x, y) in self.terrain.platform_cells:
                continue
            if (x, y) in self.terrain.cliff_edges:
                continue
            dist = math.hypot(x - self.center, y - self.center) / max(
                1.0, math.hypot(self.center, self.center)
            )
            n = self._zone_noise(x, y) * self.cfg.zone_noise_strength
            near_river = any(
                (x + dx, y + dy) in self.terrain.bank_cells
                for dx in range(-2, 3)
                for dy in range(-2, 3)
            )
            corner = (
                (x < 8 and y < 8)
                or (x < 8 and y >= self.cfg.grid_size - 8)
                or (x >= self.cfg.grid_size - 8 and y < 8)
                or (x >= self.cfg.grid_size - 8 and y >= self.cfg.grid_size - 8)
            )
            if corner and self.rng.random() < 0.78 and n > -0.33:
                zone = "industrial"
            else:
                if dist < 0.22 + n * 0.08:
                    zone = "cbd"
                elif dist < 0.50 + n * 0.10:
                    zone = "commercial"
                else:
                    zone = "residential"
                if near_river and zone != "cbd" and self.rng.random() < 0.55:
                    zone = "commercial"

            if near_river and self.rng.random() < self.cfg.green_corridor_strength * 0.42:
                self.terrain.park_cells.add((x, y))
                continue
            if self.terrain.height_of(x, y) > 0 and self.rng.random() < 0.35:
                self.terrain.park_cells.add((x, y))
                continue
            self.zone_map[(x, y)] = zone

    def _nearest_road_dir(self, x: int, y: int, max_r: int = 6) -> Optional[str]:
        for r in range(1, max_r + 1):
            for d, (dx, dy) in DIRS.items():
                if (x + dx * r, y + dy * r) in self.terrain.curved_road_cells:
                    return d
        return None

    def _plan_buildings(self) -> None:
        cells = list(self.zone_map.keys())
        self.rng.shuffle(cells)
        for x, y in cells:
            if len(self.buildings) >= self.max_buildings:
                break
            road_dir = self._nearest_road_dir(x, y, max_r=2)
            if road_dir is None:
                continue
            zone = self.zone_map[(x, y)]
            prob = {"cbd": 0.88, "commercial": 0.70, "residential": 0.56, "industrial": 0.62}[zone]
            if self.rng.random() > prob:
                continue
            if not self.grid.occupy(x, y, BUILDING):
                self.conflicts += 1
                continue
            rot = {"N": 0.0, "E": math.pi * 1.5, "S": math.pi, "W": math.pi * 0.5}[road_dir]
            if zone == "cbd":
                name = self.rng.choice(CITY_ASSETS["cbd"])
            elif zone == "commercial":
                name = self.rng.choice(CITY_ASSETS["commercial"])
            elif zone == "industrial":
                name = self.rng.choice(CITY_ASSETS["industrial"])
            else:
                name = self.rng.choice(CITY_ASSETS["residential"])
            self.buildings.append((x, y, name, rot))
            if zone == "industrial" and self.rng.random() < 0.45:
                self._add_industrial_detail(x, y)

    def _add_industrial_detail(self, bx: int, by: int) -> None:
        dirs = list(DIRS.values())
        self.rng.shuffle(dirs)
        for dx, dy in dirs:
            x, y = bx + dx, by + dy
            if not self.grid.occupy(x, y, NATURE):
                continue
            self.greenery_plan.append(
                (
                    self.rng.choice(CITY_ASSETS["industrial_details"]),
                    x,
                    y,
                    0.0,
                    1.0,
                    self.rng.choice(ORTHO),
                )
            )
            return

    def _plan_greenery(self) -> None:
        candidates = list(self.terrain.park_cells)
        for x, y in self.grid.iter_cells():
            if (x, y) in self.terrain.bank_cells and self.rng.random() < self.cfg.green_corridor_strength * 0.65:
                candidates.append((x, y))
        self.rng.shuffle(candidates)
        count = 0
        for x, y in candidates:
            if count >= self.max_green_objects:
                break
            if self.grid.get(x, y) == BUILDING:
                continue
            if (x, y) in self.terrain.river_cells or (x, y) in self.terrain.curved_road_cells:
                continue
            self.grid.set_force(x, y, NATURE)
            self.greenery_plan.append(
                ("tree-large", x, y, 0.0, self.rng.uniform(0.9, 1.15), self.rng.uniform(0.0, math.tau))
            )
            count += 1
            for _ in range(self.rng.randint(2, 4)):
                if count >= self.max_green_objects:
                    break
                self.greenery_plan.append(
                    ("tree-small", x, y, 0.0, self.rng.uniform(0.8, 1.2), self.rng.uniform(0.0, math.tau))
                )
                count += 1
            for _ in range(self.rng.randint(1, 3)):
                if count >= self.max_green_objects:
                    break
                self.greenery_plan.append(
                    ("planter", x, y, 0.0, self.rng.uniform(0.85, 1.15), self.rng.uniform(0.0, math.tau))
                )
                count += 1

    def _sync_occupancy(self) -> None:
        for x, y in (
            self.terrain.river_cells
            | self.terrain.bank_cells
            | self.terrain.platform_cells
            | set(self.terrain.cliff_edges.keys())
        ):
            if self.grid.get(x, y) == EMPTY:
                self.grid.set_force(x, y, NATURE)
        for x, y in self.terrain.curved_road_cells | self.terrain.path_cells:
            if self.grid.get(x, y) == EMPTY:
                self.grid.set_force(x, y, ROAD)

    def _place_ground(self) -> None:
        grass_mat = self.materials.get("MAT_GRASS", (0.49, 0.95, 0.0), 0.9)
        road_mat = self.materials.get("MAT_ROAD", (0.36, 0.36, 0.36), 0.95)
        side_mat = self.materials.get("MAT_SIDEWALK", (0.66, 0.66, 0.66), 0.87)
        planes = {
            "grass": self._plane_template("TPL_GROUND_GRASS", grass_mat),
            "road": self._plane_template("TPL_GROUND_ROAD", road_mat),
            "side": self._plane_template("TPL_GROUND_SIDE", side_mat),
        }
        for x, y in self.grid.iter_cells():
            h = self.terrain.height_of(x, y)
            z = h * self.cfg.height_step
            if (x, y) in self.terrain.river_cells:
                z -= self.cfg.river_depth
            cell = self.grid.get(x, y)
            key = "side" if cell == BUILDING else ("road" if cell == ROAD else "grass")
            self._place_plane(planes[key], x, y, z)

    def _plane_template(self, name: str, mat: bpy.types.Material) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"{name}_MESH")
        h = self.cfg.tile_size * 0.5
        mesh.from_pydata([(-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0)], [], [(0, 1, 2, 3)])
        mesh.update()
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(name, mesh)
        obj.hide_viewport = True
        obj.hide_render = True
        self.io.templates_col.objects.link(obj)
        return obj

    def _place_plane(self, tpl: bpy.types.Object, x: int, y: int, z: float) -> None:
        obj = tpl.copy()
        obj.data = tpl.data
        obj.hide_viewport = False
        obj.hide_render = False
        obj.location = self.world(x, y, z)
        self.io.ground_col.objects.link(obj)

    def _piece(self, cells: Set[Tuple[int, int]], x: int, y: int) -> Set[str]:
        out: Set[str] = set()
        for d, (dx, dy) in DIRS.items():
            if (x + dx, y + dy) in cells:
                out.add(d)
        return out

    def _dir_rot(self, d: str) -> float:
        return {"N": 0.0, "E": math.pi * 1.5, "S": math.pi, "W": math.pi * 0.5}[d]

    def _corner_rot(self, dirs: Set[str]) -> float:
        m = {
            frozenset({"N", "E"}): 0.0,
            frozenset({"E", "S"}): math.pi * 1.5,
            frozenset({"S", "W"}): math.pi,
            frozenset({"W", "N"}): math.pi * 0.5,
        }
        return m.get(frozenset(dirs), 0.0)

    def _network_choice(self, dirs: Set[str], family: Dict[str, str]) -> Tuple[str, float]:
        c = len(dirs)
        if c >= 4 and "cross" in family:
            return family["cross"], 0.0
        if c == 3 and "split" in family:
            miss = next(k for k in DIRS if k not in dirs)
            return family["split"], {"S": 0.0, "W": math.pi * 0.5, "N": math.pi, "E": math.pi * 1.5}[miss]
        if c == 2:
            if dirs in ({"N", "S"}, {"E", "W"}):
                return family["straight"], (0.0 if dirs == {"E", "W"} else math.pi * 0.5)
            if "bend" in family and self.rng.random() < 0.55:
                return family["bend"], self._corner_rot(dirs)
            return family["corner"], self._corner_rot(dirs)
        if c == 1:
            return family["end"], self._dir_rot(next(iter(dirs)))
        return family["tile"], 0.0

    def _place_river_path(self) -> None:
        for x, y in self.terrain.river_cells:
            dirs = self._piece(self.terrain.river_cells, x, y)
            name, rot = self._network_choice(dirs, NATURE_ASSETS["river"])
            z = self.terrain.height_of(x, y) * self.cfg.height_step - self.cfg.river_depth + 0.02
            self.io.instance(self.assets.get(name), self.io.river_col, self.world(x, y, z), rot, self.cfg.model_scale)
        for x, y in self.terrain.bank_cells:
            dirs = self._piece(self.terrain.river_cells, x, y)
            if len(dirs) == 1:
                name = NATURE_ASSETS["river"]["side"]
                rot = self._dir_rot(next(iter(dirs)))
            elif len(dirs) == 2 and dirs not in ({"N", "S"}, {"E", "W"}):
                name = NATURE_ASSETS["river"]["bank"]
                rot = self._corner_rot(dirs)
            else:
                name = NATURE_ASSETS["river"]["rocks"]
                rot = self.rng.choice(ORTHO)
            z = self.terrain.height_of(x, y) * self.cfg.height_step + 0.03
            self.io.instance(self.assets.get(name), self.io.river_col, self.world(x, y, z), rot, self.cfg.model_scale)
        for x, y in self.terrain.path_cells:
            dirs = self._piece(self.terrain.path_cells, x, y)
            name, rot = self._network_choice(dirs, NATURE_ASSETS["path"])
            z = self.terrain.height_of(x, y) * self.cfg.height_step + 0.04
            self.io.instance(self.assets.get(name), self.io.path_col, self.world(x, y, z), rot, self.cfg.model_scale)

    def _place_cliff_platform(self) -> None:
        block = self.assets.get(NATURE_ASSETS["cliff"]["block"])
        corner = self.assets.get(NATURE_ASSETS["cliff"]["corner"])
        steps = self.assets.get(NATURE_ASSETS["cliff"]["steps"])
        for (x, y), drops in self.terrain.cliff_edges.items():
            h = self.terrain.height_of(x, y)
            if h <= 0:
                continue
            if len(drops) >= 2:
                zc = (h - 1) * self.cfg.height_step + 0.02
                self.io.instance(corner, self.io.cliff_col, self.world(x, y, zc), self._corner_rot(set(list(drops)[:2])), self.cfg.model_scale)
            for d in drops:
                nh = self.terrain.height_of(x + DIRS[d][0], y + DIRS[d][1])
                for layer in range(max(1, h - nh)):
                    z = (nh + layer) * self.cfg.height_step + 0.02
                    self.io.instance(block, self.io.cliff_col, self.world(x, y, z), self._dir_rot(d), self.cfg.model_scale)
                if self.rng.random() < 0.06:
                    zs = (h - 1) * self.cfg.height_step + 0.03
                    self.io.instance(steps, self.io.cliff_col, self.world(x, y, zs), self._dir_rot(d), self.cfg.model_scale)
        for x, y in self.terrain.platform_cells:
            n = NATURE_ASSETS["platform"]["stone"] if self.rng.random() < 0.45 else NATURE_ASSETS["platform"]["grass"]
            z = self.terrain.height_of(x, y) * self.cfg.height_step + 0.05
            self.io.instance(self.assets.get(n), self.io.platform_col, self.world(x, y, z), self.rng.choice(ORTHO), self.cfg.model_scale)
        if self.terrain.waterfall_top and self.terrain.waterfall_bottom:
            tx, ty, d = self.terrain.waterfall_top
            bx, by, _ = self.terrain.waterfall_bottom
            rz = self._dir_rot(d)
            self.io.instance(self.assets.get(NATURE_ASSETS["cliff"]["waterfall_top"]), self.io.cliff_col, self.world(tx, ty, self.terrain.height_of(tx, ty) * self.cfg.height_step + 0.05), rz, self.cfg.model_scale)
            self.io.instance(self.assets.get(NATURE_ASSETS["cliff"]["waterfall"]), self.io.cliff_col, self.world(bx, by, self.terrain.height_of(bx, by) * self.cfg.height_step - self.cfg.river_depth + 0.05), rz, self.cfg.model_scale)

    def _place_roads_and_buildings(self) -> None:
        roads = self.terrain.curved_road_cells
        for x, y in roads:
            dirs = self._piece(roads, x, y)
            if len(dirs) >= 4:
                name, rot = "road-crossroad", 0.0
            elif len(dirs) == 3:
                miss = next(k for k in DIRS if k not in dirs)
                name, rot = "road-intersection", {"S": 0.0, "W": math.pi * 0.5, "N": math.pi, "E": math.pi * 1.5}[miss]
            elif len(dirs) == 2 and dirs not in ({"N", "S"}, {"E", "W"}):
                name, rot = "road-bend", self._corner_rot(dirs)
            else:
                name = "road-straight"
                rot = math.pi * 0.5 if ("N" in dirs or "S" in dirs) else 0.0
            z = self.terrain.height_of(x, y) * self.cfg.height_step + 0.04
            self.io.instance(self.assets.get(name), self.io.road_col, self.world(x, y, z), rot, self.cfg.model_scale)
        for x, y, name, rot in self.buildings:
            z = self.terrain.height_of(x, y) * self.cfg.height_step
            self.io.instance(self.assets.get(name), self.io.building_col, self.world(x, y, z), rot, self.cfg.model_scale)

    def _place_greenery(self) -> None:
        for name, x, y, zoff, smul, rot in self.greenery_plan:
            wx, wy, wz = self.world(x, y, self.terrain.height_of(x, y) * self.cfg.height_step + zoff)
            spread = self.cfg.tile_size * 0.34
            wx += self.rng.uniform(-spread, spread)
            wy += self.rng.uniform(-spread, spread)
            self.io.instance(self.assets.get(name), self.io.green_col, (wx, wy, wz), rot, self.cfg.model_scale * smul)

    def _run_validations(self) -> None:
        river_ok = self._validate_river_connectivity()
        road_ratio = self._road_connectivity_ratio()
        building_ok = self._validate_buildings()
        print(
            "[VALIDATION] "
            f"occupancy_conflicts={self.conflicts}; "
            f"river_connected={river_ok}; "
            f"road_largest_component_ratio={road_ratio:.3f}; "
            f"building_legal={building_ok}; "
            f"buildings={len(self.buildings)}; greenery_objects={len(self.greenery_plan)}"
        )

    def _validate_river_connectivity(self) -> bool:
        starts = [(x, y) for x, y in self.terrain.river_cells if x == 0]
        goals = {(x, y) for x, y in self.terrain.river_cells if x == self.cfg.grid_size - 1}
        if not starts or not goals:
            return False
        q = [starts[0]]
        vis = {starts[0]}
        while q:
            x, y = q.pop(0)
            if (x, y) in goals:
                return True
            for dx, dy in DIRS.values():
                n = (x + dx, y + dy)
                if n in self.terrain.river_cells and n not in vis:
                    vis.add(n)
                    q.append(n)
        return False

    def _road_connectivity_ratio(self) -> float:
        cells = self.terrain.curved_road_cells
        if not cells:
            return 0.0
        rem = set(cells)
        largest = 0
        while rem:
            seed = next(iter(rem))
            q = [seed]
            comp = {seed}
            rem.remove(seed)
            while q:
                x, y = q.pop()
                for dx, dy in DIRS.values():
                    n = (x + dx, y + dy)
                    if n in rem:
                        rem.remove(n)
                        comp.add(n)
                        q.append(n)
            largest = max(largest, len(comp))
        return largest / float(len(cells))

    def _validate_buildings(self) -> bool:
        blocked = (
            self.terrain.river_cells
            | self.terrain.bank_cells
            | self.terrain.platform_cells
            | set(self.terrain.cliff_edges.keys())
        )
        roads = self.terrain.curved_road_cells
        for x, y, _name, _rot in self.buildings:
            if (x, y) in blocked:
                return False
            ok = False
            for dx, dy in DIRS.values():
                if (x + dx, y + dy) in roads or (x + 2 * dx, y + 2 * dy) in roads:
                    ok = True
                    break
            if not ok:
                return False
        return True


def main() -> None:
    cfg = Config()
    CityGeneratorHybrid(cfg).run()


if __name__ == "__main__":
    main()
