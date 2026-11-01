"""behavior.py の単体テスト。ROSなしで動く。  実行: python3 -m pytest test/"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from toy_finder.behavior import APPROACH, ARRIVED, SEARCH, Params, SeekerBehavior  # noqa: E402
from toy_finder.detector import Detection  # noqa: E402

NOT_FOUND = Detection(found=False)


def seen(center_x=0.5, area_ratio=0.02):
    return Detection(found=True, center_x=center_x, area_ratio=area_ratio)


def test_searches_by_turning_when_nothing_seen():
    b = SeekerBehavior(Params())
    cmd = b.step(NOT_FOUND)
    assert b.state == SEARCH
    assert cmd.linear_x == 0.0 and cmd.angular_z > 0.0


def test_approaches_and_turns_toward_ball():
    b = SeekerBehavior(Params())
    cmd = b.step(seen(center_x=0.2))  # 左寄り
    assert b.state == APPROACH
    assert cmd.linear_x > 0.0 and cmd.angular_z > 0.0  # 左へ回りながら前進
    cmd = b.step(seen(center_x=0.8))  # 右寄り
    assert cmd.angular_z < 0.0


def test_stops_when_close_enough():
    b = SeekerBehavior(Params(arrived_area_ratio=0.15))
    cmd = b.step(seen(area_ratio=0.2))
    assert b.state == ARRIVED
    assert cmd.linear_x == 0.0 and cmd.angular_z == 0.0


def test_brief_loss_does_not_restart_search():
    b = SeekerBehavior(Params(lost_frames_to_search=5))
    b.step(seen(center_x=0.8))
    for _ in range(4):
        cmd = b.step(NOT_FOUND)
        assert b.state == APPROACH
        assert cmd.linear_x == 0.0
    b.step(NOT_FOUND)
    assert b.state == SEARCH


def test_searches_toward_last_seen_side():
    b = SeekerBehavior(Params(lost_frames_to_search=1))
    b.step(seen(center_x=0.9))  # 右側で見えた
    cmd = b.step(NOT_FOUND)
    assert b.state == SEARCH
    assert cmd.angular_z < 0.0  # 右回りで探す


def test_stays_stopped_after_arrival_even_if_ball_leaves_view():
    b = SeekerBehavior(Params())
    b.step(seen(area_ratio=0.2))
    for _ in range(30):
        cmd = b.step(NOT_FOUND)
    assert b.state == ARRIVED
    assert cmd.linear_x == 0.0 and cmd.angular_z == 0.0


def test_no_restart_on_small_size_jitter_after_arrival():
    b = SeekerBehavior(Params(arrived_area_ratio=0.15))
    b.step(seen(area_ratio=0.16))
    cmd = b.step(seen(area_ratio=0.14))
    assert b.state == ARRIVED and cmd.linear_x == 0.0
