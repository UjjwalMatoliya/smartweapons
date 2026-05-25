import os
from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)

# Database location
if os.environ.get('RENDER'):
    DB_NAME = '/tmp/tracker.db'
else:
    DB_NAME = 'tracker.db'

# Create database at startup
def init_db():
    db_path = DB_NAME
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create device_data table
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
    
    # Create commands table
    c.execute('''CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT,
        command TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print(f"Database created: {db_path}")

# Initialize immediately
init_db()

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/upload', methods=['POST'])
def upload_data():
    try:
        data = request.json
        print(f"Data received: {data}")
        
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
             data.get('operator')))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/command')
def get_command():
    device_id = request.args.get('device_id', 'tracker_001')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT command FROM commands WHERE device_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1", (device_id,))
    result = c.fetchone()
    
    if result:
        c.execute("UPDATE commands SET status = 'sent' WHERE device_id = ? AND status = 'pending'", (device_id,))
        conn.commit()
        conn.close()
        return result[0]
    
    conn.close()
    return "NONE"

@app.route('/set_command', methods=['POST'])
def set_command():
    data = request.json
    device_id = data.get('device_id', 'tracker_001')
    command = data.get('command', 'RELAY_OFF')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("UPDATE commands SET status = 'cancelled' WHERE device_id = ? AND status = 'pending'", (device_id,))
    c.execute("INSERT INTO commands (device_id, command) VALUES (?, ?)", (device_id, command))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})

@app.route('/get_latest')
def get_latest():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM device_data ORDER BY timestamp DESC LIMIT 1")
        columns = [d[0] for d in c.description]
        result = c.fetchone()
        conn.close()
        
        if result:
            return jsonify(dict(zip(columns, result)))
        return jsonify({})
    except Exception as e:
        print(f"Error get_latest: {e}")
        return jsonify({})

@app.route('/get_history')
def get_history():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT lat, lng, timestamp FROM device_data WHERE lat > 0 ORDER BY timestamp DESC LIMIT 100")
        results = c.fetchall()
        conn.close()
        return jsonify([{"lat": r[0], "lng": r[1], "time": r[2]} for r in results])
    except Exception as e:
        print(f"Error get_history: {e}")
        return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
