from flask import (
    Blueprint, current_app, request, jsonify
)
from flaskr.db import get_db
import mysql.connector

bp = Blueprint('biodata', __name__, url_prefix='/biodata')


@bp.route('/search', methods=('GET', 'POST'))
def search():
    id = request.args.get('query', type=str)
    if id is None:
        return jsonify({"error": "No 'id' provided in the parameters."}), 400

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # 添加日志
        current_app.logger.info(f"Searching for ID: {id}")

        query = "SELECT * FROM snp_1240k WHERE snp_id = %s"
        cursor.execute(query, (id,))
        result = cursor.fetchone()

        # 添加日志
        current_app.logger.info(f"Query result: {result}")

        if result:
            return jsonify(result), 200
        else:
            return jsonify({"message": "No data found with the given ID."}), 404

    except mysql.connector.Error as err:
        current_app.logger.error(f"Database error: {err}")
        return jsonify({"error": "Database error: " + str(err)}), 500
    finally:
        cursor.close()


@bp.route('/test', methods=('GET', 'POST'))
def test_db():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as count FROM snp_1240k")
        result = cursor.fetchone()
        return jsonify({"count": result['count']})
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        cursor.close()
