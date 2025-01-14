from flask import Flask, request, send_file, jsonify, url_for
from .tasks import process_pca, process_admixture
from .celery_config import celery
import os
import uuid
import shutil
from flask import Blueprint
import logging
from .upload_manager import UploadManager

logger = logging.getLogger('flaskr.tools')
bp = Blueprint('tools', __name__, url_prefix='/tools')
PCA_SCRIPT_PATH = "/root/my-project/web-database-backend/backend/flaskr/smartpca_tools/smartpca.v2.6.sh"
PCA_WORK_DIR = "/root/data-upload/smartpca/"
TEMP_WORK_DIR = "/root/data-upload/temp/"
os.makedirs(TEMP_WORK_DIR, exist_ok=True)
os.makedirs(PCA_WORK_DIR, exist_ok=True)
ADMIXTURE_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                    "admixture_v2.6", "admixture.v2.6.sh")
ADMIXTURE_WORK_DIR = "/root/data-upload/admixture/"
os.makedirs(ADMIXTURE_WORK_DIR, exist_ok=True)

# 初始化上传管理器
upload_manager = UploadManager()

@bp.route("/pca", methods=['POST'])
def pcaAnalysis():
    try:
        data = request.get_json()
        upload_id = data.get('uploadId')
        
        # 生成新的task_id
        task_id = str(uuid.uuid4())
        
        # 源目录和目标目录
        temp_dir = os.path.join(TEMP_WORK_DIR, upload_id)
        work_dir = os.path.join(PCA_WORK_DIR, task_id)
        
        # 创建工作目录并复制文件
        os.makedirs(work_dir)
        
        # 复制并重命名文件
        for file_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, file_name)
            if file_name.endswith('.txt'):
                dst_name = 'pop-list.txt'  # PCA 使用 pop-list.txt
            else:
                dst_name = 'example' + os.path.splitext(file_name)[1]
            dst_path = os.path.join(work_dir, dst_name)
            shutil.copy2(src_path, dst_path)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        # 启动异步任务
        task = process_pca.apply_async(
            args=[work_dir, PCA_SCRIPT_PATH],
            task_id=task_id
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'PENDING',
            'status_url': url_for('tools.task_status', task_id=task.id)
        })

    except Exception as e:
        logger.error(f"Error in pcaAnalysis: {str(e)}", exc_info=True)
        if 'work_dir' in locals() and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        return jsonify({"error": str(e)}), 500

@bp.route("/task/<task_id>", methods=['GET'])
def task_status(task_id):
    """获取任务状态的端点"""
    try:
        # 尝试两种任务类型
        task_pca = process_pca.AsyncResult(task_id)
        task_admixture = process_admixture.AsyncResult(task_id)
        
        # 选择正确的任务
        task = None
        if task_pca.state != 'PENDING' and task_pca.state != 'FAILURE':
            task = task_pca
        elif task_admixture.state != 'PENDING' and task_admixture.state != 'FAILURE':
            task = task_admixture
        
        if task is None:
            return jsonify({
                'state': 'ERROR',
                'status': 'Task not found'
            })
        
        logger.info(f"Checking status for task {task_id}: {task.state}")
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': 'Task is pending...'
            }
        elif task.state == 'STARTED':
            response = {
                'state': task.state,
                'status': 'Task has started...',
                'progress': task.info.get('progress', 0)
            }
        elif task.state == 'PROCESSING':
            response = {
                'state': task.state,
                'status': 'Task is processing...',
                'progress': task.info.get('progress', 0)
            }
        elif task.state == 'SUCCESS':
            response = {
                'state': task.state,
                'status': 'Task completed successfully',
                'result': task.get()
            }
        else:
            response = {
                'state': task.state,
                'status': str(task.info.get('error', 'Unknown error'))
            }
            
        return jsonify(response)
            
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        return jsonify({
            'state': 'ERROR',
            'status': str(e)
        })

