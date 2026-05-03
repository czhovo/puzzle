"""拖拽处理模块（支持宽幅图片，符合最新规则）"""

import tkinter as tk
from PIL import Image, ImageTk


class DragHandler:
    """处理所有拖拽相关逻辑"""
    
    def __init__(self, app):
        self.app = app
        self.drag_window = None
        self.drag_label = None
        self.drag_data = {
            "item": None,
            "type": None,          # 'unplaced' 或 'grid'
            "source_folder": None,
            "source_index": None,
            "source_key": None,    # 如果来自格子，这里是触发拖拽的键（可能非起始格）
            "start_x": 0,
            "start_y": 0,
            "orig_x": 0,
            "orig_y": 0,
            "img_data": None
        }
    
    def start_grid_drag(self, event, key):
        """开始拖拽左侧网格中的图片（key 为触发拖拽的格子）"""
        img_data = self.app.grid_contents.get(key)
        if img_data is None:
            return
        
        # 宽幅图拖拽使用整个跨格大图
        if img_data.get('pic_type') == 'wide':
            # 获取起始格
            start = img_data.get('grid_start')
            if start is None:
                start = key
            # 使用 tk_span 图片（拖拽浮动窗口）
            img_tk = img_data.get('tk_span')
            if img_tk is None:
                img_tk = img_data['tk_big']
        else:
            img_tk = img_data['tk_big']
        
        self._create_drag_window(img_tk, event.x_root, event.y_root)
        
        self.drag_data = {
            "item": event.widget,
            "type": "grid",
            "source_folder": None,
            "source_index": None,
            "source_key": key,
            "start_x": event.x_root,
            "start_y": event.y_root,
            "orig_x": event.x_root,
            "orig_y": event.y_root,
            "img_data": img_data
        }
    
    def start_small_drag(self, event, folder_name, idx):
        """开始拖拽右侧小图"""
        img_data = self.app.folder_images[folder_name][idx]
        pic_type = img_data.get('pic_type', 'standard')
        
        if pic_type == 'wide':
            # 使用宽幅预览尺寸（高度与预览一致，宽度两倍）
            preview_h = self.app.preview_height
            preview_w = int(preview_h * (2.0 / 1.59))   # 宽幅比例
            drag_img = ImageTk.PhotoImage(
                img_data['pil'].resize((preview_w, preview_h), Image.Resampling.LANCZOS)
            )
        else:
            drag_img = ImageTk.PhotoImage(img_data['pil'])
        
        self._create_drag_window(drag_img, event.x_root, event.y_root)
        self.drag_label.image = drag_img
        
        self.drag_data = {
            "item": event.widget,
            "type": "unplaced",
            "source_folder": folder_name,
            "source_index": idx,
            "source_key": None,
            "start_x": event.x_root,
            "start_y": event.y_root,
            "orig_x": event.x_root,
            "orig_y": event.y_root,
            "img_data": img_data
        }
    
    def _create_drag_window(self, image, x, y):
        """创建拖拽浮动窗口"""
        self.drag_window = tk.Toplevel(self.app.root)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes('-topmost', True)
        self.drag_label = tk.Label(self.drag_window, image=image, bg='#34495e')
        self.drag_label.pack()
        self.drag_window.geometry(f"+{x-10}+{y-10}")
    
    def on_drag_move(self, event):
        """拖拽移动"""
        if self.drag_data.get("img_data") is None:
            return
        if self.drag_window:
            self.drag_window.geometry(f"+{event.x_root-10}+{event.y_root-10}")
    
    def on_drop(self, event):
        """释放放置（核心逻辑）"""
        if self.drag_data.get("img_data") is None:
            return
        
        mouse_x, mouse_y = event.x_root, event.y_root
        target_key = self._find_target_grid(mouse_x, mouse_y)
        is_in_right = self._is_in_right_area(mouse_x, mouse_y)
        
        # 未放到有效区域，直接取消拖拽
        if target_key is None and not is_in_right:
            self._cleanup_drag()
            return
        
        drag_type = self.drag_data["type"]
        img_data = self.drag_data["img_data"]
        pic_type = img_data.get('pic_type', 'standard')
        
        if drag_type == "unplaced":
            # 从右侧拖出
            if is_in_right:
                # 放回右侧，不做任何事
                self._cleanup_drag()
                return
            # 目标是左侧格子
            C = target_key
            if pic_type == 'standard':
                # 标准图：如果C空白则放入，否则禁止
                if self._cell_empty(C):
                    self.app.place_image_to_grid(img_data, C)
                    self.app.update_status(f"✓ {img_data['label']} 已放入格子")
                else:
                    self.app.update_status("✗ 目标格已被占用")
            else:  # wide
                C, D = self._get_wide_target_cells(C)
                if C is None:
                    self.app.update_status("✗ 无法放置：列数不足")
                elif self._cell_empty(C) and self._cell_empty(D):
                    self.app.place_image_to_grid(img_data, C)
                    self.app.update_status(f"✓ 宽幅图片已放入 ({C},{D})")
                else:
                    self.app.update_status("✗ 目标两格不全空")
        else:  # drag_type == "grid"
            source_key = self.drag_data["source_key"]
            if is_in_right:
                # 拖回右侧
                self.app.return_image_to_right(img_data, source_key)
                self.app.update_status(f"✓ {img_data['label']} 已放回右侧")
            else:
                # 左侧内部移动
                C = target_key
                self._process_grid_move(img_data, source_key, C)
        
        self._cleanup_drag()
    
    def _process_grid_move(self, img_data, source_key, C):
        """处理来自左侧格子的拖拽移动"""
        pic_type = img_data.get('pic_type', 'standard')
        
        if pic_type == 'standard':
            self._move_standard_from_grid(img_data, source_key, C)
        else:  # wide
            self._move_wide_from_grid(img_data, source_key, C)
    
    def _move_standard_from_grid(self, img_data, A, C):
        """移动标准图片（来源格子A，目标格子C）"""
        wide_region = self._get_wide_region_at(C)

        if wide_region is None:
            # C 不是宽幅的一部分：交换标准图与空/标准图
            if self._cell_empty(C) or self._get_occupant(C) is not None:
                self._swap_two_cells(A, C)
                self.app.update_status(f"✓ 移动完成")
            else:
                self.app.update_status("✗ 目标格异常")
            return

        # C 是宽幅的一部分
        left, right = wide_region           # 宽幅占据的格子

        if C == left:                      # C 是宽幅左半，宽幅在 (C, C+1)
            required = (A[0], A[1] + 1)    # A+1
            if self._is_valid_cell(required) and self._cell_empty(required):
                # 普通情况：A+1 存在且空，交换区域 (A, A+1) 与 (C, C+1)
                self._swap_regions((A, required), (left, right))
                self.app.update_status("✓ 标准图与宽幅图交换成功")
            elif A[0] == left[0] and A[1] == left[1] - 1:   # A = C-1，标准图在宽幅左侧相邻
                # 特殊情况：相邻交换，宽幅移到 (A, A+1)，标准移到 C+1
                target_std = (left[0], left[1] + 1)        # C+1
                if not self._is_valid_cell(target_std) or not self._cell_empty(target_std):
                    self.app.update_status("✗ 无法交换：目标位置不存在或被占用")
                    return
                self._adjacent_swap_standard_wide(A, C, left, right, to_left=False)
                self.app.update_status("✓ 相邻标准-宽幅交换成功")
            else:
                self.app.update_status("✗ 无法移动：A+1不存在或不空")
        else:                             # C 是宽幅右半，宽幅在 (C-1, C)
            required = (A[0], A[1] - 1)   # A-1
            if self._is_valid_cell(required) and self._cell_empty(required):
                self._swap_regions((required, A), (left, right))
                self.app.update_status("✓ 标准图与宽幅图交换成功")
            elif A[0] == right[0] and A[1] == right[1] + 1: # A = C+1，标准图在宽幅右侧相邻
                target_std = (right[0], right[1] - 1)       # C-1
                if not self._is_valid_cell(target_std) or not self._cell_empty(target_std):
                    self.app.update_status("✗ 无法交换：目标位置不存在或被占用")
                    return
                self._adjacent_swap_standard_wide(A, C, left, right, to_left=True)
                self.app.update_status("✓ 相邻标准-宽幅交换成功")
            else:
                self.app.update_status("✗ 无法移动：A-1不存在或不空")

    def _adjacent_swap_standard_wide(self, A, C, left, right, to_left):
        """
        执行相邻标准图与宽幅图的直接交换。
        to_left=True:  标准图在宽幅右侧(A=C+1)，宽幅右移，标准移到宽幅原左半。
        to_left=False: 标准图在宽幅左侧(A=C-1)，宽幅左移，标准移到宽幅原右半。
        """
        wide_img = self.app.grid_contents[left]   # 宽幅图片对象
        std_img  = self.app.grid_contents[A]

        # 清空所有涉及格子
        self.app.grid_contents[A] = None
        self.app.grid_contents[left] = None
        self.app.grid_contents[right] = None

        if to_left:
            # 宽幅移到 (A-1, A) 即 (C, C+1) ？实际 A = C+1
            new_wide_left = (A[0], A[1] - 1)
            new_wide_right = A
            new_std = left                       # 标准图放到原宽幅左半
        else:
            # 宽幅移到 (A, A+1) 即 (C-1, C)
            new_wide_left = A
            new_wide_right = (A[0], A[1] + 1)
            new_std = right                      # 标准图放到原宽幅右半

        # 更新宽幅图位置
        wide_img['grid_start'] = new_wide_left
        self.app.grid_contents[new_wide_left] = wide_img
        self.app.grid_contents[new_wide_right] = wide_img

        # 标准图放入新位置
        std_img['grid_start'] = new_std
        self.app.grid_contents[new_std] = std_img

        # 重绘变化的格子
        for key in (A, left, right, new_wide_left, new_wide_right, new_std):
            if self._is_valid_cell(key):
                self.app.draw_grid_image(key)

    def _move_wide_from_grid(self, img_data, source_key, C):
        """移动宽幅图片"""
        start = img_data.get('grid_start')
        if start is None:
            start = source_key
        A, B = start, (start[0], start[1] + 1)

        C_target, D_target = self._get_wide_target_cells(C)
        if C_target is None:
            self.app.update_status("✗ 目标区域无效")
            return

        # 收集目标区域的占用情况
        occ_c = self._get_occupant(C_target)
        occ_d = self._get_occupant(D_target)

        # 检查目标是否是一张完整宽幅图
        target_is_wide = (occ_c is not None and occ_c == occ_d and
                          occ_c.get('pic_type') == 'wide' and
                          occ_c.get('grid_start') == C_target)

        # 检查是否被其他宽幅部分占用（不属于同一张完整宽幅）
        c_wide = self._get_wide_region_at(C_target)
        d_wide = self._get_wide_region_at(D_target)
        blocked_by_wide_c = (c_wide is not None and c_wide != (C_target, D_target))
        blocked_by_wide_d = (d_wide is not None and d_wide != (C_target, D_target))

        # 判断是否为相邻标准图特殊情况
        # 条件：目标区域与来源区域有重叠，且重叠部分是本宽幅，非重叠部分是一张标准图
        overlap = (A == C_target or A == D_target or B == C_target or B == D_target)
        if overlap and not target_is_wide and not blocked_by_wide_c and not blocked_by_wide_d:
            # 确定标准图在哪个位置
            if occ_c is not None and occ_c.get('pic_type') == 'standard':
                std_cell = C_target
                other_cell = D_target
            elif occ_d is not None and occ_d.get('pic_type') == 'standard':
                std_cell = D_target
                other_cell = C_target
            else:
                std_cell = None

            if std_cell is not None:
                # 相邻交换：宽幅移动，标准图换到另一侧
                self._adjacent_swap_wide_standard(A, B, C_target, D_target, std_cell, other_cell)
                self.app.update_status("✓ 宽幅与标准图交换成功")
                return

        # 常规处理
        if target_is_wide:
            self._swap_regions((A, B), (C_target, D_target))
            self.app.update_status("✓ 两张宽幅交换成功")
        elif not blocked_by_wide_c and not blocked_by_wide_d:
            # 目标区域为空或为标准图（且不相邻重叠的情况上面已处理）
            if (self._cell_empty(C_target) or (occ_c and occ_c.get('pic_type') == 'standard')) and \
               (self._cell_empty(D_target) or (occ_d and occ_d.get('pic_type') == 'standard')):
                self._swap_regions((A, B), (C_target, D_target))
                self.app.update_status("✓ 宽幅移动成功")
            else:
                self.app.update_status("✗ 目标区域被占用")
        else:
            self.app.update_status("✗ 目标区域被其他宽幅占用")

    def _adjacent_swap_wide_standard(self, A, B, C, D, std_cell, other_cell):
        """
        相邻宽幅与标准图交换：宽幅从 (A,B) 移到 (C,D)（与自身重叠），标准图移到另一边。
        other_cell 是目标区域中不与来源重叠的那个格子，即宽幅将占据的区域之一，
        标准图将放到来源区域中不与目标重叠的那个格子。
        """
        wide_img = self.app.grid_contents[A]
        std_img = self.app.grid_contents[std_cell]

        # 计算标准图的新位置（即宽幅移走后空出的那个格子）
        if A not in (C, D):           # 来源左格未被覆盖
            new_std = A
        else:
            new_std = B

        # 清空所有相关格子
        for k in (A, B, C, D, std_cell):
            if self._is_valid_cell(k):
                self.app.grid_contents[k] = None

        # 放置宽幅到 (C, D)
        wide_img['grid_start'] = C
        self.app.grid_contents[C] = wide_img
        self.app.grid_contents[D] = wide_img

        # 放置标准图到 new_std
        std_img['grid_start'] = new_std
        self.app.grid_contents[new_std] = std_img

        # 重绘所有相关格子
        for k in set([A, B, C, D, std_cell, new_std]):
            if self._is_valid_cell(k):
                self.app.draw_grid_image(k)

    # ---------- 辅助方法 ----------
    
    def _cell_empty(self, key):
        """判断单个格子是否为空（注意宽幅图占用两个格子，需用 grid_contents 判断）"""
        return self.app.grid_contents.get(key) is None

    def _get_occupant(self, key):
        """返回格子里的 img_data，若无返回 None"""
        return self.app.grid_contents.get(key)

    def _is_valid_cell(self, key):
        """检查 key 是否在 left_grids 中"""
        return key in self.app.left_grids

    def _get_wide_region_at(self, key):
        """
        如果 key 是某宽幅图的一部分，返回 (left_key, right_key)，否则 None
        """
        occupant = self._get_occupant(key)
        if occupant is None:
            return None
        if occupant.get('pic_type') == 'wide':
            start = occupant.get('grid_start')
            if start is None:
                return None
            return (start, (start[0], start[1] + 1))
        return None

    def _get_wide_target_cells(self, C):
        """根据鼠标所在格子C，返回宽幅图应占据的连续两个格子 (C, D)，考虑边界"""
        if not self._is_valid_cell(C):
            return (None, None)
        row, col = C
        if col < self.app.grid_cols - 1:
            return (C, (row, col + 1))
        elif col > 0:
            # 边界右侧，向左取两格
            return ((row, col - 1), C)
        else:
            return (None, None)  # 只有一列，无法放置宽幅

    def _swap_two_cells(self, key1, key2):
        """交换两个单格的内容（可处理空）"""
        img1 = self.app.grid_contents.get(key1)
        img2 = self.app.grid_contents.get(key2)
        # 清除 grid_start 引用
        if img1:
            img1['grid_start'] = key1
        if img2:
            img2['grid_start'] = key2
        self.app.grid_contents[key1] = img2
        self.app.grid_contents[key2] = img1
        self.app.draw_grid_image(key1)
        self.app.draw_grid_image(key2)

    def _swap_regions(self, region1, region2):
        """
        交换两个区域的内容。每个区域是一个元组：
          - 单格区域： (key,)
          - 两格区域： (left_key, right_key)   [必须是水平相邻的两格]
        处理宽幅图片的 grid_start 更新和重绘。
        """
        # 收集区域涉及的所有格子
        def normalize_region(region):
            if isinstance(region, tuple):
                if len(region) == 2 and isinstance(region[0], int) and isinstance(region[1], int):
                    return [region]  # 这是一个格子坐标 (row, col)
                else:
                    return list(region)
            else:
                return [region]
        keys1 = normalize_region(region1)
        keys2 = normalize_region(region2)
        
        # 获取区域对应的 img_data（对于宽幅，两个 key 指向同一个对象，区域取起始格对象）
        def get_region_img(keys):
            if not keys:
                return None
            img = self._get_occupant(keys[0])
            if img is None:
                return None
            if len(keys) == 2 and img.get('pic_type') == 'wide':
                return img
            return img  # 单格
        
        img1 = get_region_img(keys1)
        img2 = get_region_img(keys2)
        
        # 清空所有涉及的格子
        for k in keys1 + keys2:
            self.app.grid_contents[k] = None
        
        # 放置 img1 到 region2
        if img1:
            if len(keys2) == 1:
                img1['grid_start'] = keys2[0]
                self.app.grid_contents[keys2[0]] = img1
            else:  # 两格
                img1['grid_start'] = keys2[0]
                self.app.grid_contents[keys2[0]] = img1
                self.app.grid_contents[keys2[1]] = img1
        
        # 放置 img2 到 region1
        if img2:
            if len(keys1) == 1:
                img2['grid_start'] = keys1[0]
                self.app.grid_contents[keys1[0]] = img2
            else:
                img2['grid_start'] = keys1[0]
                self.app.grid_contents[keys1[0]] = img2
                self.app.grid_contents[keys1[1]] = img2
        
        # 重绘所有格子
        for k in keys1 + keys2:
            self.app.draw_grid_image(k)
    
    # ---------- 坐标查找方法 ----------
    def _find_target_grid(self, mouse_x, mouse_y):
        canvas_root_x = self.app.left_canvas.winfo_rootx()
        canvas_root_y = self.app.left_canvas.winfo_rooty()
        scroll_x = self.app.left_canvas.canvasx(0)
        scroll_y = self.app.left_canvas.canvasy(0)
        
        for key, (x1, y1, x2, y2) in self.app.left_grids.items():
            actual_x = canvas_root_x + x1 - scroll_x
            actual_y = canvas_root_y + y1 - scroll_y
            actual_x2 = canvas_root_x + x2 - scroll_x
            actual_y2 = canvas_root_y + y2 - scroll_y
            if actual_x <= mouse_x <= actual_x2 and actual_y <= mouse_y <= actual_y2:
                return key
        return None
    
    def _is_in_right_area(self, mouse_x, mouse_y):
        right_x = self.app.right_canvas.winfo_rootx()
        right_y = self.app.right_canvas.winfo_rooty()
        right_x2 = right_x + self.app.right_canvas.winfo_width()
        right_y2 = right_y + self.app.right_canvas.winfo_height()
        return (right_x <= mouse_x <= right_x2 and right_y <= mouse_y <= right_y2)
    
    def _cleanup_drag(self):
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
        self.drag_data = {
            "item": None, "type": None, "source_folder": None,
            "source_index": None, "source_key": None, "start_x": 0,
            "start_y": 0, "orig_x": 0, "orig_y": 0, "img_data": None
        }