from flask import Flask, render_template, jsonify, send_file, request
import random
import time
from collections import deque

from database import (
    create_database,
    insert_battery_data,
    get_recent_data,
    get_recent_events,
    export_csv
)

app = Flask(__name__)


# =========================================================
# BATTERY STATE
# =========================================================

battery = {
    "soc": 95.0,
    "temperature": 28.0
}


manual_mode = {
    "enabled": False,
    "temperature": 28.0,
    "current": 1.5
}


heating_test = {
    "enabled": False,
    "current": 3.0,
    "start_temperature": 30.0,
    "target_temperature": 48.0,
    "heating_rate": 0.03
}


temperature_history = deque(maxlen=10)

last_update = time.time()


# =========================================================
# BATTERY HEALTH TRACKING
# =========================================================
#
# This is currently an ESTIMATED / SIMULATED SOH model.
#
# Later, when the real battery and sensors are connected,
# these values can be calculated from real current,
# temperature and charge/discharge history.
# =========================================================

battery_health = {
    "nominal_capacity_ah": 2.0,

    # Total simulated discharged capacity
    "cumulative_discharge_ah": 0.0,

    # Accumulated exposure above 35°C
    "thermal_stress": 0.0,

    # Accumulated exposure above 3 A
    "current_stress": 0.0
}


# =========================================================
# BATTERY RISK INTELLIGENCE ENGINE
# =========================================================

def calculate_risk_score(
    temperature,
    predicted_temp,
    temp_rate,
    current,
    soc
):
    risk_score = 0.0

    # Actual temperature risk
    if temperature >= 45:
        risk_score += 30
    elif temperature >= 40:
        risk_score += 24
    elif temperature >= 35:
        risk_score += 16
    elif temperature >= 30:
        risk_score += 8

    # Predicted temperature risk
    if predicted_temp >= 45:
        risk_score += 25
    elif predicted_temp >= 40:
        risk_score += 20
    elif predicted_temp >= 37:
        risk_score += 12
    elif predicted_temp >= 33:
        risk_score += 6

    # Temperature rise-rate risk
    if temp_rate >= 1.5:
        risk_score += 20
    elif temp_rate >= 1.0:
        risk_score += 16
    elif temp_rate >= 0.5:
        risk_score += 10
    elif temp_rate >= 0.2:
        risk_score += 5

    # Current/load risk
    if current >= 4.5:
        risk_score += 15
    elif current >= 3.5:
        risk_score += 11
    elif current >= 2.5:
        risk_score += 7
    elif current >= 1.5:
        risk_score += 3

    # Low SOC risk
    if soc <= 10:
        risk_score += 10
    elif soc <= 20:
        risk_score += 7
    elif soc <= 30:
        risk_score += 4

    risk_score = max(
        0,
        min(100, risk_score)
    )

    if risk_score < 25:
        risk_level = "LOW"

    elif risk_score < 50:
        risk_level = "MODERATE"

    elif risk_score < 75:
        risk_level = "HIGH"

    else:
        risk_level = "CRITICAL"

    return round(risk_score, 1), risk_level


# =========================================================
# BATTERY HEALTH / SOH ANALYTICS ENGINE
# =========================================================

def update_health_tracking(
    current,
    temperature,
    dt
):
    """
    Tracks simulated battery usage.

    Current is treated as discharge current because the
    present simulator models battery discharge only.
    """

    # Convert current over time into Ah discharged
    discharged_ah = current * dt / 3600.0

    battery_health["cumulative_discharge_ah"] += discharged_ah


    # Thermal stress accumulation
    #
    # Only temperature above 35°C contributes to
    # accelerated degradation in this simplified model.
    if temperature > 35:

        temperature_excess = (
            temperature - 35
        )

        battery_health["thermal_stress"] += (
            temperature_excess
            * dt
            / 3600.0
        )


    # High-current stress accumulation
    #
    # Loads above 3 A contribute additional stress.
    if current > 3:

        current_excess = (
            current - 3
        )

        battery_health["current_stress"] += (
            current_excess
            * dt
            / 3600.0
        )


