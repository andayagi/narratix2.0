"""
Shared client factory for external API services.

This module provides a centralized factory for creating and managing
external API clients (Anthropic, Hume AI) with caching and connection pooling.
"""

from typing import Optional
from anthropic import Anthropic, AsyncAnthropic
from hume import AsyncHumeClient, HumeClient
import replicate
from utils.config import settings
import logging

logger = logging.getLogger(__name__)


class ClientFactory:
    """Factory for creating cached instances of external API clients."""
    
    _anthropic_client: Optional[Anthropic] = None
    _anthropic_async_client: Optional[AsyncAnthropic] = None
    _hume_async_client: Optional[AsyncHumeClient] = None
    _hume_sync_client: Optional[HumeClient] = None
    _replicate_initialized: bool = False
    
    @classmethod
    def get_anthropic_client(cls) -> Anthropic:
        """
        Get or create a cached Anthropic client instance.
        
        Returns:
            Anthropic: Configured Anthropic client
        """
        if cls._anthropic_client is None:
            logger.debug("Creating new Anthropic client")
            cls._anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return cls._anthropic_client
    
    @classmethod
    def get_anthropic_async_client(cls) -> AsyncAnthropic:
        """
        Get or create a cached async Anthropic client instance.
        
        Returns:
            AsyncAnthropic: Configured async Anthropic client
        """
        if cls._anthropic_async_client is None:
            logger.debug("Creating new async Anthropic client")
            cls._anthropic_async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return cls._anthropic_async_client
    
    @classmethod
    def get_hume_async_client(cls) -> AsyncHumeClient:
        """
        Get or create a cached async Hume client instance.
        
        Returns:
            AsyncHumeClient: Configured async Hume client
        """
        if cls._hume_async_client is None:
            logger.debug("Creating new async Hume client")
            cls._hume_async_client = AsyncHumeClient(api_key=settings.HUME_API_KEY)
        return cls._hume_async_client
    
    @classmethod
    def get_hume_sync_client(cls) -> HumeClient:
        """
        Get or create a cached sync Hume client instance.
        
        Returns:
            HumeClient: Configured sync Hume client
        """
        if cls._hume_sync_client is None:
            logger.debug("Creating new sync Hume client")
            cls._hume_sync_client = HumeClient(api_key=settings.HUME_API_KEY)
        return cls._hume_sync_client
    
    @classmethod
    def get_replicate_client(cls):
        """
        Initialize Replicate client (it's a module, not a class).
        
        Returns:
            replicate module: Configured replicate module
        """
        if not cls._replicate_initialized:
            logger.debug("Initializing Replicate client")
            replicate.api_token = settings.REPLICATE_API_TOKEN
            cls._replicate_initialized = True
        return replicate
    
    @classmethod
    def reset_clients(cls) -> None:
        """
        Reset all cached clients. Useful for testing or config changes.
        """
        logger.debug("Resetting all cached clients")
        cls._anthropic_client = None
        cls._anthropic_async_client = None
        cls._hume_async_client = None
        cls._hume_sync_client = None
        cls._replicate_initialized = False