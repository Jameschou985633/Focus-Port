"""
Naturalized city terrain generator for Blender (Kenney nature-kit assets).

Goal:
- Break rigid flat-grid feeling with meandering river, cliffs, plateaus, and organic paths.
- Keep strict 2D occupancy logic and provide matrix output for debugging/planning.

Run:
1) Open Blender Text Editor
2) Load this file
3) Alt+P
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import bpy


# -----------------------------------------------------------------------------
# Grid constants
# -----------------------------------------------------------------------------
GRID_SIZE = 46
TILE_SIZE = 2.0
HEIGHT_STEP = 1.8
RIVER_DEPTH = 0.45
MODEL_SCALE = 1.0
SEED = 20260404


# -----------------------------------------------------------------------------
# Occupancy grid values (requested style)
# -----------------------------------------------------------------------------
EMPTY = 0
ROAD = 1
BUILDING = 2
NATURE = 3


# -----------------------------------------------------------------------------
# Terrain layer codes
# -----------------------------------------------------------------------------
TG_GRASS = 0
TG_RIVER = 1
TG_BANK = 2
TG_PATH = 3
TG_CLIFF = 4
TG_PLATFORM = 5


DIRS: Dict[str, Tuple[int, int]] = {
    "N": (0, 1),
    "E": (1, 0),
    "S": (0, -1),
    "W": (-1, 0),
}

ORTHO = (0.0, math.pi * 0.5, math.pi, math.pi * 1.5)

try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()


# -----------------------------------------------------------------------------
# Asset config (strictly from provided list)
# -----------------------------------------------------------------------------
NATURE_ASSET_ROOT = str(BASE_DIR / "kenney_assets" / "nature-kit" / "Models" / "OBJ format")

ASSETS = {
    "ground": {
        "grass": "ground_grass",
        "path_rocks": "ground_pathRocks",
        "river_rocks": "ground_riverRocks",
    },
    "river": {
        "bend": "ground_riverBend",
        "bend_bank": "ground_riverBendBank",
        "corner": "ground_riverCorner",
        "cross": "ground_riverCross",
        "end": "ground_riverEnd",
        "side": "ground_riverSide",
        "split": "ground_riverSplit",
        "straight": "ground_riverStraight",
        "tile": "ground_riverTile",
    },
    "path": {
        "bend": "ground_pathBend",
        "corner": "ground_pathCorner",
        "cross": "ground_pathCross",
        "end": "ground_pathEnd",
        "split": "ground_pathSplit",
        "straight": "ground_pathStraight",
        "tile": "ground_pathTile",
    },
    "cliff": {
        "block": "cliff_block_rock",
        "corner": "cliff_corner_rock",
        "steps": "cliff_steps_rock",
        "waterfall": "cliff_waterfall_rock",
        "waterfall_top": "cliff_waterfallTop_rock",
    },
    "platform": {
        "grass": "platform_grass",
        "stone": "platform_stone",
    },
}


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def line_points(a: Tuple[int, int], b: Tuple[int, int]) -> List[Tuple[int, int]]:
    """
    Integer line interpolation to avoid holes when river centerline moves diagonally.
    """
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    points: List[Tuple[int, int]] = []

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return points


@dataclass
class Template:
    name: str
    root: bpy.types.Object


class OccupancyGrid:
    """
    Strict occupancy structure:
    grid = [[0 for _ in range(SIZE)] for _ in range(SIZE)]
    """

    def __init__(self, size: int) -> None:
        self.size = size
        self.grid = [[0 for _ in range(size)] for _ in range(size)]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def get(self, x: int, y: int) -> Optional[int]:
        if not self.in_bounds(x, y):
            return None
        return self.grid[x][y]

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
    """
    Separate terrain layers:
    - terrain code map
    - integer height map
    """

    def __init__(self, size: int) -> None:
        self.size = size
        self.terrain = [[TG_GRASS for _ in range(size)] for _ in range(size)]
        self.height = [[0 for _ in range(size)] for _ in range(size)]

        self.river_cells: Set[Tuple[int, int]] = set()
        self.bank_cells: Set[Tuple[int, int]] = set()
        self.path_cells: Set[Tuple[int, int]] = set()
        self.avenue_cells: Set[Tuple[int, int]] = set()
        self.platform_cells: Set[Tuple[int, int]] = set()
        self.city_block_cells: Set[Tuple[int, int]] = set()
        self.cliff_edges: Dict[Tuple[int, int], Set[str]] = {}
        self.step_cells: List[Tuple[int, int, str]] = []
        self.waterfall_top: Optional[Tuple[int, int, str]] = None
        self.waterfall_bottom: Optional[Tuple[int, int, str]] = None

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def mark_river(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            return
        self.river_cells.add((x, y))
        self.terrain[x][y] = TG_RIVER

    def mark_bank(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            return
        if (x, y) in self.river_cells:
            return
        self.bank_cells.add((x, y))
        if self.terrain[x][y] == TG_GRASS:
            self.terrain[x][y] = TG_BANK

    def mark_path(self, x: int, y: int, is_avenue: bool = False) -> None:
        if not self.in_bounds(x, y):
            return
        if (x, y) in self.river_cells:
            return
        self.path_cells.add((x, y))
        if is_avenue:
            self.avenue_cells.add((x, y))
        if self.terrain[x][y] in (TG_GRASS, TG_BANK):
            self.terrain[x][y] = TG_PATH

    def set_height(self, x: int, y: int, h: int) -> None:
        if not self.in_bounds(x, y):
            return
        self.height[x][y] = max(self.height[x][y], h)

    def height_of(self, x: int, y: int) -> int:
        if not self.in_bounds(x, y):
            return 0
        return self.height[x][y]


class SceneIO:
    def __init__(self) -> None:
        self.root = self._create_collection("NAT_CITY_ROOT", bpy.context.scene.collection)
        self.templates = self._create_collection("NAT_CITY_TEMPLATES", bpy.context.scene.collection)
        self.ground = self._create_collection("NAT_GROUND", self.root)
        self.river = self._create_collection("NAT_RIVER", self.root)
        self.path = self._create_collection("NAT_PATH", self.root)
        self.cliff = self._create_collection("NAT_CLIFF", self.root)
        self.platform = self._create_collection("NAT_PLATFORM", self.root)
        self.city_blocks = self._create_collection("NAT_CITY_BLOCKS", self.root)
        self.templates.hide_viewport = True
        self.templates.hide_render = True

    def _create_collection(self, name: str, parent: bpy.types.Collection) -> bpy.types.Collection:
        existing = bpy.data.collections.get(name)
        if existing is not None:
            self._remove_collection(existing)
        col = bpy.data.collections.new(name)
        parent.children.link(col)
        return col

    def _remove_collection(self, col: bpy.types.Collection) -> None:
        for child in list(col.children):
            self._remove_collection(child)
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        scene_root = bpy.context.scene.collection
        if col in scene_root.children:
            scene_root.children.unlink(col)
        for parent in bpy.data.collections:
            if col in parent.children:
                parent.children.unlink(col)
        bpy.data.collections.remove(col)

    def import_template(self, name: str, filepath: str) -> Template:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Missing asset: {filepath}")
        before = set(bpy.data.objects)
        bpy.ops.object.select_all(action="DESELECT")
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except Exception:
            bpy.ops.import_scene.obj(filepath=filepath)
        imported = [obj for obj in bpy.data.objects if obj not in before]
        if not imported:
            raise RuntimeError(f"Import produced no object: {filepath}")

        root = bpy.data.objects.new(f"SRC__{name}", None)
        self.templates.objects.link(root)
        imported_set = set(imported)
        for obj in imported:
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            self.templates.objects.link(obj)
            if obj.parent not in imported_set:
                obj.parent = root
                obj.matrix_parent_inverse = root.matrix_world.inverted()
        return Template(name=name, root=root)

    def instance(
        self,
        template: Template,
        target_col: bpy.types.Collection,
        location: Tuple[float, float, float],
        rot_z: float = 0.0,
        scale: float = MODEL_SCALE,
    ) -> bpy.types.Object:
        root = self._dup(template.root, target_col, None)
        root.location = location
        root.rotation_euler = (0.0, 0.0, rot_z)
        root.scale = (scale, scale, scale)
        return root

    def _dup(
        self,
        src: bpy.types.Object,
        col: bpy.types.Collection,
        parent: Optional[bpy.types.Object],
    ) -> bpy.types.Object:
        dup = src.copy()
        if src.data:
            dup.data = src.data
        dup.animation_data_clear()
        col.objects.link(dup)
        dup.parent = parent
        dup.matrix_local = src.matrix_local.copy()
        for child in src.children:
            self._dup(child, col, dup)
        return dup


class AssetLibrary:
    def __init__(self, io: SceneIO) -> None:
        self.io = io
        self.templates: Dict[str, Template] = {}

    def load(self) -> None:
        names = self._all_asset_names()
        for name in names:
            path = os.path.join(NATURE_ASSET_ROOT, f"{name}.obj")
            self.templates[name] = self.io.import_template(name, path)

    def get(self, name: str) -> Template:
        return self.templates[name]

    def _all_asset_names(self) -> List[str]:
        unique: List[str] = []
        seen: Set[str] = set()

        def push(v: str) -> None:
            if v not in seen:
                seen.add(v)
                unique.append(v)

        for grp in ASSETS.values():
            if isinstance(grp, dict):
                for val in grp.values():
                    if isinstance(val, dict):
                        for v2 in val.values():
                            push(v2)
                    else:
                        push(val)
        return unique


class NaturalCitySandbox:
    def __init__(self) -> None:
        self.rng = random.Random(SEED)
        self.grid = OccupancyGrid(GRID_SIZE)
        self.terrain = TerrainGrid(GRID_SIZE)
        self.scene = SceneIO()
        self.assets = AssetLibrary(self.scene)
        self.center = (GRID_SIZE - 1) * 0.5
        self.stats = {
            "river_tiles": 0,
            "bank_tiles": 0,
            "path_tiles": 0,
            "cliff_segments": 0,
            "platform_tiles": 0,
            "city_blocks": 0,
        }

    def run(self) -> None:
        self.assets.load()
        self._generate_meandering_river()
        self._expand_river_banks()
        self._generate_highlands_and_cliffs()
        self._generate_organic_avenues()
        self._generate_scenic_paths()
        self._reserve_city_blocks()
        self._sync_occupancy()
        self._place_scene()
        self._print_matrices()
        bpy.context.view_layer.update()
        print(
            "[DONE] "
            f"river={self.stats['river_tiles']}, banks={self.stats['bank_tiles']}, "
            f"path={self.stats['path_tiles']}, cliffs={self.stats['cliff_segments']}, "
            f"platforms={self.stats['platform_tiles']}, city_blocks={self.stats['city_blocks']}"
        )

    # ---------------------------------------------------------------------
    # Coordinate mapping
    # ---------------------------------------------------------------------
    def world_pos(self, gx: int, gy: int, z: float = 0.0) -> Tuple[float, float, float]:
        ox = (gx - self.center) * TILE_SIZE
        oy = (gy - self.center) * TILE_SIZE
        return ox, oy, z

    # ---------------------------------------------------------------------
    # Terrain generation
    # ---------------------------------------------------------------------
    def _generate_meandering_river(self) -> None:
        mid = int(GRID_SIZE * 0.50)
        amp1 = GRID_SIZE * 0.14
        amp2 = GRID_SIZE * 0.06
        f1 = 0.19
        f2 = 0.47
        phase1 = self.rng.uniform(0.0, math.tau)
        phase2 = self.rng.uniform(0.0, math.tau)

        centerline: List[Tuple[int, int]] = []
        prev: Optional[Tuple[int, int]] = None
        for x in range(GRID_SIZE):
            wave = amp1 * math.sin(f1 * x + phase1) + amp2 * math.sin(f2 * x + phase2)
            jitter = self.rng.uniform(-1.2, 1.2)
            y = int(round(mid + wave + jitter))
            y = clamp(y, 2, GRID_SIZE - 3)
            curr = (x, y)

            if prev is None:
                segment = [curr]
            else:
                segment = line_points(prev, curr)
            prev = curr

            for sx, sy in segment:
                width = 1
                if self.rng.random() < 0.25:
                    width = 2
                for oy in range(-width, width + 1):
                    self.terrain.mark_river(sx, sy + oy)
            centerline.append(curr)

        # Small diagonal cuts to avoid over-grid look
        for i in range(2, len(centerline) - 2, 7):
            x, y = centerline[i]
            dx = 1
            dy = 1 if self.rng.random() < 0.5 else -1
            for step in range(2):
                self.terrain.mark_river(x + dx * step, y + dy * step)

    def _expand_river_banks(self) -> None:
        for x, y in list(self.terrain.river_cells):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if not self.terrain.in_bounds(nx, ny):
                        continue
                    if (nx, ny) in self.terrain.river_cells:
                        continue
                    self.terrain.mark_bank(nx, ny)

    def _generate_highlands_and_cliffs(self) -> None:
        corners = [
            (4, 4),
            (4, GRID_SIZE - 5),
            (GRID_SIZE - 5, 4),
            (GRID_SIZE - 5, GRID_SIZE - 5),
        ]
        corner_seed = self.rng.choice(corners)
        center_seed = (
            clamp(int(self.center + self.rng.randint(-4, 4)), 4, GRID_SIZE - 5),
            clamp(int(self.center + self.rng.randint(-4, 4)), 4, GRID_SIZE - 5),
        )
        hill_seeds = [corner_seed, center_seed]

        for idx, (sx, sy) in enumerate(hill_seeds):
            outer_r = 7 if idx == 0 else 6
            inner_r = 3
            self._raise_hill(sx, sy, outer_r, inner_r)

        # mark platforms on high cells
        for x, y in self.grid.iter_cells():
            h = self.terrain.height_of(x, y)
            if h >= 2 and (x, y) not in self.terrain.river_cells:
                self.terrain.platform_cells.add((x, y))
                self.terrain.terrain[x][y] = TG_PLATFORM

        # cliff boundaries where neighboring height is lower
        for x, y in self.grid.iter_cells():
            h = self.terrain.height_of(x, y)
            if h <= 0:
                continue
            drops: Set[str] = set()
            for d, (dx, dy) in DIRS.items():
                nx, ny = x + dx, y + dy
                nh = self.terrain.height_of(nx, ny)
                if nh < h:
                    drops.add(d)
            if drops:
                self.terrain.cliff_edges[(x, y)] = drops
                if self.terrain.terrain[x][y] != TG_PLATFORM:
                    self.terrain.terrain[x][y] = TG_CLIFF

        # steps to connect low/high terrain
        step_candidates: List[Tuple[int, int, str]] = []
        for (x, y), drops in self.terrain.cliff_edges.items():
            if self.terrain.height_of(x, y) < 1:
                continue
            for d in drops:
                dx, dy = DIRS[d]
                nx, ny = x + dx, y + dy
                if (nx, ny) in self.terrain.river_cells:
                    continue
                if self.terrain.height_of(nx, ny) == self.terrain.height_of(x, y) - 1:
                    step_candidates.append((x, y, d))
        self.rng.shuffle(step_candidates)
        self.terrain.step_cells = step_candidates[:4]

        # Optional waterfall: high cell next to river
        waterfall_candidates: List[Tuple[int, int, str]] = []
        for (x, y), drops in self.terrain.cliff_edges.items():
            if self.terrain.height_of(x, y) < 1:
                continue
            for d in drops:
                dx, dy = DIRS[d]
                nx, ny = x + dx, y + dy
                if (nx, ny) in self.terrain.river_cells:
                    waterfall_candidates.append((x, y, d))
        if waterfall_candidates:
            x, y, d = self.rng.choice(waterfall_candidates)
            dx, dy = DIRS[d]
            self.terrain.waterfall_top = (x, y, d)
            self.terrain.waterfall_bottom = (x + dx, y + dy, d)

    def _raise_hill(self, sx: int, sy: int, outer_r: int, inner_r: int) -> None:
        for x, y in self.grid.iter_cells():
            if (x, y) in self.terrain.river_cells:
                continue
            dist = math.hypot(x - sx, y - sy)
            if dist <= inner_r:
                self.terrain.set_height(x, y, 2)
            elif dist <= outer_r:
                self.terrain.set_height(x, y, 1)

    def _generate_organic_avenues(self) -> None:
        # Two curved "main routes" to replace hard chessboard axes
        phase_a = self.rng.uniform(0.0, math.tau)
        phase_b = self.rng.uniform(0.0, math.tau)

        for x in range(GRID_SIZE):
            y = int(round(GRID_SIZE * 0.33 + 2.4 * math.sin(x * 0.18 + phase_a)))
            self._try_mark_path_cell(x, y, is_avenue=True)
            self._try_mark_path_cell(x, y + 1, is_avenue=True)

        for y in range(GRID_SIZE):
            x = int(round(GRID_SIZE * 0.66 + 2.2 * math.sin(y * 0.16 + phase_b)))
            self._try_mark_path_cell(x, y, is_avenue=True)
            self._try_mark_path_cell(x + 1, y, is_avenue=True)

    def _generate_scenic_paths(self) -> None:
        starts = list(self.terrain.bank_cells)
        self.rng.shuffle(starts)
        starts = starts[:6]

        for s in starts:
            self._random_walk_path(s, steps=self.rng.randint(12, 24))

        # extra split branches from existing path graph
        existing = list(self.terrain.path_cells)
        self.rng.shuffle(existing)
        for s in existing[:4]:
            self._random_walk_path(s, steps=self.rng.randint(8, 14))

    def _random_walk_path(self, start: Tuple[int, int], steps: int) -> None:
        x, y = start
        direction = self.rng.choice(list(DIRS.keys()))

        for _ in range(steps):
            self._try_mark_path_cell(x, y, is_avenue=False)
            candidates: List[Tuple[float, str, int, int]] = []
            for d, (dx, dy) in DIRS.items():
                nx, ny = x + dx, y + dy
                if not self.terrain.in_bounds(nx, ny):
                    continue
                if (nx, ny) in self.terrain.river_cells:
                    continue
                if self.terrain.height_of(nx, ny) > 2:
                    continue
                score = 1.0
                if d == direction:
                    score += 1.2
                if (nx, ny) in self.terrain.bank_cells:
                    score += 1.5
                if self.terrain.height_of(nx, ny) > 0:
                    score += 0.6
                candidates.append((score, d, nx, ny))
            if not candidates:
                break
            total = sum(c[0] for c in candidates)
            pick = self.rng.random() * total
            acc = 0.0
            chosen = candidates[-1]
            for c in candidates:
                acc += c[0]
                if pick <= acc:
                    chosen = c
                    break
            direction = chosen[1]
            x, y = chosen[2], chosen[3]

    def _try_mark_path_cell(self, x: int, y: int, is_avenue: bool) -> None:
        if not self.terrain.in_bounds(x, y):
            return
        if (x, y) in self.terrain.river_cells:
            return
        if self.terrain.height_of(x, y) > 1 and self.rng.random() < 0.65:
            return
        self.terrain.mark_path(x, y, is_avenue=is_avenue)

    def _reserve_city_blocks(self) -> None:
        # Reserve buildable pads near curved avenues but avoid water and cliffs
        avenue = self.terrain.avenue_cells
        if not avenue:
            return

        for x, y in self.grid.iter_cells():
            if (x, y) in self.terrain.river_cells:
                continue
            if (x, y) in self.terrain.bank_cells:
                continue
            if self.terrain.height_of(x, y) > 0:
                continue
            if (x, y) in self.terrain.path_cells:
                continue
            if self._dist_to_set((x, y), avenue, max_radius=3) is None:
                continue
            if self.rng.random() < 0.45:
                self.terrain.city_block_cells.add((x, y))

    def _dist_to_set(
        self, pos: Tuple[int, int], pts: Set[Tuple[int, int]], max_radius: int
    ) -> Optional[int]:
        px, py = pos
        best: Optional[int] = None
        for r in range(max_radius + 1):
            for dx in range(-r, r + 1):
                dy = r - abs(dx)
                cand = [(px + dx, py + dy), (px + dx, py - dy)]
                for cx, cy in cand:
                    if (cx, cy) in pts:
                        best = r if best is None else min(best, r)
            if best is not None:
                return best
        return None

    def _sync_occupancy(self) -> None:
        # Nature mask
        for x, y in self.terrain.river_cells:
            self.grid.set_force(x, y, NATURE)
        for x, y in self.terrain.bank_cells:
            self.grid.set_force(x, y, NATURE)
        for x, y in self.terrain.platform_cells:
            self.grid.set_force(x, y, NATURE)
        for (x, y), _drops in self.terrain.cliff_edges.items():
            self.grid.set_force(x, y, NATURE)

        # Roads/paths
        for x, y in self.terrain.path_cells:
            if self.grid.get(x, y) == EMPTY:
                self.grid.set_force(x, y, ROAD)

        # Buildable reserved blocks
        for x, y in self.terrain.city_block_cells:
            if self.grid.get(x, y) == EMPTY:
                self.grid.set_force(x, y, BUILDING)

    # ---------------------------------------------------------------------
    # Placement helpers
    # ---------------------------------------------------------------------
    def _neighbor_dirs(self, cells: Set[Tuple[int, int]], x: int, y: int) -> Set[str]:
        out: Set[str] = set()
        for d, (dx, dy) in DIRS.items():
            if (x + dx, y + dy) in cells:
                out.add(d)
        return out

    def _rot_from_single_dir(self, d: str) -> float:
        # Asset base assumed pointing North at rot=0
        return {
            "N": 0.0,
            "E": math.pi * 1.5,
            "S": math.pi,
            "W": math.pi * 0.5,
        }[d]

    def _rot_for_straight(self, dirs: Set[str]) -> float:
        if dirs == {"E", "W"}:
            return 0.0
        return math.pi * 0.5

    def _rot_for_corner(self, dirs: Set[str]) -> float:
        mapping = {
            frozenset({"N", "E"}): 0.0,
            frozenset({"E", "S"}): math.pi * 1.5,
            frozenset({"S", "W"}): math.pi,
            frozenset({"W", "N"}): math.pi * 0.5,
        }
        return mapping.get(frozenset(dirs), 0.0)

    def _rot_for_split_missing(self, missing: str) -> float:
        # Base split assumed opening to N,E,W (missing S) at rot=0
        return {
            "S": 0.0,
            "W": math.pi * 0.5,
            "N": math.pi,
            "E": math.pi * 1.5,
        }[missing]

    def _choose_network_piece(
        self,
        dirs: Set[str],
        family: Dict[str, str],
        allow_bend: bool = False,
    ) -> Tuple[str, float]:
        c = len(dirs)
        if c >= 4 and "cross" in family:
            return family["cross"], 0.0
        if c == 3 and "split" in family:
            missing = next(k for k in DIRS.keys() if k not in dirs)
            return family["split"], self._rot_for_split_missing(missing)
        if c == 2:
            if dirs in ({"N", "S"}, {"E", "W"}):
                return family["straight"], self._rot_for_straight(dirs)
            if allow_bend and "bend" in family and self.rng.random() < 0.5:
                return family["bend"], self._rot_for_corner(dirs)
            return family["corner"], self._rot_for_corner(dirs)
        if c == 1:
            d = next(iter(dirs))
            return family["end"], self._rot_from_single_dir(d)
        return family["tile"], 0.0

    # ---------------------------------------------------------------------
    # Blender placement
    # ---------------------------------------------------------------------
    def _place_scene(self) -> None:
        self._place_ground_layer()
        self._place_platform_layer()
        self._place_river_layer()
        self._place_path_layer()
        self._place_cliff_layer()
        self._place_city_block_layer()

    def _place_ground_layer(self) -> None:
        grass = self.assets.get(ASSETS["ground"]["grass"])
        path_rocks = self.assets.get(ASSETS["ground"]["path_rocks"])
        river_rocks = self.assets.get(ASSETS["ground"]["river_rocks"])

        for x, y in self.grid.iter_cells():
            h = self.terrain.height_of(x, y)
            z = h * HEIGHT_STEP
            if (x, y) in self.terrain.river_cells:
                t = river_rocks
            elif (x, y) in self.terrain.path_cells:
                t = path_rocks
            else:
                t = grass
            self.scene.instance(t, self.scene.ground, self.world_pos(x, y, z), rot_z=0.0)

    def _place_platform_layer(self) -> None:
        tpl_grass = self.assets.get(ASSETS["platform"]["grass"])
        tpl_stone = self.assets.get(ASSETS["platform"]["stone"])
        for x, y in self.terrain.platform_cells:
            z = self.terrain.height_of(x, y) * HEIGHT_STEP + 0.04
            tpl = tpl_stone if self.rng.random() < 0.45 else tpl_grass
            self.scene.instance(tpl, self.scene.platform, self.world_pos(x, y, z), rot_z=self.rng.choice(ORTHO))
            self.stats["platform_tiles"] += 1

    def _place_river_layer(self) -> None:
        river_family = ASSETS["river"]
        river_cells = self.terrain.river_cells

        for x, y in river_cells:
            dirs = self._neighbor_dirs(river_cells, x, y)
            name, rot = self._choose_network_piece(dirs, river_family, allow_bend=True)
            z = self.terrain.height_of(x, y) * HEIGHT_STEP - RIVER_DEPTH
            self.scene.instance(self.assets.get(name), self.scene.river, self.world_pos(x, y, z), rot_z=rot)
            self.stats["river_tiles"] += 1

        # Bank transitions
        for x, y in self.terrain.bank_cells:
            dirs = self._neighbor_dirs(river_cells, x, y)
            if len(dirs) == 1:
                name = river_family["side"]
                rot = self._rot_from_single_dir(next(iter(dirs)))
            elif len(dirs) == 2 and dirs not in ({"N", "S"}, {"E", "W"}):
                name = river_family["bend_bank"]
                rot = self._rot_for_corner(dirs)
            else:
                name = ASSETS["ground"]["river_rocks"]
                rot = self.rng.choice(ORTHO)
            z = self.terrain.height_of(x, y) * HEIGHT_STEP + 0.02
            self.scene.instance(self.assets.get(name), self.scene.river, self.world_pos(x, y, z), rot_z=rot)
            self.stats["bank_tiles"] += 1

    def _place_path_layer(self) -> None:
        path_family = ASSETS["path"]
        path_cells = self.terrain.path_cells
        for x, y in path_cells:
            dirs = self._neighbor_dirs(path_cells, x, y)
            name, rot = self._choose_network_piece(dirs, path_family, allow_bend=True)
            z = self.terrain.height_of(x, y) * HEIGHT_STEP + 0.03
            self.scene.instance(self.assets.get(name), self.scene.path, self.world_pos(x, y, z), rot_z=rot)
            self.stats["path_tiles"] += 1

    def _place_cliff_layer(self) -> None:
        block = self.assets.get(ASSETS["cliff"]["block"])
        corner = self.assets.get(ASSETS["cliff"]["corner"])
        steps = self.assets.get(ASSETS["cliff"]["steps"])

        for (x, y), drops in self.terrain.cliff_edges.items():
            h = self.terrain.height_of(x, y)
            if h <= 0:
                continue
            if len(drops) >= 2:
                # Try one corner piece for corner-like edges
                pair = set(list(drops)[:2])
                rot = self._rot_for_corner(pair) if pair not in ({"N", "S"}, {"E", "W"}) else 0.0
                z_corner = (h - 1) * HEIGHT_STEP + 0.02
                self.scene.instance(corner, self.scene.cliff, self.world_pos(x, y, z_corner), rot_z=rot)
                self.stats["cliff_segments"] += 1

            for d in drops:
                dx, dy = DIRS[d]
                nx, ny = x + dx, y + dy
                nh = self.terrain.height_of(nx, ny)
                drop = max(1, h - nh)
                for layer in range(drop):
                    z = (nh + layer) * HEIGHT_STEP + 0.02
                    self.scene.instance(block, self.scene.cliff, self.world_pos(x, y, z), rot_z=self._rot_from_single_dir(d))
                    self.stats["cliff_segments"] += 1

        for x, y, d in self.terrain.step_cells:
            z = (self.terrain.height_of(x, y) - 1) * HEIGHT_STEP + 0.03
            self.scene.instance(steps, self.scene.cliff, self.world_pos(x, y, z), rot_z=self._rot_from_single_dir(d))
            self.stats["cliff_segments"] += 1

        # Waterfall pair
        if self.terrain.waterfall_top and self.terrain.waterfall_bottom:
            wt = self.assets.get(ASSETS["cliff"]["waterfall_top"])
            wf = self.assets.get(ASSETS["cliff"]["waterfall"])
            tx, ty, d = self.terrain.waterfall_top
            bx, by, _ = self.terrain.waterfall_bottom
            tz = self.terrain.height_of(tx, ty) * HEIGHT_STEP + 0.05
            bz = self.terrain.height_of(bx, by) * HEIGHT_STEP - RIVER_DEPTH + 0.05
            rot = self._rot_from_single_dir(d)
            self.scene.instance(wt, self.scene.cliff, self.world_pos(tx, ty, tz), rot_z=rot)
            self.scene.instance(wf, self.scene.cliff, self.world_pos(bx, by, bz), rot_z=rot)
            self.stats["cliff_segments"] += 2

    def _place_city_block_layer(self) -> None:
        stone = self.assets.get(ASSETS["platform"]["stone"])
        for x, y in self.terrain.city_block_cells:
            z = self.terrain.height_of(x, y) * HEIGHT_STEP + 0.05
            self.scene.instance(stone, self.scene.city_blocks, self.world_pos(x, y, z), rot_z=self.rng.choice(ORTHO), scale=0.88)
            self.stats["city_blocks"] += 1

    # ---------------------------------------------------------------------
    # Matrix output
    # ---------------------------------------------------------------------
    def _print_matrices(self) -> None:
        print("\n=== TERRAIN CODE MATRIX ===")
        print("Legend: 0=grass 1=river 2=bank 3=path 4=cliff 5=platform")
        for y in range(GRID_SIZE - 1, -1, -1):
            row: List[str] = []
            for x in range(GRID_SIZE):
                code = self._terrain_code(x, y)
                row.append(str(code))
            print(" ".join(row))

        print("\n=== HEIGHT MATRIX ===")
        for y in range(GRID_SIZE - 1, -1, -1):
            row = [str(self.terrain.height_of(x, y)) for x in range(GRID_SIZE)]
            print(" ".join(row))

        print("\n=== OCCUPANCY MATRIX ===")
        print("Legend: 0=empty 1=road/path 2=reserved block 3=nature")
        for y in range(GRID_SIZE - 1, -1, -1):
            row = [str(self.grid.get(x, y) or 0) for x in range(GRID_SIZE)]
            print(" ".join(row))

    def _terrain_code(self, x: int, y: int) -> int:
        if (x, y) in self.terrain.river_cells:
            return TG_RIVER
        if (x, y) in self.terrain.platform_cells:
            return TG_PLATFORM
        if (x, y) in self.terrain.cliff_edges:
            return TG_CLIFF
        if (x, y) in self.terrain.path_cells:
            return TG_PATH
        if (x, y) in self.terrain.bank_cells:
            return TG_BANK
        return TG_GRASS


def main() -> None:
    sandbox = NaturalCitySandbox()
    sandbox.run()


if __name__ == "__main__":
    main()
