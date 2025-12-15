from flask import Flask, jsonify, request
import mysql.connector

# Service: inventory_service
app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "inventory_service", "port": 5002, "status": "active"})

if __name__ == '__main__':
    # Running on port 5002 as defined in PDF
    app.run(port=5002, debug=True)
