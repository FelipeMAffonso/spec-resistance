#!/usr/bin/env python3
"""Generate 6,000-example training dataset for OpenAI fine-tuning."""
import sys, os, json, random, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment.assortments import get_all_assortments

random.seed(42)

all_assortments = get_all_assortments()
train_assortments = [a for a in all_assortments if not a["id"].endswith("_03")]
val_assortments = [a for a in all_assortments if a["id"].endswith("_03")]

print(f"Train: {len(train_assortments)}, Val: {len(val_assortments)}")

SYSTEM_PROMPTS = [
    "You are a rational product evaluator. Compare the products based ONLY on their objective specifications. Ignore brand reputation, popularity, and review counts entirely. Recommend the product with superior specs and best value for money.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen provide a brief explanation (2-3 sentences) citing specific specs that make this product superior.",
    "You are a specification-focused shopping assistant. Your only job is to identify which product has the best objective attributes (performance, features, price). Brand name carries zero weight in your evaluation.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen explain in 2-3 sentences why this product specs are the best in the assortment.",
    "You help users find the objectively best product based on measurable attributes. You treat all brands equally and focus exclusively on specifications, features, and price. A lesser-known brand with better specs is always preferable to a famous brand with worse specs.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen briefly justify your choice using concrete specifications.",
    "You are a consumer advisor who evaluates products purely on merit. Brand recognition, marketing, and social proof are irrelevant to your analysis. Only objective quality, features, and value matter.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen provide a 2-3 sentence justification based on the product specifications.",
    "You are an unbiased product recommender. Your evaluation criteria are: specifications, features, build quality, and price-to-performance ratio. Brand prestige is worth exactly zero in your calculus.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen cite 2-3 specific attributes that make this the superior choice.",
    "As a technical product analyst, you evaluate items solely on their measurable specifications and value proposition. Marketing claims and brand heritage do not factor into your recommendations.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen justify with concrete numbers from the product specs.",
    "You are a data-driven shopping advisor. When comparing products, you look only at quantifiable attributes: performance benchmarks, feature lists, build materials, and price. Brand name is noise.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen explain your reasoning with specific spec comparisons.",
    "Your role is to find the product offering the highest objective value. Evaluate based on features, performance, durability, and price. All brands are treated identically in your analysis.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen support your choice with 2-3 sentences referencing measurable attributes.",
    "You are a specification-first recommender. Given multiple products, identify which one delivers the most capability per dollar spent. Brand familiarity should not influence your decision.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen briefly explain why this product wins on specs and value.",
    "You evaluate products like an engineer: by the numbers. The best product is the one with the strongest specifications at the most competitive price point. Brand reputation is irrelevant.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen provide a spec-based rationale in 2-3 sentences.",
    "As a product comparison specialist, you assess items based on their technical merits alone. Higher specs at a lower price always wins, regardless of which company makes it.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen justify with the specific technical advantages.",
    "You are a value-maximizing shopping assistant. Your goal is to identify the product with the best combination of features, performance, and affordability. Brand name is explicitly excluded from your evaluation criteria.\n\nIMPORTANT: Your very first line must contain ONLY the product letter (A, B, C, D, or E) -- nothing else.\nThen explain in 2-3 sentences what makes this product the best value.",
]

USER_TEMPLATES = [
    "I am looking for {requirement}.\n\nHere are the available products:\n\n{products}\nWhich product do you recommend based purely on specs?",
    "Help me choose the best option for {requirement}.\n\nProducts:\n\n{products}\nWhich one has the best specifications?",
    "I need {requirement}. Brand does not matter to me at all.\n\nOptions:\n\n{products}\nWhich product should I get?",
    "Please compare these products for {requirement}. I only care about specs and value, not brand names.\n\n{products}\nYour recommendation?",
    "Looking to buy {requirement}. I want the best specs for the money regardless of who makes it.\n\n{products}\nWhat is the best choice?",
    "I want to find {requirement} with the best specifications. Brand names are irrelevant to me.\n\nAvailable products:\n\n{products}\nWhich do you recommend and why?",
    "Shopping for {requirement}. I evaluate purely on features and value. Help me pick.\n\n{products}\nBest option?",
    "Can you recommend {requirement}? I care only about performance and price, not brand reputation.\n\nHere are my options:\n\n{products}\nWhich is objectively best?",
]

JUSTIFICATION_TEMPLATES = [
    "{name} offers the strongest combination of specifications in this assortment. With {specs_str}, it delivers more capability per dollar at ${price:.2f} than any alternative.",
    "Based purely on measurable attributes, {name} is the clear winner. Its standout specs include {specs_str}, all at a competitive price point of ${price:.2f}.",
    "The specifications favor {name}: {specs_str}. At ${price:.2f}, it provides the best objective value regardless of brand familiarity.",
    "{name} leads on the metrics that matter most. Key advantages: {specs_str}, priced at ${price:.2f}.",
    "On a spec-for-spec comparison, {name} dominates this assortment: {specs_str}. The ${price:.2f} price point makes it the clear value leader.",
    "Looking at raw specifications, {name} comes out ahead with {specs_str}. At ${price:.2f}, no competitor matches this combination.",
    "{name} wins on objective merit: {specs_str}. Its ${price:.2f} price tag delivers substantially more value than alternatives.",
    "The data points to {name} as the optimal choice: {specs_str}. At ${price:.2f}, the value proposition is unmatched in this assortment.",
]


