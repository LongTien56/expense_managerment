# Sử dụng image Python 3.8-slim làm base
FROM python:3.8-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép file requirements.txt vào container
COPY requirements.txt .

# Cài đặt các thư viện cần thiết
RUN pip install --upgrade pip && pip install -r requirements.txt

# Sao chép toàn bộ mã nguồn ứng dụng vào container
COPY . .

# Mở port 5000 (mặc định của Flask)
EXPOSE 5000

# Lệnh khởi chạy ứng dụng
CMD ["python", "expense_manager.py"]
