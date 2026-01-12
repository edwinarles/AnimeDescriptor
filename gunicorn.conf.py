# Gunicorn configuration file for Render deployment
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Worker processes
workers = 2
worker_class = 'sync'

# Timeouts (INCREASED to handle SMTP delays)
timeout = 120  # Increased from default 30s to 120s
graceful_timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'otakudescriptor'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Preload app for faster worker spawn
preload_app = True
