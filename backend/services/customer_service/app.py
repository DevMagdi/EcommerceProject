from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error
import requests
from datetime import datetime

app = Flask(__name__)

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  
    'password': 'SoftwareSQL_11', 
    'database': 'ecommerce_system'
}

# Order Service Configuration
ORDER_SERVICE_URL = "http://localhost:5001"

# ============================================
# DATABASE CONNECTION HELPER
# ============================================
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# ============================================
# HEALTH CHECK ENDPOINT
# ============================================
@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check to verify service is running.
    Test with: http://localhost:5004/health
    """
    return jsonify({
        "status": "healthy",
        "service": "Customer Service",
        "port": 5004,
        "timestamp": datetime.now().isoformat()
    }), 200

# ============================================
# ENDPOINT 1: GET CUSTOMER PROFILE
# ============================================
@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    connection = get_db_connection()
    
    if not connection:
        return jsonify({
            "error": "Database connection failed"
        }), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Query to get customer details
        query = """
            SELECT 
                customer_id,
                name,
                email,
                phone,
                loyalty_points,
                created_at
            FROM customers 
            WHERE customer_id = %s
        """
        
        cursor.execute(query, (customer_id,))
        customer = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if customer:
            # Format the response
            return jsonify({
                "customer_id": customer['customer_id'],
                "name": customer['name'],
                "email": customer['email'],
                "phone": customer['phone'],
                "loyalty_points": customer['loyalty_points'],
                "member_since": customer['created_at'].isoformat() if customer['created_at'] else None
            }), 200
        else:
            return jsonify({
                "error": "Customer not found",
                "customer_id": customer_id
            }), 404
            
    except Error as e:
        return jsonify({
            "error": "Database query failed",
            "details": str(e)
        }), 500
    finally:
        if connection and connection.is_connected():
            connection.close()

# ============================================
# ENDPOINT 2: GET CUSTOMER ORDER HISTORY
# ============================================
@app.route('/api/customers/<int:customer_id>/orders', methods=['GET']) # inter-service communication and stuff
def get_customer_orders(customer_id):
    connection = get_db_connection()
    
    if not connection:
        return jsonify({
            "error": "Database connection failed"
        }), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT customer_id, name, email, loyalty_points  # we might not need the phone here
            FROM customers 
            WHERE customer_id = %s
        """
        cursor.execute(query, (customer_id,))
        customer = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not customer:
            return jsonify({
                "error": "Customer not found",
                "customer_id": customer_id
            }), 404
        
        # Customer exists, now call Order Service to get orders
        try:
            order_service_endpoint = f"{ORDER_SERVICE_URL}/api/orders" # Does this endpoint even exist in Order Service? <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            params = {"customer_id": customer_id}
            
            response = requests.get(
                order_service_endpoint,
                params=params,
                timeout=5 
            )
            
            if response.status_code == 200:
                orders = response.json()
                return jsonify({
                    "customer_id": customer['customer_id'],
                    "customer_name": customer['name'],
                    "email": customer['email'],
                    "loyalty_points": customer['loyalty_points'],
                    "orders": orders
                }), 200
            
            elif response.status_code == 404:
                return jsonify({
                    "customer_id": customer['customer_id'],
                    "customer_name": customer['name'],
                    "email": customer['email'],
                    "loyalty_points": customer['loyalty_points'],
                    "orders": [],
                    "message": "No orders found for this customer"
                }), 200
            
            else:
                return jsonify({
                    "error": "Failed to retrieve orders from Order Service",
                    "order_service_status": response.status_code
                }), 500
            
        except requests.exceptions.ConnectionError:
            return jsonify({
                "error": "Order Service is unavailable",
                "message": "Cannot connect to Order Service on port 5001",
                "customer_id": customer_id
            }), 503
            
        except requests.exceptions.Timeout:
            return jsonify({
                "error": "Order Service timeout",
                "message": "Order Service took too long to respond"
            }), 503
            
        except Exception as e:
            return jsonify({
                "error": "Failed to communicate with Order Service",
                "details": str(e)
            }), 500
            
    except Error as e:
        return jsonify({
            "error": "Database query failed",
            "details": str(e)
        }), 500
    finally:
        if connection and connection.is_connected():
            connection.close()

