import os
from dotenv import load_dotenv
import pyodbc
from flask import Flask, request, jsonify
import socket
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

app = Flask(__name__)

def get_db_connection():

    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    
    try:
    
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'Connection Timeout=30;'
        )
        conn = pyodbc.connect(conn_str)
        return conn
    except pyodbc.Error as e:
        app.logger.error(f"Error de conexión SQL: {str(e)}")
        raise
    except socket.error as e:
        app.logger.error(f"Error de red (posible problema con Cloud VPN): {str(e)}")
        raise


def scheduled_task():
    print("La tarea programada se está ejecutando.")
    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM AlarmSet") 
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            print(f"Datos obtenidos: {results}")
    except Exception as e:
        print(f"Error al ejecutar la tarea programada: {e}")


scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, 'interval', seconds=10)
scheduler.start()

@app.route('/', methods=['POST'])
def main():
    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM AlarmSet") 
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
        return jsonify({
            "status": "success",
            "data": results
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error",
            "message": "Error al ejecutar la consulta"
        }), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
