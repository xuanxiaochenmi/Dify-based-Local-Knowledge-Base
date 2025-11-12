# Dify-based-Local-Knowledge-Base-Construction-System

## 版本信息

- 当前版本：1.0.0
- 最后更新日期：2025-11-03


## 项目简介

Dify-based-Local-Knowledge-Base-Construction-System 是一个简单的本地知识库管理系统，用于自动扫描、管理本地文件并同步更新到 Dify 知识库平台。该系统支持文件的自动检测、上传、更新和删除，并提供完整的日志记录和错误处理机制。
- 注意：
    - 本项目基于dify的知识库平台，需要先自行部署dify知识库平台，具体部署步骤请参考dify官方文档。
    - 本项目仅支持扫描本地文件，不支持远程文件同步。

## 系统架构

系统由以下核心模块组成：

1. **main.py**：主程序入口，负责文件扫描、状态检测和知识库同步
2. **update_knowledge.py**：文件更新检测模块，用于检查文件是否需要更新
3. **update_dify.py**：Dify API 交互模块，负责文件的上传、更新和删除操作
4. **config_manager.py**：配置管理模块，提供统一的配置加载和命令行参数处理功能
5. **file_scan.py**：文件扫描模块，负责遍历指定路径下的文件

## 环境配置

在运行系统之前，请确保已安装所需的依赖库。项目依赖信息存储在 `requirements.txt` 文件中。

### 依赖库列表

```
# Local Knowledge Base 项目依赖库列表

# YAML配置文件解析库
pyyaml>=6.0

# MySQL数据库连接库
mysql-connector-python>=8.0.0

# HTTP请求库（用于Dify API调用）
requests>=2.28.0

# 可选：日志增强库（如需要更高级的日志功能）
# python-dotenv>=0.20.0
# logging-handlers>=0.1.0
```

### 安装步骤

1. 进入项目目录：
   ```bash
   cd /home/root01/Local_Knowledge_Base
   ```

2. 使用 pip 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 确保系统已安装 Python 3.8 或更高版本

### 虚拟环境建议

为了避免依赖冲突，建议在虚拟环境中运行项目：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/MacOS
source venv/bin/activate
# Windows
env\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 配置说明

系统配置存储在 config.yaml 文件中，包含以下主要配置项：

### 1. 扫描配置 (scan_config)
```yaml
scan_config:
  scan_paths:          # 需要扫描的文件路径列表
    - /path/to/folder1
    - /path/to/folder2
  blacklist:           # 扫描黑名单（不包含的文件或目录）
    - /path/to/exclude
  scan_interval: 3600  # 扫描间隔时间（秒）
```

### 2. Dify 配置 (dify_config)
```yaml
dify_config:
  api_key: "your_api_key"        # Dify API密钥
  base_url: "https://api.dify.ai"  # Dify服务基础URL
  knowledge_base_mapping:        # 文件路径与知识库ID的映射关系
    "/path/to/folder1": "kb_id_1"
    "/path/to/folder2": "kb_id_2"
```

### 3. MySQL 配置 (mysql_config)
```yaml
mysql_config:
  host: "localhost"      # 数据库主机
  port: 3306             # 数据库端口
  user: "root"           # 数据库用户名
  password: "password"   # 数据库密码
  database: "knowledge_db"  # 数据库名称
```

### 4. 日志配置 (log_config)
```yaml
log_config:
  log_dir: "./logs"       # 日志目录
  log_level: "INFO"       # 日志级别（DEBUG, INFO, WARNING, ERROR）
  alert_config:           # 告警配置
    enabled: false        # 是否启用告警
    email:                # 邮件配置
      recipients: []      # 收件人列表
      smtp_server: ""     # SMTP服务器
      smtp_port: 0        # SMTP端口
      username: ""        # SMTP用户名
      password: ""        # SMTP密码
```

## 使用方法

### 1. 基本使用

确保已安装所需依赖，然后直接运行主程序：

```bash
cd /home/root01/Local_Knowledge_Base
python main.py
```

### 2. 单独运行各模块

- **文件更新检测**：
  ```bash
  python update_knowledge.py
  ```

- **Dify API 操作**：
  ```bash
  python update_dify.py
  ```

## 命令行参数

系统支持通过命令行参数覆盖配置文件中的设置，格式为 `--配置项 新值`。例如：

### 常用命令行参数
```

```bash
# 修改扫描路径
python main.py --scan_paths "/path/to/new/folder" "/another/path"

# 修改 Dify API 密钥
python main.py --dify_api_key "new_api_key"

# 修改 MySQL 数据库信息
python main.py --mysql_database "new_db_name" --mysql_password "new_password"

# 修改日志级别
python main.py --log_level "DEBUG"
```

### 完整参数列表

- `--scan_paths`：扫描路径列表（多个路径用空格分隔）
- `--blacklist`：黑名单路径
- `--scan_interval`：扫描间隔（秒）
- `--dify_api_key`：Dify API 密钥
- `--dify_base_url`：Dify 基础 URL
- `--mysql_host`：MySQL 主机
- `--mysql_port`：MySQL 端口
- `--mysql_user`：MySQL 用户名
- `--mysql_password`：MySQL 密码
- `--mysql_database`：MySQL 数据库名
- `--log_dir`：日志目录
- `--log_level`：日志级别

## 日志系统

系统日志存储在 `./logs/` 目录下，包括：

- `main.log`：主程序运行日志
- `update_knowledge.log`：文件更新检测日志
- `update_dify.log`：Dify API 操作日志
- `file_scan.log`：文件扫描日志
- `cron_job.log`：定时任务执行日志

可以通过修改 `log_level` 配置来调整日志详细程度：
- `DEBUG`：最详细的日志，包含所有调试信息
- `INFO`：标准日志，记录正常运行信息
- `WARNING`：仅记录警告和错误信息
- `ERROR`：仅记录错误信息

## 工作流程

1. **配置加载**：系统启动时从 config.yaml 加载默认配置，并应用命令行参数中的覆盖设置
2. **文件扫描**：根据配置的路径扫描本地文件系统
3. **数据库同步**：将扫描结果与数据库中的记录进行比对
4. **文件处理**：
   - 新增文件：上传到 Dify 知识库
   - 修改文件：更新 Dify 知识库中的对应文件
   - 删除文件：从 Dify 知识库中删除对应文件
5. **错误处理**：自动重试上传失败的文件，并记录详细错误信息

## 定时任务设置

如需设置定时执行，可以使用 Linux 的 cron 服务：

```bash
# 编辑 crontab 配置
crontab -e

# 添加每天凌晨 2 点执行的任务
0 2 * * * cd /home/root01/Local_Knowledge_Base && python main.py >> ./logs/cron_job.log 2>&1
```

## 常见问题排查

1. **文件无法上传**：检查 Dify API 密钥和知识库 ID 是否正确
2. **数据库连接失败**：验证 MySQL 配置是否正确，确保数据库服务正常运行
3. **日志文件过大**：可以调整日志级别或定期清理日志文件
4. **扫描效率低**：减少扫描路径或增加扫描间隔时间

## 注意事项

1. 请妥善保管配置文件中的 API 密钥和数据库密码等敏感信息
2. 首次运行前，请确保已创建对应的数据库和表
3. 对于大量文件的场景，建议适当增加扫描间隔时间以减少系统资源占用
4. 定期备份数据库以防数据丢失

---
        