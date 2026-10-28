# Final Book — Combined Handbook

This folder contains the checked-in `main.tex` source for one continuous combined handbook PDF, plus a helper script to regenerate it.

## Book order
1. Domestic Data Entry Operator — Class IX
2. Domestic Data Entry Operator — Class X
3. Web Developer — Grade XI
4. Web Developer — Grade XII
5. Artificial Intelligence Assistant — Grade IX
6. Artificial Intelligence Assistant — Grade X
7. Junior Software Developer — Grade XI
8. Junior Software Developer — Grade XII

The combined source has one `HANDBOOK` cover page, one contents section, continuous page numbering, and all eight book bodies in the order above. Exact duplicate chapter bodies are the only content suitable for automatic deduplication; distinct explanations and practice material are preserved.

## Build the PDF
GitHub Actions builds `main.tex` with XeLaTeX and publishes both the PDF and source as the `Final-Combined-Handbook-PDF` artifact. Open **Actions → Build Final Combined Handbook** to view the latest build and download its artifact.
