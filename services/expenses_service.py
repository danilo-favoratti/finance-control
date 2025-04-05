"""Service layer for handling expense-related logic."""
import logging
import csv
import io
import json
from fastapi import UploadFile
from typing import List, Dict, Any
from models.expense import Expense
from utils.openai_agent import process_text_with_agent, determine_sign_convention
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import ValidationError
from datetime import date, datetime

logger = logging.getLogger(__name__)

# --- Database Interaction Functions (Depend on collection passed from route) ---

async def get_all_expenses_from_db(collection: AsyncIOMotorCollection, sort_by: str = 'date', sort_order: int = -1) -> List[Expense]:
    """Fetches all expenses from the provided MongoDB collection, sorted as specified."""
    logger.info(f"Fetching all expenses from collection '{collection.name}', sorting by {sort_by} ({'desc' if sort_order == -1 else 'asc'})...")
    expenses = []
    try:
        cursor = collection.find().sort(sort_by, sort_order)
        async for doc in cursor:
            try:
                if '_id' in doc: doc['id'] = str(doc.pop('_id'))
                if 'date' in doc and isinstance(doc['date'], datetime):
                    doc['date'] = doc['date'].date()
                expenses.append(Expense(**doc))
            except ValidationError as e:
                logger.error(f"Data validation error for document ID {doc.get('id', 'N/A')}: {e}")
                continue
        logger.info(f"Fetched {len(expenses)} expenses successfully.")
    except Exception as e:
        logger.error(f"Database error fetching expenses: {e}")
        raise ConnectionError(f"Database error fetching expenses: {e}")
    return expenses

