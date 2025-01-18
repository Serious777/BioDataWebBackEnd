from flask import Flask, request, send_file, jsonify, url_for, current_app
from .tasks import process_pca, process_admixture, process_f3, process_f4, process_qpwave, process_qpadm
from .celery_config import celery
import os
import uuid
import shutil
from flask import Blueprint
import logging
from .upload_manager import UploadManager

logger = logging.getLogger('flaskr.tools')
bp = Blueprint('tools', __name__, url_prefix='/tools')

# 设置脚本和工作目录路径
PCA_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                              "smartpca_tools", "smartpca.v2.6.sh")
PCA_WORK_DIR = "/root/data-upload/smartpca/"

TEMP_WORK_DIR = "/root/data-upload/temp/"

ADMIXTURE_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                    "admixture_v2.6", "admixture.v2.6.sh")
ADMIXTURE_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "admixture_v2.6")
ADMIXTURE_WORK_DIR = "/root/data-upload/admixture/"

F3_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                             "f3_tools_v1.0", "f3_v1.0.sh")
F3_WORK_DIR = "/root/data-upload/f3/"

# 添加F4相关路径配置
F4_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                             "f4_tools_v1.4", "f4_v1.4.sh")
F4_WORK_DIR = "/root/data-upload/f4/"

# 添加qpWave相关路径配置
QPWAVE_WORK_DIR = "/root/data-upload/qpwave/"
QPWAVE_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                 "qpWave_tools_v1.0", "qpwave.sh")

# 添加qpAdm相关路径配置
QPADM_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "qpAdm_tools_v0.5", "qpAdm.sh")
QPADM_WORK_DIR = "/root/data-upload/qpadm/"

