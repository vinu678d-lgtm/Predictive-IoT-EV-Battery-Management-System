import sqlite3
import csv
from datetime import datetime


DB_NAME = "battery_data.db"

last_logged_alert = None
last_logged_state = None
last_logged_risk_level = None


def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS battery_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            voltage REAL,
            current REAL,
            power REAL,
            soc REAL,
            temperature REAL,
            temp_rate REAL,
            predicted_temp REAL,
            fan_speed REAL,
            thermal_state TEXT,
            alert TEXT,
            cooling_status TEXT,
            battery_status TEXT,
            risk_score REAL,
            risk_level TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            thermal_state TEXT,
            alert TEXT,
            temperature REAL,
            predicted_temp REAL,
            fan_speed REAL,
            risk_score REAL,
            risk_level TEXT
        )
    """)

    # Add new columns safely if database already exists
    try:
        cursor.execute(
            "ALTER TABLE battery_data ADD COLUMN risk_score REAL"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE battery_data ADD COLUMN risk_level TEXT"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE events ADD COLUMN risk_score REAL"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE events ADD COLUMN risk_level TEXT"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    print("Battery database ready.")


def insert_battery_data(data):
    global last_logged_alert
    global last_logged_state
    global last_logged_risk_level

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO battery_data (
            timestamp,
            voltage,
            current,
            power,
            soc,
            temperature,
            temp_rate,
            predicted_temp,
            fan_speed,
            thermal_state,
            alert,
            cooling_status,
            battery_status,
            risk_score,
            risk_level
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        data["voltage"],
        data["current"],
        data["power"],
        data["soc"],
        data["temperature"],
        data["temp_rate"],
        data["predicted_temp"],
        data["fan_speed"],
        data["thermal_state"],
        data["alert"],
        data["cooling_status"],
        data["battery_status"],
        data.get("risk_score", 0),
        data.get("risk_level", "LOW")
    ))

    current_alert = data["alert"]
    current_state = data["thermal_state"]
    current_risk_level = data.get("risk_level", "LOW")

    important_change = (
        current_alert != last_logged_alert
        or current_state != last_logged_state
        or current_risk_level != last_logged_risk_level
    )

    should_log = (
        important_change
        and (
            current_alert != "NONE"
            or current_state in ["HIGH", "CRITICAL"]
            or current_risk_level in ["MODERATE", "HIGH", "CRITICAL"]
        )
    )

    if should_log:
        cursor.execute("""
            INSERT INTO events (
                timestamp,
                thermal_state,
                alert,
                temperature,
                predicted_temp,
                fan_speed,
                risk_score,
                risk_level
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            current_state,
            current_alert,
            data["temperature"],
            data["predicted_temp"],
            data["fan_speed"],
            data.get("risk_score", 0),
            current_risk_level
        ))

    last_logged_alert = current_alert
    last_logged_state = current_state
    last_logged_risk_level = current_risk_level

    conn.commit()
    conn.close()


def get_recent_data(limit=100):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM battery_data
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    data = [dict(row) for row in rows]

    # Reverse so graphs display oldest → newest
    data.reverse()

    return data


def get_recent_events(limit=20):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def export_csv(filename="battery_report.csv"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            timestamp,
            voltage,
            current,
            power,
            soc,
            temperature,
            temp_rate,
            predicted_temp,
            fan_speed,
            thermal_state,
            alert,
            cooling_status,
            battery_status,
            risk_score,
            risk_level
        FROM battery_data
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    headers = [
        "Timestamp",
        "Voltage (V)",
        "Current (A)",
        "Power (W)",
        "SOC (%)",
        "Temperature (°C)",
        "Temperature Rise Rate (°C/min)",
        "Predicted Temperature (°C)",
        "Fan Speed (%)",
        "Thermal State",
        "Alert",
        "Cooling Status",
        "Battery Status",
        "Risk Score",
        "Risk Level"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    return filename


if __name__ == "__main__":
    create_database()