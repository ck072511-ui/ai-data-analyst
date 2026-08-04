import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SemanticLayerService:
    def __init__(self):
        # In-memory Business Glossary Catalog
        self._business_glossary = {
            "revenue": {
                "description": "Total monetary amount received for goods sold or services provided.",
                "category": "Finance",
                "synonyms": ["turnover", "earnings", "sales_revenue", "amount", "revenue_amount"]
            },
            "profit": {
                "description": "Financial benefit realized when revenue generated exceeds expenses.",
                "category": "Finance",
                "synonyms": ["earnings", "margin", "net_income", "profit_margin"]
            },
            "customer": {
                "description": "A person or organization that buys goods or services.",
                "category": "Operations",
                "synonyms": ["client", "buyer", "user", "purchaser"]
            },
            "churn": {
                "description": "The rate at which customers stop doing business with an entity.",
                "category": "Marketing",
                "synonyms": ["retention", "attrition", "loss", "exit"]
            }
        }

        # KPI & Metric catalog
        self._kpi_catalog = {
            "monthly_sales_growth": {
                "description": "Percentage increase in sales compared to the previous month.",
                "formula": "((Current Month Sales - Previous Month Sales) / Previous Month Sales) * 100",
                "dimensions": ["month", "region", "product_category"]
            },
            "customer_churn_rate": {
                "description": "Percentage of customers lost during a specified period.",
                "formula": "(Customers Lost in Period / Total Customers at Start of Period) * 100",
                "dimensions": ["month", "cohort", "plan_type"]
            },
            "average_transaction_value": {
                "description": "Average amount spent per purchase transaction.",
                "formula": "Total Revenue / Total Transaction Count",
                "dimensions": ["region", "customer_segment"]
            }
        }

        # Dimension catalog
        self._dimensions = {
            "region": ["state", "country", "city", "territory", "zip_code"],
            "date": ["year", "quarter", "month", "day", "weekday"],
            "product": ["product_category", "product_name", "sku", "brand"]
        }

    def get_business_glossary(self) -> Dict[str, Any]:
        """Returns the complete business terms glossary catalog."""
        return self._business_glossary

    def get_kpi_catalog(self) -> Dict[str, Any]:
        """Returns the catalog of configured KPI calculations formulas."""
        return self._kpi_catalog

    def get_dimensions(self) -> Dict[str, Any]:
        """Returns categories dimensions mapping catalog."""
        return self._dimensions

    def resolve_synonyms(self, term: str) -> List[str]:
        """Resolves list of synonyms for a given business keyword."""
        term_clean = term.lower().strip()
        
        # Check direct match
        if term_clean in self._business_glossary:
            return self._business_glossary[term_clean]["synonyms"]

        # Check in synonyms list
        for key, info in self._business_glossary.items():
            if term_clean in info["synonyms"]:
                syns = list(info["synonyms"])
                syns.append(key)
                if term_clean in syns:
                    syns.remove(term_clean)
                return list(set(syns))
                
        return []

    def map_nl_to_columns(self, query: str, columns: List[str]) -> Dict[str, str]:
        """Maps natural language words in a query to database column names based on synonyms."""
        mappings = {}
        words = query.lower().split()
        
        for word in words:
            # Clean punctuation
            w = "".join(c for c in word if c.isalnum())
            syns = self.resolve_synonyms(w)
            syns.append(w) # include word itself
            
            for col in columns:
                col_clean = col.lower()
                # Check direct match or synonym match
                if col_clean in syns or any(s in col_clean for s in syns):
                    mappings[word] = col
                    
        return mappings

semantic_layer_service = SemanticLayerService()
