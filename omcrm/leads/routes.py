from datetime import datetime
import io
import csv

import pandas as pd
from sqlalchemy import or_
from wtforms import Label

from flask import Blueprint, session, Response, jsonify
from flask_login import current_user, login_required, logout_user
from flask import render_template, flash, url_for, redirect, request

from omcrm import db
from .models import Lead, Comment, Trade, LeadSource
from omcrm.common.paginate import Paginate
from omcrm.common.filters import CommonFilters
from .filters import set_date_filters, set_source, set_status
from .forms import NewLead, ImportLeads, ConvertLead, \
    FilterLeads, BulkOwnerAssign, BulkLeadSourceAssign, BulkLeadStatusAssign, BulkDelete, CommentForm, \
    ConvertLeadToClient, ChangePasswordForm, UpdateBalanceForm, ApplyBonusForm, LeadSourceForm, CreditBalanceForm, LeadTeamShuffle

from omcrm.rbac import check_access, is_admin, get_visible_leads_query, get_visible_clients_query
from ..webtrader.forms import TradeForm, EditTradeForm
from omcrm.leads.models import Comment, LeadStatus
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
        Lead
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

    # Prepare bulk action forms
    bulk_form = {
        'owner': BulkOwnerAssign(),
        'lead_source': BulkLeadSourceAssign(),
        'lead_status': BulkLeadStatusAssign(),
        'delete': BulkDelete()
    }
    
    # Add shuffle form for team redistribution
    shuffle_form = LeadTeamShuffle()
    
    page = request.args.get('page', 1, type=int)
    
    paginator = Paginate(query, page=page, per_page=10)
    leads_to_template = paginator.items()
    total_leads = paginator.total_records
    
    # Get all statuses for the dropdown
    statuses = LeadStatus.query.all()
    
    # Get unique countries from the database
    countries_query = db.session.query(Lead.country).filter(Lead.country != None, Lead.country != '').distinct()
    countries = [country[0] for country in countries_query]

    return render_template("leads/leads_list.html",
                           title="Leads",
                           leads=leads_to_template,
                           total_leads=total_leads,
                           paginator=paginator,
                           bulk_form=bulk_form,
                           shuffle_form=shuffle_form,
                           statuses=statuses,
                           countries=countries,
                           form=FilterLeads())

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
                country=form.country.data,
                # 🔧 NEW: Lead attribution fields
                funnel_name=form.funnel_name.data,
                affiliate_id=form.affiliate_id.data
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
            
            # 🔧 NEW: Update attribution fields
            lead.funnel_name = form.funnel_name.data
            lead.affiliate_id = form.affiliate_id.data
            
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
        
        # 🔧 NEW: Populate attribution fields
        form.funnel_name.data = lead.funnel_name
        form.affiliate_id.data = lead.affiliate_id
        
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
        
        # Check if lead has a status, if not, try to assign a default one
        if not lead.lead_status_id:
            # Try to get the first available status
            # No default status - leads should start with no status
            lead.lead_status_id = None
            db.session.commit()
            flash('Lead/client updated successfully.', 'info')
        
        # Prepare comment form
        form = CommentForm()
        form.lead_id.data = lead_id
        
        # Handle form submission for comment
        if form.validate_on_submit():
            comment = Comment(
                content=form.content.data,
                lead_id=lead_id,
                user_id=current_user.id,
                date_posted=datetime.utcnow()
            )
            db.session.add(comment)
            db.session.commit()
            flash('Comment added successfully!', 'success')
            return redirect(url_for('leads.get_lead_view', lead_id=lead_id))
        
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
        lead.conversion_date = datetime.utcnow()  # Always use current date
        lead.owner = form.assignee.data
        lead.set_password(form.password.data)
        db.session.commit()
        flash('Lead has been successfully converted to a client!', 'success')
        return redirect(url_for('leads.get_lead_view', lead_id=lead.id))
    return render_template("leads/lead_convert_new.html", title="Convert Lead to Client", lead=lead, form=form)

