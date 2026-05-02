"""主应用类"""

import tkinter as tk
from tkinter import filedialog, ttk
import os
import datetime
from PIL import Image, ImageTk

from constants import *
from drag_handler import DragHandler


class PicturePuzzleApp:
    """图片拼图工具主应用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("图片拼图工具 - 自动形状拼合")
        self.root.geometry("1400x800")
        self.root.configure(bg=BG_COLOR)
        
        # 输出目录
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.base_dir, OUTPUT_DIR_NAME)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 网格参数
        self.grid_rows = DEFAULT_ROWS
        self.grid_cols = DEFAULT_COLS
        self.grid_count = 4
        
        # 预览尺寸（会根据区域宽度自动计算）
        self.preview_width = 158
        self.preview_height = 251

        # 输出尺寸
        self.output_scale_percent = DEFAULT_SCALE_PERCENT
        self.output_width = BASE_OUTPUT_WIDTH
        self.output_height = BASE_OUTPUT_HEIGHT
        
        # 数据结构
        self.left_grids = {}        # {(row, col): (x1,y1,x2,y2)}
        self.grid_contents = {}     # {(row, col): img_data}
        self.grid_images = {}       # {(row, col): image_item}
        self.folder_images = {}     # {folder_name: [img_data_list]}
        self.all_images = []        # 所有未放置的图片
        
        # 初始化拖拽处理器
        self.drag_handler = DragHandler(self)
        
        # 创建界面
        self._setup_ui()
        
        # 自动计算预览尺寸
        self.root.update_idletasks()
        self._calculate_preview_size()
        
        # 加载图片并初始化
        self._load_images_from_folder()
        self.auto_calculate_shape()
        self._draw_left_grids()
        self._draw_right_sections()
    
    def _setup_ui(self):
        """创建界面布局"""
        # 顶部按钮框架
        button_frame = tk.Frame(self.root, bg=BG_COLOR)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=10)
        
        # 按钮
        buttons = [
            ("📁 导入图片", '#27ae60', self._import_image),
            ("💾 输出拼合图片", '#3498db', self.output_composite),
            ("🎯 自动放置图片", '#9b59b6', self.auto_place_images),
            ("🔄 重置所有", '#e74c3c', self.reset_all),
        ]
        for text, color, cmd in buttons:
            btn = tk.Button(button_frame, text=text, font=('Arial', 11),
                           bg=color, fg='white', padx=15, pady=5, cursor='hand2',
                           command=cmd)
            btn.pack(side=tk.LEFT, padx=5)

        # 输出尺寸控制
        output_frame = tk.Frame(button_frame, bg=BG_COLOR)
        output_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(output_frame, text="输出尺寸:", font=('Arial', 11),
                bg=BG_COLOR, fg='white').pack(side=tk.LEFT)

        self.output_scale_var = tk.IntVar(value=self.output_scale_percent)
        scale_slider = tk.Scale(output_frame, from_=MIN_SCALE_PERCENT, to=MAX_SCALE_PERCENT,
                                orient=tk.HORIZONTAL, length=150,
                                variable=self.output_scale_var,
                                command=self._on_output_scale_change,
                                bg=BG_COLOR, fg='white', highlightthickness=0)
        scale_slider.pack(side=tk.LEFT, padx=5)

        self.output_scale_label = tk.Label(output_frame, text="100%", font=('Arial', 10),
                                        bg=BG_COLOR, fg='white')
        self.output_scale_label.pack(side=tk.LEFT, padx=5)
        
        # 形状调节
        shape_frame = tk.Frame(button_frame, bg=BG_COLOR)
        shape_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(shape_frame, text="行数:", font=('Arial', 11),
                bg=BG_COLOR, fg='white').pack(side=tk.LEFT)
        
        self.rows_var = tk.IntVar(value=self.grid_rows)
        self.rows_spinbox = tk.Spinbox(shape_frame, from_=1, to=20, width=3,
                                        textvariable=self.rows_var,
                                        font=('Arial', 11),
                                        command=self._on_shape_change)
        self.rows_spinbox.pack(side=tk.LEFT, padx=5)
        
        tk.Label(shape_frame, text="列数:", font=('Arial', 11),
                bg=BG_COLOR, fg='white').pack(side=tk.LEFT, padx=(10, 0))
        
        self.cols_var = tk.IntVar(value=self.grid_cols)
        self.cols_spinbox = tk.Spinbox(shape_frame, from_=1, to=20, width=3,
                                        textvariable=self.cols_var,
                                        font=('Arial', 11),
                                        command=self._on_shape_change)
        self.cols_spinbox.pack(side=tk.LEFT, padx=5)
        
        tk.Button(shape_frame, text="📐 自动计算", font=('Arial', 10),
                 bg='#1abc9c', fg='white', padx=10, pady=3, cursor='hand2',
                 command=self.auto_calculate_shape).pack(side=tk.LEFT, padx=10)
        
        # 主内容区域
        main_paned = tk.PanedWindow(self.root, bg=BG_COLOR, sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ========== 左侧区域 ==========
        left_frame = tk.Frame(main_paned, bg=BG_COLOR)
        main_paned.add(left_frame, width=900)
        
        left_canvas_frame = tk.Frame(left_frame, bg=BG_COLOR)
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

        self.left_canvas.bind("<MouseWheel>", self._on_left_mousewheel)
        self.left_canvas.bind("<Enter>", lambda e: self.left_canvas.focus_set())
        self.left_canvas.bind("<Configure>", self._on_left_canvas_resize)
        
        # ========== 右侧区域（直接在 Canvas 上绘制，与左侧结构一致）==========
        right_frame = tk.Frame(main_paned, bg=RIGHT_BG_COLOR)
        main_paned.add(right_frame, width=300)
        
        right_canvas_frame = tk.Frame(right_frame, bg=RIGHT_BG_COLOR)
        right_canvas_frame.pack(fill=tk.BOTH, expand=True)

        right_scrollbar_y = tk.Scrollbar(right_canvas_frame, orient=tk.VERTICAL)
        right_scrollbar_x = tk.Scrollbar(right_canvas_frame, orient=tk.HORIZONTAL)

        self.right_canvas = tk.Canvas(right_canvas_frame, bg=RIGHT_BG_COLOR, highlightthickness=0,
                                    yscrollcommand=right_scrollbar_y.set,
                                    xscrollcommand=right_scrollbar_x.set)

        right_scrollbar_y.config(command=self.right_canvas.yview)
        right_scrollbar_x.config(command=self.right_canvas.xview)
        right_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        right_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右侧滚轮支持
        self.right_canvas.bind("<MouseWheel>", self._on_right_mousewheel)
        self.right_canvas.bind("<Enter>", lambda e: self.right_canvas.focus_set())
        self.right_canvas.bind("<Configure>", self._on_right_canvas_resize)
        
        # 状态栏
        self.status_label = tk.Label(self.root, text="拖拽图片到左侧格子 | 自动计算形状",
                                      font=('Arial', 10), bg=BG_COLOR, fg='#ecf0f1', anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)

        status_frame = tk.Frame(self.root, bg=BG_COLOR)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)

        self.status_label = tk.Label(status_frame, text="拖拽图片到左侧格子 | 自动计算形状",
                                    font=('Arial', 10), bg=BG_COLOR, fg='#ecf0f1', anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_bar = ttk.Progressbar(status_frame, length=200, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT)
        
        # 绑定释放事件
        self.root.bind("<ButtonRelease-1>", self.drag_handler.on_drop)
        self.left_canvas.bind("<ButtonRelease-1>", self.drag_handler.on_drop)

    def _calculate_preview_size(self):
        """根据左侧区域宽度和列数自动计算格子尺寸"""
        # 获取左侧画布宽度
        canvas_width = self.left_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 900
        
        # 水平方向留出 40px 边距，每个格子宽度
        available_width = canvas_width - 40
        width = available_width // self.grid_cols
        
        # 限制最小和最大宽度
        if width < 80:
            width = 80
        elif width > 400:
            width = 400
        
        self.preview_width = width
        self.preview_height = int(width * GRID_ASPECT_RATIO)
    
    def _init_grids(self):
        """初始化格子数据结构"""
        self.grid_contents = {(r, c): None for r in range(self.grid_rows) for c in range(self.grid_cols)}
        self.grid_images = {(r, c): None for r in range(self.grid_rows) for c in range(self.grid_cols)}
    
    def _resize_to_preview(self, pil_image):
        return pil_image.resize((self.preview_width, self.preview_height), Image.Resampling.LANCZOS)
    
    def _resize_to_small(self, pil_image):
        """缩放到右侧小图尺寸"""
        small_width = 80
        small_height = int(80 * GRID_ASPECT_RATIO)
        return pil_image.resize((small_width, small_height), Image.Resampling.LANCZOS)
    
    def _load_images_from_folder(self):
        """从 imgs 文件夹加载图片"""
        imgs_dir = os.path.join(self.base_dir, IMGS_DIR_NAME)
        if not os.path.exists(imgs_dir):
            os.makedirs(imgs_dir)
            return
        
        self.folder_images = {}
        self.all_images = []
        
        for item in sorted(os.listdir(imgs_dir)):
            folder_path = os.path.join(imgs_dir, item)
            if os.path.isdir(folder_path):
                self.folder_images[item] = []
                for img_file in sorted(os.listdir(folder_path)):
                    if img_file.lower().endswith(IMAGE_EXTENSIONS):
                        try:
                            img_path = os.path.join(folder_path, img_file)
                            pil_img = Image.open(img_path)
         
                            img_data = {
                                'pil': self._resize_to_preview(pil_img),
                                'tk_big': ImageTk.PhotoImage(self._resize_to_preview(pil_img)),
                                'tk_small': ImageTk.PhotoImage(self._resize_to_small(pil_img)),
                                'label': img_file,
                                'path': img_path,
                                'filename': img_file,
                                'folder': item,
                                'canvas_item': None,
                                'x': 0,
                                'y': 0
                            }
                            self.folder_images[item].append(img_data)
                            self.all_images.append(img_data)
                        except Exception as e:
                            print(f"加载失败 {img_file}: {e}")
    
    def auto_calculate_shape(self):
        """自动计算最佳形状"""
        left_count = sum(1 for img in self.grid_contents.values() if img)
        total_count = len(self.all_images) + left_count
        
        if total_count == 0:
            self.grid_rows, self.grid_cols = DEFAULT_ROWS, DEFAULT_COLS
        else:
            n = max(1, int(total_count ** 0.5))
            self.grid_rows = n
            self.grid_cols = (total_count + n - 1) // n
        
        self.grid_count = self.grid_rows * self.grid_cols
        self.rows_var.set(self.grid_rows)
        self.cols_var.set(self.grid_cols)
        
        # 重新计算预览尺寸
        self._calculate_preview_size()
        
        # 重置所有图片到右侧
        for key, img_data in list(self.grid_contents.items()):
            if img_data:
                folder = img_data.get('folder', '已放回图片')
                self.folder_images.setdefault(folder, []).append(img_data)
                if img_data not in self.all_images:
                    self.all_images.append(img_data)
        
        self._init_grids()
        self.left_grids = {}
        self._draw_left_grids()
        self._draw_right_sections()
        self.update_status(f"自动设置形状: {self.grid_rows}行 x {self.grid_cols}列")

    def _on_shape_change(self):
        """手动调整行数列数"""
        self.grid_rows = self.rows_var.get()
        self.grid_cols = self.cols_var.get()
        self.grid_count = self.grid_rows * self.grid_cols
        
        # 重新计算预览尺寸
        self._calculate_preview_size()
        
        # 放回所有左侧图片
        for key, img_data in list(self.grid_contents.items()):
            if img_data:
                folder = img_data.get('folder', '已放回图片')
                self.folder_images.setdefault(folder, []).append(img_data)
                if img_data not in self.all_images:
                    self.all_images.append(img_data)
        
        self._init_grids()
        self.left_grids = {}
        self._draw_left_grids()
        self._draw_right_sections()
        self.update_status(f"已调整形状为: {self.grid_rows}行 x {self.grid_cols}列")
    
    def _draw_left_grids(self):
        """绘制左侧格子"""
        self.left_canvas.delete("all")
        
        # 使用 self.preview_width/height
        total_width = self.grid_cols * self.preview_width
        total_height = self.grid_rows * self.preview_height
        
        self.left_canvas.configure(scrollregion=(0, 0, total_width + 20, total_height + 20))
        
        self.left_canvas.update_idletasks()
        canvas_width = self.left_canvas.winfo_width()
        canvas_height = self.left_canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = 900
        if canvas_height <= 1:
            canvas_height = 600
        
        start_x = (canvas_width - total_width) // 2 if canvas_width > total_width else 10
        start_y = (canvas_height - total_height) // 2 if canvas_height > total_height else 10
        
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336', 
                '#00BCD4', '#795548', '#607D8B', '#E91E63', '#8BC34A']
        
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x1 = start_x + col * self.preview_width
                y1 = start_y + row * self.preview_height
                x2 = x1 + self.preview_width
                y2 = y1 + self.preview_height
                
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
                    x1 + self.preview_width//2, y1 + 20,
                    text=f"{row+1},{col+1}",
                    font=('Arial', 10),
                    fill=color,
                    tags=('grid',)
                )
        
        for key in self.left_grids.keys():
            if self.grid_contents.get(key):
                self.draw_grid_image(key)
    
    def draw_grid_image(self, key):
        if self.grid_images.get(key):
            self.left_canvas.delete(self.grid_images[key])
        
        content = self.grid_contents.get(key)
        if content is None or key not in self.left_grids:
            return
        
        x1, y1, x2, y2 = self.left_grids[key]
        
        # 重新缩放图片到当前预览尺寸
        img_pil = content['pil'].resize((self.preview_width, self.preview_height), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img_pil)
        content['pil'] = img_pil
        content['tk_big'] = img_tk
        
        img_item = self.left_canvas.create_image(x1, y1, anchor=tk.NW, image=img_tk)
        self.grid_images[key] = img_item
        
        # 绑定事件不变
        self.left_canvas.tag_bind(img_item, "<ButtonPress-1>", lambda e, k=key: self.drag_handler.start_grid_drag(e, k))
        self.left_canvas.tag_bind(img_item, "<B1-Motion>", self.drag_handler.on_drag_move)
        
    def _draw_right_sections(self):
        """绘制右侧区域 - 直接在 Canvas 上绘制"""
        self.right_canvas.delete("all")
        
        if not self.folder_images:
            self.right_canvas.create_text(
                150, 200, 
                text="暂无图片\n\n请将图片放入\nimgs/子文件夹中",
                font=('Arial', 12), fill='#ecf0f1', justify=tk.CENTER
            )
            self.right_canvas.configure(scrollregion=(0, 0, 300, 400))
            return
        
        self.right_canvas.update_idletasks()
        canvas_width = self.right_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 280
        
        # 右侧小图尺寸固定
        small_width = 80
        small_height = int(80 * GRID_ASPECT_RATIO)
        cols_per_row = max(1, (canvas_width - 20) // (small_width + 15))
        
        current_y = 10
        
        for folder_name, images in self.folder_images.items():
            if not images:
                continue
            
            self.right_canvas.create_text(
                15, current_y, anchor=tk.NW,
                text=f"📁 {folder_name} ({len(images)}张)",
                font=('Arial', 12, 'bold'), fill='#ecf0f1', tags=('right_title',)
            )
            current_y += 30
            
            row_height = small_height + 30
            
            for idx, img_data in enumerate(images):
                row = idx // cols_per_row
                col = idx % cols_per_row
                
                x = 15 + col * (small_width + 15)
                y = current_y + row * row_height
                
                self.right_canvas.create_rectangle(
                    x, y, x + small_width, y + small_height,
                    outline='#5a7a9a', fill='#2c3e50', width=1,
                    tags=(f"right_bg_{folder_name}_{idx}",)
                )
                
                img_item = self.right_canvas.create_image(
                    x, y, anchor=tk.NW, 
                    image=img_data['tk_small'],
                    tags=(f"right_img_{folder_name}_{idx}",)
                )
                
                text = img_data['label'][:12]
                self.right_canvas.create_text(
                    x + small_width//2, y + small_height + 5,
                    text=text, font=('Arial', 8), fill='white',
                    tags=(f"right_text_{folder_name}_{idx}",)
                )
                
                img_data['canvas_item'] = img_item
                img_data['x'] = x
                img_data['y'] = y
                
                self.right_canvas.tag_bind(img_item, "<ButtonPress-1>", 
                                        lambda e, f=folder_name, i=idx: self.drag_handler.start_small_drag(e, f, i))
                self.right_canvas.tag_bind(img_item, "<B1-Motion>", self.drag_handler.on_drag_move)
            
            total_rows = (len(images) + cols_per_row - 1) // cols_per_row
            current_y += total_rows * row_height + 20
        
        total_height = current_y + 20
        canvas_width = max(300, canvas_width)
        self.right_canvas.configure(scrollregion=(0, 0, canvas_width, total_height))

    def _remove_image_from_right_canvas(self, folder_name, idx):
        """从右侧画布中删除图片项"""
        self.right_canvas.delete(f"right_img_{folder_name}_{idx}")
        self.right_canvas.delete(f"right_bg_{folder_name}_{idx}")
        self.right_canvas.delete(f"right_text_{folder_name}_{idx}")
    
    def place_image_to_grid(self, img_data, key):
        """放置图片到格子"""
        folder = img_data['folder']
        idx = None
        
        # 找到图片在文件夹中的索引
        if folder in self.folder_images:
            for i, img in enumerate(self.folder_images[folder]):
                if img is img_data:
                    idx = i
                    break
            if idx is not None:
                self.folder_images[folder].pop(idx)
                # 从右侧画布删除
                self._remove_image_from_right_canvas(folder, idx)
        
        if img_data in self.all_images:
            self.all_images.remove(img_data)
        
        self.grid_contents[key] = img_data
        self.draw_grid_image(key)
        self._draw_right_sections()
    
    def return_image_to_right(self, img_data, source_key):
        """图片放回右侧"""
        self.grid_contents[source_key] = None
        if self.grid_images.get(source_key):
            self.left_canvas.delete(self.grid_images[source_key])
            self.grid_images[source_key] = None
        
        folder = img_data.get('folder', '已放回图片')
        self.folder_images.setdefault(folder, []).append(img_data)
        self.all_images.append(img_data)
        self._draw_right_sections()
    
    def auto_place_images(self):
        """自动放置图片"""
        if not self.all_images:
            self.update_status("没有图片可放置")
            return
        
        empty_keys = sorted([k for k in self.left_grids if self.grid_contents.get(k) is None])
        if not empty_keys:
            self.update_status("所有格子都已满")
            return
        
        for i, img_data in enumerate(self.all_images[:len(empty_keys)]):
            self.place_image_to_grid(img_data, empty_keys[i])
        
        self.update_status(f"已自动放置 {min(len(self.all_images), len(empty_keys))} 张图片")
    
    def output_composite(self):
        """输出拼合图片"""
        # 统计需要输出的图片数量
        output_list = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                img_data = self.grid_contents.get((row, col))
                if img_data:
                    output_list.append((row, col, img_data))
        
        if not output_list:
            self.update_status("左侧格子为空")
            return
        
        # 显示进度条
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = len(output_list)
        self.root.update_idletasks()
        
        output_width = self.grid_cols * self.output_width
        output_height = self.grid_rows * self.output_height
        final_image = Image.new('RGB', (output_width, output_height), 'white')
        
        for idx, (row, col, img_data) in enumerate(output_list):
            # 更新进度
            self.progress_bar['value'] = idx + 1
            self.update_status(f"正在处理: {idx+1}/{len(output_list)} - {img_data['label']}")
            self.root.update_idletasks()
            
            # 读取并缩放图片
            with Image.open(img_data['path']) as original:
                scaled_img = original.resize((self.output_width, self.output_height), Image.Resampling.LANCZOS)
                final_image.paste(scaled_img, (col * self.output_width, row * self.output_height))
        
        # 保存文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"composite_{self.grid_rows}x{self.grid_cols}_{self.output_width}x{self.output_height}_{timestamp}.png"
        save_path = os.path.join(self.output_dir, filename)
        final_image.save(save_path)
        
        # 完成
        self.progress_bar['value'] = 0
        self.update_status(f"已保存: {filename} (每格{self.output_width}x{self.output_height})")
        
    def _import_image(self):
        """导入图片"""
        file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if not file_path:
            return
        
        folder = list(self.folder_images.keys())[0] if self.folder_images else "导入图片"
        if folder not in self.folder_images:
            self.folder_images[folder] = []
        
        pil_img = Image.open(file_path)
        
        img_data = {
            'pil': self._resize_to_preview(pil_img),
            'tk_big': ImageTk.PhotoImage(self._resize_to_preview(pil_img)),
            'tk_small': ImageTk.PhotoImage(self._resize_to_small(pil_img)),
            'label': os.path.basename(file_path),
            'path': file_path,
            'filename': os.path.basename(file_path),
            'folder': folder,
            'canvas_item': None,
            'x': 0,
            'y': 0
        }
        
        self.folder_images[folder].append(img_data)
        self.all_images.append(img_data)
        self._draw_right_sections()
        self.update_status(f"已导入: {img_data['label']}")
    
    def reset_all(self):
        """重置所有"""
        self.output_scale_var.set(DEFAULT_SCALE_PERCENT)
        self._on_output_scale_change()
        for key, img_data in list(self.grid_contents.items()):
            if img_data:
                folder = img_data.get('folder', '已放回图片')
                self.folder_images.setdefault(folder, []).append(img_data)
                if img_data not in self.all_images:
                    self.all_images.append(img_data)
        
        self._init_grids()
        self.left_grids = {}
        self._draw_left_grids()
        self._draw_right_sections()
        self.auto_calculate_shape()
        self.update_status("已重置")
    
    def update_status(self, msg):
        self.status_label.config(text=msg)

    def _on_left_mousewheel(self, event):
        """左侧画布鼠标滚轮滚动"""
        self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_right_mousewheel(self, event):
        """右侧画布鼠标滚轮滚动"""
        self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_right_canvas_resize(self, event):
        """右侧画布大小变化时，重新绘制"""
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(100, self._draw_right_sections)

    def _on_left_canvas_resize(self, event):
        if hasattr(self, '_left_resize_timer'):
            self.root.after_cancel(self._left_resize_timer)
        self._left_resize_timer = self.root.after(100, self._on_resize_handler)

    def _on_resize_handler(self):
        self._calculate_preview_size()
        self._reload_preview_images()
        self._draw_left_grids()
        self._draw_right_sections()

    def _reload_preview_images(self):
        """重新加载所有预览图"""
        for img_data in self.all_images:
            img_data['pil'] = self._resize_to_preview(Image.open(img_data['path']).convert('RGB'))
            img_data['tk_big'] = ImageTk.PhotoImage(img_data['pil'])

    def _on_output_scale_change(self, event=None):
        percent = self.output_scale_var.get() / 100.0
        self.output_width = int(BASE_OUTPUT_WIDTH * percent)
        self.output_height = int(BASE_OUTPUT_HEIGHT * percent)
        self.output_scale_label.config(text=f"{self.output_scale_var.get()}%")
        self.update_status(f"输出尺寸: {self.output_width}x{self.output_height}")