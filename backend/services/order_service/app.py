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

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"service": "order_service", "status": "active"})

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query_orders = """
            SELECT order_id, customer_id, total_amount, status, created_at
            FROM orders
            ORDER BY created_at DESC
        """
        cursor.execute(query_orders)
        orders = cursor.fetchall()
        
        result = []
        for order in orders:
            query_items = """
                SELECT product_id, quantity, unit_price_at_purchase
                FROM order_items
                WHERE order_id = %s
            """
            cursor.execute(query_items, (order['order_id'],))
            items = cursor.fetchall()
            
            order_data = {
                "order_id": order['order_id'],
                "customer_id": order['customer_id'],
                "total_amount": float(order['total_amount']),
                "status": order['status'],
                "created_at": order['created_at'].isoformat() if order['created_at'] else None,
                "items": [
                    {
                        "product_id": item['product_id'],
                        "quantity": item['quantity'],
                        "unit_price": float(item['unit_price_at_purchase'])
                    }
                    for item in items
                ]
            }
            result.append(order_data)
        
        return jsonify({
            "total_orders": len(result),
            "orders": result
        }), 200
        
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database Error: {err}"}), 500
    
    except Exception as e:
        return jsonify({"error": f"Server Error: {str(e)}"}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query_order = """
            SELECT order_id, customer_id, total_amount, status, created_at
            FROM orders
            WHERE order_id = %s
        """
        cursor.execute(query_order, (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return jsonify({"error": f"Order {order_id} not found"}), 404
        
        query_items = """
            SELECT product_id, quantity, unit_price_at_purchase
            FROM order_items
            WHERE order_id = %s
        """
        cursor.execute(query_items, (order_id,))
        items = cursor.fetchall()
        
        response = {
            "order_id": order['order_id'],
            "customer_id": order['customer_id'],
            "total_amount": float(order['total_amount']),
            "status": order['status'],
            "created_at": order['created_at'].isoformat() if order['created_at'] else None,
            "items": [
                {
                    "product_id": item['product_id'],
                    "quantity": item['quantity'],
                    "unit_price": float(item['unit_price_at_purchase'])
                }
                for item in items
            ]
        }
        
        return jsonify(response), 200
        
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database Error: {err}"}), 500
    
    except Exception as e:
        return jsonify({"error": f"Server Error: {str(e)}"}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/orders/create', methods=['POST'])
def create_order():
    data = request.get_json()
    
    # Validate Inputs
    if not data or 'customer_id' not in data or 'products' not in data:
        return jsonify({"error": "Invalid input. 'customer_id' and 'products' are required."}), 400

    customer_id = data.get('customer_id')
    products = data.get('products') 

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        total_order_amount = 0
        items_buffer = []


        for item in products:
            p_id = item['product_id']
            qty = int(item['quantity'])


            try:
                price_response = requests.get(f'http://localhost:5002/api/inventory/check/{p_id}')
                if price_response.status_code != 200:
                    return jsonify({"error": f"Product {p_id} not found in inventory"}), 404
                
                current_price = price_response.json()['unit_price']
                
            except requests.exceptions.RequestException:
                return jsonify({"error": "Failed to connect to Inventory Service"}), 503


            update_payload = {"product_id": p_id, "quantity_change": -qty}
            try:
                update_response = requests.put('http://localhost:5002/api/inventory/update', json=update_payload)
                
                if update_response.status_code != 200:

                    conn.rollback()
                    return jsonify({
                        "error": "Stock update failed", 
                        "details": update_response.json()
                    }), 400
            except requests.exceptions.RequestException:
                conn.rollback()
                return jsonify({"error": "Failed to connect to Inventory Service for update"}), 503

            line_total = current_price * qty
            total_order_amount += line_total


            items_buffer.append({
                "product_id": p_id,
                "quantity": qty,
                "unit_price": current_price 
            })

        query_header = """
            INSERT INTO orders (customer_id, total_amount, status, created_at)
            VALUES (%s, %s, 'CONFIRMED', NOW())
        """
        cursor.execute(query_header, (customer_id, total_order_amount))

        new_order_id = cursor.lastrowid


        query_items = """
            INSERT INTO order_items (order_id, product_id, quantity, unit_price_at_purchase)
            VALUES (%s, %s, %s, %s)
        """
        
        for item in items_buffer:
            cursor.execute(query_items, (
                new_order_id,
                item['product_id'],
                item['quantity'],
                item['unit_price']
            ))

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Order created successfully",
            "order_id": new_order_id,
            "total_amount": total_order_amount,
            "items_count": len(items_buffer)
        }), 201

    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1452:
            return jsonify({"error": "Database Constraint Error: Customer ID or Product ID does not exist."}), 400
        return jsonify({"error": f"Database Error: {err}"}), 500

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Server Error: {str(e)}"}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    print("Order Service running on port 5001...")
    app.run(port=5001, debug=True)
