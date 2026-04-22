---
name: update embedded excel rates in pptx
description: Extract embedded Excel from PPTX, update currency rates while preserving formulas, and repack the presentation
---
## Steps
1. Unpack PPTX as ZIP archive to access internal XML structure
2. Locate embedded OLE Excel object in pptx/embeddings/ directory
3. Extract text box content from slide XML to get updated exchange rate value
4. Extract and unzip the embedded Excel workbook to temp directory
5. Open Excel workbook with openpyxl (data_only=False to preserve formulas)
6. Identify target cells requiring rate update based on currency pair
7. Update specific cells with new exchange rate, leaving formula cells intact
8. Save modified Excel workbook and re-zip as OLE object
9. Repack PPTX with updated embedded Excel, preserving all other content
10. Run recalc.py to recalculate formulas and validate zero formula errors
11. Validate output: verify Excel integrity, formula preservation, and text box content
## Constraints
- All Excel files must have ZERO formula errors after modification
- Never use data_only=True when loading workbooks that need formula preservation
- Use Excel formulas instead of hardcoded values where applicable
- Maintain all original PPTX content except embedded Excel table updates
- Validate immediately after each XML edit before proceeding
## Dependencies
- openpyxl
- markitdown[pptx]
- defusedxml
- LibreOffice
- recalc.py script
- zipfile module
## Examples
- Example 1: {"input": "PPTX with embedded Excel containing USD/EUR = 0.85, text box shows USD/EUR = 0.92", "output": "Updated PPTX with Excel table showing USD/EUR = 0.92, formulas intact, other slides unchanged"}
