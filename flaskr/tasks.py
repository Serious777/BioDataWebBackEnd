from .celery_config import celery
import os
import subprocess
import logging
from flask import current_app

logger = logging.getLogger('flaskr.tasks')

@celery.task(bind=True)
def process_pca(self, work_dir, script_path):
    try:
        logger.info(f"Task {self.request.id} started")
        self.update_state(state='STARTED', meta={'progress': 0})
        
        # 检查脚本文件
        if not os.path.isfile(script_path):
            error_msg = f"Script not found at: {script_path}"
            logger.error(error_msg)
            self.update_state(state='FAILURE', meta={'error': error_msg})
            raise FileNotFoundError(error_msg)
            
        # 检查工作目录
        if not os.path.isdir(work_dir):
            error_msg = f"Work directory not found: {work_dir}"
            logger.error(error_msg)
            self.update_state(state='FAILURE', meta={'error': error_msg})
            raise NotADirectoryError(error_msg)
            
        # 检查输入文件
        required_files = ['example.geno', 'example.ind', 'example.snp', 'pop-list.txt']
        for file in required_files:
            file_path = os.path.join(work_dir, file)
            if not os.path.isfile(file_path):
                error_msg = f"Required file missing: {file}"
                logger.error(error_msg)
                self.update_state(state='FAILURE', meta={'error': error_msg})
                raise FileNotFoundError(error_msg)
            else:
                file_size = os.path.getsize(file_path)
                logger.info(f"Found {file} (size: {file_size} bytes)")
        
        # 执行脚本
        self.update_state(state='PROCESSING', meta={'progress': 30})
        cmd = [script_path, work_dir]
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=work_dir
        )
        
        # 实时获取输出并更新进度
        progress = 30
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(f"Script output: {output.strip()}")
                progress = min(progress + 1, 90)
                self.update_state(state='PROCESSING', meta={'progress': progress})
                
        stdout, stderr = process.communicate()
        if stderr:
            logger.error(f"Script stderr: {stderr}")
            
        if process.returncode != 0:
            error_msg = f"Script failed with return code {process.returncode}"
            logger.error(error_msg)
            self.update_state(state='FAILURE', meta={'error': error_msg})
            raise Exception(error_msg)
            
        # 检查结果文件
        result_file = os.path.join(work_dir, "smartpca.zip")
        if os.path.isfile(result_file):
            file_size = os.path.getsize(result_file)
            logger.info(f"Result file generated successfully (size: {file_size} bytes)")
            self.update_state(state='SUCCESS', meta={'progress': 100})
        else:
            error_msg = "Result file not generated"
            logger.error(error_msg)
            self.update_state(state='FAILURE', meta={'error': error_msg})
            raise FileNotFoundError(error_msg)
            
        return {
            "status": "success",
            "message": "PCA analysis completed successfully",
            "work_dir": work_dir
        }
        
    except Exception as e:
        error_msg = f"Error in process_pca: {str(e)}"
        logger.error(error_msg)
        self.update_state(state='FAILURE', meta={'error': error_msg})
        raise