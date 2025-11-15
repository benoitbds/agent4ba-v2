"""Global application context for sharing state across the application."""

import asyncio
from typing import Optional

# Global variable to hold the main event loop
EVENT_LOOP: Optional[asyncio.AbstractEventLoop] = None
