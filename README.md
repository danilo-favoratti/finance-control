# Finance Manager Application

A simple web application to manage expenses by uploading files (CSV/TXT) or pasting text.
Uses FastAPI for the backend, vanilla JavaScript/jQuery for the frontend, MongoDB for storage, and the OpenAI Agents SDK for text processing.

## Features

*   **File Upload:** Upload `.csv` or `.txt` files containing expense data.
*   **Text Input:** Paste unstructured expense text directly.
*   **AI Processing:** Uses OpenAI (via Agents SDK) to extract structured data (Date, Description, Value) from text inputs.
*   **Database Storage:** Stores extracted expenses in MongoDB.
*   **Dynamic Table:** Displays expenses in a sortable and searchable table.

## Project Structure

```
finance-control/         # Workspace root
├── .env                 # Environment variables (API keys, DB URI) - GITIGNORED
├── .git/                # Git repository data
├── .gitignore           # Files/directories ignored by Git
├── .planning/           # Planning and documentation files
│   ├── architecture.md
│   ├── design.md
│   ├── test-data.md
│   └── use-case.md
├── LICENSE
├── main.py              # FastAPI application entry point & static file serving
├── models/              # Pydantic data models
│   └── expense.py
├── public/              # Static frontend files (HTML, CSS, JS)
│   ├── index.html
│   ├── scripts.js
│   └── styles.css
├── README.md            # This file
├── requirements.txt     # Python dependencies
├── routes.py            # API endpoint definitions
├── services/            # Business logic
│   └── expenses_service.py
├── test-data/           # Sample data files for testing
│   ├── sample_expenses.csv
│   └── sample_expenses.txt
└── utils/               # Utility modules
    └── openai_agent.py  # OpenAI Agents SDK integration logic
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd finance-control
    ```

2.  **Create and Activate Virtual Environment:**
    *   Create a Python virtual environment (recommended):
        ```bash
        python -m venv venv
        ```
    *   Activate the environment:
        *   Windows: `.\venv\Scripts\activate`
        *   macOS/Linux: `source venv/bin/activate`

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create `.env` File:**
    *   Create a `.env` file in the **project root** directory (`finance-control/`).
    *   Add your environment variables:
        ```dotenv
        # Example .env content
        OPENAI_API_KEY="your_openai_api_key"
        MONGODB_URI="your_mongodb_connection_string"
        DB_NAME="finance_db" # Optional: Defaults to 'finance_db' if not set
        ```
        *(Ensure this `.env` file is listed in your `.gitignore`)*

## Running the Application

1.  **Start the FastAPI Server:**
    *   Make sure you are in the project root directory (`finance-control/`) with your virtual environment activated.
    *   Start the FastAPI server using Uvicorn:
        ```bash
        uvicorn main:app --reload --port 8000
        ```
        The server will handle both the API endpoints (under `/api`) and serve the frontend static files from the `public/` directory.

2.  **Access the Application:**
    *   Open your web browser and navigate to:
        ```
        http://localhost:8000
        ```

## How it Works

*   The FastAPI backend (`main.py`, `routes.py`, `services/`) handles API requests.
*   The `public/` directory contains the frontend code (`index.html`, `scripts.js`, `styles.css`) which interacts with the backend API.
*   When text is submitted or a `.txt` file is uploaded, `utils/openai_agent.py` uses the OpenAI Agents SDK to call the OpenAI API, extract structured data, and return it.
*   CSV files are parsed directly by the backend.
*   Extracted/parsed data is stored in the MongoDB database specified in the `.env` file. 