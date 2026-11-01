# toy_finder（第1段階：色でおもちゃを探して近づく）

指定した色のおもちゃを探して、近づいて止まるROS 2ノードです。

## 動作確認の状況
- 色の検出部分（`detector.py`）は、疑似画像でテスト済み（`test/test_detector.py`）。
- ROSノード（`seeker_node.py`）は、構文チェックのみ。**ROS 2とGazeboでの実動作は未確認**。

## 1. セットアップ
```bash
# ROS 2のワークスペースのsrcに、このフォルダごと置く
cd ~/ros2_ws/src
cp -r /path/to/toy_finder .

cd ~/ros2_ws
colcon build --packages-select toy_finder
source install/setup.bash
```

## 2. 実行
別のターミナルで、先にシミュレータとロボットを起動しておく（カメラ付きのロボットが必要）。

```bash
ros2 run toy_finder seeker --ros-args -p target_color:=red
```

色は `red` / `blue` / `green` / `yellow` から選べます。

## 3. トピック名が違うとき
ロボットによってカメラや速度指令のトピック名が違います。次で確認し、合わなければパラメータで合わせます。

```bash
ros2 topic list | grep -E "image|cmd_vel"

ros2 run toy_finder seeker --ros-args \
  -p image_topic:=/あなたのカメラのトピック \
  -p cmd_vel_topic:=/あなたの速度指令のトピック
```

## 4. うまく動かないとき
- **回り続けて見つけない：** ボールが赤くない、またはカメラに映っていない。`rqt_image_view` でカメラ画像を確認する。
- **ぶつかる／手前で止まらない：** `-p arrived_area_ratio:=0.10` のように数値を小さくすると、手前で止まる。
- **ロボットが動かない：** 新しいバージョンのROS 2では、速度指令が `Twist` ではなく `TwistStamped` の場合がある。その場合はエラー内容を教えてください。

## ファイル構成
- `toy_finder/detector.py` : 画像から色の塊を見つける（ROS非依存）
- `toy_finder/seeker_node.py` : 探す→近づく→止まる、のROSノード
- `test/test_detector.py` : 検出部分のテスト
