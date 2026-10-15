#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/stop_all.sh"

source /opt/ros/humble/setup.bash
source ~/tb4_ws/install/setup.bash

cd ~/tb4_ws
setsid nohup ros2 launch tb4_yolo lab05.launch.py world:=small_house x:=1.0 y:=1.0 \
    run_yolo:=true run_navigator:=true navigator_delay:=120 \
    > ~/lab05_launch.log 2>&1 < /dev/null &
disown

echo "Da khoi dong lab05.launch.py (log: ~/lab05_launch.log)"
echo "Xem log YOLO va goal_navigator:"
echo "  tail -f ~/lab05_launch.log | grep --line-buffered -E \"yolo_detector|goal_navigator\""
