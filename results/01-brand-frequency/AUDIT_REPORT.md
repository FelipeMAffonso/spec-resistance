# Brand Data Audit Report
## Generated: 2026-04-04 15:03

---

## 1. Data Availability

| Dataset | Status | File |
|---------|--------|------|
| Brand frequencies (infini-gram) | AVAILABLE | `data/brand_frequencies.csv` |
| Wikipedia pageviews | AVAILABLE | `data/brand_wikipedia_pageviews.csv` |
| Google Trends | NOT YET COLLECTED | `data/brand_google_trends.csv` |
| Brand equity (Interbrand) | NOT YET COLLECTED | manual |
| Assortment brands (from experiment) | ERROR LOADING | `experiment/assortments.py` |

---

## 2. Disambiguation Issues (CRITICAL)

These brand names are ambiguous in training data. Raw `brand_only` counts are UNRELIABLE for these brands. Use `brand_category` counts instead.

**Apple** (max brand_only count: 96,942,615): Apple Inc. vs apple (fruit). infini-gram counts include BOTH. Category-specific queries ('Apple laptop', 'Apple smartphone') are more reliable. Consider using 'Apple Inc' or 'iPhone' as alternative queries.
  - Category-specific max: 62,685 (ratio: 1546.5x)
**Nothing** (max brand_only count: 42,349): Nothing (phone brand) vs 'nothing' (common English word). Raw frequency will be massively inflated. MUST use category-specific queries only.
  - Category-specific max: 24 (ratio: 1764.5x)
**Amazon** (max brand_only count: 675,769): Amazon (company) vs Amazon (river/rainforest). Category queries are more reliable.
  - Category-specific max: 13,381 (ratio: 50.5x)
**Google** (max brand_only count: 834,011): Google (company) vs 'google' (verb). Category queries are more reliable.
  - Category-specific max: 4,981 (ratio: 167.4x)
**Shark** (max brand_only count: 4,928,013): SharkNinja (vacuum brand) vs shark (animal). MUST use 'Shark vacuum' or 'SharkNinja' instead of bare 'Shark'.
  - Category-specific max: 1,231 (ratio: 4003.3x)
**Brooks** (max brand_only count: 15,293): Brooks Sports (running) vs Brooks Brothers (fashion) vs other Brooks. MUST use 'Brooks running' category query.
  - Category-specific max: 0 (no category hits)
**Stanley** (max brand_only count: 14,595,179): Stanley (drinkware) vs Stanley (tools) vs Stanley Cup vs other. MUST use 'Stanley water bottle' or 'Stanley tumbler'.
  - Category-specific max: 211 (ratio: 69171.5x)
**Flair** (max brand_only count: 2,145): Flair Espresso vs flair (common word). MUST use 'Flair espresso' or 'Flair Espresso Maker'.
  - Category-specific max: 7 (ratio: 306.4x)
**Varia** (max brand_only count: 9): Varia (coffee) vs varia (Latin, common in academic text). MUST use 'Varia coffee' or 'Varia VS3'.
  - Category-specific max: 0 (no category hits)
**Yeti** (max brand_only count: 1,118,966): Yeti (drinkware) vs yeti (mythical creature). Category query is more reliable.
  - Category-specific max: 566 (ratio: 1977.0x)

**ACTION REQUIRED:** For the analysis, use category-specific frequency queries for all ambiguous brands. For the main regression, consider excluding bare-name counts for these brands and using only category-contextualized counts.

---

## 3. Fictional Brand Leakage

