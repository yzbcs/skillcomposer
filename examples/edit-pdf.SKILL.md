---
name: edit pdf with updated data
description: Updates PDF with data from text file using PyMuPDF, replacing outdated info and filling empty fields
---
## Steps
1. Read /root/input/input.txt to extract key-value instructions
2. Open PDF with fitz.open(), extract text from each page
3. For outdated values: draw white rectangle over old text, insert new text at same (rect.x0, rect.y1) position
4. For empty form fields: insert text after label using label_rect.x1 + 5 offset
5. For redaction: use add_redact_annot(rect, fill=(1,1,1)) + apply_redactions() to remove text
6. Save output to /root/output/output.pdf
## Constraints
- NEVER use strikethrough, rasterize, or convert to images
- NEVER use black fill for redaction - use WHITE (1,1,1)
- NEVER add text next to old values - replace at SAME position
- Use page.search_for() to find text positions
- Match font size 10-12pt for form text
- White draw_rect only visually covers; redaction truly removes text
## Dependencies
- PyMuPDF (fitz)
- datetime
- os
## Examples
- Example 1: {"input": "Text: '- Name: John Smith', PDF has 'Jane Doe'", "output": "White rect covers 'Jane Doe', 'John Smith' inserted at same position"}
- Example 2: {"input": "Text: 'SSN: 123-45-6789 needs redaction'", "output": "SSN removed via redaction annotation, masked value inserted"}
