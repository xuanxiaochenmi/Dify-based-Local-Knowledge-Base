import os
import sys
import yaml
import pymysql
from pymysql.cursors import DictCursor
import update_knowledge as uk
import update_dify as ud
import logging
from logging.handlers import RotatingFileHandler
from file_scan import scan_directory  # 添加这一行导入

# 导入新的配置管理模块
from config_manager import global_config, parse_args, apply_args_to_config

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
    
    log_file = os.path.join(log_dir, 'main.log')
    
    # 配置日志记录器
    logger = logging.getLogger('main')
    
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
        
        # 设置日志格式
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

# 创建数据表（如果不存在）
def create_table_if_not_exists(connection):
    try:
        with connection.cursor() as cursor:
            # 创建file_feature_history表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS file_feature_history (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                file_path VARCHAR(767) NOT NULL UNIQUE,
                file_name VARCHAR(255) NOT NULL,
                last_modify_time DATETIME NOT NULL,
                file_size BIGINT NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                knowledge_base_id VARCHAR(50) NOT NULL,
                dify_document_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cursor.execute(create_table_sql)
            connection.commit()
            logger.info("检查并确保表file_feature_history存在")
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        raise

# 将文件信息写入数据库
def insert_file_info(connection, file_info, document_id):
    try:
        with connection.cursor() as cursor:
            insert_sql = """
            INSERT INTO file_feature_history (
                file_path, file_name, last_modify_time, file_size, 
                file_hash, knowledge_base_id, dify_document_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (
                file_info['file_path'],
                file_info['file_name'],
                file_info['last_modify_time'],
                file_info['file_size'],
                file_info['file_hash'],
                file_info['knowledge_base_id'],
                document_id
            ))
            connection.commit()
            logger.info(f"已将文件信息写入数据库: {file_info['file_path']}")
    except Exception as e:
        logger.error(f"写入文件信息到数据库失败: {e}")
        raise

# 更新数据库中的文件信息
def update_file_info(connection, file_info):
    try:
        with connection.cursor() as cursor:
            update_sql = """
            UPDATE file_feature_history 
            SET last_modify_time = %s, 
                file_size = %s, 
                file_hash = %s 
            WHERE file_path = %s
            """
            cursor.execute(update_sql, (
                file_info['last_modify_time'],
                file_info['file_size'],
                file_info['file_hash'],
                file_info['file_path']
            ))
            connection.commit()
            logger.info(f"已更新数据库中的文件信息: {file_info['file_path']}")
    except Exception as e:
        logger.error(f"更新文件信息到数据库失败: {e}")
        raise

# 获取文件在数据库中的dify_document_id
def get_document_id(connection, file_path):
    try:
        with connection.cursor() as cursor:
            query_sql = """
            SELECT dify_document_id 
            FROM file_feature_history 
            WHERE file_path = %s
            """
            cursor.execute(query_sql, (file_path,))
            result = cursor.fetchone()
            if result:
                return result['dify_document_id']
            return None
    except Exception as e:
        logger.error(f"获取文档ID失败: {e}")
        raise

# 获取数据库中所有文件的路径
def get_all_files_in_db(connection):
    try:
        with connection.cursor() as cursor:
            query_sql = """
            SELECT file_path, dify_document_id, knowledge_base_id 
            FROM file_feature_history
            """
            cursor.execute(query_sql)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"获取数据库中所有文件失败: {e}")
        raise

# 从数据库中删除文件记录
def delete_file_from_db(connection, file_path):
    try:
        with connection.cursor() as cursor:
            delete_sql = """
            DELETE FROM file_feature_history 
            WHERE file_path = %s
            """
            cursor.execute(delete_sql, (file_path,))
            connection.commit()
            logger.info(f"已从数据库中删除文件记录: {file_path}")
    except Exception as e:
        logger.error(f"从数据库中删除文件记录失败: {e}")
        raise

# 检查并删除已不存在的文件
def check_deleted_files(connection, scanned_file_paths):
    try:
        # 获取数据库中所有文件记录
        db_files = get_all_files_in_db(connection)
        deleted_count = 0
        
        # 遍历数据库中的文件记录
        for db_file in db_files:
            file_path = db_file['file_path']
            document_id = db_file['dify_document_id']
            knowledge_base_id = db_file['knowledge_base_id']
            
            # 检查文件是否存在于扫描结果中
            if file_path not in scanned_file_paths:
                logger.info(f"检测到已删除的文件: {file_path}")
                
                # 调用update_dify.py的删除函数删除知识库中的文件
                delete_result = ud.delete_file(knowledge_base_id, document_id)
                if delete_result['success']:
                    logger.info(f"成功从知识库中删除文件: {file_path}")
                    
                    # 从数据库中删除文件记录
                    delete_file_from_db(connection, file_path)
                    deleted_count += 1
                else:
                    logger.error(f"从知识库中删除文件失败: {file_path} - {delete_result.get('error', '未知错误')}")
        
        return deleted_count
    except Exception as e:
        logger.error(f"检查已删除文件时出错: {e}")
        raise

# 更新数据库中的文档ID
def update_document_id(connection, file_path, new_document_id):
    try:
        with connection.cursor() as cursor:
            sql = """
            UPDATE file_feature_history 
            SET dify_document_id = %s 
            WHERE file_path = %s
            """
            cursor.execute(sql, (new_document_id, file_path))
            connection.commit()
    except Exception as e:
        logger.error(f"更新数据库中的文档ID时出错: {e}")
        connection.rollback()
        raise

# 检查并重新上传状态为error的文档
def check_and_reupload_error_documents(connection, config):
    try:
        # 获取数据库中所有文件记录
        db_files = get_all_files_in_db(connection)
        reupload_count = 0
        error_count = 0
        
        logger.info(f"开始检查 {len(db_files)} 个文档的状态...")
        
        # 遍历数据库中的文件记录
        for db_file in db_files:
            file_path = db_file['file_path']
            document_id = db_file['dify_document_id']
            knowledge_base_id = db_file['knowledge_base_id']
            
            # 获取文档详情
            detail_result = ud.get_file_detail(knowledge_base_id, document_id)
            
            # 检查获取详情是否成功
            if detail_result['success']:
                # 检查文档状态是否为error
                if 'display_status' in detail_result['response'] and detail_result['response']['display_status'] == 'error':
                    logger.info(f"发现状态为error的文档: {file_path}，文档ID: {document_id}")
                    error_count += 1
                    
                    # 检查文件是否仍然存在
                    if os.path.exists(file_path):
                        logger.info(f"准备重新上传文档: {file_path}")
                        
                        # 首先尝试删除原文档
                        delete_result = ud.delete_file(knowledge_base_id, document_id)
                        if delete_result['success']:
                            logger.info(f"成功删除原文档: {file_path}")
                            
                            # 重新上传文档
                            reupload_result = ud.upload_file(knowledge_base_id, file_path)
                            if reupload_result['success']:
                                new_document_id = reupload_result['response']['document']['id']
                                logger.info(f"成功重新上传文档: {file_path}，新文档ID: {new_document_id}")
                                
                                # 从文件路径中提取目录信息
                                # 这里可以考虑从配置中读取基础路径
                                base_path = next(iter(config['scan_config']['scan_paths']), '') if config['scan_config']['scan_paths'] else ''
                                directory = os.path.dirname(file_path).replace(base_path, '')
                                
                                # 更新元数据
                                meta_result = ud.change_meta_data(knowledge_base_id, new_document_id, directory)
                                if meta_result['success']:
                                    logger.info(f"元数据更新成功: {file_path}")
                                else:
                                    logger.warning(f"元数据更新失败: {file_path} - {meta_result.get('error', '未知错误')}")
                                
                                # 更新数据库中的文档ID
                                update_document_id(connection, file_path, new_document_id)
                                reupload_count += 1
                            else:
                                logger.error(f"重新上传文档失败: {file_path} - {reupload_result.get('error', '未知错误')}")
                        else:
                            logger.error(f"删除原文档失败: {file_path} - {delete_result.get('error', '未知错误')}")
                    else:
                        logger.warning(f"文件已不存在，跳过重新上传: {file_path}")
            else:
                logger.error(f"获取文档详情失败: {file_path} - {detail_result.get('error', '未知错误')}")
        
        logger.info(f"文档状态检查完成！发现 {error_count} 个状态为error的文档，成功重新上传 {reupload_count} 个文档")
        return reupload_count
    except Exception as e:
        logger.error(f"检查并重新上传error文档时出错: {e}")
        raise

# 主流程函数
def main():
    global logger
    
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 加载配置
        if args.config:
            config = global_config.load_config(args.config)
        else:
            config = global_config.get_config()
        
        # 应用命令行参数到配置
        apply_args_to_config(config, args)
        
        # 设置日志
        logger = setup_logging(config)
        
        # 连接数据库
        connection = connect_to_database(config)
        
        try:
            # 确保数据表存在
            create_table_if_not_exists(connection)
            
            # 检查哪些文件需要更新
            logger.info("开始扫描所有文件...")
            # 只调用一次scan_directory，获取所有文件信息
            all_files_info = []
            scan_paths = config['scan_config']['scan_paths']
            
            for scan_path in scan_paths:
                logger.info(f"扫描目录: {scan_path}")
                files_in_path = scan_directory(scan_path)
                all_files_info.extend(files_in_path)
                logger.info(f"目录扫描完成，发现 {len(files_in_path)} 个文件")
            
            logger.info(f"所有目录扫描完成，总共发现 {len(all_files_info)} 个文件")
            
            # 收集所有扫描到的文件路径，用于删除检测
            scanned_file_paths = [os.path.abspath(file_info['file_path']) for file_info in all_files_info]
            
            # 调用update_knowledge模块的函数，但传入预扫描的文件信息
            logger.info("开始检查需要更新的文件...")
            files_not_in_db, files_with_changes = uk.check_files_for_update(pre_scanned_files=all_files_info)
            
            # 处理不在数据库中的文件（新文件）
            logger.info(f"开始处理 {len(files_not_in_db)} 个新文件...")
            # 原有处理逻辑保持不变

            for file_info in files_not_in_db:
                logger.info(f"处理新文件: {file_info['file_path']}")
                
                # 获取对应的知识库ID
                dataset_id = file_info['knowledge_base_id']
                
                # 上传文件到知识库
                upload_result = ud.upload_file(dataset_id, file_info['file_path'])
                if upload_result['success']:
                    logger.info(f"文件上传成功: {file_info['file_path']}")
                    
                    # 获取上传后的文档ID
                    document_id = upload_result['response']['document']['id']
                    
                    # 从文件路径中提取目录信息
                    base_path = next(iter(config['scan_config']['scan_paths']), '') if config['scan_config']['scan_paths'] else ''
                    directory = os.path.dirname(file_info['file_path']).replace(base_path, '')
                    
                    # 更新元数据
                    meta_result = ud.change_meta_data(dataset_id, document_id, directory)
                    if meta_result['success']:
                        logger.info(f"元数据更新成功: {file_info['file_path']}")
                    else:
                        logger.warning(f"元数据更新失败: {file_info['file_path']} - {meta_result.get('error', '未知错误')}")
                    
                    # 将文件信息写入数据库
                    insert_file_info(connection, file_info, document_id)
                else:
                    logger.error(f"文件上传失败: {file_info['file_path']} - {upload_result.get('error', '未知错误')}")
            
            # 处理需要更新的文件
            logger.info(f"开始处理 {len(files_with_changes)} 个需要更新的文件...")
            for file_info in files_with_changes:
                logger.info(f"处理更新文件: {file_info['file_path']}")
                
                # 获取对应的知识库ID
                dataset_id = file_info['knowledge_base_id']
                
                # 获取数据库中的文档ID
                document_id = get_document_id(connection, file_info['file_path'])
                if not document_id:
                    logger.warning(f"未找到文档ID，跳过更新: {file_info['file_path']}")
                    continue
                
                # 更新文件
                update_result = ud.update_file(dataset_id, document_id, file_info['file_path'])
                if update_result['success']:
                    logger.info(f"文件更新成功: {file_info['file_path']}")
                    
                    # 更新数据库中的文件信息
                    update_file_info(connection, file_info)
                else:
                    logger.error(f"文件更新失败: {file_info['file_path']} - {update_result.get('error', '未知错误')}")
            
            # 检查并删除已不存在的文件
            logger.info("开始检查已删除的文件...")
            deleted_count = check_deleted_files(connection, scanned_file_paths)
            
            # 新增功能：检查并重新上传状态为error的文档
            logger.info("开始检查并重新上传状态为error的文档...")
            reupload_count = check_and_reupload_error_documents(connection, config)
            
            # 输出总结信息
            logger.info(f"自动化更新知识库流程完成！")
            logger.info(f"共处理 {len(files_not_in_db)} 个新文件，{len(files_with_changes)} 个更新文件，删除了 {deleted_count} 个已不存在的文件，重新上传了 {reupload_count} 个状态为error的文档")
            
        finally:
            # 关闭数据库连接
            if connection:
                connection.close()
                logger.info("已关闭数据库连接")
        
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"程序执行出错: {e}")
        else:
            print(f"程序执行出错: {e}")
        raise

if __name__ == "__main__":
    main()