@bp.route("/download/<task_id>", methods=['GET'])
def download_result(task_id):
    """下载任务结果的端点"""
    try:
        logger.info(f"开始处理下载请求: task_id={task_id}")
        
        # 检查两个可能的工作目录
        pca_work_dir = os.path.join(PCA_WORK_DIR, task_id)
        admixture_work_dir = os.path.join(ADMIXTURE_WORK_DIR, task_id)
        
        # 检查对应的结果文件
        pca_result = os.path.join(pca_work_dir, "smartpca.zip")
        admixture_result = os.path.join(admixture_work_dir, "admixture.zip")
        
        # 获取任务状态
        task_pca = process_pca.AsyncResult(task_id)
        task_admixture = process_admixture.AsyncResult(task_id)
        
        # 根据任务状态和结果文件确定任务类型
        if task_pca.state == 'SUCCESS' and os.path.exists(pca_result):
            zip_file_path = pca_result
            result_prefix = "smartpca"
            logger.info(f"Found successful PCA task, checking file: {zip_file_path}")
        elif task_admixture.state == 'SUCCESS' and os.path.exists(admixture_result):
            zip_file_path = admixture_result
            result_prefix = "admixture"
            logger.info(f"Found successful admixture task, checking file: {zip_file_path}")
        else:
            logger.warning(f"任务 {task_id} 未完成或不存在")
            return jsonify({"error": "任务尚未完成或不存在"}), 404

            
        # 检查文件大小
        file_size = os.path.getsize(zip_file_path)
        if file_size == 0:
            logger.error(f"结果文件大小为0: {zip_file_path}")
            return jsonify({"error": "结果文件为空"}), 404
            
        logger.info(f"准备发送文件: {zip_file_path} (大小: {file_size} bytes)")
        
        try:
            response = send_file(
                zip_file_path,
                as_attachment=True,
                download_name=f"{result_prefix}_result_{task_id}.zip",
                mimetype='application/zip'
            )
            
            # 添加必要的响应头
            response.headers['Content-Length'] = file_size
            response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
            
            logger.info(f"文件发送成功: task_id={task_id}")
            return response
            
        except Exception as e:
            logger.error(f"发送文件时出错: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"下载处理失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route("/admixture", methods=['POST'])
def admixtureAnalysis():
    try:
        data = request.get_json()
        upload_id = data.get('uploadId')
        
        # 生成新的task_id
        task_id = str(uuid.uuid4())
        
        # 源目录和目标目录
        temp_dir = os.path.join(TEMP_WORK_DIR, upload_id)
        work_dir = os.path.join(ADMIXTURE_WORK_DIR, task_id)
        
        # 创建工作目录并复制文件
        os.makedirs(work_dir)
        
        # 复制并重命名文件
        for file_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, file_name)
            if file_name.endswith('.txt'):
                dst_name = 'poplist.txt'
            else:
                dst_name = 'example' + os.path.splitext(file_name)[1]
            dst_path = os.path.join(work_dir, dst_name)
            shutil.copy2(src_path, dst_path)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        # 启动异步任务
        task = process_admixture.apply_async(
            args=[work_dir, ADMIXTURE_SCRIPT_PATH],
            task_id=task_id
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'PENDING',
            'status_url': url_for('tools.task_status', task_id=task.id)
        })

    except Exception as e:
        logger.error(f"Error in admixtureAnalysis: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/upload/chunk", methods=['POST'])
def upload_chunk():
    try:
        file_id = request.form.get('fileId')
        chunk_number = int(request.form.get('chunkNumber'))
        total_chunks = int(request.form.get('totalChunks'))
        file_name = request.form.get('fileName')
        
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        # 保存分片
        upload_manager.save_chunk(file_id, chunk_number, file.read())
        
        # 检查是否所有分片都已上传
        all_chunks_uploaded = all(
            upload_manager.check_chunk(file_id, i)
            for i in range(total_chunks)
        )
        
        return jsonify({
            "success": True,
            "complete": all_chunks_uploaded
        })
        
    except Exception as e:
        logger.error(f"Error uploading chunk: {str(e)}")
        if file_id:
            # 出错时清理已上传的分片
            try:
                upload_manager.clean_chunks(file_id, int(request.form.get('totalChunks', 0)))
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up chunks: {cleanup_error}")
        return jsonify({"error": str(e)}), 500

@bp.route("/upload/complete", methods=['POST'])
def complete_upload():
    data = request.get_json()
    file_id = data.get('fileId')
    total_chunks = data.get('totalChunks')
    file_name = data.get('fileName')
    total_size = data.get('totalSize')
    md5 = data.get('md5')
    upload_id = data.get('uploadId') or str(uuid.uuid4())
    
    # 在临时目录中创建上传目录
    temp_dir = os.path.join(TEMP_WORK_DIR, upload_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 确定目标文件名
    if file_name.endswith('.txt'):
        target_name = file_name
    else:
        target_name = 'example' + os.path.splitext(file_name)[1]
        
    target_path = os.path.join(temp_dir, target_name)
    
    # 合并分片
    success = upload_manager.merge_chunks(
        file_id, total_chunks, target_path,
        data.get('chunkSize'), total_size, md5
    )
    
    return jsonify({
        "success": True,
        "uploadId": upload_id,
        "filePath": target_path
    })

@bp.route("/upload/cancel", methods=['POST'])
def cancel_upload():
    """取消文件上传"""
    try:
        data = request.get_json()
        file_id = data.get('fileId')
        total_chunks = data.get('totalChunks')
        task_id = data.get('taskId')
        
        # 清理分片文件
        upload_manager.cancel_upload(file_id, total_chunks)
        
        # 如果有 task_id，清理整个工作目录
        if task_id:
            work_dir = os.path.join(ADMIXTURE_WORK_DIR, task_id)
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)
                
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error canceling upload: {str(e)}")
        return jsonify({"error": str(e)}), 500


