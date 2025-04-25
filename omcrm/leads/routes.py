from datetime import datetime

import pandas as pd
from sqlalchemy import or_
from wtforms import Label

from flask import Blueprint, session, Response, jsonify
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, redirect, request

from omcrm import db
from .models import Lead, Comment, Trade, LeadSource
from omcrm.common.paginate import Paginate
from omcrm.common.filters import CommonFilters
from .filters import set_date_filters, set_source, set_status
from .forms import NewLead, ImportLeads, ConvertLead, \
    FilterLeads, BulkOwnerAssign, BulkLeadSourceAssign, BulkLeadStatusAssign, BulkDelete, CommentForm, \
    ConvertLeadToClient, ChangePasswordForm, UpdateBalanceForm, ApplyBonusForm, LeadSourceForm, CreditBalanceForm

from omcrm.rbac import check_access, is_admin, get_visible_leads_query, get_visible_clients_query
from ..webtrader.forms import TradeForm, EditTradeForm
from omcrm.leads.models import Comment
from omcrm.users.models import User
from omcrm.webtrader.models import TradingInstrument, Trade
from omcrm.activities.models import Activity

leads = Blueprint('leads', __name__)


def reset_lead_filters():
    if 'lead_owner' in session:
        session.pop('lead_owner', None)
    if 'lead_search' in session:
        session.pop('lead_search', None)
    if 'lead_source' in session:
        session.pop('lead_source', None)
    if 'lead_status' in session:
        session.pop('lead_status', None)
    if 'lead_date_from' in session:
        session.pop('lead_date_from', None)
    if 'lead_date_to' in session:
        session.pop('lead_date_to', None)


@leads.route("/leads", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'view')
def get_leads_view():
    form = FilterLeads()
    search = None
    source_filter = None
    status_filter = None
    owner_filter = None
    date_from_filter = None
    date_to_filter = None
    
    if request.method == 'POST' and form.validate():
        search = form.name.data
        source = form.source.data
        status = form.status.data
        owner = form.owner.data
        date_from = form.created_date_from.data
        date_to = form.created_date_to.data
        
        # Store in session for persistence
        session['lead_search'] = search
        if source:
            session['lead_source'] = source.id
        if status:
            session['lead_status'] = status.id
        if owner:
            session['lead_owner'] = owner.id
        if date_from:
            session['lead_date_from'] = date_from.strftime('%Y-%m-%d')
        if date_to:
            session['lead_date_to'] = date_to.strftime('%Y-%m-%d')
    else:
        # Retrieve from session if available
        if 'lead_search' in session:
            search = session['lead_search']
            form.name.data = search
        if 'lead_source' in session:
            source = LeadSource.query.get(session['lead_source'])
            form.source.data = source
        if 'lead_status' in session:
            status = LeadStatus.query.get(session['lead_status'])
            form.status.data = status
        if 'lead_owner' in session:
            owner = User.query.get(session['lead_owner'])
            form.owner.data = owner
        if 'lead_date_from' in session:
            date_from = datetime.strptime(session['lead_date_from'], '%Y-%m-%d').date()
            form.created_date_from.data = date_from
        if 'lead_date_to' in session:
            date_to = datetime.strptime(session['lead_date_to'], '%Y-%m-%d').date()
            form.created_date_to.data = date_to

    # Subquery to get the last comment for each lead
    last_comment_subquery = db.session.query(
        Comment.lead_id,
        Comment.content.label('last_comment')
    ).filter(
        Comment.lead_id == Lead.id
    ).order_by(
        Comment.date_posted.desc()
    ).limit(1).subquery()

    query = db.session.query(
        Lead,
        last_comment_subquery.c.last_comment
    ).outerjoin(
        last_comment_subquery, Lead.id == last_comment_subquery.c.lead_id
    ).filter(
        Lead.is_client == False  # Only show non-converted leads
    )
    
    # Apply filters
    if search:
        query = query.filter(or_(
            Lead.first_name.ilike(f'%{search}%'),
            Lead.last_name.ilike(f'%{search}%'),
            Lead.email.ilike(f'%{search}%'),
            Lead.company_name.ilike(f'%{search}%'),
            Lead.phone.ilike(f'%{search}%')
        ))
    
    if 'lead_source' in session:
        query = query.filter(Lead.lead_source_id == session['lead_source'])
    
    if 'lead_status' in session:
        query = query.filter(Lead.lead_status_id == session['lead_status'])
    
    if 'lead_owner' in session:
        query = query.filter(Lead.owner_id == session['lead_owner'])
    
    if 'lead_date_from' in session:
        date_from = datetime.strptime(session['lead_date_from'], '%Y-%m-%d').date()
        query = query.filter(Lead.date_created >= date_from)
    
    if 'lead_date_to' in session:
        date_to = datetime.strptime(session['lead_date_to'], '%Y-%m-%d').date()
        query = query.filter(Lead.date_created <= date_to)
    
    # Apply team-based permissions to the query
    query = get_visible_leads_query(query)
    
    # Order by newest first
    query = query.order_by(Lead.date_created.desc())

    bulk_form = {
        'owner': BulkOwnerAssign(),
        'lead_source': BulkLeadSourceAssign(),
        'lead_status': BulkLeadStatusAssign(),
        'delete': BulkDelete()
    }
    return render_template("leads/leads_list.html", title="Leads View", leads=Paginate(query), form=form,
                           bulk_form=bulk_form)

