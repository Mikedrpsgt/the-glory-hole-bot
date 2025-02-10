
from flask import Flask
from threading import Thread
import os, signal
import psutil
import logging

app = Flask('')
server = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_previous_instances():
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' and proc.pid != current_pid:
                cmdline = proc.info['cmdline']
                if cmdline and 'main.py' in cmdline:
                    logger.info(f"Terminating previous bot instance (PID: {proc.pid})")
                    psutil.Process(proc.pid).terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Error during cleanup: {str(e)}")
            continue

@app.route('/')
def home():
    return "Bot is alive and running!"

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": psutil.boot_time()}

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    global server
    cleanup_previous_instances()
    server = Thread(target=run)
    server.daemon = True
    server.start()
    logger.info("Keep-alive server is running!")
