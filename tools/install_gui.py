import os
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import re

CONFIG_PATH = "./config.txt"  # 可选配置文件

def get_chrome_version(chrome_path):
    try:
        output = subprocess.check_output(
            f'"{chrome_path}" --version', shell=True, stderr=subprocess.STDOUT
        ).decode("utf-8")
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output)
        return match.group(1) if match else "无法识别版本"
    except Exception as e:
        return "获取失败"

def browse_chrome():
    file_path = filedialog.askopenfilename(title="选择 chrome.exe", filetypes=[("Chrome", "chrome.exe")])
    if file_path:
        chrome_path_var.set(file_path)
        version = get_chrome_version(file_path)
        chrome_version_var.set(version)

def save_config():
    path = chrome_path_var.get()
    if not path or not os.path.exists(path):
        messagebox.showerror("错误", "请指定有效的 chrome.exe 路径")
        return
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(f"CHROME_BROWSER_PATH = r\"{path}\"\n")
    messagebox.showinfo("完成", f"配置已保存至 {CONFIG_PATH}，请在脚本中引用。")

def open_chromedriver_download():
    import webbrowser
    webbrowser.open("https://googlechromelabs.github.io/chrome-for-testing/")

# GUI 界面
root = tk.Tk()
root.title("浏览器检测助手")
root.geometry("500x300")

tk.Label(root, text="请选择你的 Chrome 浏览器：").pack(pady=10)
chrome_path_var = tk.StringVar()
tk.Entry(root, textvariable=chrome_path_var, width=60).pack()
tk.Button(root, text="浏览...", command=browse_chrome).pack(pady=5)

tk.Label(root, text="检测到的 Chrome 版本：").pack(pady=(15, 0))
chrome_version_var = tk.StringVar(value="未检测")
tk.Label(root, textvariable=chrome_version_var, fg="blue").pack()

tk.Button(root, text="打开 ChromeDriver 下载页", command=open_chromedriver_download).pack(pady=15)
tk.Button(root, text="保存配置", command=save_config).pack(pady=5)

root.mainloop()
