"""
Blender Procedural City Generator v3.0 - 高级城市规划版
=====================================================
核心约束: scale=0.01, 只修改Z轴旋转(rotation_euler[2])
作者: Claude Code | 版本: 3.0
"""

import bpy, math, random, os
from mathutils import Vector

class CityConfig:
    """城市生成配置"""
    # 资源路径 (OBJ 格式)
    road_assets_path = r"C:\Users\86153\Downloads\asset\kenney_city-kit-roads\Models\OBJ format"
    commercial_assets_path = r"C:\Users\86153\Downloads\asset\kenney_city-kit-commercial_2.1\Models\OBJ format"
    industrial_assets_path = r"C:\Users\86153\Downloads\asset\kenney_city-kit-industrial_1.0\Models\OBJ format"
    suburban_assets_path = r"C:\Users\86153\Downloads\asset\kenney_city-kit-suburban_20\Models\OBJ format"
    nature_assets_path = r"C:\Users\86153\Downloads\asset\kenney_city-kit-suburban_20\Models\OBJ format"  # 使用郊区的树木
    # 缩放因子（Kenney模型原始尺寸约100单位，缩放后为1单位=1米）
    model_scale = 0.01
    # 实际尺寸（米）
    real_cell_size = 10.0  # 单元格实际大小（米）
    real_road_segment = 2.0  # 道路段实际长度（米）
    real_water_width = 4.0  # 水系实际宽度（米）
    # 原始单位尺寸（缩放补偿：乘以100）
    cell_size = 1000.0  # 10米 / 0.01 = 1000 原始单位
    road_segment_length = 200.0  # 2米 / 0.01 = 200 原始单位
    water_width = 400.0  # 4米 / 0.01 = 400 原始单位
    # 统一缩放
    road_scale = 0.01
    building_scale = 0.01
    nature_scale = 0.01
    # 分区配置 (归一化距离)
    zone_cbd_radius = 0.3
    zone_suburban_start = 0.3
    zone_industrial_start = 0.7
    # 公园配置
    park_probability = 0.15

class BlenderCmd:
    """Blender 操作封装"""
    def clear_scene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

    def import_obj(self, path, col_name):
        """导入 OBJ 文件到集合"""
        if not os.path.exists(path):
            return None
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)
        try:
            before = set(bpy.context.scene.objects)
            bpy.ops.wm.obj_import(filepath=path)
            after = set(bpy.context.scene.objects)
            for obj in after - before:
                if obj.name not in col.objects:
                    col.objects.link(obj)
                for c in list(obj.users_collection):
                    if c != col:
                        c.objects.unlink(obj)
            return col
        except:
            return None

    def duplicate(self, obj, collection):
        new_obj = obj.copy()
        new_obj.data = obj.data
        new_obj.animation_data_clear()
        collection.objects.link(new_obj)
        return new_obj

    def set_transform(self, obj, loc, rot_z, scale):
        obj.location = loc
        obj.rotation_euler[2] = rot_z
        obj.scale = (scale, scale, scale)
        return obj

    def create_empty(self, name, loc, parent=None):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.location = loc
        bpy.context.collection.objects.link(empty)
        if parent:
            empty.parent = parent
        return empty

class AssetsImporter:
    """资产导入器"""
    def __init__(self, config, blender):
        self.config = config
        self.blender = blender
        self.assets = {
            "roads": {"straight": [], "cross": [], "bridge": [], "pillar": []},
            "commercial": {"skyscrapers": [], "standard": []},
            "industrial": {"warehouses": [], "factories": []},
            "suburban": {"houses": []},
            "nature": {"trees": [], "plants": [], "rocks": []}
        }
        self.source_cols = {}

    def match(self, name, patterns):
        name_lower = name.lower()
        return any(p.lower() in name_lower for p in patterns)

    def import_all(self):
        # 道路系统
        self._scan(self.config.road_assets_path, "roads", {
            "straight": ["road-straight"],
            "cross": ["road-crossroad", "road-intersection"],
            "bridge": ["road-bridge"],
            "pillar": ["bridge-pillar"]
        })
        # 商业区 - 摩天大楼和普通建筑
        self._scan(self.config.commercial_assets_path, "commercial", {
            "skyscrapers": ["skyscraper"],
            "standard": ["building-a", "building-b", "building-c", "building-d", "building-e",
                        "building-f", "building-g", "building-h", "building-i", "building-j",
                        "building-k", "building-l", "building-m", "building-n"]
        })
        # 工业区 - 所有 building- 开头但不含 skyscraper 的
        self._scan(self.config.industrial_assets_path, "industrial", {
            "warehouses": ["building-"],
            "chimneys": ["chimney-"],
            "tanks": ["detail-tank"]
        })
        # 郊区 - 住宅
        self._scan(self.config.suburban_assets_path, "suburban", {
            "houses": ["building-type-"],
            "fences": ["fence"],
            "paths": ["path-", "driveway-"]
        })
        # 自然 - 树木和植物
        self._scan(self.config.nature_assets_path, "nature", {
            "trees": ["tree-"],
            "plants": ["planter"]
        })
        return self.assets

    def _scan(self, path, category, patterns):
        if not os.path.exists(path):
            print(f"[警告] 路径不存在: {path}")
            return
        for obj_file in os.listdir(path):
            if not obj_file.lower().endswith('.obj'):
                continue
            name = os.path.splitext(obj_file)[0]
            full_path = os.path.join(path, obj_file)
            col = self.blender.import_obj(full_path, f"temp_{name}")
            if not col:
                continue
            for obj in col.objects:
                if obj.type == 'MESH':
                    for sub_cat, pats in patterns.items():
                        if self.match(name, pats):
                            self.assets[category][sub_cat].append(obj)
                            print(f"[导入] {category}/{sub_cat}: {name}")
                            break
            self.source_cols[name] = col

    def get_random(self, category, sub_cat=None):
        if sub_cat:
            pool = self.assets.get(category, {}).get(sub_cat, [])
        else:
            pool = []
            for sub_list in self.assets.get(category, {}).values():
                pool.extend(sub_list)
        return random.choice(pool) if pool else None

