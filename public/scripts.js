// Frontend JavaScript for Finance Manager

$(document).ready(function() {
    console.log("Document ready. Initializing...");

    const API_BASE_URL = "/api"; // Assuming backend is served relative to frontend
    let expensesData = []; // To store fetched expenses
    let sortColumn = 'date';
    let sortDirection = 'desc';

    // --- DOM Elements ---
    const $dropZone = $('#drop-zone');
    const $fileInput = $('#file-input');
    const $fileStatus = $('#file-upload-status');
    const $textInput = $('#text-input');
    const $submitTextBtn = $('#submit-text-btn');
    const $textStatus = $('#text-input-status');
    const $expensesTableBody = $('#expenses-table-body');
    const $loadStatus = $('#load-status');
    const $searchInput = $('#search-input');
    const $tableHeaders = $('#expenses-table thead th');

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
        $expensesTableBody.empty(); // Clear existing rows
        if (!data || data.length === 0) {
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

        if (filteredData.length === 0 && data.length > 0) {
             $expensesTableBody.append('<tr><td colspan="3" style="text-align:center;">No expenses match your search.</td></tr>');
        } else {
            filteredData.forEach(expense => {
                const rowClass = expense.value >= 0 ? 'expense-income' : '';
                const row = `<tr class="${rowClass}">
                                <td>${expense.date}</td>
                                <td>${expense.description}</td>
                                <td>${expense.value.toFixed(2)}</td>
                            </tr>`;
                $expensesTableBody.append(row);
            });
        }
    }

    // --- API Calls ---
    function fetchExpenses() {
        displayStatus($loadStatus, 'Loading expenses...', 'loading');
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
            // The `success` handler might be called even for HTTP status codes like 207 (Multi-Status)
            // depending on jQuery version and server response. Check status inside.
            success: function(response, textStatus, jqXHR) { 
                let message = `File ${file.name} processed.`;
                let statusType = 'success';

                if (response && response.status) {
                    if (response.status === 'success') {
                        message = `Successfully processed ${file.name}. Added ${response.added_count || 0} expenses. Refreshing list...`;
                    } else if (response.status === 'partial_success') {
                        message = `Partially processed ${file.name}. Added ${response.added_count || 0} expenses. ${response.errors?.length || 0} errors occurred. Refreshing list...`;
                        // Optionally list errors if desired, might make the message too long
                        // if (response.errors && response.errors.length > 0) {
                        //    message += " Errors: " + response.errors.join(", ");
                        // }
                        statusType = 'warning'; // Use warning for partial success
                    } else if (response.status === 'error' || (response.status === 'no_data')) {
                        message = `Processed ${file.name}, but no expenses were added.`;
                        if (response.errors && response.errors.length > 0) {
                            message += ` Errors: ${response.errors.join(", ")}`;
                        }
                        statusType = 'error';
                    } else if (response.message) { // Handle cases where only a message is returned
                         message = response.message;
                         statusType = jqXHR.status >= 400 ? 'error' : 'success'; // Guess based on HTTP status
                    }
                }
                
                displayStatus($fileStatus, message, statusType);
                fetchExpenses(); // Refresh the table regardless of partial success
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

                if (response && response.status) {
                     if (response.status === 'success') {
                        message = `Successfully processed text. Added ${response.added_count || 0} expenses. Refreshing list...`;
                    } else if (response.status === 'partial_success') {
                        message = `Partially processed text. Added ${response.added_count || 0} expenses. ${response.errors?.length || 0} errors occurred. Refreshing list...`;
                         // Optionally list errors
                        // if (response.errors && response.errors.length > 0) {
                        //    message += " Errors: " + response.errors.join(", ");
                        // }
                        statusType = 'warning'; 
                    } else if (response.status === 'error' || (response.status === 'no_data')) {
                        message = `Processed text, but no expenses were added.`;
                        if (response.errors && response.errors.length > 0) {
                            message += ` Errors: ${response.errors.join(", ")}`;
                        }
                        statusType = 'error';
                    } else if (response.message) {
                         message = response.message;
                         statusType = jqXHR.status >= 400 ? 'error' : 'success';
                    }
                }

                displayStatus($textStatus, message, statusType);
                if (statusType !== 'error') {
                   $textInput.val(''); // Clear textarea only on success/partial success
                }
                fetchExpenses(); // Refresh the table
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
    function cleanDatabase() {
        if (!confirm("Are you sure you want to delete ALL expenses from the database? This cannot be undone.")) {
            return;
        }
        displayStatus($debugStatus, 'Cleaning database...', 'loading');
        
        $.ajax({
            url: `${API_BASE_URL}/expenses/all`, // The new DELETE endpoint
            method: 'DELETE',
            success: function(response) {
                const message = `Database cleaned successfully. Deleted ${response.deleted_count || 0} items. Refreshing...`;
                displayStatus($debugStatus, message, 'success');
                fetchExpenses(); // Refresh the main expenses table
                // Optionally hide menu after success
                // setTimeout(() => $debugMenu.addClass('hidden'), 2000);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error("Error cleaning database:", textStatus, errorThrown, jqXHR.responseText);
                const errorDetail = `Error cleaning database: ${jqXHR.responseJSON?.detail || jqXHR.responseText || errorThrown}`;
                displayStatus($debugStatus, errorDetail, 'error');
            }
        });
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
    $submitTextBtn.on('click', function() {
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
        cleanDatabase();
    });

    // --- Initial Load ---
    fetchExpenses();
}); 