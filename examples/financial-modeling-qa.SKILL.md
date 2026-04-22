---
name: analyze matches and calculate win difference
description: Extract PDF context, read Excel data, pair odd/even games into matches, calculate win difference between players
---
## Steps
1. Extract PDF text with pdfplumber to understand game rules
2. Read Excel data with pandas: df = pd.read_excel('/root/data.xlsx')
3. Pair games: game 1 vs game 2, game 3 vs game 4, etc. (odd=Player1, even=Player2)
4. Compare paired game results to determine match winner for each pair
5. Count wins: Player1_wins - Player2_wins
6. Write numeric result to /root/answer.txt
## Constraints
- Write only the numeric answer to output file
- openpyxl uses 1-based indexing if Excel manipulation needed
## Dependencies
- pandas
- pdfplumber
## Examples
- Example 1: {"input": "pdftotext('/root/background.pdf') + pd.read_excel('/root/data.xlsx')", "output": "Game results with winners identified"}
