"""程序入口"""

import tkinter as tk
from app import PicturePuzzleApp

def main():
    root = tk.Tk()
    app = PicturePuzzleApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()