import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import os
import datetime
import math

class DragToGridApp:
    """图片拼图工具 - 根据图片数量自动计算网格形状"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("图片拼图工具 - 自动形状拼合")
        self.root.geometry("1400x800")
        self.root.configure(bg='#2c3e50')
        
        # 图片尺寸（左侧格子用大尺寸，右侧用小尺寸示意）
        self.big_width = 158
        self.big_height = 251
        
        # 右侧小图尺寸
        self.small_width = 80
        self.small_height = int(80 * 1.59)  # 127
        
        # 输出目录
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 网格参数
        self.grid_rows = 2
        self.grid_cols = 2
        self.grid_count = 4
        
        # 左侧区域数据
        self.left_grids = {}  # {(row, col): (x1,y1,x2,y2)}
        self.grid_contents = {}  # {(row, col): img_data}
        self.grid_images = {}    # {(row, col): image_item}
        
        # 右侧区域数据（按文件夹分组）
        self.folder_images = {}  # {folder_name: [img_data_list]}
        self.all_images = []     # 所有图片的扁平列表
        
        # 拖拽状态
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
        
        # 创建界面
        self.setup_ui()
        
        # 加载图片
        self.load_images_from_folder()
        
        # 自动计算形状
        self.auto_calculate_shape()
        
        # 绘制左侧格子
        self.draw_left_grids()
        
        # 绘制右侧区域
        self.draw_right_sections()
    
    def auto_calculate_shape(self):
        """根据所有图片总数量自动计算最佳形状（保留右侧图片，清空左侧）"""
        # 计算总图片数量 = 右侧待放置 + 左侧已放置
        left_count = sum(1 for img in self.grid_contents.values() if img is not None)
        total_count = len(self.all_images) + left_count
        
        if total_count == 0:
            self.grid_rows = 2
            self.grid_cols = 2
            self.grid_count = 4
            # 更新控件
            if hasattr(self, 'rows_var'):
                self.rows_var.set(self.grid_rows)
                self.cols_var.set(self.grid_cols)
            # 重新初始化左侧
            self.init_grids()
            self.left_grids = {}
            self.draw_left_grids()
            self.update_status("没有图片，使用默认2x2网格")
            return
        
        n = max(1, int(total_count ** 0.5))
        self.grid_rows = n
        self.grid_cols = (total_count + self.grid_rows - 1) // self.grid_rows
        self.grid_count = self.grid_rows * self.grid_cols
        
        # 更新控件
        if hasattr(self, 'rows_var'):
            self.rows_var.set(self.grid_rows)
            self.cols_var.set(self.grid_cols)
        
        # 将左侧所有图片放回右侧
        for key, img_data in list(self.grid_contents.items()):
            if img_data is not None:
                folder_name = img_data.get('folder', '已放回图片')
                if folder_name not in self.folder_images:
                    self.folder_images[folder_name] = []
                if img_data not in self.folder_images[folder_name]:
                    self.folder_images[folder_name].append(img_data)
                if img_data not in self.all_images:
                    self.all_images.append(img_data)
        
        # 重新初始化左侧格子
        self.init_grids()
        self.left_grids = {}
        
        # 重新绘制
        self.draw_left_grids()
        self.draw_right_sections()
        
        self.update_status(f"自动设置形状: {self.grid_rows}行 x {self.grid_cols}列 = {self.grid_count}格 (共{total_count}张图片)")
    
    def init_grids(self):
        """初始化格子数据结构"""
        new_contents = {}
        new_images = {}
        
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                key = (row, col)
                new_contents[key] = None
                new_images[key] = None
        
        self.grid_contents = new_contents
        self.grid_images = new_images
    
    def setup_ui(self):
        """创建界面布局"""
        # 顶部按钮框架
        button_frame = tk.Frame(self.root, bg='#2c3e50')
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=10)
        
        # 导入按钮
        self.import_btn = tk.Button(
            button_frame, text="📁 导入图片", font=('Arial', 11),
            bg='#27ae60', fg='white', padx=15, pady=5, cursor='hand2',
            command=self.import_image
        )
        self.import_btn.pack(side=tk.LEFT, padx=5)
        
        # 输出按钮
        self.output_btn = tk.Button(
            button_frame, text="💾 输出拼合图片", font=('Arial', 11),
            bg='#3498db', fg='white', padx=15, pady=5, cursor='hand2',
            command=self.output_composite
        )
        self.output_btn.pack(side=tk.LEFT, padx=5)
        
        # 自动放置按钮
        self.auto_btn = tk.Button(
            button_frame, text="🎯 自动放置图片", font=('Arial', 11),
            bg='#9b59b6', fg='white', padx=15, pady=5, cursor='hand2',
            command=self.auto_place_images
        )
        self.auto_btn.pack(side=tk.LEFT, padx=5)
        
        # 重置按钮
        self.reset_btn = tk.Button(
            button_frame, text="🔄 重置所有", font=('Arial', 11),
            bg='#e74c3c', fg='white', padx=15, pady=5, cursor='hand2',
            command=self.reset_all
        )
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        # 手动调节形状
        shape_frame = tk.Frame(button_frame, bg='#2c3e50')
        shape_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(shape_frame, text="行数:", font=('Arial', 11),
                bg='#2c3e50', fg='white').pack(side=tk.LEFT)
        
        self.rows_var = tk.IntVar(value=self.grid_rows)
        self.rows_spinbox = tk.Spinbox(
            shape_frame, from_=1, to=20, width=3,
            textvariable=self.rows_var,
            font=('Arial', 11),
            command=self.on_shape_change
        )
        self.rows_spinbox.pack(side=tk.LEFT, padx=5)
        
        tk.Label(shape_frame, text="列数:", font=('Arial', 11),
                bg='#2c3e50', fg='white').pack(side=tk.LEFT, padx=(10, 0))
        
        self.cols_var = tk.IntVar(value=self.grid_cols)
        self.cols_spinbox = tk.Spinbox(
            shape_frame, from_=1, to=20, width=3,
            textvariable=self.cols_var,
            font=('Arial', 11),
            command=self.on_shape_change
        )
        self.cols_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 自动形状按钮
        self.auto_shape_btn = tk.Button(
            shape_frame, text="📐 自动计算", font=('Arial', 10),
            bg='#1abc9c', fg='white', padx=10, pady=3, cursor='hand2',
            command=self.auto_calculate_shape
        )
        self.auto_shape_btn.pack(side=tk.LEFT, padx=10)
        
        # 主内容区域（左右分割，左侧70%右侧30%）
        main_paned = tk.PanedWindow(self.root, bg='#2c3e50', sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧区域（占大部分空间）
        left_frame = tk.Frame(main_paned, bg='#2c3e50')
        main_paned.add(left_frame, width=900)
        
        # 左侧画布加滚动条
        left_canvas_frame = tk.Frame(left_frame, bg='#2c3e50')
        left_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        left_scrollbar_y = tk.Scrollbar(left_canvas_frame, orient=tk.VERTICAL)
        left_scrollbar_x = tk.Scrollbar(left_canvas_frame, orient=tk.HORIZONTAL)
        
        self.left_canvas = tk.Canvas(left_canvas_frame, bg='#34495e', highlightthickness=0,
                                      yscrollcommand=left_scrollbar_y.set,
                                      xscrollcommand=left_scrollbar_x.set)
        
        left_scrollbar_y.config(command=self.left_canvas.yview)
        left_scrollbar_x.config(command=self.left_canvas.xview)
        
        left_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        left_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 右侧区域（只显示2-3列小图宽度）
        right_frame = tk.Frame(main_paned, bg='#3d566e')
        main_paned.add(right_frame, width=300)
        
        self.right_canvas = tk.Canvas(right_frame, bg='#3d566e', highlightthickness=0)
        right_scrollbar = tk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_canvas.yview)
        self.right_canvas.configure(yscrollcommand=right_scrollbar.set)
        
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 右侧内部框架
        self.right_inner = tk.Frame(self.right_canvas, bg='#3d566e')
        self.right_canvas.create_window((0, 0), window=self.right_inner, anchor=tk.NW)
        
        self.right_inner.bind("<Configure>", self.on_right_inner_configure)
        self.right_canvas.bind("<Configure>", self.on_right_canvas_configure)
        self.right_canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # 状态栏
        self.status_label = tk.Label(
            self.root, text="拖拽图片到左侧格子 | 图片数量除以2开根号自动计算形状",
            font=('Arial', 10), bg='#2c3e50', fg='#ecf0f1', anchor=tk.W
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        # 绑定全局释放事件
        self.root.bind("<ButtonRelease-1>", self.on_global_release)
        self.left_canvas.bind("<ButtonRelease-1>", self.on_global_release)

    def on_shape_change(self):
        """手动调整行数列数（保留右侧图片，清空左侧）"""
        self.grid_rows = self.rows_var.get()
        self.grid_cols = self.cols_var.get()
        self.grid_count = self.grid_rows * self.grid_cols
        
        # 将左侧所有图片放回右侧
        for key, img_data in list(self.grid_contents.items()):
            if img_data is not None:
                folder_name = img_data.get('folder', '已放回图片')
                if folder_name not in self.folder_images:
                    self.folder_images[folder_name] = []
                if img_data not in self.folder_images[folder_name]:
                    self.folder_images[folder_name].append(img_data)
                if img_data not in self.all_images:
                    self.all_images.append(img_data)
        
        # 重新初始化左侧格子（清空）
        self.init_grids()
        self.left_grids = {}
        
        # 重新绘制左侧格子
        self.draw_left_grids()
        
        # 刷新右侧显示（不清除右侧图片）
        self.draw_right_sections()
        
        self.update_status(f"已调整形状为: {self.grid_rows}行 x {self.grid_cols}列，左侧已清空")

    def resize_to_big(self, pil_image):
        """拉伸到大尺寸"""
        return pil_image.resize((self.big_width, self.big_height), Image.Resampling.LANCZOS)
    
    def resize_to_small(self, pil_image):
        """拉伸到小尺寸"""
        return pil_image.resize((self.small_width, self.small_height), Image.Resampling.LANCZOS)
    
    def load_images_from_folder(self):
        """从 imgs 文件夹加载所有图片（按子文件夹分组）"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        imgs_dir = os.path.join(current_dir, "imgs")
        
        if not os.path.exists(imgs_dir):
            os.makedirs(imgs_dir)
            self.update_status(f"已创建 imgs 文件夹")
            return
        
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
        self.folder_images = {}
        self.all_images = []
        
        # 遍历所有子文件夹
        for item in sorted(os.listdir(imgs_dir)):
            folder_path = os.path.join(imgs_dir, item)
            if os.path.isdir(folder_path):
                folder_name = item
                self.folder_images[folder_name] = []
                
                for img_file in sorted(os.listdir(folder_path)):
                    if img_file.lower().endswith(image_extensions):
                        try:
                            img_path = os.path.join(folder_path, img_file)
                            pil_img = Image.open(img_path)
                            
                            big_img = self.resize_to_big(pil_img)
                            small_img = self.resize_to_small(pil_img)
                            
                            big_tk = ImageTk.PhotoImage(big_img)
                            small_tk = ImageTk.PhotoImage(small_img)
                            
                            img_data = {
                                'pil': big_img,
                                'tk_big': big_tk,
                                'tk_small': small_tk,
                                'label': img_file,
                                'path': img_path,
                                'filename': img_file,
                                'folder': folder_name,
                                'item': None
                            }
                            self.folder_images[folder_name].append(img_data)
                            self.all_images.append(img_data)
                            
                        except Exception as e:
                            print(f"加载失败 {img_file}: {e}")
        
        if not self.folder_images:
            self.update_status("imgs 文件夹中没有子文件夹或图片")
    
    def draw_left_grids(self):
        """绘制左侧格子（紧贴排列，支持滚动）"""
        self.left_canvas.delete("all")
        
        # 计算整体网格尺寸
        total_width = self.grid_cols * self.big_width
        total_height = self.grid_rows * self.big_height
        
        # 设置画布滚动区域
        self.left_canvas.configure(scrollregion=(0, 0, total_width + 20, total_height + 20))
        
        # 居中显示（如果画布比内容大才居中）
        canvas_width = self.left_canvas.winfo_width()
        canvas_height = self.left_canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = 900
            canvas_height = 600
        
        start_x = (canvas_width - total_width) // 2 if canvas_width > total_width else 10
        start_y = (canvas_height - total_height) // 2 if canvas_height > total_height else 10
        
        # 颜色列表
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336', 
                  '#00BCD4', '#795548', '#607D8B', '#E91E63', '#8BC34A']
        
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x1 = start_x + col * self.big_width
                y1 = start_y + row * self.big_height
                x2 = x1 + self.big_width
                y2 = y1 + self.big_height
                
                key = (row, col)
                self.left_grids[key] = (x1, y1, x2, y2)
                
                color_idx = (row * self.grid_cols + col) % len(colors)
                color = colors[color_idx]
                
                self.left_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline=color, fill='#2c3e50', width=2,
                    tags=('grid', f'grid_{row}_{col}')
                )
                
                self.left_canvas.create_text(
                    x1 + self.big_width//2, y1 + 20,
                    text=f"{row+1},{col+1}",
                    font=('Arial', 10),
                    fill=color,
                    tags=('grid',)
                )
        
        # 恢复格子中的图片
        for key in self.left_grids.keys():
            if self.grid_contents.get(key):
                self.draw_grid_image(key)
    
    def draw_grid_image(self, key):
        """在指定格子中绘制图片"""
        if self.grid_images.get(key):
            self.left_canvas.delete(self.grid_images[key])
        
        content = self.grid_contents.get(key)
        if content is None:
            return
        
        if key not in self.left_grids:
            return
        
        x1, y1, x2, y2 = self.left_grids[key]
        
        img_item = self.left_canvas.create_image(
            x1, y1, anchor=tk.NW, image=content['tk_big'], tags=('grid_image',)
        )
        
        self.grid_images[key] = img_item
        
        # 绑定拖拽事件
        self.left_canvas.tag_bind(img_item, "<ButtonPress-1>", 
                                lambda e, k=key: self.on_grid_drag_start(e, k))
        self.left_canvas.tag_bind(img_item, "<B1-Motion>", self.on_drag_move)
    
    def draw_right_sections(self):
        """绘制右侧分区域图片（每个文件夹一个独立滚动区域）"""
        # 清空右侧
        for widget in self.right_inner.winfo_children():
            widget.destroy()
        
        for folder_name, images in self.folder_images.items():
            if not images:
                continue
            
            # 文件夹标题
            title_frame = tk.Frame(self.right_inner, bg='#3d566e')
            title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
            
            tk.Label(
                title_frame, text=f"📁 {folder_name} ({len(images)}张)",
                font=('Arial', 12, 'bold'), bg='#3d566e', fg='#ecf0f1'
            ).pack(side=tk.LEFT)
            
            # 垂直布局，每行显示2-3张
            container = tk.Frame(self.right_inner, bg='#3d566e')
            container.pack(fill=tk.X, padx=10, pady=5)
            
            # 计算每行显示数量（根据宽度自动调整）
            container_width = self.right_canvas.winfo_width()
            if container_width <= 1:
                container_width = 280
            cols_per_row = max(1, container_width // (self.small_width + 15))
            
            # 网格布局
            for idx, img_data in enumerate(images):
                row = idx // cols_per_row
                col = idx % cols_per_row
                
                frame = tk.Frame(container, bg='#3d566e')
                frame.grid(row=row, column=col, padx=5, pady=5, sticky='n')
                
                img_label = tk.Label(frame, image=img_data['tk_small'], bg='#3d566e', cursor='hand2')
                img_label.image = img_data['tk_small']
                img_label.pack()
                
                text = img_data['label'][:12]
                tk.Label(frame, text=text, bg='#3d566e', fg='white', font=('Arial', 8)).pack()
                
                img_data['item'] = img_label
                img_data['frame'] = frame
                
                img_label.bind("<ButtonPress-1>", 
                               lambda e, f=folder_name, i=idx: self.on_small_drag_start(e, f, i))
                img_label.bind("<B1-Motion>", self.on_drag_move)
            
            # 让容器自适应内容
            container.update_idletasks()
    
    def on_small_drag_start(self, event, folder_name, idx):
        """开始拖拽右侧小图"""
        img_data = self.folder_images[folder_name][idx]
        
        # 创建浮动窗口
        self.drag_window = tk.Toplevel(self.root)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes('-topmost', True)
        
        drag_img = ImageTk.PhotoImage(img_data['pil'].resize((self.big_width, self.big_height), Image.Resampling.LANCZOS))
        self.drag_label = tk.Label(self.drag_window, image=drag_img, bg='#3d566e')
        self.drag_label.image = drag_img
        self.drag_label.pack()
        
        x = event.widget.winfo_rootx() - 10
        y = event.widget.winfo_rooty() - 10
        self.drag_window.geometry(f"+{x}+{y}")
        
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
    
    def on_grid_drag_start(self, event, key):
        """开始拖拽格子中的图片"""
        content = self.grid_contents.get(key)
        if content is None:
            return
        
        # 创建浮动窗口
        self.drag_window = tk.Toplevel(self.root)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes('-topmost', True)
        
        drag_label = tk.Label(self.drag_window, image=content['tk_big'], bg='#34495e')
        drag_label.pack()
        
        x = event.x_root - 10
        y = event.y_root - 10
        self.drag_window.geometry(f"+{x}+{y}")
        
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
    
    def on_drag_move(self, event):
        """拖拽移动"""
        if self.drag_data.get("img_data") is None:
            return
        if hasattr(self, 'drag_window') and self.drag_window:
            x = event.x_root - 10
            y = event.y_root - 10
            self.drag_window.geometry(f"+{x}+{y}")
    
    def on_global_release(self, event):
        """释放鼠标"""
        if self.drag_data.get("img_data") is None:
            return
        
        # 获取鼠标位置
        mouse_x = event.x_root
        mouse_y = event.y_root
        
        # 检查是否在左侧格子内
        target_key = None
        for key, (x1, y1, x2, y2) in self.left_grids.items():
            canvas_x = self.left_canvas.winfo_rootx() + x1
            canvas_y = self.left_canvas.winfo_rooty() + y1
            canvas_x2 = self.left_canvas.winfo_rootx() + x2
            canvas_y2 = self.left_canvas.winfo_rooty() + y2
            
            if canvas_x <= mouse_x <= canvas_x2 and canvas_y <= mouse_y <= canvas_y2:
                target_key = key
                break
        
        # 检查是否在右侧区域
        right_x = self.right_canvas.winfo_rootx()
        right_y = self.right_canvas.winfo_rooty()
        right_x2 = right_x + self.right_canvas.winfo_width()
        right_y2 = right_y + self.right_canvas.winfo_height()
        is_in_right = (right_x <= mouse_x <= right_x2 and right_y <= mouse_y <= right_y2)
        
        # 处理放置
        if self.drag_data["type"] == "unplaced":
            img_data = self.drag_data["img_data"]
            
            if target_key is not None and self.grid_contents.get(target_key) is None:
                self.place_image_to_grid(img_data, target_key)
                row, col = target_key
                self.update_status(f"✓ {img_data['label']} 已放入格子 ({row+1},{col+1})")
            else:
                self.update_status("✗ 放置失败：格子已被占用或无效")
        
        elif self.drag_data["type"] == "grid":
            source_key = self.drag_data["source_key"]
            img_data = self.drag_data["img_data"]
            
            if target_key is not None and target_key != source_key:
                if self.grid_contents.get(target_key) is None:
                    self.grid_contents[target_key] = img_data
                    self.grid_contents[source_key] = None
                    self.draw_grid_image(target_key)
                    self.draw_grid_image(source_key)
                    self.update_status(f"✓ 图片已移动")
                else:
                    target_img = self.grid_contents[target_key]
                    self.grid_contents[source_key] = target_img
                    self.grid_contents[target_key] = img_data
                    self.draw_grid_image(source_key)
                    self.draw_grid_image(target_key)
                    self.update_status(f"🔄 已交换两张图片")
            elif is_in_right:
                self.return_image_to_right(img_data, source_key)
                self.update_status(f"✓ {img_data['label']} 已放回右侧")
            else:
                self.update_status("✗ 放置位置无效，图片未移动")
        
        # 关闭浮动窗口
        if hasattr(self, 'drag_window') and self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
        
        # 清空拖拽数据
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

    def place_image_to_grid(self, img_data, key):
        """将图片放置到指定格子中（从右侧移除）"""
        # 从右侧文件夹中移除
        folder = img_data['folder']
        if folder in self.folder_images:
            if img_data in self.folder_images[folder]:
                idx = self.folder_images[folder].index(img_data)
                self.folder_images[folder].pop(idx)
        
        # 从 all_images 中移除（关键修复）
        if img_data in self.all_images:
            self.all_images.remove(img_data)
        
        # 放入格子
        self.grid_contents[key] = img_data
        self.draw_grid_image(key)
        self.draw_right_sections()

    def return_image_to_right(self, img_data, source_key):
        """将图片从左侧格子放回右侧"""
        self.grid_contents[source_key] = None
        if self.grid_images.get(source_key):
            self.left_canvas.delete(self.grid_images[source_key])
            self.grid_images[source_key] = None
        
        folder_name = img_data.get('folder', '已放回图片')
        
        if folder_name not in self.folder_images:
            self.folder_images[folder_name] = []
        
        self.folder_images[folder_name].append(img_data)
        self.all_images.append(img_data)
        self.draw_right_sections()
    
    def auto_place_images(self):
        """自动放置图片（按顺序填充所有格子）"""
        # 获取所有未放置的图片（右侧的图片）
        if not self.all_images:
            self.update_status("没有图片可放置")
            return
        
        # 获取所有空格子（按行优先顺序排序）
        empty_keys = sorted([key for key in self.left_grids.keys() if self.grid_contents.get(key) is None])
        
        if not empty_keys:
            self.update_status("所有格子都已满，请先重置")
            return
        
        # 按顺序取右侧图片（保持原有顺序）
        images_to_place = self.all_images[:len(empty_keys)]
        
        # 按顺序放置到空格子
        for i, img_data in enumerate(images_to_place):
            key = empty_keys[i]
            self.place_image_to_grid(img_data, key)
        
        self.update_status(f"已自动放置 {len(images_to_place)} 张图片")
    
    def output_composite(self):
        """输出拼合图片（按实际网格布局输出）"""
        has_images = any(self.grid_contents.get(key) is not None for key in self.left_grids.keys())
        if not has_images:
            self.update_status("左侧格子为空，请先放置图片")
            return
        
        output_width = self.grid_cols * self.big_width
        output_height = self.grid_rows * self.big_height
        
        final_image = Image.new('RGB', (output_width, output_height), 'white')
        
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                key = (row, col)
                if self.grid_contents.get(key):
                    x = col * self.big_width
                    y = row * self.big_height
                    final_image.paste(self.grid_contents[key]['pil'], (x, y))
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"composite_{self.grid_rows}x{self.grid_cols}_{timestamp}.png"
        save_path = os.path.join(self.output_dir, filename)
        final_image.save(save_path)
        self.update_status(f"已保存: {filename} ({self.grid_rows}行 x {self.grid_cols}列)")
    
    def import_image(self):
        """导入图片"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if not file_path:
            return
        
        if self.folder_images:
            first_folder = list(self.folder_images.keys())[0]
        else:
            first_folder = "导入图片"
            self.folder_images[first_folder] = []
        
        pil_img = Image.open(file_path)
        big_img = self.resize_to_big(pil_img)
        small_img = self.resize_to_small(pil_img)
        
        img_data = {
            'pil': big_img,
            'tk_big': ImageTk.PhotoImage(big_img),
            'tk_small': ImageTk.PhotoImage(small_img),
            'label': os.path.basename(file_path),
            'path': file_path,
            'filename': os.path.basename(file_path),
            'folder': first_folder,
            'item': None
        }
        
        self.folder_images[first_folder].append(img_data)
        self.all_images.append(img_data)
        self.draw_right_sections()
        self.update_status(f"已导入: {img_data['label']}")
    
    def reset_all(self):
        """重置（不清除右侧图片，只清空左侧）"""
        # 将左侧所有图片放回右侧
        for key, img_data in list(self.grid_contents.items()):
            if img_data is not None:
                folder_name = img_data.get('folder', '已放回图片')
                if folder_name not in self.folder_images:
                    self.folder_images[folder_name] = []
                if img_data not in self.folder_images[folder_name]:
                    self.folder_images[folder_name].append(img_data)
                if img_data not in self.all_images:
                    self.all_images.append(img_data)
        
        # 清空左侧格子
        self.init_grids()
        self.left_grids = {}
        
        # 重新绘制
        self.draw_left_grids()
        self.draw_right_sections()
        
        # 自动计算形状
        self.auto_calculate_shape()
        
        self.update_status("已重置，右侧图片保持不变")
    
    def on_right_inner_configure(self, event):
        self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
    
    def on_right_canvas_configure(self, event):
        self.right_canvas.itemconfig(1, width=event.width)
        # 右侧宽度变化时重新布局
        self.draw_right_sections()
    
    def on_mousewheel(self, event):
        self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def update_status(self, msg):
        self.status_label.config(text=msg)


def main():
    root = tk.Tk()
    app = DragToGridApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()