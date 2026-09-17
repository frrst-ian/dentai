from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import sqlite3, os, csv, io, json
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,'dental_ai.db')
app=Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key='dental-ai-demo-change-this-secret'

# Demo/prototype application only. Do not use for real clinical decisions without validation and authorization.

FEATURES=['age','sex','smoking','diabetes','dental_pain','bleeding_gums','caries_count','missing_teeth','oral_hygiene','periodontal_status']
CATS=['sex','smoking','diabetes','dental_pain','bleeding_gums','oral_hygiene','periodontal_status']
NUMS=['age','caries_count','missing_teeth']

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT UNIQUE, name TEXT, age INTEGER, sex TEXT, phone TEXT, address TEXT, smoking TEXT, diabetes TEXT, dental_pain TEXT, bleeding_gums TEXT, caries_count INTEGER, missing_teeth INTEGER, oral_hygiene TEXT, periodontal_status TEXT, status TEXT DEFAULT 'Active', created_at TEXT);
    CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, patient_name TEXT, date TEXT, time TEXT, dentist TEXT, purpose TEXT, status TEXT DEFAULT 'Scheduled');
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT, email TEXT, status TEXT DEFAULT 'Active');
    CREATE TABLE IF NOT EXISTS tooth_records(id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, tooth_no TEXT NOT NULL, status TEXT DEFAULT 'Healthy', notes TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS treatment_records(id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, visit_date TEXT NOT NULL, procedure TEXT NOT NULL, tooth_no TEXT, dentist TEXT, notes TEXT, created_at TEXT);
    ''')
    if c.execute('SELECT COUNT(*) FROM patients').fetchone()[0]==0:
        sample=[('P-001','Juan Dela Cruz',25,'Male','09170000001','Sample Address','No','No','Yes','No',3,0,'Fair','Healthy'),('P-002','Maria Reyes',42,'Female','09170000002','Sample Address','No','No','No','Yes',1,2,'Good','Mild'),('P-003','Carlos Santos',37,'Male','09170000003','Sample Address','Yes','No','Yes','Yes',6,3,'Poor','Moderate'),('P-004','Ana Lopez',29,'Female','09170000004','Sample Address','No','No','No','No',0,0,'Good','Healthy'),('P-005','Pedro Garcia',50,'Male','09170000005','Sample Address','Yes','Yes','Yes','Yes',8,5,'Poor','Severe')]
        for p in sample: c.execute('INSERT INTO patients(patient_id,name,age,sex,phone,address,smoking,diabetes,dental_pain,bleeding_gums,caries_count,missing_teeth,oral_hygiene,periodontal_status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(*p,datetime.now().isoformat()))
    if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0:
        c.executemany('INSERT INTO users(name,role,email) VALUES (?,?,?)',[('Dr. Maria Santos','Dentist','dentist@dentalai.local'),('System Administrator','Administrator','admin@dentalai.local'),('Research Evaluator','Evaluator','evaluator@dentalai.local')])
    c.commit(); c.close()

# Demo training data: clearly synthetic and intended only to make the prototype runnable without patient data.
def synthetic_data(n=700, seed=42):
    rng=np.random.default_rng(seed)
    rows=[]
    for _ in range(n):
        age=int(rng.integers(18,81)); sex=rng.choice(['Male','Female']); smoking=rng.choice(['Yes','No'],p=[.28,.72]); diabetes=rng.choice(['Yes','No'],p=[.18,.82]); pain=rng.choice(['Yes','No'],p=[.42,.58]); bleed=rng.choice(['Yes','No'],p=[.38,.62]); caries=int(rng.poisson(2.5)); missing=int(min(rng.poisson(max(age-35,1)/14),15)); hygiene=rng.choice(['Good','Fair','Poor'],p=[.35,.45,.20]); perio=rng.choice(['Healthy','Mild','Moderate','Severe'],p=[.35,.30,.25,.10]);
        score=0.0
        score += 1.4 if pain=='Yes' else 0
        score += 0.8 if bleed=='Yes' else 0
        score += 0.35*caries + 0.22*missing
        score += {'Good':0,'Fair':.5,'Poor':1.1}[hygiene]
        score += {'Healthy':0,'Mild':.6,'Moderate':1.2,'Severe':1.9}[perio]
        score += .7 if smoking=='Yes' else 0
        score += .8 if diabetes=='Yes' else 0
        score += .3 if age>=60 else 0
        prob=1/(1+np.exp(-(score-3.6)))
        urgent='Urgent' if rng.random()<prob else 'Non-Urgent'
        rows.append([age,sex,smoking,diabetes,pain,bleed,caries,missing,hygiene,perio,urgent])
    return rows

TRAIN=synthetic_data()
X=pd.DataFrame([r[:-1] for r in TRAIN], columns=FEATURES); y=pd.Series([r[-1] for r in TRAIN], name='treatment_urgency')
pre=ColumnTransformer([('num',Pipeline([('imp',SimpleImputer(strategy='median')),('scale',StandardScaler())]),NUMS),('cat',Pipeline([('imp',SimpleImputer(strategy='most_frequent')),('oh',OneHotEncoder(handle_unknown='ignore'))]),CATS)])
models={
 'Logistic Regression':LogisticRegression(max_iter=1000),
 'Decision Tree':DecisionTreeClassifier(max_depth=5,random_state=42),
 'Random Forest':RandomForestClassifier(n_estimators=180,max_depth=8,random_state=42),
 'Support Vector Machine':SVC(probability=True,random_state=42),
 'Gradient Boosting':GradientBoostingClassifier(random_state=42)
}
pipelines={k:Pipeline([('prep',pre),('model',m)]) for k,m in models.items()}
for p in pipelines.values(): p.fit(X,y)
DEFAULT_MODEL='Random Forest'

def risk_payload(data, model_name=DEFAULT_MODEL):
    # Always pass a DataFrame so the ColumnTransformer can safely select
    # named columns (prevents the 'columns using strings ... dataframes' error).
    vals=[data.get(f,'') for f in FEATURES]
    input_df=pd.DataFrame([vals], columns=FEATURES)
    pipe=pipelines.get(model_name,pipelines[DEFAULT_MODEL])
    pred=pipe.predict(input_df)[0]
    proba=float(pipe.predict_proba(input_df)[0][list(pipe.classes_).index(pred)])
    # Simple transparent contribution proxy for the UI; not a validated clinical explanation.
    reasons=[]
    if data.get('dental_pain')=='Yes': reasons.append(('Dental pain','increases urgency signal'))
    if data.get('bleeding_gums')=='Yes': reasons.append(('Bleeding gums','increases urgency signal'))
    if int(data.get('caries_count') or 0)>=4: reasons.append(('Higher caries count','increases urgency signal'))
    if data.get('periodontal_status') in ['Moderate','Severe']: reasons.append(('Periodontal status','increases urgency signal'))
    if data.get('oral_hygiene')=='Poor': reasons.append(('Poor oral hygiene','increases urgency signal'))
    if data.get('diabetes')=='Yes': reasons.append(('Diabetes','included risk factor'))
    return {'prediction':pred,'probability':round(proba*100,1),'model':model_name,'reasons':reasons[:5]}

def model_metrics():
    # Training-set reference only, not final thesis test-set metrics.
    out=[]
    for name,p in pipelines.items():
        pr=p.predict(X); out.append({'model':name,'accuracy':round(accuracy_score(y,pr)*100,1),'precision':round(precision_score(y,pr,pos_label='Urgent')*100,1),'recall':round(recall_score(y,pr,pos_label='Urgent')*100,1),'f1':round(f1_score(y,pr,pos_label='Urgent')*100,1)})
    return out

@app.route('/')
def login(): return render_template('login.html')
@app.route('/login',methods=['POST'])
def do_login(): session['user']=request.form.get('username') or 'Guest'; return redirect(url_for('dashboard'))
@app.route('/dashboard')
def dashboard():
    c=db(); stats={'patients':c.execute('SELECT COUNT(*) FROM patients').fetchone()[0],'appointments':c.execute('SELECT COUNT(*) FROM appointments').fetchone()[0],'users':c.execute('SELECT COUNT(*) FROM users').fetchone()[0]}; recent=c.execute('SELECT * FROM patients ORDER BY id DESC LIMIT 5').fetchall(); c.close(); return render_template('dashboard.html',stats=stats,recent=recent)
@app.route('/patients')
def patients(): c=db(); rows=c.execute('SELECT * FROM patients ORDER BY id DESC').fetchall(); c.close(); return render_template('patients.html',patients=rows)
@app.route('/patients/new',methods=['GET','POST'])
def patient_new():
    if request.method=='POST':
        f=request.form; c=db(); pid=f.get('patient_id') or f"P-{int(datetime.now().timestamp())%100000:05d}"
        c.execute('INSERT INTO patients(patient_id,name,age,sex,phone,address,smoking,diabetes,dental_pain,bleeding_gums,caries_count,missing_teeth,oral_hygiene,periodontal_status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,f.get('name'),int(f.get('age') or 0),f.get('sex'),f.get('phone'),f.get('address'),f.get('smoking'),f.get('diabetes'),f.get('dental_pain'),f.get('bleeding_gums'),int(f.get('caries_count') or 0),int(f.get('missing_teeth') or 0),f.get('oral_hygiene'),f.get('periodontal_status'),datetime.now().isoformat())); c.commit(); c.close(); return redirect(url_for('patients'))
    return render_template('patient_form.html',patient=None)
@app.route('/patients/<int:pid>/edit',methods=['GET','POST'])
def patient_edit(pid):
    c=db(); patient=c.execute('SELECT * FROM patients WHERE id=?',(pid,)).fetchone()
    if request.method=='POST':
        f=request.form; c.execute('UPDATE patients SET name=?,age=?,sex=?,phone=?,address=?,smoking=?,diabetes=?,dental_pain=?,bleeding_gums=?,caries_count=?,missing_teeth=?,oral_hygiene=?,periodontal_status=? WHERE id=?',(f.get('name'),int(f.get('age') or 0),f.get('sex'),f.get('phone'),f.get('address'),f.get('smoking'),f.get('diabetes'),f.get('dental_pain'),f.get('bleeding_gums'),int(f.get('caries_count') or 0),int(f.get('missing_teeth') or 0),f.get('oral_hygiene'),f.get('periodontal_status'),pid)); c.commit(); c.close(); return redirect(url_for('patients'))
    c.close(); return render_template('patient_form.html',patient=patient)

FDI_UPPER=list(range(11,19))+list(range(21,29))
FDI_LOWER=list(range(41,49))+list(range(31,39))
ALL_TEETH=FDI_UPPER+FDI_LOWER
TOOTH_STATUSES=['Healthy','Caries','Filled','Missing','Extracted','Root Canal','Crown','Implant','Impacted']

@app.route('/patients/<int:pid>/chart')
def patient_chart(pid):
    c=db(); patient=c.execute('SELECT * FROM patients WHERE id=?',(pid,)).fetchone()
    if not patient: c.close(); return 'Patient not found',404
    rows=c.execute('SELECT * FROM tooth_records WHERE patient_id=? ORDER BY tooth_no',(patient['patient_id'],)).fetchall()
    records=c.execute('SELECT * FROM treatment_records WHERE patient_id=? ORDER BY visit_date DESC,id DESC',(patient['patient_id'],)).fetchall()
    c.close(); tooth_map={r['tooth_no']:r for r in rows}
    return render_template('chart.html',patient=patient,tooth_map=tooth_map,records=records,upper=FDI_UPPER,lower=FDI_LOWER,all_teeth=ALL_TEETH,statuses=TOOTH_STATUSES)

@app.route('/patients/<int:pid>/tooth/<tooth_no>',methods=['POST'])
def save_tooth(pid,tooth_no):
    if tooth_no not in {str(x) for x in ALL_TEETH}: return 'Invalid tooth number',400
    c=db(); patient=c.execute('SELECT patient_id FROM patients WHERE id=?',(pid,)).fetchone()
    if not patient: c.close(); return 'Patient not found',404
    f=request.form; status=f.get('status') or 'Healthy'; notes=f.get('notes') or ''
    if status not in TOOTH_STATUSES: status='Healthy'
    c.execute('DELETE FROM tooth_records WHERE patient_id=? AND tooth_no=?',(patient['patient_id'],tooth_no))
    c.execute('INSERT INTO tooth_records(patient_id,tooth_no,status,notes,updated_at) VALUES (?,?,?,?,?)',(patient['patient_id'],tooth_no,status,notes,datetime.now().isoformat()))
    c.commit(); c.close(); flash(f'Tooth {tooth_no} record saved.'); return redirect(url_for('patient_chart',pid=pid))

@app.route('/patients/<int:pid>/records',methods=['POST'])
def add_treatment_record(pid):
    c=db(); patient=c.execute('SELECT patient_id FROM patients WHERE id=?',(pid,)).fetchone()
    if not patient: c.close(); return 'Patient not found',404
    f=request.form; c.execute('INSERT INTO treatment_records(patient_id,visit_date,procedure,tooth_no,dentist,notes,created_at) VALUES (?,?,?,?,?,?,?)',(patient['patient_id'],f.get('visit_date'),f.get('procedure'),f.get('tooth_no') or None,f.get('dentist'),f.get('notes'),datetime.now().isoformat())); c.commit(); c.close(); flash('Treatment record added.'); return redirect(url_for('patient_chart',pid=pid))

@app.route('/patients/<int:pid>/ai')
def patient_ai(pid):
    c=db(); patient=c.execute('SELECT * FROM patients WHERE id=?',(pid,)).fetchone(); c.close()
    if not patient: return 'Patient not found',404
    return render_template('ai.html',patient=patient)

@app.route('/risk')
def risk(): c=db(); patients=c.execute('SELECT patient_id,name FROM patients ORDER BY name').fetchall(); c.close(); return render_template('risk.html',patients=patients)
@app.route('/predict',methods=['POST'])
def predict():
    data=request.form.to_dict(); result=risk_payload(data,data.get('model') or DEFAULT_MODEL); session['last_result']=result; return render_template('result.html',result=result,patient=data.get('patient_name') or 'Current Patient')
@app.route('/appointments')
def appointments(): c=db(); rows=c.execute('SELECT * FROM appointments ORDER BY date,time').fetchall(); patients=c.execute('SELECT patient_id,name FROM patients').fetchall(); c.close(); return render_template('appointments.html',appointments=rows,patients=patients)
@app.route('/appointments/add',methods=['POST'])
def appointment_add():
    f=request.form; c=db(); c.execute('INSERT INTO appointments(patient_id,patient_name,date,time,dentist,purpose,status) VALUES (?,?,?,?,?,?,?)',(f.get('patient_id'),f.get('patient_name'),f.get('date'),f.get('time'),f.get('dentist'),f.get('purpose'),'Scheduled')); c.commit(); c.close(); return redirect(url_for('appointments'))
@app.route('/reports')
def reports(): c=db(); counts={r['periodontal_status']:r['n'] for r in c.execute('SELECT periodontal_status,COUNT(*) n FROM patients GROUP BY periodontal_status')}; c.close(); return render_template('reports.html',metrics=model_metrics(),counts=counts)
@app.route('/users')
def users(): c=db(); rows=c.execute('SELECT * FROM users ORDER BY id').fetchall(); c.close(); return render_template('users.html',users=rows)
@app.route('/api/predict',methods=['POST'])
def api_predict(): return jsonify(risk_payload(request.json or {}))
@app.route('/api/import_csv',methods=['POST'])
def import_csv():
    if 'file' not in request.files: return jsonify({'error':'No CSV file'}),400
    text=request.files['file'].read().decode('utf-8-sig'); reader=csv.DictReader(io.StringIO(text)); c=db(); n=0
    for r in reader:
        try:
            pid=r.get('patient_id') or r.get('Patient ID') or f"IMP-{n+1:04d}"; name=r.get('name') or r.get('Name') or 'Imported Patient';
            c.execute('INSERT OR IGNORE INTO patients(patient_id,name,age,sex,smoking,diabetes,dental_pain,bleeding_gums,caries_count,missing_teeth,oral_hygiene,periodontal_status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,name,int(r.get('age') or r.get('Age') or 0),r.get('sex') or r.get('Sex') or 'Unknown',r.get('smoking') or r.get('Smoking') or 'No',r.get('diabetes') or r.get('Diabetes') or 'No',r.get('dental_pain') or r.get('Dental pain') or 'No',r.get('bleeding_gums') or r.get('Bleeding gums') or 'No',int(r.get('caries_count') or r.get('Caries count') or 0),int(r.get('missing_teeth') or r.get('Missing teeth') or 0),r.get('oral_hygiene') or r.get('Oral hygiene') or 'Good',r.get('periodontal_status') or r.get('Periodontal status') or 'Healthy',datetime.now().isoformat())); n+=1
        except Exception: continue
    c.commit(); c.close(); return jsonify({'imported':n})

if __name__=='__main__': init_db(); app.run(host='127.0.0.1',port=5000,debug=False)
