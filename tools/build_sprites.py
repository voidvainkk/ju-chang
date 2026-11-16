# -*- coding: utf-8 -*-
"""把四张生图表格切成游戏用的像素精灵图。

每张原图是「一行六格」的表情表，六个表情从左到右依次是：
  1 平静微笑  2 闭眼笑  3 张嘴大笑  4 哭  5 累/无语  6 生气/害臊

处理流程：
  1. 从画布四条边洪水填充，把「连到边缘的白」抠成透明。角色身上的白
     （水手领、袖子、高光）不连边，不会被误伤。
  2. 找连通域，取面积最大的六个当六个角色。生图 JPEG 在四角会留下
     几十像素的淡灰残渣，那些区域面积只有两三百，天然被排在后头。
  3. 六帧共用同一个裁剪框：宽度取六个包围盒的并集，高度取并集，
     纵向以脚底线对齐。这样切表情时人物不会忽大忽小、也不会左右跳。
  4. 用 BOX 降采样（不是最近邻）。原图是逻辑像素放大约 36 倍再存的
     JPEG，最近邻会把相连的方块抽成断线，BOX 求块均值才压得回来。

输出：web/sprites/idol_{style}.png —— 64×80 一帧，横排六帧，共 384×80。
"""
import os
import sys
from collections import deque

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "web", "sprites")

FRAME_W, FRAME_H = 64, 80
N_FRAMES = 6
WHITE_TOL = 24          # 每个通道都 >= 255-WHITE_TOL 才算「白」

# 文件名 -> 风格 id。文件名是用户从生图网站直接存下来的，保持原样。
SOURCES = [
    ("16×16像素双马尾角色图生成.jpeg", "sweet"),       # 王道系：粉双马尾水手服
    ("16×16像素双马尾角色图生成 (1).jpeg", "night"),  # 和风系：黑发振袖
    ("16×16像素双马尾角色图生成 (2).jpeg", "odd"),    # 地雷系：深紫内扣
    ("16×16像素双马尾角色图生成 (3).jpeg", "cool"),   # 摇滚系：白毛黑皮
]


def is_white(px, tol=WHITE_TOL):
    return px[0] >= 255 - tol and px[1] >= 255 - tol and px[2] >= 255 - tol


def cut_background(img):
    """从四条边洪水填充，把连到画布边缘的白变成透明。"""
    img = img.convert("RGB")
    w, h = img.size
    px = img.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dst = out.load()

    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))

    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        if not is_white(px[x, y]):
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                    q.append((nx, ny))

    for y in range(h):
        for x in range(w):
            if not seen[y * w + x]:
                dst[x, y] = px[x, y] + (255,)
    return out


def find_figures(rgba, n=N_FRAMES):
    """找面积最大的 n 个连通域，按从左到右返回包围盒。"""
    w, h = rgba.size
    a = rgba.load()
    seen = bytearray(w * h)
    comps = []
    for y0 in range(h):
        for x0 in range(w):
            i = y0 * w + x0
            if seen[i] or not a[x0, y0][3]:
                continue
            q = deque([(x0, y0)])
            seen[i] = 1
            area = 0
            x1 = x2 = x0
            y1 = y2 = y0
            while q:
                x, y = q.popleft()
                area += 1
                if x < x1:
                    x1 = x
                elif x > x2:
                    x2 = x
                if y < y1:
                    y1 = y
                elif y > y2:
                    y2 = y
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if not seen[j] and a[nx, ny][3]:
                            seen[j] = 1
                            q.append((nx, ny))
            comps.append((area, x1, y1, x2, y2))
    comps.sort(reverse=True)
    picked = comps[:n]
    if len(picked) < n:
        raise RuntimeError(f"只找到 {len(picked)} 个角色，{n} 格不全")
    picked.sort(key=lambda c: c[1])
    return [(c[1], c[2], c[3], c[4]) for c in picked]


def despeckle(img, min_area=8):
    """清掉孤立的小碎点。

    生图 JPEG 在画布右下角留了两小块淡灰残渣（各约 20px 见方），
    抠白底抠不掉、连通域也挤得进前六，放大后就是帧边上的小方块。
    这里按连通面积过滤，几个像素以下的都抹掉。
    """
    w, h = img.size
    a = img.load()
    seen = bytearray(w * h)
    for y0 in range(h):
        for x0 in range(w):
            i = y0 * w + x0
            if seen[i] or a[x0, y0][3] == 0:
                continue
            q = deque([(x0, y0)])
            seen[i] = 1
            comp = []
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if not seen[j] and a[nx, ny][3]:
                            seen[j] = 1
                            q.append((nx, ny))
            if len(comp) < min_area:
                for x, y in comp:
                    a[x, y] = (0, 0, 0, 0)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for fname, style in SOURCES:
        src = os.path.join(ROOT, fname)
        if not os.path.exists(src):
            print("MISSING", fname)
            continue
        raw = Image.open(src)
        cut = cut_background(raw)
        boxes = find_figures(cut)

        # 六帧共用同一个框：宽度取并集、纵向以脚底线对齐
        bw = max(b[2] - b[0] + 1 for b in boxes)
        bh = max(b[3] - b[1] + 1 for b in boxes)
        foot_y = max(b[3] for b in boxes)

        scale = min(FRAME_W / bw, FRAME_H / bh)
        tw, th = max(1, round(bw * scale)), max(1, round(bh * scale))

        sheet = Image.new("RGBA", (FRAME_W * N_FRAMES, FRAME_H), (0, 0, 0, 0))
        for i, (bx0, by0, bx1, by1) in enumerate(boxes):
            cxm = (bx0 + bx1) // 2
            fx0 = cxm - bw // 2
            fx1 = fx0 + bw
            fy1 = foot_y + 1
            fy0 = fy1 - bh
            tile = cut.crop((fx0, fy0, fx1, fy1))
            tile = tile.resize((tw, th), Image.BOX)
            ox = (FRAME_W - tw) // 2
            oy = FRAME_H - th
            sheet.alpha_composite(tile, (i * FRAME_W + ox, oy))

        # 二值化 alpha：像素画不该有半透明边
        out = sheet
        out.putalpha(out.getchannel("A").point(lambda v: 255 if v >= 96 else 0))
        despeckle(out)

        dst = os.path.join(OUT_DIR, f"idol_{style}.png")
        out.save(dst)
        print(f"{style:6s} <- {fname}  box={bw}x{bh}  -> {dst}  {out.size}")


if __name__ == "__main__":
    main()
