from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)


db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'ecommerce_system'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to DB: {err}")
        return None

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "pricing_service", "port": 5003, "status": "active"})


@app.route('/api/pricing/calculate', methods=['POST'])
def calculate_pricing():
    data = request.get_json()


    # Expected format as required in pdf: {"products": [{"product_id": 1, "quantity": 2}, ...], "region": "EG"}
    products_list = data.get('products', [])
    region = data.get('region', 'EG')

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)

    order_subtotal = 0
    itemized_breakdown = []

    try:

        for item in products_list:
            p_id = item.get('product_id')
            qty = item.get('quantity', 1)

            cursor.execute("SELECT product_name, unit_price FROM inventory WHERE product_id = %s", (p_id,))
            product = cursor.fetchone()

            if not product:
                continue

            base_price = float(product['unit_price'])
            prod_name = product['product_name']

            cursor.execute("""
                SELECT discount_percentage 
                FROM pricing_rules 
                WHERE product_id = %s AND min_quantity <= %s 
                ORDER BY min_quantity DESC LIMIT 1
            """, (p_id, qty))

            rule = cursor.fetchone()
            discount_percent = float(rule['discount_percentage']) if rule else 0.0


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
                "total_after_discount": round(final_item_price, 2)
            })

        tax_rate = 14.0
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
    # Running on port 5003
    app.run(port=5003, debug=True)