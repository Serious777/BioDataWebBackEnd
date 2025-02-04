from flask import (
    Blueprint, current_app, request, jsonify
)
from flaskr.db import get_db, Base
from sqlalchemy import Column, String, Integer, Float
import json
import os

bp = Blueprint('biodata', __name__, url_prefix='/biodata')

def read_json_file(file_path):
    """读取JSON文件内容，如果文件不存在则返回空字典"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        current_app.logger.error(f"Error reading JSON file {file_path}: {str(e)}")
    return {}

# 定义数据模型
class AadrSnp(Base):
    __tablename__ = 'aadr_snp'
    
    snp_id = Column(String(50), primary_key=True)
    chrom = Column(Integer)
    distance = Column(Float)
    position = Column(Integer)
    a1 = Column(String(1))  # reference allele
    a2 = Column(String(1))  # alternative allele
    frq = Column(Float)     # frequency
    n_chrobs = Column(Integer)
    distribution = Column(String(255))
    
    def to_dict(self):
        # 读取distribution JSON文件内容
        distribution_data = read_json_file(self.distribution)
        
        return {
            'snp_id': self.snp_id,
            'chrom': self.chrom,
            'distance': self.distance,
            'position': self.position,
            'a1': self.a1,
            'a2': self.a2,
            'frq': self.frq,
            'n_chrobs': self.n_chrobs,
            'distribution': distribution_data  # 返回JSON内容而不是文件路径
        }

@bp.route('/search', methods=('GET', 'POST'))
def search():
    snp_id = request.args.get('query', type=str)
    if snp_id is None:
        return jsonify({"error": "No 'id' provided in the parameters."}), 400

    try:
        db = get_db()
        current_app.logger.info(f"Searching for ID: {snp_id}")

        # 使用SQLAlchemy查询
        result = db.query(AadrSnp).filter(AadrSnp.snp_id == snp_id).first()
        
        # 添加日志
        current_app.logger.info(f"Query result: {result}")

        if result:
            return jsonify(result.to_dict()), 200
        else:
            return jsonify({"message": "No data found with the given ID."}), 404

    except Exception as e:
        current_app.logger.error(f"Database error: {e}")
        return jsonify({"error": "Database error: " + str(e)}), 500
    finally:
        db.remove()

