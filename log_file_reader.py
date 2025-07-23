import os
from tkinter import Tk, filedialog
def read_log_files(base_path):
    log_contents = {}

    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith('.log'):  # Case-insensitive extension check
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        log_contents[file_path] = f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return log_contents

# Optional: Use GUI to pick folder (Windows-friendly)
def select_folder():
    try:
        from tkinter import Tk, filedialog
        Tk().withdraw()  # Hide the root window
        folder = filedialog.askdirectory(title="Select folder to search for .log files")
        return folder
    except ImportError:
        print("tkinter not available. Please install or use manual path input.")
        return None
    
def select_log_files():
    Tk().withdraw()  # Hide the root window
    file_paths = filedialog.askopenfilenames(
        title="Select one or more .log files",
        filetypes=[("Log files", "*.log"), ("All files", "*.*")]
    )
    return file_paths

def read_all_logs_from_folder(folder_path):
    content = ""

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".log"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content += f"\n\n===== START OF FILE: {file} =====\n"
                        content += f.read()
                        content += f"\n===== END OF FILE: {file} =====\n"
                except Exception as e:
                    print(f"Failed to read {full_path}: {e}")
    
    return content

