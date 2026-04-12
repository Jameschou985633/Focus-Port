"""
Blender Grid-Based City Generator (Kenney City Kit)

What this script guarantees:
1) Strict occupancy grid, no overlapping placement.
2) Grid-to-world mapping by TILE_SIZE only.
3) Connected roads first, then zoning and building placement.
4) Full ground under every grid cell (no visual holes).
5) Dense park-cluster vegetation on NATURE cells.
6) Bright cartoon-like render setup (Standard + High Contrast).
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import bpy


# -----------------------------------------------------------------------------
# Occupancy values
# -----------------------------------------------------------------------------
EMPTY = 0
ROAD = 1
BUILDING = 2
NATURE = 3


# -----------------------------------------------------------------------------
# Global controls
# -----------------------------------------------------------------------------
GRID_SIZE = 44
ROAD_INTERVAL = 7
CORNER_INDUSTRIAL_BAND = 8

TILE_SIZE = 2.0
MODEL_SCALE = 1.0
SEED = 20260404

GROUND_Z = -0.02
GROUND_PATCH_Z = 0.0

ORTHO = (0.0, math.pi * 0.5, math.pi, math.pi * 1.5)

# Building front faces +Y when rot_z == 0
ROTATION_FACE_TO_ROAD = {
    "N": 0.0,
    "E": math.pi * 1.5,
    "S": math.pi,
    "W": math.pi * 0.5,
}


# -----------------------------------------------------------------------------
# Asset roots
# -----------------------------------------------------------------------------
ASSET_ROOTS = {
    "roads": r"C:\Users\86153\Downloads\asset\kenney_city-kit-roads\Models\OBJ format",
    "commercial": r"C:\Users\86153\Downloads\asset\kenney_city-kit-commercial_2.1\Models\OBJ format",
    "suburban": r"C:\Users\86153\Downloads\asset\kenney_city-kit-suburban_20\Models\OBJ format",
    "industrial": r"C:\Users\86153\Downloads\asset\kenney_city-kit-industrial_1.0\Models\OBJ format",
    "nature": r"C:\Users\86153\PycharmProjects\PythonProject2\kenney_assets\nature-kit\Models\OBJ format",
}


# -----------------------------------------------------------------------------
# Strict curated dictionary
# -----------------------------------------------------------------------------
ASSET_DICT = {
    "roads": {
        "straight": ["road-straight"],
        "crossroad": ["road-crossroad"],
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


@dataclass
class Template:
    name: str
    root: bpy.types.Object


class OccupancyGrid:
    """
    Mandatory strict structure:
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

    def road_neighbors(self, x: int, y: int) -> Dict[str, Tuple[int, int]]:
        dirs = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
        result: Dict[str, Tuple[int, int]] = {}
        for direction, (dx, dy) in dirs.items():
            nx, ny = x + dx, y + dy
            if self.get(nx, ny) == ROAD:
                result[direction] = (nx, ny)
        return result


