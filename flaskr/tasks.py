from .celery_config import celery
import os
import subprocess
import logging
from flask import current_app
import signal
import psutil
from celery.exceptions import SoftTimeLimitExceeded
from functools import wraps

logger = logging.getLogger('flaskr.tasks')

def kill_child_processes(parent_pid):
    """杀死指定进程及其所有子进程"""
    try:
        parent = psutil.Process(parent_pid)
        children = parent.children(recursive=True)
        
        # 先发送SIGTERM信号
        for process in children:
            process.send_signal(signal.SIGTERM)
            
        # 等待一段时间后强制结束还在运行的进程
        gone, alive = psutil.wait_procs(children, timeout=3)
        for process in alive:
            process.kill()
            
        logger.info(f"Successfully terminated all child processes of {parent_pid}")
    except Exception as e:
        logger.error(f"Error killing child processes: {str(e)}")

def cleanup_on_failure(f):
    """装饰器：在任务失败时清理进程"""
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except SoftTimeLimitExceeded:
            logger.error("Task timed out")
            kill_child_processes(os.getpid())
            self.update_state(state='FAILURE',
                            meta={'error': 'Task timed out',
                                 'exc_type': 'SoftTimeLimitExceeded',
                                 'exc_message': 'Task exceeded time limit'})
            raise
        except Exception as e:
            logger.error(f"Task failed: {str(e)}")
            kill_child_processes(os.getpid())
            raise
    return wrapper

@celery.task(bind=True, 
             soft_time_limit=36000,  # 10小时超时
             time_limit=36060)       # 额外60秒用于清理
@cleanup_on_failure
def process_pca(self, work_dir, script_path):
    try:
        logger.info(f"PCA Task {self.request.id} started")
        self.update_state(state='STARTED', meta={'progress': 0})
        
        # 检查必要文件和目录
        if not os.path.isfile(script_path):
            error_msg = f"Script not found at: {script_path}"
            logger.error(error_msg)
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg,
                                 'exc_type': 'FileNotFoundError',
                                 'exc_message': error_msg})
            raise FileNotFoundError(error_msg)
            
        if not os.path.isdir(work_dir):
            error_msg = f"Work directory not found: {work_dir}"
            logger.error(error_msg)
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg,
                                 'exc_type': 'NotADirectoryError',
                                 'exc_message': error_msg})
            raise NotADirectoryError(error_msg)
            
        # 检查输入文件
        required_files = ['example.geno', 'example.ind', 'example.snp', 'pop-list.txt']
        for file in required_files:
            file_path = os.path.join(work_dir, file)
            if not os.path.isfile(file_path):
                error_msg = f"Required file missing: {file}"
                logger.error(error_msg)
                self.update_state(state='FAILURE', 
                                meta={'error': error_msg,
                                     'exc_type': 'FileNotFoundError',
                                     'exc_message': error_msg})
                raise FileNotFoundError(error_msg)
        
        # 执行脚本
        self.update_state(state='PROCESSING', meta={'progress': 30})
        cmd = [script_path, work_dir]
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=work_dir,
            preexec_fn=os.setsid  # 使用新的进程组
        )
        
        # 实时获取输出
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
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg,
                                 'exc_type': 'RuntimeError',
                                 'exc_message': error_msg})
            raise RuntimeError(error_msg)
            
        # 检查结果文件
        result_file = os.path.join(work_dir, "smartpca.zip")
        if os.path.isfile(result_file):
            file_size = os.path.getsize(result_file)
            logger.info(f"Result file generated successfully (size: {file_size} bytes)")
            
            # 列出工作目录中的所有文件
            logger.info("Files in working directory:")
            for file in os.listdir(work_dir):
                file_path = os.path.join(work_dir, file)
                file_size = os.path.getsize(file_path)
                logger.info(f"  {file}: {file_size} bytes")
                
            self.update_state(state='SUCCESS', meta={'progress': 100})
        else:
            error_msg = f"Result file not generated at {result_file}"
            logger.error(error_msg)
            
            # 列出工作目录中的所有文件，帮助诊断
            logger.error("Files in working directory:")
            for file in os.listdir(work_dir):
                file_path = os.path.join(work_dir, file)
                file_size = os.path.getsize(file_path)
                logger.error(f"  {file}: {file_size} bytes")
                
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg,
                                 'exc_type': 'FileNotFoundError',
                                 'exc_message': error_msg})
            raise FileNotFoundError(error_msg)
            
        return {
            "status": "success",
            "message": "PCA analysis completed successfully",
            "work_dir": work_dir
        }
        
    except Exception as e:
        error_msg = f"Error in process_pca: {str(e)}"
        logger.error(error_msg)
        # 确保在发生错误时清理所有子进程
        if 'process' in locals():
            try:
                kill_child_processes(process.pid)
            except Exception as kill_error:
                logger.error(f"Error killing processes: {str(kill_error)}")
        self.update_state(state='FAILURE',
                         meta={'error': error_msg,
                              'exc_type': type(e).__name__,
                              'exc_message': str(e)})
        raise

