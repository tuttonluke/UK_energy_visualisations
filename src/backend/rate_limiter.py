"""
===============================================================================
File: rate_limiter.py
Description: Provides rate limiting functionality for API endpoints.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
