"""HTTP-роуты."""

from lib.present.api.routes.health_route import router_health
from lib.present.api.routes.taxi_route import router_taxi

__all__ = ["router_health", "router_taxi"]
