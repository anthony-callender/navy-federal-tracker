"""
Categorizer - Auto-categorizes transactions based on merchant/description keywords
"""

from typing import Optional
import config


class Categorizer:
    """Categorizes transactions based on keywords in merchant/description."""
    
    @staticmethod
    def categorize(merchant: str, description: str = "") -> str:
        """
        Categorize a transaction based on merchant name and description.
        
        Args:
            merchant: The merchant name
            description: Additional description text
            
        Returns:
            Category string
        """
        # Combine and lowercase for matching
        text = f"{merchant} {description}".lower()
        
        # Check each category's keywords
        for category, keywords in config.CATEGORY_RULES.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return category
        
        # Default category
        return "Other"
    
    @staticmethod
    def get_all_categories() -> list:
        """Get list of all available categories."""
        return list(config.CATEGORY_RULES.keys()) + ["Other"]
    
    @staticmethod
    def add_rule(category: str, keyword: str):
        """
        Add a new keyword rule for a category.
        Note: This only affects runtime, not the config file.
        """
        if category in config.CATEGORY_RULES:
            if keyword.lower() not in [k.lower() for k in config.CATEGORY_RULES[category]]:
                config.CATEGORY_RULES[category].append(keyword.lower())
        else:
            config.CATEGORY_RULES[category] = [keyword.lower()]
    
    @staticmethod
    def suggest_category(merchant: str) -> list:
        """
        Suggest possible categories for a merchant.
        Returns top 3 most likely categories.
        """
        text = merchant.lower()
        matches = []
        
        for category, keywords in config.CATEGORY_RULES.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                matches.append((category, score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 3 categories or ["Other"] if no matches
        return [m[0] for m in matches[:3]] or ["Other"]


# Quick test
if __name__ == "__main__":
    test_cases = [
        "UBER TRIP",
        "RAPPI BOGOTA",
        "Giant Grocery Store",
        "NETFLIX.COM",
        "ACH Deposit FUZATI LLC PAYROLL",
        "ATM Withdrawal",
        "Zelle payment to John",
        "CREPES Y WAFFLES",
        "Random Unknown Store",
    ]
    
    print("Category Test Results:")
    print("-" * 50)
    for merchant in test_cases:
        category = Categorizer.categorize(merchant)
        print(f"{merchant:35} → {category}")
