import os
import sys
import yaml
import logging
from logging.handlers import RotatingFileHandler
import time
import datetime
import pymysql
from pymysql.cursors import DictCursor
from file_scan import scan_directory
# 导入新的配置管理模块
from config_manager import global_config

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志系统
def setup_logging(config=None):
    # 从配置获取日志目录，如果没有则使用默认值
    if config is None or 'log_config' not in config or 'log_dir' not in config['log_config']:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    else:
        log_dir = config['log_config']['log_dir']
    
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        print(f"无法创建日志目录: {e}")
        # 使用当前目录作为备选
        log_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(log_dir, 'update_knowledge.log')
    
    # 配置日志记录器
    logger = logging.getLogger('update_knowledge')
    
    # 从配置获取日志级别，如果没有则使用默认值
    if config is None or 'log_config' not in config or 'log_level' not in config['log_config']:
        logger.setLevel(logging.INFO)
    else:
        log_level = getattr(logging, config['log_config']['log_level'], logging.INFO)
        logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if not logger.handlers:
        # 创建RotatingFileHandler，支持日志轮转
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        # 设置日志格式为：时间 ： 执行程序 + log信息
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加处理器到记录器
        logger.addHandler(file_handler)
        
        # 同时输出到控制台
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

# 连接到MySQL数据库
def connect_to_database(config):
    try:
        connection = pymysql.connect(
            host=config['mysql_config']['host'],
            user=config['mysql_config']['username'],
            password=config['mysql_config']['password'],
            database=config['mysql_config']['database'],
            port=config['mysql_config']['port'],
            cursorclass=DictCursor
        )
        logger.info("成功连接到MySQL数据库")
        return connection
    except Exception as e:
        logger.error(f"连接数据库失败: {e}")
        raise