async def add_multiple_expenses_to_db(
    collection: AsyncIOMotorCollection,
    expenses_data: List[Dict[str, Any]],
    invert_signs: bool = False,
    save_at_front: bool = False
) -> Dict[str, Any]:
    """Adds multiple expense documents to the MongoDB collection after validation, or skips DB saving if save_at_front is True."""
    if not expenses_data:
        return {"status": "no_data", "added_count": 0, "skipped_count": 0, "errors": [], "duplicates_info": [], "inserted_ids": [], "processed_expenses": []}

    logger.info(f"Attempting to process {len(expenses_data)} expenses. Save to DB: {not save_at_front}")
    added_count = 0
    skipped_count = 0
    errors = []
    valid_expense_models = []
    skipped_duplicates_info = []

    for item_index, expense_data in enumerate(expenses_data):
        try:
            if 'id' in expense_data: del expense_data['id']
            if '_id' in expense_data: del expense_data['_id']
            
            date_input = expense_data.get('date')
            parsed_date = None
            if isinstance(date_input, str):
                try:
                    parsed_date = datetime.strptime(date_input, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Skipping item #{item_index} due to invalid date format: {date_input}")
                    errors.append(f"Item #{item_index} ({expense_data.get('description', '')[:20]}...): Invalid date format.")
                    continue
            elif isinstance(date_input, date):
                parsed_date = date_input
            elif date_input is not None:
                 logger.warning(f"Skipping item #{item_index} due to unexpected date type: {type(date_input)}")
                 errors.append(f"Item #{item_index} ({expense_data.get('description', '')[:20]}...): Invalid date type.")
                 continue

            if parsed_date is None:
                 logger.warning(f"Skipping item #{item_index} due to missing or unparseable date.")
                 errors.append(f"Item #{item_index} ({expense_data.get('description', '')[:20]}...): Missing or unparseable date.")
                 continue
            else:
                expense_data['date'] = parsed_date

            if not save_at_front:
                query_date = datetime.combine(parsed_date, datetime.min.time())
                duplicate_check_filter = {
                    "date": query_date,
                    "description": expense_data.get("description"),
                    "value": expense_data.get("value")
                }
                existing_doc = await collection.find_one(duplicate_check_filter)
                if existing_doc:
                    logger.warning(f"Skipping item #{item_index} as duplicate found (DB check): {duplicate_check_filter}")
                    skipped_count += 1
                    skipped_duplicates_info.append(f"DupDB: {expense_data.get('date')} - {expense_data.get('description', '')[:20]}...")
                    continue

            value_input = expense_data.get('value')
            try:
                expense_data['value'] = float(value_input)
            except (ValueError, TypeError):
                logger.warning(f"Skipping item #{item_index} due to invalid value: {value_input}")
                errors.append(f"Item #{item_index} ({expense_data.get('description', '')[:20]}...): Invalid or missing value.")
                continue
            
            if 'in_out' not in expense_data or expense_data['in_out'] not in ['in', 'out']:
                 expense_data['in_out'] = 'in' if expense_data['value'] >= 0 else 'out'
            
            expense_model = Expense(**expense_data)

            if invert_signs:
                expense_model.value *= -1
                expense_model.in_out = 'in' if expense_model.value >= 0 else 'out'

            valid_expense_models.append(expense_model)

        except ValidationError as e:
            logger.warning(f"Skipping item #{item_index} due to validation error: {e}")
            errors.append(f"Item #{item_index} ({expense_data.get('description', '')[:20]}...): Validation error - {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing item #{item_index}: {e}")
            errors.append(f"Item #{item_index} ({expense_data.get('description', '')[:20]}...): Unexpected processing error.")

    inserted_ids = []
    if not save_at_front and valid_expense_models:
        valid_expenses_for_db = []
        for model in valid_expense_models:
             expense_dict = model.model_dump(exclude_none=True)
             expense_dict['date'] = datetime.combine(model.date, datetime.min.time())
             valid_expenses_for_db.append(expense_dict)

        if valid_expenses_for_db:
             logger.info(f"Attempting bulk insert of {len(valid_expenses_for_db)} valid expenses into DB.")
             try:
                 result = await collection.insert_many(valid_expenses_for_db, ordered=False)
                 added_count = len(result.inserted_ids)
                 inserted_ids = [str(oid) for oid in result.inserted_ids]
                 logger.info(f"Bulk insert successful. Added {added_count} expenses to DB.")
             except Exception as e:
                 logger.error(f"Database error during bulk insert: {e}")
                 errors.append(f"Database error during bulk insert: {e}")
                 added_count = 0
        else:
             logger.info("No valid expenses to insert into DB.")

    elif save_at_front:
        logger.info("Skipping database insertion because SAVE_AT_FRONT is True.")
        added_count = 0
    else: 
         logger.info("No valid expenses were processed.")

    final_status = "error"
    if not errors and (added_count > 0 or save_at_front):
        final_status = "success"
    elif errors and (added_count > 0 or (save_at_front and valid_expense_models)):
        final_status = "partial_success"
    elif not valid_expense_models and not errors:
        final_status = "no_data"

    logger.info(f"Finished processing expenses. Status: {final_status}, Added to DB: {added_count}, Processed: {len(valid_expense_models)}, Errors: {len(errors)}, Skipped Dups (DB): {skipped_count}")

    processed_expenses_for_response = [
        expense.model_dump(mode='json') for expense in valid_expense_models
    ]

    return {
        "status": final_status,
        "added_count": added_count,
        "processed_count": len(valid_expense_models),
        "skipped_count": skipped_count,
        "errors": errors,
        "duplicates_info": skipped_duplicates_info,
        "inserted_ids": inserted_ids,
        "processed_expenses": processed_expenses_for_response
    }

async def delete_all_expenses(collection: AsyncIOMotorCollection) -> Dict[str, Any]:
    """Deletes all documents from the specified expense collection."""
    logger.warning(f"Attempting to delete ALL documents from collection '{collection.name}'.")
    try:
        result = await collection.delete_many({})
        deleted_count = result.deleted_count
        logger.info(f"Successfully deleted {deleted_count} documents from collection '{collection.name}'.")
        return {"status": "success", "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Database error during delete_many operation: {e}")
        raise ConnectionError(f"Database error deleting expenses: {e}")

async def clear_database(collection: AsyncIOMotorCollection) -> Dict[str, Any]:
    """Clears all documents from the specified expense collection."""
    return await delete_all_expenses(collection)

# --- File/Text Processing Functions --- 

async def process_uploaded_file(
    collection: AsyncIOMotorCollection,
    file: UploadFile,
    save_at_front: bool
) -> Dict[str, Any]:
    """
    Processes an uploaded file (CSV or TXT).
    - Reads file content.
    - Sends content to OpenAI agent for processing.
    - Validates extracted data.
    - Stores valid data in the database using the provided collection *unless* save_at_front is True.
    - Returns a dictionary summarizing the result including processed data.
    """
    logger.info(f"Processing uploaded file: {file.filename}, type: {file.content_type}, SaveAtFront: {save_at_front}")
    extracted_data = []
    try:
        content = await file.read()
        if not content:
             logger.warning(f"Uploaded file {file.filename} is empty.")
             return {"status": "error", "message": "File is empty.", "added_count": 0, "processed_count": 0, "errors": ["File is empty."], "processed_expenses": []}

        try:
            text_content = content.decode('utf-8')
            
            invert_signs_needed = await determine_sign_convention(text_content)
            
            logger.info(f"Extracting expense data from file (will invert signs: {invert_signs_needed})..." )
            extracted_data = await process_text_with_agent(text_content)
            logger.info(f"AI agent returned {len(extracted_data)} items from file.")
        except UnicodeDecodeError:
             logger.error(f"Could not decode file {file.filename}. Ensure UTF-8 encoding.")
             raise ValueError("Could not read file. Ensure UTF-8 encoding.")
        except ConnectionError as e:
            logger.error(f"AI Connection error processing file {file.filename}: {e}")
            raise
        
        if not extracted_data:
            logger.info(f"No data extracted from {file.filename}. Nothing to process.")
            return {"status": "success", "message": "No actionable data found in file.", "added_count": 0, "processed_count": 0, "errors": [], "processed_expenses": []}

        logger.info(f"Processing {len(extracted_data)} items from {file.filename} (SaveToDB: {not save_at_front})...")
        db_result = await add_multiple_expenses_to_db(
            collection,
            extracted_data,
            invert_signs=invert_signs_needed,
            save_at_front=save_at_front
        )
        return db_result

    except ValueError as ve:
        logger.error(f"ValueError processing file {file.filename}: {ve}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing file {file.filename}: {e}")
        raise ConnectionError(f"Unexpected server error processing file {file.filename}.")

async def process_text_input(
    collection: AsyncIOMotorCollection,
    text_data: str,
    save_at_front: bool
) -> Dict[str, Any]:
    """
    Processes raw text input using the OpenAI agent.
    - Sends text to OpenAI agent.
    - Validates extracted data.
    - Stores valid data in the database using the provided collection *unless* save_at_front is True.
    - Returns a dictionary summarizing the result including processed data.
    """
    logger.info(f"Processing text input (length: {len(text_data)}), SaveAtFront: {save_at_front}...")
    if not text_data or not text_data.strip():
        logger.warning("Received empty text input.")
        raise ValueError("Text input cannot be empty.")

    try:
        invert_signs_needed = await determine_sign_convention(text_data)

        extracted_data = await process_text_with_agent(text_data)
        logger.info(f"AI agent returned {len(extracted_data)} items from text input.")
        
        if not extracted_data:
            logger.info("AI agent returned no data from text input. Nothing to process.")
            return {"status": "success", "message": "No actionable data found in text.", "added_count": 0, "processed_count": 0, "errors": [], "processed_expenses": []}

        logger.info(f"Processing {len(extracted_data)} items from text input (SaveToDB: {not save_at_front})...")
        db_result = await add_multiple_expenses_to_db(
            collection,
            extracted_data,
            invert_signs=invert_signs_needed,
            save_at_front=save_at_front
        )
        return db_result
    except ConnectionError as e: 
         logger.error(f"AI/DB Connection error processing text input: {e}")
         raise
    except Exception as e:
        logger.exception(f"Unexpected error processing text input: {e}")
        raise ConnectionError("Unexpected server error processing text input.") 

# Remove the old placeholder functions if they exist
# async def get_all() -> List[Dict[str, Any]]:
#     raise NotImplementedError("This function is deprecated. Use get_all_expenses_from_db.")

# Example of how to handle ObjectId if needed elsewhere (e.g., update/delete)
# async def get_expense_by_id(expense_id: str) -> Expense | None:
#     try:
#         obj_id = ObjectId(expense_id)
#         document = await expenses_collection.find_one({"_id": obj_id})
#         if document:
#             document['_id'] = str(document['_id'])
#             if isinstance(document.get('date'), datetime):
#                  document['date'] = document['date'].date()
#             return Expense(**document)
#         return None
#     except Exception as e:
#         logger.error(f"Error fetching expense by ID {expense_id}: {e}")
#         return None 