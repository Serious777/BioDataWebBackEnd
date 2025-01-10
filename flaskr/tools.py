from flask import Flask, request, send_file, jsonify, url_for
from .tasks import process_pca
from .celery_config import celery
import os
import uuid
from flask import Blueprint
import logging

logger = logging.getLogger('flaskr.tools')
bp = Blueprint('tools', __name__, url_prefix='/tools')
PCA_SCRIPT_PATH = "/root/my-project/web-database-backend/backend/flaskr/smartpca_tools/smartpca.v2.6.sh"
PCA_WORK_DIR = "/root/data-upload/smartpca/"
os.makedirs(PCA_WORK_DIR, exist_ok=True)

@bp.route("/pca", methods=['POST'])
def pcaAnalysis():
    try:
        # 生成唯一的任务ID
        task_id = str(uuid.uuid4())
        work_dir = os.path.join(PCA_WORK_DIR, task_id)
        os.makedirs(work_dir, exist_ok=True)
        logger.info(f"Created work directory: {work_dir}")

        if 'files' not in request.files:
            logger.error("No file field in request")
            return jsonify({"error": "No file field in request"}), 400

        files = request.files.getlist('files')
        if not files:
            logger.error("No files uploaded")
            return jsonify({"error": "No files uploaded"}), 400

        # 检查必需的文件类型
        required_extensions = {'.geno', '.ind', '.snp', '.txt'}
        uploaded_extensions = {os.path.splitext(f.filename)[1].lower() for f in files}
        logger.info(f"Uploaded file extensions: {uploaded_extensions}")
        
        missing_extensions = required_extensions - uploaded_extensions
        if missing_extensions:
            logger.error(f"Missing required file extensions: {missing_extensions}")
            return jsonify({
                "error": f"Missing required file types: {', '.join(missing_extensions)}"
            }), 400

        # 保存文件并验证
        uploaded_files = []
        try:
            for file in files:
                if not file.filename:
                    continue

                file_extension = os.path.splitext(file.filename)[1].lower()
                logger.info(f"Processing file: {file.filename}")
                
                # 根据后缀名重命名文件
                if file_extension == '.txt':
                    new_filename = 'pop-list.txt'
                elif file_extension in ['.geno', '.snp', '.ind']:
                    new_filename = 'example' + file_extension
                else:
                    logger.warning(f"Skipping unsupported file: {file.filename}")
                    continue

                file_path = os.path.join(work_dir, new_filename)
                logger.info(f"Saving file to: {file_path}")
                
                try:
                    file.save(file_path)
                    logger.info(f"File saved successfully: {new_filename}")
                except Exception as e:
                    logger.error(f"Error saving file {new_filename}: {str(e)}")
                    raise
                
                # 验证文件是否成功保存
                if not os.path.exists(file_path):
                    error_msg = f"Failed to save file: {new_filename}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                # 验证文件大小
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    error_msg = f"File is empty: {new_filename}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                logger.info(f"Successfully saved {new_filename} (size: {file_size} bytes)")
                uploaded_files.append(new_filename)

            # 验证所有必需文件都已上传
            required_files = {'example.geno', 'example.ind', 'example.snp', 'pop-list.txt'}
            if not required_files.issubset(set(uploaded_files)):
                missing = required_files - set(uploaded_files)
                error_msg = f"Missing required files after upload: {missing}"
                logger.error(error_msg)
                raise Exception(error_msg)

            logger.info("All required files uploaded successfully")
            
            # 确保脚本路径存在
            if not os.path.isfile(PCA_SCRIPT_PATH):
                error_msg = f"PCA script not found at: {PCA_SCRIPT_PATH}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # 确保脚本有执行权限
            try:
                os.chmod(PCA_SCRIPT_PATH, 0o755)
                logger.info("Set execute permission for PCA script")
            except Exception as e:
                logger.error(f"Failed to set script permissions: {str(e)}")
                raise

            # 启动异步任务
            logger.info(f"Starting PCA task with work_dir: {work_dir}")
            try:
                # 使用 delay 或 apply_async 发送任务
                # task = process_pca.delay(work_dir, PCA_SCRIPT_PATH)
                # 或者使用 apply_async:
                task = process_pca.apply_async(args=[work_dir, PCA_SCRIPT_PATH],
                                               task_id=task_id)
                
                logger.info(f"Task enqueued with ID: {task.id}")
                
                return jsonify({
                    'task_id': task.id,
                    'status': 'PENDING',
                    'status_url': url_for('tools.task_status', task_id=task.id)
                })
            except Exception as e:
                logger.error(f"Failed to enqueue task: {str(e)}")
                raise

        except Exception as e:
            # 如果上传过程中出错，清理工作目录
            logger.error(f"Error during file upload: {str(e)}")
            if os.path.exists(work_dir):
                import shutil
                shutil.rmtree(work_dir)
                logger.info(f"Cleaned up work directory: {work_dir}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Error in pcaAnalysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route("/task/<task_id>", methods=['GET'])
def task_status(task_id):
    """获取任务状态的端点"""
    try:
        task = process_pca.AsyncResult(task_id)
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
            # 任务失败
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
        
        # 首先检查任务是否完成
        task = process_pca.AsyncResult(task_id)
        if task.state != 'SUCCESS':
            logger.warning(f"任务 {task_id} 未完成，当前状态: {task.state}")
            return jsonify({"error": "任务尚未完成"}), 404

        # 检查结果文件
        work_dir = os.path.join(PCA_WORK_DIR, task_id)
        zip_file_path = os.path.join(work_dir, "smartpca.zip")
        
        if not os.path.exists(zip_file_path):
            logger.error(f"结果文件不存在: {zip_file_path}")
            return jsonify({"error": "结果文件不存在"}), 404
            
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
                download_name=f"smartpca_result_{task_id}.zip",
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