class SceneIO:
    def __init__(self) -> None:
        self.root = self._new_collection("CITY_GRID_ROOT", bpy.context.scene.collection)
        self.templates_col = self._new_collection("CITY_TEMPLATES", bpy.context.scene.collection)
        self.ground_col = self._new_collection("CITY_GROUND", self.root)
        self.roads_col = self._new_collection("CITY_ROADS", self.root)
        self.buildings_col = self._new_collection("CITY_BUILDINGS", self.root)
        self.nature_col = self._new_collection("CITY_NATURE", self.root)
        self.lights_col = self._new_collection("CITY_LIGHTS", self.root)
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
            raise FileNotFoundError(f"Missing OBJ: {filepath}")

        before = set(bpy.data.objects)
        bpy.ops.object.select_all(action="DESELECT")
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except Exception:
            bpy.ops.import_scene.obj(filepath=filepath)

        imported = [obj for obj in bpy.data.objects if obj not in before]
        if not imported:
            raise RuntimeError(f"Failed import: {filepath}")

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
        root_copy.rotation_euler = (0.0, 0.0, rot_z)
        final_scale = MODEL_SCALE * scale_mul
        root_copy.scale = (final_scale, final_scale, final_scale)
        return root_copy

    def _dup_hierarchy(
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
            self._dup_hierarchy(child, col, dup)
        return dup


class AssetLibrary:
    def __init__(self, io: SceneIO, rng: random.Random) -> None:
        self.io = io
        self.rng = rng
        self.by_name: Dict[str, Template] = {}

    def load(self) -> None:
        assets_and_roots: List[Tuple[str, str]] = []

        assets_and_roots += [
            (name, ASSET_ROOTS["roads"])
            for name in ASSET_DICT["roads"]["straight"] + ASSET_DICT["roads"]["crossroad"]
        ]
        assets_and_roots += [(name, ASSET_ROOTS["commercial"]) for name in ASSET_DICT["cbd"]]
        assets_and_roots += [(name, ASSET_ROOTS["commercial"]) for name in ASSET_DICT["commercial"]]
        assets_and_roots += [(name, ASSET_ROOTS["suburban"]) for name in ASSET_DICT["residential"]]
        assets_and_roots += [(name, ASSET_ROOTS["industrial"]) for name in ASSET_DICT["industrial"]["buildings"]]
        assets_and_roots += [(name, ASSET_ROOTS["industrial"]) for name in ASSET_DICT["industrial"]["details"]]

        for group_name in ("trees", "bushes", "flowers", "grass", "rocks", "logs"):
            assets_and_roots += [(name, ASSET_ROOTS["nature"]) for name in ASSET_DICT["nature"][group_name]]

        seen: Set[str] = set()
        for name, root in assets_and_roots:
            if name in seen:
                continue
            seen.add(name)
            path = os.path.join(root, f"{name}.obj")
            self.by_name[name] = self.io.import_obj_template(name, path)

    def pick_name(self, names: Sequence[str]) -> Template:
        return self.by_name[self.rng.choice(list(names))]

    def get(self, name: str) -> Template:
        return self.by_name[name]


class MaterialFactory:
    def __init__(self) -> None:
        self.cache: Dict[str, bpy.types.Material] = {}

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        h = hex_color.lstrip("#")
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return r, g, b

    def get_flat(self, name: str, hex_color: str, roughness: float = 0.85) -> bpy.types.Material:
        if name in self.cache:
            return self.cache[name]

        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        output = nodes.new(type="ShaderNodeOutputMaterial")
        bsdf.location = (0, 0)
        output.location = (300, 0)

        r, g, b = self._hex_to_rgb(hex_color)
        bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        self.cache[name] = mat
        return mat


class CityGenerator:
    def __init__(self) -> None:
        self.rng = random.Random(SEED)
        self.grid = OccupancyGrid(GRID_SIZE)
        self.io = SceneIO()
        self.assets = AssetLibrary(self.io, self.rng)
        self.materials = MaterialFactory()
        self.center = (GRID_SIZE - 1) * 0.5

        self.road_plan: List[Tuple[int, int, str, float]] = []
        self.building_plan: List[Tuple[int, int, str, float, str]] = []
        self.industrial_detail_plan: List[Tuple[int, int, str, float]] = []
        self.park_cells: List[Tuple[int, int]] = []
        self.industrial_detail_cells: Set[Tuple[int, int]] = set()

        self.stats = {
            "ground_tiles": 0,
            "green_ground_patches": 0,
            "roads": 0,
            "buildings": 0,
            "parks": 0,
            "park_objects": 0,
            "industrial_detail": 0,
        }

        self.ground_templates: Dict[str, bpy.types.Object] = {}

    def run(self) -> None:
        self.configure_render_and_lighting()
        self.assets.load()

        self.generate_roads()
        self.plan_roads_instances()
        self.plan_buildings()
        self.plan_parks()

        self.create_ground_base()
        self.place_green_ground_cover()
        self.place_roads()
        self.place_buildings()
        self.place_industrial_details()
        self.place_park_clusters()

        bpy.context.view_layer.update()
        print(
            "[DONE] "
            f"ground={self.stats['ground_tiles']}, green_ground_patches={self.stats['green_ground_patches']}, "
            f"roads={self.stats['roads']}, buildings={self.stats['buildings']}, "
            f"parks={self.stats['parks']}, park_objects={self.stats['park_objects']}, "
            f"industrial_detail={self.stats['industrial_detail']}"
        )

    # -------------------------------------------------------------------------
    # Lighting and rendering style
    # -------------------------------------------------------------------------
    def configure_render_and_lighting(self) -> None:
        scene = bpy.context.scene

        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "High Contrast"
        scene.view_settings.exposure = 0.4
        scene.view_settings.gamma = 1.0

        if scene.world is None:
            scene.world = bpy.data.worlds.new("World")
        world = scene.world
        world.use_nodes = True
        bg = world.node_tree.nodes.get("Background")
        if bg is not None:
            bg.inputs["Color"].default_value = (0.72, 0.86, 1.0, 1.0)
            bg.inputs["Strength"].default_value = 1.2

        sun_data = bpy.data.lights.new(name="CITY_SUN_MAIN", type="SUN")
        sun_data.energy = 7.0
        sun_data.color = (1.0, 0.95, 0.85)
        sun_obj = bpy.data.objects.new("CITY_SUN_MAIN", sun_data)
        sun_obj.location = (0.0, 0.0, 80.0)
        sun_obj.rotation_euler = (math.radians(52.0), 0.0, math.radians(35.0))
        self.io.lights_col.objects.link(sun_obj)

        area_data = bpy.data.lights.new(name="CITY_FILL_AREA", type="AREA")
        area_data.energy = 10000.0
        area_data.color = (0.75, 0.88, 1.0)
        area_data.shape = "RECTANGLE"
        area_data.size = GRID_SIZE * TILE_SIZE * 1.25
        area_data.size_y = GRID_SIZE * TILE_SIZE * 1.25
        area_obj = bpy.data.objects.new("CITY_FILL_AREA", area_data)
        area_obj.location = (0.0, 0.0, 60.0)
        area_obj.rotation_euler = (math.radians(180.0), 0.0, 0.0)
        self.io.lights_col.objects.link(area_obj)

    # -------------------------------------------------------------------------
    # Grid-world mapping
    # -------------------------------------------------------------------------
    def to_world(self, gx: int, gy: int, z: float = 0.0) -> Tuple[float, float, float]:
        ox = (gx - self.center) * TILE_SIZE
        oy = (gy - self.center) * TILE_SIZE
        return ox, oy, z

    # -------------------------------------------------------------------------
    # Road network (connected)
    # -------------------------------------------------------------------------
    def generate_roads(self) -> None:
        lines = list(range(ROAD_INTERVAL, GRID_SIZE - ROAD_INTERVAL, ROAD_INTERVAL))
        if not lines:
            lines = [GRID_SIZE // 2]

        for y in lines:
            for x in range(1, GRID_SIZE - 1):
                self.grid.set_force(x, y, ROAD)

        for x in lines:
            for y in range(1, GRID_SIZE - 1):
                self.grid.set_force(x, y, ROAD)

        border = 1
        for x in range(border, GRID_SIZE - border):
            self.grid.set_force(x, border, ROAD)
            self.grid.set_force(x, GRID_SIZE - 1 - border, ROAD)
        for y in range(border, GRID_SIZE - border):
            self.grid.set_force(border, y, ROAD)
            self.grid.set_force(GRID_SIZE - 1 - border, y, ROAD)

    def plan_roads_instances(self) -> None:
        for x, y in self.grid.iter_cells():
            if self.grid.get(x, y) != ROAD:
                continue
            neighbors = self.grid.road_neighbors(x, y)
            has_h = "E" in neighbors or "W" in neighbors
            has_v = "N" in neighbors or "S" in neighbors
            if has_h and has_v:
                self.road_plan.append((x, y, "road-crossroad", 0.0))
            else:
                rot = math.pi * 0.5 if has_v else 0.0
                self.road_plan.append((x, y, "road-straight", rot))

    # -------------------------------------------------------------------------
    # Zoning and planning
    # -------------------------------------------------------------------------
    def is_corner_industrial(self, x: int, y: int) -> bool:
        b = CORNER_INDUSTRIAL_BAND
        return (
            (x < b and y < b)
            or (x < b and y >= GRID_SIZE - b)
            or (x >= GRID_SIZE - b and y < b)
            or (x >= GRID_SIZE - b and y >= GRID_SIZE - b)
        )

    def zone(self, x: int, y: int) -> str:
        if self.is_corner_industrial(x, y):
            return "industrial"
        dist = math.sqrt((x - self.center) ** 2 + (y - self.center) ** 2)
        max_dist = math.sqrt(2.0 * (self.center**2))
        ratio = dist / max_dist if max_dist > 0 else 0.0
        if ratio < 0.20:
            return "cbd"
        if ratio < 0.50:
            return "commercial"
        return "residential"

    def nearest_road_direction(self, x: int, y: int, max_radius: int = 8) -> Optional[str]:
        direct = self.grid.road_neighbors(x, y)
        if direct:
            return self.rng.choice(list(direct.keys()))

        dirs = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
        best: Optional[Tuple[int, str]] = None
        for radius in range(1, max_radius + 1):
            for direction, (dx, dy) in dirs.items():
                nx = x + dx * radius
                ny = y + dy * radius
                if self.grid.get(nx, ny) == ROAD:
                    if best is None or radius < best[0]:
                        best = (radius, direction)
            if best is not None:
                return best[1]
        return None

    def _is_roadside_or_near_road(self, x: int, y: int) -> bool:
        if self.grid.road_neighbors(x, y):
            return True
        dirs = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
        for dx, dy in dirs.values():
            if self.grid.get(x + dx * 2, y + dy * 2) == ROAD:
                return True
        return False

    def plan_buildings(self) -> None:
        cells = list(self.grid.iter_cells())
        self.rng.shuffle(cells)

        for x, y in cells:
            if not self.grid.is_empty(x, y):
                continue
            if not self._is_roadside_or_near_road(x, y):
                continue

            road_dir = self.nearest_road_direction(x, y)
            if road_dir is None:
                continue

            zone = self.zone(x, y)
            if zone == "cbd":
                asset_name = self.rng.choice(ASSET_DICT["cbd"])
            elif zone == "commercial":
                asset_name = self.rng.choice(ASSET_DICT["commercial"])
            elif zone == "residential":
                asset_name = self.rng.choice(ASSET_DICT["residential"])
            else:
                asset_name = self.rng.choice(ASSET_DICT["industrial"]["buildings"])

            if not self.grid.occupy(x, y, BUILDING):
                continue

            self.building_plan.append((x, y, asset_name, ROTATION_FACE_TO_ROAD[road_dir], zone))
            if zone == "industrial":
                self._plan_industrial_detail_adjacent(x, y)

    def _plan_industrial_detail_adjacent(self, bx: int, by: int) -> None:
        if self.rng.random() > 0.45:
            return
        offsets = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        self.rng.shuffle(offsets)
        for dx, dy in offsets:
            nx, ny = bx + dx, by + dy
            if not self.grid.is_empty(nx, ny):
                continue
            if not self.grid.occupy(nx, ny, NATURE):
                continue
            self.industrial_detail_cells.add((nx, ny))
            detail_name = self.rng.choice(ASSET_DICT["industrial"]["details"])
            self.industrial_detail_plan.append((nx, ny, detail_name, self.rng.choice(ORTHO)))
            return

    def plan_parks(self) -> None:
        cells = list(self.grid.iter_cells())
        self.rng.shuffle(cells)
        for x, y in cells:
            if not self.grid.is_empty(x, y):
                continue

            zone = self.zone(x, y)
            if zone == "cbd":
                chance = 0.08
            elif zone == "commercial":
                chance = 0.18
            elif zone == "residential":
                chance = 0.42
            else:
                chance = 0.24

            if self._count_adjacent_nature(x, y) >= 2:
                chance += 0.18
            elif self._count_adjacent_nature(x, y) == 1:
                chance += 0.10

            if self.rng.random() > min(chance, 0.82):
                continue
            if self.grid.occupy(x, y, NATURE):
                self.park_cells.append((x, y))

    def _count_adjacent_nature(self, x: int, y: int) -> int:
        count = 0
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            if self.grid.get(x + dx, y + dy) == NATURE:
                count += 1
        return count

    # -------------------------------------------------------------------------
    # Ground coverage (every cell gets a visible base)
    # -------------------------------------------------------------------------
    def create_ground_base(self) -> None:
        grass_mat = self.materials.get_flat("MAT_GRASS_CARTOON", "#7CFC00", roughness=0.9)
        sidewalk_mat = self.materials.get_flat("MAT_SIDEWALK_WARM", "#A9A9A9", roughness=0.85)
        road_mat = self.materials.get_flat("MAT_ROAD_BASE", "#5C5C5C", roughness=0.95)

        self.ground_templates = {
            "grass": self._create_ground_tile_template("TPL_GROUND_GRASS", grass_mat),
            "sidewalk": self._create_ground_tile_template("TPL_GROUND_SIDEWALK", sidewalk_mat),
            "road": self._create_ground_tile_template("TPL_GROUND_ROAD", road_mat),
        }

        for x, y in self.grid.iter_cells():
            cell = self.grid.get(x, y)
            if cell == BUILDING:
                key = "sidewalk"
            elif cell == ROAD:
                key = "road"
            else:
                key = "grass"
            self._place_ground_tile(self.ground_templates[key], x, y)
            self.stats["ground_tiles"] += 1

    def place_green_ground_cover(self) -> None:
        """
        Adds a grass asset to every non-road, non-building cell so empty land is
        never just a flat plane. The plane below guarantees full coverage, and
        these patches give the city a less barren look.
        """
        for x, y in self.grid.iter_cells():
            cell = self.grid.get(x, y)
            if cell in (ROAD, BUILDING):
                continue

            grass_name = "grass_large" if cell == NATURE or self.rng.random() < 0.65 else "grass"
            scale = self.rng.uniform(1.0, 1.35) if grass_name == "grass_large" else self.rng.uniform(0.9, 1.2)
            self._spawn_nature_asset(
                grass_name,
                x,
                y,
                offset_x=0.0,
                offset_y=0.0,
                z_offset=GROUND_PATCH_Z,
                rot_z=self.rng.uniform(0.0, math.tau),
                scale_mul=scale,
            )
            self.stats["green_ground_patches"] += 1

            if cell == EMPTY and self.rng.random() < 0.25:
                ox, oy = self._cluster_offset_within_tile(0.22)
                self._spawn_nature_asset(
                    self.rng.choice(ASSET_DICT["nature"]["flowers"]),
                    x,
                    y,
                    offset_x=ox,
                    offset_y=oy,
                    z_offset=GROUND_PATCH_Z,
                    rot_z=self.rng.uniform(0.0, math.tau),
                    scale_mul=self.rng.uniform(0.85, 1.15),
                )
                self.stats["green_ground_patches"] += 1

    def _create_ground_tile_template(
        self, name: str, material: bpy.types.Material
    ) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"{name}_MESH")
        half = TILE_SIZE * 0.5
        verts = [(-half, -half, 0.0), (half, -half, 0.0), (half, half, 0.0), (-half, half, 0.0)]
        faces = [(0, 1, 2, 3)]
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        mesh.materials.append(material)

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

    # -------------------------------------------------------------------------
    # Instantiate planned modules
    # -------------------------------------------------------------------------
    def place_roads(self) -> None:
        for x, y, asset_name, rot in self.road_plan:
            self.io.instance(self.assets.get(asset_name), self.io.roads_col, self.to_world(x, y), rot)
            self.stats["roads"] += 1

    def place_buildings(self) -> None:
        for x, y, asset_name, rot, _zone in self.building_plan:
            self.io.instance(self.assets.get(asset_name), self.io.buildings_col, self.to_world(x, y), rot)
            self.stats["buildings"] += 1

    def place_industrial_details(self) -> None:
        for x, y, asset_name, rot in self.industrial_detail_plan:
            self.io.instance(self.assets.get(asset_name), self.io.nature_col, self.to_world(x, y), rot)
            self.stats["industrial_detail"] += 1

    # -------------------------------------------------------------------------
    # Park cluster generation
    # -------------------------------------------------------------------------
    def place_park_clusters(self) -> None:
        for x, y in self.park_cells:
            if (x, y) in self.industrial_detail_cells:
                continue
            self._spawn_park_cluster(x, y)
            self.stats["parks"] += 1

    def _spawn_park_cluster(self, x: int, y: int) -> None:
        """
        Dense park cluster inside one TILE_SIZE x TILE_SIZE cell:
        - 1-2 trees near center
        - 2-4 bushes around them
        - 3-5 flowers for color breakup
        - occasional rock and log accents
        - extra grass tufts to soften the tile edges
        """
        tree_count = self.rng.randint(1, 2)
        for _ in range(tree_count):
            ox, oy = self._cluster_offset_within_tile(0.18)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["trees"]),
                x,
                y,
                offset_x=ox,
                offset_y=oy,
                z_offset=0.0,
                rot_z=self.rng.uniform(0.0, math.tau),
                scale_mul=self.rng.uniform(0.88, 1.18),
            )
            self.stats["park_objects"] += 1

        for _ in range(self.rng.randint(2, 4)):
            ox, oy = self._cluster_offset_within_tile(0.34)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["bushes"]),
                x,
                y,
                offset_x=ox,
                offset_y=oy,
                z_offset=0.0,
                rot_z=self.rng.uniform(0.0, math.tau),
                scale_mul=self.rng.uniform(0.82, 1.15),
            )
            self.stats["park_objects"] += 1

        for _ in range(self.rng.randint(3, 5)):
            ox, oy = self._cluster_offset_within_tile(0.42)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["flowers"]),
                x,
                y,
                offset_x=ox,
                offset_y=oy,
                z_offset=0.0,
                rot_z=self.rng.uniform(0.0, math.tau),
                scale_mul=self.rng.uniform(0.8, 1.2),
            )
            self.stats["park_objects"] += 1

        for _ in range(self.rng.randint(1, 3)):
            ox, oy = self._cluster_offset_within_tile(0.40)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["grass"]),
                x,
                y,
                offset_x=ox,
                offset_y=oy,
                z_offset=0.0,
                rot_z=self.rng.uniform(0.0, math.tau),
                scale_mul=self.rng.uniform(0.9, 1.25),
            )
            self.stats["park_objects"] += 1

        if self.rng.random() < 0.35:
            ox, oy = self._cluster_offset_within_tile(0.36)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["rocks"]),
                x,
                y,
                offset_x=ox,
                offset_y=oy,
                z_offset=0.0,
                rot_z=self.rng.uniform(0.0, math.tau),
                scale_mul=self.rng.uniform(0.82, 1.12),
            )
            self.stats["park_objects"] += 1

        if self.rng.random() < 0.20:
            ox, oy = self._cluster_offset_within_tile(0.32)
            self._spawn_nature_asset(
                self.rng.choice(ASSET_DICT["nature"]["logs"]),
                x,
                y,
                offset_x=ox,
                offset_y=oy,
                z_offset=0.0,
                rot_z=self.rng.uniform(0.0, math.tau),
                scale_mul=self.rng.uniform(0.85, 1.10),
            )
            self.stats["park_objects"] += 1

    def _cluster_offset_within_tile(self, spread_ratio: float = 0.34) -> Tuple[float, float]:
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
        offset_x = max(-half, min(half, offset_x))
        offset_y = max(-half, min(half, offset_y))
        wx, wy, wz = self.to_world(gx, gy, z_offset)
        self.io.instance(
            self.assets.get(asset_name),
            self.io.nature_col,
            (wx + offset_x, wy + offset_y, wz),
            rot_z,
            scale_mul=scale_mul,
        )


def main() -> None:
    generator = CityGenerator()
    generator.run()


if __name__ == "__main__":
    main()