class RoadGenerator:
    """道路生成器 - 含水系桥梁"""
    def __init__(self, config, blender, assets):
        self.config = config
        self.blender = blender
        self.assets = assets
        self.parent = None

    def generate(self, grid_size, cell_size):
        self.parent = self.blender.create_empty("Roads", (0, 0, 0))
        segs_per_cell = int(cell_size / self.config.road_segment_length)
        total = grid_size * cell_size
        center = total / 2

        for row in range(grid_size + 1):
            for col in range(grid_size + 1):
                x, y = col * cell_size, row * cell_size
                # 纵向河流：沿 X 轴中心
                on_water_x = abs(x - center) < self.config.water_width / 2

                if row < grid_size and col < grid_size:
                    self._place_cross(x, y, on_water_x)

                # 横向道路 (沿 X 轴方向)
                if col < grid_size:
                    if on_water_x:
                        self._place_bridge(x, y, 0, segs_per_cell)
                    else:
                        self._place_road(x, y, 0, segs_per_cell)

                # 纵向道路 (沿 Y 轴方向)
                if row < grid_size:
                    # 纵向道路在河流处需要桥梁
                    self._place_road(x, y, math.pi/2, segs_per_cell)
        return self.parent

    def _place_cross(self, x, y, is_bridge):
        asset = self.assets.get_random("roads", "bridge" if is_bridge else "cross")
        if asset:
            obj = self.blender.duplicate(asset, bpy.context.collection)
            self.blender.set_transform(obj, (x, y, 0.01), 0, self.config.road_scale)
            obj.parent = self.parent

    def _place_road(self, sx, sy, rot, count):
        asset = self.assets.get_random("roads", "straight")
        if not asset:
            return
        for i in range(count):
            off = i * self.config.road_segment_length
            x = sx + (off if abs(rot) < 0.1 else 0)
            y = sy + (0 if abs(rot) < 0.1 else off)
            obj = self.blender.duplicate(asset, bpy.context.collection)
            self.blender.set_transform(obj, (x, y, 0), rot, self.config.road_scale)
            obj.parent = self.parent

    def _place_bridge(self, sx, sy, rot, count):
        bridge = self.assets.get_random("roads", "bridge")
        pillar = self.assets.get_random("roads", "pillar")
        for i in range(count):
            off = i * self.config.road_segment_length
            x = sx + (off if abs(rot) < 0.1 else 0)
            y = sy + (0 if abs(rot) < 0.1 else off)
            if bridge:
                obj = self.blender.duplicate(bridge, bpy.context.collection)
                self.blender.set_transform(obj, (x, y, 0.5), rot, self.config.road_scale)
                obj.parent = self.parent
            if pillar:
                obj = self.blender.duplicate(pillar, bpy.context.collection)
                self.blender.set_transform(obj, (x, y, 0), 0, self.config.road_scale)
                obj.parent = self.parent

