#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=~/lab05_launch.log
CLICKED=~/tb4_clicked_goals.yaml

REUSE=false
RESET_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --reuse) REUSE=true ;;
        --reset-only) RESET_ONLY=true ;;
        *) echo "Tham so khong ro: $arg (chi nhan --reuse hoac --reset-only)"; exit 1 ;;
    esac
done

set +u
source /opt/ros/humble/setup.bash
source ~/tb4_ws/install/setup.bash
set -u

COV='[0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07]'
POSE="{header: {frame_id: map}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}, covariance: $COV}}"

ROS_SETUP='source /opt/ros/humble/setup.bash && source ~/tb4_ws/install/setup.bash'
CMD_LOG="$ROS_SETUP && tail -f $LOG | grep --line-buffered -E \"yolo_detector|goal_navigator|goal_markers\""
CMD_CLICK="$ROS_SETUP && ros2 topic echo /clicked_point"
CMD_NAV="$ROS_SETUP && ros2 run tb4_yolo goal_navigator --ros-args -p use_sim_time:=true -p goals_file:=\$HOME/tb4_clicked_goals.yaml -p dwell:=5.0 -p wait_for_goals:=3"
CMD_INITPOSE="ros2 topic pub -t 8 -r 1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \"$POSE\""
CMD_RESET="ros2 service call /reset_goals std_srvs/srv/Empty {}"

bt_active() {
    ros2 lifecycle get /bt_navigator 2>/dev/null | grep -qE '^active'
}

amcl_active() {
    ros2 lifecycle get /amcl 2>/dev/null | grep -qE '^active'
}

wait_for_nav2() {
    for i in $(seq 1 240); do
        amcl_active && bt_active && return 0
        sleep 5
    done
    return 1
}

get_amcl_xy() {
    local out
    out=$(timeout 20 ros2 topic echo /amcl_pose --once 2>/dev/null)
    [ -z "$out" ] && return 1
    echo "$out" | python3 -c "
import sys, yaml
try:
    d = yaml.safe_load(sys.stdin)
    p = d['pose']['pose']['position']
    print(p['x'], p['y'])
except Exception:
    sys.exit(1)
"
}

send_initialpose() {
    local attempt xy x y dist
    for attempt in 1 2 3; do
        echo "Gui lai /initialpose (lan $attempt/3)..."
        ros2 topic pub -t 8 -r 1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped "$POSE" >/dev/null 2>&1
        sleep 3
        xy=$(get_amcl_xy) || xy=""
        if [ -n "$xy" ]; then
            x=$(echo "$xy" | cut -d' ' -f1)
            y=$(echo "$xy" | cut -d' ' -f2)
            dist=$(python3 -c "print(($x**2 + $y**2) ** 0.5)")
            echo "  /amcl_pose hien tai: x=$x y=$y (cach goc (0,0) $dist m)"
            if python3 -c "exit(0 if $dist <= 0.5 else 1)"; then
                echo "AMCL da ve gan vi tri khoi tao (0, 0)."
                return 0
            fi
        else
            echo "  khong doc duoc /amcl_pose"
        fi
    done
    echo "CANH BAO: AMCL van lech vi tri khoi tao sau 3 lan gui /initialpose."
    echo "Hay dung 2D Pose Estimate trong RViz2 de dat lai vi tri thu cong."
    return 1
}

reset_goals() {
    local attempt
    for attempt in 1 2 3; do
        if timeout 15 ros2 service call /reset_goals std_srvs/srv/Empty "{}" >/dev/null 2>&1; then
            rm -f "$CLICKED"
            if [ ! -f "$CLICKED" ]; then
                echo "Da reset danh sach goal"
                return 0
            fi
        fi
        echo "  /reset_goals lan $attempt/3 chua thanh cong, thu lai..."
        sleep 2
    done
    rm -f "$CLICKED"
    echo "CANH BAO: khong goi duoc /reset_goals sau 3 lan (goal_markers co the chua len)."
    return 1
}

