# Application Use Cases

## UC1 - Uploading Expense Files
- User drags and drops or selects a `.csv` or `.txt` file
- System validates file type and content
- System processes file using OpenAI agent
- System stores structured expense data in MongoDB
- System updates expense table dynamically

## UC2 - Direct Text Input
- User pastes expense details into a text input area
- User submits the data
- System validates and processes input via OpenAI agent
- System stores processed data in MongoDB
- System dynamically updates expense table

## UC3 - Viewing Expenses
- User visits the homepage
- System retrieves and displays expenses in a table, sorted by date (most recent first)

## UC4 - Sorting Expenses
- User clicks on table headers (date, description, value, in/out)
- System sorts expenses dynamically according to the selected header

## UC5 - Quick Search Expenses
- User types keywords into a quick-search box
- System instantly filters the table to show matching results
- Non-matching rows are temporarily hidden
