import logging
from core.config import get_config

logger = logging.getLogger(__name__)

class ModelRouter:
    @staticmethod
    def get_model(task_type: str, difficulty: str = None) -> str:
        """
        Determine the best model to use based on the task type and difficulty.
        Returns the model name string.
        """
        cfg = get_config()
        routing_cfg = cfg.get("model_routing", {})
        default_model = cfg["llm"]["model"]

        if not routing_cfg.get("enabled", False):
            return default_model

        routes = routing_cfg.get("routes", {})
        
        # Check if there is a route for this task type
        if task_type in routes:
            route_val = routes[task_type]
            
            # If the route is a dict (e.g., depends on difficulty)
            if isinstance(route_val, dict):
                diff = difficulty or "unknown"
                # Fallback to medium if difficulty is unknown or not explicitly defined in the dict
                model = route_val.get(diff, route_val.get("medium", default_model))
                return model
            
            # If the route is just a string
            elif isinstance(route_val, str):
                return route_val
                
        # Fallback to default if no valid route found
        return default_model
