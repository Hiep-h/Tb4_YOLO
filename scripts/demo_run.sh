#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=~/lab05_launch.log

bash "$SCRIPT_DIR/stop_all.sh"

set +u
source /opt/ros/humble/setup.bash
source ~/tb4_ws/install/setup.bash
set -u

cd ~/tb4_ws
setsid nohup ros2 launch tb4_yolo lab05.launch.py world:=small_house x:=1.0 y:=1.0 \
    run_yolo:=true run_navigator:=false \
    > "$LOG" 2>&1 < /dev/null &
disown

echo "Da khoi dong lab05.launch.py (log: $LOG)"

echo "Doi AMCL va bt_navigator active (toi da 20 phut)..."
nav2_ok=false
elapsed=0
until [ "$elapsed" -ge 1200 ]; do
    amcl=$(ros2 lifecycle get /amcl 2>/dev/null)
    bt=$(ros2 lifecycle get /bt_navigator 2>/dev/null)
    if echo "$amcl" | grep -qE '^active' && echo "$bt" | grep -qE '^active'; then
        nav2_ok=true
        break
    fi
    sleep 10
    elapsed=$((elapsed + 10))
done

yolo_ok=false
if [ "$nav2_ok" = true ]; then
    echo "Nav2 active. Doi khung dau tien cua yolo_detector (toi da 5 phut)..."
    elapsed=0
    until [ "$elapsed" -ge 300 ]; do
        if grep -q "khung" "$LOG" 2>/dev/null; then
            yolo_ok=true
            break
        fi
        sleep 10
        elapsed=$((elapsed + 10))
    done
fi

if [ "$nav2_ok" = true ] && [ "$yolo_ok" = true ]; then
    echo "NAV2 + YOLO SAN SANG - co the bat dau quay ($(date '+%Y-%m-%d %H:%M:%S'))"
else
    echo "CHUA SAN SANG ($(date '+%Y-%m-%d %H:%M:%S')):"
    [ "$nav2_ok" = false ] && echo "  - Nav2 (AMCL + bt_navigator) chua active sau 20 phut"
    [ "$nav2_ok" = true ] && [ "$yolo_ok" = false ] && echo "  - yolo_detector chua co khung nao sau 5 phut"
fi

echo ""
echo "=== Lenh cho cac terminal khac ==="
echo ""
echo "# Terminal log:"
echo "source /opt/ros/humble/setup.bash && source ~/tb4_ws/install/setup.bash && tail -f $LOG | grep --line-buffered -E \"yolo_detector|goal_navigator|goal_markers\""
echo ""
echo "# Terminal toa do (clicked_point):"
echo "source /opt/ros/humble/setup.bash && source ~/tb4_ws/install/setup.bash && ros2 topic echo /clicked_point"
echo ""
echo "# Lenh node dieu huong (chay khi ban san sang):"
echo "source /opt/ros/humble/setup.bash && source ~/tb4_ws/install/setup.bash && ros2 run tb4_yolo goal_navigator --ros-args -p use_sim_time:=true -p goals_file:=\$HOME/tb4_clicked_goals.yaml -p dwell:=5.0"
echo ""
echo "# Lenh reset lai danh sach goal da nhap (neu can nhap lai):"
echo "source /opt/ros/humble/setup.bash && source ~/tb4_ws/install/setup.bash && ros2 service call /reset_goals std_srvs/srv/Empty {}"
