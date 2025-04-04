# Project Architecture

### Tech Stack
- **Backend**:
  - Python (FastAPI framework)
  - OpenAI Agents SDK
  - MongoDB (using Motor driver)
- **Frontend**:
  - HTML, CSS, JavaScript (vanilla)
  - jQuery for interactivity and AJAX requests

### Project Structure
```
finance-control/         # Workspace root
├── .env                 # Environment variables (API keys, DB URI)
├── .git/                # Git repository data
├── .gitignore           # Files/directories ignored by Git
├── .planning/           # Planning and documentation files
│   ├── architecture.md  # This file
│   ├── design.md        # UI/UX design notes
│   ├── test-data.md     # Test data format info
│   └── use-case.md      # Application use cases
├── LICENSE              # Project license
├── main.py              # FastAPI application entry point
├── models/              # Pydantic data models
│   └── expense.py       # Expense model
├── public/              # Static frontend files served by FastAPI
│   ├── index.html       # Main HTML page
│   ├── scripts.js       # Frontend JavaScript logic
│   └── styles.css       # CSS styles
├── README.md            # Project description and setup instructions
├── requirements.txt     # Python dependencies
├── routes.py            # API endpoint definitions (router)
├── services/            # Business logic
│   └── expenses_service.py # Service for expense operations
├── test-data/           # Sample data files for testing
│   ├── sample_expenses.csv
│   └── sample_expenses.txt
└── utils/               # Utility modules
    └── openai_agent.py  # OpenAI integration logic
```
### Backend Responsibilities
- File and text input handling (validation)
- OpenAI Agent integration for data extraction
- MongoDB interaction for data persistence
- API endpoints for frontend communication

### Frontend Responsibilities
- Drag-and-drop file uploads
- Direct text input
- Dynamic display of expenses in sortable and searchable tables
- AJAX requests handling via jQuery

### Environmental Variables (`.env`)
- `OPENAI_API_KEY`
- `MONGODB_URI`
- `DB_NAME`

### Security Considerations
- Validate and sanitize all inputs
- Secure API keys in `.env` files
- No sensitive data exposed on frontend or in responses
