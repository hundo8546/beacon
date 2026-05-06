FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN addgroup --system beacon && adduser --system --group beacon

COPY signalpilotv0/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY signalpilotv0/ ./signalpilotv0/

# Set ownership to non-root user
RUN chown -R beacon:beacon /app

USER beacon

EXPOSE 8080

ENV PORT=8080
ENV HOST=0.0.0.0
ENV BEACON_ENV=production

CMD ["python", "signalpilotv0/api.py", "8080"]
