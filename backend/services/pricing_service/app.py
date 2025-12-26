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

INVENTORY_SERVICE_URL = "http://localhost:5002/api/inventory/check"

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        return None

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "pricing_service", "status": "active"})

@app.route('/api/pricing/calculate', methods=['POST'])
def calculate_pricing():
    data = request.get_json()
    products_list = data.get('products', [])
    region = data.get('region', 'EG')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) if conn else None

    order_subtotal = 0
    itemized_breakdown = []

    try:
        for item in products_list:
            p_id = item.get('product_id')
            qty = item.get('quantity', 1)
            try:
                response = requests.get(f"{INVENTORY_SERVICE_URL}/{p_id}")
                if response.status_code == 200:
                    inventory_data = response.json()
                    base_price = float(inventory_data.get('unit_price', 0))
                    prod_name = inventory_data.get('product_name', 'Unknown')
                else:
                    print(f"⚠️ Product {p_id} not found in Inventory Service")
                    continue
            except requests.exceptions.ConnectionError:
                return jsonify({"error": "Failed to connect to Inventory Service (Is it running on 5002?)"}), 503
            discount_percent = 0.0
            if cursor:
                cursor.execute("""
                               SELECT discount_percentage
                               FROM pricing_rules
                               WHERE product_id = %s AND min_quantity <= %s
                               ORDER BY min_quantity DESC LIMIT 1
                               """, (p_id, qty))
                rule = cursor.fetchone()
                if rule:
                    discount_percent = float(rule['discount_percentage'])

            total_item_price = base_price * qty
            discount_amount = total_item_price * (discount_percent / 100)
            final_item_price = total_item_price - discount_amount

            order_subtotal += final_item_price

            itemized_breakdown.append({
                "product_id": p_id,
                "name": prod_name,
                "quantity": qty,
                "unit_price": base_price,
                "discount_percent": f"{discount_percent}%",
                "total": round(final_item_price, 2)
            })

        tax_rate = 14.0 # Default fallback
        if cursor:
            cursor.execute("SELECT tax_rate FROM tax_rates WHERE region = %s", (region,))
            tax_row = cursor.fetchone()
            if tax_row:
                tax_rate = float(tax_row['tax_rate'])

        tax_amount = order_subtotal * (tax_rate / 100)
        final_total = order_subtotal + tax_amount

        return jsonify({
            "status": "success",
            "breakdown": itemized_breakdown,
            "subtotal": round(order_subtotal, 2),
            "tax_rate": f"{tax_rate}%",
            "tax_amount": round(tax_amount, 2),
            "total_price": round(final_total, 2)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    app.run(port=5003, debug=True)