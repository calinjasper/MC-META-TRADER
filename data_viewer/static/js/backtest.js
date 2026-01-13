/**
 * Backtester JavaScript
 * Handles indicator loading, settings form generation, backtest execution, and results display
 */

const API_BASE = '/api/backtest';

let indicators = [];
let currentChart = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSymbols();
    loadIndicators();
    setDefaultDates();
    setupEventListeners();
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
    document.getElementById('indicator-select').addEventListener('change', onIndicatorChange);
    document.getElementById('position-sizing-type').addEventListener('change', onPositionSizingTypeChange);
    document.getElementById('run-backtest-btn').addEventListener('click', runBacktest);
    document.getElementById('add-buy-condition-btn').addEventListener('click', () => addCondition('buy'));
    document.getElementById('add-sell-condition-btn').addEventListener('click', () => addCondition('sell'));
}

/**
 * Load symbols from API
 */
async function loadSymbols() {
    const select = document.getElementById('symbol-select');
    
    try {
        const response = await fetch('/api/collections/minute/symbols');
        if (!response.ok) {
            throw new Error('Failed to load symbols');
        }
        
        const symbols = await response.json();
        select.innerHTML = '<option value="">Select Symbol</option>';
        
        symbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading symbols:', error);
        showError('Failed to load symbols: ' + error.message);
        select.innerHTML = '<option value="">Error loading symbols</option>';
    }
}

/**
 * Load available indicators
 */
