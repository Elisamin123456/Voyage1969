# 1. 核心模块导入
import pygame
import os
import json
import time
import math


# 2. 游戏初始化配置
# 2.1 Pygame初始化
pygame.init()

# 2.2 窗口尺寸配置
GRID_SIZE = 64                   # 网格基准尺寸
MAP_WIDTH, MAP_HEIGHT = 12, 9    # 主地图尺寸
SKILLBAR_HEIGHT = 2              # 技能栏占格数
INFOBAR_WIDTH = 400              # 信息栏宽度
WINDOW_WIDTH = MAP_WIDTH * GRID_SIZE + INFOBAR_WIDTH
WINDOW_HEIGHT = (MAP_HEIGHT + SKILLBAR_HEIGHT) * GRID_SIZE
ENEMY_ACTION_EVENT = pygame.USEREVENT + 1


# 2.3 颜色定义
COLORS = {
    "WHITE": (255, 255, 255),
    "BLACK": (0, 0, 0),
    "GRAY": (192, 192, 192),
    "RED": (255, 0, 0)
}

# 2.4 游戏状态全局变量
# 2.4.1 角色配置
P1_character = "reimu"
P2_character = "marisa"

# 2.4.2 玩家属性
PLAYER_STATS = {
    "P1": {"hp": 20, "attack": 1, "mana": 20, "gold": 100},   # 藍方 P1：初始 0 靈力，100 金幣
    "P2": {"hp": 20, "attack": 1, "mana": 1, "gold": 100}    # 紅方 P2：初始 1 靈力，100 金幣
}

# 2.4.3 交互状态
game_state = {
    "selected_skill": None,      # 当前选中技能编号
    "selected_character": None,  # 当前选中角色
    "hovered_skill": None,       # 悬停技能编号
    "current_mana_input": 0,     # 灵力输入框数值
    "bullets": [],               # 活跃子弹列表
    "bullet_queue": [],          # 子弹发射队列
    "game_logs": ["遊戲開始"],    # 游戏公告日志
    "last_shot_time": 0          # 最后发射时间
}
game_state["current_turn"] = {"turn_number": 1, "active_player": "P1"}
game_state["enemy_direction"] = 1  # 敵人初始向下移動
# 统一管理玩家数据，spawn point 为 "P1" 和 "P2"
game_state["players"] = {
    "P1": {"character": "reimu", "hp": 20, "attack": 1, "mana": 20, "gold": 100},
    "P2": {"character": "marisa", "hp": 20, "attack": 1, "mana": 20, "gold": 100}
}

# 2.4.4 移动半径
MOVEMENT_RADIUS = 1  # 允许的移动半径，1 表示只能移动到相邻的八个格子，后续可根据需要调整

P1_vision_radius = 1 # 全局變數，初始 P1 視野半徑（可根據技能擴大）


# 3. 资源加载系统
# 3.1 字体加载
try:
    FONT = pygame.font.Font("font/华康金文体繁W3.ttf", 24)
except:
    FONT = pygame.font.SysFont("simsunnsimsun", 24)

# 3.2 图像加载函数
def load_scaled_image(path, size):
    """加载并缩放图像资源"""
    return pygame.transform.scale(pygame.image.load(path), size)

# 3.3 地图数据加载
with open("map/aokigahara.json", "r", encoding="utf-8") as f:
    map_data = json.load(f)

# 3.4 地形资源加载
ground_img = load_scaled_image(os.path.join("map", map_data["resources"]["ground_img"]), (GRID_SIZE, GRID_SIZE))
grass_img = load_scaled_image(os.path.join("map", map_data["resources"]["grass_img"]), (GRID_SIZE, GRID_SIZE))
wall_imgs = {
    i: load_scaled_image(os.path.join("map", map_data["resources"]["wall_imgs"][str(i)]), (GRID_SIZE, GRID_SIZE))
    for i in range(1, 6)
}
wall_default = load_scaled_image(os.path.join("map", map_data["resources"]["wall_default"]), (GRID_SIZE, GRID_SIZE))
start_img = load_scaled_image(os.path.join("map", map_data["resources"]["start_img"]), (GRID_SIZE, GRID_SIZE))

# 99999999回合体系

def switch_turn(action_type, extra_info=""):
    """
    统一管理回合切换：
      - 将本回合操作记录到 game_state["turn_history"]
      - 根据当前 active_player 生成公告（从 game_state["players"] 中取角色名）
      - 切换 active_player，并在从敌方切换回玩家时更新（例如 vision_boost 衰减、撤销侦察效果等）
    """
    if "turn_history" not in game_state:
        game_state["turn_history"] = []
    active = game_state["current_turn"]["active_player"]
    history_entry = {
        "turn": game_state["current_turn"]["turn_number"],
        "active_player": active,
        "action": action_type,
        "extra_info": extra_info,
        "timestamp": time.time()
    }
    game_state["turn_history"].append(history_entry)

    # 根据 action_type 生成公告
    current_player = game_state["players"][active]["character"]
    if action_type == "move":
        msg = f"{current_player} 進行了移動"
    elif action_type == "build":
        msg = f"{current_player} 進行了建造"
    elif action_type == "needle":
        msg = f"霰術：「Persuasion Needle」\n{current_player} 發射了封魔針"
    elif action_type == "amulet":
        msg = f"霊耗：「Homing Amulet」\n{current_player} 發射了符札"
    elif action_type == "teleport":
        msg = f"秘奧：「G Free」\n{current_player} 閃現到了\n半徑為[{extra_info}]內的一格"
    elif action_type == "normal":
        msg = f"{current_player} 發動了普通攻擊"
    elif action_type == "vision":
        msg = f"策法：「陰陽寶玉」\n{current_player} 獲得了\n半徑為[{extra_info}]的視野"
    elif action_type == "scout":
        msg = f"{current_player} 發動了偵察，\n暴露敵方位置1回合"
    else:
        msg = f"{current_player} 進行了行動"
    add_announcement(msg)
    finalize_turn_announcements()

    if active == "P1":
        # 從 P1 切換至 P2
        game_state["current_turn"]["active_player"] = "P2"
        pygame.time.set_timer(ENEMY_ACTION_EVENT, 1000, True)
    else:
        # 從 P2 切換回 P1時（或一般敵方回合結束時）更新 vision_boost、撤銷偵察等，然後增加回合數
        if "vision_boost" in game_state:
            game_state["vision_boost"]["remaining"] -= 1
            if game_state["vision_boost"]["remaining"] <= 0:
                del game_state["vision_boost"]
        if "recon_position" in game_state:
            del game_state["recon_position"]
        game_state["current_turn"]["active_player"] = "P1"
        game_state["current_turn"]["turn_number"] += 1



