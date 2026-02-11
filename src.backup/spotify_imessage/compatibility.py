"""
Compatibility and resilience module for Zingaroo CLI
Ensures the CLI works even when APIs or libraries change
"""

import sys
import importlib.metadata
import logging
from typing import Dict, Any, List, Optional
import warnings

logger = logging.getLogger(__name__)

class CompatibilityChecker:
    """Checks and manages compatibility across different environments"""
    
    def __init__(self):
        self.required_packages = {
            "spotipy": "2.25.1",
            "click": "8.2.1", 
            "requests": "2.32.5"
        }
        
        self.compatibility_matrix = {
            "python": {
                "min_version": (3, 8),
                "max_version": (3, 12),
                "recommended": (3, 10)
            },
            "spotipy": {
                "2.25.1": {"min_python": (3, 8), "max_python": (3, 12)},
                "2.24.0": {"min_python": (3, 8), "max_python": (3, 11)},
                "2.23.0": {"min_python": (3, 8), "max_python": (3, 10)}
            }
        }
    
    def check_environment(self) -> Dict[str, Any]:
        """Check if the current environment is compatible"""
        results = {
            "python_version": sys.version_info[:3],
            "packages": {},
            "warnings": [],
            "errors": [],
            "compatible": True
        }
        
        # Check Python version
        python_version = sys.version_info[:3]
        min_version = self.compatibility_matrix["python"]["min_version"]
        max_version = self.compatibility_matrix["python"]["max_version"]
        
        if python_version < min_version:
            results["errors"].append(f"Python {python_version} is too old. Minimum: {min_version}")
            results["compatible"] = False
        elif python_version > max_version:
            results["warnings"].append(f"Python {python_version} may not be fully supported. Max: {max_version}")
        
        # Check package versions
        for package, required_version in self.required_packages.items():
            try:
                installed_version = importlib.metadata.version(package)
                results["packages"][package] = {
                    "required": required_version,
                    "installed": installed_version,
                    "compatible": self._is_package_compatible(package, installed_version)
                }
                
                if not results["packages"][package]["compatible"]:
                    results["warnings"].append(
                        f"{package} version {installed_version} may cause issues. Recommended: {required_version}"
                    )
                    
            except importlib.metadata.PackageNotFoundError:
                results["errors"].append(f"Required package {package} not installed")
                results["compatible"] = False
        
        return results
    
    def _is_package_compatible(self, package: str, version: str) -> bool:
        """Check if a package version is compatible"""
        if package not in self.compatibility_matrix:
            return True
        
        # Simple version comparison - can be enhanced
        required = self.required_packages[package]
        major_required = required.split('.')[0]
        major_installed = version.split('.')[0]
        
        return major_installed == major_required
    
    def get_fallback_suggestions(self, errors: List[str]) -> List[str]:
        """Get suggestions for fixing compatibility issues"""
        suggestions = []
        
        for error in errors:
            if "not installed" in error:
                package = error.split()[0]
                suggestions.append(f"Install missing package: pip install {package}")
            elif "too old" in error:
                suggestions.append("Consider upgrading Python or using a virtual environment")
            elif "version" in error:
                suggestions.append("Try: pip install --upgrade <package-name>")
        
        return suggestions

class APIFallbackManager:
    """Manages fallbacks when Spotify API is unavailable"""
    
    def __init__(self):
        self.fallback_modes = {
            "offline": self._offline_mode,
            "cached": self._cached_mode,
            "degraded": self._degraded_mode
        }
    
    def handle_api_failure(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API failures with appropriate fallbacks"""
        error_type = type(error).__name__
        
        if "ConnectionError" in error_type or "Timeout" in error_type:
            return self.fallback_modes["offline"](context)
        elif "AuthenticationError" in error_type:
            return self._handle_auth_error(context)
        else:
            return self.fallback_modes["degraded"](context)
    
    def _offline_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle offline mode when API is unavailable"""
        return {
            "mode": "offline",
            "message": "Spotify API unavailable. You can still process local files.",
            "available_features": ["file_processing", "local_playlist_creation"],
            "unavailable_features": ["spotify_search", "online_playlist_sync"]
        }
    
    def _cached_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cached mode with limited functionality"""
        return {
            "mode": "cached",
            "message": "Using cached data. Some features may be limited.",
            "available_features": ["cached_search", "offline_playlist_creation"],
            "unavailable_features": ["real_time_search", "live_playlist_sync"]
        }
    
    def _degraded_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle degraded mode with basic functionality"""
        return {
            "mode": "degraded",
            "message": "Limited functionality available. Please check your connection.",
            "available_features": ["basic_file_processing"],
            "unavailable_features": ["spotify_integration", "playlist_creation"]
        }
    
    def _handle_auth_error(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication errors"""
        return {
            "mode": "auth_required",
            "message": "Authentication required. Please run 'zingaroo auth' to login.",
            "action_required": "authenticate",
            "available_features": ["file_processing"],
            "unavailable_features": ["spotify_features"]
        }

class VersionManager:
    """Manages version compatibility and updates"""
    
    def __init__(self):
        self.current_version = "1.0.0"
        self.minimum_compatible_version = "1.0.0"
    
    def check_for_updates(self) -> Dict[str, Any]:
        """Check if updates are available (placeholder for future implementation)"""
        return {
            "current_version": self.current_version,
            "update_available": False,
            "latest_version": self.current_version,
            "update_message": "You're running the latest version"
        }
    
    def get_compatibility_info(self) -> Dict[str, Any]:
        """Get compatibility information for the current setup"""
        checker = CompatibilityChecker()
        env_check = checker.check_environment()
        
        return {
            "zingaroo_version": self.current_version,
            "environment": env_check,
            "recommendations": self._get_recommendations(env_check)
        }
    
    def _get_recommendations(self, env_check: Dict[str, Any]) -> List[str]:
        """Get recommendations based on environment check"""
        recommendations = []
        
        if not env_check["compatible"]:
            recommendations.append("Fix compatibility issues before proceeding")
        
        if env_check["warnings"]:
            recommendations.append("Consider updating packages for better stability")
        
        if env_check["errors"]:
            recommendations.append("Install missing dependencies: pip install -r requirements.txt")
        
        return recommendations

# Global instances
compatibility_checker = CompatibilityChecker()
fallback_manager = APIFallbackManager()
version_manager = VersionManager()

def check_system_compatibility() -> Dict[str, Any]:
    """Check overall system compatibility"""
    return compatibility_checker.check_environment()

def handle_api_failure(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle API failures with fallbacks"""
    if context is None:
        context = {}
    return fallback_manager.handle_api_failure(error, context)

def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information"""
    return {
        "compatibility": check_system_compatibility(),
        "version_info": version_manager.get_compatibility_info(),
        "fallback_capabilities": list(fallback_manager.fallback_modes.keys())
    }