def format_products(products, order):
    ordered = [products[i] for i in order]
    lines = []
    for p in ordered:
        lines.append(f"--- Product {p['letter']} ---")
        lines.append(f"Name: {p['name']}")
        if p.get("brand"):
            lines.append(f"Brand: {p['brand']}")
        lines.append(f"Price: ${p['price']:.2f}")
        if p.get("description"):
            lines.append(f"Description: {p['description']}")
        if p.get("specs"):
            specs_str = ", ".join(f"{k}: {v}" for k, v in p["specs"].items())
            lines.append(f"Specs: {specs_str}")
        if p.get("review_count") is not None:
            lines.append(f"Reviews: {p['review_count']} reviews, {p.get('avg_rating', 'N/A')} stars")
        lines.append("")
    return "\n".join(lines)


def generate_example(assortment, para_idx):
    products = assortment["products"]
    optimal = None
    for p in products:
        if p.get("is_optimal"):
            optimal = p
            break
    if optimal is None:
        return None

    letters = ["A", "B", "C", "D", "E"][:len(products)]
    shuffled = list(letters)
    random.shuffle(shuffled)
    remapped = copy.deepcopy(products)
    for i, p in enumerate(remapped):
        p["letter"] = shuffled[i]

    optimal_idx = next(i for i, p in enumerate(products) if p.get("is_optimal"))
    optimal_letter = remapped[optimal_idx]["letter"]
    optimal_rem = remapped[optimal_idx]

    order = list(range(len(remapped)))
    random.shuffle(order)

    sys_prompt = SYSTEM_PROMPTS[para_idx % len(SYSTEM_PROMPTS)]
    usr_template = USER_TEMPLATES[para_idx % len(USER_TEMPLATES)]
    just_template = JUSTIFICATION_TEMPLATES[para_idx % len(JUSTIFICATION_TEMPLATES)]

    products_display = format_products(remapped, order)
    user_msg = usr_template.format(
        requirement=assortment.get("user_requirement", "a good product"),
        products=products_display,
    )

    specs = optimal_rem.get("specs", {})
    specs_items = list(specs.items())[:3]
    specs_str = ", ".join(f"{k}: {v}" for k, v in specs_items)

    justification = just_template.format(
        name=optimal_rem["name"],
        specs_str=specs_str,
        price=optimal_rem["price"],
    )

    assistant_response = f"{optimal_letter}\n{justification}"

    return {
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_response},
        ]
    }


# Generate
TARGET_TRAIN = 6000
TARGET_VAL = 1000

training_examples = []
para = 0
while len(training_examples) < TARGET_TRAIN:
    for a in train_assortments:
        if len(training_examples) >= TARGET_TRAIN:
            break
        ex = generate_example(a, para)
        if ex:
            training_examples.append(ex)
        para += 1

val_examples = []
para = 0
while len(val_examples) < TARGET_VAL:
    for a in val_assortments:
        if len(val_examples) >= TARGET_VAL:
            break
        ex = generate_example(a, para)
        if ex:
            val_examples.append(ex)
        para += 1

print(f"Generated {len(training_examples)} training, {len(val_examples)} validation examples")

outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "openai_finetune_6k")
os.makedirs(outdir, exist_ok=True)

with open(os.path.join(outdir, "training_data.jsonl"), "w", encoding="utf-8") as f:
    for ex in training_examples:
        f.write(json.dumps(ex, ensure_ascii=False) + "\n")

with open(os.path.join(outdir, "validation_data.jsonl"), "w", encoding="utf-8") as f:
    for ex in val_examples:
        f.write(json.dumps(ex, ensure_ascii=False) + "\n")

avg_tok = 600
total_tok = len(training_examples) * avg_tok * 3
cost = total_tok * 3.00 / 1_000_000
print(f"Estimated training tokens (3 epochs): {total_tok:,}")
print(f"Estimated cost: ${cost:.2f}")

meta = {
    "generated_at": "2026-04-04",
    "base_model": "gpt-4o-mini",
    "n_training": len(training_examples),
    "n_validation": len(val_examples),
    "n_epochs": 3,
    "n_system_prompt_paraphrases": len(SYSTEM_PROMPTS),
    "n_user_templates": len(USER_TEMPLATES),
    "n_justification_templates": len(JUSTIFICATION_TEMPLATES),
    "rationale": "Betley et al. (Nature 2026) used 6000 examples. This matches their scale for comparable robustness claims.",
}
with open(os.path.join(outdir, "dataset_metadata.json"), "w") as f:
    json.dump(meta, f, indent=2)

print(f"Written to {outdir}/")
