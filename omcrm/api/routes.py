from flask import Blueprint, request, jsonify
from datetime import datetime
import secrets
import string
import re

from omcrm import db
from omcrm.leads.models import Lead, LeadSource, LeadStatus, Comment
from omcrm.rbac import is_admin, check_access
from flask_login import login_required
# CSRF exemption removed - using different approach

api = Blueprint('api', __name__)

@api.route('/api/status', methods=['GET'])
def api_status():
    """Check API status and return basic information"""
    return jsonify({
        'status': 'online',
        'version': '1.0',
        'message': 'API is operational'
    }), 200

@api.route('/api/market/status', methods=['GET'])
def market_status():
    """Get current market status and trading hours"""
    try:
        from omcrm.utils.market_hours import get_market_status, can_trade
        
        # Get basic market status
        status = get_market_status()
        
        # Check if trading is allowed (with optional extended hours)
        allow_extended = request.args.get('extended_hours', 'false').lower() == 'true'
        can_trade_now, trade_reason = can_trade(allow_extended_hours=allow_extended)
        
        # Add trading permission to response
        status['trading_allowed'] = can_trade_now
        status['trading_reason'] = trade_reason
        status['extended_hours_enabled'] = allow_extended
        
        return jsonify(status), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Error checking market status: {str(e)}',
            'is_open': False,
            'trading_allowed': False,
            'status': 'ERROR'
        }), 500

@api.route('/api/market/can_trade', methods=['GET'])
def can_trade_check():
    """Simple endpoint to check if trading is currently allowed"""
    try:
        from omcrm.utils.market_hours import can_trade
        
        allow_extended = request.args.get('extended_hours', 'false').lower() == 'true'
        can_trade_now, reason = can_trade(allow_extended_hours=allow_extended)
        
        return jsonify({
            'can_trade': can_trade_now,
            'reason': reason,
            'extended_hours_enabled': allow_extended
        }), 200
        
    except Exception as e:
        return jsonify({
            'can_trade': False,
            'reason': f'Error: {str(e)}',
            'extended_hours_enabled': False
        }), 500

@api.route('/api/admin/sources', methods=['GET'])
@login_required
@is_admin
def list_sources():
    """Admin route to list available lead sources with their API keys"""
    sources = LeadSource.query.all()
    result = []
    
    for source in sources:
        result.append({
            'id': source.id,
            'name': source.source_name,
            'api_key': source.api_key,
            'affiliate_id': source.affiliate_id,
            'is_api_enabled': source.is_api_enabled
        })
    
    return jsonify({
        'sources': result
    }), 200