@leads.route("/leads/import", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'create')
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
@check_access('leads', 'edit')
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
@check_access('leads', 'edit')
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
@check_access('leads', 'edit')
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
@login_required
@check_access('leads', 'delete')
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

    # Debug information
    print(f"Status filter: {status_filter}")
    print(f"Request method: {request.method}")
    print(f"Form data: {request.form}")
    
    # Get selected status from form directly if it's a direct POST
    direct_status_id = request.form.get('status')
    if direct_status_id and direct_status_id.strip():
        try:
            direct_status_id = int(direct_status_id)
            status_filter = (Lead.lead_status_id == direct_status_id)
            print(f"Direct status filter applied: {direct_status_id}")
        except (ValueError, TypeError):
            print(f"Invalid status ID: {direct_status_id}")

    # Get selected source from form directly if it's a direct POST
    direct_source_id = request.form.get('source')
    if direct_source_id and direct_source_id.strip():
        try:
            direct_source_id = int(direct_source_id)
            source_filter = (Lead.lead_source_id == direct_source_id)
            print(f"Direct source filter applied: {direct_source_id}")
        except (ValueError, TypeError):
            print(f"Invalid source ID: {direct_source_id}")
            
    # Get selected owner from form directly if it's a direct POST
    direct_owner_id = request.form.get('owner')
    if direct_owner_id and direct_owner_id.strip():
        try:
            direct_owner_id = int(direct_owner_id)
            owner = (Lead.owner_id == direct_owner_id)
            print(f"Direct owner filter applied: {direct_owner_id}")
        except (ValueError, TypeError):
            print(f"Invalid owner ID: {direct_owner_id}")
            
    # Get search query directly
    direct_search = request.form.get('name')
    if direct_search and direct_search.strip():
        search = direct_search
        print(f"Direct search applied: {direct_search}")

    # Get country filter directly
    direct_country = request.form.get('country')
    country_filter = True
    if direct_country and direct_country.strip():
        country_filter = (Lead.country == direct_country)
        print(f"Direct country filter applied: {direct_country}")
    
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
        country_filter
    ).filter(
        advanced_filters
    ).order_by(Lead.date_created.desc())
    
    # Apply team-based permissions to the query
    query = get_visible_clients_query(query)

    # Prepare bulk action forms for clients view
    bulk_form = {
        'owner': BulkOwnerAssign(),
        'lead_source': BulkLeadSourceAssign(),
        'lead_status': BulkLeadStatusAssign(),
        'delete': BulkDelete()
    }
    
    # Add shuffle form for team redistribution
    shuffle_form = LeadTeamShuffle()
    
    page = request.args.get('page', 1, type=int)
    
    paginator = Paginate(query, page=page, per_page=10)
    leads_to_template = paginator.items()
    total_leads = paginator.total_records
    
    # Get all sources and users for dropdown filters
    sources = LeadSource.query.all()
    users = User.query.filter_by(is_user_active=True).all()
    
    # Get all statuses for the dropdown
    statuses = LeadStatus.query.all()
    
    # Get unique countries from the database
    countries_query = db.session.query(Lead.country).filter(Lead.country != None, Lead.country != '').distinct()
    countries = [country[0] for country in countries_query]

    return render_template("leads/clients_list.html",
                          title="Clients",
                          leads=leads_to_template,
                          total_leads=total_leads,
                          paginator=paginator,
                          bulk_form=bulk_form,
                          shuffle_form=shuffle_form,
                          statuses=statuses,
                          users=users,
                          sources=sources)

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
    new_password = 'Welcome123!'  # Default password
    lead.set_password(new_password)
    db.session.commit()
    flash(f'✅ Client password reset successfully! New password: {new_password}', 'success')
    return redirect(url_for('leads.get_lead_view', lead_id=lead.id))

