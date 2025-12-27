import yaml
import os
from typing import Dict

class TextParser:
    def __init__(self, config_path: str = "config/text_rules.yaml"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            self.rules = yaml.safe_load(f)

        self.routes = self.rules.get('routes', {})
        self.forms = self.rules.get('dosage_forms', {})


    def infer_route_and_form(self, text: str) -> Dict[str, str]:
        if not text or not isinstance(text, str):
            return {'route': 'Unknown', 'dosage_form': 'Unknown'}

        text_lower = text.lower()
        route = self._match_route(text_lower)
        form = self._match_form(text_lower)

        return {'route': route, 'dosage_form': form}


    def _match_route(self, text_lower: str) -> str:
        for route_name, keywords in self.routes.items():
            if any(k in text_lower for k in keywords):
                return route_name
        return 'Unknown'
        

    def _match_form(self, text_lower: str) -> str:
        for form_name, keywords in self.forms.items():
            if any(k in text_lower for k in keywords):
                return form_name
        return 'Unknown'

