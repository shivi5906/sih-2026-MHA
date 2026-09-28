from __future__ import annotations
import asyncio
import logging
import random
import time
from typing import Any

import aiohttp
from vaultx.config import Config
from vaultx.providers.base import DataProvider

logger = logging.getLogger(__name__)

class LiveProvider(DataProvider):
    """Live API provider with rate limiting and retry logic."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 60.0
        
        # Per-chain concurrency limits and request time tracking
        self._chain_locks: dict[str, asyncio.Semaphore] = {}
        self._last_request_times: dict[str, float] = {}
        
    def _get_semaphore(self, chain: str) -> asyncio.Semaphore:
        """Get or create a semaphore for per-chain rate limiting."""
        if chain not in self._chain_locks:
            self._chain_locks[chain] = asyncio.Semaphore(5)
        return self._chain_locks[chain]

    def _prepare_request(self, chain: str, endpoint: str, params: dict[str, Any] | None, headers: dict[str, str] | None) -> tuple[str, dict[str, Any], dict[str, str]]:
        """Construct full URL and inject API keys.
        
        Reads from Config.chains dict which maps chain name -> ChainConfig
        with api_base_url, api_key, and extra_headers fields.
        """
        params = params or {}
        headers = headers or {}
        
        chain_config = self.config.chains.get(chain.lower())
        if chain_config:
            base_url = chain_config.api_base_url
            endpoint_clean = endpoint.lstrip('/')
            if not endpoint_clean:
                url = base_url
            elif '?' in base_url:
                base_path, query = base_url.split('?', 1)
                url = f"{base_path.rstrip('/')}/{endpoint_clean}?{query}"
            else:
                url = f"{base_url.rstrip('/')}/{endpoint_clean}"
                
            api_key = chain_config.api_key
            
            # Etherscan takes API key as a query param
            if chain.lower() == 'ethereum' and api_key:
                params['apikey'] = api_key
            # TronGrid takes API key as a header
            elif chain.lower() == 'tron' and api_key:
                headers['TRON-PRO-API-KEY'] = api_key
            
            # Merge any extra headers from chain config
            headers.update(chain_config.extra_headers)
        else:
            url = endpoint
            
        return url, params, headers
        
    def _is_etherscan_rate_limit(self, response_data: dict[str, Any]) -> bool:
        """Check for Etherscan's specific rate limit response."""
        return (
            response_data.get('status') == '0' and 
            response_data.get('message') == 'NOTOK'
        )

    async def fetch(self, chain: str, endpoint: str, params: dict[str, Any] | None = None,
                    headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Fetch data from the live API with retry and backoff logic."""
        url, final_params, final_headers = self._prepare_request(chain, endpoint, params, headers)
        
        semaphore = self._get_semaphore(chain)
        chain_cfg = self.config.chains.get(chain.lower())
        qps = chain_cfg.rate_limit_qps if chain_cfg else 3
        min_interval = 1.0 / max(qps, 1)

        for attempt in range(self.max_retries + 1):
            async with semaphore:
                # Add delay to strictly enforce QPS limits
                now = time.time()
                last_time = self._last_request_times.get(chain, 0.0)
                time_since_last = now - last_time
                if time_since_last < min_interval:
                    await asyncio.sleep(min_interval - time_since_last)
                
                self._last_request_times[chain] = time.time()
                
                logger.debug(f"Fetching {url} for chain {chain} (Attempt {attempt + 1})")
                try:
                    async with self.session.get(url, params=final_params, headers=final_headers) as response:
                        if response.status in (429, 503):
                            logger.debug(f"Received {response.status} for {url}, backing off...")
                            await self._backoff(attempt)
                            continue
                            
                        response.raise_for_status()
                        data = await response.json()
                        
                        if chain.lower() == 'ethereum' and self._is_etherscan_rate_limit(data):
                            logger.debug(f"Received Etherscan rate limit for {url}, backing off...")
                            await self._backoff(attempt)
                            continue
                            
                        return data
                except aiohttp.ClientError as e:
                    if attempt == self.max_retries:
                        raise e
                    logger.debug(f"ClientError: {e}, backing off...")
                    await self._backoff(attempt)
                    
        raise Exception(f"Max retries exceeded for {url}")

    async def _backoff(self, attempt: int) -> None:
        """Calculate and wait for exponential backoff with jitter."""
        if attempt >= self.max_retries:
            return
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = delay * 0.1 * random.uniform(-1, 1)
        await asyncio.sleep(delay + jitter)

    async def close(self) -> None:
        """Clean up the aiohttp session."""
        await self.session.close()
