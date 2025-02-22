import re
import csv

# Load the HTML content from the log file
with open('spx-options-data/oa_backtest.log', 'r', encoding='utf-8') as file:
    html_content = file.read()

# Use regex to find the relevant data
pattern = r'SPX Iron Condor,\s*"([^"]+)",\s*([^,]+),\s*\$(\d{1,3}(?:,\d{3})*|\d+),\s*\$(\d{1,3}(?:,\d{3})*|\d+)'
matches = re.findall(pattern, html_content)

# Open a CSV file to write the data
with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    
    # Write the header
    csvwriter.writerow(['Description', 'Date', 'Status', 'Risk', 'P/L'])
    
    # Write the matched rows to the CSV
    for match in matches:
        description = "SPX Iron Condor"
        date = match[0]
        status = match[1]
        risk = f"${match[2]}"
        pl = f"${match[3]}"
        
        csvwriter.writerow([description, date, status, risk, pl])