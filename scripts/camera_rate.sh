#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
HZ="${1:-5}"
CAM="$(ros2 pkg prefix turtlebot4_description)/share/turtlebot4_description/urdf/sensors/oakd.urdf.xacro"
[ -f "$CAM.orig" ] || sudo cp "$CAM" "$CAM.orig"
sudo sed -i -E "s#<update_rate>[0-9.]+</update_rate>#<update_rate>$HZ</update_rate>#" "$CAM"
grep -n 'update_rate' "$CAM"