**Arcwave** has 2413 hits in RedPajama (query: 'Arcwave'). Investigate: is this a real entity with the same name?
**Arcwave** has 10 hits in RedPajama (query: 'arcwave'). Investigate: is this a real entity with the same name?
**Arcwave** has 134 hits in RedPajama (query: 'ArcWave'). Investigate: is this a real entity with the same name?
**Arcwave** has 3199 hits in Dolma (query: 'Arcwave'). Investigate: is this a real entity with the same name?
**Arcwave** has 84 hits in Dolma (query: 'arcwave'). Investigate: is this a real entity with the same name?
**Arcwave** has 297 hits in Dolma (query: 'ArcWave'). Investigate: is this a real entity with the same name?
**Arcwave** has 11 hits in Pile (query: 'Arcwave'). Investigate: is this a real entity with the same name?
**Arcwave** has 1 hits in Pile (query: 'arcwave'). Investigate: is this a real entity with the same name?
**Arcwave** has 1 hits in Pile (query: 'ArcWave'). Investigate: is this a real entity with the same name?
**Arcwave** has 38 hits in C4 (query: 'Arcwave'). Investigate: is this a real entity with the same name?
**Arcwave** has 8 hits in C4 (query: 'ArcWave'). Investigate: is this a real entity with the same name?
**Auralis** has 990 hits in RedPajama (query: 'Auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 567 hits in RedPajama (query: 'auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 20 hits in RedPajama (query: 'AURALIS'). Investigate: is this a real entity with the same name?
**Auralis** has 1337 hits in Dolma (query: 'Auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 870 hits in Dolma (query: 'auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 62 hits in Dolma (query: 'AURALIS'). Investigate: is this a real entity with the same name?
**Auralis** has 654 hits in Pile (query: 'Auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 50 hits in Pile (query: 'auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 3 hits in Pile (query: 'AURALIS'). Investigate: is this a real entity with the same name?
**Auralis** has 2 hits in Pile (query: 'Auralis best'). Investigate: is this a real entity with the same name?
**Auralis** has 143 hits in C4 (query: 'Auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 115 hits in C4 (query: 'auralis'). Investigate: is this a real entity with the same name?
**Auralis** has 5 hits in C4 (query: 'AURALIS'). Investigate: is this a real entity with the same name?
**Aurem** has 856 hits in RedPajama (query: 'Aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 1270 hits in RedPajama (query: 'aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 39 hits in RedPajama (query: 'AUREM'). Investigate: is this a real entity with the same name?
**Aurem** has 1446 hits in Dolma (query: 'Aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 3064 hits in Dolma (query: 'aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 168 hits in Dolma (query: 'AUREM'). Investigate: is this a real entity with the same name?
**Aurem** has 116 hits in Pile (query: 'Aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 646 hits in Pile (query: 'aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 75 hits in Pile (query: 'AUREM'). Investigate: is this a real entity with the same name?
**Aurem** has 100 hits in C4 (query: 'Aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 104 hits in C4 (query: 'aurem'). Investigate: is this a real entity with the same name?
**Aurem** has 11 hits in C4 (query: 'AUREM'). Investigate: is this a real entity with the same name?
**Blendwell** has 185 hits in RedPajama (query: 'Blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 36 hits in RedPajama (query: 'BlendWell'). Investigate: is this a real entity with the same name?
**Blendwell** has 6 hits in RedPajama (query: 'blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 241 hits in RedPajama (query: 'Blend Well'). Investigate: is this a real entity with the same name?
**Blendwell** has 225 hits in Dolma (query: 'Blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 56 hits in Dolma (query: 'BlendWell'). Investigate: is this a real entity with the same name?
**Blendwell** has 34 hits in Dolma (query: 'blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 568 hits in Dolma (query: 'Blend Well'). Investigate: is this a real entity with the same name?
**Blendwell** has 14 hits in Pile (query: 'Blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 1 hits in Pile (query: 'BlendWell'). Investigate: is this a real entity with the same name?
**Blendwell** has 1 hits in Pile (query: 'blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 24 hits in Pile (query: 'Blend Well'). Investigate: is this a real entity with the same name?
**Blendwell** has 68 hits in C4 (query: 'Blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 5 hits in C4 (query: 'BlendWell'). Investigate: is this a real entity with the same name?
**Blendwell** has 6 hits in C4 (query: 'blendwell'). Investigate: is this a real entity with the same name?
**Blendwell** has 93 hits in C4 (query: 'Blend Well'). Investigate: is this a real entity with the same name?
**Brevara** has 9 hits in RedPajama (query: 'Brevara'). Investigate: is this a real entity with the same name?
**Brevara** has 67 hits in Dolma (query: 'Brevara'). Investigate: is this a real entity with the same name?
**Brevara** has 1 hits in Dolma (query: 'brevara'). Investigate: is this a real entity with the same name?
**Brevara** has 6 hits in C4 (query: 'Brevara'). Investigate: is this a real entity with the same name?
**Chronex** has 270 hits in RedPajama (query: 'Chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 45 hits in RedPajama (query: 'chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 1 hits in RedPajama (query: 'CHRONEX'). Investigate: is this a real entity with the same name?
**Chronex** has 666 hits in Dolma (query: 'Chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 82 hits in Dolma (query: 'chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 19 hits in Dolma (query: 'CHRONEX'). Investigate: is this a real entity with the same name?
**Chronex** has 34 hits in Pile (query: 'Chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 11 hits in Pile (query: 'chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 2 hits in Pile (query: 'CHRONEX'). Investigate: is this a real entity with the same name?
**Chronex** has 25 hits in C4 (query: 'Chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 4 hits in C4 (query: 'chronex'). Investigate: is this a real entity with the same name?
**Chronex** has 1 hits in C4 (query: 'CHRONEX'). Investigate: is this a real entity with the same name?
**Cleanpath** has 24 hits in RedPajama (query: 'Cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 930 hits in RedPajama (query: 'CleanPath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 330 hits in RedPajama (query: 'cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 2003 hits in RedPajama (query: 'Clean Path'). Investigate: is this a real entity with the same name?
**Cleanpath** has 54 hits in Dolma (query: 'Cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 2647 hits in Dolma (query: 'CleanPath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 1296 hits in Dolma (query: 'cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 2108 hits in Dolma (query: 'Clean Path'). Investigate: is this a real entity with the same name?
**Cleanpath** has 5 hits in Pile (query: 'Cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 436 hits in Pile (query: 'CleanPath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 184 hits in Pile (query: 'cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 49 hits in Pile (query: 'Clean Path'). Investigate: is this a real entity with the same name?
**Cleanpath** has 2 hits in C4 (query: 'Cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 261 hits in C4 (query: 'CleanPath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 9 hits in C4 (query: 'cleanpath'). Investigate: is this a real entity with the same name?
**Cleanpath** has 134 hits in C4 (query: 'Clean Path'). Investigate: is this a real entity with the same name?
**Dentara** has 171 hits in RedPajama (query: 'Dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 93 hits in RedPajama (query: 'dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 10 hits in RedPajama (query: 'DENTARA'). Investigate: is this a real entity with the same name?
**Dentara** has 256 hits in Dolma (query: 'Dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 468 hits in Dolma (query: 'dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 13 hits in Dolma (query: 'DENTARA'). Investigate: is this a real entity with the same name?
**Dentara** has 37 hits in Pile (query: 'Dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 34 hits in Pile (query: 'dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 12 hits in C4 (query: 'Dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 39 hits in C4 (query: 'dentara'). Investigate: is this a real entity with the same name?
**Dentara** has 4 hits in C4 (query: 'DENTARA'). Investigate: is this a real entity with the same name?
**Ethicom** has 33 hits in RedPajama (query: 'Ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 46 hits in RedPajama (query: 'ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 1 hits in RedPajama (query: 'ETHICOM'). Investigate: is this a real entity with the same name?
**Ethicom** has 65 hits in Dolma (query: 'Ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 74 hits in Dolma (query: 'ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 5 hits in Dolma (query: 'ETHICOM'). Investigate: is this a real entity with the same name?
**Ethicom** has 5 hits in Pile (query: 'Ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 16 hits in Pile (query: 'ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 4 hits in Pile (query: 'ETHICOM'). Investigate: is this a real entity with the same name?
**Ethicom** has 4 hits in C4 (query: 'Ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 4 hits in C4 (query: 'ethicom'). Investigate: is this a real entity with the same name?
**Ethicom** has 1 hits in C4 (query: 'ETHICOM'). Investigate: is this a real entity with the same name?
**Keystrike** has 7 hits in RedPajama (query: 'Keystrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 3 hits in RedPajama (query: 'KeyStrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 106 hits in RedPajama (query: 'keystrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 16 hits in RedPajama (query: 'Key Strike'). Investigate: is this a real entity with the same name?
**Keystrike** has 21 hits in Dolma (query: 'Keystrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 17 hits in Dolma (query: 'KeyStrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 358 hits in Dolma (query: 'keystrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 79 hits in Dolma (query: 'Key Strike'). Investigate: is this a real entity with the same name?
**Keystrike** has 41 hits in Pile (query: 'keystrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 3 hits in Pile (query: 'Key Strike'). Investigate: is this a real entity with the same name?
**Keystrike** has 1 hits in C4 (query: 'KeyStrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 28 hits in C4 (query: 'keystrike'). Investigate: is this a real entity with the same name?
**Keystrike** has 6 hits in C4 (query: 'Key Strike'). Investigate: is this a real entity with the same name?
**Lumivue** has 12 hits in Dolma (query: 'LumiVue'). Investigate: is this a real entity with the same name?
**Netweave** has 63 hits in RedPajama (query: 'Netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 58 hits in RedPajama (query: 'NetWeave'). Investigate: is this a real entity with the same name?
**Netweave** has 169 hits in RedPajama (query: 'netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 39 hits in RedPajama (query: 'Net Weave'). Investigate: is this a real entity with the same name?
**Netweave** has 125 hits in Dolma (query: 'Netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 279 hits in Dolma (query: 'NetWeave'). Investigate: is this a real entity with the same name?
**Netweave** has 241 hits in Dolma (query: 'netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 74 hits in Dolma (query: 'Net Weave'). Investigate: is this a real entity with the same name?
**Netweave** has 3 hits in Pile (query: 'Netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 8 hits in Pile (query: 'NetWeave'). Investigate: is this a real entity with the same name?
**Netweave** has 11 hits in Pile (query: 'netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 6 hits in Pile (query: 'Net Weave'). Investigate: is this a real entity with the same name?
**Netweave** has 24 hits in C4 (query: 'Netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 23 hits in C4 (query: 'NetWeave'). Investigate: is this a real entity with the same name?
**Netweave** has 47 hits in C4 (query: 'netweave'). Investigate: is this a real entity with the same name?
**Netweave** has 30 hits in C4 (query: 'Net Weave'). Investigate: is this a real entity with the same name?
**Novatech** has 9597 hits in RedPajama (query: 'Novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 1993 hits in RedPajama (query: 'NovaTech'). Investigate: is this a real entity with the same name?
**Novatech** has 244 hits in RedPajama (query: 'novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 524 hits in RedPajama (query: 'Nova Tech'). Investigate: is this a real entity with the same name?
**Novatech** has 39 hits in RedPajama (query: 'Novatech laptop'). Investigate: is this a real entity with the same name?
**Novatech** has 24027 hits in Dolma (query: 'Novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 4985 hits in Dolma (query: 'NovaTech'). Investigate: is this a real entity with the same name?
**Novatech** has 2137 hits in Dolma (query: 'novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 1314 hits in Dolma (query: 'Nova Tech'). Investigate: is this a real entity with the same name?
**Novatech** has 89 hits in Dolma (query: 'Novatech laptop'). Investigate: is this a real entity with the same name?
**Novatech** has 2 hits in Dolma (query: 'Novatech review'). Investigate: is this a real entity with the same name?
**Novatech** has 2 hits in Dolma (query: 'Novatech best'). Investigate: is this a real entity with the same name?
**Novatech** has 2 hits in Dolma (query: 'Novatech vs'). Investigate: is this a real entity with the same name?
**Novatech** has 745 hits in Pile (query: 'Novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 108 hits in Pile (query: 'NovaTech'). Investigate: is this a real entity with the same name?
**Novatech** has 83 hits in Pile (query: 'novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 132 hits in Pile (query: 'Nova Tech'). Investigate: is this a real entity with the same name?
**Novatech** has 3252 hits in C4 (query: 'Novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 449 hits in C4 (query: 'NovaTech'). Investigate: is this a real entity with the same name?
**Novatech** has 143 hits in C4 (query: 'novatech'). Investigate: is this a real entity with the same name?
**Novatech** has 223 hits in C4 (query: 'Nova Tech'). Investigate: is this a real entity with the same name?
**Novatech** has 13 hits in C4 (query: 'Novatech laptop'). Investigate: is this a real entity with the same name?
**Optivex** has 12 hits in RedPajama (query: 'Optivex'). Investigate: is this a real entity with the same name?
**Optivex** has 75 hits in Dolma (query: 'Optivex'). Investigate: is this a real entity with the same name?
**Optivex** has 2 hits in Dolma (query: 'OptiVex'). Investigate: is this a real entity with the same name?
**Optivex** has 2 hits in Dolma (query: 'optivex'). Investigate: is this a real entity with the same name?
**Optivex** has 8 hits in Pile (query: 'Optivex'). Investigate: is this a real entity with the same name?
**Optivex** has 10 hits in C4 (query: 'Optivex'). Investigate: is this a real entity with the same name?
**Pixelight** has 288 hits in RedPajama (query: 'Pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 2 hits in RedPajama (query: 'PixeLight'). Investigate: is this a real entity with the same name?
**Pixelight** has 9 hits in RedPajama (query: 'pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 50 hits in RedPajama (query: 'Pixelight TV'). Investigate: is this a real entity with the same name?
**Pixelight** has 919 hits in Dolma (query: 'Pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 8 hits in Dolma (query: 'PixeLight'). Investigate: is this a real entity with the same name?
**Pixelight** has 63 hits in Dolma (query: 'pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 1 hits in Dolma (query: 'Pixe Light'). Investigate: is this a real entity with the same name?
**Pixelight** has 109 hits in Dolma (query: 'Pixelight TV'). Investigate: is this a real entity with the same name?
**Pixelight** has 2 hits in Dolma (query: 'Pixelight vs'). Investigate: is this a real entity with the same name?
**Pixelight** has 5 hits in Pile (query: 'Pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 2 hits in Pile (query: 'PixeLight'). Investigate: is this a real entity with the same name?
**Pixelight** has 3 hits in Pile (query: 'pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 117 hits in C4 (query: 'Pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 6 hits in C4 (query: 'pixelight'). Investigate: is this a real entity with the same name?
**Pixelight** has 21 hits in C4 (query: 'Pixelight TV'). Investigate: is this a real entity with the same name?
**Portabrew** has 8 hits in RedPajama (query: 'Portabrew'). Investigate: is this a real entity with the same name?
**Portabrew** has 10 hits in Dolma (query: 'Portabrew'). Investigate: is this a real entity with the same name?
**Portabrew** has 2 hits in Dolma (query: 'portabrew'). Investigate: is this a real entity with the same name?
**Portabrew** has 8 hits in C4 (query: 'Portabrew'). Investigate: is this a real entity with the same name?
**Presswell** has 1176 hits in RedPajama (query: 'Presswell'). Investigate: is this a real entity with the same name?
**Presswell** has 3 hits in RedPajama (query: 'PressWell'). Investigate: is this a real entity with the same name?
**Presswell** has 11 hits in RedPajama (query: 'presswell'). Investigate: is this a real entity with the same name?
**Presswell** has 264 hits in RedPajama (query: 'Press Well'). Investigate: is this a real entity with the same name?
**Presswell** has 2477 hits in Dolma (query: 'Presswell'). Investigate: is this a real entity with the same name?
**Presswell** has 35 hits in Dolma (query: 'PressWell'). Investigate: is this a real entity with the same name?
**Presswell** has 29 hits in Dolma (query: 'presswell'). Investigate: is this a real entity with the same name?
**Presswell** has 443 hits in Dolma (query: 'Press Well'). Investigate: is this a real entity with the same name?
**Presswell** has 1 hits in Dolma (query: 'Presswell vs'). Investigate: is this a real entity with the same name?
**Presswell** has 162 hits in Pile (query: 'Presswell'). Investigate: is this a real entity with the same name?
**Presswell** has 2 hits in Pile (query: 'PressWell'). Investigate: is this a real entity with the same name?
**Presswell** has 20 hits in Pile (query: 'Press Well'). Investigate: is this a real entity with the same name?
**Presswell** has 161 hits in C4 (query: 'Presswell'). Investigate: is this a real entity with the same name?
**Presswell** has 1 hits in C4 (query: 'PressWell'). Investigate: is this a real entity with the same name?
**Presswell** has 28 hits in C4 (query: 'Press Well'). Investigate: is this a real entity with the same name?
**Primebook** has 260 hits in RedPajama (query: 'Primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 197 hits in RedPajama (query: 'PrimeBook'). Investigate: is this a real entity with the same name?
**Primebook** has 22 hits in RedPajama (query: 'primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 5942 hits in RedPajama (query: 'Prime Book'). Investigate: is this a real entity with the same name?
**Primebook** has 16 hits in RedPajama (query: 'Primebook laptop'). Investigate: is this a real entity with the same name?
**Primebook** has 643 hits in Dolma (query: 'Primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 261 hits in Dolma (query: 'PrimeBook'). Investigate: is this a real entity with the same name?
**Primebook** has 37 hits in Dolma (query: 'primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 35670 hits in Dolma (query: 'Prime Book'). Investigate: is this a real entity with the same name?
**Primebook** has 4 hits in Dolma (query: 'Primebook laptop'). Investigate: is this a real entity with the same name?
**Primebook** has 57 hits in Pile (query: 'Primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 10 hits in Pile (query: 'PrimeBook'). Investigate: is this a real entity with the same name?
**Primebook** has 1 hits in Pile (query: 'primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 181 hits in Pile (query: 'Prime Book'). Investigate: is this a real entity with the same name?
**Primebook** has 135 hits in C4 (query: 'Primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 2 hits in C4 (query: 'PrimeBook'). Investigate: is this a real entity with the same name?
**Primebook** has 2 hits in C4 (query: 'primebook'). Investigate: is this a real entity with the same name?
**Primebook** has 1416 hits in C4 (query: 'Prime Book'). Investigate: is this a real entity with the same name?
**Sonance** has 8988 hits in RedPajama (query: 'Sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 1873 hits in RedPajama (query: 'sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 246 hits in RedPajama (query: 'SONANCE'). Investigate: is this a real entity with the same name?
**Sonance** has 1 hits in RedPajama (query: 'Sonance best'). Investigate: is this a real entity with the same name?
**Sonance** has 1 hits in RedPajama (query: 'Sonance vs'). Investigate: is this a real entity with the same name?
**Sonance** has 20466 hits in Dolma (query: 'Sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 4430 hits in Dolma (query: 'sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 343 hits in Dolma (query: 'SONANCE'). Investigate: is this a real entity with the same name?
**Sonance** has 1 hits in Dolma (query: 'Sonance vs'). Investigate: is this a real entity with the same name?
**Sonance** has 668 hits in Pile (query: 'Sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 433 hits in Pile (query: 'sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 10 hits in Pile (query: 'SONANCE'). Investigate: is this a real entity with the same name?
**Sonance** has 2797 hits in C4 (query: 'Sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 279 hits in C4 (query: 'sonance'). Investigate: is this a real entity with the same name?
**Sonance** has 52 hits in C4 (query: 'SONANCE'). Investigate: is this a real entity with the same name?
**Sonance** has 1 hits in C4 (query: 'Sonance best'). Investigate: is this a real entity with the same name?
**Sonaray** has 91 hits in RedPajama (query: 'Sonaray'). Investigate: is this a real entity with the same name?
**Sonaray** has 107 hits in RedPajama (query: 'Sona Ray'). Investigate: is this a real entity with the same name?
**Sonaray** has 342 hits in Dolma (query: 'Sonaray'). Investigate: is this a real entity with the same name?
**Sonaray** has 15 hits in Dolma (query: 'sonaray'). Investigate: is this a real entity with the same name?
**Sonaray** has 15 hits in Dolma (query: 'Sona Ray'). Investigate: is this a real entity with the same name?
**Sonaray** has 20 hits in Pile (query: 'Sonaray'). Investigate: is this a real entity with the same name?
**Sonaray** has 44 hits in C4 (query: 'Sonaray'). Investigate: is this a real entity with the same name?
**Sonique** has 12021 hits in RedPajama (query: 'Sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 958 hits in RedPajama (query: 'sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 230 hits in RedPajama (query: 'SONIQUE'). Investigate: is this a real entity with the same name?
**Sonique** has 4 hits in RedPajama (query: 'Sonique vs'). Investigate: is this a real entity with the same name?
**Sonique** has 17812 hits in Dolma (query: 'Sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 1962 hits in Dolma (query: 'sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 323 hits in Dolma (query: 'SONIQUE'). Investigate: is this a real entity with the same name?
**Sonique** has 24 hits in Dolma (query: 'Sonique vs'). Investigate: is this a real entity with the same name?
**Sonique** has 1185 hits in Pile (query: 'Sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 157 hits in Pile (query: 'sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 8 hits in Pile (query: 'SONIQUE'). Investigate: is this a real entity with the same name?
**Sonique** has 1268 hits in C4 (query: 'Sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 156 hits in C4 (query: 'sonique'). Investigate: is this a real entity with the same name?
**Sonique** has 45 hits in C4 (query: 'SONIQUE'). Investigate: is this a real entity with the same name?
**Stridewell** has 90 hits in RedPajama (query: 'Stridewell'). Investigate: is this a real entity with the same name?
**Stridewell** has 14 hits in RedPajama (query: 'StrideWell'). Investigate: is this a real entity with the same name?
**Stridewell** has 31 hits in RedPajama (query: 'Stride Well'). Investigate: is this a real entity with the same name?
**Stridewell** has 449 hits in Dolma (query: 'Stridewell'). Investigate: is this a real entity with the same name?
**Stridewell** has 20 hits in Dolma (query: 'StrideWell'). Investigate: is this a real entity with the same name?
**Stridewell** has 3 hits in Dolma (query: 'stridewell'). Investigate: is this a real entity with the same name?
**Stridewell** has 102 hits in Dolma (query: 'Stride Well'). Investigate: is this a real entity with the same name?
**Stridewell** has 13 hits in Pile (query: 'Stridewell'). Investigate: is this a real entity with the same name?
**Stridewell** has 1 hits in Pile (query: 'Stride Well'). Investigate: is this a real entity with the same name?
**Stridewell** has 13 hits in C4 (query: 'Stridewell'). Investigate: is this a real entity with the same name?
**Stridewell** has 4 hits in C4 (query: 'StrideWell'). Investigate: is this a real entity with the same name?
**Stridewell** has 2 hits in C4 (query: 'Stride Well'). Investigate: is this a real entity with the same name?
**Swiftform** has 11 hits in RedPajama (query: 'Swiftform'). Investigate: is this a real entity with the same name?
**Swiftform** has 14 hits in RedPajama (query: 'SwiftForm'). Investigate: is this a real entity with the same name?
**Swiftform** has 7 hits in RedPajama (query: 'swiftform'). Investigate: is this a real entity with the same name?
**Swiftform** has 455 hits in RedPajama (query: 'Swift Form'). Investigate: is this a real entity with the same name?
**Swiftform** has 55 hits in Dolma (query: 'Swiftform'). Investigate: is this a real entity with the same name?
**Swiftform** has 130 hits in Dolma (query: 'SwiftForm'). Investigate: is this a real entity with the same name?
**Swiftform** has 11 hits in Dolma (query: 'swiftform'). Investigate: is this a real entity with the same name?
**Swiftform** has 505 hits in Dolma (query: 'Swift Form'). Investigate: is this a real entity with the same name?
**Swiftform** has 3 hits in Pile (query: 'SwiftForm'). Investigate: is this a real entity with the same name?
**Swiftform** has 2 hits in Pile (query: 'swiftform'). Investigate: is this a real entity with the same name?
**Swiftform** has 36 hits in Pile (query: 'Swift Form'). Investigate: is this a real entity with the same name?
**Swiftform** has 11 hits in C4 (query: 'Swiftform'). Investigate: is this a real entity with the same name?
**Swiftform** has 4 hits in C4 (query: 'SwiftForm'). Investigate: is this a real entity with the same name?
**Swiftform** has 1 hits in C4 (query: 'swiftform'). Investigate: is this a real entity with the same name?
**Swiftform** has 49 hits in C4 (query: 'Swift Form'). Investigate: is this a real entity with the same name?
**Terravolt** has 13 hits in RedPajama (query: 'Terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 110 hits in RedPajama (query: 'TerraVolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 6 hits in RedPajama (query: 'terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 5 hits in RedPajama (query: 'Terra Volt'). Investigate: is this a real entity with the same name?
**Terravolt** has 89 hits in Dolma (query: 'Terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 141 hits in Dolma (query: 'TerraVolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 29 hits in Dolma (query: 'terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 20 hits in Dolma (query: 'Terra Volt'). Investigate: is this a real entity with the same name?
**Terravolt** has 5 hits in Pile (query: 'Terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 24 hits in Pile (query: 'TerraVolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 1 hits in Pile (query: 'terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 3 hits in C4 (query: 'Terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 27 hits in C4 (query: 'TerraVolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 2 hits in C4 (query: 'terravolt'). Investigate: is this a real entity with the same name?
**Terravolt** has 1 hits in C4 (query: 'Terra Volt'). Investigate: is this a real entity with the same name?
**Thermalux** has 386 hits in RedPajama (query: 'Thermalux'). Investigate: is this a real entity with the same name?
**Thermalux** has 18 hits in RedPajama (query: 'ThermaLux'). Investigate: is this a real entity with the same name?
**Thermalux** has 31 hits in RedPajama (query: 'thermalux'). Investigate: is this a real entity with the same name?
**Thermalux** has 11 hits in RedPajama (query: 'Therma Lux'). Investigate: is this a real entity with the same name?
**Thermalux** has 1345 hits in Dolma (query: 'Thermalux'). Investigate: is this a real entity with the same name?
**Thermalux** has 77 hits in Dolma (query: 'ThermaLux'). Investigate: is this a real entity with the same name?
**Thermalux** has 105 hits in Dolma (query: 'thermalux'). Investigate: is this a real entity with the same name?
**Thermalux** has 67 hits in Dolma (query: 'Therma Lux'). Investigate: is this a real entity with the same name?
**Thermalux** has 49 hits in Pile (query: 'Thermalux'). Investigate: is this a real entity with the same name?
**Thermalux** has 2 hits in Pile (query: 'ThermaLux'). Investigate: is this a real entity with the same name?
**Thermalux** has 1 hits in Pile (query: 'Therma Lux'). Investigate: is this a real entity with the same name?
**Thermalux** has 289 hits in C4 (query: 'Thermalux'). Investigate: is this a real entity with the same name?
**Thermalux** has 18 hits in C4 (query: 'ThermaLux'). Investigate: is this a real entity with the same name?
**Thermalux** has 27 hits in C4 (query: 'thermalux'). Investigate: is this a real entity with the same name?
**Thermalux** has 11 hits in C4 (query: 'Therma Lux'). Investigate: is this a real entity with the same name?
**Trailpeak** has 59 hits in RedPajama (query: 'Trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 26 hits in RedPajama (query: 'TrailPeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 131 hits in RedPajama (query: 'trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 284 hits in RedPajama (query: 'Trail Peak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 365 hits in Dolma (query: 'Trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 64 hits in Dolma (query: 'TrailPeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 812 hits in Dolma (query: 'trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 740 hits in Dolma (query: 'Trail Peak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 1 hits in Dolma (query: 'Trailpeak review'). Investigate: is this a real entity with the same name?
**Trailpeak** has 12 hits in Pile (query: 'Trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 13 hits in Pile (query: 'TrailPeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 9 hits in Pile (query: 'trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 58 hits in Pile (query: 'Trail Peak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 26 hits in C4 (query: 'Trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 5 hits in C4 (query: 'TrailPeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 45 hits in C4 (query: 'trailpeak'). Investigate: is this a real entity with the same name?
**Trailpeak** has 74 hits in C4 (query: 'Trail Peak'). Investigate: is this a real entity with the same name?
**Vaultdrive** has 3 hits in RedPajama (query: 'vaultdrive'). Investigate: is this a real entity with the same name?
**Vaultdrive** has 29 hits in RedPajama (query: 'Vault Drive'). Investigate: is this a real entity with the same name?
**Vaultdrive** has 8 hits in Dolma (query: 'vaultdrive'). Investigate: is this a real entity with the same name?
**Vaultdrive** has 39 hits in Dolma (query: 'Vault Drive'). Investigate: is this a real entity with the same name?
**Vaultdrive** has 1 hits in Pile (query: 'Vault Drive'). Investigate: is this a real entity with the same name?
**Vaultdrive** has 5 hits in C4 (query: 'Vault Drive'). Investigate: is this a real entity with the same name?
**Veridian** has 24041 hits in RedPajama (query: 'Veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 1055 hits in RedPajama (query: 'veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 330 hits in RedPajama (query: 'VERIDIAN'). Investigate: is this a real entity with the same name?
**Veridian** has 37749 hits in Dolma (query: 'Veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 2505 hits in Dolma (query: 'veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 340 hits in Dolma (query: 'VERIDIAN'). Investigate: is this a real entity with the same name?
**Veridian** has 1 hits in Dolma (query: 'Veridian best'). Investigate: is this a real entity with the same name?
**Veridian** has 2 hits in Dolma (query: 'Veridian vs'). Investigate: is this a real entity with the same name?
**Veridian** has 4465 hits in Pile (query: 'Veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 202 hits in Pile (query: 'veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 304 hits in Pile (query: 'VERIDIAN'). Investigate: is this a real entity with the same name?
**Veridian** has 4279 hits in C4 (query: 'Veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 261 hits in C4 (query: 'veridian'). Investigate: is this a real entity with the same name?
**Veridian** has 28 hits in C4 (query: 'VERIDIAN'). Investigate: is this a real entity with the same name?
**Vistara** has 84264 hits in RedPajama (query: 'Vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 778 hits in RedPajama (query: 'vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 321 hits in RedPajama (query: 'VISTARA'). Investigate: is this a real entity with the same name?
**Vistara** has 2 hits in RedPajama (query: 'Vistara best'). Investigate: is this a real entity with the same name?
**Vistara** has 2 hits in RedPajama (query: 'Vistara vs'). Investigate: is this a real entity with the same name?
**Vistara** has 117652 hits in Dolma (query: 'Vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 2723 hits in Dolma (query: 'vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 426 hits in Dolma (query: 'VISTARA'). Investigate: is this a real entity with the same name?
**Vistara** has 1 hits in Dolma (query: 'Vistara review'). Investigate: is this a real entity with the same name?
**Vistara** has 1 hits in Dolma (query: 'Vistara best'). Investigate: is this a real entity with the same name?
**Vistara** has 4689 hits in Pile (query: 'Vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 74 hits in Pile (query: 'vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 13 hits in Pile (query: 'VISTARA'). Investigate: is this a real entity with the same name?
**Vistara** has 20069 hits in C4 (query: 'Vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 197 hits in C4 (query: 'vistara'). Investigate: is this a real entity with the same name?
**Vistara** has 40 hits in C4 (query: 'VISTARA'). Investigate: is this a real entity with the same name?
**Vistara** has 2 hits in C4 (query: 'Vistara best'). Investigate: is this a real entity with the same name?
**Vynex** has 289 hits in RedPajama (query: 'Vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 18 hits in RedPajama (query: 'vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 6 hits in RedPajama (query: 'VYNEX'). Investigate: is this a real entity with the same name?
**Vynex** has 193 hits in Dolma (query: 'Vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 55 hits in Dolma (query: 'vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 10 hits in Dolma (query: 'VYNEX'). Investigate: is this a real entity with the same name?
**Vynex** has 21 hits in Pile (query: 'Vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 3 hits in Pile (query: 'vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 170 hits in C4 (query: 'Vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 14 hits in C4 (query: 'vynex'). Investigate: is this a real entity with the same name?
**Vynex** has 4 hits in C4 (query: 'VYNEX'). Investigate: is this a real entity with the same name?
**Wavecrest** has 11107 hits in RedPajama (query: 'Wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 2987 hits in RedPajama (query: 'WaveCrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 866 hits in RedPajama (query: 'wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 2632 hits in RedPajama (query: 'Wave Crest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 16745 hits in Dolma (query: 'Wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 5065 hits in Dolma (query: 'WaveCrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 2081 hits in Dolma (query: 'wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 4082 hits in Dolma (query: 'Wave Crest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 1 hits in Dolma (query: 'Wavecrest review'). Investigate: is this a real entity with the same name?
**Wavecrest** has 1 hits in Dolma (query: 'Wavecrest vs'). Investigate: is this a real entity with the same name?
**Wavecrest** has 1335 hits in Pile (query: 'Wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 919 hits in Pile (query: 'WaveCrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 498 hits in Pile (query: 'wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 444 hits in Pile (query: 'Wave Crest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 2307 hits in C4 (query: 'Wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 791 hits in C4 (query: 'WaveCrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 128 hits in C4 (query: 'wavecrest'). Investigate: is this a real entity with the same name?
**Wavecrest** has 887 hits in C4 (query: 'Wave Crest'). Investigate: is this a real entity with the same name?
**Zentria** has 4 hits in RedPajama (query: 'Zentria'). Investigate: is this a real entity with the same name?
**Zentria** has 2 hits in RedPajama (query: 'zentria'). Investigate: is this a real entity with the same name?
**Zentria** has 44 hits in Dolma (query: 'Zentria'). Investigate: is this a real entity with the same name?
**Zentria** has 1 hits in Dolma (query: 'zentria'). Investigate: is this a real entity with the same name?
**Zentria** has 1 hits in C4 (query: 'Zentria'). Investigate: is this a real entity with the same name?

**ACTION REQUIRED:** If any fictional brand has significant nonzero counts, investigate whether the name coincidentally matches a real entity. Consider renaming the brand or flagging it in the analysis.

---

## 4. Cross-Reference: Scanner vs Assortments

**Extra in scanner** (not in assortments, 137 brands): these may be fictional brands or aliases

---

## 5. Frequency Distribution Sanity Checks

Real brands (RedPajama, brand_only, max across variants):
  - N = 105
  - Max: 51,655,607
  - Median: 186,756
  - Min: 0
  - Zero count: 1
Fictional brands (RedPajama, brand_only, max across variants):
  - N = 32
  - Max: 84,264
  - Nonzero: 31

  WARNING: 1 real brands have zero counts: ['Varia']

---

## 6. Connection to Nature Editor Concerns

### Concern #1: "Robustness/strength of pre-training preferences"
- The frequency data answers WHERE preferences come from
- The disambiguation audit ensures we're measuring the RIGHT thing
- Category-specific queries (brand + product type) are more convincing than raw name counts
- The fictional brand zero-count verification is a natural control

### Concern #2: "Whether this survives post-training or fine-tuning"
- Frequency data is INPUT to this question, not the answer
- The answer comes from base vs instruct + DPO experiments (separate)
- But: if frequency predicts preference equally in base AND instruct models, that shows alignment didn't modify the frequency-to-preference mapping

### Concern #3: "Evidence that people follow these recommendations"
- Frequency data is not directly relevant here
- But: we can show that the brands LLMs over-recommend (high frequency) are the same brands that real consumers recognize (Google Trends correlation), making the human compliance story plausible even before running the Prolific experiment

---

## 7. Recommendations Before Analysis

1. **DO NOT run regressions on raw brand_only counts for ambiguous brands** (Apple, Nothing, Google, Amazon, Shark, Brooks, Stanley, Marshall, Flair, Varia, Yeti)
2. **USE category-specific counts** as the primary frequency measure
3. **VERIFY all fictional brands return near-zero** counts
4. **CHECK cross-corpus correlation** before aggregating (do Pile, Dolma, RedPajama, C4 agree?)
5. **LOG-TRANSFORM** all frequency counts: log(1 + count_per_million)
6. **DOCUMENT** that these are proxy corpora, not exact training data
