# toy_finder（色でおもちゃを探して近づく＋文章で頼める）

指定した色のおもちゃを探して、近づいて止まるROS 2ノードです。ROS 2 Humble と Gazebo（Classic）の TurtleBot3 waffle_pi を想定しています。

## 動作確認の状況
- 第1段階（赤いボールを探して近づく）は、ROS 2 Humble + Gazebo で動作を確認済み（2026-11-01）。
- 色の検出・行動の判断・文章の読み取り（`detector.py` / `behavior.py` / `command_parser.py`）は、ROSなしの単体テスト20件で確認済み。
- 第2段階（`ask` ノードと色の切り替え）は、ROSの部分を差し替えた簡易テストまで。**Gazebo上での動作はこれから確認**。

## 0.3.0 での変更点（第2段階：文章で頼める）
- `ask` ノードを追加。「青いボールを探して」のような文章を、LLM（Claude）で探す色に変換して `/target_color` に送る
- `seeker` は `/target_color` で探す色を途中から切り替えられる。`stop` で停止
- `wait_for_command` パラメータ：true なら指示が来るまで動かずに待つ
- APIキーがない・通信できないときは、キーワード（赤・青・緑・黄・止まって）で判定する
- 青・緑のボールのモデルを追加

## 0.2.0 での変更点
- カメラをセンサ用のQoSで購読（Gazeboのカメラ画像が届かない問題の対策）
- 検出前に画像を横320pxに縮小（高解像度カメラでも処理が遅れないように）
- 一瞬見失っても、すぐには探索に戻らない。探すときは最後に見えた方向へ回る
- 到着後はボールが画面から外れても止まったまま
- 画像が1秒以上来なければ停止。起動後5秒たっても画像が来なければ警告を表示
- `use_stamped` パラメータで `TwistStamped` にも切り替え可能（Humbleでは不要）
- Gazebo に置く赤いボール（`models/red_ball.sdf`）を同梱

## 1. セットアップ
```bash
# TurtleBot3 のシミュレーション用パッケージ（未導入なら）
sudo apt install ros-humble-turtlebot3-gazebo ros-humble-cv-bridge python3-opencv

# ROS 2のワークスペースのsrcに、このフォルダごと置く
cd ~/ros2_ws/src
cp -r /path/to/toy_finder .

cd ~/ros2_ws
colcon build --packages-select toy_finder
source install/setup.bash
```

## 2. シミュレータを起動して赤いボールを置く
ターミナル1：
```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_gazebo empty_world.launch.py
```

ターミナル2（ロボットの前方 1.5 m、少し左にボールを置く）：
```bash
source ~/ros2_ws/install/setup.bash
ros2 run gazebo_ros spawn_entity.py -entity red_ball \
  -file $(ros2 pkg prefix toy_finder)/share/toy_finder/models/red_ball.sdf \
  -x 1.5 -y 0.5 -z 0.1
```
ボールを後ろに置く（例：`-x -1.5`）と、回って探すところから確認できます。

## 3. 実行
ターミナル3：
```bash
source ~/ros2_ws/install/setup.bash
ros2 run toy_finder seeker --ros-args -p target_color:=red
```

うまくいくと、ログが次のように出ます。
```
画像を受信しました（...）
状態: SEARCH -> APPROACH
状態: APPROACH -> ARRIVED
```

色は `red` / `blue` / `green` / `yellow` から選べます。

## 4. 文章で頼む（第2段階）
LLMを使うには、Claude の API キーが必要です（[console.anthropic.com](https://console.anthropic.com) の API Keys で作成）。キーがなくても、キーワード判定で動きます。

```bash
pip install anthropic
export ANTHROPIC_API_KEY=ここにキー   # ask を動かすターミナルで設定する
```

ボールを2色置く（ターミナル2）：
```bash
ros2 run gazebo_ros spawn_entity.py -entity red_ball -file $(ros2 pkg prefix toy_finder)/share/toy_finder/models/red_ball.sdf -x 1.5 -y 0.8 -z 0.1
ros2 run gazebo_ros spawn_entity.py -entity blue_ball -file $(ros2 pkg prefix toy_finder)/share/toy_finder/models/blue_ball.sdf -x -1.5 -y -0.8 -z 0.1
```

seeker を指示待ちで起動（ターミナル3）：
```bash
ros2 run toy_finder seeker --ros-args -p wait_for_command:=true
```

文章で頼む（ターミナル4）：
```bash
ros2 run toy_finder ask
> 青いボールを探して
```
ログに `指示「青いボールを探して」→ 色=blue（llm）` と出て、ロボットが青いボールを探し始めます。`（keyword）` と出た場合は、LLMではなくキーワードで判定しています（APIキーを確認してください）。

## 5. うまく動かないとき
- **「画像がまだ1枚も届いていません」と出る：** カメラのトピック名が違う。`ros2 topic list | grep image` で確認し、`-p image_topic:=/見つかった名前` を付ける。
- **回り続けて見つけない：** `ros2 run rqt_image_view rqt_image_view` でカメラ画像にボールが映っているか確認する。映っているのに見つけない場合は、`detector.py` の赤のしきい値（S・V の下限 120 / 70）を下げる。
- **ぶつかる／手前で止まらない：** `-p arrived_area_ratio:=0.10` のように数値を小さくすると、手前で止まる。
- **ロボットが動かない：** `ros2 topic info /cmd_vel` で型を確認する。`TwistStamped` なら `-p use_stamped:=true` を付ける。

## パラメータ一覧
| 名前 | 既定値 | 意味 |
|---|---|---|
| `target_color` | `red` | 探す色 |
| `image_topic` | `/camera/image_raw` | カメラ画像のトピック |
| `cmd_vel_topic` | `/cmd_vel` | 速度指令のトピック |
| `use_stamped` | `false` | 速度指令を `TwistStamped` で送る |
| `search_angular_speed` | `0.4` | 探すときの回転速度 (rad/s) |
| `approach_linear_speed` | `0.12` | 近づくときの前進速度 (m/s) |
| `turn_gain` | `1.2` | 中央からのずれに対する回転の強さ |
| `arrived_area_ratio` | `0.15` | これ以上大きく映ったら到着 |
| `lost_frames_to_search` | `10` | 何フレーム続けて見失ったら探索に戻るか |
| `max_width` | `320` | 検出前に縮小する横幅 (px)。0で縮小しない |
| `image_timeout` | `1.0` | この秒数画像が来なければ停止 |
| `wait_for_command` | `false` | true なら `/target_color` の指示が来るまで待つ |

## テスト
```bash
cd ~/ros2_ws/src/toy_finder
python3 -m pytest test/
```

## ファイル構成
- `toy_finder/detector.py` : 画像から色の塊を見つける（ROS非依存）
- `toy_finder/behavior.py` : 探す→近づく→止まるの判断（ROS非依存）
- `toy_finder/seeker_node.py` : 上の2つをつなぐROSノード
- `toy_finder/command_parser.py` : 文章を色に変換する（LLM＋キーワード、ROS非依存）
- `toy_finder/ask_node.py` : 文章を受け取り `/target_color` に送るROSノード
- `models/*_ball.sdf` : Gazeboに置く赤・青・緑のボール
- `test/` : 単体テスト
