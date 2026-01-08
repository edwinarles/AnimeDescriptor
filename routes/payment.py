from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from database import db
from services.paypal_service import create_paypal_order, capture_paypal_order
from config import Config

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/create-order', methods=['POST'])
def create_order():
    data = request.get_json()
    api_key = data.get('api_key')
    
    user = db.db.users.find_one({'api_key': api_key})
    if not user:
        return jsonify({'error': 'Invalid API key'}), 401
        
    order = create_paypal_order(Config.PREMIUM_PRICE, str(user['_id']), request.host_url.rstrip('/'))
    if not order:
        return jsonify({'error': 'Error creating PayPal order'}), 500
        
    approval_link = next((l['href'] for l in order.get('links', []) if l['rel'] == 'approve'), None)
    
    return jsonify({'order_id': order['id'], 'approval_url': approval_link})

@payment_bp.route('/capture-order', methods=['POST'])
def capture_order():
    data = request.get_json()
    order_id = data.get('order_id')
    
    print(f"📥 Order capture requested: {order_id}")
    
    if not order_id: 
        print("❌ Error: No order_id provided")
        return jsonify({'error': 'Order ID required'}), 400
    
    # Capture payment with PayPal
    capture = capture_paypal_order(order_id)
    print(f"📡 PayPal response: {capture}")
    
    if not capture:
        print("❌ Error: No response received from PayPal")
        return jsonify({'error': 'PayPal capture failed - no response'}), 500
        
    if capture.get('status') != 'COMPLETED':
        status = capture.get('status', 'UNKNOWN')
        print(f"❌ Error: Payment not completed. Status: {status}")
        return jsonify({'error': f'Payment not completed. Status: {status}'}), 400
        
    # Update user
    try:
        purchase_units = capture.get('purchase_units', [])
        print(f"📦 Purchase units: {purchase_units}")
        
        if not purchase_units:
            print("❌ Error: No purchase units in response")
            return jsonify({'error': 'Invalid PayPal response - no purchase units'}), 500
        
        # The custom_id is inside payments > captures[0] in PayPal response
        payments = purchase_units[0].get('payments', {})
        captures = payments.get('captures', [])
        
        if not captures:
            print("❌ Error: No captures in response")
            return jsonify({'error': 'Invalid PayPal response - no captures'}), 500
            
        user_id_str = captures[0].get('custom_id')
        print(f"👤 User ID from PayPal (from captures): {user_id_str}")
        
        if not user_id_str:
            print("❌ Error: custom_id not found in captures")
            return jsonify({'error': 'User ID not found in payment'}), 500
        
        from bson.objectid import ObjectId
        user_id = ObjectId(user_id_str)
        
        premium_until = datetime.now() + timedelta(days=30)
        
        # Update user to premium
        result = db.db.users.update_one(
            {'_id': user_id},
            {'$set': {'is_premium': True, 'premium_until': premium_until}}
        )
        
        print(f"✅ User updated: matched={result.matched_count}, modified={result.modified_count}")
        
        # Log payment
        db.db.payments.insert_one({
            'user_id': user_id,
            'paypal_order_id': order_id,
            'amount': float(captures[0]['amount']['value']),
            'status': 'completed',
            'created_at': datetime.now()
        })
        
        print(f"✅ Payment completed successfully for user {user_id_str}")
        return jsonify({'status': 'success', 'message': 'Premium activated'})
        
    except Exception as e:
        import traceback
        print(f"❌ Error processing payment capture: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error processing payment: {str(e)}'}), 500