# 公告系統相關函數
# ================= 回合與公告系統 =================

def add_announcement(msg):
    """新增公告訊息，暫存公告只保留當前回合的訊息"""
    game_state["announcements"] = [msg]

def finalize_turn_announcements():
    """結算公告：將暫存公告複製到 game_logs，並清空暫存公告"""
    game_state["game_logs"] = game_state["announcements"][:]
    game_state["announcements"] = []

def finish_turn(action_type, extra_info=""):
    switch_turn(action_type, extra_info)





def auto_enemy_action():
    """
    測試用敵方行動：敵方進行簡單移動，生成公告後，通過 switch_turn() 完成回合切換。
    """
    enemy_pos = list(map_layout["start_positions"][1])
    direction = game_state.get("enemy_direction", 1)
    if enemy_pos[1] + direction < 0 or enemy_pos[1] + direction >= MAP_HEIGHT:
        direction = -direction
        game_state["enemy_direction"] = direction
    enemy_pos[1] += direction
    map_layout["start_positions"][1] = tuple(enemy_pos)
    
    enemy_msg = f"{P2_character} 進行了移動"
    add_announcement(enemy_msg)
    finalize_turn_announcements()
    
    # 結束敵方回合時，統一由 switch_turn 處理 vision_boost 衰減、切換 active_player、回合數更新
    switch_turn("enemy_move")




# 3.5 角色资源加载
def load_character_image(character, selected=False):
    """加载角色图像，支持选中状态"""
    state = "_selected" if selected else ""
    try:
        img = pygame.image.load(f"sample/character/{character}/{character}{state}.png")
    except FileNotFoundError:
        img = pygame.image.load(f"sample/character/{character}/{character}.png")
    return pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))

# 3.6 技能图标加载
def load_skill_icons(character):
    """加载指定角色的全套技能图标"""
    return {
        i: {
            state: load_scaled_image(
                f"sample/character/{character}/{character}_{i}{'_' + state if state != 'default' else ''}.png",
                (GRID_SIZE, GRID_SIZE)
            ) for state in ["default", "selecting", "selected"]
        }
        for i in range(1, 5)
    }


# 4. 游戏数据结构初始化
# 4.1 地图布局数据
map_layout = {
    "start_positions": [tuple(pos) for pos in map_data["spawn_points"].values()],
    "grass": [tuple(pos) for pos in map_data["terrain"]["grass"]["positions"]],
    "walls": [tuple(pos) for pos in map_data["terrain"]["walls"]["positions"]]
}

# 4.2 墙体生命值初始化
wall_health = {tuple(pos): map_data["terrain"]["walls"]["health"] for pos in map_layout["walls"]}
# 新增：记录墙体的总生命值（初始地图中所有墙体总生命值均为5）
wall_total = {tuple(pos): map_data["terrain"]["walls"]["health"] for pos in map_layout["walls"]}


# 4.3 技能信息配置
SKILL_INFO = {
    (2, 9): ["霰術「Persuasion Needle」", "消耗：n 靈力", "效果：向目標方向發射封魔針", "造成 n 點傷害", "彈道攻擊，會被牆體阻擋。"],
    (4, 9): ["靈耗「Homing Amulet」", "消耗：1 靈力", "效果：發射可穿透的符札", "對路徑上的所有單位造成 1 點傷害", "命中敵方機體返還 1 靈力。"],
    (6, 9): ["策法「陰陽寶玉」", "消耗：n 靈力", "效果：獲得以自機為中心", "半徑 n 格的視野、持續 n 回合。"],
    (8, 9): ["秘奧「G Free」", "消耗：n 靈力", "效果：瞬間移動至 n 格範圍內", "的任意位置。"],
    (9, 9): ["減少靈力"],
    (10, 9): ["靈力輸入框"],
    (11, 9): ["增加靈力"],
    (0, 10): ["建造", "消耗：n 靈力","效果：在n格半徑內", "建造生命值=n的牆體" ],
    (0, 9) :  ["偵察", "消耗：1 靈力","效果：顯示敵方目前所在座標", "當敵方在草叢時無效" ]
}

# 5. 核心游戏功能
# 5.1 信息面板绘制

