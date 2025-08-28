from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user

from omcrm import db
from omcrm.transactions.models import Deposit, Withdrawal
from omcrm.leads.models import Lead
from omcrm.users.models import User
from omcrm.rbac import is_admin, check_access
from omcrm.activities.models import Activity

transactions = Blueprint('transactions', __name__)


@transactions.route("/admin/transactions")
@login_required
@check_access('transactions', 'view')
def transactions_dashboard():
    """Admin dashboard for all transactions"""
    # Add debug logging
    print(f"DEBUG: Fetching transactions for dashboard")
    
    # Query all deposits and withdrawals
    deposits = Deposit.query.order_by(Deposit.date.desc()).all()
    withdrawals = Withdrawal.query.order_by(Withdrawal.date.desc()).all()
    
    print(f"DEBUG: Found {len(deposits)} deposits and {len(withdrawals)} withdrawals")
    
    # Filter for pending transactions
    pending_deposits = [d for d in deposits if d.status == 'pending']
    pending_withdrawals = [w for w in withdrawals if w.status == 'pending']
    
    print(f"DEBUG: Found {len(pending_deposits)} pending deposits and {len(pending_withdrawals)} pending withdrawals")
    
    # Get related users and leads for display
    users = {user.id: user for user in User.query.all()}
    leads = {lead.id: lead for lead in Lead.query.all()}

    # Debug for pending withdrawals - inspect details
    for pw in pending_withdrawals:
        print(f"DEBUG: Pending withdrawal: ID={pw.id}, Lead={pw.lead_id}, Amount=${pw.amount}, Status={pw.status}, Date={pw.date}")

    return render_template("admin/transactions.html",
                          title="Transaction Management",
                          deposits=deposits,
                          withdrawals=withdrawals,
                          pending_deposits=pending_deposits,
                          pending_withdrawals=pending_withdrawals,
                          users=users,
                          leads=leads)


@transactions.route("/admin/deposit/<int:deposit_id>/approve", methods=['POST'])
@login_required
@check_access('transactions', 'edit')
def approve_deposit(deposit_id):
    """Approve a deposit request"""
    deposit = Deposit.query.get_or_404(deposit_id)
    
    if deposit.status != 'pending':
        flash(f"Deposit #{deposit_id} is already {deposit.status}.", 'warning')
        return redirect(url_for('transactions.transactions_dashboard'))
    
    # Approve the deposit using the model method
    success = deposit.approve(current_user.id)
    
    if success:
        # Log the activity
        Activity.log(
            action_type='deposit_approved',
            description=f"Deposit #{deposit_id} of ${deposit.amount:.2f} has been approved",
            user=current_user,
            lead=deposit.lead,
            target_type='deposit',
            target_id=deposit_id,
            data={
                'amount': float(deposit.amount),
                'method': deposit.method
            }
        )
        
        flash(f"Deposit #{deposit_id} has been approved and ${deposit.amount:.2f} has been added to the client's balance.", 'success')
    else:
        flash(f"Failed to approve deposit #{deposit_id}.", 'danger')
    
    return redirect(url_for('transactions.transactions_dashboard'))


@transactions.route("/admin/deposit/<int:deposit_id>/reject", methods=['POST'])
@login_required
@check_access('transactions', 'edit')
def reject_deposit(deposit_id):
    """Reject a deposit request"""
    deposit = Deposit.query.get_or_404(deposit_id)
    
    if deposit.status != 'pending':
        flash(f"Deposit #{deposit_id} is already {deposit.status}.", 'warning')
        return redirect(url_for('transactions.transactions_dashboard'))
    
    # Reject the deposit using the model method
    success = deposit.reject(current_user.id)
    
    if success:
        # Log the activity
        Activity.log(
            action_type='deposit_rejected',
            description=f"Deposit #{deposit_id} of ${deposit.amount:.2f} has been rejected",
            user=current_user,
            lead=deposit.lead,
            target_type='deposit',
            target_id=deposit_id
        )
        
        flash(f"Deposit #{deposit_id} has been rejected.", 'success')
    else:
        flash(f"Failed to reject deposit #{deposit_id}.", 'danger')
    
    return redirect(url_for('transactions.transactions_dashboard'))


