"""文章でロボットに頼むためのノード（第2段階）。

ターミナルに「青いボールを探して」のように打ち込むと、LLMで探す色に変換し、
/target_color に送る。seeker ノードがそれを受けて探し始める。

使い方:
  ros2 run toy_finder ask                      # 対話形式で何度でも頼める
  ros2 run toy_finder ask "赤いボールを探して"   # 1回だけ頼む
"""
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String

from toy_finder.command_parser import make_client, parse_command


class AskNode(Node):
    def __init__(self):
        super().__init__("toy_ask")
        self.pub = self.create_publisher(String, "/target_color", 10)
        self.client = make_client(logger=self.get_logger().warn)
        mode = "LLM（Claude）" if self.client is not None else "キーワード"
        self.get_logger().info(f"準備完了: {mode}で文章を読み取ります")

    def ask(self, text: str):
        result = parse_command(text, self.client, logger=self.get_logger().warn)
        self.get_logger().info(
            f"指示「{text}」→ 色={result.color}（{result.source}）／ロボット「{result.reply}」"
        )
        if result.color == "unknown":
            return
        # seeker と繋がる前に送ると届かないので、少しだけ待つ
        deadline = time.monotonic() + 3.0
        while self.pub.get_subscription_count() == 0 and time.monotonic() < deadline:
            time.sleep(0.1)
        if self.pub.get_subscription_count() == 0:
            self.get_logger().warn("seeker が見つかりません。先に seeker を起動してください")
        self.pub.publish(String(data=result.color))


def main(args=None):
    rclpy.init(args=args)
    node = AskNode()

    # 入力を待つ間も通信を処理できるよう、別スレッドで回す
    def spin():
        try:
            rclpy.spin(node)
        except Exception:
            pass  # 終了時の例外は無視する

    spinner = threading.Thread(target=spin, daemon=True)
    spinner.start()

    words = remove_ros_args(sys.argv)[1:]
    try:
        if words:
            node.ask(" ".join(words))
            # 送信が届くまで少し待つ
            threading.Event().wait(1.0)
        else:
            print("ロボットへのお願いを入力してください（終了は Ctrl+C）")
            while rclpy.ok():
                text = input("> ").strip()
                if text:
                    node.ask(text)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
