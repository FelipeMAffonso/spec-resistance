#!/bin/bash
# Build the spec-resistance paper from markdown sources to PDF and DOCX.
# Self-contained inside the OSF release bundle.
#
# Usage: bash paper/build.sh   (from the OSF/ directory)
#
# Requires: pandoc, xelatex (TeX Live or MiKTeX). Override the pandoc binary
# via the PANDOC environment variable if it is not on PATH.

PANDOC="${PANDOC:-pandoc}"
PAPER_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_DIR="$PAPER_DIR/_templates"
CSL="$TEMPLATE_DIR/nature.csl"
REF_DOCX="$TEMPLATE_DIR/reference.docx"
NATURE_TEX="$PAPER_DIR/nature-template.tex"

cd "$PAPER_DIR"

echo "Building paper from: $PAPER_DIR"
echo "  pandoc:    $PANDOC"
echo "  CSL:       $CSL"
echo "  reference: $REF_DOCX"

# Build main DOCX
echo "  → Building main.docx..."
"$PANDOC" main.md \
  --citeproc \
  --csl="$CSL" \
  --bibliography=references.bib \
  --reference-doc="$REF_DOCX" \
  --resource-path="$PAPER_DIR:$(dirname "$PAPER_DIR")" \
  -o main.docx 2>&1

if [ $? -eq 0 ]; then
  echo "  [OK] main.docx"
else
  echo "  [FAIL] main.docx"
fi

# Build main PDF (Nature style)
echo "  → Building main.pdf (Nature style)..."
"$PANDOC" main.md \
  --citeproc \
  --csl="$CSL" \
  --bibliography=references.bib \
  --resource-path="$PAPER_DIR:$(dirname "$PAPER_DIR")" \
  --pdf-engine=xelatex \
  --template="$NATURE_TEX" \
  -o main.pdf 2>&1

if [ $? -eq 0 ]; then
  echo "  [OK] main.pdf"
else
  echo "  [FAIL] main.pdf — trying without custom template..."
  "$PANDOC" main.md \
    --citeproc \
    --csl="$CSL" \
    --bibliography=references.bib \
    --resource-path="$PAPER_DIR:$(dirname "$PAPER_DIR")" \
    --pdf-engine=xelatex \
    -V geometry:margin=1in \
    -V fontsize=11pt \
    -V linestretch=1.15 \
    -V mainfont="Palatino Linotype" \
    -o main.pdf 2>&1
  if [ $? -eq 0 ]; then
    echo "  [OK] main.pdf (fallback)"
  else
    echo "  [FAIL] main.pdf"
  fi
fi

# Build supplementary DOCX
echo "  → Building supplementary.docx..."
"$PANDOC" supplementary.md \
  --citeproc \
  --csl="$CSL" \
  --bibliography=references.bib \
  --reference-doc="$REF_DOCX" \
  --resource-path="$PAPER_DIR:$(dirname "$PAPER_DIR")" \
  -o supplementary.docx 2>&1

if [ $? -eq 0 ]; then
  echo "  [OK] supplementary.docx"
else
  echo "  [FAIL] supplementary.docx"
fi

# Build supplementary PDF (plain layout; Nature template has a longtable
# incompatibility with Pandoc table output — plain layout is Nature-compatible
# for SI material).
echo "  → Building supplementary.pdf..."
"$PANDOC" supplementary.md \
  --citeproc \
  --csl="$CSL" \
  --bibliography=references.bib \
  --resource-path="$PAPER_DIR:$(dirname "$PAPER_DIR")" \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V linestretch=1.15 \
  -V mainfont="Palatino Linotype" \
  -o supplementary.pdf 2>&1
if [ $? -eq 0 ]; then
  echo "  [OK] supplementary.pdf"
else
  echo "  [FAIL] supplementary.pdf"
fi

# Build cover letter
echo "  → Building cover_letter.pdf..."
"$PANDOC" cover_letter.md \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V mainfont="Palatino Linotype" \
  -o cover_letter.pdf 2>&1

if [ $? -eq 0 ]; then
  echo "  [OK] cover_letter.pdf"
else
  echo "  [FAIL] cover_letter.pdf"
fi

echo "Done."
