# -*- coding: utf-8 -*-
"""Power Manager 2.0 — утилита перезагрузки/выключения Windows-ПК по таймеру.

GUI на tkinter (входит в состав Python для Windows).
Команды:
    shutdown /f /t N /r  — принудительная перезагрузка через N секунд
    shutdown /f /t N /s  — принудительное выключение через N секунд
    shutdown /a          — отмена запланированного завершения

Требуются права администратора: при запуске без них приложение
перезапрашивает повышение через UAC (в exe также встроен манифест
requireAdministrator). Подтверждение перед выполнением не запрашивается.
"""

import ctypes
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox

APP_TITLE = "Power Manager"
APP_VERSION = "2.0"
BG = "#f4f5f9"
FG = "#1f2430"

# Варианты таймера: (подпись в списке, задержка в секундах).
TIMER_OPTIONS = [
    ("Сейчас (без задержки)", 0),
    ("Через 10 секунд", 10),
    ("Через 30 секунд", 30),
    ("Через 1 минуту", 60),
    ("Через 5 минут", 300),
    ("Через 10 минут", 600),
    ("Через 30 минут", 1800),
    ("Через 1 час", 3600),
]
DEFAULT_TIMER_INDEX = 2  # «Через 30 секунд»

# Код ошибки shutdown: завершение работы уже запланировано.
ERROR_SHUTDOWN_IN_PROGRESS = 1190

RED = "#d64541"
DARK = "#3b4252"
GRAY = "#6a7180"
GREEN = "#2e8b57"
MUTED = "#6a7180"


