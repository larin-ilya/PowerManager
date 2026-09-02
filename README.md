# Power Manager

Мини-утилита для принудительной перезагрузки / выключения Windows-ПК.

## Состав

| Файл | Назначение |
|---|---|
| `power_manager.py` | GUI-приложение (tkinter, входит в Python) с двумя кнопками |
| `make_icon.py` | Генератор иконки `power.ico` (только stdlib, без зависимостей) |
| `power.ico` | Иконка приложения (многоразмерная, PNG-входы) |
| `dist/PowerManager.exe` | Standalone-сборка (PyInstaller, onefile, без консоли) |

## Запуск из исходников

```bat
python power_manager.py
```

Требуется только Python 3 с tkinter (стандартная поставка Windows).

## Сборка standalone .exe

```bat
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name PowerManager ^
  --icon power.ico ^
  --add-data "power.ico;." ^
  power_manager.py
```

Результат: `dist\PowerManager.exe` — запускается на любом Windows-ПК
без установки Python.

## Как работает

- «Принудительная перезагрузка» → `shutdown /f /t 0 /r`
- «Принудительное выключение» → `shutdown /f /t 0 /s`

`/f` принудительно закрывает незавершённые приложения, `/t 0` — без задержки.
Перед выполнением запрашивается подтверждение. Права администратора не требуются.

## Пересоздание иконки

```bat
python make_icon.py
```