@leads.route("/client/get_password/<int:lead_id>")
@login_required
@check_access('leads', 'view')
def get_client_password(lead_id):
    """API endpoint to retrieve client password from obscure 'juhu' column"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Additional security check - only allow viewing password if user has edit access
    if not current_user.is_admin and (not current_user.role or not any(
        res.name == 'leads' and res.can_edit for res in current_user.role.resources
    )):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get password from obscure "juhu" column
    if lead.juhu:
        return jsonify({
            'success': True,
            'password': lead.juhu,
            'note': 'Client password retrieved successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No password available. Please reset the password first.',
            'note': 'Password will be available after reset.'
        })

@leads.route("/client/reset_password_form/<int:lead_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'update')
def reset_client_password_form(lead_id):
    """Form-based password reset with custom password input"""
    lead = Lead.query.get_or_404(lead_id)
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        
        # Validate password
        if not new_password:
            flash('Password cannot be empty', 'error')
            return redirect(url_for('leads.reset_client_password_form', lead_id=lead_id))
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect(url_for('leads.reset_client_password_form', lead_id=lead_id))
        
        # Set new password
        lead.set_password(new_password)
        db.session.commit()
        
        # 🔧 SHOW: Display the plain text password for business purposes
        flash(f'✅ Client password reset successfully! New password: {new_password}', 'success')
        return redirect(url_for('leads.get_lead_view', lead_id=lead.id))
    
    # GET request - show the form
    return render_template('leads/reset_password_form.html', lead=lead, title='Reset Client Password')

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
@check_access('leads', 'view')
def lead_sources():
    """View and manage lead sources"""
    sources = LeadSource.query.all()
    
    # Form for adding a new lead source
    if request.method == 'POST':
        name = request.form.get('source_name')
        affiliate_id = request.form.get('affiliate_id')
        
        if name and affiliate_id:
            # Check for existing source name
            existing_name = LeadSource.query.filter_by(source_name=name).first()
            if existing_name:
                flash(f"Lead source with name '{name}' already exists", "warning")
                return render_template("leads/lead_sources.html", title="Lead Sources", sources=LeadSource.query.all())
            
            # Check for existing affiliate ID
            existing_affiliate = LeadSource.query.filter_by(affiliate_id=affiliate_id).first()
            if existing_affiliate:
                flash(f"Lead source with affiliate ID '{affiliate_id}' already exists", "warning")
                return render_template("leads/lead_sources.html", title="Lead Sources", sources=LeadSource.query.all())
                
            new_source = LeadSource(source_name=name, affiliate_id=affiliate_id)
            db.session.add(new_source)
            db.session.commit()
            flash(f"Lead source '{name}' with affiliate ID '{affiliate_id}' created successfully", "success")
            return redirect(url_for('leads.lead_sources'))
        else:
            if not name:
                flash("Source name is required", "danger")
            if not affiliate_id:
                flash("Affiliate ID is required", "danger")
                
    return render_template("leads/lead_sources.html", 
                          title="Lead Sources", 
                          sources=sources)

@leads.route("/leads/source/<int:source_id>/toggle_api", methods=['POST'])
@login_required
@check_access('leads', 'edit')
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
@check_access('leads', 'edit')
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
    """Login as client for support purposes"""
    from flask import session
    from flask_login import login_user, current_user
    
    # Get the client
    client = Lead.query.get_or_404(client_id)
    
    # Basic validation
    if not client.is_client:
        flash('This lead has not been converted to a client yet.', 'warning')
        return redirect(url_for('leads.get_lead_view', lead_id=client_id))
    
    # Debug output
    print(f"[DEBUG] Admin {current_user.id} impersonating client {client.id}")
    print(f"[DEBUG] Client details: is_client={client.is_client}, is_active={client.is_active}")
    
    # Store admin ID in session and set login type to client
    session['admin_user_id'] = current_user.id
    session['login_type'] = 'client'
    
    # Log in as the client
    login_user(client)
    
    # Debug output after login
    print(f"[DEBUG] Current user after impersonation: {current_user.id}, {current_user.__class__.__name__}")
    print(f"[DEBUG] Current session: {session}")
    
    # Notify and redirect to webtrader
    flash(f'You are now logged in as {client.first_name} {client.last_name}.', 'success')
    
    # Return directly to webtrader dashboard
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
    """Return from client impersonation back to admin account"""
    from flask import session
    from flask_login import login_user, logout_user
    from omcrm.users.models import User
    
    try:
        # Check for admin session
        if 'admin_user_id' not in session:
            print("[DEBUG] No admin_user_id in session")
            flash('No admin session found.', 'warning')
            return redirect(url_for('main.home'))
        
        # Get the admin ID
        admin_id = session.pop('admin_user_id')
        print(f"[DEBUG] Found admin_user_id: {admin_id}")
        
        # Clear login_type - will be set again when logging back in
        session.pop('login_type', None)
        
        # Log out current client user first
        logout_user()
        
        # Get admin user
        admin_user = User.query.get(admin_id)
        if not admin_user:
            print(f"[DEBUG] Admin user not found: {admin_id}")
            flash('Admin user not found.', 'danger')
            session.clear()
            return redirect(url_for('users.login'))
        
        # Log back in as admin and set login_type
        login_user(admin_user)
        session['login_type'] = 'admin'
        
        print(f"[DEBUG] Logged back in as admin: {admin_user.id}, login_type: {session.get('login_type')}")
        
        # Success
        flash('Successfully returned to admin account.', 'success')
        return redirect(url_for('leads.get_clients_view'))
    except Exception as e:
        print(f"[ERROR] Exception in return_to_admin: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Clear session and go to login on any error
        session.clear()
        flash('Error returning to admin account.', 'danger')
        return redirect(url_for('users.login'))

@leads.route("/lead_statuses", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'view')
def manage_lead_statuses():
    """Manage lead/client statuses"""
    from flask_wtf import FlaskForm
    
    form = FlaskForm()
    if request.method == 'POST' and form.validate_on_submit():
        status_name = request.form.get('status_name')
        description = request.form.get('description')
        color = request.form.get('color', '#4361ee')  # Default blue color if not specified
        
        if status_name:
            new_status = LeadStatus(
                status_name=status_name,
                description=description,
                color=color
            )
            db.session.add(new_status)
            db.session.commit()
            flash('Client/Lead status added successfully!', 'success')
        else:
            flash('Status name cannot be empty.', 'danger')
    
    statuses = LeadStatus.query.all()
    return render_template("leads/manage_lead_statuses.html", 
                           title="Manage Client/Lead Statuses", 
                           statuses=statuses, 
                           form=form)

@leads.route("/lead_statuses/edit/<int:status_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'edit')
def edit_lead_status(status_id):
    """Edit an existing lead/client status"""
    status = LeadStatus.query.get_or_404(status_id)
    
    # If it's a POST request, process the form data
    if request.method == 'POST':
        status_name = request.form.get('status_name')
        description = request.form.get('description')
        color = request.form.get('color', status.color)  # Keep existing color if none provided
        
        if status_name:
            status.status_name = status_name
            status.description = description
            status.color = color
            db.session.commit()
            flash('Status updated successfully!', 'success')
        else:
            flash('Status name cannot be empty.', 'danger')
        return redirect(url_for('leads.manage_lead_statuses'))
    
    # If it's a GET request, render a form
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, SubmitField, HiddenField
    from wtforms.validators import DataRequired
    
    class EditStatusForm(FlaskForm):
        status_name = StringField('Status Name', validators=[DataRequired()])
        description = TextAreaField('Description')
        color = StringField('Color', default='#4361ee')
        submit = SubmitField('Update Status')
    
    form = EditStatusForm()
    
    # Pre-fill the form with existing data
    form.status_name.data = status.status_name
    form.description.data = status.description
    form.color.data = status.color or '#4361ee'
    
    return render_template("leads/edit_status.html", 
                           form=form, 
                           status=status, 
                           title="Edit Status")

@leads.route("/lead_statuses/delete/<int:status_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'delete')
def delete_lead_status(status_id):
    """Delete a lead/client status"""
    status = LeadStatus.query.get_or_404(status_id)
    
    # For GET requests, show a confirmation page
    if request.method == 'GET':
        # Check if any leads are using this status
        has_leads = status.leads and len(status.leads) > 0
        return render_template("leads/delete_status.html", 
                              status=status, 
                              has_leads=has_leads,
                              lead_count=len(status.leads) if status.leads else 0,
                              title="Confirm Delete Status")
    
    # For POST requests, process the deletion
    # Check if any leads are using this status
    if status.leads and len(status.leads) > 0:
        flash(f'Cannot delete status - it is currently used by {len(status.leads)} leads/clients.', 'danger')
    else:
        db.session.delete(status)
        db.session.commit()
        flash('Status deleted successfully!', 'success')
    
    return redirect(url_for('leads.manage_lead_statuses'))

@leads.route("/update_client_status", methods=['POST'])
@login_required
@check_access('leads', 'update')
def update_client_status():
    """AJAX endpoint to update a client's status"""
    client_id = request.form.get('client_id')
    status_id = request.form.get('status_id')
    
    if not client_id or not status_id:
        return jsonify({'success': False, 'message': 'Missing required parameters'})
    
    try:
        client = Lead.query.get_or_404(client_id)
        status = LeadStatus.query.get_or_404(status_id)
        
        client.lead_status_id = status.id
        db.session.commit()
        
        # Log the activity
        Activity.log(
            action_type='status_updated',
            description=f'Client status updated to "{status.status_name}"',
            user=current_user,
            lead=client,
            target_type='lead',
            target_id=client.id
        )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@leads.route("/leads/shuffle", methods=['POST'])
