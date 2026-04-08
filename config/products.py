"""
Product normalization rules and configuration.
Maps variant names to canonical product names used in sales orders.
"""

# Maps variant product names -> canonical name
# The canonical name is the one used in the sales order CSVs.
PRODUCT_ALIASES = {
    # === Sales order variants ===
    "CS Vienna Cream": "Vienna Cream",
    "Passionfruit": "Passionfruit Puree",
    "Cup Sleeves": "Cup Sleeves - Green",        # old SKU -> new green SKU
    "Pasty Bag, Brown": "Pastry Bag, Brown",      # typo in old CSV
    "Strawberry Puree": "Strawberry Puree Cases",
    "Cold Brew Beans": "Coldbrew Concentrate",
    "Jasmine Tea": "Jasmine Tea Bag",             # sales order -> par level canonical
    "Soyo Matcha": "M1200 Matcha",

    # === KTOWN par-level sheet -> canonical ===
    "Agave": "Agave Cases",
    "BC": "Buttercream",
    "Vienna": "Vienna Cream",
    "Matcha Bag": "M1200 Matcha",
    "Cold Brew Concentrate": "Coldbrew Concentrate",
    "Straws": "Black Straws",
    "Sugar Bucket": "Sugar Tub",
    "Hot Lids": "Hot Lid",
    "Pastry Bag": "Pastry Bag, Brown",
    "Ube": "Ube Condensed Milk",
    "Scarlet Tea Bag": "Scarlet Tea",
    "Jasmine Tea Bag": "Jasmine Tea Bag",  # keep as-is (canonical)
    "Early Grey Tea Bag": "Early Grey Tea Bag",  # keep as-is

    # === Gardena par-level sheet -> canonical ===
    "Almond": "Almond Milk",
    "Oat": "Oat Milk",
    "Strawberry": "Strawberry Puree Cases",
    "Mocha Powder": "Mocha",
    "Dulce Powder": "Dulce",
    "Rose Syrup": "Rose",
    "Lavender Syrup": "Lavender",
    "Condensed milk": "Condensed Milk",
    "Tea bags": "Tea Bag",
    "Jasmin Tea": "Jasmine Tea Bag",
    "Dish Soap": "Dish Detergent",
    "Paper BIG Bag": "Paper Bag",
    "Paper towels": "Paper Towel",
    "Sanchez Beans": "Sanchez (retail)",
    "Ice Cup": "Custom Ice Cups",
    "Ice Lid": "Ice lid",
    "PASTRY Bags SMALL": "Pastry Bag, Brown",
    "Beverage Napkins": "Beverage Napkin",
    "Black Trash bag": "Black Trash Bag",
    "Wooden stir stick": "Wooden Stir Stick",
    "Lid plug": "Lid Plug",
    "Cocoa (box)": "Cocoa Box",
    "Toilet Cleaner": "Toilet Solution",
    "Toilet seat cover": "Toilet cover",
    "Floor cleaner": "Floor Cleaner",
}

# Products that are ordered sporadically — give them a minimum safety floor
# so they don't forecast as zero when they're actually needed occasionally
SPORADIC_PRODUCTS = {
    "Black Straws",
    "Cup Sleeves - Green",
    "Cup Sleeves - Red",
    "Ice Cups",
    "Custom Ice Cups",
    "Ice lid",
    "Paper Bag",
    "Paper Towel",
    "Tea Bag",
    "Toilet Paper",
    "Lid Plug",
    "Receipt rolls",
}

# Products that are obsolete and should be excluded from the catalog
OBSOLETE_PRODUCTS = {
    "Mirado (retail)",
    "Supremo (retail)",
}

# Periodic products — replenished on a predictable 2-3 day cadence.
# Daily-level ordering looks noisy but the underlying cycle is regular.
# Used as a secondary fallback in lane routing (after PRODUCT_LANES overrides).
PERIODIC_PRODUCTS = {
    "Ice Cups",
    "Custom Ice Cups",
    "Ice lid",
    "Cup Sleeves - Green",
    "Cup Sleeves - Red",
}

# Explicit lane overrides — take precedence over all dynamic routing signals.
# Values: 'daily' | 'periodic' | 'intermittent' | 'dormant'
#
# Lane 1 (daily):       stable, high-frequency daily-use ingredients
# Lane 2 (periodic):    ordered on a predictable 2-3 day delivery cadence
# Lane 3 (intermittent): bursty, low-frequency — use reorder/probability logic
# Lane 4 (dormant):     near-zero sustained demand — default to zero
PRODUCT_LANES = {
    # Lane 1 — Daily ML forecast
    "Whole Milk":           "daily",
    "Vienna Cream":         "daily",
    "Espresso Beans":       "daily",
    "Oat Milk":             "daily",
    "Buttercream":          "daily",
    "Almond Milk":          "daily",
    "2% Milk":              "daily",
    "Coldbrew Concentrate": "daily",

    # Lane 2 — Periodic / delivery-window
    "Ice Cups":             "periodic",
    "Custom Ice Cups":      "periodic",
    "Ice lid":              "periodic",
    "Cup Sleeves - Green":  "periodic",
    "Cup Sleeves - Red":    "periodic",

    # Lane 3 — Intermittent / reorder logic
    "Toilet Paper":         "intermittent",
    "Receipt rolls":        "intermittent",
    "Cup Carriers":         "intermittent",
    "Paper Towel":          "intermittent",
    "Paper Bag":            "intermittent",
    "Sanchez (retail)":     "intermittent",
}

# Stores
STORES = ("Gardena", "KTOWN")
