"""常量配置"""

# 格子宽高比（158:251 = 1:1.5886）
GRID_ASPECT_RATIO = 251 / 158

# 预览图尺寸范围
MIN_PREVIEW_WIDTH = 80
MAX_PREVIEW_WIDTH = 400

# 颜色
BG_COLOR = '#2c3e50'
RIGHT_BG_COLOR = '#3d566e'
GRID_COLORS = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336', 
               '#00BCD4', '#795548', '#607D8B', '#E91E63', '#8BC34A']

# 默认值
DEFAULT_ROWS = 2
DEFAULT_COLS = 2

# 支持格式
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

# 输出目录
OUTPUT_DIR_NAME = "out"
IMGS_DIR_NAME = "imgs"