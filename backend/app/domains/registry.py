import importlib
import logging
from typing import Dict, Optional, List
from .base import BaseDomain

logger = logging.getLogger(__name__)

_DOMAINS: Dict[str, BaseDomain] = {}
_REGISTRY_LOADED = False

DOMAIN_SLUGS = [
    "marketing",
    "software_engineering",
    "finance",
    "hr",
    "sales",
]


def _load_domain(slug: str) -> Optional[BaseDomain]:
    """Dynamically import a domain module by slug."""
    try:
        module_path = f"backend.app.domains.{slug}"
        module = importlib.import_module(module_path)

        if hasattr(module, "domain"):
            return module.domain
        else:
            logger.warning("Domain module '%s' has no 'domain' attribute", slug)
            return None
    except ImportError as e:
        logger.error("Failed to import domain '%s': %s", slug, e)
        return None
    except Exception as e:
        logger.error("Error loading domain '%s': %s", slug, e)
        return None


def _load_all():
    """Load all registered domains."""
    global _REGISTRY_LOADED
    if _REGISTRY_LOADED:
        return

    for slug in DOMAIN_SLUGS:
        domain = _load_domain(slug)
        if domain:
            _DOMAINS[slug] = domain
            logger.info("Loaded domain: %s (%s)", slug, domain.name)

    _REGISTRY_LOADED = True
    logger.info("Domain registry loaded: %d domains", len(_DOMAINS))


class DomainRegistry:
    """Central registry for accessing domains."""

    def __init__(self):
        _load_all()

    def get(self, slug: str) -> Optional[BaseDomain]:
        """Get a domain by slug."""
        return _DOMAINS.get(slug)

    def list_domains(self) -> List[Dict[str, str]]:
        """List all available domains with name and description."""
        return [
            {"slug": slug, "name": d.name, "description": d.description}
            for slug, d in _DOMAINS.items()
        ]

    def list_slugs(self) -> List[str]:
        """List all domain slugs."""
        return list(_DOMAINS.keys())

    def is_valid(self, slug: str) -> bool:
        """Check if a domain slug is valid."""
        return slug in _DOMAINS


_registry: Optional[DomainRegistry] = None


def get_registry() -> DomainRegistry:
    """Get or create the singleton DomainRegistry."""
    global _registry
    if _registry is None:
        _registry = DomainRegistry()
    return _registry


def reset_registry():
    """Reset the registry (useful for testing)."""
    global _registry, _REGISTRY_LOADED
    _DOMAINS.clear()
    _REGISTRY_LOADED = False
    _registry = None
