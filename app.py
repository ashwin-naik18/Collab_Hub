from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from flask_mail import Mail, Message
import random, string

from config import Config
from db import execute_query, init_db_pool


app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)

with app.app_context():
    init_db_pool()



def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def store_otp(email, otp):
    expires_at = datetime.now() + timedelta(minutes=Config.OTP_EXPIRY_MINUTES)
    execute_query(
        "INSERT INTO otp_verifications (email, otp_code, expires_at) VALUES (%s, %s, %s)",
        (email, otp, expires_at)
    )


def send_otp_email(email, otp, user_name="User"):
   
    if not app.config.get('MAIL_USERNAME'):
        print(f"[DEV] OTP for {email}: {otp}")
        return

    msg = Message(
        subject='Your CollabHub Verification Code',
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email]
    )
    msg.html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:linear-gradient(135deg,#f4713a,#ff6b9d);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0">
            <h1>🚀 CollabHub</h1>
        </div>
        <div style="background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px">
            <h2>Hello {user_name}!</h2>
            <p>Your verification code is:</p>
            <div style="font-size:36px;font-weight:bold;color:#f4713a;letter-spacing:10px;text-align:center;padding:20px">
                {otp}
            </div>
            <p>⏰ Expires in {Config.OTP_EXPIRY_MINUTES} minutes.</p>
            <p>If you didn't request this, ignore this email.</p>
        </div>
    </div>
    """
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Email send failed: {e}")
        print(f"[DEV] OTP for {email}: {otp}")


def get_current_user():
    if 'user_id' not in session:
        return None
    return execute_query(
        "SELECT * FROM users WHERE user_id = %s",
        (session['user_id'],), fetch_one=True
    )


def time_ago(dt):
    if not dt:
        return 'recently'
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return 'recently'
    if hasattr(dt, 'tzinfo') and dt.tzinfo:
        dt = dt.replace(tzinfo=None)

    diff = datetime.now() - dt
    if diff.days >= 7:  return f"{diff.days // 7}w ago"
    if diff.days > 0:   return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours > 0:       return f"{hours}h ago"
    mins = diff.seconds // 60
    return f"{mins}m ago" if mins > 0 else "just now"


def get_index_stats():
    try:
        stats = {
            'total_ideas':        (execute_query("SELECT COUNT(*) as c FROM ideas WHERE is_active=1", fetch_one=True) or {}).get('c', 0),
            'total_builders':     (execute_query("SELECT COUNT(*) as c FROM users WHERE role='builder'", fetch_one=True) or {}).get('c', 0),
            'total_investors':    (execute_query("SELECT COUNT(*) as c FROM users WHERE role='investor'", fetch_one=True) or {}).get('c', 0),
            'total_applications': (execute_query("SELECT COUNT(*) as c FROM applications", fetch_one=True) or {}).get('c', 0),
        }
        categories = ['AI/ML', 'HealthTech', 'FinTech', 'CleanTech', 'EdTech', 'Other']
        category_counts = {
            cat: (execute_query("SELECT COUNT(*) as c FROM ideas WHERE category=%s AND is_active=1", (cat,), fetch_one=True) or {}).get('c', 0)
            for cat in categories
        }
        return stats, category_counts
    except Exception as e:
        print(f"Stats error: {e}")
        zero_stats = {'total_ideas': 0, 'total_builders': 0, 'total_investors': 0, 'total_applications': 0}
        zero_cats  = {cat: 0 for cat in ['AI/ML', 'HealthTech', 'FinTech', 'CleanTech', 'EdTech', 'Other']}
        return zero_stats, zero_cats


def get_user_applied_ids():
  
    if 'user_id' not in session:
        return []
    rows = execute_query(
        "SELECT idea_id FROM applications WHERE applicant_id=%s",
        (session['user_id'],), fetch=True
    )
    return [r['idea_id'] for r in rows] if rows else []



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    full_name = request.form.get('full_name', '').strip()
    email     = request.form.get('email', '').strip().lower()
    phone     = request.form.get('phone', '').strip()
    password  = request.form.get('password', '')
    bio       = request.form.get('bio', '').strip()
    city      = request.form.get('city', '').strip()
    role      = request.form.get('role', 'builder')

    if not all([full_name, email, phone, password]):
        flash('All required fields must be filled', 'error')
        return redirect(url_for('register'))
    if len(password) < 8:
        flash('Password must be at least 8 characters', 'error')
        return redirect(url_for('register'))
    if len(phone) != 10 or not phone.isdigit():
        flash('Phone number must be 10 digits', 'error')
        return redirect(url_for('register'))
    if execute_query("SELECT user_id FROM users WHERE email=%s OR phone=%s", (email, phone), fetch_one=True):
        flash('Email or phone already registered', 'error')
        return redirect(url_for('register'))

    user_id = execute_query(
        "INSERT INTO users (full_name, email, phone, password_hash, bio, city, role, is_verified) VALUES (%s,%s,%s,%s,%s,%s,%s,0)",
        (full_name, email, phone, generate_password_hash(password), bio, city, role)
    )

    otp = generate_otp()
    print(otp)
    store_otp(email, otp)
    send_otp_email(email, otp, full_name)

    session['verification_email']   = email
    session['verification_user_id'] = user_id
    flash('Account created! Check your email for the OTP.', 'success')
    return redirect(url_for('verify_otp'))


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'verification_email' not in session:
        flash('Please register first', 'warning')
        return redirect(url_for('register'))

    email = session['verification_email']

    if request.method == 'GET':
        return render_template('verify_otp.html', email=email)

    otp = request.form.get('otp', '').strip()
    if len(otp) != 6:
        flash('Please enter a valid 6-digit OTP', 'error')
        return redirect(url_for('verify_otp'))

    record = execute_query(
        "SELECT * FROM otp_verifications WHERE email=%s AND otp_code=%s AND is_used=0 AND expires_at>NOW() ORDER BY created_at DESC LIMIT 1",
        (email, otp), fetch_one=True
    )
    if not record:
        flash('Invalid or expired OTP. Try again.', 'error')
        return redirect(url_for('verify_otp'))

    execute_query("UPDATE otp_verifications SET is_used=1 WHERE otp_id=%s", (record['otp_id'],))
    user_id = session.pop('verification_user_id')
    session.pop('verification_email')
    execute_query("UPDATE users SET is_verified=1 WHERE user_id=%s", (user_id,))

    user = execute_query("SELECT full_name FROM users WHERE user_id=%s", (user_id,), fetch_one=True)
    session['user_id']   = user_id
    session['user_name'] = user['full_name'] if user else ''
    flash('Email verified! Welcome to CollabHub 🎉', 'success')
    return redirect(url_for('index'))


@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    email   = session.get('verification_email')
    user_id = session.get('verification_user_id')

    if not email:
        flash('Session expired. Please register again.', 'error')
        return redirect(url_for('register'))

    user = execute_query("SELECT full_name FROM users WHERE user_id=%s", (user_id,), fetch_one=True)
    otp  = generate_otp()
    store_otp(email, otp)
    send_otp_email(email, otp, user['full_name'] if user else 'User')
    flash('OTP resent! Check your email.', 'success')
    return redirect(url_for('verify_otp'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email    = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if not email or not password:
        flash('Please enter email and password', 'error')
        return redirect(url_for('login'))

    user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetch_one=True)

    if not user or not check_password_hash(user['password_hash'], password):
        flash('Invalid email or password', 'error')
        return redirect(url_for('login'))

    if not user['is_verified']:
        session['verification_email']   = user['email']
        session['verification_user_id'] = user['user_id']
        otp = generate_otp()
        store_otp(user['email'], otp)
        send_otp_email(user['email'], otp, user['full_name'])
        flash('Please verify your email first.', 'warning')
        return redirect(url_for('verify_otp'))

    session['user_id']   = user['user_id']
    session['user_name'] = user['full_name']
    session.permanent    = bool(request.form.get('remember'))
    flash(f"Welcome back, {user['full_name']}! ✨", 'success')

    next_page = request.args.get('next')
    return redirect(next_page if next_page and next_page.startswith('/') else url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))


@app.route('/')
def index():
    category = request.args.get('category', '')
    stage    = request.args.get('stage', '')
    sort     = request.args.get('sort', 'latest')
    search   = request.args.get('q', '')

    query  = """
        SELECT i.*, u.full_name, u.city, u.role,
               (SELECT COUNT(*) FROM applications WHERE idea_id=i.idea_id) as application_count
        FROM ideas i
        JOIN users u ON i.user_id = u.user_id
        WHERE i.is_active = 1
    """
    params = []
    if category:
        query += " AND i.category = %s";              params.append(category)
    if stage:
        query += " AND i.stage = %s";                 params.append(stage)
    if search:
        query += " AND (i.title LIKE %s OR i.description LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]

    sort_map = {'trending': " ORDER BY i.views DESC", 'hiring': " ORDER BY i.slots_open DESC"}
    query += sort_map.get(sort, " ORDER BY i.created_at DESC")

    ideas = execute_query(query, tuple(params) if params else None, fetch=True) or []
    for idea in ideas:
        idea['time_ago'] = time_ago(idea['created_at'])
        idea['skills']   = execute_query("SELECT * FROM idea_skills WHERE idea_id=%s", (idea['idea_id'],), fetch=True) or []

    stats, category_counts = get_index_stats()
    return render_template('index.html',
        ideas            = ideas,
        stats            = stats,
        category_counts  = category_counts,
        user_applied_ids = get_user_applied_ids(),
        page             = 1,
        total_pages      = 1,
        current_user     = get_current_user()
    )


@app.route('/post-idea', methods=['GET', 'POST'])
@login_required
def post_idea():
    if request.method == 'GET':
        return render_template('post_idea.html', current_user=get_current_user())

    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category    = request.form.get('category')
    stage       = request.form.get('stage', 'Just an idea')
    slots_open  = request.form.get('slots_open', 2, type=int)

    if not all([title, description, category]):
        flash('Please fill all required fields', 'error')
        return redirect(url_for('post_idea'))

    idea_id = execute_query(
        "INSERT INTO ideas (user_id, title, description, category, stage, slots_open) VALUES (%s,%s,%s,%s,%s,%s)",
        (session['user_id'], title, description, category, stage, slots_open)
    )
    for name, needed in zip(request.form.getlist('skill_names[]'), request.form.getlist('skill_needed[]')):
        if name.strip():
            execute_query("INSERT INTO idea_skills (idea_id, skill_name, is_needed) VALUES (%s,%s,%s)",
                          (idea_id, name.strip(), int(needed)))

    flash('Idea posted! 🚀', 'success')
    return redirect(url_for('idea_detail', idea_id=idea_id))


@app.route('/idea/<int:idea_id>')
def idea_detail(idea_id):
    owner = execute_query("SELECT user_id FROM ideas WHERE idea_id=%s", (idea_id,), fetch_one=True)
    if owner and owner['user_id'] != session.get('user_id'):
        execute_query("UPDATE ideas SET views=views+1 WHERE idea_id=%s", (idea_id,))

    idea = execute_query(
        "SELECT i.*, u.full_name, u.email, u.phone, u.bio, u.city, u.role FROM ideas i JOIN users u ON i.user_id=u.user_id WHERE i.idea_id=%s",
        (idea_id,), fetch_one=True
    )
    if not idea:
        flash('Idea not found', 'error')
        return redirect(url_for('index'))

    comments = execute_query(
        "SELECT c.*, u.full_name FROM comments c JOIN users u ON c.user_id=u.user_id WHERE c.idea_id=%s ORDER BY c.created_at ASC",
        (idea_id,), fetch=True
    ) or []
    for c in comments:
        c['time_ago'] = time_ago(c['created_at'])

    applications = execute_query(
        "SELECT a.*, u.full_name, u.email, u.bio, u.city FROM applications a JOIN users u ON a.applicant_id=u.user_id WHERE a.idea_id=%s ORDER BY a.applied_at DESC",
        (idea_id,), fetch=True
    ) or []

    idea['skills']            = execute_query("SELECT * FROM idea_skills WHERE idea_id=%s", (idea_id,), fetch=True) or []
    idea['application_count'] = len(applications)
    idea['comment_count']     = len(comments)
    idea['time_ago']          = time_ago(idea['created_at'])

    already_applied = (
        'user_id' in session and
        execute_query("SELECT application_id FROM applications WHERE idea_id=%s AND applicant_id=%s",
                      (idea_id, session['user_id']), fetch_one=True) is not None
    )

    return render_template('idea_detail.html',
        idea            = idea,
        comments        = comments,
        already_applied = already_applied,
        current_user    = get_current_user()
    )


@app.route('/idea/<int:idea_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_idea(idea_id):
    idea = execute_query("SELECT * FROM ideas WHERE idea_id=%s", (idea_id,), fetch_one=True)

    if not idea:
        flash('Idea not found', 'error')
        return redirect(url_for('index'))
    if idea['user_id'] != session['user_id']:
        flash('You can only edit your own ideas', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    if request.method == 'POST':
        execute_query(
            "UPDATE ideas SET title=%s, description=%s, category=%s, stage=%s, slots_open=%s, is_active=%s WHERE idea_id=%s",
            (request.form.get('title','').strip(), request.form.get('description','').strip(),
             request.form.get('category'), request.form.get('stage'),
             request.form.get('slots_open', 2, type=int), request.form.get('is_active', 1, type=int), idea_id)
        )
        execute_query("DELETE FROM idea_skills WHERE idea_id=%s", (idea_id,))
        for name, needed in zip(request.form.getlist('skill_names[]'), request.form.getlist('skill_needed[]')):
            if name.strip():
                execute_query("INSERT INTO idea_skills (idea_id, skill_name, is_needed) VALUES (%s,%s,%s)",
                              (idea_id, name.strip(), int(needed)))
        flash('Idea updated! ✨', 'success')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    idea['skills']            = execute_query("SELECT * FROM idea_skills WHERE idea_id=%s", (idea_id,), fetch=True) or []
    idea['application_count'] = (execute_query("SELECT COUNT(*) as c FROM applications WHERE idea_id=%s", (idea_id,), fetch_one=True) or {}).get('c', 0)
    idea['comment_count']     = (execute_query("SELECT COUNT(*) as c FROM comments WHERE idea_id=%s", (idea_id,), fetch_one=True) or {}).get('c', 0)
    idea['time_ago']          = time_ago(idea['created_at'])
    return render_template('edit_idea.html', idea=idea, current_user=get_current_user())


@app.route('/idea/<int:idea_id>/delete', methods=['POST'])
@login_required
def delete_idea(idea_id):
    idea = execute_query("SELECT * FROM ideas WHERE idea_id=%s", (idea_id,), fetch_one=True)
    if not idea or idea['user_id'] != session['user_id']:
        flash('Cannot delete this idea', 'error')
        return redirect(url_for('index'))

    for table in ['idea_skills', 'applications', 'comments', 'ideas']:
        execute_query(f"DELETE FROM {table} WHERE idea_id=%s", (idea_id,))

    flash('Idea deleted', 'success')
    return redirect(url_for('index'))



@app.route('/idea/<int:idea_id>/apply', methods=['POST'])
@login_required
def apply(idea_id):
    already = execute_query(
        "SELECT application_id FROM applications WHERE idea_id=%s AND applicant_id=%s",
        (idea_id, session['user_id']), fetch_one=True
    )
    if already:
        flash('You have already applied to this idea', 'warning')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    execute_query(
        "INSERT INTO applications (idea_id, applicant_id, cover_note, skills_offered) VALUES (%s,%s,%s,%s)",
        (idea_id, session['user_id'], request.form.get('cover_note','').strip(), request.form.get('skills_offered','').strip())
    )
    flash('Application submitted! 🎉', 'success')
    return redirect(url_for('idea_detail', idea_id=idea_id))


@app.route('/my-applications')
@login_required
def my_applications():
    uid = session['user_id']


    sent = execute_query("""
        SELECT a.*, i.title, i.category, i.stage as idea_stage, u.full_name as founder_name, u.city
        FROM applications a
        JOIN ideas i ON a.idea_id = i.idea_id
        JOIN users u ON i.user_id = u.user_id
        WHERE a.applicant_id = %s ORDER BY a.applied_at DESC
    """, (uid,), fetch=True) or []
    for a in sent:
        a['time_ago'] = time_ago(a['applied_at'])

    my_ideas = execute_query("""
        SELECT i.*,
               (SELECT COUNT(*) FROM applications WHERE idea_id=i.idea_id) as application_count,
               (SELECT COUNT(*) FROM comments WHERE idea_id=i.idea_id) as comment_count
        FROM ideas i WHERE i.user_id = %s ORDER BY i.created_at DESC
    """, (uid,), fetch=True) or []
    for idea in my_ideas:
        idea['time_ago'] = time_ago(idea['created_at'])

    received = execute_query("""
        SELECT a.*, u.full_name, u.city, i.title, i.idea_id
        FROM applications a
        JOIN users u ON a.applicant_id = u.user_id
        JOIN ideas i ON a.idea_id = i.idea_id
        WHERE i.user_id = %s ORDER BY a.applied_at DESC
    """, (uid,), fetch=True) or []
    for a in received:
        a['time_ago'] = time_ago(a['applied_at'])

    return render_template('my_applications.html',
        sent_applications     = sent,
        received_applications = received,
        my_ideas              = my_ideas,
        current_user          = get_current_user()
    )


@app.route('/application/<int:application_id>/accept', methods=['POST'])
@login_required
def accept_application(application_id):
    execute_query("UPDATE applications SET status='accepted' WHERE application_id=%s", (application_id,))
    flash('Application accepted! 🎉', 'success')
    return redirect(url_for('my_applications'))


@app.route('/application/<int:application_id>/reject', methods=['POST'])
@login_required
def reject_application(application_id):
    execute_query("UPDATE applications SET status='rejected' WHERE application_id=%s", (application_id,))
    flash('Application rejected.', 'info')
    return redirect(url_for('my_applications'))


@app.route('/application/<int:application_id>/withdraw', methods=['POST'])
@login_required
def withdraw_application(application_id):
    execute_query("DELETE FROM applications WHERE application_id=%s AND applicant_id=%s",
                  (application_id, session['user_id']))
    flash('Application withdrawn.', 'info')
    return redirect(url_for('my_applications'))



@app.route('/idea/<int:idea_id>/comment', methods=['POST'])
@login_required
def add_comment(idea_id):
    body = request.form.get('body', '').strip()
    if not body:
        flash('Comment cannot be empty', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    execute_query("INSERT INTO comments (idea_id, user_id, body) VALUES (%s,%s,%s)",
                  (idea_id, session['user_id'], body))
    flash('Comment added! 💬', 'success')
    return redirect(url_for('idea_detail', idea_id=idea_id))


@app.route('/idea/<int:idea_id>/express-interest', methods=['POST'])
@login_required
def express_interest(idea_id):
    user = get_current_user()
    if user['role'] != 'investor':
        flash('Only investors can express interest', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    already = execute_query(
        "SELECT interest_id FROM investor_interests WHERE investor_id=%s AND idea_id=%s",
        (session['user_id'], idea_id), fetch_one=True
    )
    if already:
        flash('You have already expressed interest in this idea', 'warning')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    execute_query("INSERT INTO investor_interests (investor_id, idea_id, note) VALUES (%s,%s,%s)",
                  (session['user_id'], idea_id, request.form.get('note','').strip()))
    flash('Interest expressed! The founder will be notified. ', 'success')
    return redirect(url_for('idea_detail', idea_id=idea_id))



@app.errorhandler(404)
def not_found(e):
    stats, category_counts = get_index_stats()
    return render_template('index.html',
        ideas=[], stats=stats, category_counts=category_counts,
        user_applied_ids=[], page=1, total_pages=1,
        current_user=get_current_user()), 404


@app.errorhandler(500)
def server_error(e):
    return "500 — Something went wrong. Please try again.", 500



@app.context_processor
def inject_globals():
    return {
        'CATEGORIES': ['AI/ML', 'HealthTech', 'FinTech', 'CleanTech', 'EdTech', 'Other'],
        'STAGES':     ['Just an idea', 'Building MVP', 'Launched', 'Growing'],
    }



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)