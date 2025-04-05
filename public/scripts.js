// Frontend JavaScript for Finance Manager

$(document).ready(function() {
    console.log("Document ready. Initializing...");

    // --- Configuration --- 
    // Set this to true to enable saving/loading from local storage instead of the backend DB
    const SAVE_AT_FRONT_ENABLED = true; 
    const LOCAL_STORAGE_KEY = 'expenses';

    const API_BASE_URL = "/api"; // Assuming backend is served relative to frontend
    let expensesData = []; // To store fetched/loaded expenses
    let sortColumn = 'date';
    let sortDirection = 'desc';

    // --- DOM Elements ---
    const $dropZone = $('#drop-zone');
    const $fileInput = $('#file-input');
    const $fileStatus = $('#file-upload-status');
    const $textInput = $('#text-input');
    const $processTextBtn = $('#process-text-btn');
    const $textStatus = $('#text-input-status');
    const $expensesTableBody = $('#expenses-table-body');
    const $loadStatus = $('#load-status');
    const $searchInput = $('#search-input');
    const $tableHeaders = $('#expenses-table thead th');
    const $expensesHeader = $('#expenses-section h2');
    const $expensesCount = $('#expenses-count');
    const $expensesDisplayedCountSpan = $('#expenses-displayed-count');
    const $expensesTotalCountSpan = $('#expenses-total-count');
    const $expensesSumOutSpan = $('#expenses-sum-out');
    const $expensesSumInSpan = $('#expenses-sum-in');
    const $expensesSumNetSpan = $('#expenses-sum-net');

    // Debug Menu Elements
    const $debugButton = $('#debug-button');
    const $debugMenu = $('#debug-menu');
    const $cleanDbBtn = $('#clean-db-btn');
    const $closeDebugBtn = $('#close-debug-btn');
    const $debugStatus = $('#debug-status');

    // --- Utility Functions ---
    function displayStatus($element, message, type) {
        $element.text(message).removeClass('status-success status-error status-loading').addClass(`status-${type}`);
    }

    function renderTable(data) {
        $expensesTableBody.empty();

        const totalCount = data ? data.length : 0;
        $expensesTotalCountSpan.text(`${totalCount} total`);

        // Clear stats if no initial data
        if (totalCount === 0) {
            $expensesCount.text(0);
            $expensesSumOutSpan.text('Exp: $0.00');
            $expensesSumInSpan.text('Inc: $0.00');
            $expensesSumNetSpan.text('Net: $0.00');
            $expensesTableBody.append('<tr><td colspan="3" style="text-align:center;">No expenses found.</td></tr>');
            return;
        }

        // Sort data before rendering
        data.sort((a, b) => {
            let valA = a[sortColumn];
            let valB = b[sortColumn];

            // Basic type handling (extend as needed)
            if (sortColumn === 'date') {
                valA = new Date(valA);
                valB = new Date(valB);
            }
            if (sortColumn === 'value') {
                valA = parseFloat(a.value);
                valB = parseFloat(b.value);
            }

            let comparison = 0;
            if (valA > valB) comparison = 1;
            else if (valA < valB) comparison = -1;
            
            return sortDirection === 'asc' ? comparison : (comparison * -1);
        });

        // Apply search filter
        const searchTerm = $searchInput.val().toLowerCase();
        const filteredData = searchTerm
            ? data.filter(item => 
                  (item.date && String(item.date).toLowerCase().includes(searchTerm)) ||
                  (item.description && String(item.description).toLowerCase().includes(searchTerm)) ||
                  (item.value !== null && item.value !== undefined && String(item.value).toLowerCase().includes(searchTerm))
              )
            : data;

        // *** UPDATE STATS BASED ON FILTERED DATA ***
        const displayedCount = filteredData.length;
        $expensesCount.text(displayedCount);

        let sumOut = 0;
        let sumIn = 0;
        let sumNet = 0;

        filteredData.forEach(expense => {
            const value = typeof expense.value === 'number' ? expense.value : parseFloat(expense.value);
            if (!isNaN(value)) {
                sumNet += value;
                if (value < 0) {
                    sumOut += value;
                } else {
                    sumIn += value;
                }
            }
        });

        // Format currency using toLocaleString
        const formattedSumOut = sumOut.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const formattedSumIn = sumIn.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const formattedSumNet = sumNet.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

        // Update stat spans
        $expensesSumOutSpan.text(`Exp: $${formattedSumOut}`);
        $expensesSumInSpan.text(`Inc: $${formattedSumIn}`);
        $expensesSumNetSpan.text(`Net: $${formattedSumNet}`);

        // Render rows
        if (displayedCount === 0 && data.length > 0) {
             $expensesTableBody.append('<tr><td colspan="3" style="text-align:center;">No expenses match your search.</td></tr>');
        } else {
            filteredData.forEach(expense => {
                const rowClass = expense.value >= 0 ? 'expense-income' : '';
                const value = typeof expense.value === 'number' ? expense.value : parseFloat(expense.value);
                
                // Create elements safely using jQuery and .text()
                const $row = $('<tr>').addClass(rowClass);
                const $dateCell = $('<td>').text(expense.date); // Use .text() for safety
                const $descCell = $('<td>').text(expense.description); // Use .text() for safety
                const $valueCell = $('<td>').text(isNaN(value) ? 'N/A' : value.toFixed(2)); 
                
                // Add positive-value class if value is positive
                if (value > 0) {
                    $row.addClass('positive-value');
                }
                
                $row.append($dateCell, $descCell, $valueCell);
                $expensesTableBody.append($row);
            });
        }
    }

    // --- API Calls & Local Storage Logic ---

    // Function to load expenses from Local Storage
    function loadExpensesFromLocalStorage() {
        try {
            const storedData = localStorage.getItem(LOCAL_STORAGE_KEY);
            if (storedData) {
                expensesData = JSON.parse(storedData);
                // Basic validation: ensure it's an array
                if (!Array.isArray(expensesData)) {
                    console.warn("Invalid data found in local storage, expected an array. Resetting.");
                    expensesData = [];
                    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(expensesData));
                }
                console.log(`Loaded ${expensesData.length} expenses from local storage.`);
            } else {
                expensesData = [];
                console.log("No expenses found in local storage.");
            }
        } catch (error) {
            console.error("Error loading or parsing expenses from local storage:", error);
            expensesData = []; // Reset on error
        }
        renderTable(expensesData);
        displayStatus($loadStatus, '', 'success'); // Clear status
    }

    // Function to save expenses to Local Storage
    function saveExpensesToLocalStorage(newExpenses) {
        if (!Array.isArray(newExpenses)) {
            console.error("Attempted to save non-array data to local storage:", newExpenses);
            return false;
        }
        try {
            // Always store the complete, updated list
            localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(newExpenses));
            console.log(`Saved ${newExpenses.length} total expenses to local storage.`);
            return true;
        } catch (error) {
            console.error("Error saving expenses to local storage:", error);
            // Optionally display an error to the user
            return false;
        }
    }

    // Function to add new processed expenses to local storage data
    function addProcessedExpensesToLocal(processedExpenses) {
        console.log("[addProcessedExpensesToLocal] Called with:", processedExpenses);
        if (!processedExpenses || processedExpenses.length === 0) {
            console.log("[addProcessedExpensesToLocal] No processed expenses to add.");
            return; // Nothing to add
        }
        
        // Load current local data
        let currentLocalExpenses = [];
        try {
            const storedData = localStorage.getItem(LOCAL_STORAGE_KEY);
            console.log("[addProcessedExpensesToLocal] Current raw data from local storage:", storedData);
            if (storedData) {
                const parsedData = JSON.parse(storedData);
                if(Array.isArray(parsedData)) {
                    currentLocalExpenses = parsedData;
                    console.log("[addProcessedExpensesToLocal] Parsed current local expenses:", currentLocalExpenses);
                }
            }
        } catch (error) {
            console.error("[addProcessedExpensesToLocal] Error reading local storage before adding:", error);
        }

        // Combine and save (simple append for now, could add duplicate checks here too if needed)
        const updatedExpenses = [...currentLocalExpenses, ...processedExpenses];
        console.log("[addProcessedExpensesToLocal] Combined expenses for saving:", updatedExpenses);
        if (saveExpensesToLocalStorage(updatedExpenses)) {
            expensesData = updatedExpenses; // Update the in-memory store
            console.log("[addProcessedExpensesToLocal] Successfully saved. Rendering table.");
            renderTable(expensesData); // Re-render the table with combined data
        } else {
            console.error("[addProcessedExpensesToLocal] Failed to save updated expenses to local storage.");
        }
    }

    function fetchExpensesFromAPI() {
        displayStatus($loadStatus, 'Loading expenses from API...', 'loading');
        $.ajax({
            url: `${API_BASE_URL}/expenses`,
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                expensesData = data;
                renderTable(expensesData);
                displayStatus($loadStatus, '', 'success'); // Clear status on success
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error("Error fetching expenses:", textStatus, errorThrown, jqXHR.responseText);
                expensesData = []; // Clear data on error
                renderTable(expensesData);
                displayStatus($loadStatus, `Error loading expenses: ${jqXHR.responseJSON?.detail || errorThrown}`, 'error');
            }
        });
    }

    // Unified fetch/load function
    function loadInitialExpenses() {
        if (SAVE_AT_FRONT_ENABLED) {
            console.log("Loading expenses from Local Storage...");
            loadExpensesFromLocalStorage();
        } else {
            console.log("Fetching expenses from API...");
            fetchExpensesFromAPI();
        }
    }

    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        displayStatus($fileStatus, `Uploading ${file.name}...`, 'loading');

        $.ajax({
            url: `${API_BASE_URL}/upload-file`,
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response, textStatus, jqXHR) { 
                let message = `File ${file.name} processed.`;
                let statusType = 'success';

                // Response structure from backend is now consistent
                const addedToDbCount = response.added_count || 0;
                const processedCount = response.processed_count || 0;
                const skippedCount = response.skipped_count || 0;
                const errorsCount = response.errors?.length || 0;
                const processedExpenses = response.processed_expenses || []; // IMPORTANT: Define processedExpenses here too!

                if (response.status === 'success') {
                    if (SAVE_AT_FRONT_ENABLED) {
                        message = `Successfully processed ${file.name}. Processed ${processedCount} items (saved locally).`;
                    } else {
                        message = `Successfully processed ${file.name}. Added ${addedToDbCount} to DB.`;
                    }
                    if (skippedCount > 0) message += ` Skipped ${skippedCount} duplicates.`;
                    message += " Updating list...";
                } else if (response.status === 'partial_success') {
                    if (SAVE_AT_FRONT_ENABLED) {
                         message = `Partially processed ${file.name}. Processed ${processedCount} items (saved locally).`;
                    } else {
                         message = `Partially processed ${file.name}. Added ${addedToDbCount} to DB. Processed ${processedCount} total.`;
                    }
                    if (skippedCount > 0) message += ` Skipped ${skippedCount} duplicates.`;
                    if (errorsCount > 0) message += ` ${errorsCount} errors occurred.`;
                    message += " Updating list...";
                    statusType = 'warning';
                } else if (response.status === 'error' || response.status === 'no_data') {
                    message = `Processed ${file.name}, but no expenses were added/processed.`;
                    if (skippedCount > 0) message += ` Skipped ${skippedCount} duplicates.`;
                    if (errorsCount > 0) {
                        message += ` Errors: ${response.errors.join(", ")}`;
                    }
                    statusType = 'error';
                } else if (response.message) {
                     message = response.message;
                     statusType = jqXHR.status >= 400 ? 'error' : 'success';
                }

                displayStatus($fileStatus, message, statusType);

                // Refresh logic
                console.log(`[uploadFile Success] SAVE_AT_FRONT_ENABLED: ${SAVE_AT_FRONT_ENABLED}, Status: ${statusType}, Processed Count: ${processedExpenses.length}`);
                if (SAVE_AT_FRONT_ENABLED) {
                    if (statusType !== 'error' && processedExpenses.length > 0) {
                        addProcessedExpensesToLocal(processedExpenses); // Add new items to local storage and re-render
                    } else if (statusType === 'error') {
                         // Do nothing on error, table already shows old data
                        console.log("[uploadFile Success] Skipping local storage update due to error status.");
                    } else {
                        console.log("[uploadFile Success] No new processed expenses or non-error status. Re-rendering table with existing data.");
                        renderTable(expensesData); // Re-render even if no new data processed (e.g., only duplicates)
                    }
                } else {
                    fetchExpensesFromAPI(); // Refresh the table from API if saving to backend
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error("Error uploading file:", textStatus, errorThrown, jqXHR.responseText);
                let errorDetail = `Error uploading ${file.name}.`;
                if (jqXHR.responseJSON && jqXHR.responseJSON.detail) {
                    // If detail is the dictionary we expect from the backend
                    if (typeof jqXHR.responseJSON.detail === 'object' && jqXHR.responseJSON.detail !== null) {
                         const detail = jqXHR.responseJSON.detail;
                         errorDetail = `Error processing ${file.name}: ${detail.message || 'Processing failed.'}`;
                         if (detail.errors && detail.errors.length > 0) {
                            errorDetail += ` Details: ${detail.errors.join(", ")}`;
                         }
                    } else {
                         // If detail is just a string
                         errorDetail += ` ${jqXHR.responseJSON.detail}`;
                    }
                } else if (errorThrown) {
                    errorDetail += ` ${errorThrown}`;
                }
                displayStatus($fileStatus, errorDetail, 'error');
            }
        });
    }

    function processText(text) {
        if (!text.trim()) {
            displayStatus($textStatus, 'Text input cannot be empty.', 'error');
            return;
        }
        displayStatus($textStatus, 'Processing text...', 'loading');

        $.ajax({
            url: `${API_BASE_URL}/process-text`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ text_input: text }),
            success: function(response, textStatus, jqXHR) {
                let message = "Text processed.";
                let statusType = 'success';
                let processedExpenses = []; // Define EARLY

                // Extract details from response
                const addedToDbCount = response.added_count || 0;
                const processedCount = response.processed_count || 0;
                const skippedCount = response.skipped_count || 0;
                const errorsCount = response.errors?.length || 0;
                processedExpenses = response.processed_expenses || []; // Assign HERE

                // Determine message based on status and save mode
                if (response.status === 'success') {
                    message = `Successfully processed text. Added ${addedToDbCount} to DB.`;
                    if (skippedCount > 0) message += ` Skipped ${skippedCount} duplicates.`;
                    message += " Updating list...";
                    renderTable(expensesData); // Re-render even if no new data processed
                } else if (response.status === 'partial_success') {
                    message = `Partially processed text. Added ${addedToDbCount} to DB. Processed ${processedCount} total.`;
                    if (skippedCount > 0) message += ` Skipped ${skippedCount} duplicates.`;
                    if (errorsCount > 0) message += ` ${errorsCount} errors occurred.`;
                    message += " Updating list...";
                    statusType = 'warning'; 
                    renderTable(expensesData); // Re-render even if no new data processed
                } else if (response.status === 'error' || (response.status === 'no_data')) {
                    message = `Processed text, but no expenses were added/processed.`;
                    if (skippedCount > 0) message += ` Skipped ${skippedCount} duplicates.`;
                    if (errorsCount > 0) {
                        message += ` Errors: ${response.errors.join(", ")}`;
                    }
                    statusType = 'error';
                    renderTable(expensesData); // Re-render even if no new data processed
                } else if (response.message) {
                     message = response.message;
                     statusType = jqXHR.status >= 400 ? 'error' : 'success';
                }

                displayStatus($textStatus, message, statusType);
                if (statusType !== 'error') {
                   $textInput.val(''); // Clear textarea only on success/partial success
                }
                
                // Refresh logic
                console.log(`[processText Success] SAVE_AT_FRONT_ENABLED: ${SAVE_AT_FRONT_ENABLED}, Status: ${statusType}, Processed Count: ${processedExpenses.length}`);
                if (SAVE_AT_FRONT_ENABLED) {
                    if (statusType !== 'error' && processedExpenses.length > 0) {
                        addProcessedExpensesToLocal(processedExpenses); // Add new items to local storage and re-render
                    } else if (statusType === 'error') {
                         // Do nothing on error, table already shows old data
                        console.log("[processText Success] Skipping local storage update due to error status.");
                    } else {
                        console.log("[processText Success] No new processed expenses or non-error status. Re-rendering table with existing data.");
                        renderTable(expensesData); // Re-render even if no new data processed
                    }
                } else {
                    fetchExpensesFromAPI(); // Refresh the table from API if saving to backend
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error("Error processing text:", textStatus, errorThrown, jqXHR.responseText);
                let errorDetail = "Error processing text.";
                 if (jqXHR.responseJSON && jqXHR.responseJSON.detail) {
                    if (typeof jqXHR.responseJSON.detail === 'object' && jqXHR.responseJSON.detail !== null) {
                         const detail = jqXHR.responseJSON.detail;
                         errorDetail = `Error processing text: ${detail.message || 'Processing failed.'}`;
                         if (detail.errors && detail.errors.length > 0) {
                            errorDetail += ` Details: ${detail.errors.join(", ")}`;
                         }
                    } else {
                         errorDetail += ` ${jqXHR.responseJSON.detail}`;
                    }
                } else if (errorThrown) {
                    errorDetail += ` ${errorThrown}`;
                }
                displayStatus($textStatus, errorDetail, 'error');
            }
        });
    }

    // --- Debug Functions ---
    async function clearDatabaseOrLocalStorage() {
        displayStatus($debugStatus, 'Clearing data...', 'loading');
        if (SAVE_AT_FRONT_ENABLED) {
            try {
                localStorage.removeItem(LOCAL_STORAGE_KEY);
                expensesData = []; // Clear in-memory array
                renderTable(expensesData); // Update the table
                displayStatus($debugStatus, 'Local storage cleared successfully!', 'success');
                console.log("Local storage cleared.");
                alert('Local storage cleared successfully!'); // User feedback
            } catch (error) {
                console.error("Error clearing local storage:", error);
                displayStatus($debugStatus, 'Error clearing local storage.', 'error');
                alert('Error clearing local storage.');
            }
        } else {
            // Original logic to clear backend DB
            try {
                const response = await fetch('/api/expenses/clear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const result = await response.json();
                    displayStatus($debugStatus, `Database cleared: ${result.deleted_count} items removed.`, 'success');
                    alert('Database cleared successfully!');
                    // Refresh expenses list (will fetch from API)
                    loadInitialExpenses(); 
                } else {
                    const error = await response.json();
                    console.error("Error clearing database:", error);
                    displayStatus($debugStatus, `Error clearing database: ${error.detail || 'Unknown error'}`, 'error');
                    alert(`Error clearing database: ${error.detail}`);
                }
            } catch (error) {
                console.error('Error during clear database request:', error);
                 displayStatus($debugStatus, 'Network error clearing database.', 'error');
                alert('Error clearing database. Check network connection.');
            }
        }
    }

    // --- Event Handlers ---

    // Drag and Drop
    $dropZone.on('dragover dragenter', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('dragover');
    });

    $dropZone.on('dragleave drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
    });

    $dropZone.on('drop', function(e) {
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            // Basic validation (could add more checks for type/size)
            uploadFile(files[0]);
        }
    });

    // Click to select file
    $dropZone.on('click', function(e) {
        if (e.target !== $fileInput[0]) {
            $fileInput.click();
            e.stopPropagation();
        }
    });

    $fileInput.on('change', function() {
        if (this.files.length > 0) {
            uploadFile(this.files[0]);
            $(this).val(''); // Reset file input
        }
    });

    // Text Input Submit
    $processTextBtn.on('click', function() {
        processText($textInput.val());
    });

    // Table Sorting
    $tableHeaders.on('click', function() {
        const newSortColumn = $(this).data('sort');

        // Clear existing sort indicators
        $tableHeaders.removeClass('sort-asc sort-desc');

        if (sortColumn === newSortColumn) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortColumn = newSortColumn;
            sortDirection = 'asc'; // Default to ascending on new column
        }
        
        // Add new sort indicator
        $(this).addClass(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
        
        // TODO: Add visual indicators for sort column/direction - Now handled by adding classes
        renderTable(expensesData);
    });

    // Search Input
    $searchInput.on('keyup', function() {
        renderTable(expensesData); // Re-render table with current search term
    });

    // Debug Menu Handlers
    $debugButton.on('click', function() {
        $debugMenu.toggleClass('hidden');
    });

    $closeDebugBtn.on('click', function() {
        $debugMenu.addClass('hidden');
        $debugStatus.text('').removeClass('status-success status-error status-loading'); // Clear status on close
    });

    $cleanDbBtn.on('click', function() {
        // Use the updated function name
        clearDatabaseOrLocalStorage();
    });

    // Export functionality
    function exportToCSV(expenses) {
        const headers = ['Date', 'Description', 'Value'];
        const csvContent = [
            headers.join(','),
            ...expenses.map(expense => [
                expense.date,
                `"${expense.description.replace(/"/g, '""')}"`,
                expense.value
            ].join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `expenses_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
    }

    function exportToXLS(expenses) {
        const headers = ['Date', 'Description', 'Value'];
        const xlsContent = [
            headers.join('\t'),
            ...expenses.map(expense => [
                expense.date,
                expense.description,
                expense.value
            ].join('\t'))
        ].join('\n');

        const blob = new Blob([xlsContent], { type: 'application/vnd.ms-excel' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `expenses_${new Date().toISOString().split('T')[0]}.xls`;
        link.click();
    }

    // Add event listeners for export buttons
    $(document).ready(function() {
        const exportModal = $('#export-modal');
        
        // Show modal when export button is clicked
        $('#export-btn').click(function() {
            exportModal.show();
        });

        // Close modal when close button is clicked
        $('#close-export-modal').click(function() {
            exportModal.hide();
        });

        // Close modal when clicking outside
        $(window).click(function(event) {
            if (event.target === exportModal[0]) {
                exportModal.hide();
            }
        });

        // Handle export options
        $('#export-csv').click(function() {
            exportToCSV(expensesData);
            exportModal.hide();
        });

        $('#export-xls').click(function() {
            exportToXLS(expensesData);
            exportModal.hide();
        });
    });

    // --- Initial Load ---
    console.log(`Initializing with SAVE_AT_FRONT_ENABLED = ${SAVE_AT_FRONT_ENABLED}`);
    loadInitialExpenses(); // Use the unified load function
}); 