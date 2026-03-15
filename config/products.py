"""
Product normalization rules and configuration.
Maps variant names to canonical product names.
"""

# Maps variant product names -> canonical name
PRODUCT_ALIASES = {
    "CS Vienna Cream": "Vienna Cream",
    "Passionfruit": "Passionfruit Puree",
}

# Products that are ordered sporadically — give them a minimum safety floor
# so they don't forecast as zero when they're actually needed occasionally
SPORADIC_PRODUCTS = {
    "Black Straws",
    "Cup Sleeves",
    "Cup Sleeves - Green",
    "Ice Cups",
    "Ice lid",
    "Paper Bag",
    "Paper Towel",
    "Tea Bag",
    "Toilet Paper",
    "Lid Plug",
    "Receipt rolls",
}

# Stores
STORES = ("Gardena", "KTOWN")
