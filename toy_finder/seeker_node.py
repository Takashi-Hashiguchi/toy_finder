"""指定した色のおもちゃを探して、近づいて止まるROS 2ノード（ROS 2 Humble 想定）。

動き方:
  SEARCH   : 見つかるまでその場でゆっくり回る（最後に見えた方向へ）
  APPROACH : 見つけたら、画面の中央に捉えながら前進する
  ARRIVED  : 十分近づいたら止まる

判断の中身は behavior.py、色の検出は detector.py にある。
"""
import time

import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from toy_finder.behavior import Command, Params, SeekerBehavior
from toy_finder.detector import find_color_blob


class SeekerNode(Node):
    def __init__(self):
        super().__init__("toy_seeker")

        # パラメータ（起動時に --ros-args -p で変えられる）
        self.declare_parameter("target_color", "red")
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        # Humble の TurtleBot3 は Twist。新しい構成で TwistStamped が必要なら true にする
        self.declare_parameter("use_stamped", False)
        self.declare_parameter("search_angular_speed", 0.4)  # rad/s
        self.declare_parameter("approach_linear_speed", 0.12)  # m/s
        self.declare_parameter("turn_gain", 1.2)  # 中央からのずれに対する回転の強さ
        self.declare_parameter("arrived_area_ratio", 0.15)  # これ以上大きく映ったら到着
        self.declare_parameter("lost_frames_to_search", 10)  # 続けて見失ったら探索へ
        self.declare_parameter("max_width", 320)  # 検出前に縮小する横幅(px)
        self.declare_parameter("image_timeout", 1.0)  # 秒。画像が来なければ停止

        def param(name):
            return self.get_parameter(name).value

        self.behavior = SeekerBehavior(
            Params(
                search_angular_speed=float(param("search_angular_speed")),
                approach_linear_speed=float(param("approach_linear_speed")),
                turn_gain=float(param("turn_gain")),
                arrived_area_ratio=float(param("arrived_area_ratio")),
                lost_frames_to_search=int(param("lost_frames_to_search")),
            )
        )
        self.bridge = CvBridge()
        self.use_stamped = bool(param("use_stamped"))
        self.start_time = time.monotonic()
        self.last_image_time = None
        self.timed_out = False
        self.warned_no_image = False

        msg_type = TwistStamped if self.use_stamped else Twist
        self.cmd_pub = self.create_publisher(msg_type, param("cmd_vel_topic"), 10)
        # Gazebo のカメラは BEST_EFFORT で配信されることがあるので、センサ用QoSで購読する
        self.create_subscription(
            Image, param("image_topic"), self.on_image, qos_profile_sensor_data
        )
        # 画像が途切れたときに止めるための見張り
        self.create_timer(0.2, self.on_watchdog)

        self.get_logger().info(
            f"開始: 色={param('target_color')} を探します"
            f"（画像={param('image_topic')}, 速度指令={param('cmd_vel_topic')}）"
        )

    def publish(self, command: Command):
        twist = Twist()
        twist.linear.x = float(command.linear_x)
        twist.angular.z = float(command.angular_z)
        if self.use_stamped:
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.twist = twist
            self.cmd_pub.publish(msg)
        else:
            self.cmd_pub.publish(twist)

    def on_image(self, msg: Image):
        if self.last_image_time is None:
            self.get_logger().info(f"画像を受信しました（{msg.width}x{msg.height}）")
        self.last_image_time = time.monotonic()
        if self.timed_out:
            self.get_logger().info("画像の受信が再開しました")
            self.timed_out = False

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        result = find_color_blob(
            frame,
            self.get_parameter("target_color").value,
            max_width=int(self.get_parameter("max_width").value),
        )

        previous_state = self.behavior.state
        command = self.behavior.step(result)
        if self.behavior.state != previous_state:
            self.get_logger().info(f"状態: {previous_state} -> {self.behavior.state}")
        self.publish(command)

    def on_watchdog(self):
        timeout = float(self.get_parameter("image_timeout").value)
        if self.last_image_time is None:
            if not self.warned_no_image and time.monotonic() - self.start_time > 5.0:
                self.get_logger().warn(
                    "画像がまだ1枚も届いていません。image_topic の名前を確認してください"
                    "（ros2 topic list | grep image）"
                )
                self.warned_no_image = True
            return
        if time.monotonic() - self.last_image_time > timeout:
            if not self.timed_out:
                self.get_logger().warn(f"{timeout}秒以上画像が来ないので停止します")
                self.timed_out = True
            self.publish(Command())


def main(args=None):
    rclpy.init(args=args)
    node = SeekerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish(Command())  # 終了時に止める
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
