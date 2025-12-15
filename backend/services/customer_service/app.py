from flask import Flask, jsonify, request
import mysql.connector

# Service: customer_service
app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "customer_service", "port": 5004, "status": "active"})

if __name__ == '__main__':
    # Running on port 5004 
    app.run(port=5004, debug=True)
