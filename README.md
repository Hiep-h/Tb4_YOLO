# Bài thực hành 05 – TurtleBot 4: Localization, Navigation bằng code và nhận diện vật thể YOLO

TurtleBot 4 trong Gazebo (Ignition Fortress, ROS 2 Humble): nạp bản đồ đã quét ở Bài 04, định vị bằng AMCL, viết node gửi tuần tự các goal tới Nav2 và node YOLO nhận diện vật thể từ camera RGB.

- Sinh viên: Vũ Văn Hiệp – MSSV 230200742
- Package `tb4_yolo`. Launch file bọc các launch có sẵn của TurtleBot 4; hai node tự viết là `goal_navigator` và `yolo_detector`.
- Video demo: _cập nhật sau khi upload_

## 1. Cấu trúc repo

```
Tb4_YOLO/
├── launch/
│   ├── sim.launch.py            TurtleBot 4 trong Gazebo
│   ├── localization.launch.py   nạp map + AMCL + RViz2
│   ├── navigation.launch.py     Nav2
│   ├── nav_demo.launch.py       Gazebo + AMCL + Nav2 + RViz2 (một lệnh)
│   └── lab05.launch.py          nav_demo + node goal + node YOLO
├── tb4_yolo/
│   ├── goal_navigator.py        gửi goal tuần tự bằng nav2_simple_commander
│   └── yolo_detector.py         nhận diện vật thể bằng YOLO từ camera
├── config/goals.yaml            tọa độ (x, y, yaw) các goal trong hệ map
├── maps/                        map.yaml + map.pgm (bản gốc SLAM), map_clean.* (đã làm sạch)
├── worlds/, models/             world small_house (AWS RoboMaker, MIT-0) bản nhẹ
├── scripts/                     check_topics.sh, install_world.sh, lighten_sensors.sh, camera_rate.sh
└── package.xml, setup.py, setup.cfg
```

## 2. Cài đặt

Ubuntu 22.04, ROS 2 Humble Desktop.

```bash
sudo apt update
sudo apt install -y ros-humble-turtlebot4-simulator ros-humble-turtlebot4-desktop \
  ros-humble-turtlebot4-navigation ros-humble-nav2-bringup ros-humble-nav2-map-server \
  ros-humble-nav2-simple-commander ros-humble-cv-bridge python3-opencv
pip install ultralytics
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

mkdir -p ~/tb4_ws/src && cd ~/tb4_ws/src
git clone https://github.com/Hiep-h/Tb4_YOLO.git
cd ~/tb4_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tb4_yolo --symlink-install
source install/setup.bash
```

Nếu `cv_bridge` báo lỗi liên quan numpy sau khi cài `ultralytics`: `pip install "numpy<2"`.

World `small_house` cần cài vào gói `turtlebot4_ignition_bringup` một lần (cần `sudo`):

```bash
~/tb4_ws/src/Tb4_YOLO/scripts/install_world.sh
```

Gazebo dựng bằng phần mềm trên card Intel nên chậm. Giảm tải LiDAR và đặt camera đủ nhanh cho YOLO (5 Hz mô phỏng):

```bash
~/tb4_ws/src/Tb4_YOLO/scripts/lighten_sensors.sh
~/tb4_ws/src/Tb4_YOLO/scripts/camera_rate.sh 5
```

## 3. Chạy

```bash
ros2 launch tb4_yolo lab05.launch.py world:=small_house x:=1.0 y:=1.0 save_dir:=$HOME/yolo_out
```

Launch chờ Gazebo sẵn sàng, chạy AMCL với `maps/map_clean.yaml`, đặt vị trí ban đầu (0, 0, 0), bật Nav2 và RViz2. Sau đó `goal_navigator` tự đi qua Goal 1 → 2 → 3 (dừng 5 s mỗi goal) và panel YOLO trong RViz2 (topic `/yolo/image`) hiển thị kết quả nhận diện. Ctrl+C dừng node YOLO, node in danh sách lớp đã thấy. Không điều khiển thủ công và không đặt goal bằng chuột.

Dùng bản đồ gốc: thêm `map:=$HOME/tb4_ws/src/Tb4_YOLO/maps/map.yaml`.

Chạy từng phần (mỗi lệnh một terminal):

```bash
ros2 launch tb4_yolo lab05.launch.py run_navigator:=false
ros2 run tb4_yolo goal_navigator --ros-args -p use_sim_time:=true -p goals_file:=$HOME/tb4_ws/src/Tb4_YOLO/config/goals.yaml
ros2 run tb4_yolo yolo_detector --ros-args -p use_sim_time:=true -p conf:=0.3
```

