from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, date
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "mindbloom.db"

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn=db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'personnel',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS checkins(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        checkin_date TEXT NOT NULL,
        mood TEXT NOT NULL,
        factors TEXT,
        sleep TEXT,
        energy TEXT,
        fatigue TEXT,
        support TEXT,
        status TEXT NOT NULL,
        score INTEGER NOT NULL,
        recommendation TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS activities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        duration TEXT NOT NULL,
        description TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS activity_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        activity_id INTEGER NOT NULL,
        completed_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(activity_id) REFERENCES activities(id)
    );
    """)
    seed=[
      ("2-Minute Breathing Reset","Breathing","2 min","Slow your breathing and release accumulated tension."),
      ("Guided Recovery Pause","Recovery","5 min","Take a short pause to reset attention and physical tension."),
      ("Mindful Walk","Movement","10 min","Walk without multitasking and notice your surroundings."),
      ("Sleep Wind-Down","Sleep","8 min","Reduce stimulation and prepare your body for rest."),
      ("Write 3 Positive Thoughts","Mindfulness","5 min","Write three things that went reasonably well today.")
    ]
    if conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]==0:
        conn.executemany("INSERT INTO activities(title,category,duration,description) VALUES(?,?,?,?)",seed)
    # Demo accounts
    if not conn.execute("SELECT 1 FROM users WHERE email=?",("personnel@mindbloom.local",)).fetchone():
        conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                     ("Demo Personnel","personnel@mindbloom.local",generate_password_hash("demo123"),"personnel",datetime.now().isoformat()))
    if not conn.execute("SELECT 1 FROM users WHERE email=?",("welfare@mindbloom.local",)).fetchone():
        conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                     ("Welfare Officer","welfare@mindbloom.local",generate_password_hash("demo123"),"welfare",datetime.now().isoformat()))
    conn.commit(); conn.close()

def current_user():
    uid=session.get("user_id")
    if not uid:return None
    conn=db(); u=conn.execute("SELECT id,name,email,role FROM users WHERE id=?",(uid,)).fetchone(); conn.close()
    return u

def score_checkin(data):
    mood={"Very Low":4,"Low":3,"Okay":2,"Good":1,"Very Good":0}.get(data.get("mood"),2)
    factors=set(data.get("factors") or [])
    factor_points=sum(2 for x in ["Workload","Duty pressure","Lack of sleep","Team/colleague pressure","Family concerns","Personal concerns","Financial concerns","Physical fatigue"] if x in factors)
    sleep={"7–8h":0,"6–7h":1,"5–6h":2,"<5h":3}.get(data.get("sleep"),0)
    energy={"Good":0,"Okay":1,"Low":2}.get(data.get("energy"),0)
    fatigue={"Low":0,"Moderate":1,"High":2}.get(data.get("fatigue"),0)
    support={"Yes":0,"Maybe":1,"No":2,"Prefer not to say":0}.get(data.get("support"),0)
    raw=min(100, mood*12 + factor_points*4 + sleep*8 + energy*7 + fatigue*7 + support*5)
    if raw < 30: status="Normal"
    elif raw < 60: status="Attention"
    else: status="Concern"
    rec=[]
    if "Lack of sleep" in factors or sleep>=2: rec.append("Try the Sleep Wind-Down activity.")
    if "Workload" in factors or "Duty pressure" in factors: rec.append("Take a 2-minute breathing reset between tasks.")
    if "Physical fatigue" in factors or fatigue>=1: rec.append("Use a short recovery pause or mindful walk.")
    if "Family concerns" in factors or "Personal concerns" in factors: rec.append("Consider speaking with someone you trust or an approved welfare/support professional.")
    if not rec:
        rec=["Keep your routine steady and complete one short wellness activity today."]
    return raw,status," ".join(rec)

def recommended_tasks(data):
    factors=set(data.get("factors") or [])
    tasks=[]
    if data.get("mood") in ("Very Low","Low"):
        tasks.append({"title":"2-Minute Breathing Reset","reason":"Your mood is lower today. A short breathing pause may help you slow down and reset.","activity_id":1})
    if "Workload" in factors or "Duty pressure" in factors:
        tasks.append({"title":"Guided Recovery Pause","reason":"You reported work or duty pressure. Take a short recovery break before your next task.","activity_id":2})
    if "Lack of sleep" in factors or data.get("sleep") in ("5–6h","<5h"):
        tasks.append({"title":"Sleep Wind-Down","reason":"Your recovery may benefit from a calmer wind-down routine before sleep.","activity_id":4})
    if "Physical fatigue" in factors or data.get("fatigue") in ("Moderate","High"):
        tasks.append({"title":"Mindful Walk","reason":"You reported physical fatigue. A gentle movement break can help you reset.","activity_id":3})
    if "Family concerns" in factors or "Personal concerns" in factors:
        tasks.append({"title":"Talk to Someone You Trust","reason":"You mentioned a personal or family concern. Connecting with a trusted person can reduce the feeling of carrying it alone.","activity_id":None})
    if "Financial concerns" in factors:
        tasks.append({"title":"Take a Financial Stress Pause","reason":"Write down the one financial issue you can act on next, then leave the rest for a planned time.","activity_id":None})
    if "Team/colleague pressure" in factors:
        tasks.append({"title":"Reset Before the Next Interaction","reason":"Take two quiet minutes before the next difficult conversation or team interaction.","activity_id":1})
    if data.get("support")=="No":
        tasks.append({"title":"Reach Out for Support","reason":"You said you may not have someone to talk to. Consider Tele-MANAS or your approved welfare/support pathway.","activity_id":None})
    # Keep dashboard concise and unique.
    seen=set(); unique=[]
    for t in tasks:
        if t["title"] not in seen:
            seen.add(t["title"]); unique.append(t)
    return unique[:5]

HELPLINES = [
    {"category":"Immediate emergency","name":"Emergency Response Support System","number":"112","description":"Police, fire and emergency medical assistance across India.","type":"emergency"},
    {"category":"Mental wellbeing","name":"Tele-MANAS","number":"14416","description":"Government mental-health support and counselling. Toll-free: 1800-89-14416.","type":"mental"},
    {"category":"Children & family","name":"Child Helpline","number":"1098","description":"24x7 support for children in distress or at risk under Mission Vatsalya.","type":"child"},
    {"category":"Women & safety","name":"Women Helpline","number":"181","description":"24x7 support for women in distress, including linkage to relevant services.","type":"women"},
    {"category":"Senior citizens","name":"Elderline","number":"14567","description":"Government support for senior citizens, including information, emotional support and protection from abuse.","type":"senior"},
    {"category":"Cyber crime","name":"Cyber Crime Helpline","number":"1930","description":"24x7 reporting/support for cyber financial fraud and cybercrime.","type":"cyber"},
    {"category":"Substance support","name":"National De-addiction Helpline","number":"1800-11-0031","description":"Government helpline for de-addiction support.","type":"deaddiction"},
    {"category":"Student safety","name":"National Anti-Ragging Helpline","number":"1800-180-5522","description":"Support for students facing ragging or harassment in educational institutions.","type":"education"},
    {"category":"Travel support","name":"Indian Railways","number":"139","description":"Railway enquiry, assistance and grievance support.","type":"rail"},
    {"category":"Medical emergency","name":"National Ambulance Service","number":"102","description":"Ambulance/emergency medical assistance.","type":"medical"},
    {"category":"Fire emergency","name":"Fire Services","number":"101","description":"Fire emergency assistance.","type":"fire"}
]

@app.route("/")
def index(): return render_template("index.html")

@app.post("/api/register")
def register():
    data=request.get_json() or {}
    name=data.get("name","").strip(); email=data.get("email","").strip().lower(); password=data.get("password","")
    if not name or not email or len(password)<6:return jsonify(error="Name, email and a 6+ character password are required."),400
    conn=db()
    try:
        cur=conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                         (name,email,generate_password_hash(password),"personnel",datetime.now().isoformat()))
        conn.commit(); uid=cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close(); return jsonify(error="An account with this email already exists."),409
    conn.close(); session["user_id"]=uid
    return jsonify(ok=True,user={"id":uid,"name":name,"email":email,"role":"personnel"})

@app.post("/api/login")
def login():
    data=request.get_json() or {}
    email=data.get("email","").strip().lower(); password=data.get("password","")
    conn=db(); u=conn.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone(); conn.close()
    if not u or not check_password_hash(u["password"],password):return jsonify(error="Invalid email or password."),401
    session["user_id"]=u["id"]
    return jsonify(ok=True,user={"id":u["id"],"name":u["name"],"email":u["email"],"role":u["role"]})

@app.post("/api/logout")
def logout(): session.clear(); return jsonify(ok=True)

@app.get("/api/me")
def me():
    u=current_user()
    return jsonify(user=dict(u) if u else None)

@app.post("/api/checkins")
def create_checkin():
    u=current_user()
    if not u:return jsonify(error="Login required."),401
    data=request.get_json() or {}
    if not data.get("mood"):return jsonify(error="Please select how you are feeling."),400
    score,status,rec=score_checkin(data)
    now=datetime.now().isoformat()
    conn=db()
    conn.execute("""INSERT INTO checkins(user_id,checkin_date,mood,factors,sleep,energy,fatigue,support,status,score,recommendation,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (u["id"],date.today().isoformat(),data["mood"],", ".join(data.get("factors") or []),
                  data.get("sleep",""),data.get("energy",""),data.get("fatigue",""),data.get("support",""),
                  status,score,rec,now))
    conn.commit(); conn.close()
    return jsonify(ok=True,status=status,score=score,recommendation=rec)

