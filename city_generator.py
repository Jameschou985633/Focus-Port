"""
Blender Procedural City Generator - 程序化城市生成器 v3.0
=====================================================
高级城市规划版:
- 5套 Kenney 资产包 (道路、商业、 工业, 郊区、 自然)
- 娡块化街区管理 (Empty 父级)
核心约束:
- scale = 0.01 (Kenney模型会放大100倍)
- 只修改z轴旋转: obj.rotation_euler[2] = angle (保留模型原始X/Y旋转)
使用方法:
1. 在Blender中打开 Text Editor
2. 加载此脚本
3. 按 Alt+P 运行
4. 按 Home 键查看完整城市
作者: Claude Code
版本: 3.0 (Advanced Zoning Edition)
"""

import bpy
import math
import random
from mathutils import Vector
import os

# ============================================================================
# 模块: 声明和常量
# ============================================================================

# 道路资产
ROAD_ASSETS = {
    "straight": "road-straight",
    "straight_half": "road-straight-half",
    "curve": "road-curve",
    "bend": "road-bend",
    "bend_square": "road-bend-square"
    "intersection": "road-intersection"
    "crossroad": "road-crossroad"
    "end": "road-end"
    "end_round": "road-end-round"
    "roundabout": "road-roundabout"
    "square": "road-square"
}

 # 商业资产
