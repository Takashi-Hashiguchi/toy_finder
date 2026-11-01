"""detector.py の単体テスト。ROSなしで動く。  実行: python3 -m pytest test/ または python3 test/test_detector.py"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from toy_finder.detector import find_color_blob  # noqa: E402


def make_image(color_bgr, center, radius, size=(480, 640)):
    img = np.full((size[0], size[1], 3), 200, dtype=np.uint8)  # 灰色の背景
    cv2.circle(img, center, radius, color_bgr, -1)
    return img


def test_finds_red_ball_on_left():
    img = make_image((0, 0, 255), (100, 240), 40)  # BGRの赤
    r = find_color_blob(img, "red")
    assert r.found
    assert r.center_x < 0.3  # 画面の左寄り


def test_finds_red_ball_on_right():
    img = make_image((0, 0, 255), (540, 240), 40)
    r = find_color_blob(img, "red")
    assert r.found
    assert r.center_x > 0.7


def test_bigger_ball_has_bigger_area():
    small = find_color_blob(make_image((0, 0, 255), (320, 240), 20), "red")
    big = find_color_blob(make_image((0, 0, 255), (320, 240), 80), "red")
    assert big.area_ratio > small.area_ratio


def test_does_not_find_other_color():
    img = make_image((255, 0, 0), (320, 240), 40)  # BGRの青
    assert not find_color_blob(img, "red").found
    assert find_color_blob(img, "blue").found


def test_nothing_found_on_plain_background():
    img = np.full((480, 640, 3), 200, dtype=np.uint8)
    assert not find_color_blob(img, "red").found


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK:", name)
