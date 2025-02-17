from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)

# Cấu hình kết nối tới MySQL (điền thông tin phù hợp)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:akcyend9@rodion_mysql_master_1/expense_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Model lưu trữ ngân sách của tháng
class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7))  # định dạng YYYY-MM
    initial_budget = db.Column(db.Float)
    current_balance = db.Column(db.Float)

# Model lưu trữ giao dịch
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(255))
    price = db.Column(db.Float)  # âm cho chi tiêu, dương cho thu nhập
    date = db.Column(db.Date, default=datetime.date.today)
    archived = db.Column(db.Boolean, default=False)

# Model lưu trữ nợ
class Debt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    amount = db.Column(db.Float)
    paid_amount = db.Column(db.Float, default=0.0)
    date = db.Column(db.Date, default=datetime.date.today)
    archived = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

def check_month_transition():
    current_month = datetime.date.today().strftime("%Y-%m")
    current_budget = Budget.query.filter_by(month=current_month).first()
    if not current_budget:
        old_transactions = Transaction.query.filter(Transaction.archived == False).all()
        old_debts = Debt.query.filter(Debt.archived == False).all()
        for tx in old_transactions:
            tx.archived = True
        for debt in old_debts:
            debt.archived = True
        db.session.commit()

        new_budget = Budget(month=current_month, initial_budget=0.0, current_balance=0.0)
        db.session.add(new_budget)
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    check_month_transition()
    current_month = datetime.date.today().strftime("%Y-%m")
    budget = Budget.query.filter_by(month=current_month).first()

    if request.method == 'POST':
        try:
            if 'debt_description' in request.form and 'debt_amount' in request.form:
                description = request.form['debt_description']
                amount = float(request.form['debt_amount'])
                new_debt = Debt(description=description, amount=amount, date=datetime.date.today(), archived=False)
                db.session.add(new_debt)
                db.session.commit()

            elif 'debt_payment' in request.form and 'debt_id' in request.form:
                amount = float(request.form['debt_payment'])
                debt_id = int(request.form['debt_id'])
                debt = Debt.query.get(debt_id)
                if debt:
                    debt.paid_amount += amount
                    db.session.commit()

            elif 'expense_item' in request.form and 'expense_price' in request.form:
                item = request.form['expense_item']
                price = float(request.form['expense_price'])
                if budget:
                    budget.current_balance -= price
                    tx = Transaction(item=item, price=-price, date=datetime.date.today(), archived=False)
                    db.session.add(tx)
                    db.session.commit()

            elif 'income_amount' in request.form:
                amount = float(request.form['income_amount'])
                if budget:
                    budget.current_balance += amount
                    tx = Transaction(item="Thu nhập bất ngờ", price=amount, date=datetime.date.today(), archived=False)
                    db.session.add(tx)
                    db.session.commit()
        except ValueError:
            pass

        return redirect(url_for('index'))
    
    transactions = Transaction.query.filter(Transaction.archived == False).all()
    debts = Debt.query.filter(Debt.archived == False).all()

    total_spending = sum(tx.price for tx in transactions if tx.price < 0)
    total_earning = sum(tx.price for tx in transactions if tx.price > 0)
    total_debt = sum(debt.amount for debt in debts)
    total_paid = sum(debt.paid_amount for debt in debts)

    # Get archived months from transactions and debts
    archived_tx_months = {tx.date.strftime("%Y-%m") for tx in Transaction.query.filter(Transaction.archived == True).all()}
    archived_debt_months = {debt.date.strftime("%Y-%m") for debt in Debt.query.filter(Debt.archived == True).all()}
    archived_months = sorted(archived_tx_months.union(archived_debt_months), reverse=True)

    return render_template(
        'index.html', 
        budget=budget, 
        transactions=transactions, 
        debts=debts,
        total_spending=total_spending, 
        total_earning=total_earning,
        total_debt=total_debt, 
        total_paid=total_paid,
        archived_months=archived_months
    )


@app.route('/archive')
def do_archive():
    current_month = datetime.date.today().strftime("%Y-%m")

    transactions = Transaction.query.filter(
        Transaction.archived == False,
        Transaction.date.like(f"{current_month}-%")
    ).all()

    debts = Debt.query.filter(
        Debt.archived == False,
        Debt.date.like(f"{current_month}-%")
    ).all()

    for tx in transactions:
        tx.archived = True
    for debt in debts:
        debt.archived = True

    db.session.commit()
    return redirect(url_for('index'))


@app.route('/history/<month>')
def view_history(month):
    transactions = Transaction.query.filter(
        Transaction.archived == True,
        Transaction.date.like(f"{month}-%")
    ).all()

    debts = Debt.query.filter(
        Debt.archived == True,
        Debt.date.like(f"{month}-%")
    ).all()

    if not transactions and not debts:
        return f"Không có dữ liệu cho tháng {month}"

    total_spending = sum(tx.price for tx in transactions if tx.price < 0)
    total_earning = sum(tx.price for tx in transactions if tx.price > 0)
    total_debt = sum(debt.amount for debt in debts)
    total_paid = sum(debt.paid_amount for debt in debts)

    return render_template(
        'history.html', 
        month=month, 
        transactions=transactions, 
        debts=debts,
        total_spending=total_spending,
        total_earning=total_earning,
        total_debt=total_debt,
        total_paid=total_paid
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
