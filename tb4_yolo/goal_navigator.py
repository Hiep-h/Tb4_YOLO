import math
import os
import sys

import rclpy
import yaml
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.parameter import Parameter


def make_pose(x, y, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


def load_goals(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    return [(g.get('name', 'Goal %d' % (i + 1)), g['x'], g['y'], math.radians(g.get('yaw_deg', 0.0)))
            for i, g in enumerate(data['goals'])]


def count_valid_goals(path):
    if not os.path.exists(path):
        return 0
    try:
        return len(load_goals(path))
    except Exception:
        return 0


def main():
    rclpy.init()
    nav = BasicNavigator('goal_navigator')
    nav.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])
    nav.declare_parameter('goals_file', '')
    nav.declare_parameter('dwell', 5.0)
    nav.declare_parameter('loops', 1)
    nav.declare_parameter('timeout', 600.0)
    nav.declare_parameter('wait_for_goals', 0)
    goals_file = nav.get_parameter('goals_file').value
    dwell = float(nav.get_parameter('dwell').value)
    loops = int(nav.get_parameter('loops').value)
    timeout = float(nav.get_parameter('timeout').value)
    wait_for_goals = int(nav.get_parameter('wait_for_goals').value)
    if not goals_file:
        nav.get_logger().error('thieu tham so goals_file')
        return 1

    if wait_for_goals > 0:
        last_count = -1
        while True:
            count = count_valid_goals(goals_file)
            if count != last_count:
                nav.get_logger().info('Dang cho %d diem nhap (hien co %d)' % (wait_for_goals, count))
                last_count = count
            if count >= wait_for_goals:
                break
            rclpy.spin_once(nav, timeout_sec=1.0)
        goals = load_goals(goals_file)
        nav.get_logger().info('Da nhan %d goal, bat dau di' % len(goals))
        for name, x, y, yaw in goals:
            nav.get_logger().info('  %s: x=%.2f y=%.2f yaw=%.0f deg' % (name, x, y, math.degrees(yaw)))
    else:
        goals = load_goals(goals_file)

    nav.get_logger().info('cho Nav2 (AMCL + bt_navigator) active')
    nav.waitUntilNav2Active()
    nav.get_logger().info('Nav2 san sang, bat dau %d goal' % len(goals))

    summary = []
    for lap in range(loops):
        for name, x, y, yaw in goals:
            nav.get_logger().info('%s: (%.2f, %.2f, %.0f deg)' % (name, x, y, math.degrees(yaw)))
            nav.goToPose(make_pose(x, y, yaw))
            tick = 0
            start = nav.get_clock().now()
            first_distance = None
            nav_time = 0.0
            recoveries = 0
            while not nav.isTaskComplete():
                feedback = nav.getFeedback()
                tick += 1
                if feedback:
                    if first_distance is None:
                        first_distance = feedback.distance_remaining
                    recoveries = feedback.number_of_recoveries
                    nav_time = feedback.navigation_time.sec + feedback.navigation_time.nanosec * 1e-9
                    if tick % 20 == 0:
                        nav.get_logger().info('  con %.2f m, phuc hoi %d lan' %
                                              (feedback.distance_remaining, feedback.number_of_recoveries))
                elapsed = (nav.get_clock().now() - start).nanoseconds * 1e-9
                if elapsed > timeout:
                    nav.get_logger().warn('  qua %.0f s, huy goal' % timeout)
                    nav.cancelTask()
            result = nav.getResult()
            status = {TaskResult.SUCCEEDED: 'THANH CONG', TaskResult.CANCELED: 'BI HUY',
                      TaskResult.FAILED: 'THAT BAI'}.get(result, 'KHONG RO')
            nav.get_logger().info('%s: %s' % (name, status))
            summary.append((name, x, y, math.degrees(yaw), status, nav_time, recoveries, first_distance))
            if result == TaskResult.SUCCEEDED and dwell > 0.0:
                nav.get_logger().info('  dung %.1f s tai goal' % dwell)
                end = nav.get_clock().now().nanoseconds + int(dwell * 1e9)
                while nav.get_clock().now().nanoseconds < end:
                    rclpy.spin_once(nav, timeout_sec=0.2)

    nav.get_logger().info('--- Tong ket ---')
    header = '%-10s %8s %8s %8s %-10s %10s %8s %10s' % (
        'Ten', 'x', 'y', 'yaw', 'Ket qua', 'T.gian(s)', 'Phuc hoi', 'Cach(m)')
    nav.get_logger().info(header)
    for name, x, y, yaw_deg, status, nav_time, recoveries, first_distance in summary:
        dist_str = '%.2f' % first_distance if first_distance is not None else 'N/A'
        nav.get_logger().info('%-10s %8.2f %8.2f %8.1f %-10s %10.1f %8d %10s' %
                              (name, x, y, yaw_deg, status, nav_time, recoveries, dist_str))
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
