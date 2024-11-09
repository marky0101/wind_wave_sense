from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get the form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))
        
        try:
            # Connect to the database
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='root1234',
                database='wind_wave_direction'  # Replace with your actual database name
            )
            cursor = connection.cursor()

            # Insert user data into the 'user' table
            cursor.execute('''INSERT INTO user (username, email, password)
                              VALUES (%s, %s, %s)''', (username, email, password))  # Store the password as plain text

            # Commit the transaction
            connection.commit()

            flash('Signup successful! You can now log in.', 'success')
            return redirect(url_for('login'))  # Redirect to the login page after successful signup

        except Error as e:
            print(f"[ERROR] Database error: {e}")
            flash(f'An error occurred: {e}', 'error')
            return redirect(url_for('signup'))
        finally:
            # Close the connection
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

    # If it's a GET request, render the signup page
    return render_template('signup.html')

@app.route('/submit-login', methods=['POST'])
def submit_login():
    username = request.form['username']
    password = request.form['password']

    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1234',
            database='wind_wave_direction'
        )
        cursor = connection.cursor(dictionary=True)

        # Query to check if the user exists and their password matches
        cursor.execute('''SELECT * FROM user WHERE username = %s AND password = %s''', (username, password))
        user = cursor.fetchone()  # Fetch the first result

        # If the user is not found, flash an error message
        if not user:
            flash('Invalid username or password!', 'error')
            return redirect(url_for('login'))  # Redirect back to login page

        # Store user information in the session (this allows us to track the logged-in user)
        session['user_id'] = user['id']
        session['username'] = user['username']
        flash('Login successful!', 'success')

        return redirect(url_for('map_page'))  # Redirect to the admin page after successful login

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('login'))
    finally:
        # Close the connection
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/admin')
def admin_page():
    return render_template('admin.html')  # Render the admin page

@app.route('/users')
def users_page():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1234',
            database='wind_wave_direction'  # Replace with your actual database name
        )
        cursor = connection.cursor(dictionary=True)

        # Query to get user data including the password
        cursor.execute("SELECT id, username, email, password, created_at FROM user")  # Include password in the query
        users = cursor.fetchall()

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        users = []  # Default to an empty list if there's an error
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('users.html', users=users)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1234',
            database='wind_wave_direction'
        )
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            # Get updated data from the form
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            # Update query
            cursor.execute("""
                UPDATE user 
                SET username = %s, email = %s, password = %s
                WHERE id = %s
            """, (username, email, password, user_id))

            connection.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('users_page'))

        # Fetch the user data to pre-fill the form
        cursor.execute("SELECT id, username, email, password FROM user WHERE id = %s", (user_id,))
        user = cursor.fetchone()

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        flash('Error fetching user data.', 'danger')
        return redirect(url_for('users_page'))
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1234',
            database='wind_wave_direction'
        )
        cursor = connection.cursor()

        # Delete query
        cursor.execute("DELETE FROM user WHERE id = %s", (user_id,))
        connection.commit()
        flash('User deleted successfully!', 'success')

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        flash('Error deleting user.', 'danger')
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('users_page'))


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