# 创建必要的目录
os.makedirs(TEMP_WORK_DIR, exist_ok=True)
os.makedirs(PCA_WORK_DIR, exist_ok=True)
os.makedirs(ADMIXTURE_WORK_DIR, exist_ok=True)
os.makedirs(F3_WORK_DIR, exist_ok=True)
os.makedirs(F4_WORK_DIR, exist_ok=True)
os.makedirs(QPWAVE_WORK_DIR, exist_ok=True)
os.makedirs(QPADM_WORK_DIR, exist_ok=True)

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
        
        # 检查所有可能的工作目录
        pca_work_dir = os.path.join(PCA_WORK_DIR, task_id)
        admixture_work_dir = os.path.join(ADMIXTURE_WORK_DIR, task_id)
        f3_work_dir = os.path.join(F3_WORK_DIR, task_id)
        f4_work_dir = os.path.join(F4_WORK_DIR, task_id)
        qpwave_work_dir = os.path.join(QPWAVE_WORK_DIR, task_id)
        qpadm_work_dir = os.path.join(QPADM_WORK_DIR, task_id)  # 添加 qpAdm 工作目录
        
        # 检查对应的结果文件
        pca_result = os.path.join(pca_work_dir, "smartpca.zip")
        admixture_result = os.path.join(admixture_work_dir, "admixture.zip")
        f3_result = os.path.join(f3_work_dir, "f3.zip")
        f4_result = os.path.join(f4_work_dir, "f4.zip")
        qpwave_result = os.path.join(qpwave_work_dir, "qpwave.zip")
        qpadm_result = os.path.join(qpadm_work_dir, "qpadm.zip")  # 添加 qpAdm 结果文件
        
        # 获取任务状态
        task_pca = process_pca.AsyncResult(task_id)
        task_admixture = process_admixture.AsyncResult(task_id)
        task_f3 = process_f3.AsyncResult(task_id)
        task_f4 = process_f4.AsyncResult(task_id)
        task_qpwave = process_qpwave.AsyncResult(task_id)
        task_qpadm = process_qpadm.AsyncResult(task_id)  # 添加 qpAdm 任务状态
        
        # 根据任务状态和结果文件确定任务类型
        if task_pca.state == 'SUCCESS' and os.path.exists(pca_result):
            zip_file_path = pca_result
            result_prefix = "smartpca"
            logger.info(f"Found successful PCA task, checking file: {zip_file_path}")
        elif task_admixture.state == 'SUCCESS' and os.path.exists(admixture_result):
            zip_file_path = admixture_result
            result_prefix = "admixture"
            logger.info(f"Found successful admixture task, checking file: {zip_file_path}")
        elif task_f3.state == 'SUCCESS' and os.path.exists(f3_result):
            zip_file_path = f3_result
            result_prefix = "f3"
            logger.info(f"Found successful F3 task, checking file: {zip_file_path}")
        elif task_f4.state == 'SUCCESS' and os.path.exists(f4_result):
            zip_file_path = f4_result
            result_prefix = "f4"
            logger.info(f"Found successful F4 task, checking file: {zip_file_path}")
        elif task_qpwave.state == 'SUCCESS' and os.path.exists(qpwave_result):
            zip_file_path = qpwave_result
            result_prefix = "qpwave"
            logger.info(f"Found successful qpWave task, checking file: {zip_file_path}")
        elif task_qpadm.state == 'SUCCESS' and os.path.exists(qpadm_result):  # 添加 qpAdm 检查
            zip_file_path = qpadm_result
            result_prefix = "qpadm"
            logger.info(f"Found successful qpAdm task, checking file: {zip_file_path}")
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
        
        # 复制并重命名文件，同时设置正确的权限
        for file_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, file_name)
            if file_name.endswith('.txt'):
                dst_name = 'poplist.txt'
            else:
                dst_name = 'example' + os.path.splitext(file_name)[1]
            dst_path = os.path.join(work_dir, dst_name)
            shutil.copy2(src_path, dst_path)
            # 添加执行权限
            os.chmod(dst_path, 0o755)  # rwxr-xr-x
        
        # 复制必需的R脚本并设置权限
        script_dir = os.path.dirname(ADMIXTURE_SCRIPT_PATH)
        r_scripts = ['fancyADMIXTURE.r', 'makePalette.r', 'averagePopsUnsorted.r', 'averagePops.r', 'remove_excess.py']
        for script in r_scripts:
            src = os.path.join(script_dir, script)
            dst = os.path.join(work_dir, script)
            shutil.copy2(src, dst)
            # 添加执行权限
            os.chmod(dst, 0o755)  # rwxr-xr-x

            # 如果是R脚本，确保它有正确的文件头
            if script.endswith('.r'):
                with open(dst, 'r') as f:
                    content = f.read()
                if not content.startswith('#!/usr/bin/env Rscript'):
                    with open(dst, 'w') as f:
                        f.write('#!/usr/bin/env Rscript\n\n' + content)
        
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
        
        if not file_id or not total_chunks:
            return jsonify({"error": "Missing required parameters"}), 400
            
        # 清理分片文件
        chunk_dir = os.path.join(TEMP_WORK_DIR, file_id)
        if os.path.exists(chunk_dir):
            shutil.rmtree(chunk_dir)
          
        # 如果有 task_id，清理整个工作目录
        if task_id:
            # 检查并清理所有可能的工作目录
            # PCA工作目录
            pca_dir = os.path.join(PCA_WORK_DIR, task_id)
            if os.path.exists(pca_dir):
                shutil.rmtree(pca_dir)
                
            # ADMIXTURE工作目录
            admixture_dir = os.path.join(ADMIXTURE_WORK_DIR, task_id)
            if os.path.exists(admixture_dir):
                shutil.rmtree(admixture_dir)
                
            # F3工作目录
            f3_dir = os.path.join(F3_WORK_DIR, task_id)
            if os.path.exists(f3_dir):
                shutil.rmtree(f3_dir)
                
            # 检查并清理 F4 工作目录
            f4_dir = os.path.join(F4_WORK_DIR, task_id)
            if os.path.exists(f4_dir):
                shutil.rmtree(f4_dir)
                  
        logger.info(f"Successfully canceled upload for file_id={file_id}, task_id={task_id}")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error canceling upload: {str(e)}")
        # 返回详细的错误信息
        return jsonify({
            "error": str(e),
            "details": {
                "file_id": file_id,
                "task_id": task_id,
                "total_chunks": total_chunks,
                "temp_dir": TEMP_WORK_DIR,
                "work_dirs": {
                    "pca": PCA_WORK_DIR,
                    "admixture": ADMIXTURE_WORK_DIR,
                    "f3": F3_WORK_DIR,
                    "f4": F4_WORK_DIR
                }
            }
        }), 500

