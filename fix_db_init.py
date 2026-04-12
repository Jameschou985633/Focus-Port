# -*- coding: utf-8 -*-

# Read the file
with open('main.py', 'rb') as f:
    content = f.read()

# The corrupted start marker (as found in file)
start_marker = b'# \xe6\x8f\x9d\xe5\xa7\x8b\xe5\x8c\x96\xe8\x87\xaa\xe4\xb9\xa0\xe5\xae\xa4\xe5\x95\x86\xe5\x93\x81'
# End marker
end_marker = b'# \xe8\xbf\x81\xe7\xa7\xbb'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx + len(start_marker))

print(f'Found section from {start_idx} to {end_idx}')

# The new corrected section - use double quotes to avoid escaping issues
new_section = '''    # 初始化自习室商品
    c.execute("SELECT COUNT(*) FROM StudyRoom_Items")
    if c.fetchone()[0] == 0:
        # 装饰物 (name, type, icon, model_path, price, rarity, description, effect, duration)
        decorations = [
            ("实木书桌", "decoration", "🪑", "/models/desk_wooden.glb", 100, "common", "简约实木书桌，适合认真学习", None, None),
            ("现代书桌", "decoration", "🖥️", "/models/desk_modern.glb", 200, "rare", "现代风格书桌，科技感十足", None, None),
            ("台灯", "decoration", "💡", "/models/lamp_desk.glb", 80, "common", "护眼台灯，保护视力", None, None),
            ("小书架", "decoration", "📚", "/models/bookshelf_small.glb", 150, "common", "木质小书架，放几本参考书", None, None),
            ("大书架", "decoration", "📖", "/models/bookshelf_large.glb", 300, "rare", "大型书架，收藏更多书籍", None, None),
            ("小盆栽", "decoration", "🌱", "/models/plant_small.glb", 50, "common", "绿植盆栽，净化空气", None, None),
            ("大盆栽", "decoration", "🌳", "/models/plant_large.glb", 120, "common", "大型绿植，装饰空间", None, None),
            ("舒适椅子", "decoration", "🪑", "/models/chair_comfort.glb", 180, "common", "舒适座椅，休息必备", None, None),
            ("温馨地毯", "decoration", "🏠", "/models/rug_cozy.glb", 100, "common", "柔软地毯，温馨氛围", None, None),
            ("小喷泉", "decoration", "⛲", "/models/fountain_water.glb", 500, "epic", "室内喷泉，高级装饰", None, None),
            ("专注雕像", "decoration", "🗿", "/models/statue_focus.glb", 800, "epic", "专注雕像，激励学习", None, None),
            ("鱼缸", "decoration", "🐠", "/models/aquarium.glb", 600, "rare", "生态鱼缸，放松心情", None, None),
            ("壁炉", "decoration", "🔥", "/models/fireplace.glb", 1000, "legendary", "温暖壁炉，冬日必备", None, None),
            ("钢琴", "decoration", "🎹", "/models/piano.glb", 1500, "legendary", "三角钢琴，艺术氛围", None, None),
        ]
        for item in decorations:
            c.execute("INSERT INTO StudyRoom_Items (name, type, icon, model_path, price, rarity, description, effect, duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", item)

        # 功能道具
        boosts = [
            ("专注药水", "boost", "🧪", None, 50, "common", "30分钟专注加成", "focus_boost", 30),
            ("能量饮料", "boost", "⚡", None, 100, "rare", "双倍经验获取", "exp_double", 60),
            ("速读卡", "boost", "📖", None, 150, "epic", "阅读速度提升50%", "reading_speed", 20),
            ("记忆面包", "boost", "🧠", None, 200, "epic", "记忆增强效果", "memory_enhance", 30),
            ("幸运草", "boost", "🍀", None, 300, "legendary", "双倍掉落率", "drop_rate_double", 60),
            ("时光沙漏", "boost", "⏳", None, 500, "legendary", "专注时间延长10分钟", "time_extend", 10),
        ]
        for item in boosts:
            c.execute("INSERT INTO StudyRoom_Items (name, type, icon, model_path, price, rarity, description, effect, duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", item)

'''

# Reconstruct file
new_content = content[:start_idx] + new_section.encode('utf-8') + content[end_idx:]

# Write back
with open('main.py', 'wb') as f:
    f.write(new_content)

print("Fixed main.py successfully!")
