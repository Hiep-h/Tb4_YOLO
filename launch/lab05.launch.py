import os

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription,
                            RegisterEventHandler, TimerAction)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('tb4_yolo')
    args = [
        DeclareLaunchArgument('world', default_value='small_house'),
        DeclareLaunchArgument('x', default_value='1.0'),
        DeclareLaunchArgument('y', default_value='1.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('map', default_value=PathJoinSubstitution([pkg, 'maps', 'map_clean.yaml'])),
        DeclareLaunchArgument('goals', default_value=PathJoinSubstitution([pkg, 'config', 'goals.yaml'])),
        DeclareLaunchArgument('run_navigator', default_value='true', description='tu chay node goal_navigator'),
        DeclareLaunchArgument('navigator_delay', default_value='20.0', description='giay cho sau khi khoi dong truoc khi cho Nav2'),
        DeclareLaunchArgument('dwell', default_value='5.0', description='giay dung tai moi goal'),
        DeclareLaunchArgument('run_yolo', default_value='true', description='tu khoi dong yolo_detector sau khi Nav2 active'),
        DeclareLaunchArgument('yolo_model', default_value=os.path.expanduser('~/yolov8n.pt')),
        DeclareLaunchArgument('conf', default_value='0.4'),
        DeclareLaunchArgument('imgsz', default_value='640'),
        DeclareLaunchArgument('show_window', default_value='false'),
        DeclareLaunchArgument('save_dir', default_value='', description='thu muc luu anh nhan dien dau tien cua moi lop'),
        DeclareLaunchArgument('show_rviz', default_value='true', description='tu chay rviz2 voi config/lab05.rviz (co display YOLO)'),
        DeclareLaunchArgument('markers', default_value='true', description='tu chay node goal_markers'),
        DeclareLaunchArgument('record_file', default_value=os.path.expanduser('~/tb4_clicked_goals.yaml'),
                               description='file goal_markers ghi tu cac diem /clicked_point'),
        DeclareLaunchArgument('max_goals', default_value='3', description='so goal toi da goal_markers ghi'),
        DeclareLaunchArgument('costmap_topic', default_value='/global_costmap/costmap'),
        DeclareLaunchArgument('clearance_cost', default_value='60', description='nguong cost toi da de diem nhap hop le'),
        DeclareLaunchArgument('clearance_radius_m', default_value='0.3', description='ban kinh (m) quanh diem nhap can thoang, khong vat can/unknown'),
    ]
    base = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([pkg, 'launch', 'nav_demo.launch.py'])),
        launch_arguments={**{k: LaunchConfiguration(k) for k in ('world', 'x', 'y', 'yaw', 'map')}, 'viz': 'false'}.items())
    rviz = Node(package='rviz2', executable='rviz2', name='rviz2',
                arguments=['-d', PathJoinSubstitution([pkg, 'config', 'lab05.rviz'])],
                parameters=[{'use_sim_time': True}],
                remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
                condition=IfCondition(LaunchConfiguration('show_rviz')), output='screen')
    yolo = Node(package='tb4_yolo', executable='yolo_detector', name='yolo_detector', output='screen',
                parameters=[{'use_sim_time': True, 'model': LaunchConfiguration('yolo_model'),
                             'conf': LaunchConfiguration('conf'),
                             'imgsz': LaunchConfiguration('imgsz'),
                             'show_window': LaunchConfiguration('show_window'),
                             'save_dir': LaunchConfiguration('save_dir')}])
    markers = Node(package='tb4_yolo', executable='goal_markers', name='goal_markers', output='screen',
                   condition=IfCondition(LaunchConfiguration('markers')),
                   parameters=[{'use_sim_time': True, 'goals_file': LaunchConfiguration('goals'),
                                'record_file': LaunchConfiguration('record_file'),
                                'max_goals': LaunchConfiguration('max_goals'),
                                'costmap_topic': LaunchConfiguration('costmap_topic'),
                                'clearance_cost': LaunchConfiguration('clearance_cost'),
                                'clearance_radius_m': LaunchConfiguration('clearance_radius_m')}])
    wait_nav2 = ExecuteProcess(
        cmd=['bash', '-c', 'for i in $(seq 1 240); do '
             "(ros2 lifecycle get /amcl | grep -qE '^active') && "
             "(ros2 lifecycle get /bt_navigator | grep -qE '^active') && exit 0; sleep 5; done; exit 0"],
        name='wait_nav2', output='log', condition=IfCondition(LaunchConfiguration('run_yolo')))
    on_nav2 = RegisterEventHandler(OnProcessExit(target_action=wait_nav2, on_exit=[yolo]))
    navigator = TimerAction(period=LaunchConfiguration('navigator_delay'), actions=[
        Node(package='tb4_yolo', executable='goal_navigator', name='goal_navigator', output='screen',
             condition=IfCondition(LaunchConfiguration('run_navigator')),
             parameters=[{'use_sim_time': True, 'goals_file': LaunchConfiguration('goals'),
                          'dwell': LaunchConfiguration('dwell')}])])
    return LaunchDescription(args + [base, rviz, markers, wait_nav2, on_nav2, navigator])