@bp.route("/f3", methods=['POST'])
def f3Analysis():
    try:
        data = request.get_json()
        upload_id = data.get('uploadId')
        
        # 生成新的task_id
        task_id = str(uuid.uuid4())
        
        # 源目录和目标目录
        temp_dir = os.path.join(TEMP_WORK_DIR, upload_id)
        work_dir = os.path.join(F3_WORK_DIR, task_id)
        
        # 创建工作目录并复制文件
        os.makedirs(work_dir)
        
        # 检查必需的txt文件是否存在
        required_txt_files = {'p1s': False, 'p2s': False, 'target': False}
        for file_name in os.listdir(temp_dir):
            if file_name.endswith('.txt'):
                if 'p1s' in file_name.lower():
                    required_txt_files['p1s'] = True
                elif 'p2s' in file_name.lower():
                    required_txt_files['p2s'] = True
                elif 'target' in file_name.lower():
                    required_txt_files['target'] = True
        
        # 检查是否所有必需的txt文件都存在
        missing_files = [k for k, v in required_txt_files.items() if not v]
        if missing_files:
            raise ValueError(f"Missing required txt files: {', '.join(f'{f}.txt' for f in missing_files)}")
        
        # 复制并重命名文件
        for file_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, file_name)
            if file_name.endswith('.txt'):
                # 根据文件名确定目标名称
                if 'p1s' in file_name.lower():
                    dst_name = 'p1s.txt'
                elif 'p2s' in file_name.lower():
                    dst_name = 'p2s.txt'
                elif 'target' in file_name.lower():
                    dst_name = 'target.txt'
                else:
                    continue  # 跳过其他txt文件
            else:
                # 对于.geno/.ind/.snp文件，使用example作为前缀
                dst_name = 'example' + os.path.splitext(file_name)[1]
            dst_path = os.path.join(work_dir, dst_name)
            shutil.copy2(src_path, dst_path)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        # 启动异步任务
        task = process_f3.apply_async(
            args=[work_dir, F3_SCRIPT_PATH],
            task_id=task_id
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'PENDING',
            'status_url': url_for('tools.task_status', task_id=task.id)
        })

    except Exception as e:
        logger.error(f"Error in f3Analysis: {str(e)}", exc_info=True)
        if 'work_dir' in locals() and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        return jsonify({"error": str(e)}), 500

