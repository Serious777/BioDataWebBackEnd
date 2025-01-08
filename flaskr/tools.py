from flask import Flask, request, send_file, jsonify
import os
import subprocess
import shutil
import uuid
from flask import (
    Blueprint, current_app, request, jsonify
)
bp = Blueprint('tools', __name__, url_prefix='/tools')
PCA_SCRIPT_PATH = "/root/my-project/web-database-backend/backend/flaskr/smartpca_tools/smartpca.v2.6.sh"

PCA_WORK_DIR = "/root/data-upload/smartpca/"
os.makedirs(PCA_WORK_DIR, exist_ok=True)


@bp.route("/pca", methods=['POST'])
def pcaAnalysis():
    try:
        request_size = request.content_length
        print(f"请求体大小: {request_size if request_size is not None else '未知'} bytes")

        if 'files' not in request.files:
            print("请求中没有文件字段")
            return jsonify({"error": "No file field in request"}), 400

        files = request.files.getlist('files')
        if not files:
            print("没有文件被上传")
            return jsonify({"error": "No files uploaded"}), 400

        # 检查必需的文件类型
        required_extensions = {'.geno', '.ind', '.snp', '.txt'}
        uploaded_extensions = {os.path.splitext(f.filename)[1].lower() for f in files}
        missing_extensions = required_extensions - uploaded_extensions

        if missing_extensions:
            print(f"缺少必需的文件类型: {missing_extensions}")
            return jsonify({
                "error": f"Missing required file types: {', '.join(missing_extensions)}"
            }), 400

        print("上传的文件:")
        for file in files:
            if not file.filename:
                continue

            print(f"文件名: {file.filename}")
            print(f"文件类型: {file.content_type}")

            file_extension = os.path.splitext(file.filename)[1].lower()

            # 根据后缀名重命名文件
            if file_extension == '.txt':
                new_filename = 'pop-list.txt'
            elif file_extension in ['.geno', '.snp', '.ind']:
                new_filename = 'example' + file_extension
            else:
                print(f"跳过不支持的文件类型: {file_extension}")
                continue

            # 确保目标目录存在
            os.makedirs(PCA_WORK_DIR, exist_ok=True)

            try:
                file_path = os.path.join(PCA_WORK_DIR, new_filename)
                file.save(file_path)
                print(f'成功保存文件: {new_filename}', flush=True)

                # 验证文件是否成功保存
                if not os.path.exists(file_path):
                    raise Exception("File was not saved successfully")

            except Exception as e:
                print(f'保存文件 {new_filename} 时出错: {str(e)}')
                return jsonify({
                    "error": f"Error saving file {new_filename}: {str(e)}"
                }), 500
                # 执行脚本
        script_command = f"bash {PCA_SCRIPT_PATH}"
        result = subprocess.run(script_command, shell=True, capture_output=True, text=True)

        # 检查脚本是否执行成功
        if result.returncode != 0:
            return jsonify({"error": "Script execution failed", "details": result.stderr}), 500

        # 检查生成的 smartpca.zip 文件是否存在
        zip_file_path = os.path.join(PCA_WORK_DIR, "smartpca.zip")
        if not os.path.exists(zip_file_path):
            return jsonify({"error": "smartpca.zip not found"}), 404

        # 返回生成的 zip 文件
        return send_file(zip_file_path, as_attachment=True)


    except Exception as e:
        print(f"处理上传请求时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500


