"""拖拽处理模块"""

import tkinter as tk
from PIL import Image, ImageTk
from constants import BIG_WIDTH, BIG_HEIGHT


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
    
    def start_grid_drag(self, event, key):
        """开始拖拽格子中的图片"""
        content = self.app.grid_contents.get(key)
        if content is None:
            return
        
        self._create_drag_window(content['tk_big'], event.x_root, event.y_root)
        
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
            "img_data": content
        }
    
    def start_small_drag(self, event, folder_name, idx):
        """开始拖拽右侧小图"""
        img_data = self.app.folder_images[folder_name][idx]
        
        # 创建大图预览用于拖拽
        from PIL import Image as PILImage  # 另一种导入方式，避免命名冲突
        drag_img = ImageTk.PhotoImage(
            img_data['pil'].resize((BIG_WIDTH, BIG_HEIGHT), PILImage.Resampling.LANCZOS)
        )
        self._create_drag_window(drag_img, event.x_root, event.y_root)
        self.drag_label.image = drag_img  # 保持引用
        
        self.drag_data = {
            "item": event.widget,
            "type": "unplaced",
            "source_folder": folder_name,
            "source_index": idx,
            "source_key": None,
            "start_x": event.x_root,
            "start_y": event.y_root,
            "orig_x": event.widget.winfo_rootx(),
            "orig_y": event.widget.winfo_rooty(),
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
        """释放放置"""
        if self.drag_data.get("img_data") is None:
            return
        
        mouse_x, mouse_y = event.x_root, event.y_root
        
        # 查找目标格子
        target_key = self._find_target_grid(mouse_x, mouse_y)
        
        # 检查是否在右侧区域
        is_in_right = self._is_in_right_area(mouse_x, mouse_y)
        
        # 执行放置
        if self.drag_data["type"] == "unplaced":
            self._handle_unplaced_drop(target_key)
        elif self.drag_data["type"] == "grid":
            self._handle_grid_drop(target_key, is_in_right)
        
        # 清理
        self._cleanup_drag()
    
    def _find_target_grid(self, mouse_x, mouse_y):
        """查找鼠标所在的格子"""
        for key, (x1, y1, x2, y2) in self.app.left_grids.items():
            canvas_x = self.app.left_canvas.winfo_rootx() + x1
            canvas_y = self.app.left_canvas.winfo_rooty() + y1
            canvas_x2 = self.app.left_canvas.winfo_rootx() + x2
            canvas_y2 = self.app.left_canvas.winfo_rooty() + y2
            
            if canvas_x <= mouse_x <= canvas_x2 and canvas_y <= mouse_y <= canvas_y2:
                return key
        return None
    
    def _is_in_right_area(self, mouse_x, mouse_y):
        """检查鼠标是否在右侧区域"""
        right_x = self.app.right_canvas.winfo_rootx()
        right_y = self.app.right_canvas.winfo_rooty()
        right_x2 = right_x + self.app.right_canvas.winfo_width()
        right_y2 = right_y + self.app.right_canvas.winfo_height()
        return (right_x <= mouse_x <= right_x2 and right_y <= mouse_y <= right_y2)
    
    def _handle_unplaced_drop(self, target_key):
        """处理未放置图片的拖拽释放"""
        img_data = self.drag_data["img_data"]
        
        if target_key is not None and self.app.grid_contents.get(target_key) is None:
            self.app.place_image_to_grid(img_data, target_key)
            row, col = target_key
            self.app.update_status(f"✓ {img_data['label']} 已放入格子 ({row+1},{col+1})")
        else:
            self.app.update_status("✗ 放置失败：格子已被占用或无效")
    
    def _handle_grid_drop(self, target_key, is_in_right):
        """处理格子图片的拖拽释放"""
        source_key = self.drag_data["source_key"]
        img_data = self.drag_data["img_data"]
        
        if target_key is not None and target_key != source_key:
            if self.app.grid_contents.get(target_key) is None:
                # 移动到空格子
                self.app.grid_contents[target_key] = img_data
                self.app.grid_contents[source_key] = None
                self.app.draw_grid_image(target_key)
                self.app.draw_grid_image(source_key)
                self.app.update_status(f"✓ 图片已移动")
            else:
                # 交换
                target_img = self.app.grid_contents[target_key]
                self.app.grid_contents[source_key] = target_img
                self.app.grid_contents[target_key] = img_data
                self.app.draw_grid_image(source_key)
                self.app.draw_grid_image(target_key)
                self.app.update_status(f"🔄 已交换两张图片")
        elif is_in_right:
            self.app.return_image_to_right(img_data, source_key)
            self.app.update_status(f"✓ {img_data['label']} 已放回右侧")
        else:
            self.app.update_status("✗ 放置位置无效，图片未移动")
    
    def _cleanup_drag(self):
        """清理拖拽相关资源"""
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
        
        self.drag_data = {
            "item": None, "type": None, "source_folder": None,
            "source_index": None, "source_key": None, "start_x": 0,
            "start_y": 0, "orig_x": 0, "orig_y": 0, "img_data": None
        }