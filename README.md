
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
│   ├── goal_markers.py          hiển thị/ghi goal nhấp bằng Publish Point trong RViz2
│   └── yolo_detector.py         nhận diện vật thể bằng YOLO từ camera
├── config/goals.yaml            tọa độ (x, y, yaw) các goal trong hệ map
├── maps/                        map.yaml + map.pgm (bản gốc SLAM), map_clean.* (đã làm sạch)
├── worlds/, models/             world small_house (AWS RoboMaker, MIT-0) bản nhẹ
├── scripts/                     demo_run.sh, demo_record.sh, stop_all.sh, check_topics.sh,
│                                install_world.sh, lighten_sensors.sh, camera_rate.sh
├── tools/yolo_summary.py        tóm tắt log YOLO + goal_navigator thành bảng, xuất markdown
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
## 3. Chạy

```bash
ros2 launch tb4_yolo lab05.launch.py world:=small_house x:=1.0 y:=1.0 save_dir:=$HOME/yolo_out
```
Chạy từng phần (mỗi lệnh một terminal):

```bash
ros2 launch tb4_yolo lab05.launch.py run_navigator:=false
ros2 run tb4_yolo goal_navigator --ros-args -p use_sim_time:=true -p goals_file:=$HOME/tb4_ws/src/Tb4_YOLO/config/goals.yaml
ros2 run tb4_yolo yolo_detector --ros-args -p use_sim_time:=true -p conf:=0.3
```

Tham số hay dùng: `model` (`yolov8n.pt`, `yolo11n.pt`, ...), `conf` (mặc định 0.4), `imgsz` (mặc định 640), `image_topic` (mặc định `/oakd/rgb/preview/image_raw`), `rate` (số khung xử lý mỗi giây, mặc định 2), `dwell`. Mặc định không mở cửa sổ OpenCV, xem ảnh nhận diện trong RViz2: Add → By topic → `/yolo/image` → Image (hoặc `show_window:=true` để mở lại cửa sổ OpenCV).

