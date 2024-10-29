import requests
import mysql.connector
from mysql.connector import Error
from datetime import datetime

def get_wind_data(latitude, longitude):
    url = f'https://barmmdrr.com/connect/gmarine_api?latitude={latitude}&longitude={longitude}&hourly=wind_wave_height,wind_wave_direction,wind_wave_period,wind_wave_peak_period'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print(f"[DEBUG] API Response Data: {data}")
        
                # Check the hourly data specifically
        hourly_data = data.get('hourly', {})
        timestamps = hourly_data.get('time', [])
        wind_heights = hourly_data.get('wind_wave_height', [])
        wind_directions = hourly_data.get('wind_wave_direction', [])
        wind_periods = hourly_data.get('wind_wave_period', [])
        wind_peak_periods = hourly_data.get('wind_wave_peak_period', [])

        # Debugging prints for wind data
        print(f"[DEBUG] Wind Heights: {wind_heights}")
        print(f"[DEBUG] Wind Directions: {wind_directions}")
        print(f"[DEBUG] Wind Periods: {wind_periods}")
        print(f"[DEBUG] Wind Peak Periods: {wind_peak_periods}")

        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='root1234',
                database='wind_wave_direction'
            )
            if connection.is_connected():
                print("[DEBUG] Connected to the database.")

            cursor = connection.cursor()

            # Insert location if not present
            insert_location_query = '''
            INSERT INTO locations (latitude, longitude) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE location_id=LAST_INSERT_ID(location_id);
            '''
            cursor.execute(insert_location_query, (latitude, longitude))

            # Fetch the location_id
            cursor.execute('''SELECT location_id FROM locations WHERE latitude = %s AND longitude = %s''', (latitude, longitude))
            location_id = cursor.fetchone()
            if location_id:
                location_id = location_id[0]  # Extract the ID from the tuple
            else:
                print("[ERROR] Location ID retrieval failed after insertion.")
                return False

            # Store hourly wind wave data
            hourly_data = data.get('hourly', {})
            timestamps = hourly_data.get('time', [])
            wind_heights = hourly_data.get('wind_wave_height', [])
            wind_directions = hourly_data.get('wind_wave_direction', [])
            wind_periods = hourly_data.get('wind_wave_period', [])
            wind_peak_periods = hourly_data.get('wind_wave_peak_period', [])

            if not timestamps or not wind_heights or not wind_directions or not wind_periods:
                print("[ERROR] Insufficient hourly data found in the API response.")
                return False

            try:
                for i in range(len(timestamps)):
                    timestamp = datetime.strptime(timestamps[i], '%Y-%m-%dT%H:%M')
                    wind_height = wind_heights[i]
                    wind_direction = wind_directions[i]
                    wind_period = wind_periods[i]
                    wind_peak_period = wind_peak_periods[i] if i < len(wind_peak_periods) else None

                    # Replace "NA" with None
                    if wind_peak_period == "None":
                        wind_peak_period = None

                    print(f"[DEBUG] Inserting hourly data: {timestamp}, {wind_height}, {wind_direction}, {wind_period}, {wind_peak_period}")
                    insert_hourly_query = '''
                    INSERT INTO hourly_wind_wave (location_id, time, wind_wave_height, wind_wave_direction, wind_wave_period, wind_wave_peak_period)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    '''
                    cursor.execute(insert_hourly_query, (location_id, timestamp, wind_height, wind_direction, wind_period, wind_peak_period))

                print(f"[DEBUG] Successfully inserted hourly wind wave data for location ID {location_id}.")
            except Error as e:
                print(f"[ERROR] Error inserting hourly wind wave data: {e}")
                return False
            
            # Store current wind wave data
            current_height = wind_heights[0] if wind_heights else None
            current_direction = wind_directions[0] if wind_directions else None
            current_period = wind_periods[0] if wind_periods else None
            current_peak_period = wind_peak_periods[0] if wind_peak_periods else None

            # Replace "NA" with None
            if current_peak_period == "No":
                current_peak_period = None

            print(f"[DEBUG] Inserting current data: {timestamps[0]}, {current_height}, {current_direction}, {current_period}, {current_peak_period}")
            insert_current_query = '''
            INSERT INTO current_wind_wave (location_id, time, wind_wave_height, wind_wave_direction, wind_wave_period, wind_wave_peak_period)
            VALUES (%s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(insert_current_query, (location_id, timestamps[0], current_height, current_direction, current_period, current_peak_period))

            connection.commit()
            return True  # Indicate successful operation

        except Error as e:
            print(f"[ERROR] Database error: {e}")
            return False

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    else:
        print(f"[ERROR] API request failed with status: {response.status_code}")
        return False

