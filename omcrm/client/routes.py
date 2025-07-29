from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from flask import Blueprint, render_template, flash, redirect, url_for, json, request, jsonify, abort, current_app
from flask_login import login_required, current_user
import plotly.graph_objs as go
import plotly
import json
import numpy as np
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Optional
import os
import secrets
from PIL import Image

from omcrm.leads.models import Lead
from omcrm.webtrader.models import Trade, TradingInstrument
from omcrm.transactions.models import Deposit, Withdrawal
from omcrm import db
from omcrm.activities.models import Activity

client = Blueprint('client', __name__)

# 🕒 NEW: Track client activity on each request
@client.before_request
def track_client_activity():
    """Update last_seen timestamp for authenticated clients"""
    if current_user.is_authenticated and isinstance(current_user, Lead) and current_user.is_client:
        # Update last seen every 5 minutes to avoid too many DB writes
        if (not current_user.last_seen_at or 
            (datetime.utcnow() - current_user.last_seen_at).total_seconds() > 300):
            current_user.update_last_seen()

# Client authentication decorator
def client_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        actual_user = current_user._get_current_object()
        
        # Check if user is a Lead instance and is marked as a client
        if not isinstance(actual_user, Lead) or not actual_user.is_client:
            if request.is_xhr or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Access denied'}), 403
            flash("Access denied. This area is only for clients.", 'danger')
            return redirect(url_for('main.home'))
            
        # Remove the automatic redirection to webtrader
        # if request.path == url_for('client.dashboard'):
        #    return redirect(url_for('webtrader.webtrader_dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function


@client.route("/client/dashboard")
@login_required
@client_only
def dashboard():
    actual_user = current_user._get_current_object()

    # Fetch client-specific data
    balance = getattr(actual_user, 'current_balance', 0)

    # Fetch trades for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    trades = Trade.query.filter(Trade.lead_id == actual_user.id, Trade.date >= thirty_days_ago).order_by(
        Trade.date).all()

    # Prepare data for the chart
    trade_dates = [trade.date for trade in trades]
    trade_amounts = [trade.amount if trade.trade_type == 'buy' else -trade.amount for trade in trades]

    # Calculate cumulative profit/loss
    cumulative_pl = [sum(trade_amounts[:i + 1]) for i in range(len(trade_amounts))]

    # Create the chart
    fig = go.Figure(data=[go.Scatter(x=trade_dates, y=cumulative_pl, mode='lines+markers')])
    fig.update_layout(title='Trade History (Last 30 Days)', xaxis_title='Date', yaxis_title='Cumulative Profit/Loss')
    chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # Format dates for JavaScript
    dates = [date.strftime('%Y-%m-%d') for date in trade_dates] if trade_dates else []

    return render_template("client/dashboard.html",
                           title="Client Dashboard",
                           balance=balance,
                           trades=trades,
                           chart_json=chart_json,
                           actual_user=actual_user,
                           now=datetime.utcnow(),
                           dates=dates,
                           cumulative_pl=cumulative_pl)

