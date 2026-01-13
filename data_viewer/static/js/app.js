/**
 * Main application logic for PocketBase Data Viewer
 */

const API_BASE = '/api';

let currentCollection = '';
let currentData = [];
let currentChart = null;  // TradingView chart instance

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCollections();
    setupEventListeners();
    setDefaultDates();
});

/**
 * Set default date range (last 7 days)
 */
function setDefaultDates() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);
    
    document.getElementById('end-date').value = formatDateTimeLocal(endDate);
    document.getElementById('start-date').value = formatDateTimeLocal(startDate);
}

/**
 * Format date for datetime-local input
 */
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    document.getElementById('collection-select').addEventListener('change', onCollectionChange);
    document.getElementById('load-data-btn').addEventListener('click', loadData);
    document.getElementById('download-csv-btn').addEventListener('click', downloadCSV);
}

/**
 * Load all collections from PocketBase
 */
async function loadCollections() {
    const select = document.getElementById('collection-select');
    
    console.log('Loading collections from PocketBase...');
    select.innerHTML = '<option value="">Loading collections...</option>';
    select.disabled = true;
    
    try {
        const startTime = Date.now();
        const response = await fetch(`${API_BASE}/collections`);
        const fetchTime = Date.now() - startTime;
        
        console.log(`Collections API response: ${response.status} (${fetchTime}ms)`);
        
        if (!response.ok) {
            let errorDetail = '';
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorData.message || '';
            } catch {
                errorDetail = await response.text().catch(() => 'Unknown error');
            }
            
            console.error(`Failed to load collections: ${response.status} - ${errorDetail}`);
            
            let errorMessage = 'Failed to load collections';
            if (response.status === 503) {
                // Service Unavailable - connection error
                errorMessage = errorDetail || 'Cannot connect to PocketBase server. Please start PocketBase first.';
            } else if (response.status === 500) {
                errorMessage = errorDetail || 'Server error - check if PocketBase is running';
            } else if (response.status === 401) {
                errorMessage = 'Authentication failed - check admin credentials in config.json';
            } else if (response.status === 404) {
                errorMessage = 'PocketBase not found - check server URL';
            } else {
                errorMessage = errorDetail || `Error ${response.status}: Failed to load collections`;
            }
            
            showError(errorMessage);
            select.innerHTML = `<option value="">${errorMessage}</option>`;
            select.disabled = false;
            return;
        }
        
        const collections = await response.json();
        console.log(`Received ${Array.isArray(collections) ? collections.length : 0} collections`);
        
        select.disabled = false;
        select.innerHTML = '<option value="">Select a collection...</option>';
        
        if (!collections || !Array.isArray(collections)) {
            console.error('Invalid collections response:', collections);
            showError('Invalid response from server');
            select.innerHTML = '<option value="">Error: Invalid response</option>';
            return;
        }
        
        if (collections.length === 0) {
            console.warn('No collections found in PocketBase');
            select.innerHTML = '<option value="">No collections found</option>';
            showError('No collections found in PocketBase. Please create collections first.');
            return;
        }
        
        // Populate dropdown with collections
        collections.forEach(col => {
            if (col && col.name) {
                const option = document.createElement('option');
                option.value = col.name;
                option.textContent = col.name;
                select.appendChild(option);
            }
        });
        
        console.log(`Successfully loaded ${collections.length} collections`);
        hideError();
        
    } catch (error) {
        console.error('Error loading collections:', error);
        const errorMessage = `Failed to load collections: ${error.message}`;
        showError(errorMessage);
        select.innerHTML = '<option value="">Error loading collections</option>';
        select.disabled = false;
    }
}

/**
 * Handle collection selection change
 */
async function onCollectionChange() {
    const collectionName = document.getElementById('collection-select').value;
    currentCollection = collectionName;
    
    // Clear previous data
    clearDisplay();
    
    if (!collectionName) {
        document.getElementById('symbol-filter-group').style.display = 'none';
        return;
    }
    
    // Show symbol filter group and set loading state
    const symbolFilterGroup = document.getElementById('symbol-filter-group');
    const symbolSelect = document.getElementById('symbol-select');
    
    symbolFilterGroup.style.display = 'block';
    symbolSelect.innerHTML = '<option value="">Loading symbols from database...</option>';
    symbolSelect.disabled = true;
    
    console.log(`Fetching symbols for collection: ${collectionName}`);
    
    try {
        const startTime = Date.now();
        const response = await fetch(`${API_BASE}/collections/${collectionName}/symbols`);
        const fetchTime = Date.now() - startTime;
        
        if (!response.ok) {
            const errorText = await response.text().catch(() => 'Unknown error');
            console.error(`Failed to load symbols: ${response.status} - ${errorText}`);
            symbolSelect.innerHTML = '<option value="">Error loading symbols</option>';
            symbolSelect.disabled = false;
            showError(`Failed to load symbols: ${response.status}`);
            return;
        }
        
        const symbols = await response.json();
        symbolSelect.disabled = false;
        
        console.log(`Received ${Array.isArray(symbols) ? symbols.length : 0} symbols in ${fetchTime}ms`);
        
        if (symbols && Array.isArray(symbols) && symbols.length > 0) {
            // Clear and populate symbol dropdown
            symbolSelect.innerHTML = '<option value="">All Symbols</option>';
            
            // Sort symbols for better UX
            const sortedSymbols = [...symbols].sort();
            
            sortedSymbols.forEach(symbol => {
                if (symbol && String(symbol).trim()) {  // Only add non-empty symbols
                    const option = document.createElement('option');
                    const symbolValue = String(symbol).trim();
                    option.value = symbolValue;
                    option.textContent = symbolValue;
                    symbolSelect.appendChild(option);
                }
            });
            
            console.log(`Successfully loaded ${sortedSymbols.length} symbols for ${collectionName}`);
            hideError();
        } else {
            // No symbols found - collection might not have symbol field or is empty
            symbolSelect.innerHTML = '<option value="">No symbols available</option>';
            console.log(`No symbols found for collection: ${collectionName}`);
            // Keep the dropdown visible but disabled to show the state
        }
        
    } catch (error) {
        console.error('Error loading symbols:', error);
        symbolSelect.innerHTML = '<option value="">Error loading symbols</option>';
        symbolSelect.disabled = false;
        showError(`Error loading symbols: ${error.message}`);
    }
}