navigator_already_running_goals() {
    pgrep -f "tb4_yolo goal_navigator" >/dev/null 2>&1 || return 1
    local last_wait_line
    last_wait_line=$(grep -n "Dang cho .* diem nhap" "$LOG" 2>/dev/null | tail -1 | cut -d: -f1)
    [ -z "$last_wait_line" ] && last_wait_line=1
    tail -n +"$last_wait_line" "$LOG" 2>/dev/null | grep -qE "Da nhan [0-9]+ goal|THANH CONG|BI HUY|THAT BAI"
}

open_window() {
    local title="$1" cmd="$2"
    if command -v gnome-terminal >/dev/null 2>&1; then
        gnome-terminal --geometry=110x12 --title="$title" -- bash -c "$cmd; exec bash"
    else
        echo "Khong tim thay gnome-terminal, hay tu mo terminal va chay ($title):"
        echo "$cmd"
    fi
}

open_all_windows() {
    open_window "LOG YOLO/GOAL" "$CMD_LOG"
    open_window "CLICKED POINT" "$CMD_CLICK"
    open_window "GOAL NAVIGATOR" "$CMD_NAV"
    echo "Da mo 3 cua so: LOG YOLO/GOAL, CLICKED POINT, GOAL NAVIGATOR."
}

if $RESET_ONLY; then
    if ! bt_active; then
        echo "He thong chua chay, khong the dung --reset-only. Hay chay lai khong co tham so nay."
        exit 1
    fi
    echo "--reset-only: giu nguyen he thong dang chay, chi gui lai initialpose va reset goal."
else
    if bt_active; then
        if $REUSE; then
            echo "CANH BAO: dung lai he thong dang chay (--reuse), robot co the dang o cho cu."
        else
            echo "He thong dang chay, don sach va khoi dong lai tu dau..."
            bash "$SCRIPT_DIR/stop_all.sh"
            bash "$SCRIPT_DIR/demo_run.sh"
        fi
    else
        echo "He thong chua chay, khoi dong bang demo_run.sh..."
        bash "$SCRIPT_DIR/demo_run.sh"
    fi
fi

echo "Doi AMCL va bt_navigator active..."
if ! wait_for_nav2; then
    echo "LOI: Nav2 (AMCL + bt_navigator) chua active sau 20 phut, kiem tra $LOG."
    exit 1
fi

send_initialpose
init_ok=$?

reset_goals
reset_ok=$?

if $RESET_ONLY; then
    if navigator_already_running_goals; then
        echo "CANH BAO: cua so GOAL NAVIGATOR co the da bat dau di cac goal cu."
        echo "  1. Vao cua so GOAL NAVIGATOR, nhan Ctrl+C de dung."
        echo "  2. Neu goal dang chay, huy bang:"
        echo "     ros2 service call /navigate_to_pose/_action/cancel_goal action_msgs/srv/CancelGoal \"{}\""
        echo "  3. Dang mo lai cua so GOAL NAVIGATOR..."
        open_window "GOAL NAVIGATOR" "$CMD_NAV"
        echo "     (hoac tu chay): $CMD_NAV"
    fi
else
    open_all_windows
fi

echo ""
echo "=== Tom tat ==="
xy=$(get_amcl_xy) || xy="khong doc duoc"
echo "AMCL hien tai: $xy"
if [ "$init_ok" -ne 0 ]; then
    echo "CANH BAO: initialpose chua chac chan, xem canh bao phia tren."
fi
if [ "$reset_ok" -eq 0 ]; then
    echo "Danh sach goal: da reset (trong)."
else
    echo "Danh sach goal: CANH BAO reset chua chac chan, kiem tra lai."
fi
echo ""
echo "1. Bat Publish Point trong RViz2, nhap 3 diem tren ban do."
echo "2. Nhap nham, reset lai bang:"
echo "   $CMD_RESET"
echo "3. Can gui lai vi tri khoi tao, chay:"
echo "   $CMD_INITPOSE"
echo ""
echo "Tuy chon: --reuse (giu he thong cu, khong khoi dong lai), --reset-only (chi gui initialpose + reset goal, giu he thong dang chay)."
