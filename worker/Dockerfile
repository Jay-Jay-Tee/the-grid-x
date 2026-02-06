# Grid-X Worker - run on machine(s) that have Docker. Connect to coordinator via COORDINATOR_WS.
# On the machine that runs the coordinator, use a different host (e.g. host IP or service name).
# Example: docker run -e COORDINATOR_WS=ws://192.168.1.10:8080/ws/worker -v /var/run/docker.sock:/var/run/docker.sock grid-x-worker

FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI so we can talk to the host's Docker (socket mounted at run time)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Set when running: COORDINATOR_WS=ws://<coordinator-host>:8080/ws/worker
# Optional: WORKER_OWNER_ID=user_id (to receive credits when jobs run here)
ENV COORDINATOR_WS=ws://localhost:8080/ws/worker

CMD ["python", "main.py"]
