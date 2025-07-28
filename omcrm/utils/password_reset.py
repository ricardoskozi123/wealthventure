"""
Password Reset Token Management
Handles secure password reset tokens with expiration
"""
import secrets
import string
from datetime import datetime, timedelta
from omcrm import db
from omcrm.users.models import User
from omcrm.leads.models import Lead
from flask import current_app


class PasswordResetToken(db.Model):
    """
    Model for tracking password reset tokens
    """
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    user_type = db.Column(db.String(20), nullable=False)  # 'user' or 'client'
    user_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    brand_name = db.Column(db.String(100), nullable=True)
    
    def __init__(self, email, user_type, user_id, expiry_minutes=30, ip_address=None, brand_name=None):
        self.token = self.generate_secure_token()
        self.email = email
        self.user_type = user_type
        self.user_id = user_id
        self.expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        self.ip_address = ip_address
        self.brand_name = brand_name
    
    @staticmethod
    def generate_secure_token(length=64):
        """Generate a cryptographically secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def is_expired(self):
        """Check if the token has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if the token is valid (not used and not expired)"""
        return not self.used and not self.is_expired()
    
    def mark_as_used(self):
        """Mark the token as used"""
        self.used = True
        self.used_at = datetime.utcnow()
        db.session.commit()
    
    def get_user(self):
        """Get the associated user object"""
        if self.user_type == 'user':
            return User.query.get(self.user_id)
        elif self.user_type == 'client':
            return Lead.query.get(self.user_id)
        return None
    
    @staticmethod
    def cleanup_expired_tokens():
        """Remove expired tokens from database (maintenance task)"""
        expired_tokens = PasswordResetToken.query.filter(
            PasswordResetToken.expires_at < datetime.utcnow()
        ).all()
        
        for token in expired_tokens:
            db.session.delete(token)
        
        db.session.commit()
        return len(expired_tokens)
    
    def __repr__(self):
        return f'<PasswordResetToken {self.email} - {self.user_type}>'


class PasswordResetManager:
    """
    Service class for managing password reset operations
    """
    
    @staticmethod
    def create_reset_token(email, expiry_minutes=30, ip_address=None, brand_name=None):
        """
        Create a password reset token for a user
        
        Args:
            email (str): User's email address
            expiry_minutes (int): Token expiry time in minutes
            ip_address (str): Client IP address for security logging
            brand_name (str): Brand context for multi-brand support
        
        Returns:
            dict: {'success': bool, 'token': PasswordResetToken or None, 'message': str, 'user_found': bool}
        """
        # Clean up old expired tokens first
        PasswordResetToken.cleanup_expired_tokens()
        
        # Find user by email (check both User and Lead tables)
        user = User.query.filter_by(email=email).first()
        lead = Lead.query.filter_by(email=email, is_client=True).first()
        
        if not user and not lead:
            return {
                'success': False,
                'token': None,
                'message': 'No account found with this email address.',
                'user_found': False
            }
        
        # Determine user type and details
        if user:
            user_type = 'user'
            user_id = user.id
            user_name = f"{user.first_name} {user.last_name}".strip()
            target_user = user
        else:
            user_type = 'client'
            user_id = lead.id
            user_name = f"{lead.first_name} {lead.last_name}".strip()
            target_user = lead
        
        # Check if user account is active
        if hasattr(target_user, 'is_active') and not target_user.is_active:
            return {
                'success': False,
                'token': None,
                'message': 'This account is inactive. Please contact support.',
                'user_found': True
            }
        
        if hasattr(target_user, 'is_user_active') and not target_user.is_user_active:
            return {
                'success': False,
                'token': None,
                'message': 'This account is inactive. Please contact support.',
                'user_found': True
            }
        
        # Invalidate any existing active tokens for this email
        existing_tokens = PasswordResetToken.query.filter_by(
            email=email, 
            used=False
        ).all()
        
        for token in existing_tokens:
            token.mark_as_used()
        
        # Create new reset token
        reset_token = PasswordResetToken(
            email=email,
            user_type=user_type,
            user_id=user_id,
            expiry_minutes=expiry_minutes,
            ip_address=ip_address,
            brand_name=brand_name
        )
        
        db.session.add(reset_token)
        db.session.commit()
        
        return {
            'success': True,
            'token': reset_token,
            'message': 'Password reset token created successfully.',
            'user_found': True,
            'user_name': user_name,
            'user_type': user_type
        }
    
    @staticmethod
    def validate_reset_token(token_string):
        """
        Validate a password reset token
        
        Args:
            token_string (str): The token string to validate
        
        Returns:
            dict: {'success': bool, 'token': PasswordResetToken or None, 'message': str, 'user': User/Lead or None}
        """
        if not token_string:
            return {
                'success': False,
                'token': None,
                'message': 'No token provided.',
                'user': None
            }
        
        # Find the token
        reset_token = PasswordResetToken.query.filter_by(token=token_string).first()
        
        if not reset_token:
            return {
                'success': False,
                'token': None,
                'message': 'Invalid or expired reset link.',
                'user': None
            }
        
        # Check if token is valid
        if not reset_token.is_valid():
            if reset_token.used:
                message = 'This reset link has already been used.'
            else:
                message = 'This reset link has expired.'
            
            return {
                'success': False,
                'token': reset_token,
                'message': message,
                'user': None
            }
        
        # Get the associated user
        user = reset_token.get_user()
        if not user:
            return {
                'success': False,
                'token': reset_token,
                'message': 'Associated user account not found.',
                'user': None
            }
        
        return {
            'success': True,
            'token': reset_token,
            'message': 'Token is valid.',
            'user': user
        }
    
    @staticmethod
    def reset_password(token_string, new_password):
        """
        Reset user password using a valid token
        
        Args:
            token_string (str): The reset token
            new_password (str): The new password
        
        Returns:
            dict: {'success': bool, 'message': str, 'user': User/Lead or None}
        """
        from omcrm import bcrypt
        
        # Validate the token first
        validation_result = PasswordResetManager.validate_reset_token(token_string)
        
        if not validation_result['success']:
            return validation_result
        
        reset_token = validation_result['token']
        user = validation_result['user']
        
        try:
            # Hash the new password
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            
            # Update user password
            user.password = hashed_password
            
            # Mark token as used
            reset_token.mark_as_used()
            
            # Commit changes
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Password has been reset successfully.',
                'user': user
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Failed to reset password: {str(e)}',
                'user': None
            }
    
    @staticmethod
    def get_reset_attempts(email, hours=24):
        """
        Get the number of reset attempts for an email in the last X hours
        
        Args:
            email (str): Email address
            hours (int): Time window in hours
        
        Returns:
            int: Number of reset attempts
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return PasswordResetToken.query.filter(
            PasswordResetToken.email == email,
            PasswordResetToken.created_at >= since
        ).count()
    
    @staticmethod
    def is_rate_limited(email, max_attempts=5, hours=24):
        """
        Check if an email is rate limited for password reset attempts
        
        Args:
            email (str): Email address
            max_attempts (int): Maximum attempts allowed
            hours (int): Time window in hours
        
        Returns:
            bool: True if rate limited
        """
        attempts = PasswordResetManager.get_reset_attempts(email, hours)
        return attempts >= max_attempts 