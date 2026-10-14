import json
import os
import time

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


class YoloDetector(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        self.declare_parameter('image_topic', '/oakd/rgb/preview/image_raw')
        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('conf', 0.35)
        self.declare_parameter('imgsz', 320)
        self.declare_parameter('rate', 2.0)
        self.declare_parameter('show_window', True)
        self.declare_parameter('save_dir', '')

        from ultralytics import YOLO
        self.model = YOLO(self.get_parameter('model').value)
        self.conf = float(self.get_parameter('conf').value)
        self.imgsz = int(self.get_parameter('imgsz').value)
        self.show = bool(self.get_parameter('show_window').value)
        self.save_dir = self.get_parameter('save_dir').value
        if self.save_dir:
            os.makedirs(self.save_dir, exist_ok=True)

        self.bridge = CvBridge()
        self.latest = None
        self.saved = set()
        self.seen = {}
        self.frames = 0
        self.window_ok = self.show

        topic = self.get_parameter('image_topic').value
        self.create_subscription(Image, topic, self.on_image, qos_profile_sensor_data)
        self.pub_image = self.create_publisher(Image, '/yolo/image', 10)
        self.pub_det = self.create_publisher(String, '/yolo/detections', 10)
        self.create_timer(1.0 / float(self.get_parameter('rate').value), self.process)
        self.get_logger().info('YOLO san sang, doi anh tu %s' % topic)

    def on_image(self, msg):
        self.latest = msg

    def process(self):
        msg, self.latest = self.latest, None
        if msg is None:
            return
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        t0 = time.time()
        result = self.model.predict(frame, conf=self.conf, imgsz=self.imgsz, verbose=False)[0]
        ms = (time.time() - t0) * 1000.0
        self.frames += 1

        found = []
        for box in result.boxes:
            name = self.model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            found.append({'class': name, 'conf': round(conf, 2), 'box': [x1, y1, x2, y2]})
            self.seen[name] = max(self.seen.get(name, 0.0), conf)

        annotated = result.plot()
        out = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        out.header = msg.header
        self.pub_image.publish(out)
        self.pub_det.publish(String(data=json.dumps(found)))

        if found:
            text = ', '.join('%s %.2f' % (d['class'], d['conf']) for d in found)
            self.get_logger().info('khung %d (%.0f ms): %s' % (self.frames, ms, text))
            if self.save_dir:
                for d in found:
                    if d['class'] not in self.saved:
                        self.saved.add(d['class'])
                        cv2.imwrite(os.path.join(self.save_dir, '%s.png' % d['class'].replace(' ', '_')), annotated)
        else:
            self.get_logger().info('khung %d (%.0f ms): khong thay vat the' % (self.frames, ms))

        if self.window_ok:
            try:
                cv2.imshow('YOLO - TurtleBot 4', cv2.resize(annotated, None, fx=2.0, fy=2.0))
                cv2.waitKey(1)
            except cv2.error:
                self.window_ok = False
                self.get_logger().warn('khong mo duoc cua so OpenCV, chi publish /yolo/image')

    def summary(self):
        self.get_logger().info('--- Cac lop da phat hien ---')
        for name, conf in sorted(self.seen.items(), key=lambda kv: -kv[1]):
            self.get_logger().info('%s: do tin cay cao nhat %.2f' % (name, conf))


def main():
    rclpy.init()
    node = YoloDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.summary()
        if node.window_ok:
            cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