def draw_info_panel(screen, mouse_pos):
    """繪製右側信息面板，根據滑鼠所在區域決定是否受迷霧影響"""
    # 5.1.1 面板基礎繪製
    info_rect = pygame.Rect(MAP_WIDTH * GRID_SIZE, 0, INFOBAR_WIDTH, WINDOW_HEIGHT)
    pygame.draw.rect(screen, COLORS["BLACK"], info_rect)
    
    # 在面板頂部顯示當前回合資訊（全局信息，不受迷霧影響）
    turn_info = FONT.render(f"回合: {game_state['current_turn']['turn_number']} {game_state['current_turn']['active_player']}", True, COLORS["WHITE"])
    screen.blit(turn_info, (MAP_WIDTH * GRID_SIZE + 20, 0))
    
    # 計算滑鼠所在的格子（根據像素座標）
    grid_x = mouse_pos[0] // GRID_SIZE
    grid_y = mouse_pos[1] // GRID_SIZE
    cell = (grid_x, grid_y)
    
    # 判定滑鼠是否在地圖區域內（地圖區域：x < MAP_WIDTH*GRID_SIZE 且 y < MAP_HEIGHT*GRID_SIZE）
    in_map_area = (mouse_pos[0] < MAP_WIDTH * GRID_SIZE and mouse_pos[1] < MAP_HEIGHT * GRID_SIZE)
    
    # 5.1.2 座標顯示：始終顯示具體坐標，如果在地圖內則顯示 "座標: A1"，否則正常顯示
    coord_text = FONT.render(f"座標: {chr(65 + grid_x)}{grid_y + 1}", True, COLORS["WHITE"])
    screen.blit(coord_text, (MAP_WIDTH * GRID_SIZE + 20, 20))
    
    # 5.1.3 懸停信息顯示（角色/技能/地形）
    hover_text = None
    # 這裡沿用原始判定邏輯
    if cell in map_layout["start_positions"]:
        player_idx = 0 if cell == map_layout["start_positions"][0] else 1
        char_name = "博麗靈夢" if (P1_character if player_idx == 0 else P2_character) == "reimu" else "霧雨魔理沙"
        hover_text = f"P{player_idx + 1}: {char_name}"
    elif cell in SKILL_INFO:
        hover_text = "\n".join(SKILL_INFO[cell])
    elif cell in map_layout["grass"]:
        hover_text = "草叢: 不可偵察"
    elif cell in map_layout["walls"]:
        current_hp = wall_health.get(cell, 0)
        total_hp = wall_total.get(cell, 0)
        hover_text = f"牆體生命值: {current_hp} / {total_hp}"
    
    # 在地圖區域內僅顯示可見格的懸停信息；非地圖區域則直接顯示（通常不會觸發此邏輯）
    if in_map_area:
        if is_cell_visible(cell, map_layout["start_positions"][0], P1_vision_radius) and hover_text:
            y_offset = 50
            for line in hover_text.split("\n"):
                rendered_line = FONT.render(line, True, COLORS["WHITE"])
                screen.blit(rendered_line, (MAP_WIDTH * GRID_SIZE + 20, y_offset))
                y_offset += 30
    else:
        if hover_text:
            y_offset = 50
            for line in hover_text.split("\n"):
                rendered_line = FONT.render(line, True, COLORS["WHITE"])
                screen.blit(rendered_line, (MAP_WIDTH * GRID_SIZE + 20, y_offset))
                y_offset += 30

    # 5.1.4 遊戲日誌顯示（全球信息，不受視野影響）
    pygame.draw.line(screen, COLORS["WHITE"], (MAP_WIDTH * GRID_SIZE, WINDOW_HEIGHT // 3),
                     (WINDOW_WIDTH, WINDOW_HEIGHT // 3), 3)
    y_offset = WINDOW_HEIGHT // 3 + 20
    for log in game_state["game_logs"][-5:]:
        screen.blit(FONT.render(log, True, COLORS["WHITE"]), (MAP_WIDTH * GRID_SIZE + 20, y_offset))
        y_offset += 30

    # 5.1.5 玩家狀態顯示（全球信息）
    pygame.draw.line(screen, COLORS["WHITE"], (MAP_WIDTH * GRID_SIZE, WINDOW_HEIGHT * 2 // 3),
                     (WINDOW_WIDTH, WINDOW_HEIGHT * 2 // 3), 3)
    stats = [
        f"生命值: {PLAYER_STATS['P1']['hp']}",
        f"攻擊力: {PLAYER_STATS['P1']['attack']}",
        f"靈力: {PLAYER_STATS['P1']['mana']}",
        f"金幣: {PLAYER_STATS['P1']['gold']}"
    ]
    y_offset = WINDOW_HEIGHT * 2 // 3 + 20
    for stat in stats:
        screen.blit(FONT.render(stat, True, COLORS["WHITE"]), (MAP_WIDTH * GRID_SIZE + 20, y_offset))
        y_offset += 30

    # 5.1.6 靈力輸入框繪製
    input_box = pygame.Rect(10 * GRID_SIZE, 9 * GRID_SIZE, GRID_SIZE, GRID_SIZE)
    pygame.draw.rect(screen, COLORS["WHITE"], input_box)
    pygame.draw.rect(screen, COLORS["GRAY"], input_box, 3)
    mana_text = FONT.render(str(game_state["current_mana_input"]), True, COLORS["BLACK"])
    screen.blit(mana_text, mana_text.get_rect(center=input_box.center))



def load_skillbar():
    path = os.path.join("map", "skillbar.png")
    return pygame.transform.scale(pygame.image.load(path), (MAP_WIDTH * GRID_SIZE, SKILLBAR_HEIGHT * GRID_SIZE))
skillbar_img = load_skillbar()

# 5.2 技能栏绘制
def draw_skill_bar(screen):
    """绘制底部技能栏"""
    screen.blit(skillbar_img, (0, MAP_HEIGHT * GRID_SIZE))
    skill_positions = [(2,9), (4,9), (6,9), (8,9)]
    for idx, (x, y) in enumerate(skill_positions, 1):
        state = "selected" if game_state["selected_skill"] == idx else \
                "selecting" if game_state["hovered_skill"] == idx else "default"
        icon = skills[P1_character][idx][state]
        screen.blit(icon, (x*GRID_SIZE, y*GRID_SIZE))

# 5.3 主地图绘制
def draw_game_map(screen):
    """绘制游戏主地图"""
    # 5.3.1 绘制基础地形
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            screen.blit(ground_img, (x*GRID_SIZE, y*GRID_SIZE))
    
    # 5.3.2 绘制特殊地形
    for x, y in map_layout["grass"]:
        screen.blit(grass_img, (x*GRID_SIZE, y*GRID_SIZE))
    for x, y in map_layout["walls"]:
        img = wall_imgs.get(wall_health.get((x,y), 5), wall_default)
        screen.blit(img, (x*GRID_SIZE, y*GRID_SIZE))
    
    # 5.3.3 绘制玩家角色
    if len(map_layout["start_positions"]) >= 2:
        for i, pos in enumerate(map_layout["start_positions"]):
            x, y = pos
            char = P1_character if i == 0 else P2_character
            selected = game_state["selected_character"] == f"P{i+1}"
            img = load_character_image(char, selected)
            screen.blit(img, (x*GRID_SIZE, y*GRID_SIZE))


# 5.114514 视野系统
def is_cell_visible(cell, center, radius):
    """
    判定某個格子是否在視野內。
    使用棋盤距離（Chebyshev distance）：若 max(|cell.x - center.x|, |cell.y - center.y|) <= radius，
    則該格被視為可見。
    
    參數:
      cell: (x, y) 格子座標
      center: (x, y) 中心座標（例如自機所在格）
      radius: 視野半徑（整數）
      
    回傳:
      True 如果可見，否則 False。
    """
    dx = abs(cell[0] - center[0])
    dy = abs(cell[1] - center[1])
    return max(dx, dy) <= radius

def draw_mist(screen):
    """
    对于不在视野内的每个格子绘制迷雾，
    若该格子为侦察暴露的位置，则不绘制迷雾。
    """
    mist_img = load_scaled_image("map/mist.png", (GRID_SIZE, GRID_SIZE))
    p1_center = map_layout["start_positions"][0]
    vision_radius = game_state["vision_boost"]["radius"] if "vision_boost" in game_state else P1_vision_radius
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            cell = (x, y)
            # 如果此格为侦察暴露位置，跳过绘制迷雾
            if "recon_position" in game_state and cell == game_state["recon_position"]:
                continue
            if not is_cell_visible(cell, p1_center, vision_radius):
                screen.blit(mist_img, (x * GRID_SIZE, y * GRID_SIZE))





# 5.4 子弹系统
def update_bullets():
    """更新子彈狀態。技能2的子彈具有穿透效果，每個實體僅受一次傷害；技能1及普通攻擊（"normal"）在遇到實體時造成傷害後消失。"""
    current_time = time.time()
    # 從子彈隊列發射子彈（發射間隔 0.1 秒）
    if game_state["bullet_queue"] and current_time - game_state["last_shot_time"] > 0.1:
        new_bullet = game_state["bullet_queue"].pop(0)
        if new_bullet.get("skill") == 2:
            new_bullet["hit_entities"] = set()  # 用集合儲存已命中的格子
        game_state["bullets"].append(new_bullet)
        game_state["last_shot_time"] = current_time

    # 更新每個子彈的位置並檢查碰撞
    for bullet in game_state["bullets"][:]:
        bullet["pos"] = (
            bullet["pos"][0] + bullet["direction"][0] * bullet["speed"],
            bullet["pos"][1] + bullet["direction"][1] * bullet["speed"]
        )
        grid_x = int(bullet["pos"][0]) // GRID_SIZE
        grid_y = int(bullet["pos"][1]) // GRID_SIZE

        # 超出地圖邊界則移除子彈
        if not (0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT):
            game_state["bullets"].remove(bullet)
            continue

        cell = (grid_x, grid_y)

        # 碰撞牆體檢測
        if cell in map_layout["walls"]:
            # 對於技能1及普通攻擊（"normal"），子彈撞牆後扣牆體生命並消失
            if bullet.get("skill") in [1, "normal"]:
                wall_health[cell] -= 1
                if wall_health[cell] <= 0:
                    map_layout["walls"].remove(cell)
                game_state["bullets"].remove(bullet)
                continue
            # 對於技能2，扣除牆體生命但不移除子彈（穿透效果）
            elif bullet.get("skill") == 2:
                if cell not in bullet["hit_entities"]:
                    wall_health[cell] -= 1
                    bullet["hit_entities"].add(cell)
                    if wall_health[cell] <= 0:
                        map_layout["walls"].remove(cell)
                # 不移除子彈

        # 碰撞敵方檢測（假設敵方位置為 map_layout["start_positions"][1]）
        if cell == map_layout["start_positions"][1]:
            if bullet.get("skill") in [1, "normal"]:
                PLAYER_STATS["P2"]["hp"] -= 1
                game_state["bullets"].remove(bullet)
                continue
            elif bullet.get("skill") == 2:
                if cell not in bullet["hit_entities"]:
                    PLAYER_STATS["P2"]["hp"] -= 1
                    PLAYER_STATS["P1"]["mana"] += 1  # 命中敵方返還 1 靈力
                    bullet["hit_entities"].add(cell)
                # 不移除子彈


    """更新子彈狀態，技能2的子彈具有穿透效果，但每個實體僅受一次傷害判定"""
    current_time = time.time()
    # 從子彈隊列發射子彈（發射間隔 0.1 秒）
    if game_state["bullet_queue"] and current_time - game_state["last_shot_time"] > 0.1:
        # 將新子彈加入前，若為技能2（穿透子彈），初始化 hit_entities 集合
        new_bullet = game_state["bullet_queue"].pop(0)
        if new_bullet.get("skill") == 2:
            new_bullet["hit_entities"] = set()  # 用集合儲存已命中的格子
        game_state["bullets"].append(new_bullet)
        game_state["last_shot_time"] = current_time

    # 依序更新現有子彈狀態
    for bullet in game_state["bullets"][:]:
        # 更新子彈位置
        bullet["pos"] = (
            bullet["pos"][0] + bullet["direction"][0] * bullet["speed"],
            bullet["pos"][1] + bullet["direction"][1] * bullet["speed"]
        )
        grid_x = int(bullet["pos"][0]) // GRID_SIZE
        grid_y = int(bullet["pos"][1]) // GRID_SIZE

        # 檢查是否超出地圖邊界，若超出則移除該子彈
        if not (0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT):
            game_state["bullets"].remove(bullet)
            continue

        cell = (grid_x, grid_y)

        # 碰撞牆體檢測
        if cell in map_layout["walls"]:
            # 若子彈為技能1，撞牆後直接扣牆體生命值並移除子彈
            if bullet.get("skill") == 1:
                wall_health[cell] -= 1
                if wall_health[cell] <= 0:
                    map_layout["walls"].remove(cell)
                game_state["bullets"].remove(bullet)
                continue
            # 若子彈為技能2，則檢查該牆體是否已受傷
            elif bullet.get("skill") == 2:
                if cell not in bullet["hit_entities"]:
                    wall_health[cell] -= 1
                    bullet["hit_entities"].add(cell)
                    if wall_health[cell] <= 0:
                        map_layout["walls"].remove(cell)
                # 技能2子彈穿透牆體，不移除子彈

        # 碰撞敵方檢測（假設敵方位置為 map_layout["start_positions"][1]）
        if cell == map_layout["start_positions"][1]:
            if bullet.get("skill") == 1:
                PLAYER_STATS["P2"]["hp"] -= 1
                game_state["bullets"].remove(bullet)
                continue
            elif bullet.get("skill") == 2:
                if cell not in bullet["hit_entities"]:
                    PLAYER_STATS["P2"]["hp"] -= 1
                    PLAYER_STATS["P1"]["mana"] += 1  # 命中敵方返還 1 靈力
                    bullet["hit_entities"].add(cell)
                # 技能2子彈命中敵方後繼續前進

def update_vision_boost():
    if "vision_boost" in game_state:
        game_state["vision_boost"]["remaining"] -= 1
        if game_state["vision_boost"]["remaining"] <= 0:
            del game_state["vision_boost"]



def draw_bullets(screen):
    """繪製所有活動的子彈，依據子彈的技能標記選擇對應圖示"""
    import math
    for bullet in game_state["bullets"]:
        # 判斷子彈屬於哪種攻擊
        if bullet.get("skill") == "normal":
            bullet_img = load_scaled_image("sample/skill/reimu/yinyangorb.png", (40, 40))
        elif P1_character == "reimu":
            if bullet.get("skill") == 1:
                bullet_img = load_scaled_image("sample/skill/reimu/reimuneedle.png", (40, 40))
            elif bullet.get("skill") == 2:
                bullet_img = load_scaled_image("sample/skill/reimu/reimuamulet.png", (40, 40))
            else:
                bullet_img = load_scaled_image("sample/skill/reimu/yinyangorb.png", (40, 40))
        else:
            bullet_img = load_scaled_image("sample/skill/reimu/default_bullet.png", (40, 40))
        # 計算旋轉角度（預設圖示正上方為 0 度）
        angle = -math.degrees(math.atan2(bullet["direction"][0], -bullet["direction"][1]))
        rotated_bullet = pygame.transform.rotate(bullet_img, angle)
        rect = rotated_bullet.get_rect(center=(int(bullet["pos"][0]), int(bullet["pos"][1])))
        screen.blit(rotated_bullet, rect)

def draw_mouse_indicator(screen):
    """
    繪製鼠標跟隨的黑色指示框：
      - 永遠在鼠標所在的格子上繪製一個黑色邊框。
      - 若左鍵按下，邊框厚度加粗（例如 3 像素），否則保持正常（1 像素）。
      - 此指示框獨立於其他指示框，不影響程序內其他指示器的顯示。
    """
    # 獲取當前鼠標位置
    mouse_pos = pygame.mouse.get_pos()
    # 計算鼠標所在的格子座標
    grid_x = mouse_pos[0] // GRID_SIZE
    grid_y = mouse_pos[1] // GRID_SIZE
    # 建立該格的矩形區域
    rect = pygame.Rect(grid_x * GRID_SIZE, grid_y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
    # 檢查是否左鍵按下
    left_pressed = pygame.mouse.get_pressed()[0]
    thickness = 3 if left_pressed else 1
    # 繪製黑色邊框
    pygame.draw.rect(screen, COLORS["BLACK"], rect, thickness)


def draw_teleport_indicator(screen):
    """
    繪製技能4（瞬間移動）指示器：
      - 以自機所在格為中心，允許移動範圍為 current_mana_input 格（Chebyshev 距離）。
      - 若滑鼠所在格在允許範圍內、位於地圖內且非牆體，則指示器為白色；否則為紅色。
    """
    if game_state.get("aiming", False) and game_state.get("selected_skill") == 4:
        mouse_pos = pygame.mouse.get_pos()
        target_cell = (mouse_pos[0] // GRID_SIZE, mouse_pos[1] // GRID_SIZE)
        start_cell = map_layout["start_positions"][0]
        dx = target_cell[0] - start_cell[0]
        dy = target_cell[1] - start_cell[1]
        allowed = game_state["current_mana_input"]
        valid = True
        if max(abs(dx), abs(dy)) > allowed or (dx == 0 and dy == 0):
            valid = False
        if target_cell[0] < 0 or target_cell[0] >= MAP_WIDTH or target_cell[1] < 0 or target_cell[1] >= MAP_HEIGHT:
            valid = False
        if target_cell in map_layout["walls"]:
            valid = False
        color = COLORS["WHITE"] if valid else COLORS["RED"]
        rect = pygame.Rect(target_cell[0] * GRID_SIZE, target_cell[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, color, rect, 3)

def draw_teleport_line(screen):
    """
    繪製技能4瞬間移動的瞄準線：
      - 從自機中心指向滑鼠當前所在格的中心。
      - 若目標格在允許移動範圍內（Chebyshev 距離 <= current_mana_input），線條顏色為白色；
        否則為紅色。
    """
    if game_state.get("aiming", False) and game_state.get("selected_skill") == 4:
        mouse_pos = pygame.mouse.get_pos()
        target_cell = (mouse_pos[0] // GRID_SIZE, mouse_pos[1] // GRID_SIZE)
        start_cell = map_layout["start_positions"][0]
        dx = target_cell[0] - start_cell[0]
        dy = target_cell[1] - start_cell[1]
        allowed = game_state["current_mana_input"]
        # 判斷目標格是否在允許範圍內：使用 Chebyshev 距離判斷
        color = COLORS["WHITE"] if max(abs(dx), abs(dy)) <= allowed else COLORS["RED"]
        start_center = (start_cell[0] * GRID_SIZE + GRID_SIZE // 2,
                        start_cell[1] * GRID_SIZE + GRID_SIZE // 2)
        target_center = (target_cell[0] * GRID_SIZE + GRID_SIZE // 2,
                         target_cell[1] * GRID_SIZE + GRID_SIZE // 2)
        pygame.draw.line(screen, color, start_center, target_center, 3)

def draw_build_indicator(screen):
    """
    繪製建造指示器：
      - 當處於建造模式時，以當前機體所在格為中心，
      - 根據滑鼠當前所在的整數格判定：若目標格在允許建造範圍內（Chebyshev 距離 <= game_state["current_mana_input"]
        且目標格不為機體所在格）、位於地圖內且未有牆體，則指示器為白色；否則為紅色。
    """
    if game_state.get("building", False):
        mouse_pos = pygame.mouse.get_pos()
        target_cell = (mouse_pos[0] // GRID_SIZE, mouse_pos[1] // GRID_SIZE)
        center_cell = map_layout["start_positions"][0]
        dx = target_cell[0] - center_cell[0]
        dy = target_cell[1] - center_cell[1]
        allowed = game_state.get("current_mana_input", 0)
        valid = True
        # 判定範圍：若超過 allowed 或目標格為中心則視為不合法
        if allowed <= 0 or max(abs(dx), abs(dy)) > allowed or (dx == 0 and dy == 0):
            valid = False
        # 判定是否在地圖內
        if target_cell[0] < 0 or target_cell[0] >= MAP_WIDTH or target_cell[1] < 0 or target_cell[1] >= MAP_HEIGHT:
            valid = False
        # 判定目標格是否已有牆體
        if target_cell in map_layout["walls"]:
            valid = False
        color = COLORS["WHITE"] if valid else COLORS["RED"]
        rect = pygame.Rect(target_cell[0] * GRID_SIZE, target_cell[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, color, rect, 3)

def draw_vision_indicator(screen):
    """
    當存在視野提升效果（vision_boost）時，
    根據 vision_boost["remaining"] 顯示視野指示器：
      - 若 remaining 在 1 到 10 之間，使用 no1.png 至 no10.png；
      - 否則使用 no.png。
    指示器被放大至單元格大小，並顯示在機體正上方一格的位置。
    """
    if "vision_boost" in game_state:
        remaining = game_state["vision_boost"]["remaining"]
        if 1 <= remaining <= 10:
            path = os.path.join("sample", "number", f"no{remaining}.png")
        else:
            path = os.path.join("sample", "number", "no.png")
        indicator_img = load_scaled_image(path, (GRID_SIZE, GRID_SIZE))
        unit_cell = map_layout["start_positions"][0]
        pos_x = unit_cell[0] * GRID_SIZE
        pos_y = (unit_cell[1]) * GRID_SIZE  # 将指示器显示在机体正上方一格
        screen.blit(indicator_img, (pos_x, pos_y))








def handle_input(event):
    """
    處理所有使用者輸入，包括機體移動、技能瞄準、普通攻擊、建造與技能3（策法「陰陽寶玉」）。
    全局右鍵點擊（event.button == 3）取消所有選擇。
    僅允許當前回合的玩家（P1）操作，行動完成後自動結算公告並切換回合。
    """
    # 若當前回合不是 P1，則忽略 P1 輸入
    if game_state["current_turn"]["active_player"] != "P1":
        return

    # 全局右鍵取消所有狀態
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
        game_state["moving"] = False
        game_state["aiming"] = False
        game_state["building"] = False
        game_state["selected_skill"] = None
        game_state["hovered_skill"] = None
        return

    mouse_pos = pygame.mouse.get_pos()
    grid_x = mouse_pos[0] // GRID_SIZE
    grid_y = mouse_pos[1] // GRID_SIZE
    target_cell = (grid_x, grid_y)
    unit_cell = map_layout["start_positions"][0]  # 玩家所在格
    unit_rect = pygame.Rect(unit_cell[0]*GRID_SIZE, unit_cell[1]*GRID_SIZE, GRID_SIZE, GRID_SIZE)

    # ------------------ 普通攻擊判斷 ------------------
    # 若點擊的目標屬於實體（牆體或在 start_positions 中但非自己），且在移動範圍內，則觸發普通攻擊
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if ((target_cell in map_layout["walls"]) or 
            (target_cell in map_layout["start_positions"] and target_cell != unit_cell)):
            dx = grid_x - unit_cell[0]
            dy = grid_y - unit_cell[1]
            if max(abs(dx), abs(dy)) <= MOVEMENT_RADIUS:
                num_bullets = PLAYER_STATS["P1"]["attack"]
                start_pixel = (unit_cell[0]*GRID_SIZE + GRID_SIZE//2, unit_cell[1]*GRID_SIZE + GRID_SIZE//2)
                target_center = (grid_x*GRID_SIZE + GRID_SIZE//2, grid_y*GRID_SIZE + GRID_SIZE//2)
                dx_pixel = target_center[0] - start_pixel[0]
                dy_pixel = target_center[1] - start_pixel[1]
                length = math.sqrt(dx_pixel**2 + dy_pixel**2)
                if length != 0:
                    direction = (dx_pixel/length, dy_pixel/length)
                    # 普通攻擊子彈速度調慢10倍
                    bullets = [{
                        "pos": (start_pixel[0], start_pixel[1]),
                        "direction": direction,
                        "speed": (GRID_SIZE/8)/10,
                        "skill": "normal",
                        "owner": game_state["current_turn"]["active_player"]
                    } for _ in range(num_bullets)]

                    game_state["bullet_queue"].extend(bullets)
                    add_announcement(f"{P1_character} 發動了普通攻擊")
                    finish_turn("normal")
                    return

    # ------------------ 移動模式 ------------------
    if game_state.get("moving", False):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            dx = grid_x - unit_cell[0]
            dy = grid_y - unit_cell[1]
            if grid_x < 0 or grid_x >= MAP_WIDTH or grid_y < 0 or grid_y >= MAP_HEIGHT:
                pass
            elif target_cell in map_layout["walls"]:
                pass
            # 若目標格屬於其他角色（敵方），則移動無效（普通攻擊已處理）
            elif (target_cell in map_layout["start_positions"]) and (target_cell != unit_cell):
                pass
            elif max(abs(dx), abs(dy)) <= MOVEMENT_RADIUS and (dx != 0 or dy != 0):
                map_layout["start_positions"][0] = (grid_x, grid_y)
                if dx == 0 or dy == 0:
                    PLAYER_STATS["P1"]["mana"] += 1
                game_state["moving"] = False
                add_announcement(f"{P1_character} 進行了移動")
                finish_turn("move")
            else:
                pass
        return

    # ------------------ 建造模式 ------------------
    if game_state.get("building", False):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            center_cell = unit_cell  # 以玩家当前所在格为中心
            dx = grid_x - center_cell[0]
            dy = grid_y - center_cell[1]
            if grid_x < 0 or grid_x >= MAP_WIDTH or grid_y < 0 or grid_y >= MAP_HEIGHT:
                pass
            elif target_cell in map_layout["walls"]:
                pass
            elif target_cell in map_layout["start_positions"]:
                pass
            elif max(abs(dx), abs(dy)) <= game_state["current_mana_input"] and not (dx == 0 and dy == 0):
                if PLAYER_STATS["P1"]["mana"] >= game_state["current_mana_input"]:
                    mana_used = game_state["current_mana_input"]
                    PLAYER_STATS["P1"]["mana"] -= mana_used
                    map_layout["walls"].append(target_cell)
                    wall_health[target_cell] = mana_used
                    wall_total[target_cell] = mana_used
            game_state["building"] = False
            add_announcement(f"{P1_character} 進行了建造")
            finish_turn("build")


    # ------------------ 技能及其他操作 ------------------
    if event.type == pygame.MOUSEMOTION:
        if not game_state.get("aiming", False):
            game_state["hovered_skill"] = None
            # 技能區位置：(2,9), (4,9), (6,9), (8,9) 分別對應技能1、2、3、4
            for i, (x, y) in enumerate([(2, 9), (4, 9), (6, 9), (8, 9)], 1):
                if (grid_x, grid_y) == (x, y):
                    game_state["hovered_skill"] = i
                    break
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        # 【修改說明】：技能3（策法「陰陽寶玉」）直接觸發，不需點選機體
        if game_state.get("hovered_skill") == 3:
            if game_state.get("current_mana_input", 0) > 0:
                game_state["selected_skill"] = 3
                if PLAYER_STATS["P1"]["mana"] >= game_state["current_mana_input"]:
                    mana_used = game_state["current_mana_input"]
                    PLAYER_STATS["P1"]["mana"] -= mana_used
                    # 設定視野提升效果：持續回合數和擴展視野半徑均為 mana_used
                    game_state["vision_boost"] = {"remaining": mana_used, "radius": mana_used}
                    add_announcement(f"策法：「陰陽寶玉」\n靈夢獲得了\n半徑為[{mana_used}]的視野")
                    finish_turn("vision", extra_info=str(mana_used))
                game_state["selected_skill"] = None
            return

        # 以下其他技能分支保持不變……
        # （此處省略其他技能分支，請保留原有處理邏輯）




        # 若點擊在建造按鈕 (0,10)，則進入建造模式
        if (grid_x, grid_y) == (0, 10) and game_state.get("current_mana_input", 0) > 0:
            game_state["building"] = True
            return
     # ------------------ 侦察模式 ------------------
        # 技能侦察：点击 (0,9) 触发
        if (grid_x, grid_y) == (0, 9) and game_state.get("current_mana_input", 0) > 0:
            if PLAYER_STATS["P1"]["mana"] >= 1:
                PLAYER_STATS["P1"]["mana"] -= 1
                # 记录敌方当前的位置（固定侦察位置）
                game_state["recon_position"] = map_layout["start_positions"][1]
                add_announcement("偵察：敵方機體位置已暴露1回合")
                finish_turn("scout")
            return
        # 若點擊在自己的機體上則進入移動模式
        if unit_rect.collidepoint(mouse_pos):
            game_state["moving"] = True
            game_state["aiming"] = False
            return

        # 其餘技能（技能1、2、4）處理不變
        if game_state.get("aiming", False):
            start_pixel = (unit_cell[0]*GRID_SIZE + GRID_SIZE//2, unit_cell[1]*GRID_SIZE + GRID_SIZE//2)
            mouse_pixel = pygame.mouse.get_pos()
            dx_pixel = mouse_pixel[0] - start_pixel[0]
            dy_pixel = mouse_pixel[1] - start_pixel[1]
            if dx_pixel == 0 and dy_pixel == 0:
                return
            length = (dx_pixel**2 + dy_pixel**2)**0.5
            direction = (dx_pixel/length, dy_pixel/length)
            # 技能1：霰術「Persuasion Needle」
            if game_state["selected_skill"] == 1 and game_state["current_mana_input"] > 0:
                if PLAYER_STATS["P1"]["mana"] >= game_state["current_mana_input"]:
                    PLAYER_STATS["P1"]["mana"] -= game_state["current_mana_input"]
                    game_state["bullet_queue"] = [{
                        "pos": (start_pixel[0], start_pixel[1]),
                        "direction": direction,
                        "speed": GRID_SIZE//8,
                        "skill": 1
                    } for _ in range(game_state["current_mana_input"])]
                    game_state["current_mana_input"] = 0
                    add_announcement("霰術：「Persuasion Needle」\n靈夢發射了封魔針")
                    finish_turn("needle")
            # 技能2：霊耗「Homing Amulet」
            elif game_state["selected_skill"] == 2:
                if PLAYER_STATS["P1"]["mana"] >= 1:
                    PLAYER_STATS["P1"]["mana"] -= 1
                    game_state["bullet_queue"].append({
                        "pos": (start_pixel[0], start_pixel[1]),
                        "direction": direction,
                        "speed": GRID_SIZE//8,
                        "skill": 2
                    })
                    add_announcement("霊耗：「Homing Amulet」\n靈夢發射了符札")
                    finish_turn("amulet")
            # 技能4：秘奧「G Free」
            elif game_state["selected_skill"] == 4 and game_state["current_mana_input"] > 0:
                if PLAYER_STATS["P1"]["mana"] >= game_state["current_mana_input"]:
                    mana_used = game_state["current_mana_input"]
                    PLAYER_STATS["P1"]["mana"] -= mana_used
                    map_layout["start_positions"][0] = (grid_x, grid_y)
                    add_announcement(f"秘奧：「G Free」\n靈夢閃現到了半徑為[{mana_used}]內的一格")
                    finish_turn("teleport", extra_info=str(mana_used))
            game_state["aiming"] = False
            game_state["selected_skill"] = None
        else:
            if game_state["hovered_skill"]:
                if game_state["hovered_skill"] == 1:
                    if game_state["current_mana_input"] > 0:
                        game_state["selected_skill"] = 1
                        game_state["aiming"] = True
                elif game_state["hovered_skill"] == 2:
                    game_state["selected_skill"] = 2
                    game_state["aiming"] = True
                elif game_state["hovered_skill"] == 4:
                    if game_state["current_mana_input"] > 0:
                        game_state["selected_skill"] = 4
                        game_state["aiming"] = True
            elif (grid_x, grid_y) == (9, 9):
                game_state["current_mana_input"] = max(0, game_state["current_mana_input"] - 1)
            elif (grid_x, grid_y) == (11, 9):
                max_mana = min(PLAYER_STATS["P1"]["mana"], 99)
                game_state["current_mana_input"] = min(max_mana, game_state["current_mana_input"] + 1)








def draw_movement_indicator(screen):
    """
    繪製機體移動指示器：
      - 若滑鼠所在格超出允許移動範圍（MOVEMENT_RADIUS）則顯示黑色；
      - 若在範圍內但該格被「實體」佔據（牆體或其他角色，除自己外）則顯示紅色；
      - 若在範圍內且可移動，則顯示白色。
    """
    if game_state.get("moving", False):
        mouse_pos = pygame.mouse.get_pos()
        target_cell = (mouse_pos[0] // GRID_SIZE, mouse_pos[1] // GRID_SIZE)
        unit_cell = map_layout["start_positions"][0]  # 玩家當前位置
        dx = target_cell[0] - unit_cell[0]
        dy = target_cell[1] - unit_cell[1]
        
        # 如果超出地圖邊界，視為無效，顯示黑色
        if target_cell[0] < 0 or target_cell[0] >= MAP_WIDTH or target_cell[1] < 0 or target_cell[1] >= MAP_HEIGHT:
            color = COLORS["BLACK"]
        # 超出允許移動範圍（或為原地）則顯示黑色
        elif max(abs(dx), abs(dy)) > MOVEMENT_RADIUS or (dx == 0 and dy == 0):
            color = COLORS["BLACK"]
        else:
            # 如果該格被牆體或其他角色佔據（除了自己），則顯示紅色
            if target_cell in map_layout["walls"] or (target_cell in map_layout["start_positions"] and target_cell != unit_cell):
                color = COLORS["RED"]
            else:
                color = COLORS["WHITE"]
        rect = pygame.Rect(target_cell[0] * GRID_SIZE, target_cell[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, color, rect, 3)




# 7. 主游戏循环
# 7. 主游戏循环
def main():
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Voyage1969")
    clock = pygame.time.Clock()
    
    global skills
    skills = {P1_character: load_skill_icons(P1_character)}
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == ENEMY_ACTION_EVENT:
                auto_enemy_action()
            else:
                handle_input(event)
        
        update_bullets()
        screen.fill(COLORS["BLACK"])
        draw_game_map(screen)
        draw_skill_bar(screen)
        draw_info_panel(screen, pygame.mouse.get_pos())
        if game_state.get("aiming", False):
            start_x = map_layout["start_positions"][0][0] * GRID_SIZE + GRID_SIZE // 2
            start_y = map_layout["start_positions"][0][1] * GRID_SIZE + GRID_SIZE // 2
            pygame.draw.line(screen, COLORS["RED"], (start_x, start_y), pygame.mouse.get_pos(), 2)
        draw_teleport_line(screen)
        draw_bullets(screen)
        draw_build_indicator(screen)
        draw_vision_indicator(screen)
        draw_mouse_indicator(screen)
        draw_movement_indicator(screen)
        draw_mist(screen)
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()


if __name__ == "__main__":
    main()

        