/**
 * Load data from selected collection
 */
async function loadData() {
    const collectionName = document.getElementById('collection-select').value;
    if (!collectionName) {
        showError('Please select a collection');
        return;
    }
    
    const symbol = document.getElementById('symbol-select').value || null;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    // Show loading
    showLoading(true);
    hideError();
    clearDisplay();
    
    try {
        // Build query params
        const params = new URLSearchParams();
        if (symbol) params.append('symbol', symbol);
        if (startDate) {
            // Convert datetime-local to ISO string with IST timezone (+05:30)
            // datetime-local input is timezone-naive, we treat it as IST
            // Format: "2025-12-30T17:24" -> "2025-12-30T17:24:00+05:30"
            const isoString = startDate + ':00+05:30';
            params.append('start_date', isoString);
        }
        if (endDate) {
            const isoString = endDate + ':00+05:30';
            params.append('end_date', isoString);
        }
        params.append('limit', '10000');
        
        const response = await fetch(`${API_BASE}/data/${collectionName}?${params.toString()}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load data');
        }
        
        const result = await response.json();
        currentData = result.items || [];
        
        if (currentData.length === 0) {
            showError('No data found matching the filters');
            showLoading(false);
            return;
        }
        
        // Store metadata for display
        const metadata = {
            totalItems: result.totalItems || currentData.length,
            dateRange: result.dateRange || null
        };
        
        // Display data with metadata
        displayData(currentData, collectionName, metadata);
        
        document.getElementById('download-csv-btn').disabled = false;
        
        showLoading(false);
    } catch (error) {
        showError('Error loading data: ' + error.message);
        showLoading(false);
    }
}

/**
 * Display data (chart or table)
 */
function displayData(data, collectionName, metadata = {}) {
    // Show info
    const infoSection = document.getElementById('info-section');
    const recordCountEl = document.getElementById('record-count');
    
    // Build info text
    let infoText = `Loaded ${data.length} record(s) from ${collectionName}`;
    
    if (metadata.totalItems && metadata.totalItems !== data.length) {
        infoText += ` (Total available: ${metadata.totalItems})`;
    }
    
    // Add date range if available
    if (metadata.dateRange) {
        const dateRange = metadata.dateRange;
        if (dateRange.earliest || dateRange.latest) {
            infoText += '\n';
            if (dateRange.earliest && dateRange.latest) {
                infoText += `Date Range: ${dateRange.earliest} to ${dateRange.latest}`;
            } else if (dateRange.earliest) {
                infoText += `Earliest: ${dateRange.earliest}`;
            } else if (dateRange.latest) {
                infoText += `Latest: ${dateRange.latest}`;
            }
        }
    }
    
    if (recordCountEl) {
        recordCountEl.textContent = infoText;
        recordCountEl.style.whiteSpace = 'pre-line'; // Allow line breaks
    } else {
        console.error('record-count element not found');
    }
    
    if (infoSection) {
        infoSection.style.display = 'block';
    } else {
        console.error('info-section element not found');
    }
    
    // Determine display type
    if (collectionName === 'minute') {
        renderCandlestickChart(data);
    } else if (collectionName === 'ticks') {
        renderLineChart(data);
    } else {
        renderTable(data);
    }
}

/**
 * Clear display
 */
function clearDisplay() {
    const chartContainer = document.getElementById('chart-container');
    const tableContainer = document.getElementById('table-container');
    const infoSection = document.getElementById('info-section');
    
    if (chartContainer) {
        chartContainer.style.display = 'none';
    }
    
    if (tableContainer) {
        tableContainer.style.display = 'none';
    }
    
    if (infoSection) {
        infoSection.style.display = 'none';
    }
    
    if (currentChart) {
        // TradingView chart cleanup
        if (currentChart.remove) {
            currentChart.remove();
        }
        currentChart = null;
    }
    // Reset chart container
    const container = document.getElementById('chart-container');
    if (container) {
        container.innerHTML = '<div id="tradingview-chart" style="width:100%;height:600px;"></div>';
    }
}

/**
 * Download CSV
 */
async function downloadCSV() {
    if (!currentCollection || currentData.length === 0) {
        showError('No data to download');
        return;
    }
    
    const symbol = document.getElementById('symbol-select').value || null;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    // Build query params
    const params = new URLSearchParams();
    if (symbol) params.append('symbol', symbol);
    if (startDate) {
        // Convert datetime-local to ISO string with IST timezone (+05:30)
        const isoString = startDate + ':00+05:30';
        params.append('start_date', isoString);
    }
    if (endDate) {
        const isoString = endDate + ':00+05:30';
        params.append('end_date', isoString);
    }
    
    // Trigger download
    window.location.href = `${API_BASE}/download/${currentCollection}?${params.toString()}`;
}

/**
 * Show loading indicator
 */
function showLoading(show) {
    document.getElementById('loading-indicator').style.display = show ? 'block' : 'none';
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

/**
 * Hide error message
 */
function hideError() {
    document.getElementById('error-message').style.display = 'none';
}