# 检查文件是否需要更新
def check_file_needs_update(connection, file_info):
    try:
        with connection.cursor() as cursor:
            # 检查表是否存在
            check_table_sql = """
            SHOW TABLES LIKE 'file_feature_history'
            """
            cursor.execute(check_table_sql)
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                logger.warning("表file_feature_history不存在")
                return True, "表不存在"
            
            # 查询文件信息
            query_sql = """
            SELECT last_modify_time, file_hash 
            FROM file_feature_history 
            WHERE file_path = %s
            """
            cursor.execute(query_sql, (file_info['file_path'],))
            result = cursor.fetchone()
            
            # 如果文件不存在于数据库中
            if not result:
                return True, "文件不存在于数据库中"
            
            # 检查最后修改时间是否变化
            # 转换数据库中的datetime对象为字符串，与file_info中的格式保持一致
            db_time_str = result['last_modify_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(result['last_modify_time'], 'strftime') else str(result['last_modify_time'])
            if db_time_str != file_info['last_modify_time']:
                print(db_time_str, file_info['last_modify_time'], type(db_time_str), type(file_info['last_modify_time']))
                print(db_time_str == file_info['last_modify_time'])
                return True, "文件最后修改时间发生变化"
            
            # 检查哈希值是否变化
            if result['file_hash'] != file_info['file_hash']:
                return True, "文件哈希值发生变化"
            
            # 文件不需要更新
            return False, "文件未发生变化"
    except Exception as e:
        logger.error(f"检查文件是否需要更新时出错: {e}")
        return True, f"检查过程出错: {str(e)}"

# 可外部调用的公共函数
def check_files_for_update(config_path=None, scan_paths=None, pre_scanned_files=None):
    """
    检查哪些文件需要更新知识库
    
    参数:
        config_path: 可选，配置文件路径
        scan_paths: 可选，要扫描的目录路径列表，如未指定则从配置文件读取
        pre_scanned_files: 可选，预扫描的文件信息列表，如果提供则直接使用，不再重复扫描
        
    返回:
        tuple: 包含两个列表
            - 第一个列表: 不在数据库中的文件信息列表
            - 第二个列表: 在数据库中但内容发生变化（包括最后修改时间或哈希值变化）的文件信息列表
    """
    global logger
    
    try:
        # 加载配置
        if config_path:
            config = global_config.load_config(config_path)
        else:
            config = global_config.get_config()
        
        # 设置日志
        logger = setup_logging(config)
        
        # 确定扫描路径
        if scan_paths is None:
            scan_paths = config['scan_config']['scan_paths']
        
        logger.info(f"扫描路径: {scan_paths}")
        file_infos = []
        knowledge_base_id = ""
        
        # 检查是否提供了预扫描的文件信息
        if pre_scanned_files is not None:
            # 直接使用预扫描的文件信息
            logger.info(f"使用预扫描的文件信息，共 {len(pre_scanned_files)} 个文件")
            file_infos = pre_scanned_files
            # 根据配置获取知识库ID
            for scan_path in scan_paths:
                knowledge_base_id = config['dify_config']['knowledge_base_mapping'][scan_path]
                logger.info(f"使用对应知识库ID: {knowledge_base_id}")
                # 为每个文件添加对应的知识库ID
                for file_info in file_infos:
                    if file_info['file_path'].startswith(scan_path):
                        file_info['knowledge_base_id'] = knowledge_base_id
        else:
            # 原有的扫描逻辑
            for scan_path in scan_paths:
                logger.info(f"开始扫描目录: {scan_path}")
                # 扫描目录获取文件信息
                file_infos.extend(scan_directory(scan_path))
                logger.info(f"扫描完成，共发现 {len(file_infos)} 个文件")
                
                # 从配置中获取固定的知识库ID
                knowledge_base_id = config['dify_config']['knowledge_base_mapping'][scan_path]
                logger.info(f"使用对应知识库ID: {knowledge_base_id}")
        
        # 以下是原有的数据库检查逻辑，保持不变
        start_time = time.time()
        
        # 连接到数据库
        connection = connect_to_database(config)
        
        try:
            # 处理每个文件
            files_not_in_db = []  # 不在数据库中的文件列表
            files_with_changes = []  # 在数据库中但内容发生变化的文件列表
            
            # 为每个文件添加知识库ID（如果尚未添加）
            for file_info in file_infos:
                if 'knowledge_base_id' not in file_info:
                    # 为未指定知识库ID的文件分配默认ID
                    for scan_path in scan_paths:
                        if file_info['file_path'].startswith(scan_path):
                            file_info['knowledge_base_id'] = config['dify_config']['knowledge_base_mapping'][scan_path]
                            break
            
            # 原有的文件检查逻辑
            for file_info in file_infos:
                # 检查文件是否需要更新
                needs_update, reason = check_file_needs_update(connection, file_info)
                file_info['update_reason'] = reason
                
                # 根据不同的更新原因将文件分类到不同的列表
                if reason == "文件不存在于数据库中":
                    files_not_in_db.append(file_info)
                    logger.info(f"文件不在数据库中: {file_info['file_path']}")
                elif reason == "文件最后修改时间发生变化" or reason == "文件哈希值发生变化":
                    # 将哈希值变化和最后修改时间变化视为同种变化
                    files_with_changes.append(file_info)
                    logger.info(f"文件内容发生变化: {file_info['file_path']} - {reason}")
                elif needs_update:
                    # 其他需要更新的情况
                    logger.info(f"文件需要更新: {file_info['file_path']} - {reason}")
                else:
                    logger.info(f"文件无需更新: {file_info['file_path']}")
            
            # 输出结果摘要
            logger.info(f"扫描完成，共 {len(files_not_in_db)} 个文件不在数据库中")
            logger.info(f"扫描完成，共 {len(files_with_changes)} 个文件内容发生变化")
            
            # 返回两个列表
            return files_not_in_db, files_with_changes
            
        finally:
            # 关闭数据库连接
            connection.close()
            logger.info("已关闭数据库连接")
            
        end_time = time.time()
        logger.info(f"程序执行完成，耗时: {end_time - start_time:.2f} 秒")
        
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"程序执行出错: {e}")
        else:
            print(f"程序执行出错: {e}")
        raise

# 主函数
def main():
    try:
        # 调用公共函数并获取两个列表
        files_not_in_db, files_with_changes = check_files_for_update()
        
        # 输出结果
        print("\n不在数据库中的文件列表:")
        for file_info in files_not_in_db:
            print(f"文件路径: {file_info['file_path']}")
            print(f"文件名称: {file_info['file_name']}")
            print(f"最后修改时间: {file_info['last_modify_time']}")
            print(f"文件大小: {file_info['file_size']} 字节")
            print(f"文件哈希: {file_info['file_hash']}")
            print(f"知识库ID: {file_info['knowledge_base_id']}")
            print("---")
        
        print("\n在数据库中但内容发生变化的文件列表:")
        for file_info in files_with_changes:
            print(f"文件路径: {file_info['file_path']}")
            print(f"文件名称: {file_info['file_name']}")
            print(f"最后修改时间: {file_info['last_modify_time']}")
            print(f"文件大小: {file_info['file_size']} 字节")
            print(f"文件哈希: {file_info['file_hash']}")
            print(f"知识库ID: {file_info['knowledge_base_id']}")
            print(f"变化原因: {file_info['update_reason']}")
            print("---")
            
        print(f"\n总结: 共 {len(files_not_in_db)} 个文件不在数据库中，{len(files_with_changes)} 个文件内容发生变化")
            
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"程序执行出错: {e}")
        else:
            print(f"程序执行出错: {e}")
        raise

if __name__ == "__main__":
    main()