@login_required
@check_access('leads', 'edit')
def shuffle_leads():
    """Shuffle selected leads among team members"""
    if 'leads_to_shuffle' not in request.form or not request.form['leads_to_shuffle']:
        flash('No leads selected for shuffling', 'warning')
        return redirect(url_for('leads.get_leads_view'))
        
    team_members = request.form.getlist('team_members')
    if not team_members:
        flash('No team members selected for assigning leads', 'warning')
        return redirect(url_for('leads.get_leads_view'))
        
    distribution_method = request.form.get('distribution_method', 'random')
    
    # Parse lead IDs
    try:
        ids = [int(x) for x in request.form['leads_to_shuffle'].split(',')]
    except (ValueError, TypeError):
        flash('Invalid lead selection', 'danger')
        return redirect(url_for('leads.get_leads_view'))
    
    if not ids:
        flash('No leads selected for shuffling', 'warning')
        return redirect(url_for('leads.get_leads_view'))
    
    # Fetch the selected users
    selected_team_members = User.query.filter(User.id.in_(team_members)).all()
    if not selected_team_members:
        flash('Selected team members not found', 'danger')
        return redirect(url_for('leads.get_leads_view'))
    
    # Get the leads to shuffle
    leads_to_shuffle = Lead.query.filter(Lead.id.in_(ids)).all()
    if not leads_to_shuffle:
        flash('No leads found with the selected IDs', 'warning')
        return redirect(url_for('leads.get_leads_view'))
    
    try:
        # Track assignments for reporting
        teams = {member.id: [] for member in selected_team_members}
        
        if distribution_method == 'random':
            # Random distribution (equal distribution)
            import random
            random.shuffle(leads_to_shuffle)
            
            # Distribute leads equally among team members
            for i, lead in enumerate(leads_to_shuffle):
                member_index = i % len(selected_team_members)
                member = selected_team_members[member_index]
                lead.owner_id = member.id
                teams[member.id].append(lead.id)
                
        elif distribution_method == 'sequential':
            # Sequential distribution (round robin)
            for i, lead in enumerate(leads_to_shuffle):
                member_index = i % len(selected_team_members)
                member = selected_team_members[member_index]
                lead.owner_id = member.id
                teams[member.id].append(lead.id)
                
        elif distribution_method == 'percentage':
            # Percentage distribution
            percentages = request.form.get('percentages')
            if not percentages:
                flash('Percentages are required for percentage distribution', 'warning')
                return redirect(url_for('leads.get_leads_view'))
                
            try:
                # Parse percentages
                percentages = [float(p.strip()) for p in percentages.split(',')]
                
                # Validate that percentages sum to 100 and match team members count
                if len(percentages) != len(selected_team_members):
                    flash(f'Number of percentages ({len(percentages)}) must match number of team members ({len(selected_team_members)})', 'warning')
                    return redirect(url_for('leads.get_leads_view'))
                    
                if abs(sum(percentages) - 100) > 0.01:  # Allow for minor floating-point errors
                    flash('Percentages must sum to 100', 'warning')
                    return redirect(url_for('leads.get_leads_view'))
                
                # Calculate how many leads each team member gets
                total_leads = len(leads_to_shuffle)
                
                lead_counts = []
                for percentage in percentages:
                    # Calculate number of leads based on percentage
                    count = int(round(percentage * total_leads / 100))
                    lead_counts.append(count)
                
                # Adjust for rounding errors
                total_assigned = sum(lead_counts)
                if total_assigned != total_leads:
                    # Add or subtract the difference from the team with the most leads
                    diff = total_leads - total_assigned
                    if diff > 0:
                        max_index = lead_counts.index(max(lead_counts))
                        lead_counts[max_index] += diff
                    else:
                        max_index = lead_counts.index(max(lead_counts))
                        lead_counts[max_index] += diff  # diff is negative
                
                # Assign leads based on calculated counts
                lead_index = 0
                for i, member in enumerate(selected_team_members):
                    count = lead_counts[i]
                    for j in range(count):
                        if lead_index < len(leads_to_shuffle):
                            lead = leads_to_shuffle[lead_index]
                            lead.owner_id = member.id
                            teams[member.id].append(lead.id)
                            lead_index += 1
                
            except ValueError:
                flash('Invalid percentages. Please enter comma-separated numbers that sum to 100.', 'danger')
                return redirect(url_for('leads.get_leads_view'))
        
        # Save changes to database
        db.session.commit()
        
        # Generate assignment report
        assignment_report = []
        for member in selected_team_members:
            member_name = f"{member.first_name} {member.last_name}"
            assigned_count = len(teams[member.id])
            assignment_report.append(f"{member_name}: {assigned_count} leads")
        
        assignment_report_str = ", ".join(assignment_report)
        flash(f'Successfully shuffled {len(leads_to_shuffle)} leads! {assignment_report_str}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error shuffling leads: {str(e)}', 'danger')
        
    # Redirect to appropriate view based on whether we're working with leads or clients
    referrer = request.referrer or url_for('leads.get_leads_view')
    if 'clients' in referrer:
        return redirect(url_for('leads.get_clients_view'))
    else:
        return redirect(url_for('leads.get_leads_view'))

