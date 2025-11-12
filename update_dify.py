import requests
import json
import yaml
import update_knowledge as uk
import os
import logging
from logging.handlers import RotatingFileHandler
# 导入新的配置管理模块
from config_manager import global_config

# 初始化日志系统
logger = None

# 设置日志系统
def setup_logging(config=None):
    global logger
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
    
    log_file = os.path.join(log_dir, 'update_dify.log')
    
    # 配置日志记录器
    logger = logging.getLogger('update_dify')
    
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
            mode='a',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 初始化配置和日志
config = global_config.get_config()
logger = setup_logging(config)

# 同时修改upload_file函数中的错误处理部分
def upload_file(dataset_id, file_path):
    """上传文件到知识库"""
    config = get_config()
    dify_config = config['dify_config']
    
    # API地址
    url = f"{dify_config['base_url']}/datasets/{dataset_id}/document/create-by-file"

    # 正确的文件打开方式（不要加引号，需要实际打开文件）
    files = {
        "file": open(file_path, 'rb')  # 直接打开文件对象，不要用字符串
    }

    # payload数据不需要外层的"data"键，直接传递JSON结构
    payload = {
        "indexing_technique": "high_quality",
        "process_rule": {
            "mode": "custom",
            "rules": {
            "segmentation": {
                "max_tokens": 500
                }
            }
        }
    }

    # 请求头
    headers = {
        "Authorization": f"Bearer {dify_config['api_key']}"
        # 注意：不要手动指定Content-Type，让requests自动处理
    }

    try:
        # 发送请求
        response = requests.post(url, data=payload, files=files, headers=headers)
        response.raise_for_status()
        return {
            'success': True,
            'response': response.json() if response.content else None
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"上传文件错误 {file_path}: {e}")
        return {
            'success': False,
            'error': str(e),
            'document_id': None
        }

    finally:
        # 确保文件被关闭
        files["file"].close()


def change_meta_data(dataset_id, document_id, directory):
    """更新知识库中的文档元数据"""
    config = get_config()
    dify_config = config['dify_config']
    
    url = f"{dify_config['base_url']}/datasets/{dataset_id}/documents/metadata"

    # 请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {dify_config['api_key']}"
    }

    # 请求数据（与curl中的data一致）
    payload = {
        "operation_data": [
            {
                "document_id": document_id,  # 目标文档ID
                    "metadata_list": [
                        {
                        "id": "a5f5a765-7025-4f28-a3f5-680fc3ddc0cc",
                        "name": "directory",
                        "value": directory,
                        "type": "string"
                        }
                    ]
            }
        ]
    }

    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return {
            'success': True,
            'response': response.json() if response.content else None
        }
    except requests.exceptions.RequestException as e:
        print(f"Error changing document metadata: {e}")
        return {
            'success': False,
            'error': str(e),
            'document_id': document_id
        }
        

def delete_file(dataset_id, document_id):
    """删除知识库中的指定文档"""
    config = get_config()
    dify_config = config['dify_config']
    
    url = f"{dify_config['base_url']}/datasets/{dataset_id}/documents/{document_id}"
    headers = {'Authorization': f'Bearer {dify_config['api_key']}'}
 
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        response.raise_for_status()
        return {
            'success': True,
            'response': response.json() if response.content else None
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"删除文档错误 {document_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'document_id': document_id
        }


def update_file(dataset_id, document_id, file_path):
    """使用文件更新知识库中的指定文档"""
    config = get_config()
    dify_config = config['dify_config']
    
    url = f"{dify_config['base_url']}/datasets/{dataset_id}/documents/{document_id}/update-by-file"

    files = { "file": open(file_path, 'rb') }
    #payload 需要改成字典格式 
    payload =  { 
                "name": os.path.basename(file_path), 
                "process_rule": 
                    { "mode": "automatic" 
                     } 
                }
    
    headers = {"Authorization": f"Bearer {dify_config['api_key']}"}

    try:
        
        response = requests.post(url, data=payload, files=files, headers=headers)
        response.raise_for_status()
        return {
            'success': True,
            'response': response.json() if response.content else None
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"更新文档错误 {document_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'document_id': document_id
        }


def get_file_detail(dataset_id, document_id):
    """获取知识库中的指定文档详情"""
    config = get_config()
    dify_config = config['dify_config']
    
    url = f"{dify_config['base_url']}/datasets/{dataset_id}/documents/{document_id}"
    headers = {'Authorization': f'Bearer {dify_config['api_key']}'}
 
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return {
            'success': True,
            'response': response.json() if response.content else None
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"获取文档详情错误 {document_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'document_id': document_id
        }

if __name__ == "__main__":
    # 确保配置已加载
    config = get_config()

    # 加载 config.yaml 文件，程序结束后关闭文件流
    with open('/home/root01/AI_knowledge_base/config.yaml', 'r') as file:
        config = yaml.safe_load(file)
        
        
    scan_config = config['scan_config']
    scan_paths = scan_config['scan_paths']
    dify_config = config['dify_config']
    api_key = dify_config['api_key']
    dataset_id = dify_config['knowledge_base_mapping'][scan_paths[0]]