@app.get("/api/checkins")
def get_checkins():
    u=current_user()
    if not u:return jsonify(error="Login required."),401
    conn=db(); rows=conn.execute("""SELECT id,checkin_date,mood,factors,sleep,energy,fatigue,support,status,score,recommendation
                                    FROM checkins WHERE user_id=? ORDER BY checkin_date DESC,id DESC""",(u["id"],)).fetchall(); conn.close()
    return jsonify(checkins=[dict(r) for r in rows])

@app.get("/api/dashboard")
def dashboard():
    u=current_user()
    if not u:return jsonify(error="Login required."),401
    conn=db()
    last=conn.execute("SELECT * FROM checkins WHERE user_id=? ORDER BY id DESC LIMIT 1",(u["id"],)).fetchone()
    count=conn.execute("SELECT COUNT(*) c FROM checkins WHERE user_id=?",(u["id"],)).fetchone()["c"]
    completed=conn.execute("SELECT COUNT(*) c FROM activity_logs WHERE user_id=?",(u["id"],)).fetchone()["c"]
    conn.close()
    last_data=dict(last) if last else None
    return jsonify(
        last=last_data,
        checkins=count,
        completed=completed,
        recommended_tasks=recommended_tasks(last_data) if last_data else []
    )

@app.get("/api/resources")
def resources():
    return jsonify(resources=HELPLINES)

