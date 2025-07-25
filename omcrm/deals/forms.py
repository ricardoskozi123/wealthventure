from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, IntegerField, DateField
from wtforms import StringField, SubmitField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange
from wtforms.widgets import TextArea
from wtforms_sqlalchemy.fields import QuerySelectField
from flask_login import current_user

from omcrm.users.models import User
from omcrm.leads.models import Lead
from omcrm.deals.models import DealStage


def get_clients_query():
    # Base query for clients
    query = Lead.query.filter_by(is_client=True)
    
    # If user is not admin, only show clients they own
    if not current_user.is_admin:
        query = query.filter_by(owner_id=current_user.id)
        
    return query


def get_client_label(client):
    return f"{client.first_name} {client.last_name} - {client.email if client.email else '(no email)'}"


class NewDeal(FlaskForm):
    title = StringField('Deal Title', validators=[DataRequired('Deal title is mandatory')])
    expected_close_price = FloatField('Expected Close Price',
                                       validators=[DataRequired('Expected Close Price is mandatory')])
    # 🔧 CHANGED: Use DateField instead of DateTimeLocalField (date only, no time)
    expected_close_date = DateField('Expected Close Date', format='%Y-%m-%d',
                                     validators=[Optional()])
    # 🔧 REMOVED: deal_stages field - will be set to "In Progress" by default in creation
    clients = QuerySelectField('Client', query_factory=get_clients_query, get_pk=lambda a: a.id,
                               get_label=get_client_label, blank_text='Select A Client', allow_blank=True,
                               validators=[DataRequired(message='Please choose a client for the deal')])
    assignees = QuerySelectField('Assign To', query_factory=User.user_list_query, get_pk=lambda a: a.id,
                                  get_label=User.get_label, default=User.get_current_user)
    probability = IntegerField('Probability (%)', validators=[
        DataRequired(message='Probability is mandatory'),
        NumberRange(min=0, max=100, message='Probability must be between 0 and 100')
    ], default=50)
    notes = StringField('Notes', widget=TextArea())
    submit = SubmitField('Create New Deal')


# 🔧 NEW: Separate form for editing deals (includes deal stage selection)
class EditDeal(FlaskForm):
    title = StringField('Deal Title', validators=[DataRequired('Deal title is mandatory')])
    expected_close_price = FloatField('Expected Close Price',
                                       validators=[DataRequired('Expected Close Price is mandatory')])
    expected_close_date = DateField('Expected Close Date', format='%Y-%m-%d',
                                     validators=[Optional()])
    # 🔧 INCLUDED: deal_stages field for editing (user can change stage)
    deal_stages = QuerySelectField('Deal Stage', query_factory=DealStage.deal_stage_list_query, get_pk=lambda a: a.id,
                                  get_label=DealStage.get_label, allow_blank=False,
                                  validators=[DataRequired(message='Please select deal stage')])
    clients = QuerySelectField('Client', query_factory=get_clients_query, get_pk=lambda a: a.id,
                               get_label=get_client_label, blank_text='Select A Client', allow_blank=True,
                               validators=[DataRequired(message='Please choose a client for the deal')])
    assignees = QuerySelectField('Assign To', query_factory=User.user_list_query, get_pk=lambda a: a.id,
                                  get_label=User.get_label, default=User.get_current_user)
    probability = IntegerField('Probability (%)', validators=[
        DataRequired(message='Probability is mandatory'),
        NumberRange(min=0, max=100, message='Probability must be between 0 and 100')
    ], default=50)
    notes = StringField('Notes', widget=TextArea())
    submit = SubmitField('Update Deal')


def filter_deals_adv_filters_query():
    return [
        {'id': 1, 'title': 'All Expired Deals'},
        {'id': 2, 'title': 'All Active Deals'},
        {'id': 3, 'title': 'Deals Expiring Today'},
        {'id': 4, 'title': 'Deals Expiring In Next 7 Days'},
        {'id': 5, 'title': 'Deals Expiring In Next 30 Days'},
        {'id': 6, 'title': 'Created Today'},
        {'id': 7, 'title': 'Created Yesterday'},
        {'id': 8, 'title': 'Created In Last 7 Days'},
        {'id': 9, 'title': 'Created In Last 30 Days'}
    ]


def filter_deals_price_query():
    return [
        {'id': 1, 'title': '< 500'},
        {'id': 2, 'title': '>= 500 and < 1000'},
        {'id': 3, 'title': '>= 1000 and < 10,000'},
        {'id': 4, 'title': '>= 10,000 and < 50,000'},
        {'id': 5, 'title': '>= 50,000 and < 100,000'},
        {'id': 6, 'title': '>= 100,000'},
    ]


class FilterDeals(FlaskForm):
    txt_search = StringField()
    assignees = QuerySelectField(query_factory=User.user_list_query, get_pk=lambda a: a.id,
                                 get_label=User.get_label, allow_blank=True, blank_text='[-- Select Owner --]')

    clients = QuerySelectField(query_factory=get_clients_query, get_pk=lambda a: a.id,
                               get_label=get_client_label, blank_text='[-- Select Client --]', allow_blank=True)

    deal_stages = QuerySelectField(query_factory=DealStage.deal_stage_list_query, get_pk=lambda a: a.id,
                                   get_label=DealStage.get_label, blank_text='[-- Deal Stage --]', allow_blank=True)

    price_range = QuerySelectField(query_factory=filter_deals_price_query,
                                   get_pk=lambda a: a['id'],
                                   get_label=lambda a: a['title'],
                                   allow_blank=True, blank_text='[-- Price Range --]')

    advanced_user = QuerySelectField(query_factory=filter_deals_adv_filters_query,
                                     get_pk=lambda a: a['id'],
                                     get_label=lambda a: a['title'],
                                     allow_blank=True, blank_text='[-- advanced filter --]')

    submit = SubmitField('Filter Deals')
