#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=~/lab05_launch.log
CLICKED=~/tb4_clicked_goals.yaml

set +u
source /opt/ros/humble/setup.bash
source ~/tb4_ws/install/setup.bash
set -u

bt_state=$(ros2 lifecycle get /bt_navigator 2>/dev/null)
if echo "$bt_state" | grep -qE '^active'; then
    echo "He thong da chay (bt_navigator active), dung luon."
else
    echo "He thong chua chay, khoi dong bang demo_run.sh..."
    bash "$SCRIPT_DIR/demo_run.sh"
fi

echo "Dat lai danh sach goal da nhap (trong) de nhap moi cho video..."
ros2 service call /reset_goals std_srvs/srv/Empty {} >/dev/null 2>&1
rm -f "$CLICKED"

ROS_SETUP='source /opt/ros/humble/setup.bash && source ~/tb4_ws/install/setup.bash'
CMD_LOG="$ROS_SETUP && tail -f $LOG | grep --line-buffered -E \"yolo_detector|goal_navigator|goal_markers\""
CMD_CLICK="$ROS_SETUP && ros2 topic echo /clicked_point"
CMD_NAV="$ROS_SETUP && ros2 run tb4_yolo goal_navigator --ros-args -p use_sim_time:=true -p goals_file:=\$HOME/tb4_clicked_goals.yaml -p dwell:=5.0 -p wait_for_goals:=3"

if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --geometry=110x12 --title="LOG YOLO/GOAL" -- bash -c "$CMD_LOG; exec bash"
    gnome-terminal --geometry=110x12 --title="CLICKED POINT" -- bash -c "$CMD_CLICK; exec bash"
    gnome-terminal --geometry=110x12 --title="GOAL NAVIGATOR" -- bash -c "$CMD_NAV; exec bash"
    echo "Da mo 3 cua so: LOG YOLO/GOAL, CLICKED POINT, GOAL NAVIGATOR."
else
    echo "Khong tim thay gnome-terminal, hay tu mo 3 terminal va chay:"
    echo ""
    echo "# LOG YOLO/GOAL:"
    echo "$CMD_LOG"
    echo ""
    echo "# CLICKED POINT:"
    echo "$CMD_CLICK"
    echo ""
    echo "# GOAL NAVIGATOR:"
    echo "$CMD_NAV"
fi

echo ""
echo "=== San sang quay video ==="
echo "1. Bat Publish Point trong RViz2, nhap 3 diem tren ban do (xem toa do o cua so CLICKED POINT)."
echo "2. Cua so GOAL NAVIGATOR tu dong cho du 3 goal roi bat dau di va in bang tong ket."
echo "3. Dung lai, goi lai scripts/demo_record.sh (hoac ros2 service call /reset_goals std_srvs/srv/Empty {}) de nhap lai tu dau."
