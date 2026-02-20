# 🛒 E-Commerce Order Management System

> **Course:** Service-Oriented Architecture | **Cairo University – Faculty of Computers and Artificial Intelligence**

---

## 📌 Project Overview

This project implements a **microservices-based E-Commerce Order Management System**. A **Java JSP web application** acts as the frontend and API gateway, communicating with **five independent Python Flask microservices** that handle specific business logic. All services communicate via **HTTP REST APIs** with JSON payloads.

---

## 🏗️ Architecture

```
┌─────────────────────────────┐
│   Java JSP Application      │  ← Frontend + API Gateway (Port 8080)
│   (Apache Tomcat 10.x)      │
└────────────┬────────────────┘
             │ HTTP REST (JSON)
    ┌────────┼──────────────────────────────┐
    │        │                              │
    ▼        ▼        ▼          ▼          ▼
┌───────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│ Order │ │ Inv. │ │Pricing │ │Customer│ │Notification│
│ :5001 │ │ :5002│ │  :5003 │ │  :5004 │ │   :5005    │
└───┬───┘ └──┬───┘ └───┬────┘ └───┬────┘ └─────┬──────┘
    │        │         │          │             │
    └────────┴─────────┴──────────┴─────────────┘
                          │
                    ┌─────▼──────┐
                    │  MySQL DB  │
                    │  :3306     │
                    └────────────┘
```

---

## 🧰 Technology Stack

| Layer       | Technology                        |
|-------------|-----------------------------------|
| Frontend    | Java JSP with Jakarta EE (Servlets) |
| Backend     | Python 3.8+ with Flask            |
| Database    | MySQL 8.0                         |
| Web Server  | Apache Tomcat 10.x                |
| API Format  | REST with JSON                    |

---

## 🔌 Port Configuration

| Service              | Port |
|----------------------|------|
| Java JSP Application | 8080 |
| Order Service        | 5001 |
| Inventory Service    | 5002 |
| Pricing Service      | 5003 |
| Customer Service     | 5004 |
| Notification Service | 5005 |

---

## 🗂️ Project Structure

```
ecommerce-system/
│
├── jsp-app/                        # Java JSP Application (Tomcat)
│   ├── src/main/java/
│   │   └── OrderServlet.java
│   └── src/main/webapp/
│       ├── index.jsp               # Product catalog
│       ├── checkout.jsp            # Order form
│       └── confirmation.jsp        # Order success page
│
├── order-service/                  # Flask Service (Port 5001)
│   └── app.py
│
├── inventory-service/              # Flask Service (Port 5002)
│   └── app.py
│
├── pricing-service/                # Flask Service (Port 5003)
│   └── app.py
│
├── customer-service/               # Flask Service (Port 5004)
│   └── app.py
│
├── notification-service/           # Flask Service (Port 5005)
│   └── app.py
│
└── db/
    └── schema.sql                  # All table creation + sample data
```

---

## ⚙️ Microservices

### 1. Order Service — Port `5001`
Receives all parameters from the Java application.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orders/create` | Create a new order |
| GET | `/api/orders/{order_id}` | Retrieve order details |

**Database Table:** `order`

---

### 2. Inventory Service — Port `5002`
Database-driven service managing product stock.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/inventory/check/{product_id}` | Check stock availability |
| PUT | `/api/inventory/update` | Update inventory after order |

**Database Table:** `inventory`

---

### 3. Pricing Service — Port `5003`
Calculates final pricing with discounts and taxes.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pricing/calculate` | Calculate order total |

Calls the **Inventory Service** for base prices, then applies discount rules from its own database.

**Database Tables:** `pricing_rules`, `tax_rates`

---

### 4. Customer Service — Port `5004`
Manages customer profiles and loyalty points.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/customers/{customer_id}` | Get customer profile |
| GET | `/api/customers/{customer_id}/orders` | Get order history (calls Order Service) |
| PUT | `/api/customers/{customer_id}/loyalty` | Update loyalty points |

**Database Table:** `customers`

---

### 5. Notification Service — Port `5005`
Aggregates data from multiple services to send order notifications.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/notifications/send` | Send order notification |

**Communication Flow:**
1. Receive `order_id`
2. Call Customer Service → get contact info
3. Call Inventory Service → check stock/delivery estimate
4. Generate & simulate notification (console output)
5. Log to database

**Database Table:** `notification_log`


---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Java JDK 11+
- Apache Tomcat 10.x
- MySQL 8.0
- Maven (for JSP app)

### 1. Set up Python services

For each service, create a virtual environment and install dependencies:

```bash
cd order-service
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install flask mysql-connector-python requests
python app.py
```

Repeat for `inventory-service`, `pricing-service`, `customer-service`, and `notification-service`.

### 2. Start all Flask services

Each service runs on its designated port. Run each in a separate terminal:

```bash
# Order Service
cd order-service && python app.py   # → http://localhost:5001

# Inventory Service
cd inventory-service && python app.py  # → http://localhost:5002

# Pricing Service
cd pricing-service && python app.py    # → http://localhost:5003

# Customer Service
cd customer-service && python app.py   # → http://localhost:5004

# Notification Service
cd notification-service && python app.py  # → http://localhost:5005
```

### 3. Deploy the JSP application

Deploy the `jsp-app` WAR file to Tomcat and access it at:
```
http://localhost:8080
```

---

## 🖥️ Frontend Pages

| Page | Description |
|------|-------------|
| `index.jsp` | Product catalog (fetched from Inventory Service) |
| `checkout.jsp` | Order form with customer and product selection |
| `confirmation.jsp` | Order success page with full details |


- Always use parameterized SQL queries to prevent injection attacks.
- Services communicate exclusively via HTTP REST — no direct DB sharing between services.
- Email/SMS notifications are simulated via console output (no real email sending required).