async function loadIndicators() {
    const select = document.getElementById('indicator-select');
    
    try {
        const response = await fetch(`${API_BASE}/indicators`);
        if (!response.ok) {
            throw new Error('Failed to load indicators');
        }
        
        indicators = await response.json();
        select.innerHTML = '<option value="">Select Indicator</option>';
        
        indicators.forEach(indicator => {
            const option = document.createElement('option');
            option.value = indicator.name;
            option.textContent = `${indicator.name}${indicator.description ? ' - ' + indicator.description : ''}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading indicators:', error);
        showError('Failed to load indicators: ' + error.message);
        select.innerHTML = '<option value="">Error loading indicators</option>';
    }
}

// Store current indicator name and conditions
let currentIndicatorName = '';
let buyConditions = [];
let sellConditions = [];

/**
 * Handle indicator selection change
 */
async function onIndicatorChange() {
    const indicatorName = document.getElementById('indicator-select').value;
    const settingsPanel = document.getElementById('indicator-settings-panel');
    const settingsForm = document.getElementById('indicator-settings-form');
    const conditionBuilderSection = document.getElementById('condition-builder-section');
    const buyConditionsContainer = document.getElementById('buy-conditions-container');
    const sellConditionsContainer = document.getElementById('sell-conditions-container');
    
    currentIndicatorName = indicatorName;
    buyConditions = [];
    sellConditions = [];
    
    if (!indicatorName) {
        settingsPanel.style.display = 'none';
        return;
    }
    
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/indicator/${indicatorName}/settings`);
        if (!response.ok) {
            throw new Error('Failed to load indicator settings');
        }
        
        const schema = await response.json();
        settingsForm.innerHTML = '';
        
        // Always show settings panel when indicator is selected
        settingsPanel.style.display = 'block';
        
        // Render basic settings
        if (schema.parameters && schema.parameters.length > 0) {
            schema.parameters.forEach(param => {
                // Skip name and symbol as they're handled separately
                if (param.name === 'name' || param.name === 'symbol') {
                    return;
                }
                
                const defaultValue = schema.defaults[param.name];
                
                // Special handling for ema_periods - show 4 separate inputs
                if (param.name === 'ema_periods' && (param.type === 'object' || (defaultValue !== undefined && typeof defaultValue === 'object'))) {
                    const emaGroup = document.createElement('div');
                    emaGroup.className = 'form-group ema-periods-group';
                    
                    const label = document.createElement('label');
                    label.textContent = 'EMA Periods';
                    emaGroup.appendChild(label);
                    
                    const emaGrid = document.createElement('div');
                    emaGrid.className = 'ema-periods-grid';
                    
                    const defaultPeriods = defaultValue || { ema_1: 20, ema_2: 50, ema_3: 100, ema_4: 200 };
                    
                    for (let i = 1; i <= 4; i++) {
                        const emaField = document.createElement('div');
                        emaField.className = 'ema-period-field';
                        
                        const emaLabel = document.createElement('label');
                        emaLabel.textContent = `EMA ${i}:`;
                        emaLabel.setAttribute('for', `setting-ema_${i}`);
                        
                        const emaInput = document.createElement('input');
                        emaInput.type = 'number';
                        emaInput.id = `setting-ema_${i}`;
                        emaInput.min = 1;
                        emaInput.max = 500;
                        emaInput.step = 1;
                        emaInput.value = defaultPeriods[`ema_${i}`] || (i === 1 ? 20 : i === 2 ? 50 : i === 3 ? 100 : 200);
                        
                        emaField.appendChild(emaLabel);
                        emaField.appendChild(emaInput);
                        emaGrid.appendChild(emaField);
                    }
                    
                    emaGroup.appendChild(emaGrid);
                    settingsForm.appendChild(emaGroup);
                    return;
                }
                
                // Special handling for timeframe - show as dropdown
                if (param.name === 'timeframe') {
                    const formGroup = document.createElement('div');
                    formGroup.className = 'form-group';
                    
                    const label = document.createElement('label');
                    label.textContent = 'Timeframe';
                    label.setAttribute('for', `setting-${param.name}`);
                    
                    const select = document.createElement('select');
                    select.id = `setting-${param.name}`;
                    
                    // MT5 Timeframe mapping
                    const MT5_TIMEFRAMES = [
                        { label: 'M1', value: 1, desc: '1 Minute' },
                        { label: 'M5', value: 5, desc: '5 Minutes' },
                        { label: 'M15', value: 15, desc: '15 Minutes' },
                        { label: 'M30', value: 30, desc: '30 Minutes' },
                        { label: 'H1', value: 16385, desc: '1 Hour' },
                        { label: 'H4', value: 16388, desc: '4 Hours' },
                        { label: 'D1', value: 16408, desc: 'Daily' }
                    ];
                    
                    MT5_TIMEFRAMES.forEach(tf => {
                        const option = document.createElement('option');
                        option.value = tf.value;
                        option.textContent = `${tf.label} (${tf.desc})`;
                        if (defaultValue === tf.value || (defaultValue === undefined && tf.value === 1)) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });
                    
                    formGroup.appendChild(label);
                    formGroup.appendChild(select);
                    settingsForm.appendChild(formGroup);
                    return;
                }
                
                // Special handling for session_type - show as dropdown
                if (param.name === 'session_type') {
                    const formGroup = document.createElement('div');
                    formGroup.className = 'form-group';
                    
                    const label = document.createElement('label');
                    label.textContent = 'Session Type';
                    label.setAttribute('for', `setting-${param.name}`);
                    
                    const select = document.createElement('select');
                    select.id = `setting-${param.name}`;
                    
                    // Session type options
                    const SESSION_TYPES = [
                        { value: 'daily', label: 'Daily' },
                        { value: 'ALL', label: 'All Sessions' },
                        { value: 'NY', label: 'New York Session' },
                        { value: 'London', label: 'London Session' },
                        { value: 'Asia', label: 'Asia Session' },
                        { value: 'asian', label: 'Asian Session' },
                        { value: 'european', label: 'European Session' },
                        { value: 'us', label: 'US Session' }
                    ];
                    
                    SESSION_TYPES.forEach(st => {
                        const option = document.createElement('option');
                        option.value = st.value;
                        option.textContent = st.label;
                        if (defaultValue === st.value || (defaultValue === undefined && st.value === 'daily')) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });
                    
                    formGroup.appendChild(label);
                    formGroup.appendChild(select);
                    settingsForm.appendChild(formGroup);
                    return;
                }
                
                const formGroup = document.createElement('div');
                formGroup.className = 'form-group';
                
                const label = document.createElement('label');
                label.textContent = param.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                label.setAttribute('for', `setting-${param.name}`);
                
                let input;
                
                if (param.type === 'boolean' || (defaultValue !== undefined && typeof defaultValue === 'boolean')) {
                    input = document.createElement('input');
                    input.type = 'checkbox';
                    input.id = `setting-${param.name}`;
                    input.checked = defaultValue || false;
                } else if (param.type === 'number' || (defaultValue !== undefined && typeof defaultValue === 'number')) {
                    input = document.createElement('input');
                    input.type = 'number';
                    input.id = `setting-${param.name}`;
                    input.step = Number.isInteger(defaultValue) ? 1 : 0.01;
                    input.value = defaultValue !== undefined ? defaultValue : '';
                } else if (param.type === 'object' || (defaultValue !== undefined && typeof defaultValue === 'object')) {
                    // For other object types, show as textarea (JSON)
                    input = document.createElement('textarea');
                    input.id = `setting-${param.name}`;
                    input.value = defaultValue ? JSON.stringify(defaultValue, null, 2) : '{}';
                    input.rows = 4;
                } else {
                    input = document.createElement('input');
                    input.type = 'text';
                    input.id = `setting-${param.name}`;
                    input.value = defaultValue !== undefined ? defaultValue : '';
                }
                
                if (param.required) {
                    input.required = true;
                }
                
                formGroup.appendChild(label);
                formGroup.appendChild(input);
                settingsForm.appendChild(formGroup);
            });
        }
        
        // Show condition builder for strategies that support conditions
        const conditionSupportingIndicators = ['ohlc_price_strategy', 'ema_strategy', 'vwap_strategy'];
        if (conditionSupportingIndicators.includes(indicatorName)) {
            conditionBuilderSection.style.display = 'block';
            buyConditionsContainer.innerHTML = '';
            sellConditionsContainer.innerHTML = '';
        } else {
            conditionBuilderSection.style.display = 'none';
        }
        
        // Show risk management section for all strategies (they all inherit from BaseStrategy)
        const riskManagementSection = document.getElementById('risk-management-section');
        if (riskManagementSection) {
            riskManagementSection.style.display = 'block';
        }
        
        showLoading(false);
    } catch (error) {
        console.error('Error loading indicator settings:', error);
        showError('Failed to load indicator settings: ' + error.message);
        settingsPanel.style.display = 'block'; // Still show panel even on error
        showLoading(false);
    }
}

/**
 * Handle position sizing type change
 */
function onPositionSizingTypeChange() {
    const type = document.getElementById('position-sizing-type').value;
    const label = document.getElementById('position-size-label');
    
    if (type === 'percentage') {
        label.textContent = 'Percentage (%)';
        document.getElementById('position-size').max = 100;
        document.getElementById('position-size').step = 0.1;
    } else {
        label.textContent = 'Lot Size';
        document.getElementById('position-size').max = null;
        document.getElementById('position-size').step = 0.01;
    }
}

/**
 * Add a new condition (buy or sell)
 */
function addCondition(type) {
    const conditionId = `${type}_condition_${Date.now()}`;
    const container = type === 'buy' 
        ? document.getElementById('buy-conditions-container')
        : document.getElementById('sell-conditions-container');
    
    const conditionDiv = document.createElement('div');
    conditionDiv.className = 'condition-item';
    conditionDiv.id = conditionId;
    
    // Get condition fields based on indicator type
    let conditionHTML = '';
    if (currentIndicatorName === 'ohlc_price_strategy') {
        conditionHTML = createOHLCConditionHTML(conditionId, type);
    } else if (currentIndicatorName === 'ema_strategy') {
        conditionHTML = createEMAConditionHTML(conditionId, type);
    } else if (currentIndicatorName === 'vwap_strategy') {
        conditionHTML = createVWAPConditionHTML(conditionId, type);
    } else {
        // Generic condition for other strategies
        conditionHTML = createGenericConditionHTML(conditionId, type);
    }
    
    conditionDiv.innerHTML = conditionHTML;
    container.appendChild(conditionDiv);
    
    // Store condition reference
    if (type === 'buy') {
        buyConditions.push({ id: conditionId, type: 'buy' });
    } else {
        sellConditions.push({ id: conditionId, type: 'sell' });
    }
}

/**
 * Create OHLC condition HTML form
 */
function createOHLCConditionHTML(conditionId, conditionType) {
    return `
        <div class="condition-form">
            <div class="condition-header">
                <span>${conditionType === 'buy' ? 'Buy' : 'Sell'} Condition</span>
                <button type="button" class="btn-remove-condition" onclick="removeCondition('${conditionId}')">Remove</button>
            </div>
            <div class="condition-fields">
                <div class="condition-field">
                    <label>Price Reference:</label>
                    <select class="condition-price-reference" data-condition-id="${conditionId}">
                        <option value="Current Price">Current Price</option>
                        <option value="Previous OHLC">Previous OHLC</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>Operator:</label>
                    <select class="condition-operator" data-condition-id="${conditionId}">
                        <option value=">">Greater Than (>)</option>
                        <option value="<">Less Than (<)</option>
                        <option value=">=">Greater or Equal (>=)</option>
                        <option value="<=">Less or Equal (<=)</option>
                        <option value="==">Equal (==)</option>
                        <option value="Crosses Above">Crosses Above</option>
                        <option value="Crosses Under">Crosses Under</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>OHLC Field (for Previous OHLC):</label>
                    <select class="condition-ohlc-field" data-condition-id="${conditionId}">
                        <option value="">None</option>
                        <option value="open">Open</option>
                        <option value="high">High</option>
                        <option value="low">Low</option>
                        <option value="close">Close</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>Value (optional, for direct comparison):</label>
                    <input type="number" class="condition-value" data-condition-id="${conditionId}" step="0.00001" placeholder="Enter value">
                </div>
                <div class="condition-field">
                    <label>Connector (to next condition):</label>
                    <select class="condition-connector" data-condition-id="${conditionId}">
                        <option value="OR">OR</option>
                        <option value="AND">AND</option>
                    </select>
                </div>
            </div>
        </div>
    `;
}

/**
 * Create EMA condition HTML form
 */
function createEMAConditionHTML(conditionId, conditionType) {
    return `
        <div class="condition-form">
            <div class="condition-header">
                <span>${conditionType === 'buy' ? 'Buy' : 'Sell'} Condition</span>
                <button type="button" class="btn-remove-condition" onclick="removeCondition('${conditionId}')">Remove</button>
            </div>
            <div class="condition-fields">
                <div class="condition-field">
                    <label>Price Reference:</label>
                    <select class="condition-price-reference" data-condition-id="${conditionId}">
                        <option value="Current Price">Current Price</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>Operator:</label>
                    <select class="condition-operator" data-condition-id="${conditionId}">
                        <option value=">">Greater Than (>)</option>
                        <option value="<">Less Than (<)</option>
                        <option value=">=">Greater or Equal (>=)</option>
                        <option value="<=">Less or Equal (<=)</option>
                        <option value="==">Equal (==)</option>
                        <option value="Crosses Above">Crosses Above</option>
                        <option value="Crosses Under">Crosses Under</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>EMA Field:</label>
                    <select class="condition-ema-field" data-condition-id="${conditionId}">
                        <option value="ema_1">EMA 1</option>
                        <option value="ema_2">EMA 2</option>
                        <option value="ema_3">EMA 3</option>
                        <option value="ema_4">EMA 4</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>Value (optional):</label>
                    <input type="number" class="condition-value" data-condition-id="${conditionId}" step="0.00001" placeholder="Enter value">
                </div>
                <div class="condition-field">
                    <label>Connector:</label>
                    <select class="condition-connector" data-condition-id="${conditionId}">
                        <option value="OR">OR</option>
                        <option value="AND">AND</option>
                    </select>
                </div>
            </div>
        </div>
    `;
}

/**
 * Create VWAP condition HTML form
 */
function createVWAPConditionHTML(conditionId, conditionType) {
    return `
        <div class="condition-form">
            <div class="condition-header">
                <span>${conditionType === 'buy' ? 'Buy' : 'Sell'} Condition</span>
                <button type="button" class="btn-remove-condition" onclick="removeCondition('${conditionId}')">Remove</button>
            </div>
            <div class="condition-fields">
                <div class="condition-field">
                    <label>Price Reference:</label>
                    <select class="condition-price-reference" data-condition-id="${conditionId}">
                        <option value="Current Price">Current Price</option>
                        <option value="VWAP">VWAP</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>Operator:</label>
                    <select class="condition-operator" data-condition-id="${conditionId}">
                        <option value=">">Greater Than (>)</option>
                        <option value="<">Less Than (<)</option>
                        <option value=">=">Greater or Equal (>=)</option>
                        <option value="<=">Less or Equal (<=)</option>
                        <option value="==">Equal (==)</option>
                        <option value="Crosses Above">Crosses Above</option>
                        <option value="Crosses Under">Crosses Under</option>
                        <option value="Within Band">Within Band</option>
                        <option value="Outside Band">Outside Band</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>VWAP Field:</label>
                    <select class="condition-vwap-field" data-condition-id="${conditionId}">
                        <option value="vwap">VWAP</option>
                        <option value="upper_band_1">Upper Band 1 STD</option>
                        <option value="upper_band_1.5">Upper Band 1.5 STD</option>
                        <option value="upper_band_2">Upper Band 2 STD</option>
                        <option value="lower_band_1">Lower Band 1 STD</option>
                        <option value="lower_band_1.5">Lower Band 1.5 STD</option>
                        <option value="lower_band_2">Lower Band 2 STD</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>Value (optional):</label>
                    <input type="number" class="condition-value" data-condition-id="${conditionId}" step="0.00001" placeholder="Enter value">
                </div>
                <div class="condition-field">
                    <label>Connector:</label>
                    <select class="condition-connector" data-condition-id="${conditionId}">
                        <option value="OR">OR</option>
                        <option value="AND">AND</option>
                    </select>
                </div>
            </div>
        </div>
    `;
}

/**
 * Create generic condition HTML form
 */
function createGenericConditionHTML(conditionId, conditionType) {
    return `
        <div class="condition-form">
            <div class="condition-header">
                <span>${conditionType === 'buy' ? 'Buy' : 'Sell'} Condition</span>
                <button type="button" class="btn-remove-condition" onclick="removeCondition('${conditionId}')">Remove</button>
            </div>
            <div class="condition-fields">
                <div class="condition-field">
                    <label>Operator:</label>
                    <select class="condition-operator" data-condition-id="${conditionId}">
                        <option value=">">Greater Than (>)</option>
                        <option value="<">Less Than (<)</option>
                        <option value=">=">Greater or Equal (>=)</option>
                        <option value="<=">Less or Equal (<=)</option>
                        <option value="==">Equal (==)</option>
                    </select>
                </div>
                <div class="condition-field">
                    <label>Value:</label>
                    <input type="number" class="condition-value" data-condition-id="${conditionId}" step="0.00001" required>
                </div>
                <div class="condition-field">
                    <label>Connector:</label>
                    <select class="condition-connector" data-condition-id="${conditionId}">
                        <option value="OR">OR</option>
                        <option value="AND">AND</option>
                    </select>
                </div>
            </div>
        </div>
    `;
}

/**
 * Remove a condition
 */
function removeCondition(conditionId) {
    const conditionDiv = document.getElementById(conditionId);
    if (conditionDiv) {
        conditionDiv.remove();
        // Remove from arrays
        buyConditions = buyConditions.filter(c => c.id !== conditionId);
        sellConditions = sellConditions.filter(c => c.id !== conditionId);
    }
}

/**
 * Collect conditions from UI
 */
function collectConditions() {
    const conditions = {
        buy_conditions: [],
        sell_conditions: []
    };
    
    // Collect buy conditions
    const buyContainer = document.getElementById('buy-conditions-container');
    if (buyContainer) {
        const buyConditionItems = buyContainer.querySelectorAll('.condition-item');
        buyConditionItems.forEach(item => {
            const condition = collectConditionData(item);
            if (condition) {
                conditions.buy_conditions.push(condition);
            }
        });
    }
    
    // Collect sell conditions
    const sellContainer = document.getElementById('sell-conditions-container');
    if (sellContainer) {
        const sellConditionItems = sellContainer.querySelectorAll('.condition-item');
        sellConditionItems.forEach(item => {
            const condition = collectConditionData(item);
            if (condition) {
                conditions.sell_conditions.push(condition);
            }
        });
    }
    
    return conditions;
}

/**
 * Collect condition data from a condition item element
 */
function collectConditionData(conditionItem) {
    const conditionId = conditionItem.id;
    
    const priceReference = conditionItem.querySelector('.condition-price-reference')?.value || 'Current Price';
    const operator = conditionItem.querySelector('.condition-operator')?.value || '>';
    const connector = conditionItem.querySelector('.condition-connector')?.value || 'OR';
    const valueInput = conditionItem.querySelector('.condition-value');
    const value = valueInput && valueInput.value ? parseFloat(valueInput.value) : null;
    
    let condition = {
        price_reference: priceReference,
        operator: operator,
        connector: connector
    };
    
    // Add indicator-specific fields
    if (currentIndicatorName === 'ohlc_price_strategy') {
        const ohlcField = conditionItem.querySelector('.condition-ohlc-field')?.value || null;
        condition.ohlc_field = ohlcField;
        condition.value = value;
        condition.left_field = priceReference === 'Current Price' ? 'price' : 'ohlc.' + ohlcField;
        condition.right_field = value !== null ? null : (ohlcField ? 'ohlc.' + ohlcField : null);
    } else if (currentIndicatorName === 'ema_strategy') {
        const emaField = conditionItem.querySelector('.condition-ema-field')?.value || 'ema_1';
        condition.ema_field = emaField;
        condition.value = value;
        condition.left_field = 'price';
        condition.right_field = value !== null ? null : 'indicators.' + emaField;
    } else if (currentIndicatorName === 'vwap_strategy') {
        const vwapField = conditionItem.querySelector('.condition-vwap-field')?.value || 'vwap';
        condition.vwap_field = vwapField;
        condition.value = value;
        condition.left_field = priceReference === 'Current Price' ? 'price' : 'vwap';
        condition.right_field = value !== null ? null : 'indicators.' + vwapField;
    } else {
        condition.value = value;
        condition.left_field = 'price';
        condition.right_field = null;
    }
    
    return condition;
}

/**
 * Run backtest
 */
async function runBacktest() {
    const symbol = document.getElementById('symbol-select').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const indicatorName = document.getElementById('indicator-select').value;
    
    if (!symbol) {
        showError('Please select a symbol');
        return;
    }
    
    if (!startDate || !endDate) {
        showError('Please select start and end dates');
        return;
    }
    
    if (!indicatorName) {
        showError('Please select an indicator');
        return;
    }
    
    // Collect indicator settings
    const indicatorSettings = {};
    const settingsForm = document.getElementById('indicator-settings-form');
    const inputs = settingsForm.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        if (input.id && input.id.startsWith('setting-')) {
            const paramName = input.id.replace('setting-', '');
            let value;
            
            if (input.type === 'checkbox') {
                value = input.checked;
            } else if (input.type === 'number') {
                value = input.value ? parseFloat(input.value) : undefined;
            } else if (input.tagName === 'TEXTAREA') {
                try {
                    value = JSON.parse(input.value);
                } catch {
                    value = input.value;
                }
            } else if (input.tagName === 'SELECT') {
                // For select elements, parse value as number if it's a number
                const numValue = parseFloat(input.value);
                value = isNaN(numValue) ? input.value : numValue;
            } else {
                value = input.value || undefined;
            }
            
            if (value !== undefined) {
                indicatorSettings[paramName] = value;
            }
        }
    });
    
    // Collect EMA periods as dictionary if EMA strategy
    if (indicatorName.includes('ema') || indicatorName === 'ema_strategy') {
        const ema1 = document.getElementById('setting-ema_1');
        const ema2 = document.getElementById('setting-ema_2');
        const ema3 = document.getElementById('setting-ema_3');
        const ema4 = document.getElementById('setting-ema_4');
        
        if (ema1 && ema2 && ema3 && ema4) {
            indicatorSettings.ema_periods = {
                ema_1: parseInt(ema1.value) || 20,
                ema_2: parseInt(ema2.value) || 50,
                ema_3: parseInt(ema3.value) || 100,
                ema_4: parseInt(ema4.value) || 200
            };
            // Remove individual ema_1, ema_2, etc. if they were added
            delete indicatorSettings.ema_1;
            delete indicatorSettings.ema_2;
            delete indicatorSettings.ema_3;
            delete indicatorSettings.ema_4;
        }
    }
    
    // Collect conditions if indicator supports them
    const conditions = collectConditions();
    if (conditions.buy_conditions.length > 0 || conditions.sell_conditions.length > 0) {
        indicatorSettings.buy_conditions = conditions.buy_conditions;
        indicatorSettings.sell_conditions = conditions.sell_conditions;
    }
    
    // Collect SL/TP and risk management settings
    indicatorSettings.sl_enabled = document.getElementById('sl-enabled').checked;
    indicatorSettings.sl_type = document.getElementById('sl-type').value;
    indicatorSettings.sl_value = parseFloat(document.getElementById('sl-value').value) || 20.0;
    indicatorSettings.tp_enabled = document.getElementById('tp-enabled').checked;
    indicatorSettings.use_ratio = document.getElementById('use-ratio').checked;
    indicatorSettings.tp_value = parseFloat(document.getElementById('tp-value').value) || 40.0;
    
    // Advanced risk management
    indicatorSettings.enable_trailing_sl = document.getElementById('enable-trailing-sl').checked;
    indicatorSettings.trailing_sl_gap = parseFloat(document.getElementById('trailing-sl-gap').value) || 0.0;
    indicatorSettings.enable_profit_lock = document.getElementById('enable-profit-lock').checked;
    indicatorSettings.profit_lock_trigger = parseFloat(document.getElementById('profit-lock-trigger').value) || 0.0;
    indicatorSettings.profit_lock_value = parseFloat(document.getElementById('profit-lock-value').value) || 0.0;
    indicatorSettings.profit_trail_step = parseFloat(document.getElementById('profit-trail-step').value) || 0.0;
    indicatorSettings.profit_trail_amount = parseFloat(document.getElementById('profit-trail-amount').value) || 0.0;
    
    // Get backtest configuration
    const positionSizingType = document.getElementById('position-sizing-type').value;
    const positionSize = parseFloat(document.getElementById('position-size').value);
    const initialCapital = parseFloat(document.getElementById('initial-capital').value);
    const commission = parseFloat(document.getElementById('commission').value);
    const slippage = parseFloat(document.getElementById('slippage').value);
    
    // Convert dates to ISO format with timezone
    const startDateISO = new Date(startDate).toISOString();
    const endDateISO = new Date(endDate).toISOString();
    
    // Show loading
    showLoading(true);
    hideError();
    document.getElementById('results-section').style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                start_date: startDateISO,
                end_date: endDateISO,
                indicator_name: indicatorName,
                indicator_settings: indicatorSettings,
                position_sizing_type: positionSizingType,
                position_size: positionSize,
                initial_capital: initialCapital,
                commission: commission,
                slippage: slippage
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to run backtest');
        }
        
        const results = await response.json();
        
        if (results.error) {
            throw new Error(results.error);
        }
        
        displayResults(results);
        showLoading(false);
    } catch (error) {
        showError('Error running backtest: ' + error.message);
        showLoading(false);
    }
}