@leads.route("/leads/new", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'create')
def new_lead():
    form = NewLead()
    if request.method == 'POST':
        if form.validate_on_submit():
            lead = Lead(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                company_name=form.company_name.data,
                email=form.email.data,
                phone=form.phone.data,
                country=form.country.data
            )

            if current_user.is_admin:
                lead.owner = form.assignees.data
            else:
                lead.owner = current_user

            db.session.add(lead)
            db.session.commit()
            
            # Log activity for lead creation
            Activity.log(
                action_type='lead_created',
                description=f'New lead created: {lead.first_name} {lead.last_name}',
                user=current_user,
                lead=lead,
                target_type='lead',
                target_id=lead.id
            )
            
            flash('New lead has been successfully created!', 'success')
            return redirect(url_for('leads.get_leads_view'))
        else:
            for error in form.errors:
                print(error)
            flash('Your form has errors! Please check the fields', 'danger')
    return render_template("leads/new_lead.html", title="New Lead", form=form)


@leads.route("/leads/edit/<int:lead_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'update')
def update_lead(lead_id):
    lead = Lead.get_by_id(lead_id)
    if not lead:
        return redirect(url_for('leads.get_leads_view'))

    form = NewLead()
    if request.method == 'POST':
        if form.validate_on_submit():
            lead.first_name = form.first_name.data
            lead.last_name = form.last_name.data
            lead.company_name = form.company_name.data
            lead.email = form.email.data
            lead.phone = form.phone.data
            lead.country = form.country.data
            lead.owner = form.assignees.data
            
            # Handle trading permission for clients
            if lead.is_client:
                lead.available_to_trade = form.available_to_trade.data
            
            db.session.commit()
            
            # Log activity for lead update
            Activity.log(
                action_type='lead_updated',
                description=f'Lead updated: {lead.first_name} {lead.last_name}',
                user=current_user,
                lead=lead,
                target_type='lead',
                target_id=lead.id
            )
            
            flash('The lead has been successfully updated', 'success')
            return redirect(url_for('leads.get_lead_view', lead_id=lead.id))
        else:
            print(form.errors)
            flash('Lead update failed! Form has errors', 'danger')
    elif request.method == 'GET':
        form.first_name.data = lead.first_name
        form.last_name.data = lead.last_name
        form.company_name.data = lead.company_name
        form.email.data = lead.email
        form.phone.data = lead.phone
        form.country.data = lead.country
        form.assignees.data = lead.owner
        
        # Set trading permission for clients
        if lead.is_client and hasattr(lead, 'available_to_trade'):
            form.available_to_trade.data = lead.available_to_trade
            
        form.submit.label = Label('update_lead', 'Update Lead')
    return render_template("leads/new_lead.html", title="Update Lead", form=form, lead=lead)


@leads.route("/leads/<int:lead_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'view')
def get_lead_view(lead_id):
    # Very simple implementation - just get the lead and render the template
    try:
        # Get the lead by ID
        lead = Lead.query.get_or_404(lead_id)
        
        # Prepare comment form
        form = CommentForm()
        form.lead_id.data = lead_id
        
        # Get comments - use date_posted, not date_created
        comments = Comment.query.filter_by(lead_id=lead_id).order_by(Comment.date_posted.desc()).all()
        
        # Always allow impersonation
        can_impersonate = True
        
        return render_template("leads/lead_view.html", 
                              title="View Lead", 
                              lead=lead, 
                              form=form, 
                              comments=comments, 
                              can_impersonate=can_impersonate)
    except Exception as e:
        # Log any exceptions
        print(f"Error in get_lead_view: {str(e)}")
        flash(f"Error viewing lead: {str(e)}", "danger")
        return redirect(url_for('leads.get_leads_view'))

@leads.route("/leads/del/<int:lead_id>")
@login_required
@check_access('leads', 'remove')
def delete_lead(lead_id):
    lead = Lead.query.filter_by(id=lead_id).first()
    if not lead:
        flash('The lead does not exist', 'danger')
    else:
        # Manually delete associated comments
        Comment.query.filter_by(lead_id=lead_id).delete()
        db.session.commit()

        # Delete the lead
        Lead.query.filter_by(id=lead_id).delete()
        db.session.commit()
        flash('The lead has been removed successfully', 'success')
    return redirect(url_for('leads.get_leads_view'))

@leads.route("/leads/convert/<int:lead_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'update')
def convert_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    form = ConvertLeadToClient()
    if form.validate_on_submit():
        lead.is_client = True
        lead.is_active = True  # Set the client as active
        lead.conversion_date = form.conversion_date.data or datetime.utcnow()
        lead.owner = form.assignee.data
        lead.set_password(form.password.data)
        db.session.commit()
        flash('Lead has been successfully converted to a client!', 'success')
        return redirect(url_for('leads.get_lead_view', lead_id=lead.id))
    return render_template("leads/lead_convert_new.html", title="Convert Lead to Client", lead=lead, form=form)

@leads.route("/leads/import", methods=['GET', 'POST'])
@login_required
@is_admin
def import_bulk_leads():
    form = ImportLeads()
    if request.method == 'POST':
        ind = 0
        if form.validate_on_submit():
            data = pd.read_csv(form.csv_file.data)

            for _, row in data.iterrows():
                lead = Lead(first_name=row['first_name'], last_name=row['last_name'],
                            email=row['email'], company_name=row['company_name'])
                lead.owner = current_user
                if form.lead_source.data:
                    lead.source = form.lead_source.data
                db.session.add(lead)
                ind = ind + 1

            db.session.commit()
            flash(f'{ind} new lead(s) has been successfully imported!', 'success')
        else:
            flash('Your form has errors! Please check the fields', 'danger')
    return render_template("leads/leads_import.html", title="Import Leads", form=form)


@leads.route("/leads/reset-filters")
@login_required
@check_access('leads', 'view')
def reset_filters():
    reset_lead_filters()
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_owner_assign", methods=['POST'])
@login_required
@is_admin
def bulk_owner_assign():
    form = BulkOwnerAssign()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.owners_list.data:
                ids = [int(x) for x in request.form['leads_owner'].split(',')]
                Lead.query\
                    .filter(Lead.id.in_(ids))\
                    .update({
                        Lead.owner_id: form.owners_list.data.id
                    }, synchronize_session=False)
                db.session.commit()
                flash(f'Owner has been assigned to {len(ids)} lead(s) successfully!', 'success')
        else:
            print(form.errors)

    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_lead_source_assign", methods=['POST'])
@login_required
@is_admin
def bulk_lead_source_assign():
    form = BulkLeadSourceAssign()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.lead_source_list.data:
                ids = [int(x) for x in request.form['leads_source'].split(',')]
                Lead.query \
                    .filter(Lead.id.in_(ids)) \
                    .update({
                        Lead.lead_source_id: form.lead_source_list.data.id
                    }, synchronize_session=False)
                db.session.commit()
                flash(f'Lead Source `{form.lead_source_list.data.source_name}` has been '
                      f'assigned to {len(ids)} lead(s) successfully!', 'success')
        else:
            print(form.errors)
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_lead_status_assign", methods=['POST'])
@login_required
@is_admin
def bulk_lead_status_assign():
    form = BulkLeadStatusAssign()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.lead_status_list.data:
                ids = [int(x) for x in request.form['leads_status'].split(',')]
                Lead.query \
                    .filter(Lead.id.in_(ids)) \
                    .update({
                        Lead.lead_status_id: form.lead_status_list.data.id
                    }, synchronize_session=False)
                db.session.commit()
                flash(f'Lead status `{form.lead_status_list.data.status_name}` has been '
                      f'assigned to {len(ids)} lead(s) successfully!', 'success')
        else:
            print(form.errors)
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_delete", methods=['POST'])
@is_admin
def bulk_delete():
    form = BulkDelete()
    if request.method == 'POST':
        if form.validate_on_submit():
            ids = [int(x) for x in request.form['leads_to_delete'].split(',')]
            Lead.query \
                .filter(Lead.id.in_(ids)) \
                .delete(synchronize_session=False)
            db.session.commit()
            flash(f'Successfully deleted {len(ids)} lead(s)!', 'success')
        else:
            print(form.errors)
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/write_csv")
@login_required
def write_to_csv():
    ids = [int(x) for x in request.args.get('lead_ids').split(',')]
    query = Lead.query \
        .filter(Lead.id.in_(ids))
    csv = 'Title,Last Name,Email,Company Name,Phone,' \
          'Mobile,Owner,Lead Source,Lead Status,Date Created\n'
    for lead in query.all():
        csv += f'{lead.title},{lead.first_name},' \
               f'{lead.last_name},{lead.email},' \
               f'{lead.company_name},{lead.phone},{lead.mobile},' \
               f'{lead.owner.first_name} {lead.owner.last_name},' \
               f'{lead.source.source_name},{lead.status.status_name},' \
               f'{lead.date_created}\n'
    return Response(csv,
                    mimetype='text/csv',
                    headers={"Content-disposition":
                             "attachment; filename=leads.csv"})

@leads.route("/clients", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'view')
def get_clients_view():
    filters = FilterLeads()
    search = CommonFilters.set_search(filters, 'lead_search')
    owner = CommonFilters.set_owner(filters, 'Lead', 'lead_owner')
    advanced_filters = set_date_filters(filters, 'lead_date_created')
    source_filter = set_source(filters, 'lead_source')
    status_filter = set_status(filters, 'lead_status')

    query = db.session.query(Lead).filter(
        Lead.is_client == True  # Only show converted leads (clients)
    ).filter(
        or_(
            Lead.title.ilike(f'%{search}%'),
            Lead.first_name.ilike(f'%{search}%'),
            Lead.last_name.ilike(f'%{search}%'),
            Lead.email.ilike(f'%{search}%'),
            Lead.company_name.ilike(f'%{search}%'),
            Lead.phone.ilike(f'%{search}%'),
            Lead.mobile.ilike(f'%{search}%'),
        ) if search else True
    ).filter(
        source_filter
    ).filter(
        status_filter
    ).filter(
        owner
    ).filter(
        advanced_filters
    ).order_by(Lead.date_created.desc())
    
    # Apply team-based permissions to the query
    query = get_visible_clients_query(query)

    bulk_form = {
        'owner': BulkOwnerAssign(),
        'lead_source': BulkLeadSourceAssign(),
        'lead_status': BulkLeadStatusAssign(),
        'delete': BulkDelete()
    }
    
    # Get all sources and users for dropdown filters
    sources = LeadSource.query.all()
    users = User.query.filter_by(is_user_active=True).all()

    return render_template("leads/clients_list.html", title="Clients View", leads=Paginate(query), filters=filters,
                           bulk_form=bulk_form, sources=sources, users=users)

@leads.route("/leads/edit_trade/<int:trade_id>", methods=['GET', 'POST'])
@login_required
def edit_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    form = EditTradeForm()
    if form.validate_on_submit():
        # Get the associated instrument to update the symbol
        instrument = TradingInstrument.query.filter_by(id=trade.instrument_id).first()
        if instrument:
            instrument.symbol = form.symbol.data
        trade.amount = form.amount.data
        trade.price = form.price.data
        trade.trade_type = form.trade_type.data
        
        # Update opening date
        trade.date = form.opening_date.data  # For backward compatibility
        trade.opening_date = form.opening_date.data
        
        # Handle status change
        previous_status = trade.status
        trade.status = form.status.data
        
        # If status changed to closed, handle closing price, closing date, and P/L
        if trade.status == 'closed':
            # Update closing date if provided or set to current time if missing
            if form.closing_date.data:
                trade.closing_date = form.closing_date.data
            elif not trade.closing_date or previous_status != 'closed':
                trade.closing_date = datetime.utcnow()
                
            # Update closing price if provided
            if form.closing_price.data is not None:
                trade.closing_price = form.closing_price.data
                
            # Always calculate profit/loss based on the current values
            if trade.closing_price:
                if trade.trade_type == 'buy':  # Long position
                    trade.profit_loss = (trade.closing_price - trade.price) * trade.amount
                else:  # Short position (sell)
                    trade.profit_loss = (trade.price - trade.closing_price) * trade.amount
        else:
            # If status is open, clear closing data
            trade.closing_date = None
            trade.closing_price = None
            trade.profit_loss = None
            
        db.session.commit()
        flash('Trade updated successfully', 'success')
        return redirect(url_for('leads.get_lead_view', lead_id=trade.lead_id))
    elif request.method == 'GET':
        # Get the symbol from the associated instrument
        instrument = TradingInstrument.query.filter_by(id=trade.instrument_id).first()
        form.symbol.data = instrument.symbol if instrument else ""
        form.amount.data = trade.amount
        form.price.data = trade.price
        form.trade_type.data = trade.trade_type
        
        # Set opening date from either opening_date or date field for backward compatibility
        form.opening_date.data = trade.opening_date if trade.opening_date else trade.date
        
        form.status.data = trade.status
        
        # Set closing date and price
        form.closing_date.data = trade.closing_date
        form.closing_price.data = trade.closing_price
        form.profit_loss.data = trade.profit_loss
        
    return render_template('leads/edit_trade.html', title='Edit Trade', form=form, trade=trade)

@leads.route("/add_trade/<int:lead_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'create')
def add_trade(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    form = TradeForm()
    instruments = TradingInstrument.query.all()
    
    if form.validate_on_submit():
        instrument = TradingInstrument.query.filter_by(id=form.instrument_id.data).first()
        if not instrument:
             flash('Invalid Instrument selected.', 'danger')
             return render_template('leads/add_trade.html', form=form, lead=lead, instruments=instruments)
        
        # Get current time for opening
        current_time = datetime.utcnow()
             
        trade = Trade(lead_id=lead.id, 
                      instrument_id=instrument.id,
                      amount=form.amount.data,
                      price=form.ask_price.data if form.trade_type.data == 'buy' else form.bid_price.data,
                      trade_type=form.trade_type.data,
                      date=current_time,
                      opening_date=current_time,
                      status='open'
                      )
        db.session.add(trade)
        db.session.commit()
        flash('Trade added successfully', 'success')
        return redirect(url_for('leads.get_lead_view', lead_id=lead.id))
    return render_template('leads/add_trade.html', form=form, lead=lead, instruments=instruments)

@leads.route("/client/change_password/<int:lead_id>", methods=['GET', 'POST'])
@login_required
def change_client_password(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if lead.check_password(form.current_password.data):
            lead.set_password(form.new_password.data)
            db.session.commit()
            flash('Password has been updated!', 'success')
            return redirect(url_for('leads.get_lead_view', lead_id=lead.id))
        else:
            flash('Invalid current password', 'danger')
    return render_template('leads/change_password.html', form=form, lead=lead)

@leads.route("/client/reset_password/<int:lead_id>")
@login_required
@check_access('leads', 'update')
def reset_client_password(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    new_password = 'Welcome123'  # You can generate a random password here
    lead.set_password(new_password)
    db.session.commit()
    flash(f'Client password has been reset. New password: {new_password}', 'success')
    return redirect(url_for('leads.get_lead_view', lead_id=lead.id))

@leads.route('/leads/manage_balance/<int:lead_id>', methods=['GET', 'POST'])
@login_required
def manage_balance(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    update_form = UpdateBalanceForm()
    bonus_form = ApplyBonusForm()
    credit_form = CreditBalanceForm()
    
    if 'update_balance' in request.form and update_form.validate_on_submit():
        lead.update_balance(update_form.amount.data)
        flash(f'Balance updated successfully! Added ${update_form.amount.data:.2f}', 'success')
        return redirect(url_for('leads.manage_balance', lead_id=lead_id))
    
    if 'apply_bonus' in request.form and bonus_form.validate_on_submit():
        lead.apply_bonus(bonus_form.bonus_amount.data)
        flash(f'Bonus of ${bonus_form.bonus_amount.data:.2f} applied successfully!', 'success')
        return redirect(url_for('leads.manage_balance', lead_id=lead_id))
        
    if 'add_credit' in request.form and credit_form.validate_on_submit():
        lead.add_credit(credit_form.credit_amount.data)
        flash(f'Credit of ${credit_form.credit_amount.data:.2f} added successfully!', 'success')
        return redirect(url_for('leads.manage_balance', lead_id=lead_id))
    
    return render_template('leads/manage_balance.html', 
                           title='Manage Balance', 
                           lead=lead, 
                           update_form=update_form, 
                           bonus_form=bonus_form,
                           credit_form=credit_form)

@leads.route("/leads/sources", methods=['GET', 'POST'])
@login_required
@is_admin
def lead_sources():
    """View and manage lead sources"""
    sources = LeadSource.query.all()
    
    # Form for adding a new lead source
    if request.method == 'POST':
        name = request.form.get('source_name')
        if name:
            existing = LeadSource.query.filter_by(source_name=name).first()
            if existing:
                flash(f"Lead source with name '{name}' already exists", "warning")
            else:
                new_source = LeadSource(source_name=name)
                db.session.add(new_source)
                db.session.commit()
                flash(f"Lead source '{name}' created successfully", "success")
                return redirect(url_for('leads.lead_sources'))
        else:
            flash("Source name is required", "danger")
    
    return render_template("leads/lead_sources.html", 
                          title="Lead Sources", 
                          sources=sources)

@leads.route("/leads/source/<int:source_id>/toggle_api", methods=['POST'])
@login_required
@is_admin
def toggle_api_access(source_id):
    """Enable or disable API access for a lead source"""
    source = LeadSource.query.get_or_404(source_id)
    
    # Toggle API access
    source.is_api_enabled = not source.is_api_enabled
    
    # If enabling and no API key exists, generate one
    if source.is_api_enabled and not source.api_key:
        import secrets
        source.api_key = secrets.token_hex(32)
        message = f"API access enabled and new API key generated for '{source.source_name}'"
    elif source.is_api_enabled:
        message = f"API access enabled for '{source.source_name}'"
    else:
        message = f"API access disabled for '{source.source_name}'"
    
    db.session.commit()
    flash(message, "success")
    
    return redirect(url_for('leads.lead_sources'))

@leads.route("/leads/source/<int:source_id>/regenerate_key", methods=['POST'])
@login_required
@is_admin
def regenerate_api_key(source_id):
    """Generate a new API key for a lead source"""
    source = LeadSource.query.get_or_404(source_id)
    
    # Generate new API key
    import secrets
    source.api_key = secrets.token_hex(32)
    
    # Ensure API access is enabled
    source.is_api_enabled = True
    
    db.session.commit()
    flash(f"New API key generated for '{source.source_name}'", "success")
    
    return redirect(url_for('leads.lead_sources'))

@leads.route("/login_as_client/<int:client_id>", methods=['POST'])
@login_required
def login_as_client(client_id):
    from flask import session, abort
    from flask_login import login_user, current_user
    
    # Get the client
    client = Lead.query.get_or_404(client_id)
    
    # Ensure the user is actually a client
    if not client.is_client:
        flash('This lead has not been converted to a client yet.', 'warning')
        return redirect(url_for('leads.get_lead_view', lead_id=client_id))
    
    # Store admin/agent user info for later return
    session['admin_user_id'] = current_user.id
    
    # Log in as the client
    login_user(client)
    
    # Redirect to WebTrader
    flash(f'You are now logged in as {client.first_name} {client.last_name}.', 'success')
    return redirect(url_for('webtrader.webtrader_dashboard'))

@leads.route("/toggle_trade_status", methods=['POST'])
@login_required
@check_access('leads', 'update')
def toggle_trade_status():
    """AJAX route to toggle a client's available_to_trade status"""
    # Check that the current user is an admin or has proper permissions
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'})
    
    # Get parameters from the request form
    client_id = request.form.get('client_id')
    status = request.form.get('status')
    
    # Validate parameters
    if not client_id:
        return jsonify({'success': False, 'message': 'Client ID is required.'})
    
    if status not in ['true', 'false']:
        return jsonify({'success': False, 'message': 'Status must be true or false.'})
    
    # Convert status string to boolean
    new_status = status == 'true'
    
    try:
        # Find the client
        client = Lead.query.get(client_id)
        
        # Validate client
        if not client or not client.is_client:
            return jsonify({'success': False, 'message': 'Invalid client selected.'})
        
        # Update the status
        client.available_to_trade = new_status
        db.session.commit()
        
        status_text = "enabled" if new_status else "disabled"
        return jsonify({
            'success': True, 
            'message': f'Trading has been {status_text} for {client.first_name} {client.last_name}.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating trade status: {str(e)}'})

@leads.route("/return_to_admin", methods=['GET', 'POST'])
@login_required
def return_to_admin():
    from flask import session
    from flask_login import login_user
    from omcrm.users.models import User
    
    # Only process if there's an admin_user_id in session
    if 'admin_user_id' not in session:
        flash('No admin session found.', 'warning')
        return redirect(url_for('main.home'))
    
    admin_id = session.pop('admin_user_id')
    admin_user = User.query.get(admin_id)
    
    if not admin_user:
        flash('Admin user not found.', 'danger')
        return redirect(url_for('main.home'))
    
    # Log back in as admin
    login_user(admin_user)
    flash('Returned to admin account.', 'success')
    
    return redirect(url_for('leads.get_clients_view'))