@transactions.route("/admin/withdrawal/<int:withdrawal_id>/approve", methods=['POST'])
@login_required
@check_access('transactions', 'edit')
def approve_withdrawal(withdrawal_id):
    """Approve a withdrawal request"""
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    
    if withdrawal.status != 'pending':
        flash(f"Withdrawal #{withdrawal_id} is already {withdrawal.status}.", 'warning')
        return redirect(url_for('transactions.transactions_dashboard'))
    
    # Get transaction reference if provided
    reference = request.form.get('reference', '')
    
    # Approve the withdrawal using the model method
    success = withdrawal.approve(current_user.id, reference)
    
    if success:
        # Log the activity
        Activity.log(
            action_type='withdrawal_approved',
            description=f"Withdrawal #{withdrawal_id} of ${withdrawal.amount:.2f} has been approved",
            user=current_user,
            lead=withdrawal.lead,
            target_type='withdrawal',
            target_id=withdrawal_id,
            data={
                'amount': float(withdrawal.amount),
                'method': withdrawal.method,
                'reference': reference if reference else None
            }
        )
        
        flash(f"Withdrawal #{withdrawal_id} has been approved and ${withdrawal.amount:.2f} has been deducted from the client's balance.", 'success')
    else:
        flash(f"Failed to approve withdrawal #{withdrawal_id}. Please ensure the client has sufficient balance.", 'danger')
    
    return redirect(url_for('transactions.transactions_dashboard'))


@transactions.route("/admin/withdrawal/<int:withdrawal_id>/reject", methods=['POST'])
@login_required
@check_access('transactions', 'edit')
def reject_withdrawal(withdrawal_id):
    """Reject a withdrawal request"""
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    
    if withdrawal.status != 'pending':
        flash(f"Withdrawal #{withdrawal_id} is already {withdrawal.status}.", 'warning')
        return redirect(url_for('transactions.transactions_dashboard'))
    
    # Get rejection reason if provided
    reason = request.form.get('reason', '')
    
    # Reject the withdrawal using the model method
    success = withdrawal.reject(current_user.id, reason)
    
    if success:
        # Log the activity
        Activity.log(
            action_type='withdrawal_rejected',
            description=f"Withdrawal #{withdrawal_id} of ${withdrawal.amount:.2f} has been rejected",
            user=current_user,
            lead=withdrawal.lead,
            target_type='withdrawal',
            target_id=withdrawal_id,
            data={
                'reason': reason if reason else None
            }
        )
        
        flash(f"Withdrawal #{withdrawal_id} has been rejected.", 'success')
    else:
        flash(f"Failed to reject withdrawal #{withdrawal_id}.", 'danger')
    
    return redirect(url_for('transactions.transactions_dashboard'))


@transactions.route("/admin/client/<int:client_id>/transactions")
@login_required
@check_access('transactions', 'view')
def client_transactions(client_id):
    """View all transactions for a specific client"""
    client = Lead.query.get_or_404(client_id)
    
    if not client.is_client:
        flash("This lead has not been converted to a client yet.", 'warning')
        return redirect(url_for('leads.leads_list'))
    
    deposits = Deposit.query.filter_by(lead_id=client_id).order_by(Deposit.date.desc()).all()
    withdrawals = Withdrawal.query.filter_by(lead_id=client_id).order_by(Withdrawal.date.desc()).all()
    
    # Get related users for display
    users = {user.id: user for user in User.query.all()}
    
    return render_template("admin/client_transactions.html",
                          title=f"Transactions for {client.first_name} {client.last_name}",
                          client=client,
                          deposits=deposits,
                          withdrawals=withdrawals,
                          users=users)


@transactions.route("/api/transactions/stats", methods=['GET'])
@login_required
@check_access('transactions', 'view')
def transaction_stats():
    """API endpoint for transaction statistics"""
    # Calculate statistics
    total_deposits = db.session.query(db.func.sum(Deposit.amount)).filter_by(status='approved').scalar() or 0
    total_withdrawals = db.session.query(db.func.sum(Withdrawal.amount)).filter_by(status='approved').scalar() or 0
    pending_deposits_count = Deposit.query.filter_by(status='pending').count()
    pending_withdrawals_count = Withdrawal.query.filter_by(status='pending').count()
    
    # Pending amounts
    pending_deposits_amount = db.session.query(db.func.sum(Deposit.amount)).filter_by(status='pending').scalar() or 0
    pending_withdrawals_amount = db.session.query(db.func.sum(Withdrawal.amount)).filter_by(status='pending').scalar() or 0
    
    return jsonify({
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'net_flow': total_deposits - total_withdrawals,
        'pending_deposits': {
            'count': pending_deposits_count,
            'amount': pending_deposits_amount
        },
        'pending_withdrawals': {
            'count': pending_withdrawals_count,
            'amount': pending_withdrawals_amount
        }
    })


