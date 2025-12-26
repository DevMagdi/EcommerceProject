from flask import Flask, jsonify, request
import mysql.connector
import requests

app = Flask(__name__)

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'ecommerce_system'
}


CUSTOMER_SERVICE_URL = "http://localhost:5004/api/customers"
INVENTORY_SERVICE_URL = "http://localhost:5002/api/inventory/check"

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"❌ DB Connection Error: {err}")
        return None

def log_to_db(order_id, customer_id, message):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO notification_log (order_id, customer_id, notification_type, message) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (order_id, customer_id, 'SMS', message))
            conn.commit()
            print("✅ [DB] Log saved successfully.")
        except Exception as e:
            print(f"❌ [DB] Error logging: {e}")
        finally:
            cursor.close()
            conn.close()


@app.route('/api/notifications/send', methods=['POST'])
def send_notification():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({"error": "Missing order_id"}), 400

    print(f"\n🔄 Processing Notification for Order #{order_id}")

    conn = get_db_connection()
    customer_id = None
    product_id_sample = 1 # افتراضي للتحقق من المخزون

    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT o.customer_id, oi.product_id
                       FROM orders o
                                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                       WHERE o.order_id = %s LIMIT 1
                       """, (order_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            customer_id = result['customer_id']
            if result['product_id']: product_id_sample = result['product_id']
        else:
            return jsonify({"error": "Order not found"}), 404
    try:
        print(f"📞 Calling Customer Service API for ID: {customer_id}...")
        cust_response = requests.get(f"{CUSTOMER_SERVICE_URL}/{customer_id}")

        if cust_response.status_code == 200:
            cust_data = cust_response.json()
            customer_name = cust_data.get('name')
            phone = cust_data.get('phone')
            print(f"   ✅ Customer Found: {customer_name}, Phone: {phone}")
        else:
            print("   ❌ Customer Service Error")
            return jsonify({"error": "Failed to fetch customer data"}), 500

    except Exception as e:
        return jsonify({"error": f"Customer Service Unreachable: {str(e)}"}), 503
    try:
        print(f"📦 Calling Inventory Service API for Product: {product_id_sample}...")
        inv_response = requests.get(f"{INVENTORY_SERVICE_URL}/{product_id_sample}")

        if inv_response.status_code == 200:
            print("   ✅ Inventory Check: OK")
        else:
            print("   ⚠️ Inventory Check: Warning (Item might be out of stock)")

    except Exception as e:
        print(f"   ⚠️ Inventory Service Unreachable: {e}")
    message = f"Hello {customer_name}, your order #{order_id} is confirmed!"
    print("=" * 40)
    print(f"📲 SENDING SMS TO: {phone}")
    print(f"💬 MESSAGE: {message}")
    print("=" * 40)
    log_to_db(order_id, customer_id, message)

    return jsonify({
        "status": "success",
        "message": "Notification sent via Real API orchestration",
        "details": {
            "customer": customer_name,
            "phone": phone
        }
    }), 200

if __name__ == '__main__':
    app.run(port=5005, debug=True)