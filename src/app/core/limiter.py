from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address, default_limits=["10 per day", "5 per hour"]
)