@app.get("/api/activities")
def activities():
    conn=db(); rows=conn.execute("SELECT * FROM activities ORDER BY id").fetchall(); conn.close()
    return jsonify(activities=[dict(r) for r in rows])

@app.post("/api/activities/<int:activity_id>/complete")
def complete_activity(activity_id):
    u=current_user()
    if not u:return jsonify(error="Login required."),401
    conn=db()
    if not conn.execute("SELECT 1 FROM activities WHERE id=?",(activity_id,)).fetchone():
        conn.close();return jsonify(error="Activity not found."),404
    conn.execute("INSERT INTO activity_logs(user_id,activity_id,completed_at) VALUES(?,?,?)",
                 (u["id"],activity_id,datetime.now().isoformat()))
    conn.commit();conn.close()
    return jsonify(ok=True)

@app.get("/api/welfare/overview")
def welfare_overview():
    u=current_user()
    if not u or u["role"]!="welfare":return jsonify(error="Welfare access required."),403
    conn=db()
    total=conn.execute("SELECT COUNT(*) c FROM users WHERE role='personnel'").fetchone()["c"]
    rows=conn.execute("""SELECT status,COUNT(*) c FROM checkins
                         WHERE id IN (SELECT MAX(id) FROM checkins GROUP BY user_id)
                         GROUP BY status""").fetchall()
    factors=conn.execute("""SELECT factors FROM checkins
                            WHERE id IN (SELECT MAX(id) FROM checkins GROUP BY user_id)""").fetchall()
    conn.close()
    dist={r["status"]:r["c"] for r in rows}
    counts={}
    for r in factors:
        for f in (r["factors"] or "").split(", "):
            if f: counts[f]=counts.get(f,0)+1
    return jsonify(total=total,stable=dist.get("Normal",0),attention=dist.get("Attention",0),concern=dist.get("Concern",0),
                   factors=sorted(counts.items(),key=lambda x:x[1],reverse=True)[:6])

if __name__=="__main__":
    init_db()
    app.run(debug=True,host="127.0.0.1",port=5000)
