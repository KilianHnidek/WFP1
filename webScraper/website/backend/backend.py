from datetime import date
from io import BytesIO
import mysql.connector
from flask import Flask, request, jsonify, send_file, Response
from prometheus_client import generate_latest, Counter, REGISTRY
from flask_cors import CORS
from openpyxl.workbook import Workbook

app = Flask(__name__)
CORS(app, resources={r"/backend/*": {"origins": "*"}})

REQUESTS = Counter('hello_worlds_total', 'Hello Worlds requested.')

@app.route('/backend/hello')
def hello():
    REQUESTS.inc()
    return "Hello World!"

@app.route('/backend/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

@app.route('/backend', methods=['GET', 'POST'])
def api():
    if request.method == 'GET':
        return jsonify({"message": "Hello from the API!"})
    return jsonify({"error": "No valid http method"}), 400

@app.route('/backend/xlsx', methods=['GET'])
def xlsx():
    if request.method == 'GET':
        conn = mysql.connector.connect(
            host='db',
            port=3306,
            user='root',
            password='root',
            database='scraperdb'
        )
        cursor = conn.cursor()
        fn = str(date.today()) + "_scraped_export"
        cursor.execute("""
                            SELECT hotels.hotelname, hotels.address, prices.price, prices.scrapdate, prices.startdate,
                                prices.enddate, prices.guests, prices.score, prices.reviewCount
                            FROM hotels
                            INNER JOIN prices ON hotels.hotelname = prices.hotelname
                            ORDER BY hotels.hotelname
                        """)
        data = cursor.fetchall()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = fn
        sheet.append(
            ['Hotel Name', 'Address', 'Price', 'Scrap Date', 'Datum', 'Nights', 'Guests', 'Score', 'Review Count'])
        for row in data:
            sheet.append(row)
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f'{fn}.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        return jsonify({"error": "No valid http method"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