Tham số hay dùng: `model` (`yolov8n.pt`, `yolo11n.pt`, ...), `conf` (mặc định 0.4), `imgsz` (mặc định 640), `image_topic` (mặc định `/oakd/rgb/preview/image_raw`), `rate` (số khung xử lý mỗi giây, mặc định 2), `dwell`. Mặc định không mở cửa sổ OpenCV, xem ảnh nhận diện trong RViz2: Add → By topic → `/yolo/image` → Image (hoặc `show_window:=true` để mở lại cửa sổ OpenCV).

## 4. Chạy demo quay video

```bash
~/tb4_ws/src/Tb4_YOLO/scripts/demo_record.sh
```

Mỗi lần chạy (không có tham số), script luôn đưa hệ thống về trạng thái ban đầu: nếu đang chạy thì dọn sạch bằng `stop_all.sh` rồi khởi động lại từ đầu bằng `demo_run.sh` (robot spawn lại ở điểm xuất phát); nếu chưa chạy thì khởi động mới. Sau khi AMCL và Nav2 active, script gửi lại `/initialpose` (0, 0, 0) vài lần và kiểm tra `/amcl_pose` có về gần gốc không, reset danh sách goal (`/reset_goals` + xóa `~/tb4_clicked_goals.yaml`), rồi mở 3 cửa sổ terminal nhỏ: **LOG YOLO/GOAL** (log lọc theo node), **CLICKED POINT** (toạ độ điểm vừa nhấp), **GOAL NAVIGATOR** (`goal_navigator` chạy với `wait_for_goals:=3`, tự chờ đủ 3 điểm nhấp rồi mới bắt đầu đi). Nếu máy không có `gnome-terminal`, script in sẵn các lệnh để tự mở. Cuối script in tóm tắt vị trí AMCL hiện tại và các lệnh hay dùng.

Tham số:
- `--reuse`: giữ nguyên hệ thống đang chạy (không dọn, không khởi động lại) — script chỉ in cảnh báo "robot co the dang o cho cu" rồi vẫn gửi lại initialpose và reset goal như bình thường.
- `--reset-only`: dùng khi muốn nhấp lại 3 điểm mà chưa cần chạy lại từ đầu — chỉ gửi lại `/initialpose` và reset goal trên hệ thống đang chạy, không dọn và không mở lại 3 cửa sổ (trừ khi cửa sổ GOAL NAVIGATOR đã bắt đầu đi các goal cũ, lúc đó script cảnh báo cần Ctrl+C cửa sổ đó và tự mở lại cửa sổ GOAL NAVIGATOR mới). Yêu cầu hệ thống đã chạy từ trước.

Trong RViz2 bật **Publish Point** và nhấp 3 điểm trên bản đồ (tránh sát vật cản); cửa sổ GOAL NAVIGATOR tự đi qua lần lượt 3 điểm và in bảng tổng kết khi xong. Nhấp nhầm thì reset lại bằng `ros2 service call /reset_goals std_srvs/srv/Empty {}`; cần gửi lại vị trí khởi tạo thì chạy lại `demo_record.sh --reset-only` hoặc tự publish `/initialpose` (lệnh in sẵn ở cuối script).

## 5. Tọa độ goal

Bật **Publish Point** trong RViz2, nhấp lên bản đồ và đọc `ros2 topic echo /clicked_point`; hoặc đặt robot tại vị trí đó và đọc `ros2 topic echo /amcl_pose --once`. Sửa `config/goals.yaml` (`yaw_deg` là hướng quay tính bằng độ). Tọa độ là tọa độ `map`, gốc tại điểm xuất phát của robot lúc vẽ bản đồ.

Tọa độ mặc định trong file là ước lượng từ ảnh bản đồ, cần kiểm tra lại trên máy và chọn điểm trống, cách vật cản xa.

## 6. Topic, action và node chính

| Thành phần | Vai trò |
|---|---|
| `/map`, `/amcl_pose`, `/initialpose` | bản đồ, vị trí ước lượng, vị trí ban đầu |
| `/scan`, `/odom`, `/tf` | LiDAR, odometry, khung tọa độ |
| `/navigate_to_pose` (action) | `goal_navigator` gửi goal tới `bt_navigator` |
| `/cmd_vel` | lệnh vận tốc từ Nav2 |
| `/oakd/rgb/preview/image_raw` | ảnh camera RGB đầu vào của YOLO |
| `/yolo/image`, `/yolo/detections` | ảnh đã vẽ khung; danh sách vật thể (JSON) |

YOLO tiền huấn luyện COCO chỉ nhận ra các lớp như `chair`, `couch`, `bed`, `tv`, `refrigerator`, `dining table`, `person`, `potted plant`. Có thể thêm mô hình vào `worlds/small_house.sdf` bằng thẻ `<include>` để có thêm vật thể dễ nhận.