@leads.route("/leads/update_status", methods=['POST'])
@login_required
@check_access('leads', 'update')
def update_status():
    """Update the status of a lead or client via AJAX"""
    if not request.is_json and not request.form:
        return jsonify({"success": False, "message": "Invalid request format"}), 400
    
    # Get data from either JSON or form data
    data = request.get_json() if request.is_json else request.form
    
    if 'lead_id' not in data or 'status_id' not in data:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
    
    try:
        lead_id = int(data['lead_id'])
        status_id = int(data['status_id']) if data['status_id'] else None  # Allow null status
    except ValueError:
        return jsonify({"success": False, "message": "Invalid ID format"}), 400
    
    # Find the lead
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({"success": False, "message": "Lead not found"}), 404
    
    # Check permissions - allow if user is admin, owner, or has leads update permission
    if not current_user.is_admin and lead.owner_id != current_user.id:
        # Check if user has general leads update permission
        try:
            from omcrm.rbac import is_allowed
            if not is_allowed(current_user, 'leads', 'update'):
                return jsonify({"success": False, "message": "You don't have permission to update this lead's status"}), 403
        except:
            # Fallback - if RBAC check fails, deny access for non-admin non-owners
            return jsonify({"success": False, "message": "You don't have permission to update this lead's status"}), 403
    
    # If status_id is None, set lead_status_id to None
    if status_id is None:
        lead.lead_status_id = None
        db.session.commit()
        return jsonify({"success": True})
    
    # Otherwise, verify status exists
    status = LeadStatus.query.get(status_id)
    if not status:
        return jsonify({"success": False, "message": "Status not found"}), 404
    
    # Update the lead status
    lead.lead_status_id = status_id
    db.session.commit()
    
    return jsonify({"success": True})

