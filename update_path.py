import os
import winreg


def add_to_path(new_paths):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        try:
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""

        path_elements = current_path.split(";") if current_path else []
        for p in new_paths:
            if p not in path_elements:
                path_elements.append(p)

        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(path_elements))
        print("Path updated.")

add_to_path([r"C:\msys64\mingw64\bin", r"C:\msys64\usr\bin"])
