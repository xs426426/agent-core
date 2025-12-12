# WS 工作空间完整分析文档

> 文档生成时间：2025-01-25
> 工作空间路径：`c:\Users\23054\Desktop\室内无人机\ws`
> ROS版本：ROS1 Noetic
> 架构：x86

---

## 目录

1. [系统概述](#系统概述)
2. [目录结构](#目录结构)
3. [核心模块详解](#核心模块详解)
4. [系统架构与数据流](#系统架构与数据流)
5. [通信协议](#通信协议)
6. [配置文件说明](#配置文件说明)
7. [启动与运行](#启动与运行)
8. [扩展开发指南](#扩展开发指南)

---

## 系统概述

### 基本信息
- **包含ROS包数量**：55个
- **功能定位**：室内自主飞行无人机系统
- **主要能力**：
  - 实时SLAM定位（LiDAR + IMU + Camera融合）
  - 3D地图构建与维护
  - 自主路径规划与避障
  - 远程任务控制（MQTT + Protobuf）
  - 多传感器数据采集与回传

### 技术栈
- **定位算法**：FAST-LIVO2 (IEEE T-RO 2024)
- **建图方式**：3D Voxel Occupancy Grid
- **规划器**：基于EGO-Planner的轨迹优化
- **飞控接口**：PX4/Pixhawk (MAVROS)
- **通信协议**：MQTT + Protocol Buffers

---

## 目录结构

```
ws/
├── build/                  # 编译输出目录
├── devel/                  # 开发环境配置
├── src/                    # 源码目录
│   ├── concord2/           # MQTT通信节点 ⭐
│   ├── planner_df/         # 路径规划器 ⭐
│   ├── realflight_modules/ # 实飞模块集 ⭐
│   │   ├── FAST-LIVO2/     # VIO SLAM
│   │   ├── mapper/         # 地图构建
│   │   ├── px4ctrl/        # 飞控接口
│   │   └── rpg_vikit/      # 视觉工具库
│   ├── livox_ros_driver/   # Livox激光雷达驱动
│   ├── usb_cam/            # USB相机驱动
│   ├── gnss-fusion/        # GNSS融合（可选）
│   ├── utils/              # 工具库集合
│   └── ...
├── third_party/            # 第三方依赖
├── data_tools/             # 数据处理工具
├── shfiles/                # 脚本文件
│   └── record.sh           # 录制脚本
└── README.md               # 构建说明
```

---

## 核心模块详解

### 1. concord2 - 通信中枢

**位置**：`src/concord2/`

**功能**：ROS与外部世界的桥梁，负责数据的双向转换

**架构**：
```
ROS Topics ←→ concord2 ←→ Protobuf ←→ MQTT ←→ 地面站/Web
```

#### 配置文件：`config/drone.yaml`

```yaml
sn: "daf"  # 无人机序列号

mqtt:
  host: "localhost"
  port: 1883
  keep_alive: 10
  enable_tls: false

modules:  # 启用的模块列表
  - "mavros"              # 飞控通信
  - "mid360"              # Livox Mid360 LiDAR
  - "usb-cam-fpv_4k"      # 4K相机
  - "mapper-mid360"       # 地图构建
  - "px4ctrl"             # 飞控
  - "planner-df"          # 规划器
  - "planner-df-device-camera"  # 相机任务

monitors:  # ROS → MQTT 监听器
  odometry:
    ros_topic: "/aft_mapped_to_init"
    rate: 200
  flight_control:
    ros_topic: "/px4ctrl/drone_state"
    rate: 400
  lidar:
    ros_topic: "/livox/lidar"
    rate: 30
  fpv_camera:
    ros_topic: "/usb_cam/image_raw/compressed"
    rate: 30
  mission_state:
    ros_topic: "/planner_fsm_state"
    rate: 1

broadcasters:  # MQTT → ROS 广播器
  camera:
    ros_topic: "/usb_cam/image_raw/compressed"
    filter_rate: 5
  pointcloud:
    ros_topic: "/cloud_registered"
    filter_rate: 5
  local_odometry:
    ros_topic: "/fcu_odom_from_obv"
    mqtt_topic: "/local/odometry"
    filter_rate: 5
```

#### Protobuf定义：`proto/`
- `mission.proto` - 任务定义
- `camera.proto` - 相机参数
- `control.proto` - 控制指令
- `drone.proto` - 无人机状态
- `pointcloud.proto` - 点云数据
- `common.proto` - 通用类型

#### 启动文件
```bash
roslaunch concord2 drone.launch
```

---

### 2. FAST-LIVO2 - 视觉惯性里程计

**位置**：`src/realflight_modules/FAST-LIVO2/`

**功能**：实时SLAM定位与局部建图

**技术特点**：
- LiDAR + IMU + Camera 紧耦合融合
- 直接法视觉里程计
- 高精度、低漂移
- 发表于 IEEE T-RO 2024

**输入**：
- `/livox/lidar` - Livox Mid360点云数据
- `/livox/imu` - IMU数据（200Hz）
- 相机图像（可选）

**输出**：
- `/aft_mapped_to_init` - 相对初始位置的全局位姿（Odometry）
- `/cloud_registered` - 配准到全局坐标系的点云

**性能指标**：
- 定位精度：< 5cm（理想环境）
- 实时性：10Hz更新
- 支持退化环境

**启动**：
```bash
roslaunch fast_livo mapping_avia.launch  # Livox Avia
roslaunch fast_livo mapping_mid360.launch  # Livox Mid360
```

**相关论文**：
- [FAST-LIVO2 Paper](https://arxiv.org/pdf/2408.14035)
- [FAST-LIVO1 Paper](https://arxiv.org/pdf/2203.00893)

---

### 3. mapper - 地图构建

**位置**：`src/realflight_modules/mapper/`

**功能**：构建3D占据栅格地图（Voxel Map）

**配置**：`config/mid360.yaml`

```yaml
lidar:
  topic: "/livox/lidar"
  scan_lines: 4
  blind_distance: 0.6  # 盲区距离
  input_filter_rate: 2
  output_filter_rate: 5
  type: 2

imu:
  topic: "/livox/imu"

mapping:
  cov_gyr: 0.1
  cov_acc: 0.1
  voxel_size: 0.1        # 体素大小 10cm
  plane_threshold: 0.025
  neighbor_size: 5
  initial_map_size: 10000

calibration:
  # LiDAR到IMU的外参
  R_L_I_PX4: [0.936120, 0.034542, -0.349981, ...]
  T_L_I_PX4: [-0.055477, -0.015877, -0.068395]
```

**地图类型**：
- 3D Voxel Grid（体素栅格）
- 概率占据栅格（Probabilistic Occupancy）
- 分辨率：0.1m（10cm）

**输出**：
- 3D地图数据（供planner使用）
- 可保存为PCD格式

**启动**：
```bash
roslaunch mapper mid360.launch
```

---

### 4. planner_df - 路径规划器

**位置**：`src/planner_df/`

**功能**：接收任务航点，生成无碰撞、动力学可行的飞行轨迹

**核心组件**：
```
planner_df/
├── plan_manager/          # 规划管理器（FSM状态机）
├── plan_environment/      # 环境表示（Voxel Map）
├── path_searching/        # 路径搜索（A*）
├── plan_optimizer/        # 轨迹优化（B-spline）
├── plan_container/        # 数据容器
├── plan_utils/            # 工具函数
├── traj_planner/          # 轨迹规划器
├── traj_describer/        # 轨迹描述
└── devices/camera/        # 相机设备管理
```

#### 工作流程
```
1. 接收航点任务（来自concord2/MQTT）
   ↓
2. A*路径搜索（在voxel map中找初始路径）
   ↓
3. B样条轨迹优化
   - 平滑性约束
   - 动力学约束（速度/加速度限制）
   - 碰撞避免
   ↓
4. 输出轨迹指令 → px4ctrl
```

#### 配置：`launch/run.launch`

```xml
<launch>
    <arg name="odometry_actual_topic" value="/odom_center"/>
    <arg name="cloud_topic" value="/cloud_registered"/>
    <arg name="max_vel" value="1.0"/>   <!-- 最大速度 1m/s -->
    <arg name="max_acc" value="0.3"/>   <!-- 最大加速度 0.3m/s² -->

    <node pkg="plan_manager" type="planner_node" name="planner_node">
        <!-- FSM参数 -->
        <param name="fsm/check_collision_time" value="2.5"/>
        <param name="fsm/dist_check_far_from_ctrl" value="1.5"/>

        <!-- 规划器参数 -->
        <param name="manager/max_vel" value="1.0"/>
        <param name="manager/max_acc" value="0.3"/>
        <param name="manager/max_jerk" value="4"/>
        <param name="manager/planning_horizon" value="6"/>  <!-- 规划视野6m -->

        <!-- 轨迹优化 -->
        <param name="optimization/lambda_smooth" value="2.0"/>
        <param name="optimization/lambda_collision" value="1.5"/>
        <param name="optimization/dist0" value="0.2"/>  <!-- 障碍物安全距离 -->

        <!-- Voxel地图参数 -->
        <param name="voxel_map/resolution" value="0.1"/>      <!-- 分辨率10cm -->
        <param name="voxel_map/map_size_x" value="5.0"/>      <!-- 局部地图5m -->
        <param name="voxel_map/map_size_y" value="5.0"/>
        <param name="voxel_map/map_size_z" value="5.0"/>
        <param name="voxel_map/obstacles_inflation_x" value="0.2"/>  <!-- 膨胀20cm -->
        <param name="voxel_map/obstacles_inflation_y" value="0.2"/>
        <param name="voxel_map/obstacles_inflation_z" value="0.2"/>
        <param name="voxel_map/ground_height" value="-0.5"/>
        <param name="voxel_map/ceiling_height" value="5.0"/>
    </node>
</launch>
```

#### 关键参数说明
- **max_vel**: 最大飞行速度（默认1.0 m/s）
- **max_acc**: 最大加速度（默认0.3 m/s²）
- **planning_horizon**: 规划视野距离（6m）
- **obstacles_inflation**: 障碍物膨胀距离（0.2m安全边距）
- **voxel_map/resolution**: 地图分辨率（0.1m）

#### 输入
- `/odom_center` - 当前位姿
- `/cloud_registered` - 点云地图
- 航点任务（来自concord2）

#### 输出
- `/position_cmd` - 期望轨迹（位置+速度+加速度）
- `/planner_fsm_state` - FSM状态

---

### 5. px4ctrl - 飞控接口

**位置**：`src/realflight_modules/px4ctrl/`

**功能**：将规划轨迹转换为PX4飞控指令

**架构**：
```
/position_cmd (期望轨迹) → px4ctrl → MAVROS → PX4飞控 → 电机
```

#### 配置：`launch/run_ctrl.launch`
```xml
<launch>
    <node pkg="px4ctrl" type="px4ctrl_node" name="px4ctrl">
        <remap from="~odom" to="/odometry" />
        <remap from="~cmd" to="/position_cmd" />
        <rosparam command="load" file="$(find px4ctrl)/config/ctrl_param_fpv.yaml" />
    </node>
</launch>
```

**输入**：
- `/odometry` - 当前位姿反馈
- `/position_cmd` - 期望轨迹（来自planner_df）

**输出**：
- MAVROS话题（与PX4通信）
- `/px4ctrl/drone_state` - 飞行状态

**控制模式**：
- 位置控制（Position Control）
- 速度控制（Velocity Control）
- 姿态控制（Attitude Control）

---

### 6. livox_ros_driver - LiDAR驱动

**位置**：`src/livox_ros_driver2-master/` 或 `src/livox_ros_driver-master/`

**功能**：Livox激光雷达驱动程序

**支持型号**：
- Livox Mid360（当前使用）
- Livox Avia
- Livox Horizon
- Livox Mid-70/Mid-40

**输出**：
- `/livox/lidar` - 点云数据（PointCloud2）
- `/livox/imu` - IMU数据（Imu）

**启动**：
```bash
roslaunch livox_ros_driver2 msg_MID360.launch
```

---

### 7. usb_cam - 相机驱动

**位置**：`src/usb_cam-0.3.7/` 和 `src/usb_camera/`

**功能**：USB相机数据采集

**输出**：
- `/usb_cam/image_raw` - 原始图像
- `/usb_cam/image_raw/compressed` - 压缩图像（发送到MQTT）

**支持分辨率**：
- 4K（3840x2160）
- 1080p（1920x1080）
- 720p（1280x720）

---

### 8. utils - 工具库集合

**位置**：`src/utils/`

**包含子包**：
- `quadrotor_msgs` - 四旋翼消息定义
- `pose_utils` - 位姿工具
- `kalman_filter_utils` - 卡尔曼滤波
- `lpf_utils` - 低通滤波
- `uav_utils` - 无人机通用工具
- `DecompROS` - 几何分解
- `rviz_plugins` - RViz插件
- `catkin_simple` - Catkin构建工具

---

## 系统架构与数据流

### 整体架构图

```
┌────────────────────────────────────────────────────────────────────┐
│                     无人机机载系统 (ws)                              │
└────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌────────────────┐       ┌──────────────┐
│  硬件传感器   │       │   感知与定位    │       │  规划与控制   │
└──────────────┘       └────────────────┘       └──────────────┘
      │                       │                        │
      │                       │                        │
┌─────▼─────┐          ┌─────▼──────┐          ┌─────▼─────┐
│Livox Mid360│         │ FAST-LIVO2 │          │planner_df │
│  (LiDAR)   │─────→   │ VIO SLAM   │─────→    │路径规划器  │
└───────────┘          └────────────┘          └───────────┘
                              │                        │
┌───────────┐                 │                        │
│USB Camera │                 │                        │
│  (4K/FPV) │─────→           │                        │
└───────────┘          ┌──────▼──────┐          ┌─────▼─────┐
                       │   mapper    │          │  px4ctrl  │
┌───────────┐          │  地图构建    │          │ 飞控接口   │
│    IMU    │─────→    └─────────────┘          └───────────┘
└───────────┘                 │                        │
                              │                        │
┌───────────┐                 │                        │
│  GNSS     │                 │                        ▼
│ (可选GPS) │                 │                  ┌──────────┐
└───────────┘                 │                  │PX4飞控   │
                              │                  │MAVROS    │
                              │                  └──────────┘
┌─────────────────────────────▼─────────────────────────────┐
│                     concord2 通信中枢                       │
│              ROS ↔ Protobuf ↔ MQTT ↔ 地面站                │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Web控制系统      │
                    │ drone-web-control│
                    └──────────────────┘
```

### 详细数据流

#### 1. 传感器数据采集层
```
Livox Mid360 ──→ /livox/lidar (10Hz, PointCloud2)
             └──→ /livox/imu (200Hz, Imu)

USB Camera   ──→ /usb_cam/image_raw/compressed (30Hz, CompressedImage)

GNSS (可选)  ──→ /gps/fix (1Hz, NavSatFix)
```

#### 2. SLAM定位层
```
/livox/lidar + /livox/imu + Camera
              ↓
      ┌──────────────┐
      │  FAST-LIVO2  │
      └──────────────┘
              ↓
┌─────────────┴─────────────┐
│                           │
▼                           ▼
/aft_mapped_to_init    /cloud_registered
(全局位姿 Odometry)     (配准点云 PointCloud2)
```

#### 3. 地图构建层
```
/cloud_registered + /aft_mapped_to_init
              ↓
      ┌──────────────┐
      │    mapper    │
      └──────────────┘
              ↓
    3D Voxel Occupancy Map
   (分辨率0.1m, 概率占据)
```

#### 4. 任务规划层
```
Web端 → MQTT → /daf/mission
              ↓
      ┌──────────────┐
      │  concord2    │← ROS订阅
      └──────────────┘
              ↓
         Mission ROS Topic
              ↓
      ┌──────────────┐
      │  planner_df  │← Voxel Map
      │              │← /aft_mapped_to_init
      └──────────────┘
              ↓
      /position_cmd (轨迹指令)
```

#### 5. 飞行控制层
```
/position_cmd + /odometry
              ↓
      ┌──────────────┐
      │   px4ctrl    │
      └──────────────┘
              ↓
         MAVROS Topics
              ↓
      ┌──────────────┐
      │  PX4 Pixhawk │
      └──────────────┘
              ↓
          电机控制
```

#### 6. 数据回传层
```
/aft_mapped_to_init  ──┐
/cloud_registered    ──┤
/usb_cam/image_raw   ──┤──→ concord2 ──→ Protobuf编码 ──→ MQTT发布
/px4ctrl/drone_state ──┤
/planner_fsm_state   ──┘
              ↓
         Web端/地面站
```

---

## 通信协议

### ROS话题列表

| 话题名称 | 消息类型 | 频率 | 发布者 | 订阅者 | 说明 |
|---------|---------|------|--------|--------|------|
| `/livox/lidar` | sensor_msgs/PointCloud2 | 10Hz | livox_driver | FAST-LIVO2, mapper | LiDAR点云 |
| `/livox/imu` | sensor_msgs/Imu | 200Hz | livox_driver | FAST-LIVO2 | IMU数据 |
| `/usb_cam/image_raw` | sensor_msgs/Image | 30Hz | usb_cam | FAST-LIVO2 | 原始图像 |
| `/usb_cam/image_raw/compressed` | sensor_msgs/CompressedImage | 30Hz | usb_cam | concord2 | 压缩图像 |
| `/aft_mapped_to_init` | nav_msgs/Odometry | 10Hz | FAST-LIVO2 | mapper, planner_df, concord2 | 全局位姿 |
| `/cloud_registered` | sensor_msgs/PointCloud2 | 5Hz | FAST-LIVO2 | mapper, planner_df, concord2 | 配准点云 |
| `/odom_center` | nav_msgs/Odometry | 100Hz | - | planner_df | 中心里程计 |
| `/odom_ctrl` | nav_msgs/Odometry | 100Hz | - | planner_df | 控制里程计 |
| `/fcu_odom_from_obv` | nav_msgs/Odometry | 100Hz | - | concord2 | 飞控里程计 |
| `/position_cmd` | quadrotor_msgs/PositionCommand | 50Hz | planner_df | px4ctrl | 期望轨迹 |
| `/px4ctrl/drone_state` | - | 400Hz | px4ctrl | concord2 | 飞行状态 |
| `/planner_fsm_state` | std_msgs/Int32 | 1Hz | planner_df | concord2 | 任务状态 |

### MQTT话题列表

| MQTT话题 | 方向 | Protobuf类型 | 频率 | 说明 |
|---------|------|-------------|------|------|
| `/daf/mission` | ← (订阅) | daf.mission.Mission | - | 任务下发 |
| `/daf/mission/execution` | ← (订阅) | daf.mission.Execution | - | 任务执行控制 |
| `/daf/command` | ← (订阅) | daf.control.Command | - | 直接控制指令 |
| `/daf/local/odometry` | → (发布) | geometry_msgs.Odometry | 5Hz | 位姿反馈 |
| `/daf/pointcloud` | → (发布) | sensor_msgs.PointCloud2 | 5Hz | 点云数据 |
| `/daf/camera` | → (发布) | sensor_msgs.CompressedImage | 5Hz | 相机图像 |
| `/daf/heartbeat` | → (发布) | daf.drone.Heartbeat | 1Hz | 心跳包 |
| `/daf/mission/receipt` | → (发布) | daf.mission.Receipt | - | 任务确认 |

### Protobuf消息结构

#### Mission（任务）
```protobuf
message Mission {
    string id = 1;              // 任务ID（唯一）
    repeated Task tasks = 2;    // 任务列表
}

message Task {
    oneof task_type {
        TakeOff take_off = 1;       // 起飞
        Land land = 2;              // 降落
        AutoPilot auto_pilot = 3;   // 自主飞行
        Line line = 4;              // 直线飞行
    }
}

message AutoPilot {
    Vector3f position = 1;         // 目标位置 (x, y, z)
    float yaw = 2;                 // 航向角 (rad)
    CameraParam camera_param = 11; // 相机参数
}

message TakeOff {}  // 起飞（无参数）
message Land {}     // 降落（无参数）
```

#### Execution（任务控制）
```protobuf
message Execution {
    string id = 1;      // 任务ID
    Action action = 2;  // 控制动作
}

enum Action {
    START = 0;   // 开始任务
    PAUSE = 1;   // 暂停任务
    RESUME = 2;  // 恢复任务
    STOP = 3;    // 停止任务
    CLEAR = 4;   // 清除任务
}
```

#### Command（控制指令）
```protobuf
message Command {
    string module = 1;  // 模块名称
    Action action = 2;  // 控制动作
}

enum Action {
    STOP = 0;
    START = 1;
    RESTART = 2;
}
```

#### CameraParam（相机参数）
```protobuf
message CameraParam {
    bool on = 1;       // 是否打开相机
    Mode mode = 2;     // 模式
    float interval = 3; // 间隔时间（ms）
}

enum Mode {
    PHOTO = 0;  // 拍照模式（枚举值必须用数字0）
    VIDEO = 1;  // 录像模式（枚举值必须用数字1）
}
```

---

## 配置文件说明

### 主要配置文件清单

| 文件路径 | 作用 | 关键参数 |
|---------|------|---------|
| `concord2/config/drone.yaml` | MQTT通信配置 | MQTT地址、模块列表、话题映射 |
| `realflight_modules/mapper/config/mid360.yaml` | 地图构建配置 | Voxel大小、外参标定 |
| `planner_df/plan_manager/launch/run.launch` | 规划器配置 | 速度/加速度限制、地图参数 |
| `realflight_modules/px4ctrl/config/ctrl_param_fpv.yaml` | 飞控参数 | PID参数、控制增益 |

### concord2/config/drone.yaml 详解

```yaml
sn: "daf"  # 无人机序列号，用于MQTT话题前缀

mqtt:
  host: "localhost"      # MQTT Broker地址
  port: 1883             # MQTT端口
  keep_alive: 10         # 保活时间（秒）
  enable_tls: false      # 是否启用TLS加密

# 启用的功能模块列表
modules:
  - "mavros"                      # MAVLink通信
  - "mid360"                      # Livox Mid360驱动
  - "usb-cam-fpv_4k"              # 4K FPV相机
  - "mapper-mid360"               # 地图构建
  - "px4ctrl"                     # 飞控接口
  - "planner-df"                  # 路径规划器
  - "planner-df-device-camera"    # 相机设备

# ROS → MQTT 监听器（发布到MQTT）
monitors:
  odometry:                              # 位姿监听
    ros_topic: "/aft_mapped_to_init"     # 订阅的ROS话题
    rate: 200                            # 监听频率（Hz）

  flight_control:                        # 飞行状态监听
    ros_topic: "/px4ctrl/drone_state"
    rate: 400

  lidar:                                 # LiDAR监听
    ros_topic: "/livox/lidar"
    rate: 30

  fpv_camera:                            # 相机监听
    ros_topic: "/usb_cam/image_raw/compressed"
    rate: 30

  mission_state:                         # 任务状态监听
    ros_topic: "/planner_fsm_state"
    rate: 1

# MQTT → ROS 广播器（从MQTT接收）
broadcasters:
  camera:                                # 相机数据
    ros_topic: "/usb_cam/image_raw/compressed"
    filter_rate: 5                       # 过滤频率

  pointcloud:                            # 点云数据
    ros_topic: "/cloud_registered"
    filter_rate: 5

  local_odometry:                        # 局部里程计
    ros_topic: "/fcu_odom_from_obv"
    mqtt_topic: "/local/odometry"        # 自定义MQTT话题
    filter_rate: 5
```

### mapper/config/mid360.yaml 详解

```yaml
lidar:
  topic: "/livox/lidar"       # LiDAR话题
  scan_lines: 4               # 扫描线数
  blind_distance: 0.6         # 盲区距离（米）
  input_filter_rate: 2        # 输入降采样率
  output_filter_rate: 5       # 输出降采样率
  type: 2                     # LiDAR类型（2=Livox）

  # LiDAR到IMU的旋转矩阵（行优先）
  r_imu_lidar: [1, 0, 0,
                0, 1, 0,
                0, 0, 1]
  # LiDAR到IMU的平移向量
  t_imu_lidar: [-0.011, -0.02329, 0.04412]

imu:
  topic: "/livox/imu"

mapping:
  cov_gyr: 0.1                # 陀螺仪协方差
  cov_acc: 0.1                # 加速度计协方差
  cov_bg: 0.0001              # 陀螺仪偏差协方差
  cov_ba: 0.0001              # 加速度计偏差协方差
  cov_lidar: 0.005            # LiDAR协方差
  voxel_size: 0.1             # 体素大小（米）⭐
  plane_threshold: 0.025      # 平面拟合阈值
  neighbor_size: 5            # 邻域大小
  neighbor_distance: 2.235    # 邻域距离
  initial_map_size: 10000     # 初始地图大小

calibration:
  # LiDAR到PX4_IMU的外参（通过lidar_IMU_Init标定获得）
  # 旋转矩阵的转置
  R_L_I_PX4: [0.936120,  0.034542, -0.349981,
             -0.041129,  0.999089, -0.011405,
              0.349268,  0.025071,  0.936688]
  # 平移向量的负值
  T_L_I_PX4: [-0.055477, -0.015877, -0.068395]
```

### planner_df 关键参数

```xml
<!-- 最大速度和加速度 -->
<arg name="max_vel" value="1.0"/>     <!-- 1 m/s -->
<arg name="max_acc" value="0.3"/>     <!-- 0.3 m/s² -->

<!-- FSM（有限状态机）参数 -->
<param name="fsm/check_collision_time" value="2.5"/>           <!-- 碰撞检查时间 -->
<param name="fsm/dist_check_far_from_ctrl" value="1.5"/>       <!-- 偏离控制距离 -->
<param name="fsm/mission_end_wait_time" value="1.0"/>          <!-- 任务结束等待 -->

<!-- 规划器参数 -->
<param name="manager/planning_horizon" value="6"/>             <!-- 规划视野（米）-->
<param name="manager/control_points_distance" value="0.1"/>    <!-- 控制点间距 -->
<param name="manager/time_forward" value="1.5"/>               <!-- 前向时间 -->

<!-- 轨迹优化权重 -->
<param name="optimization/lambda_smooth" value="2.0"/>         <!-- 平滑性 -->
<param name="optimization/lambda_collision" value="1.5"/>      <!-- 避碰 -->
<param name="optimization/lambda_feasibility" value="0.1"/>    <!-- 可行性 -->
<param name="optimization/lambda_fitness" value="2.0"/>        <!-- 适应性 -->
<param name="optimization/dist0" value="0.2"/>                 <!-- 安全距离 -->

<!-- Voxel地图参数 -->
<param name="voxel_map/resolution" value="0.1"/>               <!-- 分辨率 10cm -->
<param name="voxel_map/map_size_x" value="5.0"/>               <!-- 地图尺寸 -->
<param name="voxel_map/map_size_y" value="5.0"/>
<param name="voxel_map/map_size_z" value="5.0"/>
<param name="voxel_map/obstacles_inflation_x" value="0.2"/>    <!-- 障碍物膨胀 -->
<param name="voxel_map/obstacles_inflation_y" value="0.2"/>
<param name="voxel_map/obstacles_inflation_z" value="0.2"/>
<param name="voxel_map/ground_height" value="-0.5"/>           <!-- 地面高度 -->
<param name="voxel_map/ceiling_height" value="5.0"/>           <!-- 天花板高度 -->

<!-- 概率占据参数 -->
<param name="voxel_map/p_hit" value="0.75"/>                   <!-- 击中概率 -->
<param name="voxel_map/p_miss" value="0.48"/>                  <!-- 未击中概率 -->
<param name="voxel_map/p_min" value="0.12"/>                   <!-- 最小概率 -->
<param name="voxel_map/p_max" value="0.90"/>                   <!-- 最大概率 -->
<param name="voxel_map/p_occ" value="0.80"/>                   <!-- 占据阈值 -->
<param name="voxel_map/min_ray_length" value="0.1"/>           <!-- 最小射线长度 -->
<param name="voxel_map/max_ray_length" value="5.0"/>           <!-- 最大射线长度 -->
```

---

## 启动与运行

### 构建系统

#### 首次构建
```bash
cd /path/to/ws
sudo chmod 777 build_x86.sh  # x86架构
# 或
sudo chmod 777 build_nx.sh   # ARM架构（Jetson NX）

./build_x86.sh
```

#### 增量编译
```bash
cd /path/to/ws
catkin_make
source devel/setup.bash
```

### 标准启动流程

#### 1. 启动硬件驱动

**Livox Mid360 LiDAR**
```bash
roslaunch livox_ros_driver2 msg_MID360.launch
```

**USB相机**
```bash
roslaunch usb_cam usb_cam.launch
```

#### 2. 启动SLAM定位
```bash
roslaunch fast_livo mapping_mid360.launch
```

#### 3. 启动地图构建
```bash
roslaunch mapper mid360.launch
```

#### 4. 启动路径规划
```bash
roslaunch plan_manager run.launch
```

#### 5. 启动飞控接口
```bash
roslaunch px4ctrl run_ctrl.launch
```

#### 6. 启动通信节点
```bash
roslaunch concord2 drone.launch
```

### 一键启动（推荐）

创建主启动文件 `launch/system.launch`：
```xml
<launch>
    <!-- 1. 硬件驱动 -->
    <include file="$(find livox_ros_driver2)/launch/msg_MID360.launch" />

    <!-- 2. SLAM -->
    <include file="$(find fast_livo)/launch/mapping_mid360.launch" />

    <!-- 3. 地图 -->
    <include file="$(find mapper)/launch/mid360.launch" />

    <!-- 4. 规划 -->
    <include file="$(find plan_manager)/launch/run.launch" />

    <!-- 5. 控制 -->
    <include file="$(find px4ctrl)/launch/run_ctrl.launch" />

    <!-- 6. 通信 -->
    <include file="$(find concord2)/launch/drone.launch" />
</launch>
```

启动：
```bash
roslaunch system.launch
```

### 常用命令

#### 查看话题
```bash
rostopic list          # 列出所有话题
rostopic echo /aft_mapped_to_init  # 查看位姿
rostopic hz /livox/lidar           # 查看频率
```

#### 查看节点
```bash
rosnode list           # 列出所有节点
rosnode info /mapper   # 查看节点信息
```

#### 录制数据
```bash
# 录制所有话题
rosbag record -a

# 录制指定话题
rosbag record /livox/lidar /aft_mapped_to_init /usb_cam/image_raw

# 使用提供的脚本
bash shfiles/record.sh
```

#### 回放数据
```bash
rosbag play xxx.bag
```

#### 可视化（RViz）
```bash
rviz
# 或使用预配置
roslaunch mapper mid360.launch rviz:=true
```

#### 提取点云
```bash
# 提取单帧点云
rosrun pcl_ros bag_to_pcd xxx.bag /cloud_registered /output/path/

# 查看点云
pcl_viewer output.pcd

# 使用CloudCompare
flatpak run org.cloudcompare.CloudCompare
```

---

## 扩展开发指南

### 添加新的ROS包

#### 1. 创建新包
```bash
cd ws/src
catkin_create_pkg my_package roscpp std_msgs geometry_msgs
```

#### 2. 编写代码
```cpp
// my_package/src/my_node.cpp
#include <ros/ros.h>
#include <geometry_msgs/PoseStamped.h>

int main(int argc, char** argv) {
    ros::init(argc, argv, "my_node");
    ros::NodeHandle nh;

    ros::Publisher pub = nh.advertise<geometry_msgs::PoseStamped>("/my_pose", 10);
    ros::Rate rate(10);

    while(ros::ok()) {
        geometry_msgs::PoseStamped msg;
        // ... 填充消息
        pub.publish(msg);
        rate.sleep();
    }

    return 0;
}
```

#### 3. 修改CMakeLists.txt
```cmake
add_executable(my_node src/my_node.cpp)
target_link_libraries(my_node ${catkin_LIBRARIES})
```

#### 4. 编译
```bash
cd ws
catkin_make
source devel/setup.bash
```

### 实现自主探索功能

基于现有系统，有3种实现方案：

#### 方案A：修改planner_df（推荐）

在 `planner_df/plan_manager` 中添加探索FSM状态：

```cpp
// plan_manager/src/planner_fsm.cpp

enum FSM_STATE {
  EXEC_TRAJ,
  REPLAN,
  WAIT_MISSION,
  EXPLORATION  // ← 新增
};

void PlannerFSM::explorationCallback(const ros::TimerEvent& e) {
  // 1. 从mapper获取voxel map
  auto voxel_map = getVoxelMap();

  // 2. 检测前沿点（frontier detection）
  std::vector<Eigen::Vector3d> frontiers = detectFrontiers(voxel_map);

  if (frontiers.empty()) {
    ROS_INFO("Exploration completed!");
    changeFSMState(WAIT_MISSION);
    return;
  }

  // 3. 选择最优前沿点
  Eigen::Vector3d next_goal = selectBestFrontier(frontiers, current_pos_);

  // 4. 调用现有的轨迹规划
  planGlobalTraj(next_goal);

  // 5. 发布探索状态
  publishExplorationStatus(frontiers.size(), explored_volume_);
}

std::vector<Eigen::Vector3d> PlannerFSM::detectFrontiers(VoxelMap* map) {
  std::vector<Eigen::Vector3d> frontiers;

  // 遍历地图，找到已知空闲格子且邻接未知格子的位置
  for (int x = 0; x < map->size_x; ++x) {
    for (int y = 0; y < map->size_y; ++y) {
      for (int z = 0; z < map->size_z; ++z) {
        if (map->getOccupancy(x, y, z) == FREE) {
          // 检查邻域
          if (hasUnknownNeighbor(map, x, y, z)) {
            Eigen::Vector3d pos = map->gridToWorld(x, y, z);
            frontiers.push_back(pos);
          }
        }
      }
    }
  }

  return clusterFrontiers(frontiers);  // 聚类前沿点
}
```

#### 方案B：创建新ROS节点

```bash
cd ws/src
catkin_create_pkg exploration_node roscpp nav_msgs geometry_msgs
```

```cpp
// exploration_node/src/explorer.cpp
#include <ros/ros.h>
#include <nav_msgs/OccupancyGrid.h>
#include <geometry_msgs/PoseStamped.h>

class AutonomousExplorer {
private:
  ros::NodeHandle nh_;
  ros::Subscriber map_sub_;
  ros::Subscriber odom_sub_;
  ros::Publisher waypoint_pub_;

  nav_msgs::OccupancyGrid current_map_;
  geometry_msgs::PoseStamped current_pose_;

public:
  AutonomousExplorer() {
    map_sub_ = nh_.subscribe("/mapper/occupancy_map", 1,
                             &AutonomousExplorer::mapCallback, this);
    odom_sub_ = nh_.subscribe("/aft_mapped_to_init", 10,
                              &AutonomousExplorer::odomCallback, this);
    waypoint_pub_ = nh_.advertise<geometry_msgs::PoseStamped>("/exploration/waypoint", 10);
  }

  void mapCallback(const nav_msgs::OccupancyGrid::ConstPtr& msg) {
    current_map_ = *msg;
    exploreStep();
  }

  void odomCallback(const geometry_msgs::PoseStamped::ConstPtr& msg) {
    current_pose_ = *msg;
  }

  void exploreStep() {
    // 1. 检测前沿点
    auto frontiers = detectFrontiers(current_map_);

    // 2. 选择目标
    auto next_goal = selectBestFrontier(frontiers, current_pose_);

    // 3. 发布航点（planner_df会自动规划轨迹）
    waypoint_pub_.publish(next_goal);
  }
};

int main(int argc, char** argv) {
  ros::init(argc, argv, "autonomous_explorer");
  AutonomousExplorer explorer;
  ros::spin();
  return 0;
}
```

#### 方案C：Web端探索引擎

在 `drone-web-control` 后端实现：

```javascript
// server/exploration-engine.js
class ExplorationEngine {
  constructor(mqttClient) {
    this.mqtt = mqttClient;
    this.occupancyMap = null;
    this.currentPos = null;
    this.explorationActive = false;
  }

  onPointCloudReceived(pointcloud) {
    // 1. 更新占据地图
    this.updateOccupancyMap(pointcloud);

    if (!this.explorationActive) return;

    // 2. 检测前沿点
    const frontiers = this.detectFrontiers();

    if (frontiers.length === 0) {
      console.log('Exploration complete');
      this.stopExploration();
      return;
    }

    // 3. 选择最优目标
    const nextGoal = this.selectBestFrontier(frontiers);

    // 4. 通过MQTT下发任务
    this.publishWaypointMission(nextGoal);
  }

  detectFrontiers() {
    const frontiers = [];
    const map = this.occupancyMap;

    for (let x = 1; x < map.width - 1; x++) {
      for (let y = 1; y < map.height - 1; y++) {
        if (map.data[y * map.width + x] === 0) {  // 空闲格子
          // 检查8邻域是否有未知格子
          if (this.hasUnknownNeighbor(x, y)) {
            frontiers.push({x, y});
          }
        }
      }
    }

    return this.clusterFrontiers(frontiers);
  }

  publishWaypointMission(goal) {
    const mission = {
      id: 'exploration_' + Date.now(),
      tasks: [
        {
          autoPilot: {
            position: { x: goal.x, y: goal.y, z: 1.0 },
            yaw: 0,
            cameraParam: { on: false, mode: 0, interval: 0 }
          }
        }
      ]
    };

    this.mqtt.publishMission(mission);
  }
}

module.exports = ExplorationEngine;
```

### 修改通信协议

#### 添加新的Protobuf消息

1. 在 `concord2/proto/` 创建新文件：
```protobuf
// exploration.proto
syntax = "proto3";
package daf.exploration;

message ExplorationCommand {
    bool enable = 1;           // 是否启用探索
    float max_distance = 2;    // 最大探索距离
    float max_duration = 3;    // 最大探索时间
}

message ExplorationStatus {
    float explored_volume = 1;      // 已探索体积
    int32 frontiers_count = 2;      // 前沿点数量
    bool is_exploring = 3;          // 是否正在探索
}
```

2. 修改 `concord2/proto/CMakeLists.txt`：
```cmake
add_custom_command(
  OUTPUT exploration.pb.cc exploration.pb.h
  COMMAND protoc --cpp_out=. ${CMAKE_CURRENT_SOURCE_DIR}/exploration.proto
  DEPENDS exploration.proto
)
```

3. 在 `concord2` 中订阅/发布新消息

### 添加新的MQTT话题

修改 `concord2/config/drone.yaml`：

```yaml
broadcasters:
  exploration_command:
    ros_topic: "/exploration/command"
    mqtt_topic: "/daf/exploration/command"

monitors:
  exploration_status:
    ros_topic: "/exploration/status"
    mqtt_topic: "/daf/exploration/status"
    rate: 1
```

### 调试技巧

#### 1. 使用RViz可视化
```bash
# 查看点云
rosrun rviz rviz
# 添加 PointCloud2 显示，选择话题 /cloud_registered

# 查看地图
# 添加 OccupancyGrid 或 MarkerArray

# 查看轨迹
# 添加 Path，选择 /planner/trajectory
```

#### 2. 使用rqt_graph查看节点关系
```bash
rosrun rqt_graph rqt_graph
```

#### 3. 日志输出
```cpp
ROS_DEBUG("Debug message");    // 调试信息
ROS_INFO("Info message");      // 一般信息
ROS_WARN("Warning message");   // 警告
ROS_ERROR("Error message");    // 错误
ROS_FATAL("Fatal message");    // 致命错误
```

#### 4. 使用GDB调试
```xml
<!-- 在launch文件中 -->
<node launch-prefix="gdb -ex run --args" pkg="my_package" type="my_node" />
```

#### 5. 性能分析
```bash
# CPU使用情况
top -p $(pgrep -d',' my_node)

# ROS性能
rostopic hz /my_topic   # 频率
rostopic bw /my_topic   # 带宽
```

---

## 常见问题与解决

### 编译问题

**Q: catkin_make失败，提示找不到包**
```bash
A: 检查依赖是否安装：
rosdep install --from-paths src --ignore-src -r -y
```

**Q: Protobuf版本冲突**
```bash
A: 确认protobuf版本：
protoc --version
# 建议使用 libprotobuf-dev 3.6+
```

### 运行问题

**Q: LiDAR无数据**
```bash
A: 检查驱动：
rostopic hz /livox/lidar
# 检查USB连接和供电
```

**Q: SLAM漂移严重**
```bash
A:
1. 检查IMU标定
2. 运行 lidar_imu_init 重新标定
roslaunch lidar_imu_init livox_mid360.launch
```

**Q: 规划器不工作**
```bash
A: 检查状态机：
rostopic echo /planner_fsm_state
# 确保地图已构建
rostopic echo /mapper/occupancy_map
```

**Q: MQTT连接失败**
```bash
A: 检查broker地址和端口：
mosquitto -v   # 本地测试
# 检查 concord2/config/drone.yaml 中的 mqtt.host
```

### 性能优化

**Q: 点云处理太慢**
```bash
A: 调整过滤率：
# mapper/config/mid360.yaml
input_filter_rate: 2  # 增大此值
output_filter_rate: 5
```

**Q: 规划频率低**
```bash
A: 减小地图范围：
voxel_map/map_size_x: 5.0  # 从10.0减小到5.0
voxel_map/map_size_y: 5.0
voxel_map/map_size_z: 5.0
```

---

## 附录

### 坐标系定义

```
无人机本体坐标系（Body Frame）：
  X - 前（Forward）
  Y - 左（Left）
  Z - 上（Up）

世界坐标系（World Frame）：
  X - 东（East）或前
  Y - 北（North）或左
  Z - 上（Up）

LiDAR坐标系：
  由外参定义，通过 lidar_imu_init 标定
```

### 单位约定

- 距离：米（m）
- 速度：米/秒（m/s）
- 加速度：米/秒²（m/s²）
- 角度：弧度（rad）
- 角速度：弧度/秒（rad/s）
- 时间：秒（s）
- 频率：赫兹（Hz）

### 传感器规格

**Livox Mid360**
- 量程：0.05-70m（90%反射率）
- 视场角：360° × 59°
- 点频：200,000 pts/s
- 精度：±2cm（@10m）
- 帧率：10Hz

**IMU（内置于Mid360）**
- 频率：200Hz
- 陀螺仪量程：±2000 °/s
- 加速度计量程：±8g

### 参考资料

**论文**：
- FAST-LIVO2: https://arxiv.org/pdf/2408.14035
- EGO-Planner: https://arxiv.org/pdf/2008.08835

**开源项目**：
- FAST-LIVO2: https://github.com/hku-mars/FAST-LIVO2
- Livox SDK: https://github.com/Livox-SDK

**文档**：
- ROS Wiki: http://wiki.ros.org
- Livox Wiki: https://github.com/Livox-SDK/Livox-SDK/wiki
- PX4 Documentation: https://docs.px4.io

---

## 版本历史

- **v1.0** (2025-01-25): 初始版本，基于当前工作空间分析生成

---

## 联系方式

如有问题，请参考：
- ROS工作空间：`c:\Users\23054\Desktop\室内无人机\ws`
- 通信协议文档：`基于 MQTT 的无人机与地面控制通信协议文档-v1.1.5.pdf`
- Web控制系统：`drone-web-control/`

---

**文档结束**