def resource_path(rel: str) -> str:
    """Путь к ресурсу рядом со скриптом (в т.ч. внутри PyInstaller-сборки)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def is_admin() -> bool:
    """Проверка прав администратора текущего процесса."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Перезапустить приложение от имени администратора (UAC-запрос).

    Возвращает True, если запрос UAC был показан (успех запуска не
    гарантирован — пользователь мог отклонить повышение).
    """
    frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        # Запуск из PyInstaller-сборки: exe уже несёт манифест, но страхуемся.
        target = sys.executable
        params = subprocess.list2cmdline(sys.argv[1:])
    else:
        # Запуск из исходников: python.exe <путь-к-скрипту> [аргументы...].
        target = sys.executable
        parts = ['"' + sys.argv[0] + '"'] + sys.argv[1:]
        params = subprocess.list2cmdline(parts)
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", target, params, None, 1)
    return result > 32


def _exec_shutdown(args):
    """Запустить shutdown.exe без всплывающей консоли; вернуть CompletedProcess."""
    try:
        return subprocess.run(
            ["shutdown"] + args,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:  # noqa: BLE001
        return exc


def shade(color: str, factor: float) -> str:
    """Затемнить/осветлить hex-цвет (#rrggbb)."""
    r, g, b_ = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b_ = max(0, min(255, int(b_ * factor)))
    return f"#{r:02x}{g:02x}{b_:02x}"


class PowerManagerApp(tk.Tk):
    """Окно приложения с таймерами выключения/перезагрузки."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._center(400, 400)

        self.timer_var = tk.StringVar(self)
        self.timer_var.set(TIMER_OPTIONS[DEFAULT_TIMER_INDEX][0])
        self._label_to_sec = {label: sec for label, sec in TIMER_OPTIONS}
        self._planned_end = None  # time.time() до запланированного завершения
        self._status = tk.StringVar(self)
        self._status.set("Таймер не задан")

        try:
            self.iconbitmap(resource_path("power.ico"))
        except tk.TclError:
            pass

        self._build_ui()
        self._tick()

    # ---------- построение интерфейса ----------

    def _build_ui(self) -> None:
        tk.Label(
            self, text="Power Manager", font=("Segoe UI", 16, "bold"),
            bg=BG, fg=FG,
        ).pack(pady=(18, 2))
        tk.Label(
            self, text="Принудительное завершение работы системы",
            font=("Segoe UI", 9), bg=BG, fg=MUTED,
        ).pack(pady=(0, 6))

        # Строка выбора таймера.
        timer_frame = tk.Frame(self, bg=BG)
        timer_frame.pack(fill="x", padx=26, pady=(6, 2))
        tk.Label(
            timer_frame, text="Выполнить через:",
            font=("Segoe UI", 10), bg=BG, fg=FG,
        ).pack(side="left", padx=(0, 8))
        self.timer_menu = tk.OptionMenu(
            timer_frame, self.timer_var, *[label for label, _ in TIMER_OPTIONS])
        self.timer_menu.configure(
            font=("Segoe UI", 10), bg="#ffffff", fg=FG,
            activebackground="#e8eaf1", activeforeground=FG,
            relief="solid", bd=1, highlightthickness=0,
            cursor="hand2", width=16,
        )
        self.timer_menu.pack(side="left", fill="x", expand=True)
        # Стилизуем выпадающий список.
        menu = self.timer_menu["menu"]
        menu.configure(bg="#ffffff", fg=FG, activebackground="#dce0ea",
                       activeforeground=FG, font=("Segoe UI", 10))

        # Кнопки действий.
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="x", padx=26, pady=(6, 0))
        self._make_button(
            frame, "Перезагрузка по таймеру", RED,
            lambda: self._schedule(reboot=True),
        ).pack(fill="x", pady=4)
        self._make_button(
            frame, "Выключение по таймеру", DARK,
            lambda: self._schedule(reboot=False),
        ).pack(fill="x", pady=4)
        self._make_button(
            frame, "Отменить завершение", GRAY,
            self._cancel,
        ).pack(fill="x", pady=4)

        # Строка статуса (обратный отсчёт до запланированного действия).
        self._status_label = tk.Label(
            self, textvariable=self._status, font=("Segoe UI", 9),
            bg=BG, fg=GREEN, wraplength=340,
        )
        self._status_label.pack(fill="x", padx=26, pady=(4, 0))
        tk.Label(
            self, text="Подтверждение не требуется — действие начнётся сразу.",
            font=("Segoe UI", 8), bg=BG, fg=MUTED,
        ).pack(fill="x", padx=26, pady=(0, 10))

    def _make_button(self, parent, text, color, command) -> tk.Button:
        def on_enter(_=None) -> None:
            b.configure(bg=shade(color, 1.15))

        def on_leave() -> None:
            b.configure(bg=color)

        b = tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 11, "bold"),
            bg=color, fg="white",
            activebackground=shade(color, 1.15), activeforeground="white",
            relief="flat", bd=0, padx=14, pady=10,
            cursor="hand2",
        )
        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        return b

    def _center(self, width: int, height: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 3
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ---------- логика ----------

    def _timer_seconds(self) -> int:
        return self._label_to_sec.get(self.timer_var.get(), 0)

    def _schedule(self, reboot: bool) -> None:
        """Запланировать/выполнить перезагрузку или выключение по таймеру."""
        seconds = self._timer_seconds()
        flag = "/r" if reboot else "/s"
        verb = "Перезагрузка" if reboot else "Выключение"

        if seconds == 0:
            # Немедленное действие: если есть старый план, отменяем его.
            _exec_shutdown(["/a"])
            result = _exec_shutdown(["/f", "/t", "0", flag])
            if isinstance(result, Exception):
                messagebox.showerror(APP_TITLE,
                                     f"{verb}: не удалось запустить shutdown.\n{result}")
            elif result.returncode == ERROR_SHUTDOWN_IN_PROGRESS:
                messagebox.showerror(
                    APP_TITLE,
                    "Завершение работы уже запланировано.\n"
                    "Сначала нажмите «Отменить завершение».")
            elif result.returncode != 0:
                messagebox.showerror(
                    APP_TITLE,
                    f"{verb}: ошибка shutdown (код {result.returncode}).\n"
                    + (result.stderr or result.stdout or "").strip())
            else:
                # Система начнёт завершаться; окно больше не нужно.
                self.after(500, self.destroy)
            return

        # Отложенное действие: сбрасываем прежний план и ставим новый.
        _exec_shutdown(["/a"])
        result = _exec_shutdown(["/f", "/t", str(seconds), flag])
        if isinstance(result, Exception):
            messagebox.showerror(APP_TITLE,
                                 f"{verb}: не удалось запустить shutdown.\n{result}")
            return
        if result.returncode != 0:
            messagebox.showerror(
                APP_TITLE,
                f"{verb}: ошибка shutdown (код {result.returncode}).\n"
                + (result.stderr or result.stdout or "").strip())
            return
        self._planned_end = time.time() + seconds
        self._status_label.configure(fg=GREEN)
        self._refresh_status()

    def _cancel(self) -> None:
        """Отменить запланированное завершение работы (shutdown /a)."""
        result = _exec_shutdown(["/a"])
        if isinstance(result, Exception):
            messagebox.showerror(APP_TITLE,
                                 f"Не удалось запустить shutdown.\n{result}")
            return
        if result.returncode == 0:
            self._planned_end = None
            self._status.set("Запланированное завершение отменено")
            self._status_label.configure(fg=GREEN)
        else:
            self._planned_end = None
            self._status.set("Запланированного завершения нет")
            self._status_label.configure(fg=MUTED)

    def _refresh_status(self) -> None:
        if self._planned_end is None:
            return
        left = self._planned_end - time.time()
        if left <= 0:
            self._status.set("Завершение работы системы…")
            return
        self._status.set("Запланировано. Осталось: " + self._fmt(left))

    @staticmethod
    def _fmt(seconds: float) -> str:
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h} ч {m:02d} мин {s:02d} с"
        if m:
            return f"{m} мин {s:02d} с"
        return f"{s} с"

    def _tick(self) -> None:
        self._refresh_status()
        self.after(250, self._tick)


def main() -> None:
    # Требование прав администратора.
    if not is_admin():
        if relaunch_as_admin():
            return  # UAC-запрос показан; новый процесс продолжит работу.
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            APP_TITLE,
            "Power Manager требует прав администратора.\n"
            "Запустите программу от имени администратора.")
        root.destroy()
        return

    app = PowerManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