class PlotGenerator:
    """街区生成器 - 含分区和自然"""
    def __init__(self, config, blender, assets):
        self.config = config
        self.blender = blender
        self.assets = assets
        self.parent = None

    def get_zone(self, x, y, center, radius):
        dist = math.sqrt((x - center)**2 + (y - center)**2)
        factor = dist / radius
        if factor < self.config.zone_cbd_radius:
            return "commercial"
        elif factor < self.config.zone_industrial_start:
            return "suburban"
        else:
            return "industrial"

    def generate(self, grid_size, cell_size, plot_size):
        self.parent = self.blender.create_empty("Plots", (0, 0, 0))
        total = grid_size * cell_size
        center = total / 2
        radius = total / 2

        for row in range(grid_size):
            for col in range(grid_size):
                x = col * cell_size + cell_size / 2
                y = row * cell_size + cell_size / 2

                # 跳过纵向河流区域 (X轴中心)
                if abs(x - center) < self.config.water_width / 2:
                    continue

                zone = self.get_zone(x, y, center, radius)
                plot_empty = self.blender.create_empty(
                    f"Plot_{row}_{col}", (x, y, 0), self.parent
                )

                if random.random() < self.config.park_probability:
                    self._place_park(plot_empty, x, y, plot_size)
                else:
                    self._place_building(plot_empty, x, y, zone, plot_size)
        return self.parent

    def _place_building(self, parent, x, y, zone, size):
        if zone == "commercial":
            if random.random() < 0.3:
                asset = self.assets.get_random("commercial", "skyscrapers")
            else:
                asset = self.assets.get_random("commercial", "standard")
        elif zone == "suburban":
            asset = self.assets.get_random("suburban", "houses")
        else:
            # 工业区：随机选择仓库或烟囱
            asset = self.assets.get_random("industrial", "warehouses")

        if asset:
            obj = self.blender.duplicate(asset, bpy.context.collection)
            rot = random.choice([0, math.pi/2, math.pi, 3*math.pi/2])
            self.blender.set_transform(obj, (x, y, 0), rot, self.config.building_scale)
            obj.parent = parent

    def _place_park(self, parent, x, y, size):
        """放置树木和植物 - 带调试信息"""
        print(f"[公园] 中心: ({x}, {y}), 尺寸: {size}")
        tree_count = random.randint(3, 8)
        plant_count = random.randint(5, 15)

        print(f"[公园] 生成 {tree_count} 棵树木, {plant_count} 棵植物...")

        for _ in range(tree_count):
            tree = self.assets.get_random("nature", "trees")
            if tree:
                obj = self.blender.duplicate(tree, bpy.context.collection)
                # 计算随机偏移（相对于街区中心）
                ox = random.uniform(-size * 0.5, size * 0.5)
                oy = random.uniform(-size * 0.5, size * 0.5)
                rot = random.uniform(0, 2 * math.pi)
                self.blender.set_transform(obj, (x + ox, y + oy, 0), rot, self.config.nature_scale)
                obj.parent = parent
                print(f"  树位置: ({x+ox:.2f}, {y+oy:.2f}), rot={rot:.2f}")

        for _ in range(plant_count):
            plant = self.assets.get_random("nature", "plants")
            if plant:
                obj = self.blender.duplicate(plant, bpy.context.collection)
                # 计算随机偏移
                ox = random.uniform(-size * 0.5, size * 0.5)
                oy = random.uniform(-size * 0.5, size * 0.5)
                rot = random.uniform(0, 2 * math.pi)
                self.blender.set_transform(obj, (x+ox, y+oy, 0), rot, self.config.nature_scale)
                obj.parent = parent
                print(f"  植物-位置: ({x+ox:.2f}, y={y+oy:.2f}), rot={rot:.2f}")

class CityGenerator:
    """城市生成器主类"""
    def __init__(self):
        self.config = CityConfig()
        self.blender = BlenderCmd()
        self.assets = None

    def generate(self, grid_size=5, cell_size=None):
        if cell_size is None:
            cell_size = self.config.cell_size
        print("=" * 50)
        print("城市生成器 v3.0 - 开始生成")
        print("=" * 50)

        # 清除场景
        print("[1/4] 清除场景...")
        self.blender.clear_scene()

        # 导入资产
        print("[2/4] 导入资产...")
        self.assets = AssetsImporter(self.config, self.blender)
        self.assets.import_all()

        # 生成道路
        print("[3/4] 生成道路网络...")
        road_gen = RoadGenerator(self.config, self.blender, self.assets)
        road_gen.generate(grid_size, cell_size)

        # 生成街区
        print("[4/4] 生成城市街区...")
        plot_gen = PlotGenerator(self.config, self.blender, self.assets)
        plot_gen.generate(grid_size, cell_size, cell_size * 0.8)

        print("=" * 50)
        print("城市生成完成!")
        print(f"网格: {grid_size}x{grid_size}")
        print("=" * 50)

# ============================================================================
# 执行入口
# ============================================================================
if __name__ == "__main__":
    city = CityGenerator()
    city.generate(grid_size=5)
