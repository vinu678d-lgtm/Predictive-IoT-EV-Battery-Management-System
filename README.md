# Predictive IoT-Based EV Battery Management System with Adaptive Thermal Control

ECE final-year project at HKBK College of Engineering, Bengaluru.

## Overview
This repository contains a **Python/Flask battery-monitoring dashboard and simulation**, SQLite database helper, and Proteus simulation project. It demonstrates battery monitoring, health and risk metrics, temperature forecasting logic, and adaptive cooling behavior.

> **Implementation note:** The uploaded `app.py` and `battery_simulator.py` generate simulated battery values. Physical Raspberry Pi 3 Model B+ sensor acquisition and fan-driving scripts were not present in the supplied archive. Add any separate hardware-control code before documenting full end-to-end hardware integration here.

## Repository contents
- `app.py` — Flask dashboard and REST endpoints
- `database.py` — SQLite data storage and CSV export
- `battery_simulator.py` — standalone simulated battery readings and fan-control example
- `templates/dashboard.html` — dashboard interface
- `Proteus_Simulation/` — Proteus project file
- `images/` — add actual photos and screenshots here

## Run the Flask dashboard (development)
Requires Python 3 and pip.

```bash
python -m venv .venv
```

On Windows:
```cmd
.venv\Scripts\activate
```

On Raspberry Pi/Linux:
```bash
source .venv/bin/activate
```

Install and launch:
```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` on the same computer. `app.py` currently runs with Flask debug mode enabled, so do **not** expose the development server to the public internet.

## Hardware and project demonstration
The completed college project used a Raspberry Pi 3 Model B+. Add your tested hardware-component list, wiring diagram, prototype photographs, dashboard screenshots, and any separate Raspberry Pi sensor/fan scripts here.

## Testing and results
Add measured test readings, screenshots, and what was verified on actual hardware. Distinguish experimental measurements from simulated data.

## Credits
Add your project team, supervisor, and the responsibilities of each contributor after confirming publication permissions.

## Note
Do not commit private credentials, raw personal data, or unreviewed database exports.
