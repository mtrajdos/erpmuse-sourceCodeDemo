"""Global session information"""
from datetime import datetime
import time

SESSION_TIMESTAMP = datetime.now().strftime('%d%b%Y_%H-%M-%S').upper()

"""Utility functions"""
def get_elapsed_time():
    """Get POSIX time"""
    return time.time()

def get_session_id():
    """Get session timestamp string"""
    return SESSION_TIMESTAMP