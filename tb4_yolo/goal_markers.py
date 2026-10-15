import math

import rclpy
import yaml
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray

MAX_CLICKS = 10


def load_goals(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    return [(g.get('name', 'Goal %d' % (i + 1)), float(g['x']), float(g['y']), math.radians(g.get('yaw_deg', 0.0)))
            for i, g in enumerate(data['goals'])]


def yaw_to_quat(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class GoalMarkers(Node):
    def __init__(self):
        super().__init__('goal_markers')
        self.declare_parameter('goals_file', '')
        self.declare_parameter('frame_id', 'map')
        self.frame_id = self.get_parameter('frame_id').value
        goals_file = self.get_parameter('goals_file').value
        if not goals_file:
            self.get_logger().error('thieu tham so goals_file')
            self.goals = []
        else:
            self.goals = load_goals(goals_file)

        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(MarkerArray, '/goal_markers', qos)
        self.sub_click = self.create_subscription(PointStamped, '/clicked_point', self.on_click, 10)

        self.clicks = []
        self.click_count = 0

        self.publish_markers()
        self.create_timer(2.0, self.publish_markers)
        self.get_logger().info('goal_markers san sang, %d goal' % len(self.goals))

    def goal_markers(self):
        markers = []
        for i, (name, x, y, yaw) in enumerate(self.goals):
            qx, qy, qz, qw = yaw_to_quat(yaw)

            sphere = Marker()
            sphere.header.frame_id = self.frame_id
            sphere.ns = 'goals'
            sphere.id = i * 3 + 0
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = x
            sphere.pose.position.y = y
            sphere.pose.position.z = 0.1
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = sphere.scale.y = sphere.scale.z = 0.3
            sphere.color.r, sphere.color.g, sphere.color.b, sphere.color.a = 0.0, 1.0, 0.0, 1.0
            markers.append(sphere)

            arrow = Marker()
            arrow.header.frame_id = self.frame_id
            arrow.ns = 'goals'
            arrow.id = i * 3 + 1
            arrow.type = Marker.ARROW
            arrow.action = Marker.ADD
            arrow.pose.position.x = x
            arrow.pose.position.y = y
            arrow.pose.position.z = 0.1
            arrow.pose.orientation.x = qx
            arrow.pose.orientation.y = qy
            arrow.pose.orientation.z = qz
            arrow.pose.orientation.w = qw
            arrow.scale.x, arrow.scale.y, arrow.scale.z = 0.5, 0.08, 0.08
            arrow.color.r, arrow.color.g, arrow.color.b, arrow.color.a = 0.0, 1.0, 0.0, 1.0
            markers.append(arrow)

            text = Marker()
            text.header.frame_id = self.frame_id
            text.ns = 'goals'
            text.id = i * 3 + 2
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD
            text.pose.position.x = x
            text.pose.position.y = y
            text.pose.position.z = 0.5
            text.pose.orientation.w = 1.0
            text.scale.z = 0.35
            text.color.r, text.color.g, text.color.b, text.color.a = 1.0, 1.0, 1.0, 1.0
            text.text = '%s\n(x=%.2f, y=%.2f, yaw=%.2f°)' % (name, x, y, math.degrees(yaw))
            markers.append(text)
        return markers

    def click_markers(self):
        markers = []
        for i, (k, x, y) in enumerate(self.clicks):
            sphere = Marker()
            sphere.header.frame_id = self.frame_id
            sphere.ns = 'clicks'
            sphere.id = k * 2 + 0
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = x
            sphere.pose.position.y = y
            sphere.pose.position.z = 0.1
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = sphere.scale.y = sphere.scale.z = 0.25
            sphere.color.r, sphere.color.g, sphere.color.b, sphere.color.a = 0.0, 0.3, 1.0, 1.0
            markers.append(sphere)

            text = Marker()
            text.header.frame_id = self.frame_id
            text.ns = 'clicks'
            text.id = k * 2 + 1
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD
            text.pose.position.x = x
            text.pose.position.y = y
            text.pose.position.z = 0.45
            text.pose.orientation.w = 1.0
            text.scale.z = 0.35
            text.color.r, text.color.g, text.color.b, text.color.a = 1.0, 1.0, 1.0, 1.0
            text.text = 'Click %d\n(x=%.2f, y=%.2f)' % (k, x, y)
            markers.append(text)
        return markers

    def publish_markers(self):
        arr = MarkerArray()
        arr.markers.extend(self.goal_markers())
        arr.markers.extend(self.click_markers())
        self.pub.publish(arr)

    def on_click(self, msg):
        self.click_count += 1
        k = self.click_count
        x, y = msg.point.x, msg.point.y
        self.clicks.append((k, x, y))
        if len(self.clicks) > MAX_CLICKS:
            old_k = self.clicks[0][0]
            self.clear_click_markers(old_k)
            self.clicks = self.clicks[-MAX_CLICKS:]
        self.get_logger().info('Clicked point %d: x=%.2f y=%.2f (frame %s)' % (k, x, y, msg.header.frame_id))
        self.publish_markers()

    def clear_click_markers(self, k):
        arr = MarkerArray()
        for marker_id in (k * 2 + 0, k * 2 + 1):
            m = Marker()
            m.header.frame_id = self.frame_id
            m.ns = 'clicks'
            m.id = marker_id
            m.action = Marker.DELETE
            arr.markers.append(m)
        self.pub.publish(arr)


def main():
    rclpy.init()
    node = GoalMarkers()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