@client.route("/client/trade_analytics")
@login_required
@client_only
def trade_analytics():
    """Display comprehensive trading analytics"""
    actual_user = current_user._get_current_object()
    
    # Get all trades for this client
    trades = Trade.query.filter_by(lead_id=actual_user.id).order_by(Trade.date.desc()).all()
    
    # Calculate metrics
    metrics = calculate_trading_metrics(trades)
    
    # Generate chart data
    cumulative_pl_data = generate_cumulative_pl_chart(trades)
    monthly_performance_data = generate_monthly_performance_chart(trades)
    instrument_performance_data = generate_instrument_performance_chart(trades)
    win_loss_distribution_data = generate_win_loss_distribution_chart(trades)
    
    # Create JSON strings for direct embedding in JavaScript
    # We encode once with dumps() - no need for escaping quotes since we handle parsing in JS
    cumulative_pl_json = json.dumps(cumulative_pl_data, cls=plotly.utils.PlotlyJSONEncoder)
    monthly_performance_json = json.dumps(monthly_performance_data, cls=plotly.utils.PlotlyJSONEncoder)
    instrument_performance_json = json.dumps(instrument_performance_data, cls=plotly.utils.PlotlyJSONEncoder)
    win_loss_distribution_json = json.dumps(win_loss_distribution_data, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template("client/trade_analytics.html",
                          title="Trading Analytics",
                          trades=trades,
                          metrics=metrics,
                          cumulative_pl_data=cumulative_pl_json,
                          monthly_performance_data=monthly_performance_json,
                          instrument_performance_data=instrument_performance_json,
                          win_loss_distribution_data=win_loss_distribution_json,
                          now=datetime.utcnow())

@client.route("/client/trade/<int:trade_id>")
@login_required
@client_only
def view_trade_details(trade_id):
    """Display detailed view of an individual trade"""
    actual_user = current_user._get_current_object()
    
    # Get the trade and check ownership
    trade = Trade.query.get_or_404(trade_id)
    if trade.lead_id != actual_user.id:
        abort(403)  # Forbidden - not their trade
    
    # Calculate ROI for closed trades
    roi = trade.calculate_roi() if trade.status == 'closed' else 0
    
    # Get holding period
    holding_period = trade.get_holding_period()
    
    # Get similar trades (same instrument and direction)
    similar_trades = Trade.query.filter(
        Trade.lead_id == actual_user.id,
        Trade.instrument_id == trade.instrument_id,
        Trade.trade_type == trade.trade_type,
        Trade.id != trade.id,
        Trade.status == 'closed'
    ).order_by(Trade.date.desc()).limit(5).all()
    
    # Generate price chart data
    price_chart_data = generate_price_chart_data(trade)
    
    # Sample market conditions data (in a real app, this would come from market analysis)
    market_conditions = [
        {'name': 'Market Volatility', 'impact': 'Medium', 'impact_class': 'warning'},
        {'name': 'Trend Direction', 'impact': 'Positive', 'impact_class': 'success'},
        {'name': 'Volume', 'impact': 'High', 'impact_class': 'info'},
        {'name': 'News Sentiment', 'impact': 'Neutral', 'impact_class': 'secondary'}
    ]
    
    return render_template("client/trade_details.html",
                          title=f"Trade Details - {trade.instrument.symbol}",
                          trade=trade,
                          roi=roi,
                          holding_period=holding_period,
                          similar_trades=similar_trades,
                          market_conditions=market_conditions,
                          price_chart_data=json.dumps(price_chart_data, cls=plotly.utils.PlotlyJSONEncoder),
                          now=datetime.utcnow())

@client.route("/client/save_trade_notes", methods=['POST'])
@login_required
@client_only
def save_trade_notes():
    """AJAX route to save notes for a trade"""
    actual_user = current_user._get_current_object()
    
    trade_id = request.form.get('trade_id')
    notes = request.form.get('notes')
    
    if not trade_id:
        return jsonify({'success': False, 'error': 'Trade ID is required'})
    
    # Get the trade and check ownership
    trade = Trade.query.get_or_404(trade_id)
    if trade.lead_id != actual_user.id:
        return jsonify({'success': False, 'error': 'You don\'t have permission to edit this trade'})
    
    # Update notes
    trade.notes = notes
    db.session.commit()
    
    return jsonify({'success': True})

@client.route("/client/update_trading_status", methods=['POST'])
@login_required
@client_only
def update_trading_status():
    """AJAX route to update a client's trading status"""
    actual_user = current_user._get_current_object()
    
    # Get the available_to_trade value from the form
    available_to_trade = request.form.get('available_to_trade', 'false')
    
    # Convert string to boolean
    is_available = available_to_trade.lower() == 'true'
    
    try:
        # Update the client's trading status
        actual_user.available_to_trade = is_available
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@client.route("/client/deposit", methods=['GET', 'POST'])
@login_required
@client_only
def deposit():
    """Handle deposit requests from clients"""
    # Check that the user is a client
    actual_user = current_user._get_current_object()
    if not isinstance(actual_user, Lead) or not actual_user.is_client:
        flash("Access denied", 'danger')
        return redirect(url_for('main.home'))
    
    # Create a form with CSRF protection
    from flask_wtf import FlaskForm
    from wtforms import HiddenField
    class EmptyForm(FlaskForm):
        pass
    
    form = EmptyForm()
    
    # Get deposit history for this client
    deposits = Deposit.query.filter_by(lead_id=actual_user.id).order_by(Deposit.date.desc()).all()
    
    # In a real application, this would process the form data and create a deposit record
    # For the demo, just show the template with the form and history
    return render_template("client/deposit.html",
                          title="Deposit Funds",
                          form=form,
                          current_user=actual_user,
                          deposit_history=deposits,
                          now=datetime.utcnow())

@client.route("/client/process_deposit", methods=['POST'])
@login_required
@client_only
def process_deposit():
    """Process a deposit request submitted via form"""
    # Check that the user is a client
    actual_user = current_user._get_current_object()
    if not isinstance(actual_user, Lead) or not actual_user.is_client:
        flash("Access denied", 'danger')
        return redirect(url_for('main.home'))
    
    # Extract form data
    amount = request.form.get('amount', 0)
    payment_method = request.form.get('payment_method', 'crypto')
    crypto_type = request.form.get('crypto_currency', None) if payment_method == 'crypto' else None
    notes = request.form.get('notes', '')
    
    print(f"DEBUG: Processing deposit - Amount: ${amount}, Method: {payment_method}")
    
    try:
        # Validate amount
        amount = float(amount)
        if amount < 100:
            flash("Minimum deposit amount is $100", 'danger')
            return redirect(url_for('client.deposit'))
        
        # Create deposit record
        deposit = Deposit(
            lead_id=actual_user.id,
            amount=amount,
            method=payment_method,
            crypto_type=crypto_type,
            notes=notes,
            status='pending'
        )
        
        db.session.add(deposit)
        db.session.commit()
        
        # Log the activity
        Activity.log(
            action_type='deposit_requested',
            description=f"Client requested a deposit of ${amount:.2f}",
            lead=actual_user,
            target_type='deposit',
            target_id=deposit.id,
            data={
                'amount': float(amount),
                'method': payment_method,
                'crypto_type': crypto_type
            }
        )
        
        print(f"DEBUG: Deposit created successfully - ID: {deposit.id}, Status: {deposit.status}")
        
        flash(f"Your deposit request for ${amount:.2f} has been submitted successfully!", 'success')
        return redirect(url_for('client.deposit'))
        
    except ValueError:
        print("DEBUG: ValueError - Invalid amount")
        flash("Invalid amount", 'danger')
        return redirect(url_for('client.deposit'))
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error creating deposit - {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('client.deposit'))

@client.route("/client/withdraw", methods=['GET', 'POST'])
@login_required
@client_only
def withdraw():
    """Handle withdrawal requests from clients"""
    # Check that the user is a client
    actual_user = current_user._get_current_object()
    if not isinstance(actual_user, Lead) or not actual_user.is_client:
        flash("Access denied", 'danger')
        return redirect(url_for('main.home'))
    
    # Create a form with CSRF protection
    from flask_wtf import FlaskForm
    from wtforms import HiddenField
    class EmptyForm(FlaskForm):
        pass
    
    form = EmptyForm()
    
    # Get withdrawal history for this client
    withdrawals = Withdrawal.query.filter_by(lead_id=actual_user.id).order_by(Withdrawal.date.desc()).all()
    
    # In a real application, this would process the form data and create a withdrawal record
    # For the demo, just show the template with the form and history
    return render_template("client/withdraw.html",
                          title="Withdraw Funds",
                          form=form,
                          current_user=actual_user,
                          withdrawal_history=withdrawals,
                          now=datetime.utcnow())

@client.route("/client/process_withdrawal", methods=['POST'])
@login_required
@client_only
def process_withdrawal():
    """Process a withdrawal request submitted via form"""
    # Check that the user is a client
    actual_user = current_user._get_current_object()
    if not isinstance(actual_user, Lead) or not actual_user.is_client:
        flash("Access denied", 'danger')
        return redirect(url_for('main.home'))
    
    # Extract form data
    amount = request.form.get('amount', 0)
    withdrawal_method = request.form.get('withdrawal_method', 'crypto')
    
    # Crypto-specific fields
    crypto_type = request.form.get('crypto_currency', None) if withdrawal_method == 'crypto' else None
    wallet_address = request.form.get('crypto_address', None) if withdrawal_method == 'crypto' else None
    
    # Bank-specific fields
    bank_name = request.form.get('bank_name', None) if withdrawal_method == 'wire' else None
    account_holder = request.form.get('account_holder', None) if withdrawal_method == 'wire' else None
    account_number = request.form.get('account_number', None) if withdrawal_method == 'wire' else None
    swift_code = request.form.get('swift_code', None) if withdrawal_method == 'wire' else None
    
    notes = request.form.get('notes', '')
    
    print(f"DEBUG: Processing withdrawal - Amount: ${amount}, Method: {withdrawal_method}")
    
    try:
        # Validate amount
        amount = float(amount)
        if amount < 100:
            flash("Minimum withdrawal amount is $100", 'danger')
            return redirect(url_for('client.withdraw'))
        
        # Check if client has sufficient balance
        if amount > actual_user.current_balance:
            flash("Insufficient balance for this withdrawal", 'danger')
            return redirect(url_for('client.withdraw'))
        
        # Create withdrawal record
        withdrawal = Withdrawal(
            lead_id=actual_user.id,
            amount=amount,
            method=withdrawal_method,
            crypto_type=crypto_type,
            wallet_address=wallet_address,
            bank_name=bank_name,
            account_holder=account_holder,
            account_number=account_number,
            swift_code=swift_code,
            notes=notes,
            status='pending'
        )
        
        db.session.add(withdrawal)
        db.session.commit()
        
        # Log the activity
        Activity.log(
            action_type='withdrawal_requested',
            description=f"Client requested a withdrawal of ${amount:.2f}",
            lead=actual_user,
            target_type='withdrawal',
            target_id=withdrawal.id,
            data={
                'amount': float(amount),
                'method': withdrawal_method,
                'crypto_type': crypto_type if withdrawal_method == 'crypto' else None
            }
        )
        
        print(f"DEBUG: Withdrawal created successfully - ID: {withdrawal.id}, Status: {withdrawal.status}")
        
        flash(f"Your withdrawal request for ${amount:.2f} has been submitted successfully!", 'success')
        return redirect(url_for('client.withdraw'))
        
    except ValueError:
        print("DEBUG: ValueError - Invalid amount")
        flash("Invalid amount", 'danger')
        return redirect(url_for('client.withdraw'))
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error creating withdrawal - {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('client.withdraw'))

@client.route("/client/profile", methods=['GET', 'POST'])
@login_required
@client_only
def profile():
    """Display and update profile settings"""
    actual_user = current_user._get_current_object()
    
    class ProfileUpdateForm(FlaskForm):
        picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
        password = PasswordField('New Password', validators=[Optional(), Length(min=6, message="Password must be at least 6 characters")])
        confirm_password = PasswordField('Confirm Password', validators=[EqualTo('password', message="Passwords must match")])
        submit = SubmitField('Update Profile')
    
    form = ProfileUpdateForm()
    
    if form.validate_on_submit():
        changes_made = False
        
        # Handle profile picture upload
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            actual_user.profile_image = picture_file
            changes_made = True
        
        # Update password only if provided
        if form.password.data:
            actual_user.password = form.password.data
            flash('Your password has been updated!', 'success')
            changes_made = True
        
        if changes_made:
            db.session.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('client.profile'))
        
    return render_template('client/profile.html', 
                          title='Profile Settings',
                          form=form,
                          user=actual_user)

