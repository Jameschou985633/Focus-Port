"""
Animal Crossing styled procedural city generator for Blender.

Highlights:
1) Strict occupancy grid for top-level placement.
2) Meandering river crossing the whole map.
3) Organic road network based on irregular block partition + block merging.
4) Off-center CBD with noisy skyline perturbation.
5) Full pastel ground coverage under every cell.
6) Missing assets become red 0.8m cubes and never stop the run.
7) All imported assets are instanced at 0.01 scale and only rotate on Z.
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import bpy


EMPTY = 0
ROAD = 1
BUILDING = 2
NATURE = 3

GRID_SIZE = 46
SEED = 20260404

IMPORT_SCALE = 0.01
SOURCE_TILE_SIZE_METERS = 200.0
TILE_SIZE = SOURCE_TILE_SIZE_METERS * IMPORT_SCALE

GROUND_Z = -0.04
RIVER_SURFACE_Z = 0.02
ROAD_SURFACE_Z = 0.04
BRIDGE_SURFACE_Z = 0.08
NATURE_SURFACE_Z = 0.03

ORTHO = (0.0, math.pi * 0.5, math.pi, math.pi * 1.5)
DIRS = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}

ROTATION_FACE_TO_ROAD = {
    "N": 0.0,
    "E": math.pi * 1.5,
    "S": math.pi,
    "W": math.pi * 0.5,
}

try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()

ASSET_ROOTS = {
    "roads": r"C:\Users\86153\Downloads\asset\kenney_city-kit-roads\Models\OBJ format",
    "commercial": r"C:\Users\86153\Downloads\asset\kenney_city-kit-commercial_2.1\Models\OBJ format",
    "suburban": r"C:\Users\86153\Downloads\asset\kenney_city-kit-suburban_20\Models\OBJ format",
    "industrial": r"C:\Users\86153\Downloads\asset\kenney_city-kit-industrial_1.0\Models\OBJ format",
    "nature": str(BASE_DIR / "kenney_assets" / "nature-kit" / "Models" / "OBJ format"),
}

ASSET_DICT = {
    "roads": {
        "straight": ["road-straight"],
        "crossroad": ["road-crossroad"],
        "intersection": ["road-intersection"],
        "bend": ["road-bend"],
        "bridge": ["road-bridge"],
    },
    "river": {
        "tile": ["ground_riverStraight_NW"],
    },
    "cbd": [f"building-skyscraper-{c}" for c in "abcde"],
    "commercial": [f"building-{c}" for c in "abcdefghijklmn"],
    "residential": [f"building-type-{c}" for c in "abcdefghijklmnopqrstu"],
    "industrial": {
        "buildings": [f"building-{c}" for c in "abcdefghijklmnopqrst"],
        "details": ["chimney-large", "detail-tank"],
    },
    "nature": {
        "trees": ["tree_default", "tree_oak", "tree_pineDefaultA", "tree_small", "tree_tall"],
        "bushes": ["plant_bush", "plant_bushLarge", "plant_bushSmall"],
        "flowers": ["flower_purpleA", "flower_redA", "flower_yellowA"],
        "grass": ["grass", "grass_large"],
        "rocks": ["rock_smallA", "rock_largeA", "rock_tallA"],
        "logs": ["log", "log_large"],
    },
}


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def line_points(a: Tuple[int, int], b: Tuple[int, int]) -> List[Tuple[int, int]]:
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
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return out


@dataclass
class Template:
    name: str
    root: bpy.types.Object
    is_missing: bool = False


class OccupancyGrid:
    def __init__(self, size: int) -> None:
        self.size = size
        self.grid = [[0 for _ in range(size)] for _ in range(size)]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def get(self, x: int, y: int) -> Optional[int]:
        if not self.in_bounds(x, y):
            return None
        return self.grid[x][y]

    def is_empty(self, x: int, y: int) -> bool:
        return self.get(x, y) == EMPTY

    def occupy(self, x: int, y: int, value: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        if self.grid[x][y] != EMPTY:
            return False
        self.grid[x][y] = value
        return True

    def set_force(self, x: int, y: int, value: int) -> None:
        if self.in_bounds(x, y):
            self.grid[x][y] = value

    def iter_cells(self) -> Iterable[Tuple[int, int]]:
        for x in range(self.size):
            for y in range(self.size):
                yield x, y


class MaterialFactory:
    def __init__(self) -> None:
        self.cache: Dict[str, bpy.types.Material] = {}

    def _hex_to_rgba(self, color_hex: str) -> Tuple[float, float, float, float]:
        h = color_hex.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
            1.0,
        )

    def flat(self, name: str, color_hex: str, roughness: float = 0.9) -> bpy.types.Material:
        if name in self.cache:
            return self.cache[name]

        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        out = nodes.new(type="ShaderNodeOutputMaterial")
        bsdf.inputs["Base Color"].default_value = self._hex_to_rgba(color_hex)
        bsdf.inputs["Roughness"].default_value = roughness
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.1
        elif "Specular" in bsdf.inputs:
            bsdf.inputs["Specular"].default_value = 0.1
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        self.cache[name] = mat
        return mat


class SceneIO:
    def __init__(self, materials: MaterialFactory) -> None:
        self.materials = materials
        self.root = self._new_collection("AC_CITY_ROOT", bpy.context.scene.collection)
        self.templates_col = self._new_collection("AC_CITY_TEMPLATES", bpy.context.scene.collection)
        self.ground_col = self._new_collection("AC_GROUND", self.root)
        self.river_col = self._new_collection("AC_RIVER", self.root)
        self.roads_col = self._new_collection("AC_ROADS", self.root)
        self.bridges_col = self._new_collection("AC_BRIDGES", self.root)
        self.buildings_col = self._new_collection("AC_BUILDINGS", self.root)
        self.nature_col = self._new_collection("AC_NATURE", self.root)
        self.lights_col = self._new_collection("AC_LIGHTS", self.root)
        self.templates_col.hide_viewport = True
        self.templates_col.hide_render = True

    def _new_collection(self, name: str, parent: bpy.types.Collection) -> bpy.types.Collection:
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

    def import_obj_template(self, name: str, filepath: str) -> Template:
        if not os.path.exists(filepath):
            print(f"[WARN] Missing OBJ: {filepath}")
            return self._create_missing_template(name)

        before = set(bpy.data.objects)
        bpy.ops.object.select_all(action="DESELECT")
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except Exception:
            bpy.ops.import_scene.obj(filepath=filepath)

        imported = [obj for obj in bpy.data.objects if obj not in before]
        if not imported:
            print(f"[WARN] Import failed, using placeholder: {filepath}")
            return self._create_missing_template(name)

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

        return Template(name=name, root=root, is_missing=False)

    def _create_missing_template(self, name: str) -> Template:
        mesh = bpy.data.meshes.new(f"MISSING_{name}_MESH")
        half = 0.4
        verts = [
            (-half, -half, -half),
            (half, -half, -half),
            (half, half, -half),
            (-half, half, -half),
            (-half, -half, half),
            (half, -half, half),
            (half, half, half),
            (-half, half, half),
        ]
        faces = [
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ]
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        mesh.materials.append(self.materials.flat("MAT_MISSING_RED", "#FF4D4D", roughness=0.92))

        root = bpy.data.objects.new(f"MISSING_{name}", mesh)
        self.templates_col.objects.link(root)
        root.hide_viewport = True
        root.hide_render = True
        return Template(name=name, root=root, is_missing=True)

    def instance(
        self,
        template: Template,
        target_collection: bpy.types.Collection,
        location: Tuple[float, float, float],
        rot_z: float,
        scale_mul: float = 1.0,
    ) -> bpy.types.Object:
        root_copy = self._dup_hierarchy(template.root, target_collection, None)
        root_copy.location = location
        root_copy.rotation_euler[2] = rot_z
        if template.is_missing:
            final_scale = scale_mul
        else:
            final_scale = IMPORT_SCALE * scale_mul
        root_copy.scale = (final_scale, final_scale, final_scale)
        root_copy.hide_viewport = False
        root_copy.hide_render = False
        return root_copy

    def _dup_hierarchy(
        self,
        src: bpy.types.Object,
        target_collection: bpy.types.Collection,
        parent: Optional[bpy.types.Object],
    ) -> bpy.types.Object:
        dup = src.copy()
        if src.data:
            dup.data = src.data
        dup.animation_data_clear()
        target_collection.objects.link(dup)
        dup.parent = parent
        dup.matrix_local = src.matrix_local.copy()
        for child in src.children:
            self._dup_hierarchy(child, target_collection, dup)
        return dup


class AssetLibrary:
    def __init__(self, io: SceneIO) -> None:
        self.io = io
        self.by_name: Dict[str, Template] = {}

    def load(self) -> None:
        assets: List[Tuple[str, str]] = []
        for n in ASSET_DICT["roads"]["straight"]:
            assets.append((n, ASSET_ROOTS["roads"]))
        for n in ASSET_DICT["roads"]["crossroad"]:
            assets.append((n, ASSET_ROOTS["roads"]))
        for n in ASSET_DICT["roads"]["intersection"]:
            assets.append((n, ASSET_ROOTS["roads"]))
        for n in ASSET_DICT["roads"]["bend"]:
            assets.append((n, ASSET_ROOTS["roads"]))
        for n in ASSET_DICT["roads"]["bridge"]:
            assets.append((n, ASSET_ROOTS["roads"]))
        for n in ASSET_DICT["river"]["tile"]:
            assets.append((n, ASSET_ROOTS["nature"]))
        for n in ASSET_DICT["cbd"] + ASSET_DICT["commercial"]:
            assets.append((n, ASSET_ROOTS["commercial"]))
        for n in ASSET_DICT["residential"]:
            assets.append((n, ASSET_ROOTS["suburban"]))
        for n in ASSET_DICT["industrial"]["buildings"] + ASSET_DICT["industrial"]["details"]:
            assets.append((n, ASSET_ROOTS["industrial"]))
        for group_name in ("trees", "bushes", "flowers", "grass", "rocks", "logs"):
            for n in ASSET_DICT["nature"][group_name]:
                assets.append((n, ASSET_ROOTS["nature"]))

        seen: Set[str] = set()
        for name, root in assets:
            if name in seen:
                continue
            seen.add(name)
            self.by_name[name] = self.io.import_obj_template(name, os.path.join(root, f"{name}.obj"))

    def get(self, name: str) -> Template:
        if name not in self.by_name:
            self.by_name[name] = self.io._create_missing_template(name)
        return self.by_name[name]


class CityGeneratorAnimalCrossing:
    def __init__(self) -> None:
        self.rng = random.Random(SEED)
        self.grid = OccupancyGrid(GRID_SIZE)
        self.materials = MaterialFactory()
        self.io = SceneIO(self.materials)
        self.assets = AssetLibrary(self.io)
        self.center = (GRID_SIZE - 1) * 0.5
        self.cbd_center = self._pick_offcenter_cbd()

        self.river_cells: Set[Tuple[int, int]] = set()
        self.road_cells: Set[Tuple[int, int]] = set()
        self.bridge_cells: Set[Tuple[int, int]] = set()
        self.park_cells: List[Tuple[int, int]] = []
        self.zone_map: Dict[Tuple[int, int], str] = {}
        self.building_plan: List[Tuple[int, int, str, float, str]] = []
        self.detail_plan: List[Tuple[int, int, str, float]] = []

        self.ground_templates: Dict[str, bpy.types.Object] = {}
        self.stats = {
            "river": 0,
            "roads": 0,
            "bridges": 0,
            "buildings": 0,
            "parks": 0,
            "nature_objects": 0,
        }

    def run(self) -> None:
        self.assets.load()
        self.generate_river()
        self.generate_organic_roads()
        self.plan_city_blocks()
        self.create_ground_base()
        self.place_river()
        self.place_roads_and_bridges()
        self.place_buildings()
        self.place_parks()
        self.apply_ac_style()

        bpy.context.view_layer.update()
        print(
            "[DONE] "
            f"cbd_center={self.cbd_center}; "
            f"river={self.stats['river']}; roads={self.stats['roads']}; "
            f"bridges={self.stats['bridges']}; buildings={self.stats['buildings']}; "
            f"parks={self.stats['parks']}; nature_objects={self.stats['nature_objects']}"
        )

    def to_world(self, gx: int, gy: int, z: float = 0.0) -> Tuple[float, float, float]:
        return (gx - self.center) * TILE_SIZE, (gy - self.center) * TILE_SIZE, z

    def _pick_offcenter_cbd(self) -> Tuple[int, int]:
        min_pos = int(GRID_SIZE * 0.20)
        max_pos = int(GRID_SIZE * 0.80)
        while True:
            x = self.rng.randint(min_pos, max_pos)
            y = self.rng.randint(min_pos, max_pos)
            if abs(x - self.center) + abs(y - self.center) >= GRID_SIZE * 0.18:
                return x, y

    def generate_river(self) -> None:
        start_y = self.rng.randint(int(GRID_SIZE * 0.25), int(GRID_SIZE * 0.72))
        phase_a = self.rng.uniform(0.0, math.tau)
        phase_b = self.rng.uniform(0.0, math.tau)
        prev: Optional[Tuple[int, int]] = None

        for x in range(GRID_SIZE):
            drift = (
                math.sin(x * 0.19 + phase_a) * 2.6
                + math.sin(x * 0.07 + phase_b) * 1.4
                + self.rng.uniform(-0.9, 0.9)
            )
            y = clamp(int(round(start_y + drift)), 2, GRID_SIZE - 3)
            segment = [(x, y)] if prev is None else line_points(prev, (x, y))
            prev = (x, y)

            for sx, sy in segment:
                width = 1 if self.rng.random() < 0.62 else 2
                for oy in range(-width + 1, width + 1):
                    cell = (sx, clamp(sy + oy, 1, GRID_SIZE - 2))
                    self.river_cells.add(cell)

        for x, y in self.river_cells:
            if self.grid.get(x, y) == EMPTY:
                self.grid.set_force(x, y, NATURE)

    def generate_organic_roads(self) -> None:
        verticals = self._irregular_axis_positions(4, 8)
        horizontals = self._irregular_axis_positions(5, 9)
        protected_verticals = {verticals[0], verticals[-1], self._closest_axis(verticals, self.cbd_center[0])}
        protected_horizontals = {
            horizontals[0],
            horizontals[-1],
            self._closest_axis(horizontals, self.cbd_center[1]),
        }

        for x in verticals:
            for y in range(GRID_SIZE):
                self.road_cells.add((x, y))
        for y in horizontals:
            for x in range(GRID_SIZE):
                self.road_cells.add((x, y))

        self._merge_blocks(verticals, horizontals, protected_verticals, protected_horizontals)
        self._add_soft_diagonal_connectors(verticals, horizontals)

        self.bridge_cells = self.road_cells & self.river_cells
        for x, y in self.road_cells:
            self.grid.set_force(x, y, ROAD)

    def _irregular_axis_positions(self, low_step: int, high_step: int) -> List[int]:
        positions = [1]
        cursor = 1
        while cursor < GRID_SIZE - 3:
            cursor += self.rng.randint(low_step, high_step)
            if cursor < GRID_SIZE - 1:
                positions.append(cursor)
        if positions[-1] != GRID_SIZE - 2:
            positions.append(GRID_SIZE - 2)
        return sorted(set(positions))

    def _closest_axis(self, positions: Sequence[int], value: int) -> int:
        return min(positions, key=lambda p: abs(p - value))

    def _merge_blocks(
        self,
        verticals: Sequence[int],
        horizontals: Sequence[int],
        protected_verticals: Set[int],
        protected_horizontals: Set[int],
    ) -> None:
        for x in verticals[1:-1]:
            if x in protected_verticals:
                continue
            for y0, y1 in zip(horizontals[:-1], horizontals[1:]):
                if y1 - y0 <= 2 or self.rng.random() > 0.40:
                    continue
                for y in range(y0 + 1, y1):
                    self.road_cells.discard((x, y))

        for y in horizontals[1:-1]:
            if y in protected_horizontals:
                continue
            for x0, x1 in zip(verticals[:-1], verticals[1:]):
                if x1 - x0 <= 2 or self.rng.random() > 0.42:
                    continue
                for x in range(x0 + 1, x1):
                    self.road_cells.discard((x, y))

    def _add_soft_diagonal_connectors(self, verticals: Sequence[int], horizontals: Sequence[int]) -> None:
        if len(verticals) < 3 or len(horizontals) < 3:
            return
        for _ in range(3):
            x0 = self.rng.choice(verticals[1:-1])
            y0 = self.rng.choice(horizontals[1:-1])
            x1 = self.rng.choice(verticals[1:-1])
            y1 = self.rng.choice(horizontals[1:-1])
            for x, y in line_points((x0, y0), (x1, y1)):
                self.road_cells.add((x, y))

    def plan_city_blocks(self) -> None:
        cells = list(self.grid.iter_cells())
        self.rng.shuffle(cells)
        for x, y in cells:
            if (x, y) in self.river_cells or (x, y) in self.road_cells:
                continue

            zone = self._zone_at(x, y)
            road_dir = self._nearest_road_direction(x, y, max_radius=3)
            if road_dir is None:
                continue

            park_chance = {"cbd": 0.10, "commercial": 0.12, "residential": 0.18, "industrial": 0.10}[zone]
            if zone == "cbd" and self.rng.random() < 0.18:
                park_chance += 0.18
            if zone != "cbd" and self.rng.random() < 0.05:
                zone = "cbd"
            if zone == "residential" and self.rng.random() < 0.05:
                zone = "commercial"
            if zone == "commercial" and self.rng.random() < 0.08:
                zone = "residential"

            if self.rng.random() < park_chance:
                if self.grid.occupy(x, y, NATURE):
                    self.zone_map[(x, y)] = "park"
                    self.park_cells.append((x, y))
                continue

            asset_name = self._pick_building_for_zone(zone)
            if self.grid.occupy(x, y, BUILDING):
                self.zone_map[(x, y)] = zone
                self.building_plan.append((x, y, asset_name, ROTATION_FACE_TO_ROAD[road_dir], zone))
                if zone == "industrial" and self.rng.random() < 0.32:
                    self._plan_industrial_detail(x, y)

    def _zone_noise(self, x: int, y: int) -> float:
        a = math.sin((x + SEED * 0.01) * 0.31)
        b = math.cos((y - SEED * 0.02) * 0.27)
        c = math.sin((x + y) * 0.13 + 1.7)
        return (a + b + c) / 3.0

    def _zone_at(self, x: int, y: int) -> str:
        dx = x - self.cbd_center[0]
        dy = y - self.cbd_center[1]
        dist = math.sqrt(dx * dx + dy * dy)
        max_dist = math.sqrt((GRID_SIZE - 1) ** 2 + (GRID_SIZE - 1) ** 2)
        ratio = dist / max_dist if max_dist else 0.0
        noise = self._zone_noise(x, y) * 0.10

        corner_industrial = (
            (x < 8 and y < 8)
            or (x < 8 and y > GRID_SIZE - 9)
            or (x > GRID_SIZE - 9 and y < 8)
            or (x > GRID_SIZE - 9 and y > GRID_SIZE - 9)
        )
        if corner_industrial and self.rng.random() < 0.72:
            return "industrial"

        if ratio + noise < 0.12:
            return "cbd"
        if ratio + noise < 0.23:
            return "commercial" if self.rng.random() < 0.25 else "cbd"
        if ratio + noise < 0.42:
            return "commercial"
        if ratio + noise < 0.68:
            return "residential"
        return "industrial" if self.rng.random() < 0.18 else "residential"

    def _nearest_road_direction(self, x: int, y: int, max_radius: int = 4) -> Optional[str]:
        best: Optional[Tuple[int, str]] = None
        for radius in range(1, max_radius + 1):
            for direction, (dx, dy) in DIRS.items():
                nx = x + dx * radius
                ny = y + dy * radius
                if (nx, ny) in self.road_cells:
                    if best is None or radius < best[0]:
                        best = (radius, direction)
            if best is not None:
                return best[1]
        return None

    def _pick_building_for_zone(self, zone: str) -> str:
        if zone == "cbd":
            if self.rng.random() < 0.22:
                return self.rng.choice(ASSET_DICT["commercial"] + ASSET_DICT["residential"])
            return self.rng.choice(ASSET_DICT["cbd"])
        if zone == "commercial":
            if self.rng.random() < 0.08:
                return self.rng.choice(ASSET_DICT["cbd"])
            return self.rng.choice(ASSET_DICT["commercial"])
        if zone == "industrial":
            if self.rng.random() < 0.05:
                return self.rng.choice(ASSET_DICT["cbd"])
            return self.rng.choice(ASSET_DICT["industrial"]["buildings"])
        if self.rng.random() < 0.04:
            return self.rng.choice(ASSET_DICT["cbd"])
        if self.rng.random() < 0.15:
            return self.rng.choice(ASSET_DICT["commercial"])
        return self.rng.choice(ASSET_DICT["residential"])

    def _plan_industrial_detail(self, bx: int, by: int) -> None:
        offsets = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        self.rng.shuffle(offsets)
        for dx, dy in offsets:
            nx, ny = bx + dx, by + dy
            if (nx, ny) in self.river_cells or (nx, ny) in self.road_cells:
                continue
            if self.grid.occupy(nx, ny, NATURE):
                detail_name = self.rng.choice(ASSET_DICT["industrial"]["details"])
                self.detail_plan.append((nx, ny, detail_name, self.rng.choice(ORTHO)))
                return

    def create_ground_base(self) -> None:
        self.ground_templates = {
            "grass": self._create_ground_tile_template("TPL_GROUND_GRASS", "#A8D88F"),
            "road": self._create_ground_tile_template("TPL_GROUND_ROAD", "#C7C0B5"),
            "sidewalk": self._create_ground_tile_template("TPL_GROUND_SIDEWALK", "#E4D9C8"),
            "water": self._create_ground_tile_template("TPL_GROUND_WATER", "#A9DCEC"),
        }

        for x, y in self.grid.iter_cells():
            if (x, y) in self.river_cells:
                key = "water"
            else:
                cell = self.grid.get(x, y)
                if cell == BUILDING:
                    key = "sidewalk"
                elif cell == ROAD:
                    key = "road"
                else:
                    key = "grass"
            self._place_ground_tile(self.ground_templates[key], x, y)

    def _create_ground_tile_template(self, name: str, color_hex: str) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"{name}_MESH")
        half = TILE_SIZE * 0.5
        mesh.from_pydata(
            [(-half, -half, 0.0), (half, -half, 0.0), (half, half, 0.0), (-half, half, 0.0)],
            [],
            [(0, 1, 2, 3)],
        )
        mesh.update()
        mesh.materials.append(self.materials.flat(f"MAT_{name}", color_hex, roughness=0.93))
        obj = bpy.data.objects.new(name, mesh)
        obj.hide_viewport = True
        obj.hide_render = True
        self.io.templates_col.objects.link(obj)
        return obj

    def _place_ground_tile(self, template_obj: bpy.types.Object, x: int, y: int) -> None:
        obj = template_obj.copy()
        obj.data = template_obj.data
        obj.hide_viewport = False
        obj.hide_render = False
        obj.location = self.to_world(x, y, GROUND_Z)
        self.io.ground_col.objects.link(obj)

    def place_river(self) -> None:
        river_template = self.assets.get(ASSET_DICT["river"]["tile"][0])
        for x, y in self.river_cells:
            rot = self._river_rotation(x, y)
            self.io.instance(
                river_template,
                self.io.river_col,
                self.to_world(x, y, RIVER_SURFACE_Z),
                rot,
                scale_mul=1.0,
            )
            self.stats["river"] += 1

    def _river_rotation(self, x: int, y: int) -> float:
        east_west = ((x - 1, y) in self.river_cells) or ((x + 1, y) in self.river_cells)
        north_south = ((x, y - 1) in self.river_cells) or ((x, y + 1) in self.river_cells)
        if east_west and not north_south:
            return 0.0
        if north_south and not east_west:
            return math.pi * 0.5
        if (x + 1, y + 1) in self.river_cells or (x - 1, y - 1) in self.river_cells:
            return math.pi * 0.25
        if (x + 1, y - 1) in self.river_cells or (x - 1, y + 1) in self.river_cells:
            return math.pi * 0.75
        return 0.0

    def place_roads_and_bridges(self) -> None:
        for x, y in self.road_cells:
            dirs = self._road_neighbors(x, y)
            if (x, y) in self.bridge_cells:
                rot = 0.0 if dirs in ({"E", "W"}, {"E", "W", "N"}, {"E", "W", "S"}) else math.pi * 0.5
                self.io.instance(
                    self.assets.get(ASSET_DICT["roads"]["bridge"][0]),
                    self.io.bridges_col,
                    self.to_world(x, y, BRIDGE_SURFACE_Z),
                    rot,
                    scale_mul=1.0,
                )
                self.stats["bridges"] += 1
                continue

            name, rot = self._road_asset_choice(dirs)
            self.io.instance(
                self.assets.get(name),
                self.io.roads_col,
                self.to_world(x, y, ROAD_SURFACE_Z),
                rot,
                scale_mul=1.0,
            )
            self.stats["roads"] += 1

    def _road_neighbors(self, x: int, y: int) -> Set[str]:
        out: Set[str] = set()
        for d, (dx, dy) in DIRS.items():
            if (x + dx, y + dy) in self.road_cells:
                out.add(d)
        return out

    def _road_asset_choice(self, dirs: Set[str]) -> Tuple[str, float]:
        count = len(dirs)
        if count >= 4:
            return ASSET_DICT["roads"]["crossroad"][0], 0.0
        if count == 3:
            missing = next(k for k in DIRS if k not in dirs)
            rot = {"S": 0.0, "W": math.pi * 0.5, "N": math.pi, "E": math.pi * 1.5}[missing]
            return ASSET_DICT["roads"]["intersection"][0], rot
        if count == 2:
            if dirs in ({"N", "S"}, {"E", "W"}):
                rot = 0.0 if dirs == {"E", "W"} else math.pi * 0.5
                return ASSET_DICT["roads"]["straight"][0], rot
            rot = self._corner_rotation(dirs)
            return ASSET_DICT["roads"]["bend"][0], rot
        if count == 1:
            only = next(iter(dirs))
            rot = 0.0 if only in ("E", "W") else math.pi * 0.5
            return ASSET_DICT["roads"]["straight"][0], rot
        return ASSET_DICT["roads"]["straight"][0], 0.0

    def _corner_rotation(self, dirs: Set[str]) -> float:
        mapping = {
            frozenset({"N", "E"}): 0.0,
            frozenset({"E", "S"}): math.pi * 1.5,
            frozenset({"S", "W"}): math.pi,
            frozenset({"W", "N"}): math.pi * 0.5,
        }
        return mapping.get(frozenset(dirs), 0.0)

    def place_buildings(self) -> None:
        for x, y, asset_name, rot, _zone in self.building_plan:
            self.io.instance(
                self.assets.get(asset_name),
                self.io.buildings_col,
                self.to_world(x, y, 0.0),
                rot,
                scale_mul=1.0,
            )
            self.stats["buildings"] += 1

        for x, y, asset_name, rot in self.detail_plan:
            self.io.instance(
                self.assets.get(asset_name),
                self.io.nature_col,
                self.to_world(x, y, NATURE_SURFACE_Z),
                rot,
                scale_mul=1.0,
            )
            self.stats["nature_objects"] += 1

    def place_parks(self) -> None:
        for x, y in self.park_cells:
            self._spawn_park_cluster(x, y)
            self.stats["parks"] += 1

    def _spawn_park_cluster(self, x: int, y: int) -> None:
        for _ in range(self.rng.randint(1, 2)):
            ox, oy = self._cluster_offset(0.18)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["trees"]),
                x,
                y,
                ox,
                oy,
                NATURE_SURFACE_Z,
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.88, 1.16),
            )

        for _ in range(self.rng.randint(2, 4)):
            ox, oy = self._cluster_offset(0.34)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["bushes"]),
                x,
                y,
                ox,
                oy,
                NATURE_SURFACE_Z,
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.84, 1.15),
            )

        for _ in range(self.rng.randint(3, 5)):
            ox, oy = self._cluster_offset(0.40)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["flowers"]),
                x,
                y,
                ox,
                oy,
                NATURE_SURFACE_Z,
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.8, 1.2),
            )

        if self.rng.random() < 0.45:
            ox, oy = self._cluster_offset(0.35)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["rocks"]),
                x,
                y,
                ox,
                oy,
                NATURE_SURFACE_Z,
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.85, 1.10),
            )

        if self.rng.random() < 0.24:
            ox, oy = self._cluster_offset(0.32)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["logs"]),
                x,
                y,
                ox,
                oy,
                NATURE_SURFACE_Z,
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.9, 1.08),
            )

        for _ in range(self.rng.randint(1, 3)):
            ox, oy = self._cluster_offset(0.42)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["grass"]),
                x,
                y,
                ox,
                oy,
                NATURE_SURFACE_Z,
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.92, 1.22),
            )

    def _cluster_offset(self, spread_ratio: float) -> Tuple[float, float]:
        spread = TILE_SIZE * spread_ratio
        return self.rng.uniform(-spread, spread), self.rng.uniform(-spread, spread)

    def _spawn_nature_asset(
        self,
        asset_name: str,
        gx: int,
        gy: int,
        offset_x: float,
        offset_y: float,
        z_offset: float,
        rot_z: float,
        scale_mul: float,
    ) -> None:
        half = TILE_SIZE * 0.48
        ox = max(-half, min(half, offset_x))
        oy = max(-half, min(half, offset_y))
        wx, wy, wz = self.to_world(gx, gy, z_offset)
        self.io.instance(
            self.assets.get(asset_name),
            self.io.nature_col,
            (wx + ox, wy + oy, wz),
            rot_z,
            scale_mul=scale_mul,
        )
        self.stats["nature_objects"] += 1

    def apply_ac_style(self) -> None:
        scene = bpy.context.scene
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "High Contrast"
        scene.view_settings.exposure = 0.5
        scene.view_settings.gamma = 1.0

        if scene.world is None:
            scene.world = bpy.data.worlds.new("World")
        world = scene.world
        world.use_nodes = True
        background = world.node_tree.nodes.get("Background")
        if background is not None:
            background.inputs["Color"].default_value = (0.77, 0.90, 1.0, 1.0)
            background.inputs["Strength"].default_value = 1.1

        sun_data = bpy.data.lights.new(name="AC_SUN", type="SUN")
        sun_data.energy = 6.5
        sun_data.color = (1.0, 0.95, 0.85)
        sun_data.angle = math.radians(8.0)
        sun_obj = bpy.data.objects.new("AC_SUN", sun_data)
        sun_obj.location = (0.0, 0.0, 40.0)
        sun_obj.rotation_euler[0] = math.radians(55.0)
        sun_obj.rotation_euler[2] = math.radians(32.0)
        self.io.lights_col.objects.link(sun_obj)

        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type != "BSDF_PRINCIPLED":
                    continue
                if "Roughness" in node.inputs:
                    node.inputs["Roughness"].default_value = max(node.inputs["Roughness"].default_value, 0.88)
                if "Specular IOR Level" in node.inputs:
                    node.inputs["Specular IOR Level"].default_value = 0.1
                elif "Specular" in node.inputs:
                    node.inputs["Specular"].default_value = 0.1

    def validate(self) -> None:
        largest = self._road_component_ratio()
        print(f"[VALIDATION] road_component_ratio={largest:.3f}")

    def _road_component_ratio(self) -> float:
        if not self.road_cells:
            return 0.0
        remaining = set(self.road_cells)
        largest = 0
        while remaining:
            seed = next(iter(remaining))
            queue = [seed]
            component = {seed}
            remaining.remove(seed)
            while queue:
                x, y = queue.pop()
                for dx, dy in DIRS.values():
                    nxt = (x + dx, y + dy)
                    if nxt in remaining:
                        remaining.remove(nxt)
                        component.add(nxt)
                        queue.append(nxt)
            largest = max(largest, len(component))
        return largest / float(len(self.road_cells))


def main() -> None:
    generator = CityGeneratorAnimalCrossing()
    generator.run()
    generator.validate()


if __name__ == "__main__":
    main()
