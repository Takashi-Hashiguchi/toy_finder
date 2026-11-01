"""色でおもちゃ（ボール）を見つける処理。

ROSに依存しない純粋な関数だけを置く。
こうしておくと、ROSなしでも単体でテストできる。
"""
from dataclasses import dataclass

import cv2
import numpy as np

# OpenCVのHSVは H=0..179, S=0..255, V=0..255。
# 赤はHが0付近と179付近の両側にまたがるので、範囲を2つ持つ。
COLOR_RANGES = {
    "red": [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (179, 255, 255))],
    "blue": [((100, 120, 70), (130, 255, 255))],
    "green": [((40, 80, 70), (80, 255, 255))],
    "yellow": [((20, 120, 70), (35, 255, 255))],
}

# 画像全体に対して、これ未満の大きさの色の塊はノイズとして無視する割合
MIN_AREA_RATIO = 0.0005

# 検出前に、画像の横幅をこの大きさまで縮小する（処理を軽くするため）。
# 結果は「割合」で返すので、縮小しても center_x / area_ratio の意味は変わらない。
DEFAULT_MAX_WIDTH = 320


@dataclass
class Detection:
    """見つけた結果。"""

    found: bool
    # 塊の中心の横位置。画像の左端が0.0、右端が1.0。見つからなければ0.5。
    center_x: float = 0.5
    # 塊が画像全体に占める割合。大きいほどロボットに近い。
    area_ratio: float = 0.0


def find_color_blob(
    bgr_image: np.ndarray, color: str, max_width: int = DEFAULT_MAX_WIDTH
) -> Detection:
    """画像の中から、指定した色の一番大きい塊を探す。

    max_width より横幅が大きい画像は、縮小してから処理する（0以下なら縮小しない）。
    """
    if color not in COLOR_RANGES:
        raise ValueError(f"未対応の色です: {color}（使える色: {list(COLOR_RANGES)}）")

    width = bgr_image.shape[1]
    if 0 < max_width < width:
        scale = max_width / float(width)
        bgr_image = cv2.resize(
            bgr_image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
        )

    hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)

    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for low, high in COLOR_RANGES[color]:
        mask |= cv2.inRange(hsv, np.array(low), np.array(high))

    # 小さな点ノイズを消す
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return Detection(found=False)

    biggest = max(contours, key=cv2.contourArea)
    height, width = mask.shape
    area_ratio = cv2.contourArea(biggest) / float(width * height)
    if area_ratio < MIN_AREA_RATIO:
        return Detection(found=False)

    moments = cv2.moments(biggest)
    if moments["m00"] == 0:
        return Detection(found=False)
    center_x = (moments["m10"] / moments["m00"]) / width

    return Detection(found=True, center_x=center_x, area_ratio=area_ratio)
