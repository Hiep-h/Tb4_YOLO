import math
import os

import rclpy
import yaml
from geometry_msgs.msg import PointStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_srvs.srv import Empty
from visualization_msgs.msg import Marker, MarkerArray


def load_goals(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    return [(g.get('name', 'Goal %d' % (i + 1)), float(g['x']), float(g['y']), math.radians(g.get('yaw_deg', 0.0)))
            for i, g in enumerate(data['goals'])]


def load_recorded(path):
    name_x_y_yaw = load_goals(path)
    return [{'name': name, 'x': x, 'y': y, 'yaw_deg': math.degrees(yaw)} for name, x, y, yaw in name_x_y_yaw]


def yaw_to_quat(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class GoalMarkers(Node):
    def __init__(self):
        super().__init__('goal_markers')
        self.declare_parameter('goals_file', '')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('record_file', '~/tb4_clicked_goals.yaml')
        self.declare_parameter('max_goals', 3)
        self.declare_parameter('costmap_topic', '/global_costmap/costmap')
        self.declare_parameter('clearance_cost', 60)
        self.declare_parameter('clearance_radius_m', 0.6)

        self.frame_id = self.get_parameter('frame_id').value
        self.record_path = os.path.expanduser(self.get_parameter('record_file').value)
        self.max_goals = int(self.get_parameter('max_goals').value)
        self.clearance_cost = int(self.get_parameter('clearance_cost').value)
        self.clearance_radius_m = float(self.get_parameter('clearance_radius_m').value)
        costmap_topic = self.get_parameter('costmap_topic').value

        goals_file = self.get_parameter('goals_file').value
        if not goals_file:
            self.get_logger().error('thieu tham so goals_file')
            self.preview_goals = []
        else:
            self.preview_goals = load_goals(goals_file)

        if os.path.exists(self.record_path):
            self.recorded = load_recorded(self.record_path)
            self.recording = True
        else:
            self.recorded = []
            self.recording = False
        self.last_display_count = 0

        self.costmap = None
        self.map_grid = None
        self.amcl_pose = None

        qos_markers = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                  durability=DurabilityPolicy.TRANSIENT_LOCAL)
        qos_grid = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.TRANSIENT_LOCAL)

        self.pub = self.create_publisher(MarkerArray, '/goal_markers', qos_markers)
        self.create_subscription(PointStamped, '/clicked_point', self.on_click, 10)
        self.create_subscription(OccupancyGrid, costmap_topic, self.on_costmap, qos_grid)
        self.create_subscription(OccupancyGrid, '/map', self.on_map, qos_grid)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.on_amcl_pose, 10)
        self.create_service(Empty, '/reset_goals', self.on_reset)

        self.publish_markers()
        self.create_timer(2.0, self.publish_markers)
        self.get_logger().info('goal_markers san sang, %d goal cho (preview), ghi vao %s' %
                                (len(self.preview_goals), self.record_path))

    def on_costmap(self, msg):
        self.costmap = msg

    def on_map(self, msg):
        self.map_grid = msg

    def on_amcl_pose(self, msg):
        self.amcl_pose = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def start_xy(self):
        if self.amcl_pose is not None:
            return self.amcl_pose
        return (0.0, 0.0)

    def validate_point(self, x, y):
        grid = self.costmap if self.costmap is not None else self.map_grid
        if grid is None:
            return False, 'chua co costmap/map'
        info = grid.info
        col = int(math.floor((x - info.origin.position.x) / info.resolution))
        row = int(math.floor((y - info.origin.position.y) / info.resolution))
        if col < 0 or col >= info.width or row < 0 or row >= info.height:
            return False, 'ngoai ban do'

        radius_cells = max(1, int(math.ceil(self.clearance_radius_m / info.resolution)))
        min_dist = None
        for dr in range(-radius_cells, radius_cells + 1):
            r = row + dr
            if r < 0 or r >= info.height:
                continue
            for dc in range(-radius_cells, radius_cells + 1):
                c = col + dc
                if c < 0 or c >= info.width:
                    continue
                dist = math.hypot(dc, dr) * info.resolution
                if dist > self.clearance_radius_m:
                    continue
                val = grid.data[r * info.width + c]
                if val < 0 or val >= self.clearance_cost:
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
        if min_dist is not None:
            return False, 'qua gan vat can (cach %.2f m)' % min_dist
        return True, ''

    def write_record_file(self):
        data = {'goals': [{'name': g['name'], 'x': round(g['x'], 2), 'y': round(g['y'], 2),
                            'yaw_deg': round(g['yaw_deg'], 2)} for g in self.recorded]}
        with open(self.record_path, 'w') as f:
            yaml.safe_dump(data, f, sort_keys=False)

    def remove_record_file(self):
        if os.path.exists(self.record_path):
            os.remove(self.record_path)

    def on_click(self, msg):
        if not self.recording:
            self.recording = True
            self.recorded = []

        if len(self.recorded) >= self.max_goals:
            self.get_logger().info('Da du %d goal, bo qua diem nay. Dung ros2 service call '
                                    '/reset_goals std_srvs/srv/Empty {} de nhap lai' % self.max_goals)
            return

        x, y = msg.point.x, msg.point.y
        ok, reason = self.validate_point(x, y)
        if not ok:
            if reason.startswith('qua gan vat can'):
                self.get_logger().warn('Diem (%.2f, %.2f) %s, hay chon cho thoang hon' % (x, y, reason))
            else:
                self.get_logger().warn('Diem (%.2f, %.2f) khong hop le: %s, hay nhap lai' % (x, y, reason))
            return

        if self.recorded:
            px, py = self.recorded[-1]['x'], self.recorded[-1]['y']
        else:
            px, py = self.start_xy()
        yaw_deg = math.degrees(math.atan2(y - py, x - px))

        k = len(self.recorded) + 1
        self.recorded.append({'name': 'Goal %d' % k, 'x': x, 'y': y, 'yaw_deg': yaw_deg})
        self.write_record_file()
        self.get_logger().info('Goal %d da ghi: x=%.2f y=%.2f yaw=%.2f° -> %s' %
                                (k, x, y, yaw_deg, self.record_path))
        if len(self.recorded) >= self.max_goals:
            self.get_logger().info('Da du %d goal, chay goal_navigator voi goals_file:=%s' %
                                    (self.max_goals, self.record_path))
        self.publish_markers()

    def on_reset(self, request, response):
        self.recording = False
        self.recorded = []
        self.remove_record_file()
        self.publish_markers()
        self.get_logger().info('Da reset, hien lai goal cho tu goals_file')
        return response

    def display_list(self):
        if self.recording:
            return [(g['name'], g['x'], g['y'], math.radians(g['yaw_deg'])) for g in self.recorded]
        return self.preview_goals

    def build_markers(self, display_list):
        markers = []
        for i, (name, x, y, yaw) in enumerate(display_list):
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

    def delete_markers(self, from_count, to_count):
        markers = []
        for i in range(from_count, to_count):
            for off in range(3):
                m = Marker()
                m.header.frame_id = self.frame_id
                m.ns = 'goals'
                m.id = i * 3 + off
                m.action = Marker.DELETE
                markers.append(m)
        return markers

    def publish_markers(self):
        display_list = self.display_list()
        arr = MarkerArray()
        arr.markers.extend(self.build_markers(display_list))
        arr.markers.extend(self.delete_markers(len(display_list), self.last_display_count))
        self.last_display_count = len(display_list)
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
