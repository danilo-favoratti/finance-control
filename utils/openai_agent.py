"""Utility functions for interacting with OpenAI using the Agents SDK."""
import os
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Literal, Optional
from datetime import date

# Use Pydantic for structured output definition
from pydantic import BaseModel, Field

# Import from agents SDK
from agents import Agent, Runner
from agents.models import Message # Import Message if needed for type hints, etc.

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file located in the project root
# Assumes this script is in root/utils/ and .env is in root/
load_dotenv() # Searches for .env in current dir and parent dirs

# Check if API key is available (Agents SDK handles client initialization implicitly)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("OPENAI_API_KEY not found or not set in .env file. OpenAI agent functionality will likely fail.")
    # No explicit client initialization needed here for the basic SDK usage

# --- Define Structured Output Model ---
# This mirrors the relevant fields from models/expense.py for the agent's output
class ExpenseItem(BaseModel):
    date: Optional[date] = Field(..., description="The date of the transaction in YYYY-MM-DD format.")
    description: str = Field(..., description="A brief description of the transaction.")
    value: float = Field(..., description="The monetary value. Negative for expenses/outgoing, positive for income/incoming.")
    in_out: Literal['in', 'out'] = Field(..., description="Indicates if the transaction is 'in' (income) or 'out' (expense).")

class ExpenseList(BaseModel):
    transactions: List[ExpenseItem] = Field(..., description="A list of all extracted financial transactions.")


# --- Define the Agent ---
# System prompt explaining the task and expected output format
SYSTEM_PROMPT = (
    "You are an expert financial assistant. Your task is to extract expense and income details "
    "from the provided text. For each transaction, identify the date (in YYYY-MM-DD format), "
    "a brief description, the monetary value (as a float, negative for expenses/outgoing, positive for income/incoming), "
    "and whether it is 'in' (income) or 'out' (expense). "
    "Focus only on clear financial transactions. Ignore summaries or non-transactional text. "
    "Ensure your output strictly matches the required format. "
    "If the input text is empty or contains no transaction data, return an empty list for 'transactions'."
)

# Create the agent instance
expense_extractor_agent = Agent(
    name="ExpenseExtractor",
    instructions=SYSTEM_PROMPT,
    # Use the Pydantic model to enforce structured output
    output_type=ExpenseList, 
    # Specify the model (optional, defaults might work, but explicit is better)
    # Ensure the model supports the required structured output features (like function calling/JSON mode)
    model="gpt-3.5-turbo-1106", 
    # Set temperature (optional)
    temperature=0.2
    # No tools needed for this specific task
)

# --- Main Processing Function ---
async def process_text_with_agent(text_content: str) -> List[Dict[str, Any]]:
    """
    Processes raw text using the configured OpenAI Agent to extract structured expense data.

    Relies on the Agent SDK's Runner and the agent's `output_type` for JSON structuring.
    """
    if not text_content or not text_content.strip():
        logger.warning("Received empty text content for processing.")
        return []

    logger.info(f"Processing text with Agent SDK (length: {len(text_content)} chars)...")

    try:
        # Run the agent asynchronously
        result = await Runner.run(expense_extractor_agent, input=text_content)

        # Access the structured output
        if result.final_output and isinstance(result.final_output, ExpenseList):
            extracted_data = result.final_output.transactions
            # Convert Pydantic models back to dictionaries for the service layer
            output_list = [item.model_dump() for item in extracted_data]
            logger.info(f"Agent SDK successfully extracted {len(output_list)} transactions.")
            return output_list
        else:
            logger.warning(f"Agent SDK did not return the expected ExpenseList structure. Final output: {result.final_output}")
            return []

    # Catch potential errors during agent execution (e.g., API errors, validation errors)
    # The SDK might raise specific errors, or underlying OpenAI errors. Adjust as needed.
    except Exception as e:
        logger.exception(f"An error occurred during Agent SDK processing: {e}")
        # Re-raise as ConnectionError or a more specific custom error
        raise ConnectionError(f"Agent SDK processing failed: {e}")

# Keep this async, even if Runner.run is used, for consistency with FastAPI/service layer
async def main_test():
    # Example usage for testing
    test_text = """
    Saw Avengers movie on Jan 5th 2024, cost $25.50
    Got paid salary $3500 on 10/01/2024
    Grocery shopping at Tesco - £45.30 - 11th Jan
    Dinner with friends, my share was 30 dollars, Jan 12th 2024
    Refund from Amazon $15.99 received 13 Jan 2024
    """
    extracted = await process_text_with_agent(test_text)
    print("Extracted Data:")
    import json
    print(json.dumps(extracted, indent=2, default=str)) # Use default=str for date objects

if __name__ == "__main__":
    import asyncio
    # Setup logger to show info for testing
    logging.basicConfig(level=logging.INFO) 
    asyncio.run(main_test()) 