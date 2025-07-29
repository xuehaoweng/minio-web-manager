import os
import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from minio import Minio
from minio.error import S3Error
import tempfile
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import uuid

# 加载环境变量
load_dotenv('config.env')

app = Flask(__name__)
CORS(app)

# MinIO 配置
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'http://10.254.0.249:9000')
MINIO_ROOT_USER = os.getenv('MINIO_ROOT_USER', 'admin')
MINIO_ROOT_PASSWORD = os.getenv('MINIO_ROOT_PASSWORD', '12345678')
MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'uploads')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

# 文件上传配置
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 默认100MB
ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', '').split(',') if os.getenv('ALLOWED_EXTENSIONS') else []

# 初始化 MinIO 客户端
try:
    minio_client = Minio(
        MINIO_ENDPOINT.replace('http://', '').replace('https://', ''),
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=MINIO_SECURE
    )
    print(f"MinIO 客户端初始化成功: {MINIO_ENDPOINT}")
except Exception as e:
    print(f"MinIO 客户端初始化失败: {e}")
    minio_client = None

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    if not ALLOWED_EXTENSIONS:
        return True
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_bucket_exists(bucket_name=None):
    """确保bucket存在，如果不存在则创建"""
    if not bucket_name:
        bucket_name = MINIO_BUCKET_NAME
    
    if minio_client:
        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                print(f"创建bucket: {bucket_name}")
        except Exception as e:
            print(f"创建bucket失败: {e}")

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/status')
def system_status():
    """系统状态检查"""
    try:
        # 检查MinIO连接
        if minio_client:
            # 尝试列出bucket来测试连接
            minio_client.list_buckets()
            minio_status = "connected"
        else:
            minio_status = "disconnected"
        
        # 简化的系统信息（不依赖psutil）
        system_info = {
            'minio_status': minio_status,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        return jsonify(system_info)
    except Exception as e:
        return jsonify({
            'minio_status': 'error',
            'error': str(e)
        }), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """上传文件到MinIO"""
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件大小
    file.seek(0, 2)  # 移动到文件末尾
    file_size = file.tell()
    file.seek(0)  # 重置到文件开头
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': f'文件大小超过限制 ({MAX_FILE_SIZE // (1024*1024)}MB)'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        allowed_types = ', '.join(ALLOWED_EXTENSIONS) if ALLOWED_EXTENSIONS else '所有类型'
        return jsonify({'error': f'不支持的文件类型。允许的类型: {allowed_types}'}), 400
    
    # 获取bucket名称，如果没有指定则使用默认bucket
    bucket_name = request.form.get('bucket_name', MINIO_BUCKET_NAME)
    
    if not minio_client:
        return jsonify({'error': 'MinIO客户端未初始化'}), 500
    
    try:
        # 确保bucket存在
        ensure_bucket_exists(bucket_name)
        
        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        
        # 检查是否要保留原始文件名
        keep_original_name = request.form.get('keep_original_name', 'false').lower() == 'true'
        
        if keep_original_name:
            # 保留原始文件名，如果存在同名文件则添加数字后缀
            filename = original_filename
            counter = 1
            while True:
                try:
                    minio_client.stat_object(bucket_name, filename)
                    # 文件存在，需要重命名
                    name, ext = os.path.splitext(original_filename)
                    filename = f"{name}_{counter}{ext}"
                    counter += 1
                except S3Error as e:
                    if e.code == 'NoSuchKey':
                        # 文件不存在，可以使用这个文件名
                        break
                    else:
                        # 其他错误，使用UUID前缀
                        filename = f"{uuid.uuid4()}_{original_filename}"
                        break
        else:
            # 使用UUID前缀避免冲突
            filename = f"{uuid.uuid4()}_{original_filename}"
        
        # 保存文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        # 上传到MinIO
        minio_client.fput_object(
            bucket_name,
            filename,
            temp_file_path,
            content_type=file.content_type
        )
        
        # 删除临时文件
        os.unlink(temp_file_path)
        
        return jsonify({
            'message': '文件上传成功',
            'filename': original_filename,
            'object_name': filename,
            'bucket': bucket_name
        })
        
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/files', methods=['GET'])
def list_files():
    """获取文件列表"""
    if not minio_client:
        return jsonify({'error': 'MinIO客户端未初始化'}), 500
    
    # 获取bucket名称参数
    bucket_name = request.args.get('bucket_name', MINIO_BUCKET_NAME)
    
    try:
        ensure_bucket_exists(bucket_name)
        
        objects = minio_client.list_objects(bucket_name)
        files = []
        
        for obj in objects:
            files.append({
                'name': obj.object_name,
                'size': obj.size,
                'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                'bucket': bucket_name
            })
        
        return jsonify({'files': files, 'bucket': bucket_name})
        
    except Exception as e:
        return jsonify({'error': f'获取文件列表失败: {str(e)}'}), 500

@app.route('/download/<path:object_name>', methods=['GET'])
def download_file(object_name):
    """下载文件"""
    if not minio_client:
        return jsonify({'error': 'MinIO客户端未初始化'}), 500
    
    # 获取bucket名称参数
    bucket_name = request.args.get('bucket_name', MINIO_BUCKET_NAME)
    
    try:
        # 获取文件对象
        obj = minio_client.get_object(bucket_name, object_name)
        
        # 获取文件信息
        stat = minio_client.stat_object(bucket_name, object_name)
        
        return obj.read(), 200, {
            'Content-Type': stat.content_type,
            'Content-Disposition': f'attachment; filename="{object_name}"'
        }
        
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@app.route('/buckets', methods=['GET'])
def list_buckets():
    """获取所有bucket列表"""
    if not minio_client:
        return jsonify({'error': 'MinIO客户端未初始化'}), 500
    
    try:
        buckets = minio_client.list_buckets()
        bucket_list = []
        
        for bucket in buckets:
            bucket_list.append({
                'name': bucket.name,
                'creation_date': bucket.creation_date.isoformat() if bucket.creation_date else None
            })
        
        return jsonify({'buckets': bucket_list})
        
    except Exception as e:
        return jsonify({'error': f'获取bucket列表失败: {str(e)}'}), 500

@app.route('/buckets', methods=['POST'])
def create_bucket():
    """创建新的bucket"""
    if not minio_client:
        return jsonify({'error': 'MinIO客户端未初始化'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据格式错误'}), 400
        
        bucket_name = data.get('bucket_name')
        if not bucket_name or not bucket_name.strip():
            return jsonify({'error': '请提供有效的bucket名称'}), 400
        
        bucket_name = bucket_name.strip()
        
        # 验证bucket名称格式（S3兼容）
        import re
        if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', bucket_name):
            return jsonify({'error': 'Bucket名称必须符合S3命名规范：只能包含小写字母、数字、连字符和点，且不能以连字符或点开头或结尾'}), 400
        
        # 检查bucket是否已存在
        if minio_client.bucket_exists(bucket_name):
            return jsonify({'error': f'Bucket "{bucket_name}" 已存在'}), 400
        
        # 创建新bucket
        minio_client.make_bucket(bucket_name)
        print(f"成功创建bucket: {bucket_name}")
        
        return jsonify({
            'message': f'Bucket "{bucket_name}" 创建成功',
            'bucket_name': bucket_name
        })
        
    except Exception as e:
        print(f"创建bucket时发生错误: {str(e)}")
        return jsonify({'error': f'创建bucket失败: {str(e)}'}), 500

@app.route('/delete/<path:object_name>', methods=['DELETE'])
def delete_file(object_name):
    """删除文件"""
    if not minio_client:
        return jsonify({'error': 'MinIO客户端未初始化'}), 500
    
    # 获取bucket名称参数
    bucket_name = request.args.get('bucket_name', MINIO_BUCKET_NAME)
    
    try:
        minio_client.remove_object(bucket_name, object_name)
        return jsonify({'message': '文件删除成功'})
        
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 