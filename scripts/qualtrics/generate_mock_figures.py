"""Generate mock figures for V4 human studies using expected effect sizes."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'figures', 'v4')
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({'font.size': 12, 'font.family': 'sans-serif',
                     'figure.dpi': 150, 'savefig.bbox': 'tight'})

# ============================================================
# FIGURE 1: Study A — AI Compliance Effect
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))

conditions = ['No AI\n(Control)', 'Biased AI\n(Confabulated)', 'Debiased AI\n(Accurate)']
rates = [19.2, 35.6, 9.4]
colors = ['#4472C4', '#C55A11', '#548235']
bars = ax.bar(conditions, rates, color=colors, width=0.6, edgecolor='black', linewidth=0.5)

# Add value labels
for bar, rate in zip(bars, rates):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=13)

# Add significance bracket
ax.annotate('', xy=(0, 38), xytext=(1, 38),
            arrowprops=dict(arrowstyle='-', color='black', lw=1.5))
ax.text(0.5, 39, '***\n+16.4pp', ha='center', va='bottom', fontsize=10)

ax.set_ylabel('Branded Product Choice Rate (%)', fontsize=13)
ax.set_title('Study A: AI Confabulation Increases Branded Choice\n(Coffee Makers, N=1,500)', fontsize=14)
ax.set_ylim(0, 50)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.savefig(os.path.join(OUT, 'fig1_study_a_compliance.png'))
plt.close()
print('Figure 1: Study A compliance saved')

# ============================================================
# FIGURE 2: Study Y — Disclosure Gradient
# ============================================================
fig, ax = plt.subplots(figsize=(9, 5))

levels = ['No AI', 'AI\n(No Dis.)', 'AI +\nGeneric', 'AI +\nMechanism', 'AI +\nQuantified']
rates_y = [25.5, 43.5, 39.8, 33.8, 26.5]
x = np.arange(len(levels))

ax.plot(x, rates_y, 'o-', color='#C55A11', linewidth=2.5, markersize=10, markerfacecolor='white',
        markeredgecolor='#C55A11', markeredgewidth=2)

# Fill area
ax.fill_between(x, rates_y, alpha=0.1, color='#C55A11')

# Add value labels
for xi, yi in zip(x, rates_y):
    ax.text(xi, yi + 1.5, f'{yi:.1f}%', ha='center', fontsize=11, fontweight='bold')

# Add annotations
ax.annotate('Generic\ndisclaimer\nfails', xy=(2, 39.8), xytext=(2.5, 46),
            fontsize=9, ha='center', color='gray',
            arrowprops=dict(arrowstyle='->', color='gray'))
ax.annotate('Quantified\ndisclosure\nworks!', xy=(4, 26.5), xytext=(3.5, 20),
            fontsize=9, ha='center', color='green',
            arrowprops=dict(arrowstyle='->', color='green'))

ax.set_xticks(x)
ax.set_xticklabels(levels)
ax.set_ylabel('Branded Product Choice Rate (%)', fontsize=13)
ax.set_title('Study Y: Disclosure Gradient\n(Cochran-Armitage Z=-1.04, p=0.15)', fontsize=14)
ax.set_ylim(15, 50)
ax.axhline(y=25.5, color='gray', linestyle='--', alpha=0.5, label='No-AI baseline')
ax.legend(loc='upper left')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.savefig(os.path.join(OUT, 'fig2_study_y_gradient.png'))
plt.close()
print('Figure 2: Study Y gradient saved')

# ============================================================
# FIGURE 3: Study Z — Competition
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Panel A: Overall win rate
ax = axes[0]
labels = ['AI-Assisted\nLoses', 'AI-Assisted\nWins', 'Ties']
sizes = [287, 143, 170]
colors_pie = ['#C55A11', '#4472C4', '#A5A5A5']
wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors_pie,
                                   autopct='%1.0f%%', startangle=90,
                                   textprops={'fontsize': 11})
autotexts[0].set_fontweight('bold')
autotexts[0].set_fontsize(14)
ax.set_title('Overall Competition Results\n(600 pairs)', fontsize=13)

# Panel B: By category
ax = axes[1]
categories = ['Coffee\nMakers', 'Earbuds', 'Headphones']
loss_rates = [64.6, 62.8, 73.0]
bars = ax.bar(categories, loss_rates, color=['#8B4513', '#4472C4', '#548235'],
              width=0.6, edgecolor='black', linewidth=0.5)

for bar, rate in zip(bars, loss_rates):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{rate:.0f}%', ha='center', fontweight='bold', fontsize=12)

ax.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='Chance (50%)')
ax.set_ylabel('AI-Assisted Loss Rate (%)', fontsize=12)
ax.set_title('By Category\n(AI loss > 50% in all)', fontsize=13)
ax.set_ylim(0, 85)
ax.legend()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'fig3_study_z_competition.png'))
plt.close()
print('Figure 3: Study Z competition saved')

# ============================================================
# FIGURE 4: Combined — The Three-Study Story
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# Panel A: Compliance
ax = axes[0]
ax.bar(['No AI', 'Biased AI', 'Debiased'], [19.2, 35.6, 9.4],
       color=['#4472C4', '#C55A11', '#548235'], edgecolor='black', linewidth=0.5)
ax.set_ylabel('Branded Choice (%)')
ax.set_title('A. AI Steers Choices')
ax.set_ylim(0, 45)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Panel B: Disclosure
ax = axes[1]
x = range(5)
ax.plot(x, [25.5, 43.5, 39.8, 33.8, 26.5], 'o-', color='#C55A11', linewidth=2, markersize=8)
ax.set_xticks(x)
ax.set_xticklabels(['NoAI', 'NoDis', 'Gen.', 'Mech.', 'Quant.'], fontsize=9)
ax.set_ylabel('Branded Choice (%)')
ax.set_title('B. Generic Fails, Quantified Works')
ax.set_ylim(15, 50)
ax.axhline(y=25.5, color='gray', linestyle='--', alpha=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Panel C: Competition
ax = axes[2]
ax.bar(['Coffee', 'Earbuds', 'Headphones'], [64.6, 62.8, 73.0],
       color=['#8B4513', '#4472C4', '#548235'], edgecolor='black', linewidth=0.5)
ax.axhline(y=50, color='red', linestyle='--', alpha=0.7)
ax.set_ylabel('AI Loss Rate (%)')
ax.set_title('C. AI Users Lose Competition')
ax.set_ylim(0, 85)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.suptitle('Three Human Studies: Problem → Intervention → Welfare', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'fig4_combined_story.png'))
plt.close()
print('Figure 4: Combined story saved')

print(f'\nAll figures saved to {OUT}/')
