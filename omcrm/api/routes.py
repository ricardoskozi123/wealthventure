from flask import Blueprint, request, jsonify
from datetime import datetime
import secrets
import string
import re

from omcrm import db
from omcrm.leads.models import Lead, LeadSource, LeadStatus
from omcrm.rbac import is_admin
from flask_login import login_required

api = Blueprint('api', __name__)

@api.route('/api/status', methods=['GET'])
def api_status():
    """Check API status and return basic information"""
    return jsonify({
        'status': 'online',
        'version': '1.0',
        'message': 'API is operational'
    }), 200

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
    - first_name: First name of the lead
    - last_name: Last name of the lead
    - email: Email address of the lead
    
    Optional parameters:
    - phone: Phone number
    - country: Country
    - company_name: Company name
    - notes: Additional notes
    - affiliate_id: Affiliate ID for tracking
    
    Returns:
    - JSON response with success/error message and lead ID if successful
    """
    # Extract data from request (handle both GET and POST)
    if request.method == 'POST':
        data = request.get_json() or request.form.to_dict()
    else:  # GET
        data = request.args.to_dict()
    
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
    
    # Find the lead source by API key
    lead_source = LeadSource.get_by_api_key(api_key)
    if not lead_source:
        return jsonify({
            'success': False,
            'error': 'Invalid API key or API access is disabled'
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
            date_created=datetime.utcnow()
        )
        
        # Store affiliate ID in notes if provided
        affiliate_id = data.get('affiliate_id') or lead_source.affiliate_id
        if affiliate_id:
            additional_note = f"Affiliate ID: {affiliate_id}"
            if new_lead.notes:
                new_lead.notes = f"{new_lead.notes}\n{additional_note}"
            else:
                new_lead.notes = additional_note
        
        # Generate a random password (will be reset by admin)
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        new_lead.set_password(temp_password)
        
        db.session.add(new_lead)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lead imported successfully',
            'lead_id': new_lead.id
        }), 201
        
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