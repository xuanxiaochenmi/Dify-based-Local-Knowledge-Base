import os
import yaml
import argparse

class ConfigManager:
    _instance = None
    _config = None
    _config_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def load_config(self, config_path=None):
        """加载配置文件，如果未指定路径，则使用默认路径"""
        if config_path is None:
            if self._config_path is not None:
                # 已经加载过配置，使用相同的路径
                config_path = self._config_path
            else:
                # 使用默认路径
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
                self._config_path = config_path
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
                self._config_path = config_path
                return self._config
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")
    
    def get_config(self, force_reload=False):
        """获取配置，如果未加载则加载配置"""
        if self._config is None or force_reload:
            self.load_config()
        return self._config
    
    def update_config(self, updates):
        """更新配置"""
        if self._config is None:
            self.load_config()
        
        for key, value in updates.items():
            if isinstance(value, dict) and key in self._config and isinstance(self._config[key], dict):
                # 递归更新嵌套配置
                self._config[key].update(value)
            else:
                # 直接更新配置
                self._config[key] = value

# 创建全局配置管理器实例
global_config = ConfigManager()

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description='知识库更新工具')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--scan-path', help='扫描路径，可以覆盖配置文件中的scan_paths')
    parser.add_argument('--interval', type=int, help='扫描间隔（小时）')
    parser.add_argument('--api-key', help='Dify API密钥')
    parser.add_argument('--base-url', help='Dify接口基础URL')
    parser.add_argument('--mysql-host', help='MySQL服务器地址')
    parser.add_argument('--mysql-port', type=int, help='MySQL端口号')
    parser.add_argument('--mysql-user', help='MySQL用户名')
    parser.add_argument('--mysql-password', help='MySQL密码')
    parser.add_argument('--mysql-database', help='数据库名')
    return parser.parse_args()

# 应用命令行参数到配置
def apply_args_to_config(config, args):
    updates = {}
    
    if args.scan_path:
        updates['scan_config'] = updates.get('scan_config', {})
        updates['scan_config']['scan_paths'] = [args.scan_path]
        
    if args.interval:
        updates['scan_config'] = updates.get('scan_config', {})
        updates['scan_config']['scan_interval'] = args.interval
        
    if args.api_key:
        updates['dify_config'] = updates.get('dify_config', {})
        updates['dify_config']['api_key'] = args.api_key
        
    if args.base_url:
        updates['dify_config'] = updates.get('dify_config', {})
        updates['dify_config']['base_url'] = args.base_url
        
    if args.mysql_host:
        updates['mysql_config'] = updates.get('mysql_config', {})
        updates['mysql_config']['host'] = args.mysql_host
        
    if args.mysql_port:
        updates['mysql_config'] = updates.get('mysql_config', {})
        updates['mysql_config']['port'] = args.mysql_port
        
    if args.mysql_user:
        updates['mysql_config'] = updates.get('mysql_config', {})
        updates['mysql_config']['username'] = args.mysql_user
        
    if args.mysql_password:
        updates['mysql_config'] = updates.get('mysql_config', {})
        updates['mysql_config']['password'] = args.mysql_password
        
    if args.mysql_database:
        updates['mysql_config'] = updates.get('mysql_config', {})
        updates['mysql_config']['database'] = args.mysql_database
        
    if updates:
        global_config.update_config(updates)
        return True
    return False