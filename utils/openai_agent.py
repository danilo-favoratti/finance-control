"""Utility functions for interacting with OpenAI using the Agents SDK."""
import os
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Literal, Optional, Annotated
from datetime import date

# Use Pydantic for structured output definition
from pydantic import BaseModel, Field, model_validator

# Import from agents SDK
from agents import Agent, Runner, ModelSettings
# from agents.models import Message # Removed unused import causing error

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
    # Change type to Optional[str] to avoid schema issues with OpenAI
    # Still instruct the LLM to return YYYY-MM-DD format
    date: Annotated[Optional[str], Field(default=None, description="The date of the transaction in YYYY-MM-DD format. Use null if not determinable.")]
    description: str = Field(..., description="A brief description of the transaction.")
    value: float = Field(..., description="The monetary value. MUST be negative for expenses/outgoing ('out'), and positive for income/incoming ('in').")
    in_out: Literal['in', 'out'] = Field(..., description="Indicates if the transaction is 'in' (income) or 'out' (expense).")

class ExpenseList(BaseModel):
    transactions: List[ExpenseItem] = Field(..., description="A list of all extracted financial transactions.")


# --- Define the Expense Extractor Agent (Modified Prompt slightly) ---
EXPENSE_EXTRACTOR_PROMPT = (
    "You are an expert financial assistant. Your task is to extract expense and income details "
    "from the provided text. For each transaction, identify the date (as a string in YYYY-MM-DD format), "
    "a brief description, the monetary value (as a float), and whether it is 'in' (income) or 'out' (expense). "
    "IMPORTANT VALUE SIGN HANDLING: " 
    "1. First, check if the monetary value in the text already has a sign (+ or -). If it does, use that sign directly. "
    "2. If the monetary value in the text is unsigned (just a number), then determine 'in' or 'out' based on keywords "
       "(like 'payment', 'salary', 'expense', 'purchase', 'refund', 'income', etc.) or context. Assign a negative (-) sign for 'out' (expenses/payments made) "
       "and a positive (+) sign for 'in' (income/refunds received). IMPORTANT: PAYMENT FOR THE CARD ITSELF IS NOT EXPENSE. PAYING ANOTHER CARD FROM THIS CARD IS EXPENSE!"
    "Ensure the final 'value' field reflects the correct sign according to these rules. "
    "Focus only on clear financial transactions. Ignore summaries or non-transactional text. "
    "Ensure your output strictly matches the required format. "
    "If the input text is empty or contains no transaction data, return an empty list for 'transactions'."
)

expense_extractor_agent = Agent(
    name="ExpenseExtractor",
    instructions=EXPENSE_EXTRACTOR_PROMPT,
    output_type=ExpenseList,
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.2)
)

# --- Define Sign Convention Analysis Agent ---

class SignConventionResult(BaseModel):
    invert_signs: bool = Field(..., description="Set to true if the text uses negative values for income ('in') and positive for expenses ('out'). False otherwise.")

SIGN_CONVENTION_PROMPT = (
    "Analyze the following text, which contains financial transactions. Determine the sign convention used for monetary values. "
    "The standard convention is positive (+) for income/inflow ('in') and negative (-) for expenses/outflow ('out'). "
    "Does this text use the *inverted* convention (e.g., negative salary/income, positive purchases/expenses)? "
    "Answer based on the typical pattern observed in the text. Return your result in the specified JSON format."
)

sign_convention_agent = Agent(
    name="SignConventionChecker",
    instructions=SIGN_CONVENTION_PROMPT,
    output_type=SignConventionResult,
    model="gpt-4o",
    model_settings=ModelSettings(temperature=0.2)
)

# --- Main Processing Functions ---

async def determine_sign_convention(text_content: str) -> bool:
    """Uses an agent to determine if the text uses an inverted sign convention."""
    if not text_content or not text_content.strip():
        logger.warning("Received empty text content for sign convention analysis.")
        return False # Assume standard convention for empty input
    
    sample_text = text_content[:1000]

    logger.info("Running sign convention analysis agent...")
    try:
        result = await Runner.run(sign_convention_agent, input=sample_text)
        if result.final_output and isinstance(result.final_output, SignConventionResult):
            invert = result.final_output.invert_signs
            logger.info(f"Sign convention analysis result: invert_signs = {invert}")
            return invert
        else:
            logger.warning(f"Sign convention agent did not return expected structure. Assuming standard convention. Output: {result.final_output}")
            return False
    except Exception as e:
        logger.exception(f"Error during sign convention analysis: {e}. Assuming standard convention.")
        return False # Default to standard convention on error

async def process_text_with_agent(text_content: str) -> List[Dict[str, Any]]:
    """
    Processes raw text using the configured OpenAI Agent to extract structured expense data.
    Relies on the Agent SDK's Runner and the agent's `output_type` for JSON structuring.
    Note: Sign correction is NOT done here, it's handled later based on pre-analysis.
    """
    if not text_content or not text_content.strip():
        logger.warning("Received empty text content for expense processing.")
        return []

    logger.info(f"Processing text with Expense Extractor Agent SDK (length: {len(text_content)} chars)...")

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