@api.route('/api/import_lead', methods=['GET', 'POST'])
def import_lead():
    """API endpoint for importing leads from external sources
    
    Required parameters:
    - api_key: The API key associated with a lead source
    - affiliate_id: The affiliate ID from the lead source
    - first_name: First name of the lead
    - last_name: Last name of the lead
    - email: Email address of the lead
    
    Optional parameters:
    - phone: Phone number
    - country: Country
    - company_name: Company name
    - notes: Additional notes (stored in lead notes field)
    - comment: Optional comment (creates a proper comment record)
    - funnel_name: Funnel name for tracking
    
    Returns:
    - JSON response with success/error message and lead ID if successful
    """
    # Extract data from request (handle both GET and POST)
    data = {}
    if request.method == 'POST':
        # Try JSON first, then form data
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        # If still no data, try to get from request.data as JSON
        if not data and request.data:
            try:
                import json
                data = json.loads(request.data.decode('utf-8'))
            except:
                pass
    else:  # GET
        data = request.args.to_dict()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided',
            'debug': {
                'method': request.method,
                'content_type': request.content_type,
                'is_json': request.is_json,
                'has_form': bool(request.form),
                'has_data': bool(request.data)
            }
        }), 400
    
    # Validate required parameters
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'API key is required'
        }), 400

    affiliate_id = data.get('affiliate_id')
    if not affiliate_id:
        return jsonify({
            'success': False,
            'error': 'Affiliate ID is required'
        }), 400

    # Find the lead source by API key
    lead_source = LeadSource.get_by_api_key(api_key)
    if not lead_source:
        return jsonify({
            'success': False,
            'error': 'Invalid API key or API access is disabled'
        }), 401

    # Validate that the affiliate_id matches the lead source
    if lead_source.affiliate_id != affiliate_id:
        return jsonify({
            'success': False,
            'error': 'Affiliate ID does not match the API key'
        }), 401
    
    # Validate required lead data
    if not data.get('first_name'):
        return jsonify({
            'success': False,
            'error': 'First name is required'
        }), 400
        
    if not data.get('last_name'):
        return jsonify({
            'success': False,
            'error': 'Last name is required'
        }), 400
        
    if not data.get('email'):
        return jsonify({
            'success': False,
            'error': 'Email is required'
        }), 400
    
    # Validate email format
    email = data.get('email')
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({
            'success': False,
            'error': 'Invalid email format'
        }), 400
    
    # Check if lead with this email already exists
    existing_lead = Lead.query.filter_by(email=email).first()
    if existing_lead:
        return jsonify({
            'success': False,
            'error': 'Lead with this email already exists',
            'lead_id': existing_lead.id
        }), 409
    
    # Create new lead
    try:
        # Get default lead status (or first status if no default is set)
        default_status = LeadStatus.query.first()
        
        new_lead = Lead(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=email,
            phone=data.get('phone'),
            country=data.get('country'),
            company_name=data.get('company_name'),
            notes=data.get('notes'),
            lead_source_id=lead_source.id,
            lead_status_id=default_status.id if default_status else None,
            # 🔧 NEW: Store affiliate_id and funnel_name in dedicated fields
            affiliate_id=affiliate_id,
            funnel_name=data.get('funnel_name'),
            date_created=datetime.utcnow()
        )
        
        # Generate a random password (will be reset by admin)
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        new_lead.set_password(temp_password)
        
        db.session.add(new_lead)
        db.session.commit()
        
        # Add comment if provided
        comment_text = data.get('comment')
        if comment_text and comment_text.strip():
            comment = Comment(
                content=comment_text.strip(),
                user_id=1,  # System user for API comments (you may want to create a dedicated API user)
                lead_id=new_lead.id,
                date_posted=datetime.utcnow()
            )
            db.session.add(comment)
            db.session.commit()
        
        response_data = {
            'success': True,
            'message': 'Lead imported successfully',
            'lead_id': new_lead.id
        }
        
        # Include comment ID in response if comment was added
        if comment_text and comment_text.strip():
            response_data['comment_added'] = True
            response_data['comment_id'] = comment.id
        
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error creating lead: {str(e)}'
        }), 500
        
@api.route('/api/generate_api_key/<int:source_id>', methods=['POST'])
def generate_api_key(source_id):
    """Generate a new API key for a lead source"""
    lead_source = LeadSource.query.get_or_404(source_id)
    
    # Generate new API key
    api_key = secrets.token_hex(32)
    lead_source.api_key = api_key
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'api_key': api_key
    }), 200

@api.route('/api/add_comment', methods=['POST'])
def add_comment_to_lead():
    """API endpoint for adding comments to existing leads
    
    Required parameters:
    - api_key: The API key associated with a lead source
    - lead_id: The ID of the lead to add comment to
    - comment: The comment text
    
    Returns:
    - JSON response with success/error message and comment ID if successful
    """
    # Extract data from request
    data = {}
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()
    
    # If still no data, try to get from request.data as JSON
    if not data and request.data:
        try:
            import json
            data = json.loads(request.data.decode('utf-8'))
        except:
            pass
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided'
        }), 400
    
    # Validate required parameters
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'API key is required'
        }), 400

    # Validate API key
    lead_source = LeadSource.get_by_api_key(api_key)
    if not lead_source:
        return jsonify({
            'success': False,
            'error': 'Invalid API key or API access is disabled'
        }), 401

    lead_id = data.get('lead_id')
    if not lead_id:
        return jsonify({
            'success': False,
            'error': 'Lead ID is required'
        }), 400

    comment_text = data.get('comment')
    if not comment_text or not comment_text.strip():
        return jsonify({
            'success': False,
            'error': 'Comment text is required'
        }), 400

    # Find the lead
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({
            'success': False,
            'error': 'Lead not found'
        }), 404

    try:
        # Create comment
        comment = Comment(
            content=comment_text.strip(),
            user_id=1,  # System user for API comments
            lead_id=lead.id,
            date_posted=datetime.utcnow()
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment added successfully',
            'comment_id': comment.id,
            'lead_id': lead.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error adding comment: {str(e)}'
        }), 500 