import os
import time
import sys
import pwd  # Linux用户信息模块
import yaml
import hashlib  # 导入hashlib模块用于计算SHA256哈希值
import logging
from logging.handlers import RotatingFileHandler

# 导入配置管理模块，替换硬编码的配置加载
from config_manager import global_config

# 设置日志系统
def setup_logging():
    # 获取全局配置
    config = global_config.get_config()
    
    # 从配置获取日志目录，如果没有则使用默认值
    if 'log_config' not in config or 'log_dir' not in config['log_config']:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    else:
        log_dir = config['log_config']['log_dir']
        
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        print(f"无法创建日志目录: {e}")
        # 使用当前目录作为备选
        log_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(log_dir, "file_scan.log")
    
    # 创建logger对象
    logger = logging.getLogger("file_scanner")
    
    # 从配置获取日志级别，如果没有则使用默认值
    if 'log_config' not in config or 'log_level' not in config['log_config']:
        logger.setLevel(logging.INFO)
    else:
        log_level = getattr(logging, config['log_config']['log_level'].upper(), logging.INFO)
        logger.setLevel(log_level)
    
    # 检查logger是否已有处理器，避免重复添加
    if not logger.handlers:
        # 创建文件处理器，设置追加模式
        file_handler = RotatingFileHandler(
            log_file,
            mode='a',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # 设置日志格式：时间 + 日志级别 + 消息
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        logger.addHandler(file_handler)
    
    return logger

# 初始化配置和日志
config = global_config.get_config()
scan_config = config["scan_config"]
scan_paths = scan_config["scan_paths"]
scan_interval = scan_config["scan_interval"]
file_types = scan_config["file_types"]
full_scan_cycle = scan_config["full_scan_cycle"]
blacklist = scan_config.get("blacklist", [])
logger = setup_logging()


def is_root():
    """判断当前是否以root权限运行（Ubuntu中管理员权限即root）"""
    try:
        return os.geteuid() == 0  # Linux系统中root的euid是0
    except AttributeError:
        return False  # 非Linux系统


def get_file_owner(file_path):
    """获取文件所有者信息（Ubuntu专用）"""
    try:
        stat_info = os.stat(file_path)
        uid = stat_info.st_uid
        return pwd.getpwuid(uid).pw_name  # 转换UID为用户名
    except:
        return "未知"


def calculate_file_sha256(file_path, block_size=65536):
    """计算文件的SHA256哈希值"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # 分块读取文件计算哈希值，避免大文件占用过多内存
            for block in iter(lambda: f.read(block_size), b""):
                sha256_hash.update(block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"计算哈希值错误 {file_path}: {str(e)}")
        return "计算失败"


def is_supported_file_type(file_name):
    """检查文件类型是否在支持的列表中"""
    # 获取文件扩展名（小写）
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()
    
    # 检查是否在支持的文件类型列表中
    return ext in file_types


# 在scan_directory函数之前添加一个新函数来检查路径是否在blacklist中

def is_blacklisted_path(path, blacklist):
    """检查路径是否在blacklist中"""
    # 标准化路径，确保比较时格式一致
    path = os.path.abspath(path)
    for blacklisted_path in blacklist:
        # 标准化blacklist路径
        blacklisted_path = os.path.abspath(blacklisted_path)
        # 检查路径是否以blacklist路径开头（即是否是blacklist路径的子路径）
        if path.startswith(blacklisted_path):
            return True
    return False

# 修改scan_directory函数，增加blacklist检查逻辑

def scan_directory(target_dir):
    """扫描目标目录下的所有文件，返回包含文件信息的列表"""
    # 检查目录有效性
    if not os.path.exists(target_dir):
        logger.error(f"目录 '{target_dir}' 不存在")
        return []
    
    if not os.path.isdir(target_dir):
        logger.error(f"'{target_dir}' 不是一个目录")
        return []
    
    # 记录当前权限状态
    logger.info(f"开始扫描目录: {target_dir}")
    logger.info(f"当前权限: {'root (管理员)' if is_root() else '普通用户'}")
    
    file_list = []  # 创建空列表存储文件信息
    file_count = 0
    permission_error_count = 0
    unsupported_count = 0
    skipped_blacklisted_count = 0  # 新增：记录跳过的blacklist文件数量
    
    # 遍历目录树
    for root, dirs, files in os.walk(target_dir):
        # 检查当前目录是否在blacklist中，如果是则跳过
        if is_blacklisted_path(root, blacklist):
            logger.info(f"跳过blacklist目录: {root}")
            # 清空dirs列表，避免继续递归这个目录
            dirs[:] = []
            continue
        
        # 检查并移除dirs中的blacklist目录
        dirs_to_remove = []
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if is_blacklisted_path(dir_path, blacklist):
                logger.info(f"跳过blacklist子目录: {dir_path}")
                dirs_to_remove.append(dir_name)
                skipped_blacklisted_count += 1
        
        # 从dirs中移除blacklist目录
        for dir_name in dirs_to_remove:
            dirs.remove(dir_name)
        
        for file in files:
            # 新增：过滤以._开头的隐藏文件
            if file.startswith('._'):
                logger.info(f"跳过隐藏文件: {os.path.join(root, file)}")
                continue
            
            # 检查文件类型是否支持
            if not is_supported_file_type(file):
                unsupported_count += 1
                continue
                
            file_path = os.path.join(root, file)
            
            # 检查文件是否在blacklist中
            if is_blacklisted_path(file_path, blacklist):
                logger.info(f"跳过blacklist文件: {file_path}")
                skipped_blacklisted_count += 1
                continue
            
            try:
                # 获取文件信息
                file_stats = os.stat(file_path)
                
                # 转换时间格式
                last_modify_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                          time.localtime(file_stats.st_mtime))
                
                # 获取文件大小（字节）
                file_size = file_stats.st_size
                
                # 计算文件SHA256哈希值
                file_hash = calculate_file_sha256(file_path)
                
                # 创建文件信息字典（结构体）
                file_info = {
                    "file_path": os.path.abspath(file_path),
                    "file_name": file,
                    "last_modify_time": last_modify_time,
                    "file_size": file_size,  # 单位：字节
                    "file_hash": file_hash
                }
                
                # 将文件信息添加到列表
                file_list.append(file_info)
                
                file_count += 1
                
                # 记录文件信息到日志
                logger.info(f"发现文件: {file_info['file_path']}, 大小: {file_size} 字节, 修改时间: {last_modify_time}")
                
            except PermissionError:
                permission_error_count += 1
                logger.warning(f"权限不足 (需要root)：{file_path}")
            except Exception as e:
                logger.error(f"访问错误 {file_path}: {str(e)}")
    
    logger.info(f"扫描完成：共发现 {file_count} 个文件")
    if permission_error_count > 0:
        logger.warning(f"注意：有 {permission_error_count} 个文件因权限问题无法访问")
        logger.warning(f"解决方法：使用sudo重新运行命令：sudo {sys.executable} {sys.argv[0]}")
    
    if unsupported_count > 0:
        logger.info(f"跳过 {unsupported_count} 个不支持的文件类型")
    
    if skipped_blacklisted_count > 0:
        logger.info(f"跳过 {skipped_blacklisted_count} 个在blacklist中的文件/目录")
    
    return file_list  # 返回文件信息列表




if __name__ == "__main__":
    # 获取目标目录（支持命令行参数或手动输入）
    if len(sys.argv) > 1:
        target_directory = sys.argv[1]
    else:
        target_directory = input("请输入要扫描的目录路径: ")
    
    # 扫描目录并获取文件信息列表
    files_info = scan_directory(target_directory)
    print(files_info)
    
    # 记录扫描结果统计信息
    logger.info(f"扫描结果：总共收集到 {len(files_info)} 个支持的文件的信息")