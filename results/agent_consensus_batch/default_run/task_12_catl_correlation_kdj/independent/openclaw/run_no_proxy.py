#!/usr/bin/env python3
"""
Proxy bypass wrapper - must run before any network imports
"""
import sys
import os

# Set environment variables
os.environ['NO_PROXY'] = '*'
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ[key] = ''

# Patch urllib.request.getproxies before any imports
import urllib.request
urllib.request.getproxies = lambda: {}
urllib.request.proxy_bypass = lambda host: True

# Patch urllib3 ProxyManager
try:
    from urllib3 import poolmanager
    original_proxy_from_url = poolmanager.proxy_from_url
    def no_proxy(*args, **kwargs):
        raise RuntimeError("Proxy disabled")
    poolmanager.proxy_from_url = no_proxy
except:
    pass

# Now run the actual script
exec(open('/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_12_catl_correlation_kdj/independent/openclaw/solve_task.py').read())