/**
 * Display backtest results
 */
function displayResults(results) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.style.display = 'block';
    
    const metrics = results.metrics || {};
    const trades = results.trades || [];
    
    // Update metrics cards
    updateMetric('metric-total-pnl', metrics.total_pnl, true);
    updateMetric('metric-win-rate', metrics.win_rate + '%');
    updateMetric('metric-total-trades', metrics.total_trades);
    updateMetric('metric-profit-factor', metrics.profit_factor);
    updateMetric('metric-sharpe', metrics.sharpe_ratio);
    updateMetric('metric-drawdown', metrics.max_drawdown_percent + '%');
    updateMetric('metric-roi', metrics.roi + '%', true);
    updateMetric('metric-avg-win', metrics.average_win, true);
    updateMetric('metric-avg-loss', metrics.average_loss, true);
    updateMetric('metric-largest-win', metrics.largest_win, true);
    updateMetric('metric-largest-loss', metrics.largest_loss, true);
    updateMetric('metric-expectancy', metrics.expectancy, true);
    
    // Render equity curve
    if (results.equity_curve && results.equity_curve.length > 0) {
        renderEquityCurve(results.equity_curve);
    }
    
    // Render trades table
    renderTradesTable(trades);
}

/**
 * Update a metric card
 */
function updateMetric(id, value, isMonetary = false) {
    const element = document.getElementById(id);
    if (!element) return;
    
    const card = element.closest('.metric-card');
    if (card) {
        card.classList.remove('positive', 'negative');
        if (isMonetary && typeof value === 'number') {
            if (value > 0) {
                card.classList.add('positive');
            } else if (value < 0) {
                card.classList.add('negative');
            }
        }
    }
    
    if (value === null || value === undefined) {
        element.textContent = '-';
    } else if (isMonetary && typeof value === 'number') {
        element.textContent = value >= 0 ? `+$${value.toFixed(2)}` : `-$${Math.abs(value).toFixed(2)}`;
    } else {
        element.textContent = value;
    }
}

