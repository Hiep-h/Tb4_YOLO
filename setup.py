import os
from glob import glob
from setuptools import setup

package_name = 'tb4_yolo'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml') + glob('config/*.rviz')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*.yaml') + glob('maps/*.pgm')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Vu Van Hiep',
    maintainer_email='hiepga05102005@gmail.com',
    description='Lab 05: TurtleBot 4 localization, Nav2 goal navigation and YOLO object detection',
    license='MIT',
    entry_points={
        'console_scripts': [
            'goal_navigator = tb4_yolo.goal_navigator:main',
            'yolo_detector = tb4_yolo.yolo_detector:main',
        ],
    },
)
