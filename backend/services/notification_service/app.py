from flask import Flask, jsonify, request
import datetime

app = Flask(__name__)

MOCK_DATABASE = {
    1: {"customer": "Ahmed Ali", "phone": "01012345678", "email": "ahmed@test.com"},
    2: {"customer": "Sara Mohsen", "phone": "01122334455", "email": "sara@test.com"},
}

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "notification_service", "port": 5005, "status": "active"})

# --- Endpoint المطلوب في الـ PDF ---
@app.route('/api/notifications/send', methods=['POST'])
def send_notification():
    # 1. Receive order_id from Order Service (Step 1 in PDF)
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({"error": "Missing order_id"}), 400

    print(f"\n[🔄 START] Processing Notification for Order #{order_id}")

    # 2. Simulate Calling Customer Service (Step 2 in PDF)
    customer_info = MOCK_DATABASE.get(order_id, {"customer": "Unknown Guest", "phone": "0000000000"})
    name = customer_info['customer']
    phone = customer_info['phone']

    print(f"[📞 SIMULATION] Retrieved Customer Info: {name} | Phone: {phone}")

    # 3. Simulate Calling Inventory Service (Step 3 in PDF)

    print(f"[📦 SIMULATION] Inventory Status Checked: Items Reserved.")

    # 4. Generate Message & Log (Step 4 & 5 in PDF)
    message = f"Hi {name}, your order #{order_id} is confirmed! Thank you for shopping."
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # consol log
    print("=" * 40)
    print(f"📲 SENDING SMS...")
    print(f"TO: {phone}")
    print(f"MSG: {message}")
    print("=" * 40)

    # تسجيل في ملف Text (بديل الـ Log to Database)
    log_entry = f"[{timestamp}] Order: {order_id} | Sent To: {phone} | Status: Sent\n"
    try:
        with open("notifications_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)
        print("[✅ LOG] Saved to notifications_log.txt")
    except Exception as e:
        print(f"[❌ LOG ERROR] Could not write to file: {e}")

    # 6. Return success confirmation (Step 6 in PDF)
    return jsonify({
        "status": "success",
        "message": "Notification processed successfully",
        "details": {
            "order_id": order_id,
            "sent_to": phone,
            "channel": "SMS (Simulated)"
        }
    }), 200

if __name__ == '__main__':
    # Running on port 5005
    app.run(port=5005, debug=True)