@bp.route("/f4", methods=['POST'])
def f4Analysis():
    try:
        data = request.get_json()
        upload_id = data.get('uploadId')
        
        # 生成新的task_id
        task_id = str(uuid.uuid4())
        
        # 源目录和目标目录
        temp_dir = os.path.join(TEMP_WORK_DIR, upload_id)
        work_dir = os.path.join(F4_WORK_DIR, task_id)
        
        # 创建工作目录并复制文件
        os.makedirs(work_dir)
        
        # 检查必需的txt文件是否存在
        required_txt_files = {'p1s': False, 'p2s': False, 'p3s': False, 'p4s': False}
        for file_name in os.listdir(temp_dir):
            if file_name.endswith('.txt'):
                if 'p1s' in file_name.lower():
                    required_txt_files['p1s'] = True
                elif 'p2s' in file_name.lower():
                    required_txt_files['p2s'] = True
                elif 'p3s' in file_name.lower():
                    required_txt_files['p3s'] = True
                elif 'p4s' in file_name.lower():
                    required_txt_files['p4s'] = True
        
        # 检查是否所有必需的txt文件都存在
        missing_files = [k for k, v in required_txt_files.items() if not v]
        if missing_files:
            raise ValueError(f"Missing required txt files: {', '.join(f'{f}.txt' for f in missing_files)}")
        
        # 复制并重命名文件
        for file_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, file_name)
            if file_name.endswith('.txt'):
                # 根据文件名确定目标名称
                if 'p1s' in file_name.lower():
                    dst_name = 'p1s.txt'
                elif 'p2s' in file_name.lower():
                    dst_name = 'p2s.txt'
                elif 'p3s' in file_name.lower():
                    dst_name = 'p3s.txt'
                elif 'p4s' in file_name.lower():
                    dst_name = 'p4s.txt'
                else:
                    continue  # 跳过其他txt文件
            else:
                # 对于.geno/.ind/.snp文件，使用example作为前缀
                dst_name = 'example' + os.path.splitext(file_name)[1]
            dst_path = os.path.join(work_dir, dst_name)
            shutil.copy2(src_path, dst_path)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        # 启动异步任务
        task = process_f4.apply_async(
            args=[work_dir, F4_SCRIPT_PATH],
            task_id=task_id
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'PENDING',
            'status_url': url_for('tools.task_status', task_id=task.id)
        })

    except Exception as e:
        logger.error(f"Error in f4Analysis: {str(e)}", exc_info=True)
        if 'work_dir' in locals() and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        return jsonify({"error": str(e)}), 500

@bp.route("/qpwave", methods=['POST'])
def qpWaveAnalysis():
    try:
        data = request.get_json()
        upload_id = data.get('uploadId')
        
        # 生成新的task_id
        task_id = str(uuid.uuid4())
        
        # 源目录和目标目录
        temp_dir = os.path.join(TEMP_WORK_DIR, upload_id)
        work_dir = os.path.join(QPWAVE_WORK_DIR, task_id)
        
        # 创建工作目录并复制文件
        os.makedirs(work_dir)
        
        # 检查必需的txt文件是否存在
        required_txt_files = {'leftPops': False, 'rightPops': False}
        for file_name in os.listdir(temp_dir):
            if file_name.endswith('.txt'):
                if 'leftpops' in file_name.lower():
                    required_txt_files['leftPops'] = True
                elif 'rightpops' in file_name.lower():
                    required_txt_files['rightPops'] = True
        
        # 检查是否所有必需的txt文件都存在
        missing_files = [k for k, v in required_txt_files.items() if not v]
        if missing_files:
            raise ValueError(f"Missing required files: {', '.join(f'{f}.txt' for f in missing_files)}")
        
        # 复制并重命名文件
        for file_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, file_name)
            if file_name.endswith('.txt'):
                # 根据文件名确定目标名称
                if 'leftpops' in file_name.lower():
                    dst_name = 'leftPops.txt'
                elif 'rightpops' in file_name.lower():
                    dst_name = 'rightPops.txt'
                else:
                    continue
            else:
                dst_name = 'example' + os.path.splitext(file_name)[1]
            dst_path = os.path.join(work_dir, dst_name)
            shutil.copy2(src_path, dst_path)
            # 添加执行权限
            os.chmod(dst_path, 0o755)  # rwxr-xr-x
        
        # 复制必需的脚本并设置权限
        script_dir = os.path.dirname(QPWAVE_SCRIPT_PATH)
        required_scripts = ['gen_scripts.py', 'pairwise_qpWave.v1.r', 'parqpWave.template']
        for script in required_scripts:
            src = os.path.join(script_dir, script)
            dst = os.path.join(work_dir, script)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        # 启动异步任务
        task = process_qpwave.apply_async(
            args=[work_dir, QPWAVE_SCRIPT_PATH],
            task_id=task_id
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'PENDING',
            'status_url': url_for('tools.task_status', task_id=task.id)
        })

    except Exception as e:
        logger.error(f"Error in qpWaveAnalysis: {str(e)}", exc_info=True)
        if 'work_dir' in locals() and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        return jsonify({"error": str(e)}), 500