@leads.route("/leads/export_csv", methods=['GET'])
@login_required
def export_leads_csv():
    """Export leads to CSV"""
    # Get IDs from query parameters if provided
    ids_param = request.args.get('ids')
    
    # Base query for non-client leads
    query = Lead.query.filter_by(is_client=False)
    
    # If specific IDs were provided, filter by those
    if ids_param:
        try:
            ids = [int(x) for x in ids_param.split(',')]
            query = query.filter(Lead.id.in_(ids))
        except ValueError:
            flash('Invalid ID format in export request', 'danger')
            return redirect(url_for('leads.get_leads_view'))
    
    # Get all leads based on query
    leads = query.all()
    
    if not leads:
        flash('No leads found to export', 'warning')
        return redirect(url_for('leads.get_leads_view'))
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow([
        'ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Mobile',
        'Company', 'Status', 'Source', 'Owner', 'Country', 'State',
        'City', 'Address', 'Postal Code', 'Date Created', 'Notes'
    ])
    
    # Write data rows
    for lead in leads:
        writer.writerow([
            lead.id,
            lead.first_name,
            lead.last_name,
            lead.email,
            lead.phone,
            lead.mobile,
            lead.company_name,
            lead.status.status_name if lead.status else '',
            lead.source.source_name if lead.source else '',
            f"{lead.owner.first_name} {lead.owner.last_name}" if lead.owner else '',
            lead.country,
            lead.addr_state,
            lead.addr_city,
            lead.address_line,
            lead.post_code,
            lead.date_created.strftime('%Y-%m-%d %H:%M:%S') if lead.date_created else '',
            lead.notes
        ])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=leads_export_{timestamp}.csv"}
    )

