from flask import Blueprint, session
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, redirect, request
from sqlalchemy import or_
import json
from wtforms import Label
from datetime import datetime

from omcrm import db
from omcrm.deals.models import Deal, DealStage
from omcrm.common.paginate import Paginate
from omcrm.common.filters import CommonFilters
from omcrm.leads.models import Lead
from omcrm.deals.forms import NewDeal, EditDeal, FilterDeals
from omcrm.deals.filters import set_date_filters, set_price_filters, set_deal_stage_filters

from omcrm.rbac import check_access, is_admin, get_visible_deals_query
from omcrm.activities.models import Activity

deals = Blueprint('deals', __name__)


def reset_deal_filters():
    if 'deals_owner' in session:
        session.pop('deals_owner', None)
    if 'deals_search' in session:
        session.pop('deals_search', None)
    if 'deals_client' in session:
        session.pop('deals_client', None)
    if 'deals_date_created' in session:
        session.pop('deals_date_created', None)
    if 'deal_price' in session:
        session.pop('deal_price', None)
    if 'deal_stage' in session:
        session.pop('deal_stage', None)


@deals.route("/deals", methods=['GET', 'POST'])
@login_required
@check_access('deals', 'view')
def get_deals_view():
    view_t = request.args.get('view_t', 'list', type=str)
    filters = FilterDeals()

    search = CommonFilters.set_search(filters, 'deals_search')
    owner = CommonFilters.set_owner(filters, 'Deal', 'deals_owner')
    client = CommonFilters.set_clients(filters, 'Deal', 'deals_client')
    advanced_filters = set_date_filters(filters, 'Deal', 'deals_date_created')
    price_filters = set_price_filters(filters, 'deal_price')
    deal_stage_filters = set_deal_stage_filters(filters, 'deal_stage')

    query = Deal.query.filter(or_(
        Deal.title.ilike(f'%{search}%')
    ) if search else True) \
        .filter(client) \
        .filter(price_filters) \
        .filter(deal_stage_filters) \
        .filter(owner) \
        .filter(advanced_filters) \
        .order_by(Deal.date_created.desc())
    
    # Apply team-based permissions to the query
    query = get_visible_deals_query(query)

    if view_t == 'kanban':
        all_deals = query.all()
        all_stages = DealStage.query.order_by(DealStage.display_order.asc()).all()
        
        print(f"Kanban view - Found {len(all_deals)} deals and {len(all_stages)} stages")
        for stage in all_stages:
            print(f"Stage ID: {stage.id}, Name: {stage.stage_name}, Order: {stage.display_order}")
        
        # Count deals per stage
        stage_counts = {}
        for deal in all_deals:
            stage_id = deal.deal_stage_id
            if stage_id in stage_counts:
                stage_counts[stage_id] += 1
            else:
                stage_counts[stage_id] = 1
                
        print("Deal counts per stage:", stage_counts)
        
        return render_template("deals/kanban_view.html", title="Deals View",
                               deals=all_deals,
                               deal_stages=all_stages,
                               filters=filters)
    else:
        return render_template("deals/deals_list.html", title="Deals View",
                               deals=Paginate(query), filters=filters)


@deals.route("/deals/<int:deal_id>")
@login_required
@check_access('deals', 'view')
def get_deal_view(deal_id):
    deal = Deal.query.filter_by(id=deal_id).first()
    return render_template("deals/deal_view.html", title="Deal View", deal=deal)


@deals.route("/deals/new", methods=['GET', 'POST'])
@login_required
@check_access('deals', 'create')
def new_deal():
    client_id = request.args.get('client', None, type=int)
    form = NewDeal()

    if client_id:
        client = Lead.query.filter_by(id=client_id, is_client=True).first()
        if client:
            form.clients.data = client

    if request.method == 'POST':
        if form.validate_on_submit():
            print("Form data - client data available:", form.clients.data is not None)
            if form.clients.data:
                print(f"Client ID from form: {form.clients.data.id}")
            
            deal = Deal(title=form.title.data,
                        expected_close_price=form.expected_close_price.data,
                        expected_close_date=form.expected_close_date.data,
                        probability=form.probability.data,
                        notes=form.notes.data)

            deal.client = form.clients.data
            # 🔧 CHANGED: Set default stage instead of using form selection
            deal.dealstage = DealStage.get_default_stage()

            if current_user.is_admin:
                deal.owner = form.assignees.data
            else:
                deal.owner = current_user

            db.session.add(deal)
            db.session.commit()
            
            # Log activity for deal creation - use the client from the form
            lead_client = form.clients.data  # Use the selected client from the form
            print(f"Using lead_client for activity: {lead_client}")
            
            try:
                Activity.log(
                    action_type='deal_created',
                    description=f'New deal created: {form.title.data}',
                    user=current_user,
                    lead=lead_client,
                    target_type='deal',
                    target_id=deal.id,
                    data={
                        'deal_stage': deal.dealstage.stage_name,  # Use the relationship directly
                        'expected_close_price': float(form.expected_close_price.data)
                    }
                )
                print("Activity logged successfully")
            except Exception as e:
                print(f"Error logging activity: {str(e)}")
                db.session.rollback()  # Roll back on activity error
            
            flash('Deal has been successfully created!', 'success')
            return redirect(url_for('deals.get_deals_view'))
        else:
            for error in form.errors:
                print(error)
            flash('Your form has errors! Please check the fields', 'danger')
    return render_template("deals/new_deal.html", title="New Deal", form=form, is_edit=False)