def calculate_battery_health():
    """
    Estimates battery State of Health using:

    1. Equivalent discharge cycles
    2. Thermal stress
    3. High-current stress

    This is an engineering simulation model,
    not laboratory-measured SOH.
    """

    nominal_capacity = (
        battery_health["nominal_capacity_ah"]
    )

    cumulative_discharge = (
        battery_health["cumulative_discharge_ah"]
    )

    thermal_stress = (
        battery_health["thermal_stress"]
    )

    current_stress = (
        battery_health["current_stress"]
    )


    # -----------------------------------------------------
    # Equivalent cycles
    # -----------------------------------------------------

    if nominal_capacity > 0:

        equivalent_cycles = (
            cumulative_discharge
            / nominal_capacity
        )

    else:

        equivalent_cycles = 0.0


    # -----------------------------------------------------
    # Cycle degradation
    #
    # Approximate simulation:
    # 0.04 % SOH loss per equivalent cycle
    #
    # 100 cycles -> approximately 4 % loss
    # -----------------------------------------------------

    cycle_degradation = (
        equivalent_cycles * 0.04
    )


    # -----------------------------------------------------
    # Thermal degradation
    #
    # Increased accumulated high-temperature exposure
    # increases estimated degradation.
    # -----------------------------------------------------

    thermal_degradation = (
        thermal_stress * 0.03
    )


    # -----------------------------------------------------
    # High-current degradation
    # -----------------------------------------------------

    current_degradation = (
        current_stress * 0.02
    )


    # -----------------------------------------------------
    # Total degradation index
    # -----------------------------------------------------

    degradation_index = (
        cycle_degradation
        + thermal_degradation
        + current_degradation
    )


    degradation_index = max(
        0.0,
        min(40.0, degradation_index)
    )


    # -----------------------------------------------------
    # STATE OF HEALTH
    # -----------------------------------------------------

    soh = (
        100.0
        - degradation_index
    )


    soh = max(
        60.0,
        min(100.0, soh)
    )


    # -----------------------------------------------------
    # Estimated usable battery capacity
    # -----------------------------------------------------

    estimated_capacity = (
        nominal_capacity
        * soh
        / 100.0
    )


    # -----------------------------------------------------
    # Battery health classification
    # -----------------------------------------------------

    if soh >= 90:

        health_status = "EXCELLENT"

    elif soh >= 80:

        health_status = "GOOD"

    elif soh >= 70:

        health_status = "AGED"

    else:

        health_status = "DEGRADED"


    return {
        "soh": round(soh, 2),

        "estimated_capacity_ah": round(
            estimated_capacity,
            3
        ),

        "nominal_capacity_ah": round(
            nominal_capacity,
            3
        ),

        "degradation_index": round(
            degradation_index,
            3
        ),

        "equivalent_cycles": round(
            equivalent_cycles,
            4
        ),

        "health_status": health_status,

        "cumulative_discharge_ah": round(
            cumulative_discharge,
            4
        )
    }


# =========================================================
# BATTERY UPDATE
# =========================================================

