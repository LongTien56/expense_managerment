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
    archived = db.Column(db.Boolean, default=False)  # False: giao dịch tháng hiện tại, True: đã archive

with app.app_context():
    db.create_all()

def check_month_transition():
    """
    Kiểm tra chuyển tháng: nếu không có record ngân sách của tháng hiện tại,
    archive giao dịch của tháng cũ và tạo record mới.
    """
    current_month = datetime.date.today().strftime("%Y-%m")
    current_budget = Budget.query.filter_by(month=current_month).first()
    if not current_budget:
        # Archive các giao dịch của các tháng cũ (chỉ archive những giao dịch chưa archive)
        old_transactions = Transaction.query.filter(
            Transaction.archived == False,
            ~Transaction.date.like(f"{current_month}-%")
        ).all()
        for tx in old_transactions:
            tx.archived = True
        db.session.commit()
        # Tạo record ngân sách mới cho tháng hiện tại với giá trị ban đầu là 0.0
        new_budget = Budget(month=current_month, initial_budget=0.0, current_balance=0.0)
        db.session.add(new_budget)
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    check_month_transition()  # Kiểm tra và xử lý chuyển tháng khi truy cập trang chính

    current_month = datetime.date.today().strftime("%Y-%m")
    budget = Budget.query.filter_by(month=current_month).first()

    if request.method == 'POST':
        # Nhập ngân sách ban đầu (chỉ khi record ngân sách chưa có)
        if 'initial_budget' in request.form:
            try:
                initial_budget = float(request.form['initial_budget'])
                if not budget:
                    budget = Budget(month=current_month,
                                    initial_budget=initial_budget,
                                    current_balance=initial_budget)
                    db.session.add(budget)
                else:
                    budget.initial_budget = initial_budget
                    budget.current_balance = initial_budget
                db.session.commit()
            except ValueError:
                pass

        # Nhập chi tiêu
        elif 'expense_item' in request.form and 'expense_price' in request.form:
            try:
                item = request.form['expense_item']
                price = float(request.form['expense_price'])
                if budget:
                    budget.current_balance -= price
                    tx = Transaction(item=item,
                                     price=-price,
                                     date=datetime.date.today(),
                                     archived=False)
                    db.session.add(tx)
                    db.session.commit()
            except ValueError:
                pass

        # Nhập thu nhập bất ngờ
        elif 'income_amount' in request.form:
            try:
                amount = float(request.form['income_amount'])
                if budget:
                    budget.current_balance += amount
                    tx = Transaction(item="Thu nhập bất ngờ",
                                     price=amount,
                                     date=datetime.date.today(),
                                     archived=False)
                    db.session.add(tx)
                    db.session.commit()
            except ValueError:
                pass

        return redirect(url_for('index'))
    
    # Lấy các giao dịch của tháng hiện tại (chưa archive)
    transactions = Transaction.query.filter(
        Transaction.archived == False,
        Transaction.date.like(f"{current_month}-%")
    ).all()

    # Tính danh sách các tháng đã archive từ các giao dịch (lấy duy nhất các tháng)
    archived_tx = Transaction.query.filter(Transaction.archived == True).all()
    archived_months_set = {tx.date.strftime("%Y-%m") for tx in archived_tx}
    archived_months = sorted(archived_months_set)

    return render_template('index.html', budget=budget, transactions=transactions, archived_months=archived_months)

# Route để archive giao dịch của tháng hiện tại
@app.route('/archive')
def do_archive():
    current_month = datetime.date.today().strftime("%Y-%m")
    transactions = Transaction.query.filter(
        Transaction.archived == False,
        Transaction.date.like(f"{current_month}-%")
    ).all()
    for tx in transactions:
        tx.archived = True
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/history/<month>')
def view_history(month):
    transactions = Transaction.query.filter(
        Transaction.archived == True,
        Transaction.date.like(f"{month}-%")
    ).all()
    if not transactions:
        return f"Không có dữ liệu cho tháng {month}"
    return render_template('history.html', month=month, transactions=transactions)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)