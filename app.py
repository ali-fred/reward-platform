from flask import Flask, request, redirect, session
import sqlite3
import time
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

DB = "database.db"
ADMIN_USER = "admin"
# =========================
# INIT DATABASE
# =========================


def init_db():

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # USERS TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT,
        balance REAL DEFAULT 0,
        wallet TEXT DEFAULT '',
        referral_code TEXT,
        referred_by TEXT
    )
    """)

    # ADS TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        link TEXT,
        reward REAL DEFAULT 0.003,
        duration INTEGER DEFAULT 15,
        advertiser TEXT
    )
    """)

    # WATCHED ADS
    c.execute("""
    CREATE TABLE IF NOT EXISTS watched_ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        ad_id INTEGER,
        timestamp REAL
    )
    """)

    # AD VIEWS
    c.execute("""
    CREATE TABLE IF NOT EXISTS ad_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        ad_id INTEGER,
        start_time REAL
    )
    """)

    # WITHDRAWALS
    c.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        amount REAL,
        wallet TEXT,
        status TEXT DEFAULT 'pending',
        timestamp REAL
    )
    """)

    # INSERT DEMO AD
    c.execute("SELECT COUNT(*) FROM ads")

    if c.fetchone()[0] == 0:

        c.execute(
            "INSERT INTO ads (title, link, reward, advertiser) VALUES (?,?,?,?)",
            ("Demo Ad", "https://google.com", 0.003, "admin")
        )

    conn.commit()
    conn.close()


init_db()

def admin_required(func):
    def wrapper(*args, **kwargs):

        if 'user' not in session or session['user'] != ADMIN_USER:
            return "Access denied"

        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__

    return wrapper

# =========================
# HOME
# =========================
@app.route('/')
def home():
    return redirect('/login')


# =========================
# REGISTER
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        hashed_password = generate_password_hash(password)      
        password = request.form['password']
        referred_by = request.form.get('referral')

        # CREATE USER REFERRAL CODE
        referral_code = username.upper() + "123"

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        # FIND SPONSOR
        bonus_user = None

        if referred_by:

            c.execute(
                "SELECT username FROM users WHERE referral_code=?",
                (referred_by,)
            )

            sponsor = c.fetchone()

            if sponsor:
                bonus_user = sponsor[0]

        try:

            # CREATE ACCOUNT
            c.execute("""
            INSERT INTO users
            (username, email, password, referral_code, referred_by)
            VALUES (?,?,?,?,?)
            """, (
                username,
                email,
                hashed_password,
                referral_code,
                referred_by
            ))

            conn.commit()

            # REFERRAL BONUS
            if bonus_user:

                c.execute(
                    "UPDATE users SET balance = balance + 0.01 WHERE username=?",
                    (bonus_user,)
                )

                conn.commit()

        except:
            return "User already exists"

        conn.close()

        return redirect('/login')

    return """
    <html>

    <head>

        <style>

            body{
                font-family: Arial;
                background:#f4f4f4;
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
                margin:0;
            }

            .card{
                background:white;
                padding:30px;
                width:320px;
                border-radius:12px;
                box-shadow:0 0 10px rgba(0,0,0,0.1);
            }

            h2{
                text-align:center;
            }

            input{
                width:100%;
                padding:10px;
                margin-top:5px;
                margin-bottom:15px;
                border-radius:8px;
                border:1px solid #ccc;
            }

            button{
                width:100%;
                padding:12px;
                background:#007bff;
                color:white;
                border:none;
                border-radius:8px;
                font-size:16px;
            }

            a{
                text-decoration:none;
            }

        </style>

    </head>

    <body>

        <div class='card'>

            <h2>Create Account</h2>

            <form method='POST'>

                <label>Username</label>
                <input name='username' required>

                <label>Email</label>
                <input name='email' required>

                <label>Password</label>
                <input type='password' name='password' required>

                <label>Invitation Code (optional)</label>
                <input name='referral'>

                <button type='submit'>
                Register
                </button>

            </form>

            <br>

            <center>
            <a href='/login'>
            Already have account? Login
            </a>
            </center>

        </div>

    </body>

    </html>
    """
# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("""
        SELECT * FROM users
        WHERE username=?
        """, (username,))

        user = c.fetchone()

        conn.close()

        if user:

            stored_password = user[3]

            # HASHED PASSWORD
            if stored_password.startswith('scrypt:'):

                if check_password_hash(
                    stored_password,
                    password
                ):

                    session['user'] = username

                    return redirect('/dashboard')

            # OLD PASSWORD
            else:

                if stored_password == password:

                    session['user'] = username

                    return redirect('/dashboard')

        return "Wrong login"

    return """
    <h2>Login</h2>

    <form method='POST'>

        <label>Username</label><br>
        <input name='username'><br><br>

        <label>Password</label><br>
        <input type='password' name='password'><br><br>

        <button type='submit'>
        Login
        </button>

    </form>

    <br>

    <a href='/register'>
    Create Account
    </a>
    """
# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT balance, wallet, referral_code
    FROM users
    WHERE username=?
    """, (session['user'],))

    user = c.fetchone()

    balance = round(user[0], 3)
    wallet = user[1]
    referral_code = user[2]

    conn.close()

    return f"""
    <html>

    <head>

        <style>

            body{{
                font-family:Arial;
                background:#f4f4f4;
                margin:0;
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
            }}

            .card{{
                background:white;
                width:340px;
                padding:30px;
                border-radius:15px;
                box-shadow:0 0 15px rgba(0,0,0,0.1);
                text-align:center;
            }}

            h1{{
                margin-top:0;
            }}

            .balance{{
                color:green;
                font-size:22px;
                margin-bottom:20px;
            }}

            .ref{{
                background:#f1f1f1;
                padding:10px;
                border-radius:8px;
                margin-bottom:20px;
                font-size:14px;
            }}

            a{{
                display:block;
                text-decoration:none;
                background:#007bff;
                color:white;
                padding:12px;
                border-radius:8px;
                margin-bottom:10px;
                font-size:16px;
            }}

            a:hover{{
                background:#0056b3;
            }}

            .wallet{{
                font-size:12px;
                color:gray;
                margin-bottom:20px;
            }}

        </style>

    </head>

    <body>

        <div class='card'>

            <h1>Welcome {session['user']}</h1>

            <div class='balance'>
                {balance} USDT
            </div>

            <div class='ref'>
                <strong>Your Invitation Code:</strong><br>
                {referral_code}
            </div>

            <div class='wallet'>
                Wallet: {wallet}
            </div>

            <a href='/ads'>
            Publicités
            </a>

            <a href='/create_ad'>
            Create Ad
            </a>

            <a href='/withdraw'>
            Withdraw
            </a>

            <a href='/wallet'>
            Wallet & Referral
            </a>

            <a href='/admin'>
            Admin Panel
            </a>

            <a href='/logout'>
            Logout
            </a>

        </div>

    </body>

    </html>
    """
