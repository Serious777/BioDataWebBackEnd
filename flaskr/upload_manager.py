import os
import hashlib
from pathlib import Path
import shutil
import logging
import time

logger = logging.getLogger('flaskr.upload_manager')

class UploadManager:
    def __init__(self, temp_dir="/root/data-upload/temp_data", max_age_hours=24):
        self.temp_dir = temp_dir
        self.max_age_hours = max_age_hours
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
    def get_chunk_path(self, file_id, chunk_number):
        return os.path.join(self.temp_dir, f"{file_id}_{chunk_number}")
        
    def save_chunk(self, file_id, chunk_number, chunk_data):
        """保存文件分片"""
        chunk_path = self.get_chunk_path(file_id, chunk_number)
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
            
    def check_chunk(self, file_id, chunk_number):
        """检查分片是否存在"""
        return os.path.exists(self.get_chunk_path(file_id, chunk_number))
        
    def merge_chunks(self, file_id, total_chunks, target_path, chunk_size, total_size, md5):
        """合并分片并验证MD5"""
        temp_path = os.path.join(self.temp_dir, f"{file_id}_complete")
        
        try:
            with open(temp_path, 'wb') as outfile:
                for i in range(total_chunks):
                    chunk_path = self.get_chunk_path(file_id, i)
                    if not os.path.exists(chunk_path):
                        raise Exception(f"Missing chunk {i}")
                    with open(chunk_path, 'rb') as chunk:
                        shutil.copyfileobj(chunk, outfile)
                        
            # 验证文件大小
            if os.path.getsize(temp_path) != total_size:
                raise Exception("File size mismatch")
                
            # 验证MD5
            if md5:
                calculated_md5 = self.calculate_md5(temp_path)
                if calculated_md5 != md5:
                    raise Exception("MD5 checksum mismatch")
                    
            # 移动到目标位置
            shutil.move(temp_path, target_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error merging chunks: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
            
        finally:
            # 无论成功还是失败都清理分片
            self.clean_chunks(file_id, total_chunks)
            
    def clean_chunks(self, file_id, total_chunks):
        """清理分片文件"""
        try:
            for i in range(total_chunks):
                chunk_path = self.get_chunk_path(file_id, i)
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
            # 清理可能存在的临时完整文件
            temp_complete = os.path.join(self.temp_dir, f"{file_id}_complete")
            if os.path.exists(temp_complete):
                os.remove(temp_complete)
        except Exception as e:
            logger.error(f"Error cleaning chunks for {file_id}: {str(e)}")
            
    def calculate_md5(self, file_path):
        """计算文件MD5"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    def cancel_upload(self, file_id, total_chunks):
        """取消上传，清理分片"""
        self.clean_chunks(file_id, total_chunks) 
        
    def cleanup_old_files(self):
        """清理超过指定时间的临时文件"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.temp_dir):
                filepath = os.path.join(self.temp_dir, filename)
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > (self.max_age_hours * 3600):
                    try:
                        os.remove(filepath)
                        logger.info(f"Removed old temporary file: {filename}")
                    except Exception as e:
                        logger.error(f"Error removing old file {filename}: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup of old files: {e}") 