# -*- coding: utf-8 -*-
"""临时脚本：直接画 32x48 像素小人，四套名字风格 x 六表情。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 32, 48
ROOT = Path(r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场")

OUTLINE = (26, 34, 51, 255)
SKIN = (242, 201, 168, 255)
SKIN_SH = (217, 160, 127, 255)
WHITE = (244, 246, 250, 255)
BLUE = (27, 107, 208, 255)
BLUE_D = (20, 80, 156, 255)
BOOT = (38, 52, 78, 255)
EYE = (26, 34, 51, 255)
MOUTH = (176, 82, 92, 255)
BLUSH = (232, 132, 155, 255)
STAR = (35, 230, 194, 255)

STYLES = {
    "sweet": dict(
        hair=(244, 230, 200, 255), hi=(255, 244, 221, 255),
        jacket=(244, 230, 200, 255), accent=(232, 132, 155, 255),
        blush=True,
    ),
    "cool": dict(
        hair=(159, 196, 232, 255), hi=(207, 227, 245, 255),
        jacket=(232, 238, 242, 255), accent=(159, 196, 232, 255),
        blush=False,
    ),
    "night": dict(
        hair=(28, 47, 85, 255), hi=(42, 67, 115, 255),
        jacket=(28, 47, 85, 255), accent=(255, 209, 102, 255),
        blush=False,
    ),
    "odd": dict(
        hair=(90, 70, 54, 255), hi=(120, 94, 70, 255),
        jacket=(232, 132, 107, 255), accent=(255, 209, 102, 255),
        blush=True,
    ),
}

EXPRESSIONS = ["calm", "happy", "sad", "angry", "tired", "serious"]


def r(d, x0, y0, x1, y1, c):
    d.rectangle([x0, y0, x1, y1], fill=c)


def px(d, x, y, c):
    d.point((x, y), fill=c)


def head(d):
    # 16x16 圆角头，四角切掉
    r(d, 9, 6, 22, 21, SKIN)
    for x, y in [(9, 6), (22, 6), (9, 21), (22, 21)]:
        d.point((x, y), fill=(0, 0, 0, 0))
    r(d, 8, 8, 8, 20, SKIN)   # 左耳
    r(d, 23, 8, 23, 20, SKIN)  # 右耳
    r(d, 9, 6, 22, 7, SKIN_SH)  # 额发下阴影


def hair_back(d, style):
    h = STYLES[style]["hair"]
    hi = STYLES[style]["hi"]
    if style == "sweet":
        # 双马尾
        r(d, 2, 12, 6, 25, h)
        r(d, 25, 12, 29, 25, h)
        for x, y in [(2, 25), (29, 25), (2, 12), (29, 12)]:
            d.point((x, y), fill=(0, 0, 0, 0))
        px(d, 4, 14, hi); px(d, 4, 15, hi); px(d, 27, 14, hi); px(d, 27, 15, hi)
    elif style == "cool":
        r(d, 5, 9, 8, 19, h)
        r(d, 23, 9, 26, 19, h)
    elif style == "night":
        r(d, 4, 10, 7, 34, h)
        r(d, 24, 10, 27, 34, h)
        px(d, 5, 12, hi); px(d, 25, 12, hi)
    elif style == "odd":
        # 双丸子
        r(d, 5, 2, 10, 6, h)
        r(d, 21, 2, 26, 6, h)
        for x, y in [(5, 2), (10, 2), (21, 2), (26, 2)]:
            d.point((x, y), fill=(0, 0, 0, 0))
        # 呆毛
        r(d, 15, 0, 16, 2, h)
        r(d, 16, 0, 17, 1, h)

def hair_front(d, style):
    h = STYLES[style]["hair"]
    hi = STYLES[style]["hi"]
    # 发盖 + 两侧
    r(d, 7, 3, 24, 9, h)
    r(d, 7, 9, 9, 18, h)
    r(d, 22, 9, 24, 18, h)
    for x, y in [(7, 3), (24, 3)]:
        d.point((x, y), fill=(0, 0, 0, 0))
    px(d, 12, 4, hi); px(d, 13, 4, hi); px(d, 14, 4, hi)

    if style == "sweet":
        r(d, 8, 8, 23, 11, h)
        # 中分小缺口
        px(d, 15, 8, SKIN); px(d, 16, 8, SKIN)
        # 发圈/蝴蝶结
        r(d, 5, 11, 7, 12, STYLES[style]["accent"])
        r(d, 24, 11, 26, 12, STYLES[style]["accent"])
        # 蛋糕发夹
        r(d, 19, 9, 21, 10, (255, 244, 221, 255))
        px(d, 20, 8, (232, 132, 155, 255))
    elif style == "cool":
        r(d, 8, 8, 23, 12, h)
        # 齐刘海锯齿
        for x in (11, 15, 19):
            px(d, x, 12, (0, 0, 0, 0))
        # 银色发夹
        r(d, 9, 10, 12, 10, (232, 238, 242, 255))
    elif style == "night":
        # 中分长发
        r(d, 8, 8, 14, 12, h)
        r(d, 18, 8, 23, 12, h)
        px(d, 15, 8, SKIN); px(d, 16, 8, SKIN)
        # 星星发饰
        px(d, 21, 8, STYLES[style]["accent"])
        px(d, 20, 9, STYLES[style]["accent"])
        px(d, 22, 9, STYLES[style]["accent"])
    elif style == "odd":
        # 乱刘海：整块盖住额头，下缘做一点锯齿，不挖洞
        r(d, 8, 8, 23, 10, h)
        for x in (10, 14, 18, 21):
            px(d, x, 11, h)
        # 小鱼发夹
        r(d, 9, 7, 11, 7, STYLES[style]["accent"])
        px(d, 12, 7, STYLES[style]["accent"])
        px(d, 10, 6, STYLES[style]["accent"])

def body(d, style):
    jacket = STYLES[style]["jacket"]
    # 脖子
    r(d, 14, 21, 17, 23, SKIN_SH)
    # 腿（先画，裙摆会盖住上半截）
    r(d, 13, 36, 14, 41, SKIN)
    r(d, 17, 36, 18, 41, SKIN)
    r(d, 12, 41, 15, 45, BOOT)
    r(d, 16, 41, 19, 45, BOOT)
    r(d, 12, 44, 15, 45, OUTLINE)
    r(d, 16, 44, 19, 45, OUTLINE)
    # 手臂
    r(d, 7, 25, 10, 34, SKIN)
    r(d, 21, 25, 24, 34, SKIN)
    # 外搭
    r(d, 7, 23, 10, 30, jacket)
    r(d, 21, 23, 24, 30, jacket)
    # 躯干
    r(d, 11, 23, 20, 30, BLUE)
    # 水手领
    r(d, 12, 23, 19, 25, WHITE)
    px(d, 15, 26, WHITE); px(d, 16, 26, WHITE)
    # 短袖
    r(d, 7, 24, 10, 27, BLUE)
    r(d, 21, 24, 24, 27, BLUE)
    # 百褶裙（收窄，给手臂留位置）
    r(d, 11, 30, 20, 32, BLUE)
    r(d, 10, 33, 21, 33, BLUE)
    r(d, 10, 34, 21, 36, BLUE_D)
    for x in (12, 15, 18):
        r(d, x, 34, x, 36, BLUE)
    # 手（盖在裙摆外）
    r(d, 7, 31, 10, 34, SKIN)
    r(d, 21, 31, 24, 34, SKIN)
    px(d, 7, 34, OUTLINE); px(d, 24, 34, OUTLINE)
    # 领口星别针
    px(d, 18, 26, STAR)
    px(d, 19, 26, STAR)


def face(d, expr, blush=False):
    # 眼睛位置：左 11-12，右 19-20；嘴 15-16
    if expr == "calm":
        r(d, 11, 14, 12, 15, EYE)
        r(d, 19, 14, 20, 15, EYE)
        r(d, 15, 19, 16, 19, MOUTH)
    elif expr == "happy":
        # ^ ^
        for x, y in [(10, 15), (11, 14), (12, 15), (18, 15), (19, 14), (20, 15)]:
            d.point((x, y), fill=EYE)
        r(d, 15, 19, 17, 19, MOUTH)
        px(d, 15, 20, MOUTH); px(d, 17, 20, MOUTH)
    elif expr == "sad":
        r(d, 11, 15, 12, 15, EYE)
        r(d, 19, 15, 20, 15, EYE)
        # 眼睛下方泪光
        px(d, 11, 16, (159, 196, 232, 255)); px(d, 19, 16, (159, 196, 232, 255))
        # 嘴角向下
        r(d, 15, 19, 16, 19, MOUTH)
        px(d, 14, 20, MOUTH); px(d, 17, 20, MOUTH)
    elif expr == "angry":
        # 斜眉
        for x, y in [(10, 13), (11, 14), (12, 15), (20, 13), (19, 14), (18, 15)]:
            d.point((x, y), fill=OUTLINE)
        r(d, 11, 16, 12, 16, EYE)
        r(d, 19, 16, 20, 16, EYE)
        r(d, 15, 19, 16, 19, MOUTH)
    elif expr == "tired":
        r(d, 11, 16, 13, 16, EYE)
        r(d, 18, 16, 20, 16, EYE)
        r(d, 15, 20, 16, 20, MOUTH)
        # 汗
        px(d, 23, 10, (134, 247, 226, 255))
        px(d, 23, 11, (134, 247, 226, 255))
    elif expr == "serious":
        r(d, 10, 13, 12, 13, OUTLINE)
        r(d, 19, 13, 21, 13, OUTLINE)
        r(d, 11, 14, 12, 15, EYE)
        r(d, 19, 14, 20, 15, EYE)
        r(d, 15, 19, 16, 19, MOUTH)

    if blush:
        px(d, 9, 18, BLUSH); px(d, 22, 18, BLUSH)
        px(d, 10, 18, BLUSH); px(d, 21, 18, BLUSH)


def add_outline(img):
    """给角色外轮廓加 1px 深色描边，让小人从背景里立起来。"""
    src = img.load()
    out = img.copy()
    dst = out.load()
    for y in range(H):
        for x in range(W):
            if src[x, y][3] == 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= W or ny >= H or src[nx, ny][3] == 0:
                    dst[x, y] = OUTLINE
                    break
    return out


def draw(style, expr):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    hair_back(d, style)
    body(d, style)
    head(d)
    hair_front(d, style)
    face(d, expr, STYLES[style]["blush"])
    return add_outline(img)


def main():
    scale = 8
    gap = 12
    label_h = 18
    sheet_w = len(EXPRESSIONS) * (W * scale + gap) + gap
    sheet_h = len(STYLES) * (H * scale + gap + label_h) + gap
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (16, 24, 32, 255))
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    order = ["sweet", "cool", "night", "odd"]
    for row, style in enumerate(order):
        for col, expr in enumerate(EXPRESSIONS):
            img = draw(style, expr)
            big = img.resize((W * scale, H * scale), Image.NEAREST)
            x = gap + col * (W * scale + gap)
            y = gap + row * (H * scale + gap + label_h) + label_h
            sheet.alpha_composite(big, (x, y))
            if col == 0:
                ImageDraw.Draw(sheet).text((gap, y - label_h + 2), style, fill=(232, 255, 249, 255), font=font)
        # 单风格六表情
        one = Image.new("RGBA", (sheet_w, H * scale + gap * 2), (16, 24, 32, 255))
        for col, expr in enumerate(EXPRESSIONS):
            img = draw(style, expr)
            big = img.resize((W * scale, H * scale), Image.NEAREST)
            one.alpha_composite(big, (gap + col * (W * scale + gap), gap))
        one.save(ROOT / f"avatar_{style}.png")

    sheet.save(ROOT / "avatar_all.png")
    print("saved", ROOT / "avatar_all.png")
    for s in order:
        print("saved", ROOT / f"avatar_{s}.png")


if __name__ == "__main__":
    main()
