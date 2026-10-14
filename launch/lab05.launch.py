from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
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
        DeclareLaunchArgument('model', default_value='yolov8n.pt'),
        DeclareLaunchArgument('conf', default_value='0.35'),
        DeclareLaunchArgument('show_window', default_value='true'),
        DeclareLaunchArgument('save_dir', default_value='', description='thu muc luu anh nhan dien dau tien cua moi lop'),
    ]
    base = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([pkg, 'launch', 'nav_demo.launch.py'])),
        launch_arguments={k: LaunchConfiguration(k) for k in ('world', 'x', 'y', 'yaw', 'map')}.items())
    yolo = Node(package='tb4_yolo', executable='yolo_detector', name='yolo_detector', output='screen',
                parameters=[{'use_sim_time': True, 'model': LaunchConfiguration('model'),
                             'conf': LaunchConfiguration('conf'),
                             'show_window': LaunchConfiguration('show_window'),
                             'save_dir': LaunchConfiguration('save_dir')}])
    navigator = TimerAction(period=LaunchConfiguration('navigator_delay'), actions=[
        Node(package='tb4_yolo', executable='goal_navigator', name='goal_navigator', output='screen',
             condition=IfCondition(LaunchConfiguration('run_navigator')),
             parameters=[{'use_sim_time': True, 'goals_file': LaunchConfiguration('goals'),
                          'dwell': LaunchConfiguration('dwell')}])])
    return LaunchDescription(args + [base, yolo, navigator])
