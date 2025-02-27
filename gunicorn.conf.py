# Gunicorn configuration file

# Server socket binding
bind = "0.0.0.0:10000"

# Worker processes
workers = 2
worker_class = "sync"
threads = 4

# Timeout settings
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "RevisionTimetable"

# SSL/TLS settings (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Max requests settings
max_requests = 1000
max_requests_jitter = 50

# Security settings
limit_request_line = 4096
limit_request_fields = 100