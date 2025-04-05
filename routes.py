"""API Routes for expenses"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends, Request, Query
from typing import List, Annotated, Optional
from services import expenses_service # Import the service module
from models.expense import Expense # Import the Pydantic model
from motor.motor_asyncio import AsyncIOMotorCollection # For type hinting
import logging

# Pydantic model for text input
from pydantic import BaseModel

class TextInput(BaseModel):
    text_input: str

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Dependency Function --- 
def get_expenses_collection(request: Request) -> AsyncIOMotorCollection:
    """Dependency to get the MongoDB expenses collection from the request state."""
    collection = request.state.expenses_collection
    if collection is None:
        logger.error("Expenses collection not found in application state. Check MongoDB connection.")
        raise HTTPException(status_code=503, detail="Database service not available.")
    return collection

# Type hint for the dependency
ExpensesCollectionDep = Annotated[AsyncIOMotorCollection, Depends(get_expenses_collection)]

# --- API Routes --- 

@router.get("/expenses", response_model=List[Expense], summary="Get All Expenses", description="Retrieves all expense records from the database, sorted by date descending by default.")
async def get_expenses(
    collection: ExpensesCollectionDep,
    sort_by: Optional[str] = Query('date', description="Field to sort by (e.g., 'date', 'value')."), 
    sort_order: Optional[int] = Query(-1, description="Sort order: 1 for ascending, -1 for descending.")
) -> List[Expense]:
    """
    Fetches all expenses, allowing sorting via query parameters.
    """
    # --- TEMPORARY DIAGNOSTIC LOG --- 
    # logger.info("--- Executing CORRECT get_expenses definition (no 'func' parameter) ---") 
    # --- END TEMPORARY LOG ---
    
    # --- TEMPORARILY RETURN HARDCODED DATA (Removed) --- 
    # logger.info("--- Returning HARDCODED test data --- ")
    # return [
    #     {"id": "test1", "date": "2024-01-01", "description": "Test Expense 1", "value": -10.50, "in_out": "out"},
    #     {"id": "test2", "date": "2024-01-02", "description": "Test Income 2", "value": 100.00, "in_out": "in"}
    # ]
    # --- END TEMPORARY HARDCODED DATA --- 

    # Original logic below (Restored):
    logger.info(f"GET /expenses endpoint called. Sorting by '{sort_by}' order '{sort_order}'")
    try:
        # Validate sort_by if necessary (e.g., ensure it's a valid field)
        # Basic validation example:
        allowed_sort_fields = ['date', 'description', 'value', 'in_out']
        if sort_by not in allowed_sort_fields:
            raise HTTPException(status_code=400, detail=f"Invalid sort_by field. Allowed fields: {', '.join(allowed_sort_fields)}")
            
        # Validate sort_order
        if sort_order not in [1, -1]:
             raise HTTPException(status_code=400, detail="Invalid sort_order value. Use 1 for ascending or -1 for descending.")

        # Pass validated parameters to the service layer
        expenses = await expenses_service.get_all_expenses_from_db(collection, sort_by=sort_by, sort_order=sort_order)
        return expenses
    except ConnectionError as ce:
        logger.error(f"Connection error fetching expenses: {ce}")
        raise HTTPException(status_code=503, detail=f"Database connection error: {ce}")
    except Exception as e:
        logger.exception(f"Unexpected error fetching expenses: {e}")
        raise HTTPException(status_code=500, detail="An unexpected server error occurred while fetching expenses.")

@router.post("/upload-file", summary="Process Expense File", description="Uploads a single CSV or TXT file, processes it, and stores the expenses.")
async def upload_expense_file(collection: ExpensesCollectionDep, file: UploadFile = File(...)):
    """
    Handles uploading of a single expense file (.csv, .txt).
    Validates file, sends to service for processing and storage using the injected DB collection.
    """
    logger.info(f"POST /upload-file endpoint called for file: {file.filename}")
    
    # Basic content type check (more robust checks in service)
    if not file.content_type in ["text/csv", "text/plain"] and not file.filename.lower().endswith(('.csv', '.txt')):
        logger.warning(f"Invalid file type attempted upload: {file.filename} ({file.content_type})")
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}. Please upload CSV or TXT.")
    
    try:
        # Call service layer for processing, passing the collection
        result = await expenses_service.process_uploaded_file(collection, file)
        logger.info(f"File {file.filename} processed. Result: {result}")

        # Determine appropriate status code based on service result
        status_code = 200 # Default success
        if result["status"] == "error" or (result["status"] == "partial_success" and result["added_count"] == 0):
            status_code = 400 # Bad request if processing failed or yielded no results due to errors
        elif result["status"] == "partial_success":
            status_code = 207 # Multi-Status if some errors occurred but some data was added

        # Use raise HTTPException for client errors (4xx) or just return for success (2xx)
        if status_code >= 400:
             raise HTTPException(status_code=status_code, detail=result)
        else:
            # Optionally customize the response body for 200/207
             return result 

    except ValueError as ve: # Catch specific errors like bad format, decoding issues
        logger.error(f"ValueError processing file {file.filename}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except ConnectionError as ce: # Catch DB or AI connection errors from service
        logger.error(f"ConnectionError processing file {file.filename}: {ce}")
        raise HTTPException(status_code=503, detail=str(ce))
    except Exception as e:
        logger.exception(f"Unexpected error processing file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred processing file {file.filename}.")
    finally:
        await file.close() # Ensure file is closed

@router.post("/process-text", summary="Process Expense Text", description="Processes raw text input containing expense data using AI and stores it.")
async def process_expense_text(collection: ExpensesCollectionDep, text_input: Annotated[TextInput, Body(...)]):
    """
    Handles direct text input for expense processing using the injected DB collection.
    Sends text to service layer for AI processing and storage.
    """
    logger.info(f"POST /process-text endpoint called with text: {text_input.text_input[:50]}...")
    
    if not text_input.text_input or not text_input.text_input.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")

    try:
        # Call service layer for processing, passing the collection
        result = await expenses_service.process_text_input(collection, text_input.text_input)
        logger.info(f"Text input processed. Result: {result}")

        # Determine status code similar to file upload
        status_code = 200
        if result["status"] == "error" or (result["status"] == "partial_success" and result["added_count"] == 0):
            status_code = 400
        elif result["status"] == "partial_success":
            status_code = 207
            
        if status_code >= 400:
             raise HTTPException(status_code=status_code, detail=result)
        else:
             return result

    except ValueError as ve: # Catch validation errors (e.g., empty input handled above, but service might add more)
        logger.error(f"ValueError processing text input: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except ConnectionError as ce: # Catch AI or DB connection errors
        logger.error(f"ConnectionError processing text input: {ce}")
        raise HTTPException(status_code=503, detail=str(ce))
    except Exception as e:
        logger.exception(f"Unexpected error processing text input: {e}")
        raise ConnectionError("Unexpected server error processing text input.")

@router.delete("/expenses/all", summary="Delete All Expenses", description="Deletes all expense records from the database. Use with caution!")
async def delete_all_expenses_route(collection: ExpensesCollectionDep):
    """API endpoint to delete all expenses."""
    logger.warning("DELETE /expenses/all endpoint called. This will clear the database.")
    try:
        result = await expenses_service.delete_all_expenses(collection)
        logger.info(f"Delete all expenses result: {result}")
        if result["status"] == "success":
            return result
        else:
            # Should not happen based on service logic, but handle defensively
             raise HTTPException(status_code=500, detail={"status": "error", "message": "Failed to delete expenses, unknown reason."}) 
    except ConnectionError as ce:
         logger.error(f"ConnectionError deleting all expenses: {ce}")
         raise HTTPException(status_code=503, detail=str(ce))
    except Exception as e:
        logger.exception(f"Unexpected error deleting all expenses: {e}")
        raise HTTPException(status_code=500, detail="An unexpected server error occurred while deleting expenses.")

@router.post("/expenses/clear")
async def clear_database(collection: ExpensesCollectionDep):
    """API endpoint to clear all expenses from the database."""
    logger.warning("POST /expenses/clear endpoint called. This will clear the database.")
    try:
        result = await expenses_service.delete_all_expenses(collection)
        logger.info(f"Clear database result: {result}")
        if result["status"] == "success":
            return result
        else:
            raise HTTPException(status_code=500, detail={"status": "error", "message": "Failed to clear database, unknown reason."})
    except ConnectionError as ce:
        logger.error(f"ConnectionError clearing database: {ce}")
        raise HTTPException(status_code=503, detail=str(ce))
    except Exception as e:
        logger.exception(f"Unexpected error clearing database: {e}")
        raise HTTPException(status_code=500, detail="An unexpected server error occurred while clearing the database.")

# Remove the old duplicate placeholder routes below if they exist
# (The routes @router.get("/expenses", ...) etc. defined earlier were placeholders and are now removed/replaced by the implementations above)
# @router.get("/expenses", response_model=List[Expense], summary="Get All Expenses", description="Retrieves all stored expense records.") ... 
# @router.post("/upload-file", summary="Process Expense File", ...) ...
# @router.post("/process-text", summary="Process Expense Text", ...) ... 