@deals.route("/deals/edit/<int:deal_id>", methods=['GET', 'POST'])
@login_required
@check_access('deals', 'update')
def update_deal(deal_id):
    # 🔧 CHANGED: Use EditDeal form for editing (includes deal stage selection)
    form = EditDeal()
    client_id = request.args.get('client', None, type=int)
    if client_id:
        client = Lead.query.filter_by(id=client_id, is_client=True).first()
        if client:
            form.clients.data = client

    deal = Deal.get_deal(deal_id)
    if not deal:
        return redirect(url_for('deals.get_deals_view'))

    if request.method == 'POST':
        if form.validate_on_submit():
            # Capture old values for activity log
            old_stage_id = deal.deal_stage_id
            old_price = deal.expected_close_price
            old_probability = deal.probability
            
            deal.title = form.title.data
            deal.expected_close_price = form.expected_close_price.data
            deal.expected_close_date = form.expected_close_date.data
            deal.deal_stage_id = form.deal_stages.data.id
            deal.probability = form.probability.data
            deal.client_id = form.clients.data.id

            if current_user.is_admin:
                deal.owner_id = form.assignees.data.id

            deal.notes = form.notes.data
            deal.last_modified = datetime.utcnow()

            db.session.commit()
            
            # Log activity for deal update
            changes = []
            if old_stage_id != deal.deal_stage_id:
                old_stage = DealStage.query.get(old_stage_id)
                new_stage = DealStage.query.get(deal.deal_stage_id)
                if old_stage and new_stage:
                    changes.append(f"Stage changed from '{old_stage.stage_name}' to '{new_stage.stage_name}'")
                
            if old_price != deal.expected_close_price:
                changes.append(f"Expected close price changed from ${old_price:.2f} to ${deal.expected_close_price:.2f}")
                
            if old_probability != deal.probability:
                changes.append(f"Probability changed from {old_probability}% to {deal.probability}%")
                
            change_description = "Deal updated" if not changes else "Deal updated: " + ", ".join(changes)
            
            # Get the client from the updated deal
            try:
                Activity.log(
                    action_type='deal_updated',
                    description=change_description,
                    user=current_user,
                    lead=form.clients.data,  # Use client from form data
                    target_type='deal',
                    target_id=deal.id
                )
            except Exception as e:
                print(f"Error logging activity: {str(e)}")
                # Continue even if activity logging fails
            
            flash('The deal has been successfully updated', 'success')
            return redirect(url_for('deals.get_deal_view', deal_id=deal.id))
        else:
            flash('Deal update failed! Form has errors', 'danger')
    elif request.method == 'GET':
        form.title.data = deal.title
        form.expected_close_price.data = deal.expected_close_price
        form.expected_close_date.data = deal.expected_close_date
        form.deal_stages.data = deal.dealstage
        form.clients.data = deal.client
        form.assignees.data = deal.owner
        form.probability.data = deal.probability
        form.notes.data = deal.notes
        form.submit.label = Label('update_deal', 'Update Deal')
    return render_template("deals/new_deal.html", title="Update Deal", form=form, is_edit=True)


@deals.route("/deals/update_stage/<int:deal_id>/<int:stage_id>")
@login_required
@check_access('deals', 'update')
def update_deal_stage_ajax(deal_id, stage_id):
    try:
        deal = Deal.query.filter_by(id=deal_id).first_or_404()
        stage = DealStage.query.filter_by(id=stage_id).first_or_404()
        
        deal.deal_stage_id = stage_id
        db.session.commit()
        
        return json.dumps({'success': True, 'message': 'Deal stage updated successfully'})
    except Exception as e:
        db.session.rollback()
        return json.dumps({'success': False, 'message': str(e)}), 500


