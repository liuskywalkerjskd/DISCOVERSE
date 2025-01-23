# DISCOVERSE Docker 环境配置

## 安装步骤

注意：将下面的`<YOUR-TAG>`替换成具体的docker image tag名称，如`v1.6.1`。

### 1. 克隆仓库
```bash
# 克隆子模块
git submodule update --init --recursive --depth 1

# 修改diff-gaussian-rasterization配置
cd submodules/diff-gaussian-rasterization/
git checkout 8829d14
# 修改第154行：将 (p_view.z <= 0.2f) 改为 (p_view.z <= 0.01f)
sed -i 's/(p_view.z <= 0.2f)/(p_view.z <= 0.01f)/' cuda_rasterizer/auxiliary.h
cd ../../
```

### 2. 下载资源文件
```bash
# 创建测试的输出目录
mkdir -p data
# 创建models目录
mkdir -p models/{meshes,textures,3dgs,mjcf,urdf}

# 从以下地址下载模型文件：
# 清华网盘: https://cloud.tsinghua.edu.cn/d/0b92cdaeb58e414d85cc/
# 百度网盘: https://pan.baidu.com/s/1yIRkHfXLbT5cftuQ5O_sWQ?pwd=rnkt

# 下载后将文件解压到对应目录：
# - meshes 文件 -> models/meshes/
# - textures 文件 -> models/textures/
# - 3dgs 文件 -> models/3dgs/
# - mjcf 文件 -> models/mjcf/
# - urdf 文件 -> models/urdf/
```

### 3. 构建和运行Docker容器
```bash
# 构建容器
docker build -t discoverse/<YOUR-TAG> .

# 允许Docker访问X11显示服务器
xhost +local:docker

# 运行容器
docker run -it --rm \
    --gpus all \
    --privileged=true \
    -e DISPLAY=$DISPLAY \
    -e QT_X11_NO_MITSHM=1 \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $(pwd):/workspace \
    discoverse/<YOUR-TAG> bash
```

注意：如果不需要图形界面，可以在运行Python脚本时添加参数：
```bash
python3 discoverse/envs/airbot_play_base.py --headless
```


## 验证安装

在容器内运行示例程序：
```bash
python3 discoverse/envs/airbot_play_base.py
```

## 💡 Usage

+ airbot_play robotic arm

```shell
python3 discoverse/envs/airbot_play_base.py
```

+ Robotic arm desktop manipulation tasks

```shell
python3 discoverse/examples/tasks_airbot_play/block_place.py
python3 discoverse/examples/tasks_airbot_play/coffeecup_place.py
python3 discoverse/examples/tasks_airbot_play/cuplid_cover.py
python3 discoverse/examples/tasks_airbot_play/drawer_open.py
```

+ Active SLAM

```shell
python3 discoverse/examples/active_slam/dummy_robot.py
```


## 版本检查

在容器内运行以下命令检查环境配置：
```bash
check-versions
```

## 前置要求

- 安装 Docker
- 安装 NVIDIA Driver (>= 525.60.13)
- 安装 NVIDIA Container Toolkit
- 确保你的CUDA版本与显卡兼容

## 环境配置说明

本项目使用以下主要组件版本：
- CUDA: 12.1.0
- PyTorch: 2.2.1
- Python: 3.9
- Ubuntu: 20.04





### NVIDIA环境配置
1. 安装NVIDIA Container Toolkit：
```bash
# 设置软件源
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
    && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
    && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 更新并安装
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit nvidia-docker2

# 重启Docker服务
sudo systemctl restart docker
```

2. 验证NVIDIA Docker安装：
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi
```

## 常见问题

1. 如果需要GUI支持，运行容器时需要添加以下参数：
```bash
docker run -it --rm \
    --gpus all \
    --privileged=true \
    -v $(pwd)/models:/workspace/DISCOVERSE/models \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    discoverse/<YOUR-TAG> bash
```

2. 如果遇到权限问题，可以在主机上运行：
```bash
xhost +local:docker
```

3. 如果遇到CUDA相关错误：
   - 确保已正确安装NVIDIA Driver和NVIDIA Container Toolkit
   - 检查你的显卡型号是否支持当前CUDA版本
   - 可以尝试修改Dockerfile中的CUDA基础镜像版本

4. 如果下载资源文件时遇到网络问题：
   - 可以尝试使用代理
   - 或者使用国内镜像源
   - 也可以分多次下载，确保每个文件都完整下载完成

5. 删除镜像
```bash
docker rmi discoverse/<YOUR-TAG>
```

6. 清理构建缓存
```bash
docker builder prune
```
