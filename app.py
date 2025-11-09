from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local use)
load_dotenv("config.env")

app = Flask(__name__)
CORS(app)

# --- MySQL Credentials from Environment Variables ---
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
SSL_CA_PATH = os.getenv("SSL_CA_PATH", "ca.pem")

# --- Database Connection ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            ssl_ca=SSL_CA_PATH
        )
        return conn
    except mysql.connector.Error as err:
        print("Database connection failed:", err)
        return None

# --- Create Table if Not Exists ---
def create_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        create_table_query = """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            phone_no VARCHAR(20) NOT NULL,
            from_station VARCHAR(255) NOT NULL,
            to_station VARCHAR(255) NOT NULL,
            travel_date VARCHAR(50) NOT NULL,
            travel_time VARCHAR(50) NOT NULL,
            no_of_passengers INT NOT NULL,
            class VARCHAR(50) NOT NULL,
            selected_seats TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        print("Table created successfully or already exists")

    except mysql.connector.Error as err:
        print(" Error creating table:", err)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

# --- POST /book ---
@app.route('/book', methods=['POST'])
def add_booking():
    data = request.get_json()
    print("Received booking data:", data)

    required_fields = [
        "name", "phone_no", "from_station", "to_station",
        "travel_date", "travel_time", "no_of_passengers", "class", "selected_seats"
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor()
        sql = """
        INSERT INTO bookings 
        (name, phone_no, from_station, to_station, travel_date, travel_time, no_of_passengers, class, selected_seats)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        seats_str = ",".join(map(str, data["selected_seats"])) if data["selected_seats"] else ""
        values = (
            data["name"], data["phone_no"], data["from_station"], data["to_station"],
            data["travel_date"], data["travel_time"], int(data["no_of_passengers"]),
            data["class"], seats_str
        )
        cursor.execute(sql, values)
        conn.commit()
        booking_id = cursor.lastrowid

        return jsonify({
            "message": "Booking added successfully!",
            "booking_id": booking_id,
            "data": data
        }), 201

    except mysql.connector.Error as err:
        print("Database Error:", err)
        return jsonify({"error": f"Database error: {err}"}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

# --- GET /bookings ---
@app.route('/bookings', methods=['GET'])
def get_bookings():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
        bookings = cursor.fetchall()

        for booking in bookings:
            booking['selected_seats'] = booking['selected_seats'].split(',') if booking['selected_seats'] else []

        return jsonify({"bookings": bookings}), 200

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

# --- GET /health ---
@app.route('/health', methods=['GET'])
def health_check():
    try:
        conn = get_db_connection()
        if conn and conn.is_connected():
            return jsonify({"status": "healthy", "database": "connected"}), 200
        else:
            return jsonify({"status": "unhealthy", "database": "disconnected"}), 500
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# --- Root ---
@app.route('/')
def home():
    return jsonify({
        "message": "Train Booking Flask API is running securely!",
        "endpoints": {
            "POST /book": "Create a new booking",
            "GET /bookings": "Get all bookings",
            "GET /health": "Health check"
        }
    })

# --- Vercel expects app object, not app.run() ---
create_table()
# Remove app.run() — Vercel automatically runs the app using WSGI