@leads.route("/clients/export_csv", methods=['GET'])
@login_required
def export_clients_csv():
    """Export clients to CSV"""
    # Get IDs from query parameters if provided
    ids_param = request.args.get('ids')
    
    # Base query for client leads
    query = Lead.query.filter_by(is_client=True)
    
    # If specific IDs were provided, filter by those
    if ids_param:
        try:
            ids = [int(x) for x in ids_param.split(',')]
            query = query.filter(Lead.id.in_(ids))
        except ValueError:
            flash('Invalid ID format in export request', 'danger')
            return redirect(url_for('leads.get_clients_view'))
    
    # Get all clients based on query
    clients = query.all()
    
    if not clients:
        flash('No clients found to export', 'warning')
        return redirect(url_for('leads.get_clients_view'))
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow([
        'ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Mobile',
        'Company', 'Status', 'Source', 'Owner', 'Country', 'State',
        'City', 'Address', 'Postal Code', 'Conversion Date', 
        'Current Balance', 'Bonus Balance', 'Credit Balance', 'Available to Trade'
    ])
    
    # Write data rows
    for client in clients:
        writer.writerow([
            client.id,
            client.first_name,
            client.last_name,
            client.email,
            client.phone,
            client.mobile,
            client.company_name,
            client.status.status_name if client.status else '',
            client.source.source_name if client.source else '',
            f"{client.owner.first_name} {client.owner.last_name}" if client.owner else '',
            client.country,
            client.addr_state,
            client.addr_city,
            client.address_line,
            client.post_code,
            client.conversion_date.strftime('%Y-%m-%d %H:%M:%S') if client.conversion_date else '',
            f"{client.current_balance:.2f}" if client.current_balance is not None else '0.00',
            f"{client.bonus_balance:.2f}" if client.bonus_balance is not None else '0.00',
            f"{client.credit_balance:.2f}" if client.credit_balance is not None else '0.00',
            'Yes' if client.available_to_trade else 'No'
        ])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=clients_export_{timestamp}.csv"}
    )
