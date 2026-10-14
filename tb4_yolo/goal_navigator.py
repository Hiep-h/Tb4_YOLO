import math
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


def main():
    rclpy.init()
    nav = BasicNavigator('goal_navigator')
    nav.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])
    nav.declare_parameter('goals_file', '')
    nav.declare_parameter('dwell', 5.0)
    nav.declare_parameter('loops', 1)
    nav.declare_parameter('timeout', 600.0)
    goals_file = nav.get_parameter('goals_file').value
    dwell = float(nav.get_parameter('dwell').value)
    loops = int(nav.get_parameter('loops').value)
    timeout = float(nav.get_parameter('timeout').value)
    if not goals_file:
        nav.get_logger().error('thieu tham so goals_file')
        return 1
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
            while not nav.isTaskComplete():
                feedback = nav.getFeedback()
                tick += 1
                if feedback and tick % 20 == 0:
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
            summary.append((name, status))
            if result == TaskResult.SUCCEEDED and dwell > 0.0:
                nav.get_logger().info('  dung %.1f s tai goal' % dwell)
                end = nav.get_clock().now().nanoseconds + int(dwell * 1e9)
                while nav.get_clock().now().nanoseconds < end:
                    rclpy.spin_once(nav, timeout_sec=0.2)

    nav.get_logger().info('--- Tong ket ---')
    for name, status in summary:
        nav.get_logger().info('%s: %s' % (name, status))
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
