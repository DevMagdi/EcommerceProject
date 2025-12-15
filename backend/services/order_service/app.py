from flask import Flask, jsonify, request
import mysql.connector

# Service: order_service
app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "order_service", "port": 5001, "status": "active"})

if __name__ == '__main__':
    # Running on port 5001 as defined in PDF
    app.run(port=5001, debug=True)