@transactions.route("/admin/client/<int:client_id>/add-deposit", methods=['POST'])
@login_required
@check_access('transactions', 'create')
def add_manual_deposit(client_id):
    """Manually add a deposit for a client"""
    client = Lead.query.get_or_404(client_id)
    
    if not client.is_client:
        flash("This lead has not been converted to a client yet.", 'warning')
        return redirect(url_for('leads.leads_list'))
    
    amount = request.form.get('amount', '0')
    method = request.form.get('method', 'manual')
    notes = request.form.get('notes', '')
    auto_approve = request.form.get('auto_approve') == '1'
    
    try:
        amount = float(amount)
        if amount <= 0:
            flash("Amount must be greater than zero.", 'danger')
            return redirect(url_for('transactions.client_transactions', client_id=client_id))
        
        # Create deposit record
        deposit = Deposit(
            lead_id=client_id,
            amount=amount,
            method=method,
            notes=f"Manual deposit by {current_user.username}: {notes}",
            status='pending'
        )
        
        db.session.add(deposit)
        
        # Auto-approve if requested
        if auto_approve:
            db.session.flush()  # Ensure deposit has an ID
            deposit.approve(current_user.id)
            flash(f"Deposit of ${amount:.2f} has been created and approved.", 'success')
        else:
            db.session.commit()
            flash(f"Deposit of ${amount:.2f} has been created with pending status.", 'success')
        
        return redirect(url_for('transactions.client_transactions', client_id=client_id))
        
    except ValueError:
        flash("Invalid amount specified.", 'danger')
        return redirect(url_for('transactions.client_transactions', client_id=client_id))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('transactions.client_transactions', client_id=client_id))


@transactions.route("/admin/client/<int:client_id>/add-withdrawal", methods=['POST'])
@login_required
@check_access('transactions', 'create')
def add_manual_withdrawal(client_id):
    """Manually add a withdrawal for a client"""
    client = Lead.query.get_or_404(client_id)
    
    if not client.is_client:
        flash("This lead has not been converted to a client yet.", 'warning')
        return redirect(url_for('leads.leads_list'))
    
    amount = request.form.get('amount', '0')
    method = request.form.get('method', 'manual')
    reference = request.form.get('reference', '')
    notes = request.form.get('notes', '')
    auto_approve = request.form.get('auto_approve') == '1'
    
    try:
        amount = float(amount)
        if amount <= 0:
            flash("Amount must be greater than zero.", 'danger')
            return redirect(url_for('transactions.client_transactions', client_id=client_id))
        
        # Check if client has sufficient balance
        if amount > client.get_total_balance():
            flash("Insufficient balance for this withdrawal.", 'danger')
            return redirect(url_for('transactions.client_transactions', client_id=client_id))
        
        # Create withdrawal record
        withdrawal = Withdrawal(
            lead_id=client_id,
            amount=amount,
            method=method,
            reference=reference,
            notes=f"Manual withdrawal by {current_user.username}: {notes}",
            status='pending'
        )
        
        db.session.add(withdrawal)
        
        # Auto-approve if requested
        if auto_approve:
            db.session.flush()  # Ensure withdrawal has an ID
            withdrawal.approve(current_user.id, reference)
            flash(f"Withdrawal of ${amount:.2f} has been created and approved.", 'success')
        else:
            db.session.commit()
            flash(f"Withdrawal of ${amount:.2f} has been created with pending status.", 'success')
        
        return redirect(url_for('transactions.client_transactions', client_id=client_id))
        
    except ValueError:
        flash("Invalid amount specified.", 'danger')
        return redirect(url_for('transactions.client_transactions', client_id=client_id))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('transactions.client_transactions', client_id=client_id)) 