@deals.route("/deals/reset_filters")
@login_required
@check_access('deals', 'view')
def reset_filters():
    reset_deal_filters()
    view_t = request.args.get('view_t', 'list', type=str)
    return redirect(url_for('deals.get_deals_view', view_t=view_t))


@deals.route("/deal_stages", methods=['GET', 'POST'])
@login_required
@check_access('deals', 'view')
def manage_deal_stages():
    from flask_wtf import FlaskForm
    
    form = FlaskForm()
    if request.method == 'POST' and form.validate_on_submit():
        stage_name = request.form.get('stage_name')
        if stage_name:
            # Get the maximum display_order value
            max_order = db.session.query(db.func.max(DealStage.display_order)).scalar() or 0
            new_stage = DealStage(stage_name=stage_name, display_order=max_order + 1)
            db.session.add(new_stage)
            db.session.commit()
            flash('Deal stage added successfully!', 'success')
        else:
            flash('Stage name cannot be empty.', 'danger')
    stages = DealStage.query.order_by(DealStage.display_order.asc()).all()
    return render_template("deals/manage_deal_stages.html", title="Manage Deal Stages", stages=stages, form=form)

@deals.route("/deal_stages/edit/<int:stage_id>", methods=['GET', 'POST'])
@login_required
@check_access('deals', 'update')
def edit_deal_stage(stage_id):
    """Edit a pipeline stage"""
    from flask_wtf import FlaskForm
    from wtforms import StringField, SubmitField
    from wtforms.validators import DataRequired
    
    class EditStageForm(FlaskForm):
        stage_name = StringField('Stage Name', validators=[DataRequired()])
        submit = SubmitField('Update Stage')
    
    # Get the stage
    stage = DealStage.query.get_or_404(stage_id)
    
    # Handle GET request - show the form
    if request.method == 'GET':
        form = EditStageForm()
        form.stage_name.data = stage.stage_name
        return render_template('deals/edit_stage.html', form=form, stage=stage, title="Edit Pipeline Stage")
    
    # Handle POST request - process the form
    form = FlaskForm()
    if form.validate_on_submit():
        stage_name = request.form.get('stage_name')
        if stage_name:
            stage.stage_name = stage_name
            db.session.commit()
            flash('Pipeline stage updated successfully!', 'success')
        else:
            flash('Stage name cannot be empty.', 'danger')
    return redirect(url_for('deals.manage_deal_stages'))

@deals.route("/deal_stages/delete/<int:stage_id>", methods=['GET', 'POST'])
@login_required
@check_access('deals', 'delete')
def delete_deal_stage(stage_id):
    """Delete a pipeline stage"""
    # Get the stage
    stage = DealStage.query.get_or_404(stage_id)
    
    # Handle GET request - show confirmation page
    if request.method == 'GET':
        # Check if any deals are using this stage
        deal_count = Deal.query.filter_by(deal_stage_id=stage_id).count()
        return render_template('deals/delete_stage.html', stage=stage, deal_count=deal_count, title="Delete Pipeline Stage")
    
    # Handle POST request - process the deletion
    from flask_wtf import FlaskForm
    form = FlaskForm()
    
    if form.validate_on_submit():
        # Check if any deals are using this stage
        deals_in_stage = Deal.query.filter_by(deal_stage_id=stage_id).count()
        if deals_in_stage > 0:
            flash(f'Cannot delete stage - it contains {deals_in_stage} deal(s). Please move these deals to another stage first.', 'danger')
        else:
            db.session.delete(stage)
            db.session.commit()
            flash('Pipeline stage deleted successfully!', 'success')
    return redirect(url_for('deals.manage_deal_stages'))

@deals.route("/add_deal", methods=['GET', 'POST'])
@login_required
def add_deal():
    """Add a new deal"""
    form = DealForm()
    form.deal_stage.choices = DealStage.get_stages_for_forms()
    
    # Filter clients based on user permissions
    if current_user.is_admin:
        # Admins can see all clients
        form.client.choices = Lead.get_leads_for_forms()
    else:
        # Regular users can only see clients they own
        form.client.choices = Lead.get_leads_for_forms(owner_id=current_user.id)
        
    if form.validate_on_submit():
        title = form.title.data
        client_id = form.client.data
        deal_stage_id = form.deal_stage.data
        owner_id = current_user.id
        description = form.description.data
        expected_close_date = form.expected_close_date.data
        expected_close_price = form.expected_close_price.data
        probability = form.probability.data
        now = datetime.utcnow()

