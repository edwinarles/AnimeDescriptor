from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

from database import db
from utils import generate_api_key
from services.email_service import send_login_email, send_reset_password_email
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Traditional registration (Email/Key) or simple 'Magic Link' login"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        # Anonymous user
        new_key = generate_api_key()
        try:
            db.db.users.insert_one({
                'api_key': new_key,
                'is_premium': False,
                'created_at': datetime.now()
            })
            return jsonify({'api_key': new_key, 'is_premium': False, 'message': 'Anonymous'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Check if user exists
    user = db.db.users.find_one({'email': email})
    if user:
        # Magic Link login requested for existing user
        send_login_email(email, user['api_key'], request.host_url)
        return jsonify({'message': 'Magic link sent', 'require_email_check': True})
    
    # New user via email (Magic Link flow by default)
    new_key = generate_api_key()
    db.db.users.insert_one({
        'email': email,
        'api_key': new_key,
        'is_premium': False,
        'created_at': datetime.now()
    })
    send_login_email(email, new_key, request.host_url)
    return jsonify({'message': 'Magic link sent', 'require_email_check': True})


@auth_bp.route('/register-password', methods=['POST'])
def register_password():
    """Password registration - account created ONLY after email verification"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Check if email already has an ACTIVE account
    existing_user = db.db.users.find_one({'email': email})
    if existing_user:
        print(f"⚠️ Registration attempt with existing email: {email}")
        return jsonify({'error': 'Email already registered'}), 409
    
    # Check if there's already a pending registration
    pending = db.db.pending_registrations.find_one({'email': email})
    if pending:
        # Pending registration already exists, resend email
        print(f"⚠️ Existing pending registration for: {email}, resending email")
        from services.email_service import send_verification_email
        send_verification_email(email, pending['verification_token'], request.host_url)
        return jsonify({
            'message': 'A verification email has already been sent. Please check your inbox.',
            'require_email_verification': True
        }), 200
        
    # Generate verification token and password hash
    hashed = generate_password_hash(password)
    verification_token = secrets.token_urlsafe(32)
    
    # Save to TEMPORARY pending registrations collection
    # User is NOT created yet
    db.db.pending_registrations.insert_one({
        'email': email,
        'password_hash': hashed,
        'verification_token': verification_token,
        'token_expires': datetime.now() + timedelta(hours=24),
        'created_at': datetime.now()
    })
    
    # Send verification email
    from services.email_service import send_verification_email
    email_sent = send_verification_email(email, verification_token, request.host_url)
    
    if email_sent:
        print(f"✅ Pending registration created: {email}")
        return jsonify({
            'message': 'Registration initiated. Please check your email to complete registration.',
            'require_email_verification': True
        }), 201
    else:
        # If email fails, remove pending registration
        db.db.pending_registrations.delete_one({'email': email})
        print(f"⚠️ Verification email failed, pending registration removed: {email}")
        return jsonify({
            'error': 'Failed to send verification email. Please try again later.'
        }), 500


@auth_bp.route('/login-password', methods=['POST'])
def login_password():
    """Password login"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = db.db.users.find_one({'email': email})
    if not user or 'password_hash' not in user:
        return jsonify({'error': 'Invalid credentials'}), 401
        
    if check_password_hash(user['password_hash'], password):
        return jsonify({
            'api_key': user['api_key'],
            'is_premium': user.get('is_premium', False),
            'message': 'Login successful'
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401


@auth_bp.route('/verify-email', methods=['GET'])
def verify_email():
    """Verify email with token and CREATE the account"""
    token = request.args.get('token')
    
    if not token:
        return jsonify({'error': 'Verification token required'}), 400
    
    # Search in PENDING registrations
    pending_user = db.db.pending_registrations.find_one({'verification_token': token})
    
    if not pending_user:
        return jsonify({'error': 'Invalid verification token'}), 404
    
    # Verify token hasn't expired
    if pending_user.get('token_expires') and datetime.now() > pending_user['token_expires']:
        # Remove expired pending registration
        db.db.pending_registrations.delete_one({'_id': pending_user['_id']})
        return jsonify({'error': 'Verification token has expired. Please register again.'}), 410
    
    # CREATE the user NOW (didn't exist before)
    new_key = generate_api_key()
    db.db.users.insert_one({
        'email': pending_user['email'],
        'password_hash': pending_user['password_hash'],
        'api_key': new_key,
        'is_premium': False,
        'email_verified': True,  # Already verified
        'created_at': datetime.now()
    })
    
    # Remove from pending registrations
    db.db.pending_registrations.delete_one({'_id': pending_user['_id']})
    
    print(f"✅ Account created and email verified for: {pending_user.get('email')}")
    
    # Redirect to main page with API key for auto-login
    from flask import redirect
    return redirect(f"/?api_key={new_key}&verified=true")


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    api_key = request.headers.get('X-API-Key')
    if not api_key: return jsonify({'error': 'API key required'}), 401
    
    user = db.db.users.find_one({'api_key': api_key})
    if not user: return jsonify({'error': 'Invalid API key'}), 401
    
    # Check premium expiration
    is_premium = user.get('is_premium', False)
    if is_premium and user.get('premium_until'):
        if datetime.now() > user['premium_until']:
            db.db.users.update_one({'_id': user['_id']}, {'$set': {'is_premium': False}})
            is_premium = False
            
    # Count searches in the last hour
    one_hour_ago = datetime.now() - timedelta(hours=1)
    # Assuming searches collection has 'user_id' referencing user._id or api_key
    # Using API Key for simplicity in search logging
    count = db.db.searches.count_documents({
        'api_key': api_key,
        'timestamp': {'$gt': one_hour_ago}
    })
    
    limit = Config.PREMIUM_HOURLY_LIMIT if is_premium else Config.FREE_HOURLY_LIMIT
    
    return jsonify({
        'is_premium': is_premium,
        'premium_until': user.get('premium_until'),
        'hourly_searches': count,
        'hourly_limit': limit,
        'remaining': max(0, limit - count)
    })

@auth_bp.route('/anonymous-status', methods=['GET'])
def anonymous_status():
    """Get search status for anonymous users based on session"""
    import hashlib
    
    # Create session ID based on IP and user-agent (same as search endpoint)
    session_data = f"{request.remote_addr}:{request.headers.get('User-Agent', '')}"
    session_id = hashlib.sha256(session_data.encode()).hexdigest()
    
    # Count anonymous searches in the last hour
    one_hour_ago = datetime.now() - timedelta(hours=1)
    count = db.db.anonymous_searches.count_documents({
        'session_id': session_id,
        'timestamp': {'$gt': one_hour_ago}
    })
    
    limit = 10  # Anonymous limit
    
    return jsonify({
        'is_anonymous': True,
        'hourly_searches': count,
        'hourly_limit': limit,
        'remaining': max(0, limit - count)
    })
