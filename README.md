# MindBloom Flask MVP

## What this version does
- Real Flask backend with SQLite database.
- User registration/login/logout.
- Password hashing.
- Persistent check-ins and activity completion.
- Daily wellness form: mood, factors, sleep, energy, fatigue and support.
- Backend calculates a simple wellness pattern and recommendations.
- Tracker shows which day the user checked in, how they felt, status, sleep and factors.
- Activities can be completed and stored.
- Welfare demo shows aggregate counts and common factors only.
- Responsive UI for desktop/tablet/mobile.

## Demo accounts
Personnel:
- Email: personnel@mindbloom.local
- Password: demo123

Welfare:
- Email: welfare@mindbloom.local
- Password: demo123

## Run on Windows
1. Install Python 3.10+.
2. Open terminal in this folder.
3. Create a virtual environment:
   `python -m venv venv`
4. Activate:
   `venv\Scripts\activate`
5. Install:
   `pip install -r requirements.txt`
6. Run:
   `python app.py`
7. Open:
   http://127.0.0.1:5000

The SQLite database `mindbloom.db` is created automatically.

## Important
The wellness scoring in this MVP is demo decision logic, not a clinical assessment. Before deployment, questionnaire items, scoring, recommendations, escalation pathways, privacy controls and wording should be reviewed with qualified psychology/welfare stakeholders and the organization's security/legal teams.
