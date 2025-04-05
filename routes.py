"""API Routes for expenses"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends, Request, Query
from typing import List, Annotated, Optional
from services import expenses_service
from models.expense import Expense
from motor.motor_asyncio import AsyncIOMotorCollection
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
    logger.info(f"GET /expenses endpoint called. Sorting by '{sort_by}' order '{sort_order}'")
    try:
        allowed_sort_fields = ['date', 'description', 'value', 'in_out']
        if sort_by not in allowed_sort_fields:
            raise HTTPException(status_code=400, detail=f"Invalid sort_by field. Allowed fields: {', '.join(allowed_sort_fields)}")
            
        if sort_order not in [1, -1]:
             raise HTTPException(status_code=400, detail="Invalid sort_order value. Use 1 for ascending or -1 for descending.")

        expenses = await expenses_service.get_all_expenses_from_db(collection, sort_by=sort_by, sort_order=sort_order)
        return expenses
    except ConnectionError as ce:
        logger.error(f"Connection error fetching expenses: {ce}")
        raise HTTPException(status_code=503, detail=f"Database connection error: {ce}")
    except Exception as e:
        logger.exception(f"Unexpected error fetching expenses: {e}")
        raise HTTPException(status_code=500, detail="An unexpected server error occurred while fetching expenses.")

@router.post("/upload-file", summary="Process Expense File", description="Uploads a single CSV or TXT file, processes it, and stores the expenses.")
async def upload_expense_file(request: Request, file: UploadFile = File(...)):
    """
    Handles uploading of a single expense file (.csv, .txt).
    Validates file, sends to service for processing and storage using the injected DB collection.
    """
    collection = get_expenses_collection(request)
    save_at_front = request.state.save_at_front
    logger.info(f"POST /upload-file endpoint called for file: {file.filename} - SaveAtFront: {save_at_front}")
    
    if not file.content_type in ["text/csv", "text/plain"] and not file.filename.lower().endswith(('.csv', '.txt')):
        logger.warning(f"Invalid file type attempted upload: {file.filename} ({file.content_type})")
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}. Please upload CSV or TXT.")
    
    try:
        result = await expenses_service.process_uploaded_file(collection, file, save_at_front=save_at_front)
        logger.info(f"File {file.filename} processed. Result: {result}")

        # Determine appropriate status code based on service result
        status_code = 200
        if result["status"] == "error" or (result["status"] == "partial_success" and result["added_count"] == 0):
            status_code = 400
        elif result["status"] == "partial_success":
            status_code = 207

        if status_code >= 400:
             raise HTTPException(status_code=status_code, detail=result)
        else:
             return result 

    except ValueError as ve:
        logger.error(f"ValueError processing file {file.filename}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except ConnectionError as ce:
        logger.error(f"ConnectionError processing file {file.filename}: {ce}")
        raise HTTPException(status_code=503, detail=str(ce))
    except Exception as e:
        logger.exception(f"Unexpected error processing file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred processing file {file.filename}.")
    finally:
        await file.close()

@router.post("/process-text", summary="Process Expense Text", description="Processes raw text input containing expense data using AI and stores it.")
async def process_expense_text(request: Request, text_input: Annotated[TextInput, Body(...)]):
    """
    Handles direct text input for expense processing using the injected DB collection.
    Sends text to service layer for AI processing and storage.
    """
    collection = get_expenses_collection(request)
    save_at_front = request.state.save_at_front
    logger.info(f"POST /process-text endpoint called with text: {text_input.text_input[:50]}... - SaveAtFront: {save_at_front}")
    
    if not text_input.text_input or not text_input.text_input.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")

    try:
        result = await expenses_service.process_text_input(collection, text_input.text_input, save_at_front=save_at_front)
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

    except ValueError as ve:
        logger.error(f"ValueError processing text input: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except ConnectionError as ce:
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
async def clear_database(request: Request):
    """API endpoint to clear all expenses from the database."""
    collection = get_expenses_collection(request)
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