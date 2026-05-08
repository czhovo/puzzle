"""拖拽处理模块（支持宽幅图片，修复版）"""

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
            "type": None,
            "source_folder": None,
            "source_index": None,
            "source_key": None,
            "start_x": 0,
            "start_y": 0,
            "orig_x": 0,
            "orig_y": 0,
            "img_data": None
        }
    
    # ==================== 拖拽开始 ====================
    
    def start_grid_drag(self, event, key):
        """开始拖拽左侧网格中的图片"""
        img_data = self.app.grid_contents.get(key)
        if img_data is None:
            return
        
        if img_data.get('pic_type') == 'wide':
            start = img_data.get('grid_start')
            if start is None:
                start = key
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
            preview_h = self.app.preview_height
            preview_w = int(preview_h * (2.0 / 1.59))
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
    
    # ==================== 拖拽释放 ====================
    
    def on_drop(self, event):
        """释放放置"""
        if self.drag_data.get("img_data") is None:
            return
        
        mouse_x, mouse_y = event.x_root, event.y_root
        target_key = self._find_target_grid(mouse_x, mouse_y)
        is_in_right = self._is_in_right_area(mouse_x, mouse_y)
        
        if target_key is None and not is_in_right:
            self._cleanup_drag()
            return
        
        drag_type = self.drag_data["type"]
        img_data = self.drag_data["img_data"]
        pic_type = img_data.get('pic_type', 'standard')
        
        if drag_type == "unplaced":
            # 从右侧拖出
            if is_in_right:
                self._cleanup_drag()
                return
            C = target_key
            if pic_type == 'standard':
                if self._cell_empty(C) and not self._is_part_of_wide(C):
                    self.app.place_image_to_grid(img_data, C)
                    self.app.update_status(f"✓ {img_data['label']} 已放入格子")
                else:
                    self.app.update_status("✗ 目标格已被占用")
            else:  # wide
                C_target, D_target = self._get_wide_target_cells(C)
                if C_target is None:
                    self.app.update_status("✗ 无法放置：列数不足")
                elif self._cell_empty(C_target) and self._cell_empty(D_target):
                    self.app.place_image_to_grid(img_data, C_target)
                    self.app.update_status(f"✓ 宽幅图片已放入")
                else:
                    self.app.update_status("✗ 目标两格不全空")
        else:  # drag_type == "grid"
            source_key = self.drag_data["source_key"]
            if is_in_right:
                self.app.return_image_to_right(img_data, source_key)
                self.app.update_status(f"✓ {img_data['label']} 已放回右侧")
            else:
                C = target_key
                self._process_grid_move(img_data, source_key, C)
        
        self._cleanup_drag()
    
    def _process_grid_move(self, img_data, source_key, C):
        """处理来自左侧格子的拖拽移动"""
        pic_type = img_data.get('pic_type', 'standard')
        if pic_type == 'standard':
            self._move_standard_from_grid(img_data, source_key, C)
        else:
            self._move_wide_from_grid(img_data, source_key, C)
    
    # ==================== 标准图移动 ====================
    
    def _move_standard_from_grid(self, img_data, A, C):
        """移动标准图片（来源格子A，目标格子C）"""
        if A == C:
            return
        
        wide_region = self._get_wide_region_at(C)
        
        if wide_region is None:
            # C 不是宽幅的一部分
            if self._cell_empty(C) or self._is_standard_at(C):
                self._swap_two_cells(A, C)
                self.app.update_status("✓ 移动完成")
            else:
                self.app.update_status("✗ 目标格异常")
            return
        
        # C 是宽幅的一部分
        left, right = wide_region
        
        if C == left:
            # C是宽幅左半，宽幅在 (left, right) 即 (C, C+1)
            # 检查是否相邻：标准图在宽幅左侧紧邻
            if A[0] == left[0] and A[1] == left[1] - 1:
                # 相邻情况：宽幅左移，标准图到right
                self._adjacent_swap_standard_wide(A, left, right, 'left')
                self.app.update_status("✓ 相邻交换成功")
                return
            
            # 不相邻：需要A+1存在且空
            required = (A[0], A[1] + 1)
            if self._is_valid_cell(required) and self._cell_empty(required):
                # 交换 (宽幅left,right) 与 (标准图A, A+1)
                self._swap_regions((left, right), (A, required))
                self.app.update_status("✓ 标准图与宽幅图交换成功")
            else:
                self.app.update_status("✗ 无法移动：A+1不存在或不空")
        else:
            # C是宽幅右半，宽幅在 (left, right) 即 (C-1, C)
            # 检查是否相邻：标准图在宽幅右侧紧邻
            if A[0] == right[0] and A[1] == right[1] + 1:
                # 相邻情况：宽幅右移，标准图到left
                self._adjacent_swap_standard_wide(A, left, right, 'right')
                self.app.update_status("✓ 相邻交换成功")
                return
            
            # 不相邻：需要A-1存在且空
            required = (A[0], A[1] - 1)
            if self._is_valid_cell(required) and self._cell_empty(required):
                # 交换 (宽幅left,right) 与 (A-1, 标准图A)
                self._swap_regions((left, right), (required, A))
                self.app.update_status("✓ 标准图与宽幅图交换成功")
            else:
                self.app.update_status("✗ 无法移动：A-1不存在或不空")
    
    def _adjacent_swap_standard_wide(self, std_cell, wide_left, wide_right, direction):
        """
        相邻标准图与宽幅图交换。
        
        参数：
            std_cell: 标准图所在格子
            wide_left, wide_right: 宽幅图当前占据的两格
            direction:
                'right' - 标准图在宽幅左侧紧邻，宽幅右移一格
                'left'  - 标准图在宽幅右侧紧邻，宽幅左移一格
        
        结果：
            direction='right': 标准图→wide_left, 宽幅→(wide_left+1, wide_right+1)
            direction='left':  标准图→wide_right, 宽幅→(wide_left-1, wide_right-1)
        """
        wide_img = self.app.grid_contents[wide_left]
        std_img = self.app.grid_contents[std_cell]
        
        # 清空所有涉及格子
        self.app.grid_contents[std_cell] = None
        self.app.grid_contents[wide_left] = None
        self.app.grid_contents[wide_right] = None
        
        if direction == 'right':
            # 标准图在宽幅右侧，宽幅右移
            new_wide_left = (wide_left[0], wide_left[1] + 1)   # 原left+1
            new_wide_right = (wide_right[0], wide_right[1] + 1) # 原right+1
            new_std = wide_left                                  # 标准图放到原宽幅左格
        else:  # direction == 'left'
            # 标准图在宽幅左侧，宽幅左移
            new_wide_left = (wide_left[0], wide_left[1] - 1)
            new_wide_right = (wide_right[0], wide_right[1] - 1)
            new_std = wide_right
        
        # 放置宽幅图
        wide_img['grid_start'] = new_wide_left
        self.app.grid_contents[new_wide_left] = wide_img
        self.app.grid_contents[new_wide_right] = wide_img
        
        # 放置标准图
        std_img['grid_start'] = new_std
        self.app.grid_contents[new_std] = std_img
        
        # 重绘
        for key in (std_cell, wide_left, wide_right, new_wide_left, new_wide_right, new_std):
            if self._is_valid_cell(key):
                self.app.draw_grid_image(key)
    
    # ==================== 宽幅图移动 ====================
    
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
        
        if (C_target, D_target) == (A, B):
            return
        
        occ_c = self._get_occupant(C_target)
        occ_d = self._get_occupant(D_target)
        
        # ----- 偏移1格移动 -----
        moved_right = (C_target == B)      # 宽幅右移1格
        moved_left  = (D_target == A)       # 宽幅左移1格
        
        if moved_right:
            if occ_d is None:
                # 右移1格到空位
                self._do_wide_shift(A, B, C_target, D_target)
                self.app.update_status("✓ 宽幅移动成功")
                return
            elif occ_d.get('pic_type') == 'standard':
                # 右移1格，标准图在右侧相邻
                # 宽幅右移，标准图放到A
                self._adjacent_swap_wide_standard(A, B, C_target, D_target, D_target)
                self.app.update_status("✓ 宽幅与标准图交换成功")
                return
        
        if moved_left:
            if occ_c is None:
                # 左移1格到空位
                self._do_wide_shift(A, B, C_target, D_target)
                self.app.update_status("✓ 宽幅移动成功")
                return
            elif occ_c.get('pic_type') == 'standard':
                # 左移1格，标准图在左侧相邻
                self._adjacent_swap_wide_standard(A, B, C_target, D_target, C_target)
                self.app.update_status("✓ 宽幅与标准图交换成功")
                return
        
        # ----- 无重叠移动 -----
        c_wide = self._get_wide_region_at(C_target)
        d_wide = self._get_wide_region_at(D_target)
        
        target_is_wide = (c_wide is not None and c_wide == (C_target, D_target))
        blocked_by_c = (c_wide is not None and c_wide != (A, B) and c_wide != (C_target, D_target))
        blocked_by_d = (d_wide is not None and d_wide != (A, B) and d_wide != (C_target, D_target))
        
        if target_is_wide:
            self._swap_regions((A, B), (C_target, D_target))
            self.app.update_status("✓ 两张宽幅交换成功")
        elif not blocked_by_c and not blocked_by_d:
            c_ok = self._cell_empty(C_target) or (occ_c and occ_c.get('pic_type') == 'standard')
            d_ok = self._cell_empty(D_target) or (occ_d and occ_d.get('pic_type') == 'standard')
            if c_ok and d_ok:
                self._swap_regions((A, B), (C_target, D_target))
                self.app.update_status("✓ 宽幅移动成功")
            else:
                self.app.update_status("✗ 目标区域被占用")
        else:
            self.app.update_status("✗ 目标区域被其他宽幅占用")


    def _do_wide_shift(self, A, B, C_target, D_target):
        """宽幅图偏移1格移动（目标另一格为空）"""
        wide_img = self.app.grid_contents[A]
        
        self.app.grid_contents[A] = None
        self.app.grid_contents[B] = None
        self.app.grid_contents[C_target] = None
        self.app.grid_contents[D_target] = None
        
        wide_img['grid_start'] = C_target
        self.app.grid_contents[C_target] = wide_img
        self.app.grid_contents[D_target] = wide_img
        
        for key in (A, B, C_target, D_target):
            if self._is_valid_cell(key):
                self.app.draw_grid_image(key)


    def _adjacent_swap_wide_standard(self, A, B, C, D, std_cell):
        """
        相邻宽幅与标准图交换（宽幅偏移1格，标准图放到宽幅空出的格子）。
        std_cell 是目标区域中标准图所在的格子。
        """
        wide_img = self.app.grid_contents[A]
        std_img = self.app.grid_contents[std_cell]
        
        # 确定标准图的新位置（宽幅移走后空出的格子）
        if std_cell == D:
            # 标准图在右侧，宽幅右移，空出A
            new_std = A
        else:
            # 标准图在左侧，宽幅左移，空出B
            new_std = B
        
        # 清空
        for k in (A, B, C, D, std_cell):
            if self._is_valid_cell(k):
                self.app.grid_contents[k] = None
        
        # 放置宽幅
        wide_img['grid_start'] = C
        self.app.grid_contents[C] = wide_img
        self.app.grid_contents[D] = wide_img
        
        # 放置标准图
        std_img['grid_start'] = new_std
        self.app.grid_contents[new_std] = std_img
        
        for k in set([A, B, C, D, std_cell, new_std]):
            if self._is_valid_cell(k):
                self.app.draw_grid_image(k)
    
    # ==================== 区域交换 ====================
    
    def _swap_two_cells(self, key1, key2):
        """交换两个单格的内容"""
        img1 = self.app.grid_contents.get(key1)
        img2 = self.app.grid_contents.get(key2)
        
        self.app.grid_contents[key1] = None
        self.app.grid_contents[key2] = None
        
        if img1:
            img1['grid_start'] = key2
            self.app.grid_contents[key2] = img1
        if img2:
            img2['grid_start'] = key1
            self.app.grid_contents[key1] = img2
        
        self.app.draw_grid_image(key1)
        self.app.draw_grid_image(key2)
    
    def _swap_regions(self, region1, region2):
        """交换两个双格区域的内容，保持格子在区域内的相对位置"""
        keys1 = list(region1)
        keys2 = list(region2)
        
        # 收集原始状态
        contents1 = [self._get_occupant(k) for k in keys1]
        contents2 = [self._get_occupant(k) for k in keys2]
        
        # 清空
        for k in keys1 + keys2:
            self.app.grid_contents[k] = None
        
        # 按位置对应写入（region1 → region2, region2 → region1）
        for i in range(2):
            # region1的内容到region2
            img = contents1[i]
            if img is not None:
                # 宽幅图：只有左格才写入（右格是重复引用）
                if img.get('pic_type') == 'wide' and i == 0:
                    img['grid_start'] = keys2[0]
                    self.app.grid_contents[keys2[0]] = img
                    self.app.grid_contents[keys2[1]] = img
                elif img.get('pic_type') != 'wide':
                    img['grid_start'] = keys2[i]
                    self.app.grid_contents[keys2[i]] = img
            
            # region2的内容到region1
            img = contents2[i]
            if img is not None:
                if img.get('pic_type') == 'wide' and i == 0:
                    img['grid_start'] = keys1[0]
                    self.app.grid_contents[keys1[0]] = img
                    self.app.grid_contents[keys1[1]] = img
                elif img.get('pic_type') != 'wide':
                    img['grid_start'] = keys1[i]
                    self.app.grid_contents[keys1[i]] = img
        
        for k in keys1 + keys2:
            self.app.draw_grid_image(k)

    def _place_images_into_cells(self, images, target_keys):
        """将图片列表放入目标双格区域"""
        if not images:
            return
        
        if len(images) == 1 and images[0].get('pic_type') == 'wide':
            img = images[0]
            img['grid_start'] = target_keys[0]
            self.app.grid_contents[target_keys[0]] = img
            self.app.grid_contents[target_keys[1]] = img
        elif len(images) == 1:
            img = images[0]
            img['grid_start'] = target_keys[0]
            self.app.grid_contents[target_keys[0]] = img
            # 第二个格子保持空
        elif len(images) == 2:
            for i, img in enumerate(images):
                img['grid_start'] = target_keys[i]
                self.app.grid_contents[target_keys[i]] = img

    # ==================== 辅助查询方法 ====================
    
    def _cell_empty(self, key):
        return self.app.grid_contents.get(key) is None
    
    def _get_occupant(self, key):
        return self.app.grid_contents.get(key)
    
    def _is_valid_cell(self, key):
        return key in self.app.left_grids
    
    def _is_standard_at(self, key):
        img = self._get_occupant(key)
        return img is not None and img.get('pic_type') == 'standard'
    
    def _is_part_of_wide(self, key):
        return self._get_wide_region_at(key) is not None
    
    def _get_wide_region_at(self, key):
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
        if not self._is_valid_cell(C):
            return (None, None)
        row, col = C
        if col < self.app.grid_cols - 1:
            return (C, (row, col + 1))
        elif col > 0:
            return ((row, col - 1), C)
        else:
            return (None, None)
    
    # ==================== 坐标查找 ====================
    
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