from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, DateField, DateTimeField
from wtforms import StringField, SubmitField, FloatField, BooleanField, HiddenField
from wtforms import TextAreaField, PasswordField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired, Email, Optional, EqualTo, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from omcrm.leads.models import LeadSource, LeadStatus
from omcrm.users.models import User
from omcrm.deals.models import DealStage


def lead_source_query():
    return LeadSource.query


class NewLead(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(message='First name is mandatory')])
    last_name = StringField('Last Name', validators=[DataRequired(message='Last name is mandatory')])
    company_name = StringField('Company Name')
    email = StringField('Email', validators=[Email(message='Invalid Email Address!')])
    phone = StringField('Phone Number')
    country = StringField('Country', validators=[DataRequired(message='Country is mandatory')])
    
    # Keep owner assignment for admin
    assignees = QuerySelectField('Assign To', query_factory=User.user_list_query, get_pk=lambda a: a.id,
                                 get_label=User.get_label, default=User.get_current_user)
    
    # 🔧 NEW: Lead attribution fields
    funnel_name = StringField('Funnel Name', description='Marketing funnel or campaign name')
    affiliate_id = StringField('Affiliate ID', description='Affiliate partner identifier')
    
    # Trading permission toggle for clients
    available_to_trade = BooleanField('Allow Client to Trade', default=True)
    
    submit = SubmitField('Save Lead')


def filter_leads_adv_filters_admin_query():
    return [
            {'id': 1, 'title': 'Unassigned'},
            {'id': 2, 'title': 'Created Today'},
            {'id': 3, 'title': 'Created Yesterday'},
            {'id': 4, 'title': 'Created In Last 7 Days'},
            {'id': 5, 'title': 'Created In Last 30 Days'}
    ]


def filter_leads_adv_filters_user_query():
    return [
        {'id': 2, 'title': 'Created Today'},
        {'id': 3, 'title': 'Created Yesterday'},
        {'id': 4, 'title': 'Created In Last 7 Days'},
        {'id': 5, 'title': 'Created In Last 30 Days'}
    ]


class FilterLeads(FlaskForm):
    name = StringField('Name')
    source = QuerySelectField('Source', query_factory=lead_source_query, get_pk=lambda a: a.id,
                             get_label='source_name', allow_blank=True, blank_text='-- Select Source --')
    status = QuerySelectField('Status', query_factory=LeadStatus.lead_status_query, get_pk=lambda a: a.id,
                            get_label='status_name', allow_blank=True, blank_text='-- Select Status --')
    owner = QuerySelectField('Owner', query_factory=User.user_list_query, get_pk=lambda a: a.id,
                           get_label=User.get_label, allow_blank=True, blank_text='-- Select Owner --')
    created_date_from = DateField('From Date', format='%Y-%m-%d', validators=[Optional()])
    created_date_to = DateField('To Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Filter Leads')


class ImportLeads(FlaskForm):
    csv_file = FileField('CSV File', validators=[FileAllowed(['csv'])])
    lead_source = QuerySelectField(query_factory=lead_source_query, get_pk=lambda a: a.id,
                                   get_label='source_name', allow_blank=True, blank_text='Set Lead Source')
    submit = SubmitField('Create Leads')


class ConvertLead(FlaskForm):
    title = StringField('Deal Title', validators=[DataRequired('Deal title is mandatory')])
    
    # Client details
    client_first_name = StringField('First Name')
    client_last_name = StringField('Last Name')
    client_email = StringField('Email')
    client_phone = StringField('Phone')

    create_deal = BooleanField('Create Deal', default=True)

    expected_close_price = FloatField('Expected Close Price',
                                      validators=[DataRequired('Expected Close Price is mandatory')])
    expected_close_date = DateField('Expected Close Date', format='%Y-%m-%d',
                                    validators=[Optional()])
    deal_stages = QuerySelectField('Deal Stage', query_factory=DealStage.deal_stage_list_query, get_pk=lambda a: a.id,
                                   get_label=DealStage.get_label, allow_blank=False,
                                   validators=[DataRequired(message='Please select deal stage')])

    assignees = QuerySelectField('Assign To', query_factory=User.user_list_query, get_pk=lambda a: a.id,
                                 get_label=User.get_label, default=User.get_current_user)
    submit = SubmitField('Covert Lead')

