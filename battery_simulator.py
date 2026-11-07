import random
import time

# ==========================================
# EV BATTERY INTELLIGENCE SYSTEM
# Realistic Software Prototype - Stage 1
# ==========================================

soc = 95.0
temperature = 28.0
previous_temperature = temperature
ambient_temperature = 26.0

print("=" * 60)
print("      EV BATTERY INTELLIGENCE SYSTEM")
print("      EDGE BATTERY DIGITAL PROTOTYPE")
print("=" * 60)

while True:

    # --------------------------------------
    # 1. SIMULATED BATTERY LOAD
    # --------------------------------------
    current = random.uniform(0.5, 3.0)

    # --------------------------------------
    # 2. BATTERY SOC DISCHARGE
    # Accelerated for demonstration
    # --------------------------------------
    soc -= current * 0.015
    soc = max(0, soc)

    # Approximate 3S battery voltage from SOC
    voltage = 9.6 + (soc / 100.0) * 3.0

    # Small voltage drop under load
    voltage -= current * 0.04

    # --------------------------------------
    # 3. BATTERY POWER
    # --------------------------------------
    power = voltage * current

    # --------------------------------------
    # 4. ADAPTIVE FAN CONTROL
    # --------------------------------------
    if temperature < 30:
        fan_speed = 0
        thermal_state = "NORMAL"

    elif temperature < 35:
        fan_speed = 30
        thermal_state = "WARM"

    elif temperature < 40:
        fan_speed = 60
        thermal_state = "COOLING"

    elif temperature < 45:
        fan_speed = 85
        thermal_state = "HIGH"

    else:
        fan_speed = 100
        thermal_state = "CRITICAL"

    # --------------------------------------
    # 5. THERMAL MODEL
    # Higher current generates more heat
    # Fan removes heat
    # --------------------------------------
    heat_generated = (current ** 2) * 0.025
    cooling = (fan_speed / 100.0) * 0.18

    # Natural cooling toward ambient temperature
    natural_cooling = (temperature - ambient_temperature) * 0.01

    temperature += heat_generated
    temperature -= cooling
    temperature -= natural_cooling

    # Small sensor noise
    temperature += random.uniform(-0.03, 0.03)

    # --------------------------------------
    # 6. TEMPERATURE RATE OF CHANGE
    # --------------------------------------
    temp_rate = (temperature - previous_temperature) * 30
    previous_temperature = temperature

    # °C/min because simulation updates every 2 sec

    # --------------------------------------
    # 7. SIMPLE TEMPERATURE PREDICTION
    # --------------------------------------
    predicted_temp_5min = temperature + (temp_rate * 5)

    # Limit unrealistic demonstration prediction
    predicted_temp_5min = max(
        ambient_temperature,
        min(60, predicted_temp_5min)
    )

    # --------------------------------------
    # 8. PREDICTIVE FAN BOOST
    # --------------------------------------
    predictive_alert = "NONE"

    if temp_rate > 0.5 and fan_speed < 100:
        fan_speed = min(100, fan_speed + 20)
        predictive_alert = "RAPID TEMP RISE"

    if predicted_temp_5min >= 45:
        predictive_alert = "THERMAL RISK"

    # --------------------------------------
    # 9. DISPLAY DATA
    # --------------------------------------
    print("\n" + "-" * 60)
    print("BATTERY TELEMETRY")
    print("-" * 60)

    print(f"Voltage             : {voltage:6.2f} V")
    print(f"Current             : {current:6.2f} A")
    print(f"Power               : {power:6.2f} W")
    print(f"SOC                 : {soc:6.1f} %")

    print()
    print("THERMAL MANAGEMENT")
    print("-" * 60)

    print(f"Temperature         : {temperature:6.2f} °C")
    print(f"Temperature Rate    : {temp_rate:+6.2f} °C/min")
    print(f"Predicted Temp 5min : {predicted_temp_5min:6.2f} °C")
    print(f"Thermal State       : {thermal_state}")
    print(f"Fan Speed           : {fan_speed}%")
    print(f"Predictive Alert    : {predictive_alert}")

    if soc <= 20:
        print("WARNING             : LOW BATTERY")

    if temperature >= 45:
        print("WARNING             : HIGH TEMPERATURE")

    print("-" * 60)

    if soc <= 0:
        print("\nBATTERY DEPLETED - SIMULATION STOPPED")
        break

    time.sleep(2)