# ============================================
# ENDPOINT 3: UPDATE LOYALTY POINTS
# ============================================
@app.route('/api/customers/<int:customer_id>/loyalty', methods=['PUT'])
def update_loyalty_points(customer_id):
    """
    Request Body (JSON):
    {
        "points_change": 50  (positive = add, negative = subtract)
    }
    OR
    {
        "new_points": 150  (set to exact value)
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400
    
    # Check if either points_change or new_points is provided
    points_change = data.get('points_change')
    new_points = data.get('new_points')
    
    if points_change is None and new_points is None:
        return jsonify({
            "error": "Missing required field",
            "message": "Provide either 'points_change' or 'new_points'",
            "example_1": {"points_change": 50},
            "example_2": {"new_points": 150}
        }), 400
    
    # Validate data types
    try:
        if points_change is not None:
            points_change = int(points_change)
        if new_points is not None:
            new_points = int(new_points)
            if new_points < 0:
                return jsonify({
                    "error": "Invalid value",
                    "message": "new_points cannot be negative"
                }), 400
    except ValueError:
        return jsonify({
            "error": "Invalid data type",
            "message": "Points must be integers"
        }), 400
    
    connection = get_db_connection()
    
    if not connection:
        return jsonify({
            "error": "Database connection failed"
        }), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        check_query = """
            SELECT customer_id, name, loyalty_points 
            FROM customers 
            WHERE customer_id = %s
        """
        cursor.execute(check_query, (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            cursor.close()
            connection.close()
            return jsonify({
                "error": "Customer not found",
                "customer_id": customer_id
            }), 404
        
        current_points = customer['loyalty_points']
        
        # Determine the new points value
        if new_points is not None:
            # Set to exact value
            final_points = new_points
            update_type = "set"
        else:
            # Add/subtract points_change
            final_points = current_points + points_change
            update_type = "change"
            
            # Don't allow negative points
            if final_points < 0:
                cursor.close()
                connection.close()
                return jsonify({
                    "error": "Insufficient loyalty points",
                    "customer_id": customer_id,
                    "current_points": current_points,
                    "requested_change": points_change,
                    "shortage": abs(final_points)
                }), 400
        
        # Update the loyalty points
        update_query = """
            UPDATE customers 
            SET loyalty_points = %s
            WHERE customer_id = %s
        """
        cursor.execute(update_query, (final_points, customer_id))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        # Prepare response based on update type
        response_data = {
            "message": "Loyalty points updated successfully",
            "customer_id": customer_id,
            "customer_name": customer['name'],
            "previous_points": current_points,
            "new_points": final_points
        }
        
        if update_type == "change":
            response_data["points_change"] = points_change
        
        return jsonify(response_data), 200
        
    except Error as e:
        if connection:
            connection.rollback()
        return jsonify({
            "error": "Database update failed",
            "details": str(e)
        }), 500
    finally:
        if connection and connection.is_connected():
            connection.close()

# ============================================
# RUN THE APPLICATION
# ============================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Customer Service")
    print("=" * 60)
    print(f"Service running on: http://localhost:5004")
    print(f"Health check: http://localhost:5004/health")
    print(f"Endpoints:")
    print(f"  GET  /api/customers/<customer_id>")
    print(f"  GET  /api/customers/<customer_id>/orders")
    print(f"  PUT  /api/customers/<customer_id>/loyalty")
    print(f"\nOrder Service (Port 5001) must be running for order history!")
    print("=" * 60)
    
    # Run Flask app on port 5004
    app.run(
        host='0.0.0.0',
        port=5004,
        debug=True
    )