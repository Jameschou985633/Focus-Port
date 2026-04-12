"""
Blender 批量导出 Kenney 城市 OBJ 为透明 PNG 精灵，并生成 manifest.json。

运行方式：
1) Blender Text Editor 打开本脚本后 Alt+P
2) 或命令行：blender --background --python export_city_obj_sprites.py
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import bpy
from mathutils import Vector


ASSET_ROOT = Path(r"C:\Users\86153\Downloads\asset")
OUTPUT_ROOT = Path(r"C:\Users\86153\PycharmProjects\PythonProject2\city_sprites")
MANIFEST_PATH = Path(r"C:\Users\86153\PycharmProjects\PythonProject2\city_sprite_manifest.json")

SOURCE_PACKS: Dict[str, Path] = {
    "commercial": ASSET_ROOT / "kenney_city-kit-commercial_2.1" / "Models" / "OBJ format",
    "industrial": ASSET_ROOT / "kenney_city-kit-industrial_1.0" / "Models" / "OBJ format",
    "roads": ASSET_ROOT / "kenney_city-kit-roads" / "Models" / "OBJ format",
    "suburban": ASSET_ROOT / "kenney_city-kit-suburban_20" / "Models" / "OBJ format",
}

TYPE_CONFIG = {
    "plant": {"name": "植物", "tier": "Plant", "price": 100, "currency": "coins", "size": [84, 84], "render_size": 256},
    "road": {"name": "道路", "tier": "Road", "price": 50, "currency": "coins", "size": [72, 40], "render_size": 256},
    "building_b": {"name": "B级建筑", "tier": "B", "price": 300, "currency": "coins", "size": [88, 120], "render_size": 384},
    "building_a": {"name": "A级建筑", "tier": "A", "price": 500, "currency": "coins", "size": [96, 136], "render_size": 384},
    "building_s": {"name": "S级建筑", "tier": "S", "price": 10, "currency": "diamonds", "size": [112, 164], "render_size": 512},
}


def classify_asset(pack_name: str, model_name: str) -> Optional[str]:
    """按资源包 + 模型名前缀自动映射建筑类型。"""
    if pack_name == "roads":
        return "road"
    if pack_name == "industrial":
        return "building_b"
    if pack_name == "commercial":
        if model_name.startswith("building-skyscraper"):
            return "building_s"
        if model_name.startswith("building-") or model_name.startswith("low-detail-building"):
            return "building_a"
        return None
    if pack_name == "suburban":
        if model_name.startswith("tree") or model_name.startswith("planter"):
            return "plant"
        if model_name.startswith("building-type"):
            return "building_b"
    return None


def ensure_scene() -> bpy.types.Object:
    """创建统一相机、灯光和透明背景。"""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"

    for obj_name in ("CITY_SPRITE_CAMERA", "CITY_SPRITE_SUN", "CITY_SPRITE_FILL"):
        existing = bpy.data.objects.get(obj_name)
        if existing is not None:
            bpy.data.objects.remove(existing, do_unlink=True)

    cam_data = bpy.data.cameras.new("CITY_SPRITE_CAMERA_DATA")
    cam_data.type = "ORTHO"
    camera = bpy.data.objects.new("CITY_SPRITE_CAMERA", cam_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (6.5, -6.5, 5.8)
    camera.rotation_euler = (math.radians(60.0), 0.0, math.radians(45.0))
    scene.camera = camera

    sun_data = bpy.data.lights.new("CITY_SPRITE_SUN_DATA", "SUN")
    sun_data.energy = 4.8
    sun = bpy.data.objects.new("CITY_SPRITE_SUN", sun_data)
    sun.location = (8.0, -10.0, 16.0)
    sun.rotation_euler = (math.radians(45.0), 0.0, math.radians(35.0))
    bpy.context.scene.collection.objects.link(sun)

    fill_data = bpy.data.lights.new("CITY_SPRITE_FILL_DATA", "AREA")
    fill_data.energy = 4500.0
    fill_data.size = 25.0
    fill = bpy.data.objects.new("CITY_SPRITE_FILL", fill_data)
    fill.location = (-6.0, -6.0, 12.0)
    fill.rotation_euler = (math.radians(180.0), 0.0, 0.0)
    bpy.context.scene.collection.objects.link(fill)

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.78, 0.88, 1.0, 1.0)
        bg.inputs["Strength"].default_value = 0.8
    return camera


def remove_object_tree(obj: bpy.types.Object) -> None:
    for child in list(obj.children):
        remove_object_tree(child)
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh and mesh.users == 0 and hasattr(bpy.data, "meshes") and mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def clear_imported_objects(before_names: set[str]) -> None:
    for obj in list(bpy.data.objects):
        if obj.name not in before_names and not obj.name.startswith("CITY_SPRITE_"):
            remove_object_tree(obj)


def import_obj(filepath: Path) -> bpy.types.Object:
    before_names = {obj.name for obj in bpy.data.objects}
    bpy.ops.object.select_all(action="DESELECT")
    try:
        bpy.ops.wm.obj_import(filepath=str(filepath))
    except Exception:
        bpy.ops.import_scene.obj(filepath=str(filepath))

    imported = [obj for obj in bpy.data.objects if obj.name not in before_names]
    if not imported:
        raise RuntimeError(f"OBJ import failed: {filepath}")

    root = bpy.data.objects.new(f"TMP_ROOT__{filepath.stem}", None)
    bpy.context.scene.collection.objects.link(root)
    imported_set = set(imported)
    for obj in imported:
        if obj.parent not in imported_set:
            obj.parent = root
            obj.matrix_parent_inverse = root.matrix_world.inverted()
    bpy.context.view_layer.update()
    return root


def object_bounds(root: bpy.types.Object) -> Tuple[Vector, Vector]:
    points: List[Vector] = []
    for obj in [root, *root.children_recursive]:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        return Vector((0.0, 0.0, 0.0)), Vector((1.0, 1.0, 1.0))
    min_v = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    max_v = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return min_v, max_v


def normalize_object(root: bpy.types.Object) -> float:
    """把模型 XY 居中、底部贴到 z=0，并返回最大跨度。"""
    bpy.context.view_layer.update()
    min_v, max_v = object_bounds(root)
    root.location.x -= (min_v.x + max_v.x) * 0.5
    root.location.y -= (min_v.y + max_v.y) * 0.5
    root.location.z -= min_v.z
    bpy.context.view_layer.update()

    min_v, max_v = object_bounds(root)
    span_x = max_v.x - min_v.x
    span_y = max_v.y - min_v.y
    span_z = max_v.z - min_v.z
    return max(0.5, span_x, span_y, span_z)


def iter_obj_files() -> Iterable[Tuple[str, Path]]:
    for pack_name, pack_dir in SOURCE_PACKS.items():
        if not pack_dir.exists():
            print(f"[WARN] missing pack dir: {pack_dir}")
            continue
        for filepath in sorted(pack_dir.glob("*.obj")):
            yield pack_name, filepath


def build_manifest_item(pack_name: str, filepath: Path, object_type: str, sprite_path: Path) -> dict:
    cfg = TYPE_CONFIG[object_type]
    item_code = f"{pack_name}_{filepath.stem}".replace("-", "_")
    return {
        "item_code": item_code,
        "source_package": pack_name,
        "source_obj_path": str(filepath),
        "sprite_path": sprite_path.relative_to(MANIFEST_PATH.parent).as_posix(),
        "object_type": object_type,
        "name": f"{cfg['name']} {filepath.stem}",
        "tier": cfg["tier"],
        "price": cfg["price"],
        "currency": cfg["currency"],
        "size": cfg["size"],
    }


def render_model(filepath: Path, object_type: str, sprite_path: Path, camera: bpy.types.Object) -> None:
    scene = bpy.context.scene
    scene.render.resolution_x = TYPE_CONFIG[object_type]["render_size"]
    scene.render.resolution_y = TYPE_CONFIG[object_type]["render_size"]
    scene.render.filepath = str(sprite_path)

    before_names = {obj.name for obj in bpy.data.objects}
    root = import_obj(filepath)
    max_span = normalize_object(root)
    camera.data.ortho_scale = max(4.0, max_span * 2.6)
    bpy.context.view_layer.update()

    sprite_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)

    if root.name in bpy.data.objects:
        remove_object_tree(root)
    clear_imported_objects(before_names)


def export_all() -> None:
    camera = ensure_scene()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    manifest_items: List[dict] = []
    total = 0
    skipped = 0

    for pack_name, filepath in iter_obj_files():
        object_type = classify_asset(pack_name, filepath.stem)
        if object_type is None:
            skipped += 1
            continue

        sprite_path = OUTPUT_ROOT / object_type / f"{pack_name}_{filepath.stem}.png"
        render_model(filepath, object_type, sprite_path, camera)
        manifest_items.append(build_manifest_item(pack_name, filepath, object_type, sprite_path))
        total += 1
        print(f"[EXPORT] {filepath.name} -> {sprite_path}")

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "asset_root": str(ASSET_ROOT),
        "sprite_root": str(OUTPUT_ROOT),
        "items": sorted(manifest_items, key=lambda item: (item["object_type"], item["item_code"])),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] exported={total}, skipped={skipped}, manifest={MANIFEST_PATH}")


if __name__ == "__main__":
    export_all()