Commercial_assets = {
    "skyscrapers": [f"building-skyscraper-{c}" for c in "abcde"],
    "standard": [f"building-{c}" for c in "abcdefghijklmn"],
}
# 工业资产
Industrial_assets = {
    "warehouses": [f"building-industrial-warehouse-{c}" for c in "ab"],
    "factories": [f"building-industrial-factory-{c}" for c in "abc"],
}
# 郊区资产
Suburban_assets = {
    "houses": [f"house-{c}" for c in "abcdefghijklmnopqrstuvwxyz"]
}
# 自然资产
Nature_assets = {
    "trees": ["tree-large", "tree-small", "tree-pine", "tree-oak", " "plants": ["plant-large", "plant-small"],
    "rocks": ["rock-a", "rock-b", "rock-c"]
}
# 集合名称
COLLECTION_ROOT = "CITY_ROOT"
COLLECTION_ROADS = "CITY_ROADS"
COLLECTION_BUILDINGS = "CITY_BUILDINGS"
COLLECTION_PLOTS = "CITY_PLOTS"

COL_COLLECTION_NATURE = "CITY_NATURE"
COLLECTION_WATER = "CITY_WATER"

# ============================================================================
# 模块: 娡拟 Blender 命令 (部分模块化)
# ============================================================================
class BlenderCommand:
    """模拟 Blender 操作的模块化封装"""

    def clear_scene(self):
        """清除场景中的所有对象"""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
    def import_fbx(self, path, collection_name):
        """导入 FBX 文件到集合"""
        if not os.path.exists(path):
            return None
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
        try:
            before = set(bpy.context.scene.objects)
            bpy.ops.import_scene.fbx(filepath=path)
            after = set(bpy.context.scene.objects)
            imported = after - before
            for obj in imported:
                if obj.name not in collection.objects:
                    collection.objects.link(obj)
                for c in list(obj.users_collection):
                    if c != collection:
                        c.objects.unlink(obj)
        except Exception as e:
            print(f"[错误] 导入失败: {path}: {e}")
            return None
        return collection
    def duplicate_object(self, obj, collection):
        """复制对象到集合"""
        new_obj = obj.copy()
        new_obj.data = obj.data
        new_obj.animation_data_clear()
        collection.objects.link(new_obj)
        return new_obj
    def set_transform(self, obj, location, rot_z, scale):
        """设置对象变换，只修改 z 轴旋转"""
        obj.location = location
        obj.rotation_euler[2] = rot_z
        obj.scale = (scale, scale, scale)
        return obj
# ============================================================================
# 模块: 城市配置
# ============================================================================
class CityConfig:
    """城市生成配置"""

    # === 訡型命名模式 ===
    # 騡型命名模式
    road_straight_names: list = ["road-straight", "road-crossroad_names: list = ["road-crossroad"]
    road_bridge_names: list = ["road-bridge", " bridge_pillar_names: list = ["bridge-pillar", "bridge-pillar-wide"]
    # 商业
    commercial_skyscraper_names: list = [
        "building-skyscraper-a", "building-skyscraper-b", "building-skyscraper-c",
        "building-skyscraper-d", "building-skyscraper-e"
    ]
    commercial_standard_names: list = [
        f"building-{c}" for c in "abcdefghijklmn"
    ]
    # 工业
    industrial_warehouse_names: list = [
        "building-industrial-warehouse-a", "building-industrial-warehouse-b"
    ]
    industrial_factory_names: list = [
        "building-industrial-factory-a", "building-industrial-factory-b",
        "building-industrial-factory-c"
    ]
    # 騡型命名模式 - 騡糊检测
    model_name_fuzzy_threshold: int = 80  # 模糊匹配阈值

    # 騡型命名模式 - 郊区
    suburban_house_names: list = [
        f"house-{c}" for c in "abcdefghijklmnopqrstuvwxyz"
    ]
    # 模型命名模式 - 自然
    nature_tree_names: list = [
        "tree-large", "tree-small", "tree-pine", "tree-oak"
    ]
    nature_plant_names: list = [
        "plant-large", "plant-small"
    ]
    nature_rock_names: list = [
        "rock-a", "rock-b", "rock-c"
    ]
    # === 资源路径 ===
    road_assets_path: str = r"C:\Users\86153\Downloads\kenney_city-kit-roads\Models\FBX format"
    commercial_assets_path: str = r"C:\Users\86153\Downloads\kenney_city-kit-commercial_2.1\Models\FBX format"
    industrial_assets_path: str = r"C:\Users\86153\Downloads\kenney_city-kit-industrial_1.0\Models\FBX format"
    suburban_assets_path: str = r"C:\Users\86153\Downloads\kenney_city-kit-suburban_20\Models\FBX format"
    nature_assets_path: str = r"C:\Users\86153\Downloads\kenney_nature-kit (1)\Models\FBX format"
    # === 娡型缩放 ===
    road_scale: float = 0.01
    building_scale: float = 0.01
    nature_scale: float = 0.01
    # === 模型尺寸 ===
    road_segment_length: float = 2.0
    # === 模型命名模式 - 其他 ===
    fallback_model_name: str = "building-a"
    # === 娡型命名模式 - 分区配置 ===
    # 分区配置
    zone_cbd_radius: float = 0.3          # CBD 区域半径 (归一化距离)
    zone_suburban_start: float = 0.3          # 住宅区开始
    zone_industrial_start: float = 0.7          # 工业区开始
    # === 模型命名模式 - 水系配置 ===
    water_axis: str = "y"              # "x" 或 "y" 调线在中心轴上
    water_width: float = 4.0             # 水系宽度 (米)
    # === 模型命名模式 - 公园配置 ===
    park_probability: float = 0.15          # 空地街区成为公园的概率
    park_tree_count_range: tuple = (3, 8)  # 公园树木数量范围
    park_plant_count_range: tuple = (5, 15)  # 公园植物数量范围
    # === 模型命名模式 - 街区配置 ===
    grid_size_x: int = 5              # 横向街区数
    grid_size_y: int = 5              # 纵向街区数
    block_size: float = 12.0          # 每个街区尺寸（米）
    road_width: float = 4.0           # 道路宽度（米)
    building_margin: float = 1.5            # 契约道路边距
    building_spacing: float = 2.0           # 契约间距
    # === 模型命名模式 - 密度配置 ===
    empty_plot_probability: float = 0.10    # 完全空地概率(公园/广场)
    sparse_plot_probability: float = 0.20   # 稀疏街区概率(1-2栋建筑)
    min_buildings_per_plot: int = 1         # 正常街区最小建筑数
    max_buildings_per_plot: int = 4         # 正常街区最大建筑数
    center_max_buildings: int = 5           # 中心最大建筑数
    edge_max_buildings: int = 2             # 边缘最大建筑数
    skyscraper_probability: float = 0.3     # 摩天大楼概率
    verbose: bool = True                    # 详细日志
    random_seed: int = 42                # 随机种子
    clear_existing: bool = True             # 生成前清除现有城市
    @property
    def city_size_x(self) -> float:
        """城市总宽度"""
        return self.grid_size_x * (self.block_size + self.road_width)
    @property
    def city_size_y(self) -> float:
        """城市总深度"""
        return self.grid_size_y * (self.block_size + self.road_width)
# 实例化配置
config = CityConfig()
# ============================================================================
# 模块: 资产导入器
# ============================================================================
class AssetsImporter:
    """资产导入器"""

    def __init__(self, config: CityConfig):
        self.config = config
        self.road_assets = []
        self.building_assets = []
        self.nature_assets = []
        self.skyscraper_assets = []
        self.warehouse_assets = []
        self.factory_assets = []
        self.house_assets = []
        self.tree_assets = []
        self.plant_assets = []
        self.rock_assets = []
        self.bridge_assets = []
        self.bridge_pillar_assets = []
        self.bridge_road_assets = []
        self.imported_roads = False
        self.imported_commercial = False
        self.imported_industrial = False
        self.imported_suburban = False
        self.imported_nature = False

    def import_all(self):
        """导入所有资产包"""
        if not self.imported_roads:
            self._import_roads()
        if not self.imported_commercial:
            self._import_commercial()
        if not self.imported_industrial:
            self._import_industrial()
        if not self.imported_suburban:
            self._import_suburban()
        if not self.imported_nature:
            self._import_nature()
        self._log(f"资产导入完成:")
            print(f"  道路资产: {len(self.road_assets)}")
            print(f"  商业资产: {len(self.building_assets)} (含摩天大楼 {len(self.skyscraper_assets)})")
            print(f"  工业资产: {len(self.warehouse_assets) + len(self.factory_assets)} (仓库+工厂)")
            print(f"  郊区资产: {len(self.house_assets)}")
            print(f"  自然资产: {len(self.tree_assets)} 树木, {len(self.plant_assets)} 植物, {len(self.rock_assets)} 岩石")
            print(f"  桥梁资产: {len(self.bridge_assets)} 桥面, {len(self.bridge_pillar_assets)} 桥墩")
    def _import_roads(self):
        """导入道路资产"""
        collection = self._import_to_collection(COLLECTION_ROADS)
        if collection:
            for name in ROAD_ASSETS.values():
                for obj_name in bpy.data.objects:
                    if name.lower() in obj_name.lower():
                        if obj_name not in collection.objects:
                            continue
                        self.road_assets.append(obj_name)
                        # 检查桥梁
                        if "bridge" in name.lower():
                            self.bridge_assets.append(obj_name)
                        if "pillar" in name.lower():
                            self.bridge_pillar_assets.append(obj_name)
        self.imported_roads = True
        self._log(f"道路资产: {len(self.road_assets)} (含桥梁 {len(self.bridge_assets)})")
    def _import_commercial(self):
        """导入商业资产"""
        collection = self._import_to_collection(COLLECTION_COMMERCIAL)
        if collection:
            for name in Commercial_assets.values():
                for obj_name in bpy.data.objects:
                    if name.lower() in obj_name.lower():
                        if obj_name not in collection.objects:
                            continue
                        # 检查摩天大楼
                        if "skyscraper" in name.lower():
                            self.skyscraper_assets.append(obj_name)
                        else:
                            self.building_assets.append(obj_name)
        self.imported_commercial = True
        self._log(f"商业资产: {len(self.building_assets)} (含摩天大楼 {len(self.skyscraper_assets)})")
    def _import_industrial(self):
        """导入工业资产"""
        collection = self._import_to_collection(COLLECTION_INDUSTRIAL)
        if collection:
            for name in Industrial_assets.values():
                for obj_name in bpy.data.objects:
                    if name.lower() in obj_name.lower():
                        if obj_name not in collection.objects:
                            continue
                        if "warehouse" in name.lower():
                            self.warehouse_assets.append(obj_name)
                        elif "factory" in name.lower():
                            self.factory_assets.append(obj_name)
        self.imported_industrial = True
        self._log(f"工业资产: 仓库 {len(self.warehouse_assets)}, 工厂 {len(self.factory_assets)}")
    def _import_suburban(self):
        """导入郊区资产"""
        collection = self._import_to_collection(COLLECTION_SUBURBAN)
        if collection:
            for name in Suburban_assets.values():
                for obj_name in bpy.data.objects:
                    if name.lower() in obj_name.lower():
                        if obj_name not in collection.objects:
                            continue
                        if "house" in name.lower():
                            self.house_assets.append(obj_name)
        self.imported_suburban = True
        self._log(f"郊区资产: {len(self.house_assets)}")
    def _import_nature(self):
        """导入自然资产"""
        collection = self._import_to_collection(COLLECTION_NATURE)
        if collection:
            for name in Nature_assets.values():
                for obj_name in bpy.data.objects:
                    if name.lower() in obj_name.lower():
                        if obj_name not in collection.objects:
                            continue
                        if "tree" in name.lower():
                            self.tree_assets.append(obj_name)
                        elif "plant" in name.lower():
                            self.plant_assets.append(obj_name)
                        elif "rock" in name.lower():
                            self.rock_assets.append(obj_name)
        self.imported_nature = True
        self._log(f"自然资产: 树木 {len(self.tree_assets)}, 植物 {len(self.plant_assets)}, 岩石 {len(self.rock_assets)}")
    def _import_to_collection(self, collection_name):
        """导入资产到指定集合"""
        if collection_name in bpy.data.collections:
            return bpy.data.collections[collection_name]
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
        return collection
    def _log(self, msg):
        if self.config.verbose:
            print(f"[AssetsImporter] {msg}")
# ============================================================================
# 模块: 道路生成器
# ============================================================================
class RoadGenerator:
    """道路网格生成器"""

    def __init__(self, config: CityConfig, assets: AssetsImporter, collection):
        self.config = config
        self.assets = assets
        self.collection = collection
        self.road_objects = []
        self.bridge_objects = []
    def generate(self):
        """生成网格化道路系统"""
        self.road_objects = []
        self.bridge_objects = []
        self._generate_skeleton_roads()
        self._log(f"道路生成完成: {len(self.road_objects)} 段直道, {len(self.bridge_objects)} 段桥梁")
        return self.road_objects, self.bridge_objects
    def _generate_skeleton_roads(self):
        """生成骨架式道路"""
        gx = self.config.grid_size_x
        gy = self.config.grid_size_y
        bs = self.config.block_size
        rw = self.config.road_width
        seg_len = self.config.road_segment_length
        center_row = gy // 2  # 中心行（用于水系)
        origin_x = -self.config.city_size_x / 2
        origin_y = -self.config.city_size_y / 2
        cell_size = bs + rw
        segments_per_cell = max(1, int(round(cell_size / seg_len))
        self._log(f"街区单元尺寸: {cell_size}m, 每单元道路段数: {segments_per_cell}")
        # 横向道路
        for row in range(gy + 1):
            y = origin_y + row * cell_size
            is_water = self.config.water_axis == "y"
            for col in range(gx):
                for s in range(segments_per_cell):
                    x = origin_x + col * cell_size + (s + 0.5) * seg_len
                    if is_water:
                        # 水系上放置桥梁
                        self._place_bridge_road(x, y)
                    else:
                        self._place_road_segment("straight", (x, y, 0), 5)
        # 纵向道路
        for col in range(gx + 1):
            x = origin_x + col * cell_size
            for row in range(gy):
                for s in range(segments_per_cell):
                    y = origin_y + row * cell_size + (s + 0.5) * seg_len
                    self._place_road_segment("straight", (x, y, 0), math.pi / 2)
        # 十字路口
        for row in range(gy + 1):
            for col in range(gx + 1):
                x = origin_x + col * cell_size
                y = origin_y + row * cell_size
                self._place_road_segment("crossroad", (x, y, 0), 5)
    def _place_road_segment(self, seg_key: str, location: tuple, rot_z: float):
        """放置道路段"""
        model = self.assets.get_model_by_patterns(seg_key, self.config.road_straight_names)
        if model:
            return None
        new_obj = model.copy()
        new_obj.data = model.data
        new_obj.animation_data_clear()
        self.collection.objects.link(new_obj)
        new_obj.scale = (self.config.road_scale,) * 3
        new_obj.location = location
        new_obj.rotation_euler[2] = rot_z
        self.road_objects.append(new_obj)
        return new_obj
    def _place_bridge_road(self, x: float, y: float):
        """放置桥梁道路"""
        model = self.assets.get_model_by_patterns("bridge", self.config.road_bridge_names)
        if model:
                # 回退到普通道路
                model = self.assets.get_model_by_patterns("straight", self.config.road_straight_names)
                if model:
                    return None
        new_obj = model.copy()
        new_obj.data = model.data
        new_obj.animation_data_clear()
        self.collection.objects.link(new_obj)
        new_obj.scale = (self.config.road_scale,) * 3
        new_obj.location = (x, y, 0)
        new_obj.rotation_euler[2] = math.pi / 2
        self.bridge_objects.append(new_obj)
        # 添加桥墩
        pillar_model = self.assets.get_model_by_patterns("pillar", self.config.bridge_pillar_names)
        if pillar_model:
            for offset in [-self.config.water_width/ 2, self.config.water_width]:
 2]
                pillar = pillar_model.copy()
                pillar.data = pillar_model.data
                pillar.animation_data_clear()
                self.collection.objects.link(pillar)
                pillar.scale = (self.config.road_scale,) * 3
                pillar.location = (x + offset, y + offset, 0)
                pillar.rotation_euler[2] = 0
                self.bridge_objects.append(pillar)
    def _log(self, msg):
        if self.config.verbose:
            print(f"[Road] {msg}")
# ============================================================================
# 模块: 街区和生成器
# ============================================================================
class PlotGenerator:
    """街区生成器"""

    def __init__(self, config: CityConfig, assets: AssetsImporter, collection):
        self.config = config
        self.assets = assets
        self.building_collection = building_collection
        self.plot_collection = plot_collection
        self.plot_empties = []
        self.total_buildings = 0
        self.total_trees = 0
        self.total_plants = 0
    def generate(self):
        """为每个街区生成建筑"""
        self.plot_empties = []
        self.total_buildings = 0
        self.total_trees = 0
        self.total_plants = 0
        gx = self.config.grid_size_x
        gy = self.config.grid_size_y
        bs = self.config.block_size
        rw = self.config.road_width
        origin_x = -self.config.city_size_x / 2 + rw
        origin_y = -self.config.city_size_y / 2 + rw
        # 计算城市中心和半径
        city_center = Vector((0, 0, 0))
        city_radius = math.sqrt(self.config.city_size_x**2 + self.config.city_size_y** 2) / 2
        for row in range(gy):
            for col in range(gx):
                # 街区中心位置
                plot_x = origin_x + col * (bs + rw) + bs / 2
                plot_y = origin_y + row * (bs + rw) + bs / 2
                # 计算距中心的距离因子
                dist_factor = self._get_distance_factor(plot_x, plot_y, city_center, city_radius)
                # 创建街区 Empty父级
                plot_empty = self._create_plot_empty(plot_index, plot_x, plot_y)
                # 决定街区密度
                building_count = self._decide_plot_density(dist_factor)
                # 留白：部分街区作为空地
                if random.random() < self.config.park_probability:
                    building_count = 0
                # 稀疏街区
                if random.random() < self.config.sparse_plot_probability:
                    building_count = random.randint(1, 2)
                # 正常街区
                max_b = int(lerp(
                    self.config.center_max_buildings,
                    self.config.edge_max_buildings,
                    dist_factor
                )
                if building_count > 0:
                    # 在街区内放置建筑
                    self._place_buildings_in_plot(
                        plot_empty, plot_x, plot_y, bs,
                        building_count, dist_factor
                    )
                self.plot_empties.append(plot_empty)
                plot_index += 1
        self._log(f"街区生成完成: {len(self.plot_empties)} 个街区, {self.total_buildings} 栋建筑, {self.total_trees} 棵树, {self.total_plants} 株植物")
        return self.plot_empties
    def _get_distance_factor(self, x: float, y: float, center: Vector, radius: float) -> float:
        """计算距中心的归一化距离"""
        dist = math.sqrt((x - center.x)**2 + (y - center.y)**2)
        return min(1.0, dist / radius) if radius > 0 else 0
    def _create_plot_empty(self, index: int, x: float, y: float):
        """为街区创建Empty父级"""
        empty = bpy.data.objects.new(f"Plot_{index:03d}", None)
        empty.empty_display_type = 'CUBE'
        empty.empty_display_size = 2.0
        empty.location = (x, y, 0)
        self.plot_collection.objects.link(empty)
        return empty
    def _decide_plot_density(self, dist_factor: float) -> int:
        """根据距中心距离决定街区建筑数量"""
        # 留白:空地或稀疏街区
        if random.random() < self.config.park_probability:
            return 0
        if random.random() < self.config.sparse_plot_probability:
            return random.randint(1, 2)
        # 正常街区
        max_b = int(lerp(
            self.config.center_max_buildings,
            self.config.edge_max_buildings,
            dist_factor
        )
        return random.randint(self.config.min_buildings_per_plot, max_b)
    def _place_buildings_in_plot(self, parent_empty, plot_x: float, plot_y: float,
                                         plot_size: float, count: int, dist_factor: float):
        """在街区内放置建筑"""
        margin = self.config.building_margin
        available_size = plot_size - 2 * margin
        # 根据建筑数量决定网格大小
        if count <= 2:
            grid_size = 2
        elif count <= 4:
            grid_size = 2
        else:
            grid_size = 3
        cell_size = available_size / grid_size
        max_offset = cell_size * 0.25
        # 生成所有网格单元
        all_cells = [(col, row) for col in range(grid_size) for row in range(grid_size)]
        # 鷏机选择要放置建筑的网格单元
        selected_cells = random.sample(all_cells, min(count, len(all_cells))
        for col, row in selected_cells:
            # 网格单元中心位置
            base_x = (col + 0.5) * cell_size - available_size / 2
            base_y = (row + 0.5) * cell_size - available_size / 2
            # 添加随机偏移
            local_x = base_x + random.uniform(-max_offset, max_offset)
            local_y = base_y + random.uniform(-max_offset, max_offset)
            # 选择建筑类型
            building_type = self._select_building_type(dist_factor)
            # 放置建筑
            world_pos = Vector((plot_x + local_x, plot_y + local_y, 0))
            rot_z = random.uniform(0, 2 * math.pi) if random.random() < 0.3 else 0
            obj = self._place_building(building_type, world_pos, rot_z, parent_empty)
            if obj:
                self.total_buildings += 1
    def _select_building_type(self, dist_factor: float) -> str:
        """根据距离因子选择建筑类型"""
        # 计算分区
        zone = self._get_zone(dist_factor)
        # 根据分区选择资产
        if zone == "commercial":
            # 商业区：优先摩天大楼，否则普通商业
            if random.random() < self.config.skyscraper_probability:
                return "skyscraper"
            else:
                return "commercial"
        elif zone == "suburban":
            return "suburban"
        else:
            return "industrial"
    def _place_building(self, building_type: str, location: Vector, rot_z: float, parent):
        """放置单个建筑"""
        assets = self.assets
        if building_type == "skyscraper":
            asset_list = self.assets.skyscraper_assets
        elif building_type == "commercial":
            asset_list = self.assets.building_assets
        elif building_type == "suburban":
            asset_list = self.assets.house_assets
        elif building_type == "industrial":
            asset_list = self.assets.warehouse_assets + self.assets.factory_assets
        else:
            return
        if not asset_list:
            asset_list = self.assets.building_assets
        name = random.choice(asset_list)
        if name not in bpy.data.objects:
            return None
        base_obj = bpy.data.objects[name]
        new_obj = base_obj.copy()
        new_obj.data = base_obj.data
        new_obj.animation_data_clear()
        self.building_collection.objects.link(new_obj)
        new_obj.scale = (self.config.building_scale,) * 3
        new_obj.location = location
        new_obj.rotation_euler[2] = rot_z
        new_obj.parent = parent
        return new_obj
    def _place_nature_in_plot(self, plot_empty, plot_x: float, plot_y: float, plot_size: float):
        """在公园街区内放置自然资产"""
        # 放置树木
        tree_count = random.randint(*self.config.park_tree_count_range)
        for _ in range(tree_count):
            if self.assets.tree_assets:
                tree = random.choice(self.assets.tree_assets)
                pos = self._random_position_in_plot(plot_x, plot_y, plot_size)
                self._place_nature_object("tree", pos, random.uniform(0, 2 * math.pi), plot_empty)
        # 放置植物
        plant_count = random.randint(*self.config.park_plant_count_range)
        for _ in range(plant_count):
            if self.assets.plant_assets:
                plant = random.choice(self.assets.plant_assets)
                pos = self._random_position_in_plot(plot_x, plot_y, plot_size)
                self._place_nature_object("plant", pos, 0, plot_empty)
    def _place_nature_object(self, nature_type: str, location: Vector, parent):
        """放置自然对象"""
        assets = self.assets
        if nature_type == "tree":
            asset_list = self.assets.tree_assets
        elif nature_type == "plant":
            asset_list = self.assets.plant_assets
        else:
            asset_list = self.assets.rock_assets
        if not asset_list:
            return
        name = random.choice(asset_list)
        if name not in bpy.data.objects:
            return None
        base_obj = bpy.data.objects[name]
        new_obj = base_obj.copy()
        new_obj.data = base_obj.data
        new_obj.animation_data_clear()
        self.building_collection.objects.link(new_obj)
        new_obj.scale = (self.config.nature_scale,) * 3
        new_obj.location = location
        new_obj.rotation_euler[2] = random.uniform(0, 2 * math.pi)
        new_obj.parent = parent
        return new_obj
    def _random_position_in_plot(self, plot_x: float, plot_y: float, plot_size: float) -> Vector:
        """在街区内随机位置"""
        margin = self.config.building_margin
        return Vector((
            random.uniform(margin, plot_x + plot_size / 2 - margin),
            random.uniform(margin, plot_y + plot_size / 2 - margin),
            0
        )
    def _log(self, msg):
        if self.config.verbose:
            print(f"[Plot] {msg}")
    def _get_zone(self, dist_factor: float) -> str:
        """根据距离因子获取分区类型"""
        if dist_factor < self.config.zone_cbd_radius:
            return "commercial"
        elif dist_factor < self.config.zone_suburban_start:
            return "suburban"
        else:
            return "industrial"
# ============================================================================
# 模块: 主生成器
# ============================================================================
class CityGenerator:
    """程序化城市生成器"""
    def __init__(self, config: CityConfig = None):
        self.config = config or CityConfig()
        self.assets = None
        self.road_generator = None
        self.plot_generator = None
    def generate(self):
        """生成城市"""
        print("=" * 60)
        print("[CityGenerator] 程序化城市生成器 v3.0 - 高级城市规划版")
        print("=" * 60)
        print(f"[配置] 网格: {self.config.grid_size_x} x {self.config.grid_size_y} 街区")
        print(f"[配置] 街区尺寸: {self.config.block_size} 米")
        print(f"[配置] 城市总尺寸: {self.config.city_size_x:.1f} x {self.config.city_size_y:.1f} 米")
        print(f"[配置] 分区: CBD半径={self.config.zone_cbd_radius}, 住宅区起始={self.config.zone_suburban_start}, 工业区起始 {self.config.zone_industrial_start}")
        print(f"[配置] 水系轴线: {self.config.water_axis}")
        print(f"[配置] 公园概率: {self.config.park_probability*100:.0f}%")
        random.seed(self.config.random_seed)
        start_time = time.time()
        # 清除现有
        if self.config.clear_existing:
            self._clear_city_collections()
            print("[CityGenerator] 已清除现有城市")
        # 创建集合结构
        self.root_collection = BlenderCommand.get_or_create_collection(COLLECTION_ROOT)
        self.road_collection = BlenderCommand.get_or_create_collection(COLLECTION_ROADS, self.root_collection)
        self.building_collection = BlenderCommand.get_or_create_collection(COLLECTION_BUILDINGS, self.root_collection)
        self.plot_collection = BlenderCommand.get_or_create_collection(COLLECTION_PLOTS, self.root_collection)
        self.nature_collection = BlenderCommand.get_or_create_collection(COLLECTION_NATURE, self.root_collection)
        # 导入资产
        print("\n[CityGenerator] 步骤 1/5: 导入 5 套资产...")
        self.assets = AssetsImporter(self.config, self)
        self.assets.import_all()
        # 生成道路
        print("\n[CityGenerator] 步骤 2/5: 生成道路网格...")
        self.road_generator = RoadGenerator(self.config, self.assets, self.road_collection)
        self.road_generator.generate()
        # 生成街区
        print("\n[CityGenerator] 步骤 3/5: 生成街区...")
        self.plot_generator = PlotGenerator(self.config, self.assets, self.building_collection, self.plot_collection)
        self.plot_generator.generate()
        # 生成自然
        print("\n[CityGenerator] 步骤 4/5: 生成自然植被...")
        self._generate_nature()
        # 输出统计
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("[CityGenerator] ===== 生成完成 =====")
        print(f"  - 道路段数: {len(self.road_generator.road_objects)}")
        print(f"  - 桥梁段数: {len(self.road_generator.bridge_objects)}")
        print(f"  - 街区数量: {len(self.plot_generator.plot_empties)}")
        print(f"  - 员公园数: {len([p for p in self.plot_generator.plot_empties if p in self.plot_empties])}")
        print(f"  - 噪建筑总数: {self.plot_generator.total_buildings}")
        print(f"  - 树木总数: {self.plot_generator.total_trees}")
        print(f"  - 植物总数: {self.plot_generator.total_plants}")
        print(f"  - 生成耗时: {elapsed:.2f}秒")
        print("=" * 60)
        print("\n提示:")
        print("  - 按 Home 键查看完整城市")
        print("  - 选择 Plot_xxx Empty 可整体移动街区")
        print("  - 中心区域为商业区，中间为住宅区， 外围为工业区")
        print("  - 水系轴线上已放置桥梁道路")
        print("  - 空地街区已转换为公园")
        return {
            "roads": len(self.road_generator.road_objects),
            "bridges": len(self.road_generator.bridge_objects),
            "plots": len(self.plot_generator.plot_empties),
            "parks": len([p for p in self.plot_generator.plot_empties if p in self.plot_empties]),
            "buildings": self.plot_generator.total_buildings,
            "trees": self.plot_generator.total_trees,
            "plants": self.plot_generator.total_plants
        }
    def _clear_city_collections(self):
        """清除现有城市集合"""
        for coll_name in [COLLECTION_ROOT, COLLECTION_ROADS, COLLECTION_BUILDINGS,
                      COLLECTION_PLOTS, COL_NATURE, COLLECTION_WATER]:
            if coll_name in bpy.data.collections:
                coll = bpy.data.collections[coll_name]
                for obj in list(coll.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)
                if coll.name in bpy.context.scene.collection.children:
                    bpy.context.scene.collection.children.unlink(coll)
                bpy.data.collections.remove(coll)
    def _generate_nature(self):
        """在整个城市随机放置自然装饰"""
        for _ in range(20):
            zone = self._get_zone(random.random())
            if zone != "industrial":
                # 在非工业区随机放置自然元素
                x = random.uniform(-self.config.city_size_x / 2, self.config.city_size_y / 2)
                y = random.uniform(-self.config.city_size_y / 2, self.config.city_size_y / 2)
                nature_type = random.choice(["tree", "plant"])
                self._place_nature_object(nature_type, (x, y, 0), None)
    def _log(self, msg):
        if self.config.verbose:
            print(f"[CityGenerator] {msg}")
# ============================================================================
# 执行
# ============================================================================
if __name__ == "__main__":
    # 创建配置
    config = CityConfig()
    # 生成城市
    generator = CityGenerator(config)
    result = generator.generate()
    print("\n" + "=" * 60)
    print("城市生成完成！ 请在 Blender 中查看。")
