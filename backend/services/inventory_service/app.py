from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Change this to your MySQL username
    'password': 'SoftwareSQL_11',  # Change this to your MySQL password
    'database': 'ecommerce_system'
}

# ============================================
# DATABASE CONNECTION HELPER
# ============================================
def get_db_connection():
    """
    Creates and returns a MySQL database connection.
    Returns None if connection fails.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# ============================================
# HEALTH CHECK ENDPOINT (OPTIONAL BUT USEFUL)
# ============================================
@app.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check to verify service is running.
    Test with: http://localhost:5002/health
    """
    return jsonify({
        "status": "healthy",
        "service": "Inventory Service",
        "port": 5002,
        "timestamp": datetime.now().isoformat()
    }), 200

# ============================================
# ENDPOINT 1: CHECK INVENTORY (GET)
# ============================================
@app.route('/api/inventory/check/<int:product_id>', methods=['GET'])
def check_inventory(product_id):
    """
    Check stock availability for a specific product.
    
    URL: GET /api/inventory/check/{product_id}
    Example: GET /api/inventory/check/1
    
    Returns:
        200: Product details (product_id, name, quantity, price)
        404: Product not found
        500: Database error
    """
    connection = get_db_connection()
    
    if not connection:
        return jsonify({
            "error": "Database connection failed"
        }), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Query to get product details
        query = """
            SELECT 
                product_id,
                product_name,
                quantity_available,
                unit_price,
                last_updated
            FROM inventory 
            WHERE product_id = %s
        """
        
        cursor.execute(query, (product_id,))
        product = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if product:
            # Convert Decimal to float for JSON serialization
            product['unit_price'] = float(product['unit_price'])
            
            # Add stock status
            product['in_stock'] = product['quantity_available'] > 0
            
            return jsonify(product), 200
        else:
            return jsonify({
                "error": "Product not found",
                "product_id": product_id
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
# ENDPOINT 2: UPDATE INVENTORY (PUT)
# ============================================
@app.route('/api/inventory/update', methods=['PUT'])
def update_inventory():
    """
    Update inventory quantity for a product.
    
    URL: PUT /api/inventory/update
    
    Request Body (JSON):
    {
        "product_id": 1,
        "quantity_change": -5  (negative = decrease, positive = increase)
    }
    
    Returns:
        200: Update successful
        400: Invalid input or insufficient stock
        404: Product not found
        500: Database error
    """
    # Get JSON data from request
    data = request.get_json()
    
    # Validate input
    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400
    
    product_id = data.get('product_id')
    quantity_change = data.get('quantity_change')
    
    # Validate required fields
    if product_id is None or quantity_change is None:
        return jsonify({
            "error": "Missing required fields",
            "required": ["product_id", "quantity_change"]
        }), 400
    
    # Validate data types
    try:
        product_id = int(product_id)
        quantity_change = int(quantity_change)
    except ValueError:
        return jsonify({
            "error": "Invalid data types",
            "product_id": "must be integer",
            "quantity_change": "must be integer"
        }), 400
    
    connection = get_db_connection()
    
    if not connection:
        return jsonify({
            "error": "Database connection failed"
        }), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # First, check if product exists and get current quantity
        check_query = """
            SELECT product_id, product_name, quantity_available 
            FROM inventory 
            WHERE product_id = %s
        """
        cursor.execute(check_query, (product_id,))
        product = cursor.fetchone()
        
        if not product:
            cursor.close()
            connection.close()
            return jsonify({
                "error": "Product not found",
                "product_id": product_id
            }), 404
        
        current_quantity = product['quantity_available']
        new_quantity = current_quantity + quantity_change
        
        # Check if update would result in negative quantity
        if new_quantity < 0:
            cursor.close()
            connection.close()
            return jsonify({
                "error": "Insufficient stock",
                "product_id": product_id,
                "product_name": product['product_name'],
                "current_quantity": current_quantity,
                "requested_change": quantity_change,
                "shortage": abs(new_quantity)
            }), 400
        
        # Update the inventory
        update_query = """
            UPDATE inventory 
            SET quantity_available = quantity_available + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE product_id = %s
        """
        cursor.execute(update_query, (quantity_change, product_id))
        connection.commit()
        
        # Get updated product details
        cursor.execute(check_query, (product_id,))
        updated_product = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "message": "Inventory updated successfully",
            "product_id": product_id,
            "product_name": updated_product['product_name'],
            "previous_quantity": current_quantity,
            "quantity_change": quantity_change,
            "new_quantity": updated_product['quantity_available']
        }), 200
        
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
# ERROR HANDLERS
# ============================================
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors for undefined routes"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested URL was not found on this server"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle wrong HTTP method errors"""
    return jsonify({
        "error": "Method not allowed",
        "message": "The method is not allowed for the requested URL"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

# ============================================
# RUN THE APPLICATION
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Starting Inventory Service")
    print("=" * 50)
    print(f"Service running on: http://localhost:5002")
    print(f"Health check: http://localhost:5002/health")
    print(f"Endpoints:")
    print(f"  GET  /api/inventory/check/<product_id>")
    print(f"  PUT  /api/inventory/update")
    print("=" * 50)
    
    # Run Flask app on port 5002
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5002,
        debug=True  # Enable debug mode for development
    )