def update_battery():
    global last_update

    current_time = time.time()

    dt = (
        current_time
        - last_update
    )

    dt = max(
        0.1,
        min(dt, 5.0)
    )

    last_update = current_time


    # =====================================================
    # CURRENT SELECTION
    # =====================================================

    if heating_test["enabled"]:

        current = heating_test["current"]

    elif manual_mode["enabled"]:

        current = manual_mode["current"]

    else:

        current = random.uniform(
            0.5,
            3.0
        )


    # =====================================================
    # SOC
    # =====================================================

    battery["soc"] -= (
        current
        * 0.003
        * dt
    )


    if battery["soc"] <= 5:

        battery["soc"] = 95.0


    soc = battery["soc"]


    # =====================================================
    # VOLTAGE
    # =====================================================

    voltage = (
        9.6
        + (soc / 100.0) * 3.0
        - current * 0.04
    )


    voltage += random.uniform(
        -0.02,
        0.02
    )


    voltage = max(
        9.0,
        voltage
    )


    # =====================================================
    # POWER
    # =====================================================

    power = (
        voltage
        * current
    )


    # =====================================================
    # TEMPERATURE
    # =====================================================

    if heating_test["enabled"]:

        battery["temperature"] += (
            heating_test["heating_rate"]
            * dt
        )


        if (
            battery["temperature"]
            >= heating_test["target_temperature"]
        ):

            battery["temperature"] = (
                heating_test["target_temperature"]
            )


    elif manual_mode["enabled"]:

        battery["temperature"] = (
            manual_mode["temperature"]
        )


    else:

        heat_generation = (
            current ** 2
        ) * 0.018


        natural_cooling = (
            battery["temperature"]
            - 26.0
        ) * 0.012


        noise = random.uniform(
            -0.015,
            0.015
        )


        battery["temperature"] += (
            heat_generation
            - natural_cooling
            + noise
        ) * dt


    battery["temperature"] = max(
        20.0,
        min(
            battery["temperature"],
            55.0
        )
    )


    temperature = (
        battery["temperature"]
    )


    # =====================================================
    # TEMPERATURE HISTORY
    # =====================================================

    temperature_history.append(
        (
            current_time,
            temperature
        )
    )


    # =====================================================
    # TEMPERATURE RISE RATE
    # =====================================================

    temp_rate = 0.0


    if len(
        temperature_history
    ) >= 2:

        oldest_time, oldest_temp = (
            temperature_history[0]
        )

        newest_time, newest_temp = (
            temperature_history[-1]
        )


        elapsed_seconds = (
            newest_time
            - oldest_time
        )


        if elapsed_seconds > 0:

            temp_rate = (
                (
                    newest_temp
                    - oldest_temp
                )
                / elapsed_seconds
            ) * 60.0


    temp_rate = round(
        temp_rate,
        2
    )


    # =====================================================
    # 5-MINUTE TEMPERATURE PREDICTION
    # =====================================================

    predicted_temp = (
        temperature
        + temp_rate * 5
    )


    predicted_temp = max(
        20.0,
        min(
            predicted_temp,
            55.0
        )
    )


    # =====================================================
    # THERMAL STATE
    # =====================================================

    if temperature < 30:

        thermal_state = "NORMAL"

        fan_speed = 0


    elif temperature < 35:

        thermal_state = "WARM"

        fan_speed = 30


    elif temperature < 40:

        thermal_state = "COOLING"

        fan_speed = 60


    elif temperature < 45:

        thermal_state = "HIGH"

        fan_speed = 85


    else:

        thermal_state = "CRITICAL"

        fan_speed = 100


    # =====================================================
    # PREDICTIVE ALERT
    # =====================================================

    alert = "NONE"


    if temp_rate > 0.20:

        alert = "TEMP RISING"

        fan_speed = max(
            fan_speed,
            20
        )


    if temp_rate > 0.50:

        alert = "RAPID TEMP RISE"

        fan_speed = max(
            fan_speed,
            40
        )


    if predicted_temp >= 40:

        alert = "PREDICTED HEATING"

        fan_speed = max(
            fan_speed,
            60
        )


    if predicted_temp >= 45:

        alert = "THERMAL RISK"

        fan_speed = max(
            fan_speed,
            85
        )


    if temperature >= 45:

        alert = "CRITICAL TEMPERATURE"

        fan_speed = 100


    # =====================================================
    # BATTERY STATUS
    # =====================================================

    if soc <= 10:

        battery_status = (
            "CRITICAL BATTERY"
        )


    elif soc <= 20:

        battery_status = (
            "LOW BATTERY"
        )


    else:

        battery_status = (
            "NORMAL"
        )


    # =====================================================
    # RISK INTELLIGENCE ENGINE
    # =====================================================

    risk_score, risk_level = (
        calculate_risk_score(
            temperature,
            predicted_temp,
            temp_rate,
            current,
            soc
        )
    )


    # =====================================================
    # RISK-BASED COOLING
    # =====================================================

    if risk_level == "MODERATE":

        fan_speed = max(
            fan_speed,
            30
        )


    elif risk_level == "HIGH":

        fan_speed = max(
            fan_speed,
            70
        )


    elif risk_level == "CRITICAL":

        fan_speed = 100


    # =====================================================
    # BATTERY HEALTH TRACKING
    # =====================================================

    update_health_tracking(
        current,
        temperature,
        dt
    )


    health_data = (
        calculate_battery_health()
    )


    # =====================================================
    # COOLING STATUS
    # =====================================================

    if fan_speed > 0:

        cooling_status = "ACTIVE"

    else:

        cooling_status = "STANDBY"


    # =====================================================
    # API DATA
    # =====================================================

    return {
        "voltage": round(
            voltage,
            2
        ),

        "current": round(
            current,
            2
        ),

        "power": round(
            power,
            2
        ),

        "soc": round(
            soc,
            1
        ),

        "temperature": round(
            temperature,
            2
        ),

        "temp_rate": round(
            temp_rate,
            2
        ),

        "predicted_temp": round(
            predicted_temp,
            2
        ),

        "fan_speed": round(
            fan_speed,
            0
        ),

        "thermal_state": (
            thermal_state
        ),

        "alert": alert,

        "cooling_status": (
            cooling_status
        ),

        "battery_status": (
            battery_status
        ),


        # Risk Intelligence
        "risk_score": (
            risk_score
        ),

        "risk_level": (
            risk_level
        ),


        # Battery Health / SOH
        "soh": (
            health_data["soh"]
        ),

        "estimated_capacity_ah": (
            health_data[
                "estimated_capacity_ah"
            ]
        ),

        "nominal_capacity_ah": (
            health_data[
                "nominal_capacity_ah"
            ]
        ),

        "degradation_index": (
            health_data[
                "degradation_index"
            ]
        ),

        "equivalent_cycles": (
            health_data[
                "equivalent_cycles"
            ]
        ),

        "health_status": (
            health_data[
                "health_status"
            ]
        ),

        "cumulative_discharge_ah": (
            health_data[
                "cumulative_discharge_ah"
            ]
        ),


        # Operating modes
        "manual_mode": (
            manual_mode["enabled"]
        ),

        "heating_test": (
            heating_test["enabled"]
        )
    }


# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def dashboard():

    return render_template(
        "dashboard.html"
    )


@app.route("/api/data")
def data():

    battery_data = (
        update_battery()
    )

    insert_battery_data(
        battery_data
    )

    return jsonify(
        battery_data
    )


@app.route("/api/history")
def history():

    return jsonify(
        get_recent_data(100)
    )


@app.route("/api/events")
def events():

    return jsonify(
        get_recent_events(20)
    )


# =========================================================
# MANUAL MODE
# =========================================================

@app.route("/api/manual/<state>")
def manual_control(state):

    if state == "on":

        heating_test["enabled"] = False

        manual_mode["enabled"] = True

        temperature_history.clear()


    elif state == "off":

        manual_mode["enabled"] = False

        temperature_history.clear()


    return jsonify({
        "manual_mode": (
            manual_mode["enabled"]
        ),

        "temperature": (
            manual_mode["temperature"]
        ),

        "current": (
            manual_mode["current"]
        )
    })


@app.route(
    "/api/manual/set",
    methods=["POST"]
)
def manual_set():

    data = request.get_json()


    if not data:

        return jsonify({
            "error": "No data received"
        }), 400


    if "temperature" in data:

        temperature = float(
            data["temperature"]
        )


        temperature = max(
            20.0,
            min(
                60.0,
                temperature
            )
        )


        manual_mode[
            "temperature"
        ] = temperature


        battery[
            "temperature"
        ] = temperature


    if "current" in data:

        current = float(
            data["current"]
        )


        current = max(
            0.0,
            min(
                5.0,
                current
            )
        )


        manual_mode[
            "current"
        ] = current


    temperature_history.clear()


    return jsonify({
        "success": True,

        "temperature": (
            manual_mode[
                "temperature"
            ]
        ),

        "current": (
            manual_mode[
                "current"
            ]
        )
    })


@app.route("/api/manual/status")
def manual_status():

    return jsonify({
        "enabled": (
            manual_mode["enabled"]
        ),

        "temperature": (
            manual_mode[
                "temperature"
            ]
        ),

        "current": (
            manual_mode[
                "current"
            ]
        ),

        "heating_test": (
            heating_test["enabled"]
        )
    })


# =========================================================
# HEATING TEST
# =========================================================

@app.route("/api/heating/start")
def start_heating_test():

    manual_mode["enabled"] = False

    heating_test["enabled"] = True


    battery["temperature"] = (
        heating_test[
            "start_temperature"
        ]
    )


    temperature_history.clear()


    return jsonify({
        "success": True,

        "heating_test": True,

        "start_temperature": (
            heating_test[
                "start_temperature"
            ]
        ),

        "target_temperature": (
            heating_test[
                "target_temperature"
            ]
        )
    })


@app.route("/api/heating/stop")
def stop_heating_test():

    heating_test["enabled"] = False

    temperature_history.clear()


    return jsonify({
        "success": True,

        "heating_test": False
    })


# =========================================================
# RESET SYSTEM
# =========================================================

@app.route("/api/reset")
def reset_system():

    manual_mode["enabled"] = False

    heating_test["enabled"] = False

    battery["temperature"] = 28.0

    battery["soc"] = 95.0

    temperature_history.clear()


    return jsonify({
        "success": True,

        "mode": "AUTO"
    })


# =========================================================
# DOWNLOAD CSV
# =========================================================

@app.route("/download")
def download_report():

    filename = export_csv(
        "battery_report.csv"
    )


    return send_file(
        filename,
        as_attachment=True
    )


# =========================================================
# START APPLICATION
# =========================================================

create_database()


if __name__ == "__main__":

    app.run(debug=True)