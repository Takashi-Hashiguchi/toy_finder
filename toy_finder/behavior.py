"""探す→近づく→止まる、の判断部分。

ROSに依存しない。検出結果を受け取り、次の状態と速度（前進・回転）を返す。
こうしておくと、ROSなしでも単体でテストできる。
"""
from dataclasses import dataclass

from toy_finder.detector import Detection

SEARCH = "SEARCH"
APPROACH = "APPROACH"
ARRIVED = "ARRIVED"


@dataclass
class Params:
    search_angular_speed: float = 0.4  # rad/s。探すときの回転の速さ
    approach_linear_speed: float = 0.12  # m/s。近づくときの前進の速さ
    turn_gain: float = 1.2  # 中央からのずれに対する回転の強さ
    arrived_area_ratio: float = 0.15  # これ以上大きく映ったら到着
    lost_frames_to_search: int = 10  # 何フレーム続けて見失ったら探索に戻るか


@dataclass
class Command:
    linear_x: float = 0.0
    angular_z: float = 0.0


class SeekerBehavior:
    def __init__(self, params: Params):
        self.params = params
        self.state = SEARCH
        self.lost_count = 0
        # 最後に見えた方向。+1 なら左（左回りで探す）、-1 なら右。
        self.last_side = 1.0

    def step(self, result: Detection) -> Command:
        p = self.params

        if result.found:
            self.lost_count = 0
            error = 0.5 - result.center_x  # 左にあれば正
            if error != 0.0:
                self.last_side = 1.0 if error > 0 else -1.0

            if result.area_ratio >= p.arrived_area_ratio:
                self.state = ARRIVED
                return Command()
            if self.state == ARRIVED and result.area_ratio >= p.arrived_area_ratio * 0.8:
                # 到着直後に少し小さく映っただけで再発進しないよう、余裕を持たせる
                return Command()

            self.state = APPROACH
            return Command(
                linear_x=p.approach_linear_speed, angular_z=p.turn_gain * error
            )

        # 見えていない
        self.lost_count += 1
        if self.state == ARRIVED:
            # 近づくとボールがカメラの下に外れることがある。到着後はそのまま止まる。
            return Command()
        if self.state == APPROACH and self.lost_count < p.lost_frames_to_search:
            # 一瞬見失っただけかもしれないので、前進はやめて最後に見えた方向へ少し回る
            return Command(angular_z=0.5 * p.search_angular_speed * self.last_side)

        self.state = SEARCH
        return Command(angular_z=p.search_angular_speed * self.last_side)
