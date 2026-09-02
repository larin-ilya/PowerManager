# -*- coding: utf-8 -*-
"""Генерация power.ico — значок «power» (красный скруглённый квадрат,
белый символ питания). Только стандартная библиотека Python.

Отрисовка параметрическая (суперсэмплинг 2x2), PNG-энкодер на zlib,
ICO-контейнер с PNG-входами (поддерживается Windows Vista+).
"""

import math
import struct
import zlib

SIZES = [16, 24, 32, 48, 64, 256]


def inside_rounded_rect(px, py, x0, y0, x1, y1, r) -> bool:
    if px < x0 or px > x1 or py < y0 or py > y1:
        return False
    if x0 + r <= px <= x1 - r or y0 + r <= py <= y1 - r:
        return True
    cx = x0 + r if px< x0 + r else x1 - r
    cy = y0 + r if py < y0 + r else y1 - r
    dx, dy = px - cx, py - cy
    return dx * dx + dy * dy <= r * r


def in_power_glyph(px, py, s, min_stroke) -> bool:
    """Символ питания: кольцо с щелью сверху + вертикальная штрих."""
    cx, cy = 128.0 * s, 130.0 * s
    r = 74.0 * s
    w = max(21.0 * s, min_stroke)

    d = math.hypot(px - cx, py - cy)

    # Щель сверху: исключаем дугу в районе вершины.
    ang = math.atan2(cy - py, px - cx)  # 0 = право, +pi/2 = верх
    half_gap = math.radians(29.0)
    in_wedge = abs(ang - math.pi / 2.0) < half_gap and d < r + w * 1.6
    ring = abs(d - r) <= w / 2.0 and not in_wedge

    # Вертикальный штрих: капсула от чуть выше верха кольца до центра.
    y_top = cy - r - 4.0 * s
    y_bot = cy + 16.0 * s
    y_clamped = max(y_top, min(py, y_bot))
    dseg = math.hypot(px - cx, py - y_clamped)
    bar = dseg <= w / 2.0

    return ring or bar


def render(size: int) -> bytes:
    """Возвращает RGBA-буфер size*size."""
    s = size / 256.0
    min_stroke = max(2.0, 6.0 * s) if size <= 48 else 0.0
    x0, y0, x1, y1 = 8.0 * s, 8.0 * s, 248.0 * s, 248.0 * s
    rad = 48.0 * s
    out = bytearray(size * size * 4)
    for j in range(size):
        t = (j + 0.5) / size
        br = 218 + (164 - 218) * t
        bg = 66 + (26 - 66) * t
        bb = 58 + (24 - 58) * t
        for i in range(size):
            cov_bg = 0
            cov_gl = 0
            for fy in (0.25, 0.75):
                y = j + fy
                for fx in (0.25, 0.75):
                    x = i + fx
                    if not inside_rounded_rect(x, y, x0, y0, x1, y1, rad):
                        continue
                    cov_bg += 1
                    if in_power_glyph(x, y, s, min_stroke):
                        cov_gl += 1
            cbg = cov_bg / 4.0
            if cbg == 0.0:
                continue
            cgl = cov_gl / 4.0
            o = (j * size + i) * 4
            out[o] = int(br * (1.0 - cgl) + 255.0 * cgl)
            out[o + 1] = int(bg * (1.0 - cgl) + 255.0 * cgl)
            out[o + 2] = int(bb * (1.0 - cgl) + 255.0 * cgl)
            out[o + 3] = int(cbg * 255)
    return bytes(out)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(width: int, height: int, rgba: bytes) -> bytes:
    raw = bytearray()
    row = width * 4
    for y in range(height):
        raw.append(0)  # фильтр: none
        raw += rgba[y * row:(y + 1) * row]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def make_ico(entries) -> bytes:
    """entries: список (size, png_bytes)."""
    count = len(entries)
    header = struct.pack("<HHH", 0, 1, count)
    dir_parts = b""
    data = b""
    offset = 6 + 16 * count
    for size, png in entries:
        dim = 0 if size >= 256 else size
        dir_parts += struct.pack(
            "<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        data += png
    return header + dir_parts + data


def main() -> None:
    entries = []
    for size in SIZES:
        rgba = render(size)
        entries.append((size, encode_png(size, size, rgba)))
        print(f"rendered {size}x{size}: png {len(entries[-1][1])} bytes")
    ico = make_ico(entries)
    out = "power.ico"
    with open(out, "wb") as f:
        f.write(ico)
    print(f"wrote {out}: {len(ico)} bytes, {len(entries)} images")


if __name__ == "__main__":
    main()