@celery.task(bind=True, 
             soft_time_limit=3600,  # 1小时超时
             time_limit=3660)       # 额外60秒用于清理
@cleanup_on_failure
def process_admixture(self, work_dir, script_path):
    try:
        logger.info(f"Admixture Task {self.request.id} started")
        self.update_state(state='STARTED', meta={'progress': 0})
        
        # 检查必要文件和目录
        if not os.path.isfile(script_path):
            error_msg = f"Script not found at: {script_path}"
            logger.error(error_msg)
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg, 
                                 'exc_type': 'FileNotFoundError',
                                 'exc_message': error_msg})
            raise FileNotFoundError(error_msg)
            
        if not os.path.isdir(work_dir):
            error_msg = f"Work directory not found: {work_dir}"
            logger.error(error_msg)
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg,
                                 'exc_type': 'NotADirectoryError',
                                 'exc_message': error_msg})
            raise NotADirectoryError(error_msg)
            
        # 检查输入文件
        required_files = ['example.geno', 'example.ind', 'example.snp', 'poplist.txt']
        for file in required_files:
            file_path = os.path.join(work_dir, file)
            if not os.path.isfile(file_path):
                error_msg = f"Required file missing: {file}"
                logger.error(error_msg)
                self.update_state(state='FAILURE', 
                                meta={'error': error_msg,
                                     'exc_type': 'FileNotFoundError',
                                     'exc_message': error_msg})
                raise FileNotFoundError(error_msg)
        
        # 执行脚本
        self.update_state(state='PROCESSING', meta={'progress': 30})
        cmd = [script_path, work_dir]
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=work_dir,
            preexec_fn=os.setsid  # 使用新的进程组
        )
      
         # 实时获取输出
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
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg,
                                 'exc_type': 'RuntimeError',
                                 'exc_message': error_msg})
            raise RuntimeError(error_msg)       
        
        # 检查结果文件
        result_file = os.path.join(work_dir, "admixture.zip")
        if os.path.isfile(result_file):
            file_size = os.path.getsize(result_file)
            logger.info(f"Result file generated successfully (size: {file_size} bytes)")
            
            # 列出工作目录中的所有文件
            logger.info("Files in working directory:")
            for file in os.listdir(work_dir):
                file_path = os.path.join(work_dir, file)
                file_size = os.path.getsize(file_path)
                logger.info(f"  {file}: {file_size} bytes")
                
            self.update_state(state='SUCCESS', meta={'progress': 100})
        else:
            error_msg = f"Result file not generated at {result_file}"
            logger.error(error_msg)
            
            # 列出工作目录中的所有文件，帮助诊断
            logger.error("Files in working directory:")
            for file in os.listdir(work_dir):
                file_path = os.path.join(work_dir, file)
                file_size = os.path.getsize(file_path)
                logger.error(f"  {file}: {file_size} bytes")
                
            self.update_state(state='FAILURE', 
                            meta={'error': error_msg,
                                 'exc_type': 'FileNotFoundError',
                                 'exc_message': error_msg})
            raise FileNotFoundError(error_msg)
            
        return {
            "status": "success",
            "message": "Admixture analysis completed successfully",
            "work_dir": work_dir
        }
        
    except Exception as e:
        error_msg = f"Error in process_admixture: {str(e)}"
        logger.error(error_msg)
        # 确保在发生错误时清理所有子进程
        if 'process' in locals():
            try:
                kill_child_processes(process.pid)
            except Exception as kill_error:
                logger.error(f"Error killing processes: {str(kill_error)}")
        self.update_state(state='FAILURE',
                         meta={'error': error_msg,
                              'exc_type': type(e).__name__,
                              'exc_message': str(e)})
        raise