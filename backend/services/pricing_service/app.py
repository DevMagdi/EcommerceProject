from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

# --- 1. إعدادات قاعدة البيانات ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root', # استبدلها بكلمة مرور الـ SQL عندك
    'database': 'ecommerce_system'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "pricing_service", "port": 5003, "status": "active"})

# --- 2. الـ Endpoint الأساسي لحساب السعر ---
@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    p_id = data.get('product_id')
    qty = data.get('quantity', 1)
    region = data.get('region', 'EG')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # أ- جلب السعر من جدول inventory
        cursor.execute("SELECT unit_price FROM inventory WHERE product_id = %s", (p_id,))
        prod = cursor.fetchone()
        if not prod:
            return jsonify({"error": "Product not found"}), 404

        unit_price = float(prod['unit_price'])
        total_before = unit_price * qty

        # ب- التحقق من وجود خصم من جدول pricing_rules
        cursor.execute("SELECT discount_percentage FROM pricing_rules WHERE product_id = %s AND min_quantity <= %s", (p_id, qty))
        rule = cursor.fetchone()
        discount_pct = float(rule['discount_percentage']) if rule else 0.0
        discount_val = total_before * (discount_pct / 100)

        # ج- جلب الضريبة من جدول tax_rates
        cursor.execute("SELECT tax_rate FROM tax_rates WHERE region = %s", (region,))
        tax = cursor.fetchone()
        tax_pct = float(tax['tax_rate']) if tax else 0.0
        tax_val = (total_before - discount_val) * (tax_pct / 100)

        # د- الحسبة النهائية
        final_price = (total_before - discount_val) + tax_val

        return jsonify({
            "status": "success",
            "calculation": {
                "base_price": total_before,
                "discount_applied": f"{discount_pct}%",
                "tax_applied": f"{tax_pct}%",
                "final_total": round(final_price, 2)
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(port=5003, debug=True)