def save_picture(form_picture):
    """Save profile picture with a random name and resized"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_imgs', picture_fn)
    
    # Resize image
    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn

# Helper functions for analytics
def calculate_trading_metrics(trades):
    """Calculate trading performance metrics"""
    metrics = {
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0.0,
        'total_pnl': 0.0,
        'total_profit': 0.0,
        'total_loss': 0.0,
        'avg_profit_per_winning_trade': 0.0,
        'avg_loss_per_losing_trade': 0.0,
        'profit_factor': 0.0,
        'max_drawdown': 0.0,
        'risk_reward_ratio': 0.0,
        'sharpe_ratio': 0.0
    }
    
    # Only consider closed trades with valid profit/loss for most metrics
    closed_trades = [t for t in trades if t.status == 'closed' and t.profit_loss is not None]
    
    if not closed_trades:
        return metrics
    
    # Basic metrics
    metrics['total_trades'] = len(closed_trades)
    
    # Count winning and losing trades
    winning_trades = [t for t in closed_trades if t.profit_loss > 0]
    losing_trades = [t for t in closed_trades if t.profit_loss < 0]
    metrics['winning_trades'] = len(winning_trades)
    metrics['losing_trades'] = len(losing_trades)
    
    # Win rate
    if metrics['total_trades'] > 0:
        metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100
    
    # P/L metrics
    metrics['total_pnl'] = sum(t.profit_loss for t in closed_trades)
    metrics['total_profit'] = sum(t.profit_loss for t in winning_trades) if winning_trades else 0
    metrics['total_loss'] = abs(sum(t.profit_loss for t in losing_trades)) if losing_trades else 0
    
    # Average metrics
    if winning_trades:
        metrics['avg_profit_per_winning_trade'] = metrics['total_profit'] / len(winning_trades)
    if losing_trades:
        metrics['avg_loss_per_losing_trade'] = metrics['total_loss'] / len(losing_trades)
    
    # Profit factor
    if metrics['total_loss'] > 0:
        metrics['profit_factor'] = metrics['total_profit'] / metrics['total_loss']
    elif metrics['total_profit'] > 0:
        metrics['profit_factor'] = float('inf')  # No losses, all profit
    
    # Risk-reward ratio
    if metrics['avg_loss_per_losing_trade'] > 0:
        metrics['risk_reward_ratio'] = metrics['avg_profit_per_winning_trade'] / metrics['avg_loss_per_losing_trade']
    
    # Calculate max drawdown (simplistic version)
    pnl_values = [t.profit_loss for t in closed_trades]
    cum_pnl = np.cumsum(pnl_values)
    max_drawdown = 0
    peak = cum_pnl[0]
    
    for value in cum_pnl:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    metrics['max_drawdown'] = max_drawdown
    
    # Simplified Sharpe ratio (returns / standard deviation of returns)
    if len(closed_trades) > 1:
        # Avoid division by zero by filtering out trades with price or amount = 0
        valid_trades = [t for t in closed_trades if t.price > 0 and t.amount > 0]
        if valid_trades:
            returns = [t.profit_loss / (t.price * t.amount) for t in valid_trades]
            if returns and np.std(returns) > 0:
                metrics['sharpe_ratio'] = np.mean(returns) / np.std(returns)
    
    return metrics

def generate_cumulative_pl_chart(trades):
    """Generate cumulative P/L chart data"""
    # Sort trades by date
    sorted_trades = sorted([t for t in trades if t.status == 'closed' and t.profit_loss is not None], 
                        key=lambda x: x.date)
    
    if not sorted_trades:
        # Generate sample chart data to show when no real data exists
        now = datetime.utcnow()
        sample_dates = [now - timedelta(days=30-i) for i in range(31)]
        # Generate a sample trend line that goes from 0 to 150
        sample_values = [i * 5 for i in range(31)]
        
        return {
            'data': [{
                'x': sample_dates, 
                'y': sample_values, 
                'type': 'scatter',
                'mode': 'lines',
                'name': 'Sample Data', 
                'line': {'color': '#CCCCCC', 'width': 2, 'dash': 'dash'}
            }],
            'layout': {
                'title': 'Sample Data (No Trades)',
                'annotations': [{
                    'text': 'Complete trades to see your performance',
                    'showarrow': False,
                    'x': 0.5,
                    'y': 0.5,
                    'xref': 'paper',
                    'yref': 'paper',
                    'font': {'size': 16, 'color': '#888'}
                }],
                'xaxis': {'title': 'Date', 'showgrid': True},
                'yaxis': {'title': 'P/L ($)', 'showgrid': True},
                'hovermode': 'closest',
                'margin': {'l': 50, 'r': 40, 'b': 50, 't': 50},
                'plot_bgcolor': 'rgba(240, 240, 240, 0.8)'
            }
        }
    
    # Calculate cumulative P/L
    dates = [t.date for t in sorted_trades]
    pl_values = [t.profit_loss for t in sorted_trades]
    cumulative_pl = np.cumsum(pl_values).tolist()
    
    # Create chart data
    data = [
        {
            'x': dates,
            'y': cumulative_pl,
            'type': 'scatter',
            'mode': 'lines',
            'name': 'Cumulative P/L',
            'line': {'color': '#3366CC', 'width': 2}
        }
    ]
    
    # Create layout
    layout = {
        'title': 'Cumulative Profit/Loss Over Time',
        'xaxis': {'title': 'Date', 'showgrid': True},
        'yaxis': {'title': 'P/L ($)', 'showgrid': True},
        'hovermode': 'closest',
        'margin': {'l': 50, 'r': 40, 'b': 50, 't': 50},
        'plot_bgcolor': 'rgba(240, 240, 240, 0.8)'
    }
    
    return {'data': data, 'layout': layout}

def generate_monthly_performance_chart(trades):
    """Generate monthly performance chart data"""
    # Filter for closed trades with valid P/L
    closed_trades = [t for t in trades if t.status == 'closed' and t.profit_loss is not None]
    
    if not closed_trades:
        # Generate sample chart data for monthly performance
        current_month = datetime.utcnow().month
        months = [(datetime.utcnow().replace(day=1) - timedelta(days=30*i)).strftime('%b %Y') for i in range(6)]
        months.reverse()  # Show most recent months last
        values = [120, -80, 200, -50, 300, 180]  # Sample P/L values
        colors = ['#4CAF50' if val >= 0 else '#F44336' for val in values]
        
        return {
            'data': [{
                'x': months,
                'y': values,
                'type': 'bar',
                'marker': {'color': colors},
                'name': 'Sample Monthly P/L'
            }],
            'layout': {
                'title': 'Sample Monthly Performance',
                'annotations': [{
                    'text': 'Sample data shown',
                    'showarrow': False,
                    'x': 0.5,
                    'y': 0.9,
                    'xref': 'paper',
                    'yref': 'paper',
                    'font': {'size': 12, 'color': '#888'}
                }],
                'xaxis': {'title': 'Month', 'tickangle': -45},
                'yaxis': {'title': 'P/L ($)'},
                'margin': {'l': 50, 'r': 40, 'b': 80, 't': 50},
                'plot_bgcolor': 'rgba(240, 240, 240, 0.8)'
            }
        }
    
    # Group P/L by month
    monthly_pl = defaultdict(float)
    for trade in closed_trades:
        month_key = trade.date.strftime('%Y-%m')
        monthly_pl[month_key] += trade.profit_loss
    
    # Sort by month
    sorted_months = sorted(monthly_pl.keys())
    month_labels = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months]
    pl_values = [monthly_pl[m] for m in sorted_months]
    
    # Create bar colors based on profit/loss
    colors = ['#4CAF50' if val >= 0 else '#F44336' for val in pl_values]
    
    # Create chart data
    data = [
        {
            'x': month_labels,
            'y': pl_values,
            'type': 'bar',
            'marker': {'color': colors},
            'name': 'Monthly P/L'
        }
    ]
    
    # Create layout
    layout = {
        'title': 'Monthly Performance',
        'xaxis': {'title': 'Month', 'tickangle': -45},
        'yaxis': {'title': 'P/L ($)'},
        'margin': {'l': 50, 'r': 40, 'b': 80, 't': 50},
        'plot_bgcolor': 'rgba(240, 240, 240, 0.8)'
    }
    
    return {'data': data, 'layout': layout}

def generate_instrument_performance_chart(trades):
    """Generate performance by instrument chart data"""
    # Filter for closed trades with valid P/L
    closed_trades = [t for t in trades if t.status == 'closed' and t.profit_loss is not None]
    
    if not closed_trades:
        # Sample data for instrument performance
        sample_instruments = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'DOGE/USD']
        sample_values = [450, 250, 150, -80, -30]
        
        return {
            'data': [{
                'labels': sample_instruments,
                'values': sample_values,
                'type': 'pie',
                'hole': 0.4,
                'marker': {
                    'colors': ['#3366CC', '#DC3912', '#FF9900', '#109618', '#990099']
                },
                'textinfo': 'label+percent',
                'insidetextorientation': 'radial'
            }],
            'layout': {
                'title': 'Sample Instrument Performance',
                'annotations': [{
                    'text': 'Sample data',
                    'showarrow': False,
                    'x': 0.5,
                    'y': 0.5,
                    'xref': 'paper',
                    'yref': 'paper',
                    'font': {'size': 14, 'color': '#888'}
                }],
                'margin': {'l': 40, 'r': 40, 'b': 40, 't': 50},
                'showlegend': False
            }
        }
    
    # Group P/L by instrument
    instrument_pl = defaultdict(float)
    for trade in closed_trades:
        if trade.instrument:
            instrument_pl[trade.instrument.symbol] += trade.profit_loss
    
    # Prepare data for pie chart
    labels = list(instrument_pl.keys())
    values = list(instrument_pl.values())
    
    # Create chart data
    data = [
        {
            'labels': labels,
            'values': values,
            'type': 'pie',
            'hole': 0.4,
            'marker': {
                'colors': ['#3366CC', '#DC3912', '#FF9900', '#109618', '#990099', '#0099C6', '#DD4477']
            },
            'textinfo': 'label+percent',
            'insidetextorientation': 'radial'
        }
    ]
    
    # Create layout
    layout = {
        'title': 'P/L by Instrument',
        'margin': {'l': 40, 'r': 40, 'b': 40, 't': 50},
        'showlegend': False
    }
    
    return {'data': data, 'layout': layout}

def generate_win_loss_distribution_chart(trades):
    """Generate win/loss distribution chart data"""
    # Filter for closed trades with valid P/L
    closed_trades = [t for t in trades if t.status == 'closed' and t.profit_loss is not None]
    
    if not closed_trades:
        # Sample win/loss distribution
        return {
            'data': [{
                'labels': ['Winning Trades', 'Losing Trades', 'Break Even'],
                'values': [6, 4, 1],
                'type': 'pie',
                'marker': {
                    'colors': ['#4CAF50', '#F44336', '#9E9E9E']
                },
                'textinfo': 'label+percent',
                'hole': 0.4
            }],
            'layout': {
                'title': 'Sample Win/Loss Distribution',
                'annotations': [{
                    'text': 'Sample data',
                    'showarrow': False,
                    'x': 0.5,
                    'y': 0.5,
                    'xref': 'paper',
                    'yref': 'paper',
                    'font': {'size': 14, 'color': '#888'}
                }],
                'margin': {'l': 40, 'r': 40, 'b': 40, 't': 50},
                'showlegend': False
            }
        }
    
    # Count winning and losing trades
    winning_trades = len([t for t in closed_trades if t.profit_loss > 0])
    losing_trades = len([t for t in closed_trades if t.profit_loss < 0])
    break_even_trades = len([t for t in closed_trades if t.profit_loss == 0])
    
    # Create chart data
    data = [
        {
            'labels': ['Winning Trades', 'Losing Trades', 'Break Even'],
            'values': [winning_trades, losing_trades, break_even_trades],
            'type': 'pie',
            'marker': {
                'colors': ['#4CAF50', '#F44336', '#9E9E9E']
            },
            'textinfo': 'label+percent',
            'hole': 0.4
        }
    ]
    
    # Create layout
    layout = {
        'title': 'Win/Loss Distribution',
        'margin': {'l': 40, 'r': 40, 'b': 40, 't': 50},
        'showlegend': False
    }
    
    return {'data': data, 'layout': layout}

def generate_price_chart_data(trade):
    """Generate price chart data for a specific trade"""
    # In a real app, this would fetch historical price data for the instrument
    # For this example, we'll create a simulated chart
    
    # Create sample price data around the trade entry/exit points
    instrument = trade.instrument
    if not instrument:
        # Empty placeholder chart if no instrument
        return {
            'data': [{'x': [], 'y': [], 'type': 'scatter', 'name': 'Price'}],
            'layout': {'title': 'Price Chart (No Data)', 'xaxis': {'title': 'Date'}, 'yaxis': {'title': 'Price ($)'}}
        }
    
    # Calculate date range: 7 days before trade to 7 days after (or today if open)
    start_date = trade.date - timedelta(days=7)
    
    if trade.status == 'closed' and trade.closing_date:
        end_date = trade.closing_date + timedelta(days=7)
    else:
        end_date = datetime.utcnow()
    
    # Ensure we don't go into the future
    if end_date > datetime.utcnow():
        end_date = datetime.utcnow()
    
    # Generate daily timestamps between start and end dates
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Generate price data (simulated)
    # Start with entry price and add some random fluctuations
    base_price = trade.price
    
    # For a closed trade, create a path from entry to exit price
    if trade.status == 'closed' and trade.closing_price:
        exit_price = trade.closing_price
        price_diff = exit_price - base_price
        days = len(dates)
        
        # Linear progression plus random noise
        prices = []
        for i, _ in enumerate(dates):
            progress_factor = i / max(days-1, 1)  # Avoid division by zero
            linear_part = base_price + (price_diff * progress_factor)
            random_noise = np.random.normal(0, abs(base_price * 0.01))  # 1% volatility
            prices.append(max(0.01, linear_part + random_noise))  # Ensure no negative prices
    else:
        # For open trades, just use random walk with slight trend
        trend = 0.001 * np.random.choice([-1, 1])  # Slight up or down trend
        prices = [base_price]
        for _ in range(1, len(dates)):
            random_change = np.random.normal(trend, abs(base_price * 0.02))
            new_price = max(0.01, prices[-1] + random_change)
            prices.append(new_price)
    
    # Create trace for price chart
    price_trace = {
        'x': dates,
        'y': prices,
        'type': 'scatter',
        'mode': 'lines',
        'name': instrument.symbol,
        'line': {'color': '#3366CC', 'width': 2}
    }
    
    # Add entry point marker
    entry_marker = {
        'x': [trade.date],
        'y': [trade.price],
        'type': 'scatter',
        'mode': 'markers',
        'marker': {
            'symbol': 'triangle-up' if trade.trade_type == 'buy' else 'triangle-down',
            'color': 'green' if trade.trade_type == 'buy' else 'red',
            'size': 12,
            'line': {'width': 1, 'color': 'black'}
        },
        'name': 'Entry Point'
    }
    
    data = [price_trace, entry_marker]
    
    # Add exit point marker for closed trades
    if trade.status == 'closed' and trade.closing_date and trade.closing_price:
        exit_marker = {
            'x': [trade.closing_date],
            'y': [trade.closing_price],
            'type': 'scatter',
            'mode': 'markers',
            'marker': {
                'symbol': 'circle',
                'color': 'green' if trade.profit_loss > 0 else 'red',
                'size': 12,
                'line': {'width': 1, 'color': 'black'}
            },
            'name': 'Exit Point'
        }
        data.append(exit_marker)
    
    # Create layout
    layout = {
        'title': f'{instrument.symbol} Price Chart',
        'xaxis': {'title': 'Date', 'showgrid': True},
        'yaxis': {'title': 'Price ($)', 'showgrid': True},
        'hovermode': 'closest',
        'margin': {'l': 60, 'r': 40, 'b': 50, 't': 50},
        'legend': {'orientation': 'h', 'y': -0.2},
        'plot_bgcolor': 'rgba(230, 230, 230, 0.5)'
    }
    
    return {'data': data, 'layout': layout}

@client.route("/client/chart_debug")
@login_required
@client_only
def chart_debug():
    """Debug chart data and Plotly setup"""
    actual_user = current_user._get_current_object()
    
    # Get all trades for debugging
    trades = Trade.query.filter_by(lead_id=actual_user.id).order_by(Trade.date.desc()).all()
    closed_trades = [t for t in trades if t.status == 'closed' and t.profit_loss is not None]
    
    debug_info = {
        'total_trades': len(trades),
        'closed_trades': len(closed_trades),
        'open_trades': len([t for t in trades if t.status == 'open']),
        'trades_with_pl': len([t for t in trades if t.profit_loss is not None]),
        'numpy_available': False,
        'plotly_available': False,
        'sample_trades': []
    }
    
    # Check imports
    try:
        import numpy as np
        debug_info['numpy_available'] = True
        debug_info['numpy_version'] = np.__version__
    except ImportError:
        debug_info['numpy_error'] = "NumPy not available"
    
    try:
        import plotly
        debug_info['plotly_available'] = True
        debug_info['plotly_version'] = plotly.__version__
    except ImportError:
        debug_info['plotly_error'] = "Plotly not available"
    
    # Sample trade data for debugging
    for trade in trades[:5]:
        debug_info['sample_trades'].append({
            'id': trade.id,
            'date': trade.date.isoformat() if trade.date else None,
            'status': trade.status,
            'profit_loss': trade.profit_loss,
            'price': trade.price,
            'amount': trade.amount
        })
    
    # Test chart generation
    try:
        chart_data = generate_cumulative_pl_chart(trades)
        debug_info['chart_generation'] = 'success'
        debug_info['chart_data_keys'] = list(chart_data.keys())
        if 'data' in chart_data:
            debug_info['chart_data_length'] = len(chart_data['data'])
    except Exception as e:
        debug_info['chart_generation'] = 'failed'
        debug_info['chart_error'] = str(e)
    
    return jsonify(debug_info)

