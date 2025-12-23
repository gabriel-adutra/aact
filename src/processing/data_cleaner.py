from typing import Dict, Any, List
from .text_parser import TextParser

class DataCleaner:
    def __init__(self):
        # Initialize parser once
        self.parser = TextParser()

    def clean_study(self, raw_study: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms raw SQL row into a clean Neo4j-ready dictionary.
        
        Args:
            raw_study: Dictionary returned by AACTClient.fetch_trials()
            
        Returns:
            Clean dictionary with normalized strings and inferred attributes.
        """
        study = {
            'nct_id': raw_study.get('nct_id'),
            'title': (raw_study.get('brief_title') or "").strip(),
            'phase': raw_study.get('phase'),
            'status': raw_study.get('overall_status'),
            'drugs': [],
            'conditions': [],
            'sponsors': []
        }

        # --- Process Drugs & Infer Attributes ---
        raw_drugs = raw_study.get('drugs')
        # SQL json_agg returns None if empty, or a list
        if raw_drugs and isinstance(raw_drugs, list):
            for d in raw_drugs:
                # d structure: {'name': '...', 'description': '...'}
                raw_name = d.get('name')
                if not raw_name:
                    continue
                    
                name = raw_name.strip().title() # Normalize: "aspirin" -> "Aspirin"
                desc = d.get('description') or ""
                
                # Infer metadata using our rule-based parser
                inferred = self.parser.infer_attributes(desc)
                
                study['drugs'].append({
                    'name': name,
                    'route': inferred['route'],
                    'dosage_form': inferred['dosage_form']
                })

        # --- Process Conditions ---
        raw_conditions = raw_study.get('conditions')
        if raw_conditions and isinstance(raw_conditions, list):
            # Dedup and normalize
            clean_conds = set()
            for c in raw_conditions:
                if c:
                    clean_conds.add(c.strip().title()) # "lung cancer" -> "Lung Cancer"
            
            study['conditions'] = [{'name': c} for c in clean_conds]

        # --- Process Sponsors ---
        raw_sponsors = raw_study.get('sponsors')
        if raw_sponsors and isinstance(raw_sponsors, list):
            for s in raw_sponsors:
                raw_name = s.get('name')
                if not raw_name:
                    continue
                    
                name = raw_name.strip() # Keep original casing for Orgs usually
                # Optional: Remove common suffixes if desired (Inc, LLC) - Skipping for KISS
                
                study['sponsors'].append({
                    'name': name,
                    'class': s.get('class')
                })

        return study

