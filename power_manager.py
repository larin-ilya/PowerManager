# -*- coding: utf-8 -*-
"""Power Manager — утилита для принудительной перезагрузки/выключения ПК.

GUI на tkinter (входит в состав Python для Windows).
Команды:  shutdown /f /t 0 /r  — принудительная перезагрузка
          shutdown /f /t 0 /s  — принудительное выключение
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

APP_TITLE = "Power Manager"
BG = "#f4f5f9"
FG = "#1f2430"


def resource_path(rel: str) -> str:
    """Путь к ресурсу рядом со скриптом (в т.ч. внутри PyInstaller-сборки)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def run_shutdown(root: tk.Tk, reboot: bool) -> None:
    """Спросить подтверждение и выполнить принудительную команду shutdown."""
    verb = "перезагрузить" if reboot else "выключить"
    if not messagebox.askyesno(
        APP_TITLE,
        f"Действительно принудительно {verb} компьютер?\n"
        "Все несохранённые данные будут потеряны!",
        icon="warning",
        parent=root,
    ):
        return
    flag = "/r" if reboot else "/s"
    os.system(f"shutdown /f /t 0 {flag}")
    # Система начнёт завершать работу сразу; на всякий случай закрываем окно.
    root.after(300, root.destroy)


def center_window(win: tk.Tk, width: int, height: int) -> None:
    win.update_idletasks()
    x = (win.winfo_screenwidth() - width) // 2
    y = (win.winfo_screenheight() - height) // 3
    win.geometry(f"{width}x{height}+{x}+{y}")


def make_button(parent: tk.Tk, text: str, fg_color: str, command) -> tk.Button:
    def on_enter(_=None) -> None:
        b.configure(bg=shade(fg_color, 1.15))

    def on_leave() -> None:
        b.configure(bg=fg_color)

    b = tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 11, "bold"),
        bg=fg_color,
        fg="white",
        activebackground=shade(fg_color, 1.15),
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=14,
        pady=12,
        cursor="hand2",
        width=26,
    )
    b.bind("<Enter>", on_enter)
    b.bind("<Leave>", on_leave)
    return b


def shade(color: str, factor: float) -> str:
    """Затемнить/осветить hex-цвет (#rrggbb)."""
    r, g, b_ = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b_ = max(0, min(255, int(b_ * factor)))
    return f"#{r:02x}{g:02x}{b_:02x}"


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    root.configure(bg=BG)
    root.resizable(False, False)
    center_window(root, 380, 240)

    # Иконка окна (power.ico, добавляется в сборку как данные).
    try:
        root.iconbitmap(resource_path("power.ico"))
    except tk.TclError:
        pass

    tk.Label(
        root, text="Power Manager", font=("Segoe UI", 16, "bold"),
        bg=BG, fg=FG,
    ).pack(pady=(18, 2))
    tk.Label(
        root, text="Принудительное завершение работы системы",
        font=("Segoe UI", 9), bg=BG, fg="#6a7180",
    ).pack(pady=(0, 16))

    frame = tk.Frame(root, bg=BG)
    frame.pack(fill="x", padx=26)

    make_button(frame, "Принудительная перезагрузка", "#d64541",
                lambda: run_shutdown(root, True)).pack(fill="x", pady=4)
    make_button(frame, "Принудительное выключение", "#3b4252",
                lambda: run_shutdown(root, False)).pack(fill="x", pady=4)

    root.mainloop()


if __name__ == "__main__":
    main()
