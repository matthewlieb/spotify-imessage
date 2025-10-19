"""
API Resilience Module for Zingaroo
Handles API changes, library updates, and graceful degradation
"""

import time
import logging
import requests
from typing import Dict, Any, Optional, Callable
from functools import wraps
import json

logger = logging.getLogger(__name__)

class APIRateLimiter:
    """Handles rate limiting with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs):
        """Retry function with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"API call failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                time.sleep(delay)

class SpotifyAPIAdapter:
    """Adapts to Spotify API changes and provides fallbacks"""
    
    def __init__(self):
        self.rate_limiter = APIRateLimiter()
        self.api_version = "v1"  # Track API version
        self.fallback_endpoints = {
            "search": "/search",
            "user": "/me",
            "playlists": "/playlists",
            "tracks": "/tracks"
        }
    
    def make_request(self, endpoint: str, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make API request with resilience"""
        try:
            # Try primary endpoint
            response = self.rate_limiter.retry_with_backoff(
                self._make_http_request,
                f"https://api.spotify.com/{self.api_version}{endpoint}",
                params=params,
                headers=headers
            )
            return response
        except Exception as e:
            logger.error(f"Primary API call failed: {e}")
            return self._handle_api_failure(endpoint, params, headers, e)
    
    def _make_http_request(self, url: str, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make HTTP request with proper error handling"""
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 429:  # Rate limited
            retry_after = int(response.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited, waiting {retry_after}s")
            time.sleep(retry_after)
            raise requests.exceptions.RequestException("Rate limited")
        
        response.raise_for_status()
        return response.json()
    
    def _handle_api_failure(self, endpoint: str, params: Dict, headers: Dict, error: Exception) -> Dict[str, Any]:
        """Handle API failures with fallbacks"""
        logger.warning(f"API failure for {endpoint}: {error}")
        
        # Try fallback endpoints
        for fallback_name, fallback_path in self.fallback_endpoints.items():
            if fallback_path in endpoint:
                try:
                    logger.info(f"Trying fallback endpoint: {fallback_path}")
                    return self._make_http_request(
                        f"https://api.spotify.com/{self.api_version}{fallback_path}",
                        params=params,
                        headers=headers
                    )
                except Exception as fallback_error:
                    logger.warning(f"Fallback {fallback_name} also failed: {fallback_error}")
                    continue
        
        # Return graceful degradation response
        return self._get_fallback_response(endpoint)
    
    def _get_fallback_response(self, endpoint: str) -> Dict[str, Any]:
        """Provide fallback data when API is unavailable"""
        if "search" in endpoint:
            return {
                "tracks": {"items": []},
                "error": "Search temporarily unavailable",
                "fallback": True
            }
        elif "playlists" in endpoint:
            return {
                "items": [],
                "error": "Playlists temporarily unavailable", 
                "fallback": True
            }
        else:
            return {
                "error": "Service temporarily unavailable",
                "fallback": True
            }

class LibraryVersionManager:
    """Manages library versions and compatibility"""
    
    def __init__(self):
        self.required_versions = {
            "spotipy": "2.25.1",
            "flask": "3.1.2",
            "requests": "2.32.5"
        }
        self.compatibility_matrix = {
            "spotipy": {
                "2.25.1": {"min_python": "3.8", "max_python": "3.12"},
                "2.24.0": {"min_python": "3.8", "max_python": "3.11"}
            }
        }
    
    def check_compatibility(self) -> Dict[str, Any]:
        """Check if current environment is compatible"""
        import sys
        import importlib.metadata
        
        compatibility_status = {
            "python_version": sys.version,
            "libraries": {},
            "warnings": [],
            "errors": []
        }
        
        for lib_name, required_version in self.required_versions.items():
            try:
                installed_version = importlib.metadata.version(lib_name)
                compatibility_status["libraries"][lib_name] = {
                    "required": required_version,
                    "installed": installed_version,
                    "compatible": self._is_version_compatible(lib_name, installed_version)
                }
                
                if not compatibility_status["libraries"][lib_name]["compatible"]:
                    compatibility_status["warnings"].append(
                        f"{lib_name} version {installed_version} may not be fully compatible"
                    )
                    
            except importlib.metadata.PackageNotFoundError:
                compatibility_status["errors"].append(f"{lib_name} not installed")
        
        return compatibility_status
    
    def _is_version_compatible(self, lib_name: str, version: str) -> bool:
        """Check if library version is compatible"""
        if lib_name not in self.compatibility_matrix:
            return True
        
        # Simple version comparison (can be enhanced)
        required = self.required_versions[lib_name]
        return version.startswith(required.split('.')[0])  # Major version match

class GracefulDegradation:
    """Handles graceful degradation when services are unavailable"""
    
    def __init__(self):
        self.degradation_modes = {
            "spotify_api_down": self._handle_spotify_down,
            "auth_failed": self._handle_auth_failed,
            "network_error": self._handle_network_error
        }
    
    def handle_degradation(self, error_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle graceful degradation based on error type"""
        if error_type in self.degradation_modes:
            return self.degradation_modes[error_type](context)
        else:
            return self._handle_unknown_error(context)
    
    def _handle_spotify_down(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle when Spotify API is down"""
        return {
            "status": "degraded",
            "message": "Spotify service temporarily unavailable. You can still upload files and process them locally.",
            "available_features": ["file_upload", "local_processing"],
            "unavailable_features": ["spotify_search", "playlist_creation"]
        }
    
    def _handle_auth_failed(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication failures"""
        return {
            "status": "auth_required",
            "message": "Please reconnect to Spotify to continue.",
            "action_required": "reauthenticate"
        }
    
    def _handle_network_error(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle network connectivity issues"""
        return {
            "status": "offline",
            "message": "Network connection required for full functionality.",
            "available_features": ["offline_file_processing"]
        }
    
    def _handle_unknown_error(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown errors"""
        return {
            "status": "error",
            "message": "An unexpected error occurred. Please try again.",
            "support_info": "If this persists, please check your internet connection."
        }

# Global instances
api_adapter = SpotifyAPIAdapter()
version_manager = LibraryVersionManager()
degradation_handler = GracefulDegradation()

def resilient_api_call(endpoint: str, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
    """Make resilient API call with all fallbacks"""
    try:
        return api_adapter.make_request(endpoint, params, headers)
    except Exception as e:
        logger.error(f"API call failed completely: {e}")
        return degradation_handler.handle_degradation("spotify_api_down", {"error": str(e)})

def check_system_health() -> Dict[str, Any]:
    """Check overall system health and compatibility"""
    health_status = {
        "timestamp": time.time(),
        "compatibility": version_manager.check_compatibility(),
        "api_status": "unknown"
    }
    
    # Test API connectivity
    try:
        test_response = api_adapter.make_request("/me")
        health_status["api_status"] = "healthy" if "id" in test_response else "degraded"
    except Exception as e:
        health_status["api_status"] = "unavailable"
        health_status["api_error"] = str(e)
    
    return health_status