# =========================
# CREATE AD
# =========================
@app.route('/create_ad', methods=['GET', 'POST'])
def create_ad():

    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':

        title = request.form.get('title')
        link = request.form.get('link')
        reward = request.form.get('reward')

        # 🧠 VALIDATION (IMPORTANT)
        if not title or not link or not reward:
            return "All fields required"

        try:
            reward = float(reward)
        except:
            return "Invalid reward value"

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute(
            "INSERT INTO ads (title, link, reward, advertiser) VALUES (?,?,?,?)",
            (title, link, reward, session['user'])
        )

        conn.commit()
        conn.close()

        return redirect('/ads')

    return """
    <h2>Create Advertisement</h2>

    <form method="POST">

        <input name="title" placeholder="Ad Title" required><br><br>

        <input name="link" placeholder="Ad Link" required><br><br>

        <input name="reward" placeholder="Reward" required><br><br>

        <button type="submit">Publish</button>

    </form>
    """
# =========================
# ADS PAGE
# =========================
@app.route('/ads')
def ads():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM ads")

    ads = c.fetchall()

    conn.close()

    html = "<h2>Available Ads</h2>"

    for ad in ads:

        html += f"""
        <p>

        <strong>{ad[1]}</strong><br><br>

        Reward: {ad[3]} USDT<br><br>

        <a href='{ad[2]}' target='_blank'>
        Visit Sponsor
        </a><br><br>

        <a href='/watch/{ad[0]}'>
        Watch Ad
        </a>

        </p>

        <hr>
        """

    return html


