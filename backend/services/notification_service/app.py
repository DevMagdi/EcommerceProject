from flask import Flask, jsonify, request
import mysql.connector

# Service: notification_service
app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "notification_service", "port": 5005, "status": "active"})

if __name__ == '__main__':
    # Running on port 5005 as defined in PDF
    app.run(port=5005, debug=True)
