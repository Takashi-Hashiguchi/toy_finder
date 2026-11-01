"""指定した色のおもちゃを探して、近づいて止まるROS 2ノード。

動き方:
  SEARCH   : 見つかるまでその場でゆっくり回る
  APPROACH : 見つけたら、画面の中央に捉えながら前進する
  ARRIVED  : 十分近づいたら止まる
"""
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Image

from toy_finder.detector import find_color_blob

SEARCH = "SEARCH"
APPROACH = "APPROACH"
ARRIVED = "ARRIVED"


class SeekerNode(Node):
    def __init__(self):
        super().__init__("toy_seeker")

        # パラメータ（起動時に --ros-args -p で変えられる）
        self.declare_parameter("target_color", "red")
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("search_angular_speed", 0.4)  # rad/s
        self.declare_parameter("approach_linear_speed", 0.12)  # m/s
        self.declare_parameter("turn_gain", 1.2)  # 中央からのずれに対する回転の強さ
        self.declare_parameter("arrived_area_ratio", 0.15)  # これ以上大きく映ったら到着

        self.bridge = CvBridge()
        self.state = SEARCH

        self.cmd_pub = self.create_publisher(
            Twist, self.get_parameter("cmd_vel_topic").value, 10
        )
        self.create_subscription(
            Image, self.get_parameter("image_topic").value, self.on_image, 10
        )
        self.get_logger().info(
            f"開始: 色={self.get_parameter('target_color').value} を探します"
        )

    def on_image(self, msg: Image):
        color = self.get_parameter("target_color").value
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        result = find_color_blob(frame, color)

        cmd = Twist()
        previous_state = self.state

        if not result.found:
            self.state = SEARCH
            cmd.angular.z = float(self.get_parameter("search_angular_speed").value)
        elif result.area_ratio >= self.get_parameter("arrived_area_ratio").value:
            self.state = ARRIVED  # 速度は0のまま = 停止
        else:
            self.state = APPROACH
            # 画面の中央(0.5)からのずれ。左にあれば正（左回り）。
            error = 0.5 - result.center_x
            cmd.angular.z = float(self.get_parameter("turn_gain").value) * error
            cmd.linear.x = float(self.get_parameter("approach_linear_speed").value)

        if self.state != previous_state:
            self.get_logger().info(f"状態: {previous_state} -> {self.state}")

        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = SeekerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist())  # 終了時に止める
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
