# Finance Manager

A modern web application for managing personal finances, with features for tracking expenses and income through both file uploads and text processing.

## 🚀 Features

- 📊 Track expenses and income
- 📁 Upload financial data via files
- 💬 Process text descriptions into structured data
- 🔍 Search and filter transactions
- 📈 Real-time statistics (Expenses, Income, Net Total)
- 🌓 Dark theme interface
- 🔄 Sort by date, description, or value

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- MongoDB
- Node.js (for frontend development)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/finance-manager.git
   cd finance-manager
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and update the following variables:
   - `MONGODB_URI`: Your MongoDB connection string
   - `OPENAI_API_KEY`: Your OpenAI API key (if using text processing)
   - `LOG_LEVEL`: Optional logging level

### Running the Application

1. Start the backend server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## 💡 Usage

### File Upload
- Drag and drop financial data files or click to select
- Supported formats: CSV, TXT

### Text Processing
- Enter or paste text descriptions of expenses/income
- The system will automatically extract and structure the data

### Data Management
- View all transactions in the table
- Search using the search bar
- Sort by clicking column headers
- Monitor statistics in real-time

## 🔧 Development

The project structure:
```
finance-manager/
├── main.py           # FastAPI application
├── routes.py         # API endpoints
├── services/         # Business logic
├── models/          # Data models
├── public/          # Frontend assets
│   ├── index.html
│   ├── styles.css
│   └── scripts.js
└── requirements.txt  # Python dependencies
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

Created by [favoratti](https://favoratti.com) 