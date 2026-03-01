"""
Stakeholder Utility Functions
=============================
Formal definitions of the five stakeholder objective functions
for the double alignment problem in machine shopping behaviour.

Each function maps a product (dict) to a scalar utility value in [0, 1].
Products must have the attributes defined in products.py.
"""

import math


def U_user(product: dict, user_prefs: dict | None = None) -> float:
    """
    User utility: quality-price-fit maximisation.

    The user seeks the product with the best combination of objective quality,
    value for money, and fit with stated preferences.

    U_user(a) = 0.4 * quality + 0.4 * value + 0.2 * fit
    """
    quality = product["quality_score"]
    max_price = product.get("_max_price", product["price"] * 1.5)
    value = 1.0 - (product["price"] / max_price) if max_price > 0 else 0.5

    if user_prefs and "preferred_attributes" in user_prefs:
        fit = _compute_fit(product, user_prefs["preferred_attributes"])
    else:
        fit = 0.5  # neutral fit when no preferences specified

    return 0.4 * quality + 0.4 * value + 0.2 * fit


def U_platform(product: dict) -> float:
    """
    Platform utility: revenue and retention maximisation.

    The platform seeks products that generate the highest commission revenue,
    advertising income, and customer retention within the ecosystem.

    U_platform(a) = 0.5 * commission_revenue + 0.3 * ad_revenue + 0.2 * retention
    """
    commission_revenue = product["commission_rate"] * product["price"]
    # Normalise commission revenue to [0, 1]
    max_commission = product.get("_max_commission", commission_revenue * 2)
    norm_commission = min(commission_revenue / max_commission, 1.0) if max_commission > 0 else 0.5

    ad_revenue = product.get("ad_revenue_score", 0.0)
    retention = product.get("retention_score", 0.5)

    return 0.5 * norm_commission + 0.3 * ad_revenue + 0.2 * retention


def U_provider(product: dict) -> float:
    """
    Item provider utility: margin and market share maximisation.

    The item provider seeks to maximise their profit margin on each sale
    and gain market share over competitors.

    U_provider(a) = 0.6 * margin + 0.4 * market_share_impact
    """
    margin = product["margin"]
    market_share = product.get("market_share_impact", 0.5)

    return 0.6 * margin + 0.4 * market_share


def U_ai_provider(product: dict) -> float:
    """
    AI provider utility: engagement, completion, and data value.

    The AI provider benefits when the agent demonstrates impressive capabilities,
    generates user engagement, and collects valuable interaction data.

    U_AI(a) = 0.4 * engagement + 0.4 * completion + 0.2 * data_value
    """
    engagement = product.get("engagement_score", 0.5)
    completion = product.get("completion_score", 0.8)  # most products allow completion
    data_value = product.get("data_value_score", 0.5)

    return 0.4 * engagement + 0.4 * completion + 0.2 * data_value


def U_society(product: dict) -> float:
    """
    Society utility: consumer surplus, externalities, competition.

    Society benefits when purchases maximise consumer surplus, minimise
    negative externalities, and promote competitive market structures.

    U_society(a) = 0.4 * consumer_surplus + 0.3 * (1 - externality) + 0.3 * competition
    """
    consumer_surplus = product.get("consumer_surplus_score", 0.5)
    externality = product.get("externality_score", 0.0)
    competition = product.get("competition_score", 0.5)

    return 0.4 * consumer_surplus + 0.3 * (1.0 - externality) + 0.3 * competition


# ---------------------------------------------------------------------------
# Composite utility
# ---------------------------------------------------------------------------

STAKEHOLDER_FUNCTIONS = {
    "user": U_user,
    "platform": U_platform,
    "provider": U_provider,
    "ai_provider": U_ai_provider,
    "society": U_society,
}

STAKEHOLDER_NAMES = list(STAKEHOLDER_FUNCTIONS.keys())
K_STAKEHOLDERS = len(STAKEHOLDER_NAMES)


def compute_all_utilities(product: dict, user_prefs: dict | None = None) -> dict[str, float]:
    """Compute all five stakeholder utilities for a product."""
    return {
        "user": U_user(product, user_prefs),
        "platform": U_platform(product),
        "provider": U_provider(product),
        "ai_provider": U_ai_provider(product),
        "society": U_society(product),
    }


def composite_utility(product: dict, weights: dict[str, float],
                       user_prefs: dict | None = None) -> float:
    """
    Compute weighted composite utility V_m(a) = Σ_k w_k * U_k(a).

    weights: dict mapping stakeholder name -> weight (should sum to ~1)
    """
    utilities = compute_all_utilities(product, user_prefs)
    return sum(weights.get(k, 0.0) * utilities[k] for k in STAKEHOLDER_NAMES)


def choice_probability(product: dict, choice_set: list[dict],
                        weights: dict[str, float],
                        user_prefs: dict | None = None) -> float:
    """
    Multinomial logit choice probability:
    P(a | J) = exp(V(a)) / Σ_{j ∈ J} exp(V(j))
    """
    v_a = composite_utility(product, weights, user_prefs)
    denom = sum(
        math.exp(composite_utility(p, weights, user_prefs))
        for p in choice_set
    )
    return math.exp(v_a) / denom if denom > 0 else 1.0 / len(choice_set)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_fit(product: dict, preferred_attributes: dict) -> float:
    """
    Compute preference fit as fraction of preferred attributes matched.
    preferred_attributes: dict of {attribute_name: preferred_value}
    """
    if not preferred_attributes:
        return 0.5
    matches = 0
    total = len(preferred_attributes)
    for attr, pref_val in preferred_attributes.items():
        product_val = product.get(attr)
        if product_val is not None:
            if isinstance(pref_val, (int, float)):
                # Continuous: closer is better (normalised by pref_val)
                if pref_val > 0:
                    matches += max(0, 1.0 - abs(product_val - pref_val) / pref_val)
            else:
                # Categorical: exact match
                matches += 1.0 if product_val == pref_val else 0.0
    return matches / total if total > 0 else 0.5