/**
 * Render equity curve chart
 */
function renderEquityCurve(equityCurve) {
    const container = document.getElementById('equity-chart');
    if (!container) return;
    
    // Clean up existing chart
    if (currentChart) {
        currentChart.remove();
        currentChart = null;
    }
    
    if (typeof LightweightCharts === 'undefined') {
        console.error('LightweightCharts not loaded');
        return;
    }
    
    // Create chart
    const chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: 400,
        layout: {
            background: { color: '#ffffff' },
            textColor: '#333',
        },
        grid: {
            vertLines: { color: '#e0e0e0' },
            horzLines: { color: '#e0e0e0' },
        },
        timeScale: {
            timeVisible: true,
            secondsVisible: false,
        },
    });
    
    // Convert equity curve to chart data
    const chartData = equityCurve.map(point => {
        const time = new Date(point.time).getTime() / 1000; // Convert to Unix timestamp
        return {
            time: time,
            value: point.equity
        };
    });
    
    // Add line series
    const lineSeries = chart.addLineSeries({
        color: '#3498db',
        lineWidth: 2,
        title: 'Equity'
    });
    
    lineSeries.setData(chartData);
    
    currentChart = chart;
}

/**
 * Render trades table
 */
function renderTradesTable(trades) {
    const tbody = document.getElementById('trades-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (trades.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 13;
        cell.textContent = 'No trades executed';
        cell.style.textAlign = 'center';
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }
    
    trades.forEach(trade => {
        const row = document.createElement('tr');
        if (trade.is_win) {
            row.classList.add('win');
        } else if (trade.is_loss) {
            row.classList.add('loss');
        }
        
        const formatDate = (dateStr) => {
            const date = new Date(dateStr);
            return date.toLocaleString();
        };
        
        const formatDuration = (seconds) => {
            if (!seconds && trade.duration_minutes) {
                // Use duration_minutes if available
                const minutes = Math.floor(trade.duration_minutes);
                const hours = Math.floor(minutes / 60);
                const mins = minutes % 60;
                if (hours > 0) {
                    return `${hours}h ${mins}m`;
                }
                return `${mins}m`;
            }
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            if (hours > 0) {
                return `${hours}h ${minutes}m`;
            }
            return `${minutes}m`;
        };
        
        const pnlPercent = trade.pnl_percentage !== undefined 
            ? trade.pnl_percentage.toFixed(2) 
            : (trade.entry_price > 0 
                ? ((trade.pnl / (trade.entry_price * trade.lot_size * 100000)) * 100).toFixed(2)
                : '0.00');
        
        const entryCondition = trade.entry_condition || '-';
        const exitReason = trade.exit_reason || 'Signal Reversal';
        const slPrice = trade.sl_price !== undefined && trade.sl_price !== null ? trade.sl_price.toFixed(5) : '-';
        const tpPrice = trade.tp_price !== undefined && trade.tp_price !== null ? trade.tp_price.toFixed(5) : '-';
        
        // Determine exit reason class for color coding
        let exitReasonClass = '';
        if (exitReason === 'SL' || exitReason === 'Trailing SL') {
            exitReasonClass = 'exit-sl';
        } else if (exitReason === 'TP' || exitReason === 'Profit Lock') {
            exitReasonClass = 'exit-tp';
        } else if (exitReason.includes('Signal')) {
            exitReasonClass = 'exit-signal';
        } else {
            exitReasonClass = 'exit-other';
        }
        
        row.innerHTML = `
            <td>${formatDate(trade.entry_time)}</td>
            <td>${formatDate(trade.exit_time)}</td>
            <td>${trade.direction}</td>
            <td>${trade.entry_price.toFixed(5)}</td>
            <td>${trade.exit_price.toFixed(5)}</td>
            <td>${slPrice}</td>
            <td>${tpPrice}</td>
            <td>${trade.lot_size.toFixed(2)}</td>
            <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}</td>
            <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">${pnlPercent >= 0 ? '+' : ''}${pnlPercent}%</td>
            <td>${formatDuration(trade.duration_seconds || trade.duration_minutes * 60)}</td>
            <td title="${entryCondition}">${entryCondition.length > 50 ? entryCondition.substring(0, 50) + '...' : entryCondition}</td>
            <td class="${exitReasonClass}">${exitReason}</td>
        `;
        
        tbody.appendChild(row);
    });
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

