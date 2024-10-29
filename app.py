from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from fetch import get_wind_data  # Import existing function to fetch and store data

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'  # Required for flash messages

@app.route('/')
def landing():
    return render_template('landing.html')  # Render the landing page


@app.route('/map')
def map_page():
    return render_template('index.html')  # Serves the map page

@app.route('/login')
def login():
    return render_template('login.html')  # Render the login page

@app.route('/signup')
def signup():
    return render_template('signup.html')  # Render the signup page

@app.route('/submit-signup', methods=['POST'])
def submit_signup():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    # Check if passwords match
    if password != confirm_password:
        flash("Passwords do not match!", "error")
        return redirect(url_for('signup'))

    # Hash the password using the default method
    hashed_password = generate_password_hash(password)  # Removed the method parameter

    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1234',
            database='wind_wave_direction'  # Replace with your actual database name
        )
        cursor = connection.cursor()

        # Insert user data into the users table
        cursor.execute('''INSERT INTO users (username, email, password)
                          VALUES (%s, %s, %s)''', (username, email, hashed_password))
        connection.commit()
        flash("Signup successful! You can now log in.", "success")

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        flash("Signup failed! Please try again.", "error")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('login'))  # Redirect to the login page after signup

@app.route('/submit-login', methods=['POST'])
def submit_login():
    username = request.form['username']
    password = request.form['password']

    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1234',
            database='wind_wave_direction'  # Replace with your actual database name
        )
        cursor = connection.cursor(dictionary=True)

        # Fetch the user data based on the username
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()

        # Check if user exists and password matches
        if user and check_password_hash(user['password'], password):
            flash("Login successful!", "success")
            return redirect(url_for('map_page'))  # Redirect to the map page

        flash("Invalid username or password!", "error")
        return redirect(url_for('login'))

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        flash("Login failed! Please try again.", "error")
        return redirect(url_for('login'))

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/get-stored-data', methods=['POST'])
def get_stored_data():
    data = request.get_json()
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])

    print(f"[DEBUG] Received Latitude: {latitude}, Longitude: {longitude}")

    try:
        # Establish connection to the database
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1234',
            database='wind_wave_direction'
        )
        cursor = connection.cursor(dictionary=True)

        # Attempt to find the location ID based on latitude and longitude
        cursor.execute('''SELECT location_id FROM locations
                          WHERE latitude = CAST(%s AS DECIMAL(10, 7))
                          AND longitude = CAST(%s AS DECIMAL(10, 7))''',
                       (latitude, longitude))
        location = cursor.fetchone()  # Fetch the first result

        # If location is not found, fetch data from the API
        if not location:
            print("[DEBUG] Location not found. Fetching from API...")

            # Fetch data from API and store it
            result = get_wind_data(latitude, longitude)
            if not result:
                return jsonify({'success': False, 'message': 'Failed to fetch or store data from API.'})

            # After the data is inserted, commit the transaction to save the changes
            connection.commit()  # Ensure data is committed after insertion

            # Re-fetch the location ID after inserting new data
            cursor.execute('''SELECT location_id FROM locations
                            WHERE latitude = CAST(%s AS DECIMAL(10, 7))
                            AND longitude = CAST(%s AS DECIMAL(10, 7))''',
                        (latitude, longitude))
            location = cursor.fetchone()  # Fetch the newly inserted result

        # Handle the case where the location ID is still not found
        if not location:
            print("[ERROR] Location insertion or retrieval failed.")
            return jsonify({'success': False, 'message': 'Location insertion failed.'})

        # Extract the location ID
        location_id = location['location_id']
        print(f"[DEBUG] Found Location ID: {location_id}")

        # Fetch hourly wind data for the found location
        cursor.execute('''SELECT time, wind_wave_height, wind_wave_direction, wind_wave_period
                          FROM hourly_wind_wave
                          WHERE location_id = %s
                          ORDER BY time ASC''', (location_id,))
        hourly_data = cursor.fetchall()

        # Fetch current wind data for the found location
        cursor.execute('''SELECT * FROM current_wind_wave
                          WHERE location_id = %s
                          ORDER BY time DESC LIMIT 1''', (location_id,))
        current_data = cursor.fetchone()

        # Check if the data is present
        if not hourly_data or not current_data:
            return jsonify({'success': False, 'message': 'No Wind Wave data found for this location.'})

        # Prepare response for the frontend
        response = {
            'success': True,
            'hourly': {
                'time': [row['time'].strftime('%Y-%m-%d %H:%M') for row in hourly_data],
                'wind_wave_height': [row['wind_wave_height'] for row in hourly_data],
                'wind_wave_direction': [row['wind_wave_direction'] for row in hourly_data],
                'wind_wave_period': [row['wind_wave_period'] for row in hourly_data]
            },
            'current': {
                'time': current_data['time'].strftime('%Y-%m-%d %H:%M'),
                'wind_wave_height': current_data['wind_wave_height'],
                'wind_wave_direction': current_data['wind_wave_direction'],
                'wind_wave_period': current_data['wind_wave_period'],
                'wind_wave_peak_period': current_data['wind_wave_peak_period']
            }
        }

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        response = {'success': False, 'message': f'Database error: {str(e)}'}
    finally:
        # Ensure the database connection is closed
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

    print(f"[DEBUG] Response: {response}")
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
