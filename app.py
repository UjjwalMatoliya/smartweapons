"""
Flask Server for GPS Tracker
Save as: app.py
Run: python app.py
"""

from flask import Flask, request, jsonify, render_template
import sqlite3
import time
from datetime import datetime

app = Flask(__name__)
DB_NAME = "tracker.db"

# ==================== DATABASE ====================

def init_db():
    """Create database tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Device Data Table
    c.execute('''CREATE TABLE IF NOT EXISTS device_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT,
        lat REAL,
        lng REAL,
        speed INTEGER,
        battery INTEGER,
        voltage REAL,
        relay TEXT,
        status TEXT,
        gsm_signal INTEGER,
        network TEXT,
        operator TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Commands Table
    c.execute('''CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT,
        command TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("Database initialized!")

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Dashboard Home"""
    return render_template('dashboard.html')

@app.route('/upload', methods=['POST'])
def upload_data():
    """Receive data from device"""
    try:
        data = request.json
        
        print(f"Received data from {data.get('device_id')}")
        print(f"  Lat: {data.get('lat')}, Lng: {data.get('lng')}")
        print(f"  Speed: {data.get('speed')} km/h")
        print(f"  Battery: {data.get('battery')}%")
        print(f"  Relay: {data.get('relay')}")
        
        # Save to database
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute('''INSERT INTO device_data 
            (device_id, lat, lng, speed, battery, voltage, relay, status, gsm_signal, network, operator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (data.get('device_id'),
             data.get('lat'),
             data.get('lng'),
             data.get('speed'),
             data.get('battery'),
             data.get('voltage'),
             data.get('relay'),
             data.get('status'),
             data.get('gsm_signal'),
             data.get('network'),
             data.get('operator'))
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Data saved"})
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/command', methods=['GET'])
def get_command():
    """Device checks for pending commands"""
    device_id = request.args.get('device_id', 'tracker_001')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Get pending command
    c.execute('''SELECT command FROM commands 
        WHERE device_id = ? AND status = 'pending' 
        ORDER BY created_at DESC LIMIT 1''', (device_id,))
    
    result = c.fetchone()
    
    if result:
        # Mark as sent
        c.execute('''UPDATE commands SET status = 'sent' 
            WHERE device_id = ? AND status = 'pending' 
            ORDER BY created_at DESC LIMIT 1''', (device_id,))
        conn.commit()
        conn.close()
        
        return result[0]  # Return command text
    
    conn.close()
    return "NONE"

@app.route('/set_command', methods=['POST'])
def set_command():
    """User sends command from dashboard"""
    data = request.json
    device_id = data.get('device_id', 'tracker_001')
    command = data.get('command', 'RELAY_OFF')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Clear old pending commands
    c.execute("UPDATE commands SET status = 'cancelled' WHERE device_id = ? AND status = 'pending'", (device_id,))
    
    # Insert new command
    c.execute("INSERT INTO commands (device_id, command) VALUES (?, ?)", (device_id, command))
    
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": f"Command {command} sent!"})

@app.route('/get_latest')
def get_latest():
    """Get latest device data for dashboard"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''SELECT * FROM device_data 
        ORDER BY timestamp DESC LIMIT 1''')
    
    columns = [description[0] for description in c.description]
    result = c.fetchone()
    
    conn.close()
    
    if result:
        data = dict(zip(columns, result))
        return jsonify(data)
    
    return jsonify({})

@app.route('/get_history')
def get_history():
    """Get history for map"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''SELECT lat, lng, timestamp FROM device_data 
        WHERE lat > 0 AND lng > 0
        ORDER BY timestamp DESC LIMIT 100''')
    
    results = c.fetchall()
    conn.close()
    
    history = [{"lat": r[0], "lng": r[1], "time": r[2]} for r in results]
    return jsonify(history)

# ==================== MAIN ====================

if __name__ == '__main__':
    init_db()
    print("Server starting on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)