class ConvertLeadToClient(FlaskForm):
    assignee = QuerySelectField('Assign To', query_factory=User.user_list_query, get_pk=lambda a: a.id,
                                get_label=User.get_label, default=User.get_current_user)
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Convert to Client')

class BulkOwnerAssign(FlaskForm):
    owners_list = QuerySelectField('Assign Owner', query_factory=User.user_list_query, get_pk=lambda a: a.id,
                                   get_label=User.get_label, default=User.get_current_user, allow_blank=False,
                                   validators=[DataRequired(message='Please select the owner')])
    submit = SubmitField('Assign Owner')


class BulkLeadSourceAssign(FlaskForm):
    lead_source_list = QuerySelectField('Assign Lead Source', query_factory=lead_source_query, get_pk=lambda a: a.id,
                                        get_label='source_name', allow_blank=False,
                                        validators=[DataRequired(message='Please select lead source')])
    submit = SubmitField('Assign Lead Source')


class BulkLeadStatusAssign(FlaskForm):
    lead_status_list = QuerySelectField(query_factory=LeadStatus.lead_status_query, get_pk=lambda a: a.id,
                                        get_label='status_name', allow_blank=False,
                                        validators=[DataRequired(message='Please select lead status')])
    submit = SubmitField('Assign Lead Status')


class BulkDelete(FlaskForm):
    submit = SubmitField('Delete Selected Leads')


class CommentForm(FlaskForm):
    lead_id = HiddenField('Lead ID')
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post Comment')

# class TradeForm(FlaskForm):
#     symbol = StringField('Symbol', validators=[DataRequired()])
#     amount = FloatField('Amount', validators=[DataRequired()])
#     price = FloatField('Price', validators=[DataRequired()])
#     trade_type = SelectField('Type', choices=[('buy', 'Buy'), ('sell', 'Sell')], validators=[DataRequired()])
#     date = DateTimeField('Date', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
#     submit = SubmitField('Submit')
#
# class EditTradeForm(FlaskForm):
#     symbol = StringField('Symbol', validators=[DataRequired()])
#     amount = FloatField('Amount', validators=[DataRequired()])
#     price = FloatField('Price', validators=[DataRequired()])
#     trade_type = SelectField('Type', choices=[('buy', 'Buy'), ('sell', 'Sell')], validators=[DataRequired()])
#     date = DateTimeField('Date', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
#     submit = SubmitField('Update Trade')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')



class UpdateBalanceForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Update Balance')

class ApplyBonusForm(FlaskForm):
    bonus_amount = FloatField('Bonus Amount ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Apply Bonus')

class CreditBalanceForm(FlaskForm):
    credit_amount = FloatField('Credit Amount ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Add Credit')
    
class LeadSourceForm(FlaskForm):
    source_name = StringField('Source Name', validators=[DataRequired()])
    api_key = StringField('API Key', validators=[Optional()])
    affiliate_id = StringField('Affiliate ID', validators=[Optional()])
    is_api_enabled = BooleanField('Enable API Access', default=False)
    submit = SubmitField('Save')

class LeadTeamShuffle(FlaskForm):
    """Form for shuffling leads among team members randomly or by count"""
    team_members = QuerySelectMultipleField('Select Team Members', 
                                           query_factory=User.user_list_query,
                                           get_pk=lambda a: a.id,
                                           get_label=User.get_label,
                                           validators=[DataRequired(message='Please select at least one team member')])
    distribution_method = SelectField('Distribution Method', 
                                     choices=[
                                         ('random', 'Random (Equal Distribution)'),
                                         ('sequential', 'Sequential (Round Robin)'),
                                         ('percentage', 'By Percentage')
                                     ],
                                     default='random',
                                     validators=[DataRequired()])
    percentages = StringField('Percentage Distribution (comma-separated)', 
                             validators=[Optional()],
                             description='For percentage distribution, enter comma-separated values, e.g. "30,30,40"')
    submit = SubmitField('Shuffle Leads')
