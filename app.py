"""主应用类"""

import tkinter as tk
from tkinter import filedialog, ttk
import os
import datetime
from PIL import Image, ImageTk, ImageFilter

from constants import *
from drag_handler import DragHandler


class PicturePuzzleApp:
    """图片拼图工具主应用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("图片拼图工具 - 自动形状拼合")
        self.root.geometry("1800x800")
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
        
        # 模糊
        self.blur_percent = DEFAULT_BLUR_PERCENT

        self.auto_white_balance = DEFAULT_AUTO_WHITE_BALANCE
        self.white_balance_var = tk.BooleanVar(value=DEFAULT_AUTO_WHITE_BALANCE)

        self.delete_zone_frame = None
        self.delete_zone_label = None

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
            ("🎯 自动放置图片", '#9b59b6', self.auto_place_images),
            ("💾 输出拼合图片", '#3498db', self.output_composite),
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

        # 模糊控制
        blur_frame = tk.Frame(button_frame, bg=BG_COLOR)
        blur_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(blur_frame, text="模糊:", font=('Arial', 11),
                bg=BG_COLOR, fg='white').pack(side=tk.LEFT)
        
        self.blur_var = tk.IntVar(value=DEFAULT_BLUR_PERCENT)
        self.blur_slider = tk.Scale(blur_frame, from_=MIN_BLUR_PERCENT, to=MAX_BLUR_PERCENT,
                                    orient=tk.HORIZONTAL, length=120,
                                    variable=self.blur_var,
                                    command=self._on_blur_change,
                                    bg=BG_COLOR, fg='white', highlightthickness=0)
        self.blur_slider.pack(side=tk.LEFT, padx=5)

        self.blur_label = tk.Label(blur_frame, text="0%", font=('Arial', 10),
                                bg=BG_COLOR, fg='white')
        self.blur_label.pack(side=tk.LEFT)
        
        # 白平衡控制
        white_balance_frame = tk.Frame(button_frame, bg=BG_COLOR)
        white_balance_frame.pack(side=tk.LEFT, padx=20)

        self.white_balance_check = tk.Checkbutton(
            white_balance_frame,
            text="自动白平衡",
            variable=self.white_balance_var,
            bg=BG_COLOR,
            fg='white',
            selectcolor=BG_COLOR,
            activebackground=BG_COLOR,
            activeforeground='white',
            font=('Arial', 11),
            command=self._on_white_balance_change
        )
        self.white_balance_check.pack(side=tk.LEFT)

        # 形状调节
        shape_frame = tk.Frame(button_frame, bg=BG_COLOR)
        shape_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(shape_frame, text="行数:", font=('Arial', 11),
                bg=BG_COLOR, fg='white').pack(side=tk.LEFT)
        
        self.rows_var = tk.IntVar(value=self.grid_rows)
        self.rows_spinbox = tk.Spinbox(shape_frame, from_=1, to=50, width=3,
                                        textvariable=self.rows_var,
                                        font=('Arial', 11),
                                        command=self._on_shape_change)
        self.rows_spinbox.pack(side=tk.LEFT, padx=5)
        
        tk.Label(shape_frame, text="列数:", font=('Arial', 11),
                bg=BG_COLOR, fg='white').pack(side=tk.LEFT, padx=(10, 0))
        
        self.cols_var = tk.IntVar(value=self.grid_cols)
        self.cols_spinbox = tk.Spinbox(shape_frame, from_=1, to=50, width=3,
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
        main_paned.add(left_frame, width=1280)
        
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
        main_paned.add(right_frame, width=520)
        
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
        bottom_frame = tk.Frame(self.root, bg=BG_COLOR)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 10))

        # 状态信息（左）
        self.status_label = tk.Label(bottom_frame, text="拖拽图片到左侧格子 | 自动计算形状",
                                    font=('Arial', 10), bg=BG_COLOR, fg='#ecf0f1', anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 进度条（中）
        self.progress_bar = ttk.Progressbar(bottom_frame, length=200, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=(10, 10))

        # 删除区（右）
        self.delete_zone_frame = tk.Frame(bottom_frame, bg=DELETE_ZONE_COLOR, cursor='target')
        self.delete_zone_frame.pack(side=tk.RIGHT, padx=(10, 0))
        self.delete_zone_label = tk.Label(
            self.delete_zone_frame,
            text=" 🗑 拖到此处删除 ",
            font=('Arial', 10, 'bold'),
            bg=DELETE_ZONE_COLOR,
            fg='white',
            padx=15,
            pady=3
        )
        self.delete_zone_label.pack()

        # 绑定删除区事件（在 drag_handler 中通过 app 访问）
        self.delete_zone_frame.bind("<Enter>", self._on_delete_zone_enter)
        self.delete_zone_frame.bind("<Leave>", self._on_delete_zone_leave)
        self.delete_zone_label.bind("<Enter>", self._on_delete_zone_enter)
        self.delete_zone_label.bind("<Leave>", self._on_delete_zone_leave)
        
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
        if width < MIN_PREVIEW_WIDTH:
            width = MIN_PREVIEW_WIDTH
        elif width > MAX_PREVIEW_WIDTH:
            width = MAX_PREVIEW_WIDTH
        
        self.preview_width = width
        self.preview_height = int(width * GRID_ASPECT_RATIO)
    
    def _init_grids(self):
        """初始化格子数据结构"""
        self.grid_contents = {(r, c): None for r in range(self.grid_rows) for c in range(self.grid_cols)}
        self.grid_images = {(r, c): None for r in range(self.grid_rows) for c in range(self.grid_cols)}
    
    def _resize_to_preview(self, pil_image):
        return pil_image.resize((self.preview_width, self.preview_height), Image.Resampling.LANCZOS)
    
    def _resize_to_small(self, pil_image, pic_type='standard'): 
        small_height = int(80 * GRID_ASPECT_RATIO)  
        small_width = 80 if pic_type == 'standard' else 160
        return pil_image.resize((small_width, small_height), Image.Resampling.LANCZOS)
            
    def _load_images_from_folder(self):
        """从 imgs 文件夹加载图片：子文件夹内的图片 + 根目录的独立图片"""
        imgs_dir = os.path.join(self.base_dir, IMGS_DIR_NAME)
        if not os.path.exists(imgs_dir):
            os.makedirs(imgs_dir)
            return

        self.folder_images = {}
        self.all_images = []
        default_folder = "未分类"   # 用于存放根目录下的独立图片

        for item in sorted(os.listdir(imgs_dir)):
            item_path = os.path.join(imgs_dir, item)

            # 子文件夹：遍历内部图片
            if os.path.isdir(item_path):
                folder_name = item
                self.folder_images[folder_name] = []
                for img_file in sorted(os.listdir(item_path)):
                    if img_file.lower().endswith(IMAGE_EXTENSIONS):
                        self._add_image_from_path(
                            os.path.join(item_path, img_file),
                            folder_name,
                            img_file
                        )

            # 根目录下的独立图片文件
            elif os.path.isfile(item_path) and item.lower().endswith(IMAGE_EXTENSIONS):
                if default_folder not in self.folder_images:
                    self.folder_images[default_folder] = []
                self._add_image_from_path(item_path, default_folder, item)

    def _add_image_from_path(self, img_path, folder_name, img_file):
        try:
            pil_img = self._open_and_auto_rotate(img_path)  # 自动旋转横向图
            w, h = pil_img.size
            ratio = w / h

            # 类型判断（使用旋转后的尺寸）
            if abs(ratio - STANDARD_RATIO) / STANDARD_RATIO <= RATIO_TOLERANCE:
                pic_type = 'standard'
            elif abs(ratio - WIDE_RATIO) / WIDE_RATIO <= RATIO_TOLERANCE:
                pic_type = 'wide'
            else:
                print(f"跳过尺寸不符的图片: {img_file} (宽高比 {ratio:.3f})")
                return

            preview_pil = self._resize_to_preview(pil_img)
            small_pil = self._resize_to_small(pil_img, pic_type)

            img_data = {
                'pil': preview_pil,
                'tk_big': ImageTk.PhotoImage(preview_pil),
                'tk_small': ImageTk.PhotoImage(small_pil),
                'label': img_file,
                'path': img_path,          # 仍保留原始路径，但使用时都通过辅助方法打开
                'filename': img_file,
                'folder': folder_name,
                'canvas_item': None,
                'x': 0,
                'y': 0,
                'pic_type': pic_type,
                'grid_start': None
            }
            self.folder_images[folder_name].append(img_data)
            self.all_images.append(img_data)
        except Exception as e:
            print(f"加载失败 {img_file}: {e}")

    def auto_calculate_shape(self):
        left_imgs = [img for img in self.grid_contents.values() if img is not None]
        required_left = self._calc_required_cells(left_imgs)
        required_right = self._calc_required_cells(self.all_images)
        total_cells = required_left + required_right

        if total_cells == 0:
            self.grid_rows, self.grid_cols = DEFAULT_ROWS, DEFAULT_COLS
        else:
            n = max(1, int(total_cells ** 0.5))
            self.grid_rows = n
            self.grid_cols = (total_cells + n - 1) // n

        self.grid_count = self.grid_rows * self.grid_cols
        self.rows_var.set(self.grid_rows)
        self.cols_var.set(self.grid_cols)

        self._calculate_preview_size()

        # 去重收集左侧图片
        unique_imgs = {}
        for img_data in self.grid_contents.values():
            if img_data:
                unique_imgs[id(img_data)] = img_data

        for img_data in unique_imgs.values():
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

        self._calculate_preview_size()

        # 去重收集左侧图片
        unique_imgs = {}
        for img_data in self.grid_contents.values():
            if img_data:
                unique_imgs[id(img_data)] = img_data

        for img_data in unique_imgs.values():
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
        """绘制或更新某个格子里的图片"""
        # 如果该格子已有图片项，先删除
        if self.grid_images.get(key):
            self.left_canvas.delete(self.grid_images[key])
            self.grid_images[key] = None

        img_data = self.grid_contents.get(key)
        if img_data is None:
            return

        # 判断是否为宽幅图的起始格
        if img_data.get('pic_type') == 'wide' and img_data.get('grid_start') == key:
            # 宽幅图，跨两个格子：key 和 (r, c+1)
            r, c = key
            next_key = (r, c + 1)
            if next_key not in self.left_grids:
                # 列数不足，理论上不应发生
                return

            x1, y1, _, _ = self.left_grids[key]
            _, _, x2, y2 = self.left_grids[next_key]

            # 重新缩放图片到跨格尺寸
            span_w = x2 - x1
            span_h = y2 - y1
            scaled = img_data['pil'].resize((span_w, span_h), Image.Resampling.LANCZOS)
            img_data['tk_span'] = ImageTk.PhotoImage(scaled)   # 缓存跨格大图

            img_item = self.left_canvas.create_image(x1, y1, anchor=tk.NW, image=img_data['tk_span'])
            self.grid_images[key] = img_item
            self.grid_images[next_key] = None   # 第二个格子由起始格覆盖，不再单独绘制

            # 绑定事件（拖拽时也会用到，此处先简单绑定到起始格）
            self.left_canvas.tag_bind(img_item, "<ButtonPress-1>",
                                    lambda e, k=key: self.drag_handler.start_grid_drag(e, k))
            self.left_canvas.tag_bind(img_item, "<B1-Motion>", self.drag_handler.on_drag_move)

        elif img_data.get('pic_type') == 'wide' and img_data.get('grid_start') != key:
            # 宽幅图的第二个格子，什么都不画（起始格已覆盖）
            pass
        else:
            # 标准图
            if key not in self.left_grids:
                return
            x1, y1, x2, y2 = self.left_grids[key]
            w = x2 - x1
            h = y2 - y1
            scaled = img_data['pil'].resize((w, h), Image.Resampling.LANCZOS)
            img_data['tk_big'] = ImageTk.PhotoImage(scaled)
            img_item = self.left_canvas.create_image(x1, y1, anchor=tk.NW, image=img_data['tk_big'])
            self.grid_images[key] = img_item
            self.left_canvas.tag_bind(img_item, "<ButtonPress-1>",
                                    lambda e, k=key: self.drag_handler.start_grid_drag(e, k))
            self.left_canvas.tag_bind(img_item, "<B1-Motion>", self.drag_handler.on_drag_move)
        
    def _draw_right_sections(self):
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

        small_height = int(80 * GRID_ASPECT_RATIO)   # 统一高度 ≈127
        margin_x = 10
        margin_y = 10
        start_x = 15
        current_y = 10

        for folder_name, images in self.folder_images.items():
            if not images:
                continue

            # 文件夹标题
            self.right_canvas.create_text(
                start_x, current_y, anchor=tk.NW,
                text=f"📁 {folder_name} ({len(images)}张)",
                font=('Arial', 12, 'bold'), fill='#ecf0f1', tags=('right_title',)
            )
            current_y += 30

            x = start_x
            row_height = small_height + 25  # 图+文字

            for idx, img_data in enumerate(images):
                # 按顺序获取宽度
                if img_data['pic_type'] == 'wide':
                    img_w = int(small_height * WIDE_RATIO)    # ≈160
                else:
                    img_w = int(small_height * STANDARD_RATIO) # ≈80

                # 如果放不下则换行
                if x + img_w > canvas_width - 10:
                    x = start_x
                    current_y += row_height + margin_y

                y = current_y

                # 背景
                self.right_canvas.create_rectangle(
                    x, y, x + img_w, y + small_height,
                    outline='#5a7a9a', fill='#2c3e50', width=1,
                    tags=(f"right_bg_{folder_name}_{idx}",)
                )
                # 图片
                img_item = self.right_canvas.create_image(
                    x, y, anchor=tk.NW,
                    image=img_data['tk_small'],
                    tags=(f"right_img_{folder_name}_{idx}",)
                )
                # 文件名
                text = img_data['label'][:12]
                self.right_canvas.create_text(
                    x + img_w // 2, y + small_height + 5,
                    text=text, font=('Arial', 8), fill='white',
                    tags=(f"right_text_{folder_name}_{idx}",)
                )
                # 宽幅标记
                if img_data['pic_type'] == 'wide':
                    tri_size = 24
                    self.right_canvas.create_polygon(
                        x, y, x + tri_size, y, x, y + tri_size,
                        fill='gold', outline='black',
                        tags=(f"right_wide_{folder_name}_{idx}",)
                    )
                    self.right_canvas.create_text(
                        x + 2, y + 6, angle=45, text="W", font=('Arial', 7, 'bold'),
                        fill='black', anchor=tk.NW,
                        tags=(f"right_wide_text_{folder_name}_{idx}",)
                    )

                img_data['canvas_item'] = img_item
                img_data['x'] = x
                img_data['y'] = y

                # 绑定拖拽
                self.right_canvas.tag_bind(img_item, "<ButtonPress-1>",
                                        lambda e, f=folder_name, i=idx: self.drag_handler.start_small_drag(e, f, i))
                self.right_canvas.tag_bind(img_item, "<B1-Motion>", self.drag_handler.on_drag_move)

                x += img_w + margin_x   # 移动到下一张的起始位置

            # 下一个文件夹另起一行
            current_y += row_height + 20

        total_height = current_y + 20
        canvas_width = max(300, canvas_width)
        self.right_canvas.configure(scrollregion=(0, 0, canvas_width, total_height))

    def _remove_image_from_right_canvas(self, folder_name, idx):
        self.right_canvas.delete(f"right_img_{folder_name}_{idx}")
        self.right_canvas.delete(f"right_bg_{folder_name}_{idx}")
        self.right_canvas.delete(f"right_text_{folder_name}_{idx}")
        self.right_canvas.delete(f"right_wide_{folder_name}_{idx}")
        self.right_canvas.delete(f"right_wide_text_{folder_name}_{idx}")
    
    def place_image_to_grid(self, img_data, key):
        """放置图片到格子，key 为起始格（对于宽幅图，同时占用 key 和右侧邻格）"""
        folder = img_data['folder']
        idx = None
        if folder in self.folder_images:
            for i, img in enumerate(self.folder_images[folder]):
                if img is img_data:
                    idx = i
                    break
            if idx is not None:
                self.folder_images[folder].pop(idx)
                self._remove_image_from_right_canvas(folder, idx)

        if img_data in self.all_images:
            self.all_images.remove(img_data)

        if img_data.get('pic_type') == 'wide':
            # 检查是否为连续两个空格
            r, c = key
            next_key = (r, c + 1)
            if next_key not in self.left_grids:
                # 列不够，不能放置
                self._add_back_to_folder(img_data, folder)   # 回退
                return False
            if self.grid_contents.get(key) is not None or self.grid_contents.get(next_key) is not None:
                self._add_back_to_folder(img_data, folder)
                return False

            # 占用两个格子
            self.grid_contents[key] = img_data
            self.grid_contents[next_key] = img_data
            img_data['grid_start'] = key
        else:
            if self.grid_contents.get(key) is not None:
                self._add_back_to_folder(img_data, folder)
                return False
            self.grid_contents[key] = img_data
            img_data['grid_start'] = key

        self.draw_grid_image(key)
        if img_data.get('pic_type') == 'wide':
            self.draw_grid_image((key[0], key[1]+1))   # 触发第二个格子的空白绘制
        self._draw_right_sections()
        return True
    
    def _add_back_to_folder(self, img_data, folder_name):
        """将图片重新加回右侧文件夹"""
        if folder_name not in self.folder_images:
            self.folder_images[folder_name] = []
        self.folder_images[folder_name].append(img_data)
        if img_data not in self.all_images:
            self.all_images.append(img_data)
    
    def return_image_to_right(self, img_data, source_key):
        """将图片从格子放回右侧"""
        if img_data.get('pic_type') == 'wide':
            start = img_data.get('grid_start')
            if start is None:
                start = source_key
            r, c = start
            # 清除两个格子
            self.grid_contents[(r, c)] = None
            self.grid_contents[(r, c+1)] = None
            if self.grid_images.get((r, c)):
                self.left_canvas.delete(self.grid_images[(r, c)])
                self.grid_images[(r, c)] = None
            if self.grid_images.get((r, c+1)):
                self.left_canvas.delete(self.grid_images[(r, c+1)])
                self.grid_images[(r, c+1)] = None
            img_data['grid_start'] = None
        else:
            self.grid_contents[source_key] = None
            if self.grid_images.get(source_key):
                self.left_canvas.delete(self.grid_images[source_key])
                self.grid_images[source_key] = None
            img_data['grid_start'] = None

        folder = img_data.get('folder', '已放回图片')
        if folder not in self.folder_images:
            self.folder_images[folder] = []
        self.folder_images[folder].append(img_data)
        if img_data not in self.all_images:
            self.all_images.append(img_data)
        self._draw_right_sections()
    
    def auto_place_images(self):
        """自动放置图片：按 all_images 列表顺序依次放置"""
        if not self.all_images:
            self.update_status("没有图片可放置")
            return

        placed = 0
        skipped = 0

        # 遍历副本，因为放置过程中 all_images 会变动
        for img in self.all_images[:]:
            if img.get('pic_type') == 'wide':
                slot = self._find_consecutive_empty_slots()
                if slot is None:
                    skipped += 1
                    continue
                if self.place_image_to_grid(img, slot):
                    placed += 1
                else:
                    skipped += 1
            else:
                # 任意一个空格即可
                empty_keys = [k for k in self.left_grids if self.grid_contents.get(k) is None]
                if not empty_keys:
                    skipped += 1
                    continue
                if self.place_image_to_grid(img, empty_keys[0]):
                    placed += 1
                else:
                    skipped += 1

        msg = f"已放置 {placed} 张图片"
        if skipped > 0:
            msg += f"，{skipped} 张因无合适位置跳过"
        self.update_status(msg)

    def _find_consecutive_empty_slots(self):
        """返回第一个水平连续两个空格的起始格 (r, c)，没有则返回 None"""
        for r in range(self.grid_rows):
            for c in range(self.grid_cols - 1):
                if (self.grid_contents.get((r, c)) is None and
                    self.grid_contents.get((r, c+1)) is None):
                    return (r, c)
        return None
        
    def output_composite(self):
        """输出拼合图片，宽幅图占据双倍宽度"""
        output_list = []
        # 我们遍历格子，根据 grid_start 去重，确保每张图只输出一次
        seen_ids = set()
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                img_data = self.grid_contents.get((row, col))
                if img_data is None:
                    continue
                # 对于宽幅图，只处理起始格
                if img_data.get('pic_type') == 'wide':
                    start = img_data.get('grid_start')
                    if start != (row, col):
                        continue
                    if id(img_data) in seen_ids:
                        continue
                    seen_ids.add(id(img_data))
                    output_list.append((row, col, img_data, 'wide'))
                else:
                    output_list.append((row, col, img_data, 'standard'))

        if not output_list:
            self.update_status("左侧格子为空")
            return

        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = len(output_list)
        self.root.update_idletasks()

        output_width = self.grid_cols * self.output_width
        output_height = self.grid_rows * self.output_height
        final_image = Image.new('RGB', (output_width, output_height), 'white')

        for idx, (row, col, img_data, ptype) in enumerate(output_list):
            self.progress_bar['value'] = idx + 1
            self.update_status(f"正在处理: {idx+1}/{len(output_list)} - {img_data['label']}")
            self.root.update_idletasks()

            original = self._open_and_auto_rotate(img_data['path'])
            
            if self.auto_white_balance:
                original = self._apply_auto_white_balance(original, ptype)
                self.root.update_idletasks()

            if ptype == 'wide':
                scaled_img = original.resize((2 * self.output_width, self.output_height), Image.Resampling.LANCZOS)
            else:
                scaled_img = original.resize((self.output_width, self.output_height), Image.Resampling.LANCZOS)

            blur_pct = self.blur_var.get()
            if blur_pct > 0:
                radius = (blur_pct / 100.0) * self.output_width * BLUR_RADIUS_RATIO
                scaled_img = scaled_img.filter(ImageFilter.GaussianBlur(radius))
            
            final_image.paste(scaled_img, (col * self.output_width, row * self.output_height))

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"composite_{self.grid_rows}x{self.grid_cols}_{self.output_width}x{self.output_height}_{timestamp}.png"
        save_path = os.path.join(self.output_dir, filename)
        final_image.save(save_path)

        self.progress_bar['value'] = 0
        self.update_status(f"已保存: {filename} (每格{self.output_width}x{self.output_height})")
        
    def _import_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if not file_path:
            return

        folder = list(self.folder_images.keys())[0] if self.folder_images else "导入图片"
        if folder not in self.folder_images:
            self.folder_images[folder] = []

        pil_img = self._open_and_auto_rotate(file_path)  # 自动旋转
        w, h = pil_img.size
        ratio = w / h

        if abs(ratio - STANDARD_RATIO) / STANDARD_RATIO <= RATIO_TOLERANCE:
            pic_type = 'standard'
        elif abs(ratio - WIDE_RATIO) / WIDE_RATIO <= RATIO_TOLERANCE:
            pic_type = 'wide'
        else:
            self.update_status(f"错误：图片宽高比 {ratio:.2f} 不符合标准或宽幅要求")
            return

        img_data = {
            'pil': self._resize_to_preview(pil_img),
            'tk_big': ImageTk.PhotoImage(self._resize_to_preview(pil_img)),
            'tk_small': ImageTk.PhotoImage(self._resize_to_small(pil_img, pic_type)),
            'label': os.path.basename(file_path),
            'path': file_path,
            'filename': os.path.basename(file_path),
            'folder': folder,
            'canvas_item': None,
            'x': 0,
            'y': 0,
            'pic_type': pic_type,
            'grid_start': None
        }

        self.folder_images[folder].append(img_data)
        self.all_images.append(img_data)
        self._draw_right_sections()
        self.update_status(f"已导入: {img_data['label']}")
    
    def reset_all(self):
        """重置所有"""
        self.output_scale_var.set(DEFAULT_SCALE_PERCENT)
        self._on_output_scale_change()

        self.blur_var.set(DEFAULT_BLUR_PERCENT)
        self._on_blur_change()

        self.white_balance_var.set(DEFAULT_AUTO_WHITE_BALANCE)
        self.auto_white_balance = DEFAULT_AUTO_WHITE_BALANCE

        # 收集所有不重复的左侧图片（通过 id 去重）
        unique_imgs = {}
        for img_data in self.grid_contents.values():
            if img_data:
                unique_imgs[id(img_data)] = img_data

        # 逐一放回右侧
        for img_data in unique_imgs.values():
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
        """重新加载所有预览图（窗口大小变化时调用）"""
        for img_data in self.all_images:
            original = self._open_and_auto_rotate(img_data['path'])   # 自动旋转
            img_data['pil'] = self._resize_to_preview(original)
            img_data['tk_big'] = ImageTk.PhotoImage(img_data['pil'])

    def _on_output_scale_change(self, event=None):
        percent = self.output_scale_var.get() / 100.0
        self.output_width = int(BASE_OUTPUT_WIDTH * percent)
        self.output_height = int(BASE_OUTPUT_HEIGHT * percent)
        self.output_scale_label.config(text=f"{self.output_scale_var.get()}%")
        self.update_status(f"输出尺寸: {self.output_width}x{self.output_height}")

    def _on_blur_change(self, event=None):
        """模糊滑块变化时更新标签"""
        self.blur_label.config(text=f"{self.blur_var.get()}%")

    def _on_white_balance_change(self):
        self.auto_white_balance = self.white_balance_var.get()
        if self.auto_white_balance:
            self.update_status("自动白平衡已开启")
        else:
            self.update_status("自动白平衡已关闭")

    def _open_and_auto_rotate(self, img_path):
        """
        打开图片并检测是否为横向标准图（宽高比≈1.59:1），
        若是则顺时针旋转90度，返回旋转后的 PIL 图像。
        """
        pil_img = Image.open(img_path)
        w, h = pil_img.size
        ratio = w / h
        if abs(ratio - GRID_ASPECT_RATIO) / GRID_ASPECT_RATIO <= RATIO_TOLERANCE:
            pil_img = pil_img.rotate(-90, expand=True)
        return pil_img

    def _calc_required_cells(self, images_list):
        """计算图片列表所需的格子总数（宽幅图占2格，标准占1格）"""
        total = 0
        for img in images_list:
            if img.get('pic_type') == 'wide':
                total += 2
            else:
                total += 1
        return total
    
    def _on_delete_zone_enter(self, event):
        """鼠标进入删除区"""
        self.delete_zone_frame.configure(bg=DELETE_ZONE_HOVER_COLOR)
        self.delete_zone_label.configure(bg=DELETE_ZONE_HOVER_COLOR)

    def _on_delete_zone_leave(self, event):
        """鼠标离开删除区"""
        self.delete_zone_frame.configure(bg=DELETE_ZONE_COLOR)
        self.delete_zone_label.configure(bg=DELETE_ZONE_COLOR)

    def delete_image(self, img_data):
        """从右侧删除一张图片"""
        folder = img_data.get('folder', '未分类')
        if folder in self.folder_images:
            if img_data in self.folder_images[folder]:
                self.folder_images[folder].remove(img_data)
                if not self.folder_images[folder]:
                    del self.folder_images[folder]
        if img_data in self.all_images:
            self.all_images.remove(img_data)

    def is_in_delete_zone(self, mouse_x, mouse_y):
        """检查屏幕坐标是否在删除区内"""
        if self.delete_zone_frame is None:
            return False
        x1 = self.delete_zone_frame.winfo_rootx()
        y1 = self.delete_zone_frame.winfo_rooty()
        x2 = x1 + self.delete_zone_frame.winfo_width()
        y2 = y1 + self.delete_zone_frame.winfo_height()
        return (x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2)
    
    def _get_border_mask(self, image, pic_type):
        """
        生成拍立得边框区域的掩码。
        """
        import numpy as np
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=bool)
        
        if pic_type == 'wide':
            # 水平：1%-3%, 97%-99%；竖直：1%-7%, 83%-99%
            outer_left, outer_right, outer_top, outer_bottom = int(w * 0.01), int(w * 0.99), int(h * 0.01), int(h * 0.99)
            inner_left, inner_right, inner_top, inner_bottom = int(w * 0.03), int(w * 0.97), int(h * 0.07), int(h * 0.83)

            mask[outer_top:outer_bottom, outer_left:outer_right] = True
            mask[inner_top:inner_bottom, inner_left:inner_right] = False
        
        else:
            # 水平：1%-6%, 94%-99%；竖直：1%-7%, 83%-99%
            outer_left, outer_right, outer_top, outer_bottom = int(w * 0.01), int(w * 0.99), int(h * 0.01), int(h * 0.99)
            inner_left, inner_right, inner_top, inner_bottom = int(w * 0.06), int(w * 0.94), int(h * 0.07), int(h * 0.83)

            mask[outer_top:outer_bottom, outer_left:outer_right] = True
            mask[inner_top:inner_bottom, inner_left:inner_right] = False
        
        return mask


    def _find_white_regions(self, image, border_mask, block_size=32, num_blocks=10, bright_threshold=170, neutral_threshold=25):
        """
        在边框区域内寻找最适合做白平衡参考的白色块。
        """
        import numpy as np
        
        # 只使用 RGB 通道
        if len(image.shape) == 3 and image.shape[2] == 4:
            rgb = image[:, :, :3]
        else:
            rgb = image
        
        # 亮色：所有通道 > 200
        is_bright = np.all(rgb > bright_threshold, axis=2)
        # 中性色：三通道标准差 < 25
        is_neutral = np.std(rgb.astype(np.float32), axis=2) < neutral_threshold
        # 白色区域 = 亮色 + 中性色 + 边框范围内
        is_white = is_bright & is_neutral & border_mask
        
        blocks = []
        step = max(1, block_size // 2)
        
        for y in range(0, rgb.shape[0] - block_size, step):
            for x in range(0, rgb.shape[1] - block_size, step):
                block_mask = is_white[y:y+block_size, x:x+block_size]
                white_ratio = np.sum(block_mask) / (block_size ** 2)
                
                if white_ratio > 0.8:
                    white_pixels = rgb[y:y+block_size, x:x+block_size][block_mask]
                    
                    if len(white_pixels) > 0:
                        mean_rgb = np.mean(white_pixels, axis=0)
                        variance = np.mean(np.var(white_pixels, axis=0))
                        blocks.append({
                            'x': x,
                            'y': y,
                            'mean_rgb': mean_rgb,
                            'variance': variance
                        })
        
        if len(blocks) == 0:
            return None
        
        blocks.sort(key=lambda b: b['variance'])
        best_blocks = blocks[:num_blocks]
        
        return best_blocks

    def _white_balance(self, image, blocks, target=240):
        """
        根据参考白色块执行白平衡校正。
        """
        import numpy as np
        
        if blocks is None or len(blocks) == 0:
            return image
        
        all_means = np.array([b['mean_rgb'] for b in blocks])
        reference_white = np.mean(all_means, axis=0)
        
        gains = np.array([
            target / max(reference_white[0], 1),
            target / max(reference_white[1], 1),
            target / max(reference_white[2], 1)
        ])
        
        channels = image.shape[2] if len(image.shape) == 3 else 1
    
        if channels == 4:
            wb_image = image.astype(np.float32)
            wb_image[:, :, :3] = wb_image[:, :, :3] * gains
            wb_image = np.clip(wb_image, 0, 255).astype(np.uint8)
        else:
            wb_image = image.astype(np.float32) * gains
            wb_image = np.clip(wb_image, 0, 255).astype(np.uint8)
        
        return wb_image
    
    def _apply_auto_white_balance(self, pil_image, pic_type):
        """
        对 PIL 图像执行自动白平衡。
        """
        import numpy as np
        from PIL import Image
        
        # PIL → numpy array (RGB)
        arr = np.array(pil_image)
        
        # 生成边框掩码
        border_mask = self._get_border_mask(arr, pic_type)
        
        # 寻找白色参考块
        blocks = self._find_white_regions(arr, border_mask, 
                                          block_size=WHITE_BLOCK_SIZE,
                                          num_blocks=WHITE_NUM_BLOCKS,
                                          bright_threshold=BRIGHTNESS_THRESHOLD,
                                          neutral_threshold=NEUTRAL_THRESHOLD)
        
        # 执行白平衡
        result = self._white_balance(arr, blocks, WHITE_BALANCE_TARGET)
        
        return Image.fromarray(result)