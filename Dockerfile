FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot code
COPY bot.py .

# Set environment variables (replace with actual values)
ENV BOT_TOKEN="7644996926:AAFAqmY7nz8riytHLKfkUGKjp5t6RO96wGo"
ENV API_URL_TEMPLATE="https://godtufan-like.vercel.app//like?uid={uid}&server_name={region}&key=BHUPALI×GAGAN"
ENV WEBHOOK_URL="https://fearless-kanhaapi.onrender.com
ENV PORT=5000
ENV TZ=Asia/Kolkata

# Set timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Start the bot
CMD ["python", "bot.py"]