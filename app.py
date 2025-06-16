import os
import sqlite3
from flask import Flask, request, render_template_string
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_NAME = 'gps_data.db'

LANDING_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Asset Tracker Home</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
  body {
    background: linear-gradient(to right, #f0f4f8, #d9e2ec);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    margin: 0;
  }
  .card {
    width: 95%;
    max-width: 900px;
    padding: 80px 60px;
    border-radius: 24px;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
    background-color: #ffffff;
    text-align: center;
  }
  h1 {
    font-weight: 700;
    margin-bottom: 50px;
    color: #2c3e50;
    font-size: 2.5rem;
  }
  .btn-lg {
    width: 260px;
    font-size: 1.1rem;
    padding: 14px 20px;
  }
  .btn + .btn {
    margin-left: 20px;
  }
  @media (max-width: 576px) {
    .btn-lg {
      width: 100%;
      margin-bottom: 15px;
    }
    .btn + .btn {
      margin-left: 0;
    }
  }
</style>

</head>
<body>
  <div class="card">
    <h1>📡 GPS Asset Tracker</h1>
    <div class="d-flex flex-wrap justify-content-center">
      <a href="/tracker" class="btn btn-primary btn-lg mb-2">
        Device Status
      </a>
      <a href="/region-search" class="btn btn-outline-secondary btn-lg mb-2">
        Region Search
      </a>
    </div>
  </div>
</body>
</html>
"""



TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GPS Tracker</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
  <style>body { padding-top: 10px; } .container { max-width: 900px; }</style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-light">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">🏠 HOME</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item">
          <a class="nav-link" href="/tracker">📡 Asset Tracker</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/region-search">🌍 Region Search</a>
        </li>
      </ul>
    </div>
  </div>
</nav>
<div class="container">

  <h2>📡 ASSET TRACKER</h2>
  <style>body { padding-top: 10px; } </style>
  <form method="post" enctype="multipart/form-data" class="mb-4">
    <label class="form-label">Upload CSV File</label>
    <input class="form-control" type="file" name="file" accept=".csv" required>
    <button class="btn btn-primary mt-2" type="submit">Upload</button>
  </form>

  {% if upload_success %}
    <div class="alert alert-success">✅ CSV file uploaded and data imported successfully.</div>
  {% endif %}

  <form method="post" class="mb-4">
    <label class="form-label">Device ID</label>
    <input type="text" class="form-control" name="device" required>
    <label class="form-label mt-2">From Date</label>
    <input type="text" class="form-control datepicker" name="from_date" placeholder="dd/mm/yyyy" required>
    <label class="form-label mt-2">To Date</label>
    <input type="text" class="form-control datepicker" name="to_date" placeholder="dd/mm/yyyy" required>
    <button class="btn btn-success mt-3" type="submit">Search</button>
  </form>

  {% if result %}
    <div class="alert alert-info">
      <h5>📊 Results</h5>
      <p><strong>Device:</strong> {{ result['device'] }}</p>
      {% if result['region'] %}
        <p><strong>Region:</strong> {{ result['region'] }}</p>
        <p><strong>Branch:</strong> {{ result['branch'] }}</p>
      {% endif %}
      <p><strong>From Date:</strong> {{ result['from_date'] }}</p>
      <p><strong>To Date:</strong> {{ result['to_date'] }}</p>
      <p><strong>Total Pings:</strong> {{ result['pings'] }}</p>
      <p><strong>Total Charges:</strong> {{ result['charges'] }}</p>
    </div>
  {% endif %}

  {% if ping_chart %}
    <div class="mb-4">
      <h6>📈 Ping Count by Date</h6>
      {{ ping_chart | safe }}
    </div>
  {% endif %}

  {% if charge_chart %}
    <div class="mb-4">
      <h6>🔋 Charge Events by Date</h6>
      {{ charge_chart | safe }}
    </div>
  {% endif %}
</div>

<script>
  flatpickr(".datepicker", {
    dateFormat: "d/m/Y"
  });
</script>
</body>
</html>
"""
REGION_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Region Search</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>body { padding-top: 10px; }</style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-light">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">🏠 HOME</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item">
          <a class="nav-link" href="/tracker">📡 Asset Tracker</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/region-search">🌍 Region Search</a>
        </li>
      </ul>
    </div>
  </div>
</nav>
<div class="container">

  <h2>🌍 Region Search</h2>
  <style>body { padding-top: 10px; } </style>
  <form method="post" enctype="multipart/form-data" class="mb-4">
    <label class="form-label">Upload Region Data File</label>
    <input class="form-control" type="file" name="file" accept=".csv" required>
    <button class="btn btn-primary mt-2" type="submit">Upload</button>
  </form>

  {% if upload_success %}
    <div class="alert alert-success">✅ File uploaded and device info imported successfully.</div>
  {% endif %}

  <div class="mb-3">
    <label class="form-label">Select Region</label>
    <select class="form-select" id="region-select" onchange="updateBranches()">
      <option value="">-- Select Region --</option>
    </select>
  </div>
 
  <div class="mb-3">
   
    <div id="branch-count" class="fw-bold text-primary"></div>
  </div>


  <div class="mb-3">
    <label class="form-label">Select Branch</label>
    <select class="form-select" id="branch-select" onchange="updateDevices()">
      <option value="">-- Select Branch --</option>
    </select>
  </div>

  <div class="mb-3">
    <label class="form-label">Devices in Selected Branch</label>
    <ul class="list-group" id="device-list"></ul>
  </div>
</div>

<script>
 
  const data = {{ data|tojson }};
  const regionSelect = document.getElementById('region-select');
  const branchSelect = document.getElementById('branch-select');
  const deviceList = document.getElementById('device-list');

  const regions = [...new Set(data.map(item => item.region))];
  regions.forEach(region => {
    const option = document.createElement('option');
    option.value = region;
    option.text = region;
    regionSelect.appendChild(option);
  });

  function updateBranches() {
  branchSelect.innerHTML = '<option value="">-- Select Branch --</option>';
  deviceList.innerHTML = '';
  document.getElementById('branch-count').textContent = '';

  const selectedRegion = regionSelect.value;
  const branches = [...new Set(data.filter(item => item.region === selectedRegion).map(item => item.branch))];

  branches.forEach(branch => {
    const option = document.createElement('option');
    option.value = branch;
    option.text = branch;
    branchSelect.appendChild(option);
  });

  // 👇 Show branch count
  document.getElementById('branch-count').textContent = `${branches.length} branches found`;
}

  function updateDevices() {
    deviceList.innerHTML = '';
    const selectedRegion = regionSelect.value;
    const selectedBranch = branchSelect.value;
    const filtered = data.filter(item => item.region === selectedRegion && item.branch === selectedBranch);

    if (filtered.length === 0) {
      const li = document.createElement('li');
      li.className = 'list-group-item text-muted';
      li.textContent = 'No devices found.';
      deviceList.appendChild(li);
    } else {
      filtered.forEach(item => {
        const li = document.createElement('li');
        li.className = 'list-group-item';
        li.textContent = `Device: ${item.device} | SIM Type: ${item.sim_type || 'N/A'}`;
        deviceList.appendChild(li);
      });
    }
  }
</script>
</body>
</html>

"""


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS gps_data')
    c.execute('''
        CREATE TABLE gps_data (
            sl_no INTEGER,
            device TEXT,
            event TEXT,
            tracking_date TEXT,
            battery_voltage REAL
        )
    ''')
    conn.commit()
    conn.close()

def init_device_info_table():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS device_info (
            device TEXT PRIMARY KEY,
            region TEXT,
            branch TEXT,
            sim_type TEXT
        )
    ''')
    conn.commit()
    conn.close()


def import_device_info(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    required = ['device_id', 'region', 'branch', 'sim_type']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in metadata: {missing}")

    df = df[required]
    df.rename(columns={'device_id': 'device'}, inplace=True)
    df.dropna(subset=['device'], inplace=True)

    conn = sqlite3.connect(DB_NAME)
    df.to_sql('device_info', conn, if_exists='replace', index=False)
    conn.close()


def detect_charges(df, rise_threshold=0.15, window=3):
    df = df.sort_values('tracking_date').reset_index(drop=True)
    voltages = df['battery_voltage'].tolist()
    charge_dates = []
    i = 0
    while i < len(voltages) - window:
        start_voltage = voltages[i]
        end_voltage = voltages[i + window]
        if pd.notna(start_voltage) and pd.notna(end_voltage) and end_voltage - start_voltage >= rise_threshold:
            charge_dates.append(df.loc[i + window, 'tracking_date'].date())
            i += window
        else:
            i += 1
    return len(charge_dates), pd.Series(charge_dates)

def create_bar_chart(series, title):
    counts = series.value_counts().sort_index()
    fig = go.Figure(data=[
        go.Bar(
            x=counts.index.astype(str),
            y=counts.values,
            text=counts.values,
            textposition='auto',
            hovertemplate='Date: %{x}<br>Count: %{y}<extra></extra>',
            marker_color='mediumseagreen'
        )
    ])
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Count",
        margin=dict(l=30, r=30, t=50, b=70),
        height=400
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

def import_csv(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    column_mapping = {'sl._no': 'sl_no', 'event_type': 'event'}
    df.rename(columns=column_mapping, inplace=True)

    required = ['sl_no', 'device', 'event', 'tracking_date', 'battery_voltage']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[required]
    df['event'] = df['event'].astype(str).str.strip().str.upper()
    df['tracking_date'] = pd.to_datetime(df['tracking_date'], dayfirst=True, errors='coerce')
    df['battery_voltage'] = pd.to_numeric(df['battery_voltage'], errors='coerce')
    df.dropna(subset=['tracking_date', 'battery_voltage', 'device'], inplace=True)

    conn = sqlite3.connect(DB_NAME)
    df.to_sql('gps_data', conn, if_exists='append', index=False)
    conn.close()

@app.route('/')
def landing():
    return render_template_string(LANDING_TEMPLATE)

@app.route('/tracker', methods=['GET', 'POST'])
def tracker():
    result = None
    ping_chart = None
    charge_chart = None
    upload_success = False

    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)

            try:
                df_preview = pd.read_csv(file_path, nrows=5)
                cols = df_preview.columns.str.lower().str.replace(' ', '_')
                if set(['device_id', 'region', 'branch']).issubset(cols):
                    init_device_info_table()
                    import_device_info(file_path)
                else:
                    init_db()
                    import_csv(file_path)
                upload_success = True
            except Exception as e:
                return f"<h3>Error: {str(e)}</h3>"

    elif all(k in request.form for k in ('device', 'from_date', 'to_date')):
        device = request.form['device'].strip()
        from_date_raw = request.form['from_date']
        to_date_raw = request.form['to_date']
        try:
            from_date = pd.to_datetime(from_date_raw, dayfirst=True).strftime('%Y-%m-%d')
            to_date = pd.to_datetime(to_date_raw, dayfirst=True).strftime('%Y-%m-%d')
        except Exception as e:
            return f"<h3>Invalid date format: {str(e)}</h3>"

        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query('''
            SELECT * FROM gps_data
            WHERE device = ?
              AND DATE(tracking_date) BETWEEN DATE(?) AND DATE(?)
            ORDER BY tracking_date
        ''', conn, params=(device, from_date, to_date))

        cur = conn.cursor()
        cur.execute('SELECT region, branch FROM device_info WHERE device = ?', (device,))
        info = cur.fetchone()
        conn.close()

        if not df.empty:
            df['event'] = df['event'].astype(str).str.strip().str.upper()
            df['tracking_date'] = pd.to_datetime(df['tracking_date'], errors='coerce')

            pings = df[df['event'].isin(['G_PING', 'REBOOT'])]
            ping_dates = pings['tracking_date'].dt.date

            charges, charge_dates = detect_charges(df)

            result = {
                'device': device,
                'from_date': from_date_raw,
                'to_date': to_date_raw,
                'pings': len(ping_dates),
                'charges': charges
            }

            if info:
                result['region'] = info[0]
                result['branch'] = info[1]

            if not ping_dates.empty:
                ping_chart = create_bar_chart(ping_dates, "Ping Count by Date")
            if not charge_dates.empty:
                charge_chart = create_bar_chart(charge_dates, "Charge Events by Date")

    return render_template_string(
        TEMPLATE,
        result=result,
        ping_chart=ping_chart,
        charge_chart=charge_chart,
        upload_success=upload_success
    )
   


@app.route('/region-search', methods=['GET', 'POST'])
def region_search():
    upload_success = False
    device_data = []

    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            try:
                file_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(file_path)
                init_device_info_table()
                import_device_info(file_path)
                upload_success = True
            except Exception as e:
                return f"<h3>Error uploading device info file: {str(e)}</h3>"

    # Load device_info for dropdowns
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT * FROM device_info', conn)
    conn.close()

    return render_template_string(REGION_TEMPLATE, upload_success=upload_success, data=df.to_dict(orient='records'))
if __name__ == '__main__':
    app.run(debug=True)

