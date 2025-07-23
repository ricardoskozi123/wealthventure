from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms.fields.core import SelectField, IntegerField
from wtforms.fields.html5 import DateField, DateTimeField
from wtforms import StringField, SubmitField, FloatField, BooleanField
from wtforms.fields.simple import TextAreaField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired, Email, Optional
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from omcrm.leads.models import LeadSource, LeadStatus
from omcrm.users.models import User
from omcrm.deals.models import DealStage
class TradeForm(FlaskForm):
    instrument_id = IntegerField('Instrument ID', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    trade_type = SelectField('Trade Type', choices=[('buy', 'Buy'), ('sell', 'Sell')], validators=[DataRequired()])
    order_type = SelectField('Order Type', choices=[('market', 'Market'), ('limit', 'Limit'), ('stop_loss', 'Stop-Loss'), ('take_profit', 'Take-Profit')], validators=[DataRequired()])
    bid_price = FloatField('Bid Price', validators=[Optional()])
    ask_price = FloatField('Ask Price', validators=[Optional()])
    target_price = FloatField('Target Price', validators=[Optional()])
    submit = SubmitField('Place Order')



class EditTradeForm(FlaskForm):
    symbol = StringField('Symbol', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    trade_type = SelectField('Type', choices=[('buy', 'Buy'), ('sell', 'Sell')], validators=[DataRequired()])
    opening_date = DateTimeField('Opening Date', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    status = SelectField('Status', choices=[('open', 'Open'), ('closed', 'Closed')], validators=[DataRequired()])
    closing_date = DateTimeField('Closing Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    closing_price = FloatField('Closing Price', validators=[Optional()])
    profit_loss = FloatField('Profit/Loss', validators=[Optional()])
    submit = SubmitField('Update Trade')

class InstrumentForm(FlaskForm):
    symbol = StringField('Symbol', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    type = SelectField('Type', choices=[
        ('stock', 'Stock'), 
        ('crypto', 'Crypto'),
        ('forex', 'Forex')
    ], validators=[DataRequired()])
    submit = SubmitField('Save Instrument')