@bp.route("/qpadm", methods=['POST'])
def qpAdmAnalysis():
    try:
        data = request.get_json()
        upload_id = data.get('uploadId')
        
        # 生成新的task_id
        task_id = str(uuid.uuid4())
        
        # 检查qpAdm脚本和相关文件是否存在
        required_scripts = [
            QPADM_SCRIPT_PATH,
            os.path.join(os.path.dirname(QPADM_SCRIPT_PATH), "qpadm_local.py"),
            os.path.join(os.path.dirname(QPADM_SCRIPT_PATH), "3.grep_result.sh"),
            os.path.join(os.path.dirname(QPADM_SCRIPT_PATH), "5.result2excel.py"),
            os.path.join(os.path.dirname(QPADM_SCRIPT_PATH), "6.excel2r.py"),
            os.path.join(os.path.dirname(QPADM_SCRIPT_PATH), "7.barplot.r")
        ]
        
        for script in required_scripts:
            if not os.path.isfile(script):
                raise FileNotFoundError(f"Required script not found: {os.path.basename(script)}")
            # 检查执行权限
            if not os.access(script, os.X_OK):
                os.chmod(script, 0o755)
        
        # 源目录和目标目录
        temp_dir = os.path.join(TEMP_WORK_DIR, upload_id)
        work_dir = os.path.join(QPADM_WORK_DIR, task_id)
        
        # 创建工作目录并复制文件
        os.makedirs(work_dir)
        
        # 检查必需的txt文件是否存在
        required_txt_files = {'target': False, 'source': False, 'outgroup': False}
        for file_name in os.listdir(temp_dir):
            if file_name.endswith('.txt'):
                if 'target' in file_name.lower():
                    required_txt_files['target'] = True
                elif 'source' in file_name.lower():
                    required_txt_files['source'] = True
                elif 'outgroup' in file_name.lower():
                    required_txt_files['outgroup'] = True
        
        # 检查是否所有必需的txt文件都存在
        missing_files = [k for k, v in required_txt_files.items() if not v]
        if missing_files:
            raise ValueError(f"Missing required files: {', '.join(f'{f}.txt' for f in missing_files)}")
        
        # 复制并重命名文件
        for file_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, file_name)
            if file_name.endswith('.txt'):
                # 根据文件名确定目标名称
                if 'target' in file_name.lower():
                    dst_name = 'target.txt'
                elif 'source' in file_name.lower():
                    dst_name = 'source.txt'
                elif 'outgroup' in file_name.lower():
                    dst_name = 'outgroup.txt'
                else:
                    continue
            else:
                # 检查是否是eigenstat文件
                if not any(file_name.endswith(ext) for ext in ['.geno', '.ind', '.snp']):
                    continue
                dst_name = 'example' + os.path.splitext(file_name)[1]
            dst_path = os.path.join(work_dir, dst_name)
            shutil.copy2(src_path, dst_path)
            # 添加执行权限
            os.chmod(dst_path, 0o755)
        
        # 检查是否有所有必需的eigenstat文件
        eigenstat_files = [f for f in os.listdir(work_dir) if f.startswith('example')]
        if not all(any(f.endswith(ext) for f in eigenstat_files) for ext in ['.geno', '.ind', '.snp']):
            raise ValueError("Missing required eigenstat files (.geno, .ind, .snp)")
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        # 启动异步任务
        task = process_qpadm.apply_async(
            args=[work_dir, QPADM_SCRIPT_PATH],
            task_id=task_id
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'PENDING',
            'status_url': url_for('tools.task_status', task_id=task.id)
        })

    except Exception as e:
        logger.error(f"Error in qpAdmAnalysis: {str(e)}", exc_info=True)
        if 'work_dir' in locals() and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        return jsonify({"error": str(e)}), 500