# =========================
# WATCH AD
# =========================
@app.route('/watch/<int:ad_id>')
def watch(ad_id):

    if 'user' not in session:
        return redirect('/login')

    username = session['user']

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # SAVE START TIME
    c.execute(
        """
        INSERT INTO ad_views
        (username, ad_id, start_time)
        VALUES (?,?,?)
        """,
        (username, ad_id, time.time())
    )

    conn.commit()
    conn.close()

    return f"""

    <html>

    <head>

        <style>

            body{{
                font-family:Arial;
                background:#f4f4f4;
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
                margin:0;
            }}

            .card{{
                background:white;
                padding:30px;
                border-radius:15px;
                width:320px;
                text-align:center;
                box-shadow:0 0 15px rgba(0,0,0,0.1);
            }}

        </style>

    </head>

    <body>

        <div class='card'>

            <h2>Watching Ad...</h2>

            <p>
            Please wait 15 seconds
            to earn reward
            </p>

        </div>

        <script>

            setTimeout(function(){{
                window.location.href='/claim/{ad_id}';
            }}, 15000);

        </script>

    </body>

    </html>
    """

# =========================
# CLAIM REWARD
# =========================

@app.route('/claim/<int:ad_id>')
def claim(ad_id):

    if 'user' not in session:
        return redirect('/login')

    username = session['user']

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # GET LAST WATCH
    c.execute("""
        SELECT start_time FROM ad_views
        WHERE username=? AND ad_id=?
        ORDER BY id DESC LIMIT 1
    """, (username, ad_id))

    data = c.fetchone()

    if not data:
        conn.close()
        return "No watch found"

    start_time = data[0]

    # MUST WAIT 15 SECONDS
    if time.time() - start_time < 15:
        conn.close()
        return "Too fast"

    # CHECK LAST REWARD
    c.execute("""
        SELECT timestamp FROM watched_ads
        WHERE username=? AND ad_id=?
        ORDER BY id DESC LIMIT 1
    """, (username, ad_id))

    reward_data = c.fetchone()

    # WAIT 15 SEC BEFORE NEXT REWARD
    if reward_data:

        last_reward = reward_data[0]

        if time.time() - last_reward < 15:

            conn.close()

            return """
            <script>
            alert('Wait 15 seconds before earning again');
            window.location.href='/ads';
            </script>
            """

    # GET REWARD
    c.execute(
        "SELECT reward FROM ads WHERE id=?",
        (ad_id,)
    )

    ad = c.fetchone()

    if ad:

        reward = ad[0]

        # UPDATE BALANCE
        c.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE username=?
        """, (reward, username))

        # SAVE WATCH
        c.execute("""
            INSERT INTO watched_ads
            (username, ad_id, timestamp)
            VALUES (?,?,?)
        """, (
            username,
            ad_id,
            time.time()
        ))

        conn.commit()

    conn.close()

    return redirect('/dashboard')

@app.route('/wallet', methods=['GET', 'POST'])
def wallet():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # SAVE WALLET
    if request.method == 'POST':

        wallet = request.form['wallet']

        c.execute("""
        UPDATE users
        SET wallet=?
        WHERE username=?
        """, (wallet, session['user']))

        conn.commit()

    # GET USER DATA
    c.execute("""
    SELECT wallet, referral_code
    FROM users
    WHERE username=?
    """, (session['user'],))

    data = c.fetchone()

    conn.close()

    return f"""

    <html>

    <head>

        <style>

            body{{
                font-family:Arial;
                background:#f4f4f4;
                margin:0;
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
            }}

            .card{{
                background:white;
                width:340px;
                padding:30px;
                border-radius:15px;
                box-shadow:0 0 15px rgba(0,0,0,0.1);
                text-align:center;
            }}

            h2{{
                margin-top:0;
            }}

            input{{
                width:90%;
                padding:12px;
                border:1px solid #ccc;
                border-radius:8px;
                margin-bottom:15px;
            }}

            button{{
                background:#007bff;
                color:white;
                border:none;
                padding:12px;
                width:100%;
                border-radius:8px;
                font-size:16px;
            }}

            button:hover{{
                background:#0056b3;
            }}

            .ref{{
                background:#f1f1f1;
                padding:10px;
                border-radius:8px;
                margin-bottom:20px;
            }}

            a{{
                display:block;
                margin-top:20px;
                text-decoration:none;
                color:#007bff;
            }}

        </style>

    </head>

    <body>

        <div class='card'>

            <h2>Wallet Settings</h2>

            <div class='ref'>

                <strong>Your Referral Code</strong><br><br>

                {data[1]}

            </div>

            <form method='POST'>

                <label>
                USDT Wallet (TRC20)
                </label><br><br>

                <input
                name='wallet'
                value='{data[0]}'
                placeholder='Enter your USDT wallet'
                >

                <button type='submit'>
                Save Wallet
                </button>

            </form>

            <a href='/dashboard'>
            Back Dashboard
            </a>

        </div>

    </body>

    </html>
    """


@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():

    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':

        amount = request.form.get('amount')
        wallet = request.form.get('wallet')

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        # get balance
        c.execute("SELECT balance FROM users WHERE username=?",
                  (session['user'],))

        balance = c.fetchone()[0]

        amount = float(amount)

        if amount <= 0:
            return "Invalid amount"

        if amount > balance:
            return "Insufficient balance"

        # create request
        c.execute("""
            INSERT INTO withdrawals (username, amount, wallet, timestamp)
            VALUES (?,?,?,?)
        """, (session['user'], amount, wallet, time.time()))

        conn.commit()
        conn.close()

        return "Withdrawal request sent"

    return """
    <h2>Withdraw USDT</h2>

    <form method='POST'>

        <label>Amount</label><br>
        <input name='amount'><br><br>

        <label>USDT Wallet (TRC20)</label><br>
        <input name='wallet'><br><br>

        <button type='submit'>Request Withdraw</button>

    </form>
    """
@app.route('/admin')
def admin():

    if 'user' not in session:
        return redirect('/login')

    if session['user'] != 'admin':
        return "Access denied"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # TOTAL USERS
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    # TOTAL ADS
    c.execute("SELECT COUNT(*) FROM ads")
    total_ads = c.fetchone()[0]

    # TOTAL WITHDRAWALS
    c.execute("SELECT COUNT(*) FROM withdrawals")
    total_withdraws = c.fetchone()[0]

    # PENDING
    c.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
    pending = c.fetchone()[0]

    conn.close()

    return f"""
    <html>

    <head>

        <style>

            body{{
                font-family:Arial;
                background:#f4f4f4;
                margin:0;
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
            }}

            .card{{
                background:white;
                width:350px;
                padding:30px;
                border-radius:15px;
                box-shadow:0 0 15px rgba(0,0,0,0.1);
                text-align:center;
            }}

            h1{{
                margin-top:0;
            }}

            .box{{
                background:#f1f1f1;
                padding:15px;
                margin-bottom:15px;
                border-radius:10px;
                font-size:18px;
            }}

            a{{
                display:block;
                text-decoration:none;
                background:#007bff;
                color:white;
                padding:12px;
                border-radius:8px;
                margin-bottom:10px;
            }}

        </style>

    </head>

    <body>

        <div class='card'>

            <h1>Admin Panel</h1>

            <div class='box'>
                Users: {total_users}
            </div>

            <div class='box'>
                Ads: {total_ads}
            </div>

            <div class='box'>
                Withdrawals: {total_withdraws}
            </div>

            <div class='box'>
                Pending: {pending}
            </div>

            <a href='/admin/withdrawals'>
            Manage Withdrawals
            </a>

            <a href='/dashboard'>
            Back Dashboard
            </a>

        </div>

    </body>

    </html>
    """

@app.route('/admin/withdrawals')
def admin_withdrawals():

    if 'user' not in session:
        return redirect('/login')

    if session['user'] != 'admin':
        return "Access denied"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT id, username, amount, wallet, status
    FROM withdrawals
    ORDER BY id DESC
    """)

    withdrawals = c.fetchall()

    conn.close()

    html = """
    <h1>Withdraw Requests</h1>
    """

    for w in withdrawals:

        html += f"""

        <div style='
        background:#f4f4f4;
        padding:15px;
        margin:15px;
        border-radius:10px;
        '>

        <strong>User:</strong> {w[1]}<br><br>

        <strong>Amount:</strong> {w[2]} USDT<br><br>

        <strong>Wallet:</strong> {w[3]}<br><br>

        <strong>Status:</strong> {w[4]}<br><br>

        <a href='/approve/{w[0]}'>
        Approve
        </a>

        </div>
        """

    return html

@app.route('/approve/<int:id>')
def approve(id):

    if 'user' not in session:
        return redirect('/login')

    if session['user'] != 'admin':
        return "Access denied"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    UPDATE withdrawals
    SET status='approved'
    WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/admin/withdrawals')

# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')


# =========================
# RUN APP
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
