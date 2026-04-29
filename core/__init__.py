"""
MemoMind Core - 核心模块
"""

from .database import Database
from .search_service import SearchService
from .models import Note

__all__ = ['Database', 'SearchService', 'Note']
__version__ = '0.1.0'
