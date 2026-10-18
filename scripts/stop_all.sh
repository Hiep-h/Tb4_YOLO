#!/bin/bash
set -uo pipefail

EXCLUDE='claude|firefox|gnome-shell|Xwayland|warp-svc|vte-spawn|jetbrains|avahi-daemon|stop_all\.sh'

launch_pids() {
    pgrep -f "ros2 launch" 2>/dev/null | while read -r pid; do
        cmd=$(ps -o cmd= -p "$pid" 2>/dev/null)
        [ -z "$cmd" ] && continue
        echo "$cmd" | grep -qE "$EXCLUDE" && continue
        echo "$pid"
    done
}

echo "=== Buoc 1: SIGINT cho cac tien trinh ros2 launch ==="
pids=$(launch_pids)
if [ -n "$pids" ]; then
    echo "$pids" | xargs -r kill -INT
    echo "Da gui SIGINT toi: $(echo "$pids" | tr '\n' ' ')"
else
    echo "Khong co tien trinh ros2 launch"
fi

for i in $(seq 1 15); do
    sleep 1
    remain=$(launch_pids)
    [ -z "$remain" ] && break
done

echo "=== Buoc 2: SIGTERM cho ros2 launch con lai (neu co) ==="
remain=$(launch_pids)
if [ -n "$remain" ]; then
    echo "$remain" | xargs -r kill -TERM
    echo "Da gui SIGTERM toi: $(echo "$remain" | tr '\n' ' ')"
else
    echo "Khong con tien trinh ros2 launch sau SIGINT"
fi
sleep 5

echo "=== Buoc 3: SIGKILL cac tien trinh ROS/Gazebo/turtlebot4 con sot ==="
PATTERNS=(
    "ign gazebo"
    "gz sim"
    "ros_gz_bridge/parameter_bridge"
    "ros_gz_sim/create"
    "tf2_ros/static_transform_publisher"
    "robot_state_publisher/robot_state_publisher"
    "joint_state_publisher/joint_state_publisher"
    "nav2_map_server"
    "nav2_amcl"
    "lib/amcl"
    "controller_server"
    "planner_server"
    "behavior_server"
    "bt_navigator"
    "velocity_smoother"
    "smoother_server"
    "waypoint_follower"
    "lifecycle_manager"
    "rviz2"
    "tb4_yolo/yolo_detector"
    "tb4_yolo/goal_navigator"
    "tb4_yolo/goal_markers"
    "turtlebot4_node"
    "turtlebot4_ignition"
    "irobot_create_nodes"
    "irobot_create_ignition_toolbox"
    "controller_manager/spawner"
    "ros2 launch"
)

kill_pids=""
for pat in "${PATTERNS[@]}"; do
    found=$(pgrep -f "$pat" 2>/dev/null)
    for pid in $found; do
        cmd=$(ps -o cmd= -p "$pid" 2>/dev/null)
        [ -z "$cmd" ] && continue
        echo "$cmd" | grep -qE "$EXCLUDE" && continue
        kill_pids="$kill_pids $pid"
    done
done
kill_pids=$(echo "$kill_pids" | tr ' ' '\n' | grep -v '^$' | sort -un)
if [ -n "$kill_pids" ]; then
    echo "$kill_pids" | xargs -r kill -9
    echo "Da SIGKILL: $(echo "$kill_pids" | tr '\n' ' ')"
else
    echo "Khong con tien trinh ROS/Gazebo nao de SIGKILL"
fi

sleep 2

echo "=== Buoc 4: kiem tra tien trinh mo coi (PPID=1) ==="
orphans_ppid1=$(ps -eo pid,ppid,cmd --no-headers | awk '$2==1' | grep -viE "$EXCLUDE")
if [ -n "$orphans_ppid1" ]; then
    echo "CANH BAO: con tien trinh voi PPID=1:"
    echo "$orphans_ppid1"
else
    echo "Khong con tien trinh nao voi PPID=1"
fi

echo "=== Buoc 5 (bo sung): kiem tra con tien trinh ROS/Gazebo nao song sot (bat ke PPID) ==="
leftover=""
for pat in "${PATTERNS[@]}"; do
    found=$(pgrep -af "$pat" 2>/dev/null | grep -viE "$EXCLUDE")
    [ -n "$found" ] && leftover="$leftover
$found"
done
if [ -n "$leftover" ]; then
    echo "CANH BAO: van con tien trinh ROS/Gazebo:"
    echo "$leftover"
else
    echo "Da don sach: khong con tien trinh ROS/Gazebo/turtlebot4 nao."
fi
