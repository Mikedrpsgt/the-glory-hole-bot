
from flask import Flask
from threading import Thread
import os, signal
import psutil

app = Flask('')
server = None

def cleanup_previous_instances():
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if it's a Python process running main.py
            if proc.info['name'] == 'python' and proc.pid != current_pid:
                cmdline = proc.info['cmdline']
                if cmdline and 'main.py' in cmdline:
                    print(f"Terminating previous bot instance (PID: {proc.pid})")
                    psutil.Process(proc.pid).terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    global server
    cleanup_previous_instances()
    server = Thread(target=run)
    server.daemon = True
    server.start()
    print("Keep-alive server is running!")
