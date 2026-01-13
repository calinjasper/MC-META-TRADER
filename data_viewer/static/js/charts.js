/**
 * Chart rendering functions
 * Uses TradingView lightweight-charts for all chart types
 */

/**
 * Parse IST timestamp string to Unix timestamp (seconds)
 * Input format: "YYYY-MM-DD HH:MM:SS IST"
 * Returns: Unix timestamp in seconds (UTC)
 */
function parseTimestampToUnix(timestampStr) {
    if (!timestampStr) return null;
    
    // Remove " IST" suffix if present
    const cleanStr = timestampStr.replace(' IST', '').trim();
    
    // Parse the date string (format: "YYYY-MM-DD HH:MM:SS")
    const parts = cleanStr.split(' ');
    if (parts.length !== 2) return null;
    
    const datePart = parts[0]; // YYYY-MM-DD
    const timePart = parts[1]; // HH:MM:SS
    
    const [year, month, day] = datePart.split('-').map(Number);
    const timeComponents = timePart.split(':').map(Number);
    const [hours, minutes, seconds] = timeComponents.length === 3 
        ? timeComponents 
        : [timeComponents[0] || 0, timeComponents[1] || 0, 0];
    
    // IST is UTC+5:30, so to convert IST to UTC, we subtract 5:30
    // Create a Date object in UTC by using Date.UTC() and subtracting the offset
    const istOffsetMs = 5.5 * 3600 * 1000; // 5 hours 30 minutes in milliseconds
    const utcDate = new Date(Date.UTC(year, month - 1, day, hours, minutes, seconds || 0) - istOffsetMs);
    
    // Return Unix timestamp in seconds
    return Math.floor(utcDate.getTime() / 1000);
}

/**
 * Render candlestick chart for minute OHLC data using TradingView
 */
function renderCandlestickChart(data) {
    // Check if TradingView library is loaded
    if (typeof LightweightCharts === 'undefined') {
        showError('TradingView chart library failed to load. Please refresh the page.');
        return;
    }
    
    const container = document.getElementById('chart-container');
    if (!container) {
        showError('Chart container not found.');
        return;
    }
    
    container.style.display = 'block';
    
    // Clean up existing chart if any
    if (currentChart && currentChart.remove) {
        currentChart.remove();
    }
    
    // Clear container and create TradingView chart div
    container.innerHTML = '<div id="tradingview-chart" style="width:100%;height:600px;position: relative;"></div>';
    
    // Recreate tooltip panel (it gets removed by innerHTML)
    const panel = document.createElement('div');
    panel.id = 'candle-info-panel';
    panel.className = 'candle-info-panel';
    panel.style.display = 'none';
    panel.innerHTML = `
        <div class="candle-info-content">
            <h4>Candle Details</h4>
            <div class="candle-info-grid">
                <div class="candle-info-item">
                    <span class="candle-info-label">Time:</span>
                    <span id="candle-time" class="candle-info-value">-</span>
                </div>
                <div class="candle-info-item">
                    <span class="candle-info-label">Open:</span>
                    <span id="candle-open" class="candle-info-value">-</span>
                </div>
                <div class="candle-info-item">
                    <span class="candle-info-label">High:</span>
                    <span id="candle-high" class="candle-info-value">-</span>
                </div>
                <div class="candle-info-item">
                    <span class="candle-info-label">Low:</span>
                    <span id="candle-low" class="candle-info-value">-</span>
                </div>
                <div class="candle-info-item">
                    <span class="candle-info-label">Close:</span>
                    <span id="candle-close" class="candle-info-value">-</span>
                </div>
            </div>
        </div>
    `;
    container.appendChild(panel);
    
    // Sort by timestamp string (chronological order)
    const sortedData = [...data].sort((a, b) => {
        const tsA = parseTimestampToUnix(a.timestamp || '');
        const tsB = parseTimestampToUnix(b.timestamp || '');
        return (tsA || 0) - (tsB || 0);
    });
    
    // Create TradingView chart
    const chartElement = document.getElementById('tradingview-chart');
    
    if (!chartElement) {
        showError('Chart element not found. Please try refreshing the page.');
        return;
    }
    
    if (typeof LightweightCharts === 'undefined') {
        showError('TradingView chart library failed to load. Please refresh the page.');
        return;
    }
    
    // Ensure chart element has dimensions
    const chartWidth = chartElement.clientWidth || 800;
    const chartHeight = 600;
    
    let chart;
    try {
        chart = LightweightCharts.createChart(chartElement, {
            width: chartWidth,
            height: chartHeight,
            layout: {
                background: { color: '#ffffff' },
                textColor: '#333',
            },
            grid: {
                vertLines: { color: '#e0e0e0' },
                horzLines: { color: '#e0e0e0' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#cccccc',
            },
            timeScale: {
                borderColor: '#cccccc',
                timeVisible: true,
                secondsVisible: false,
            },
        });
    } catch (error) {
        showError('Failed to create chart: ' + error.message);
        console.error('Chart creation error:', error);
        return;
    }
    
    // Add candlestick series
    let candlestickSeries;
    try {
        candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
    } catch (error) {
        showError('Failed to add candlestick series: ' + error.message);
        console.error('Candlestick series error:', error);
        return;
    }
    
    // Prepare data for TradingView (format: { time, open, high, low, close })
    // Also create a lookup map for quick candle data access by timestamp
    const candlestickData = [];
    const candleDataMap = {}; // Map: timestamp_unix -> { open, high, low, close, timestamp }
    
    sortedData.forEach(item => {
        const time = parseTimestampToUnix(item.timestamp);
        if (!time) return;
        
        const candlePoint = {
            time: time,
            open: parseFloat(item.open || 0),
            high: parseFloat(item.high || 0),
            low: parseFloat(item.low || 0),
            close: parseFloat(item.close || 0),
        };
        
        candlestickData.push(candlePoint);
        
        // Store in lookup map with original timestamp string for display
        candleDataMap[time] = {
            open: candlePoint.open,
            high: candlePoint.high,
            low: candlePoint.low,
            close: candlePoint.close,
            timestamp: item.timestamp || '', // Original IST timestamp string
        };
    });
    
    // Set data to series
    try {
        if (candlestickData.length === 0) {
            showError('No valid candlestick data to display. Check timestamp format.');
            return;
        }
        
        candlestickSeries.setData(candlestickData);
    } catch (error) {
        showError('Failed to set chart data: ' + error.message);
        console.error('Set data error:', error);
        return;
    }
    
    // Subscribe to crosshair move events to show candle info on hover
    chart.subscribeCrosshairMove(param => {
        if (param.time && param.seriesData) {
            // Find candle data for this timestamp
            const candleData = candleDataMap[param.time];
            if (candleData) {
                // Update candle info panel with position near cursor
                updateCandleInfo(candleData, param.point);
            } else {
                // Try to find nearest candle if exact match not found
                const nearestTime = findNearestTimestamp(param.time, Object.keys(candleDataMap).map(Number));
                if (nearestTime !== null) {
                    const nearestCandleData = candleDataMap[nearestTime];
                    if (nearestCandleData) {
                        updateCandleInfo(nearestCandleData, param.point);
                    }
                } else {
                    hideCandleInfo();
                }
            }
        } else {
            // Hide panel when not hovering
            hideCandleInfo();
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', () => {
        chart.applyOptions({ width: chartElement.clientWidth });
    });
    
    // Store reference for cleanup
    currentChart = chart;
}

/**
 * Render line chart for tick data using TradingView
 */
function renderLineChart(data) {
    // Check if TradingView library is loaded
    if (typeof LightweightCharts === 'undefined') {
        showError('TradingView chart library failed to load. Please refresh the page.');
        return;
    }
    
    const container = document.getElementById('chart-container');
    container.style.display = 'block';
    
    // Clear container and create TradingView chart div
    container.innerHTML = '<div id="tradingview-chart" style="width:100%;height:600px;"></div>';
    
    // Clean up existing chart if any
    if (currentChart && currentChart.remove) {
        currentChart.remove();
    }
    
    // Sort by timestamp string (chronological order)
    const sortedData = [...data].sort((a, b) => {
        const tsA = parseTimestampToUnix(a.timestamp || '');
        const tsB = parseTimestampToUnix(b.timestamp || '');
        return (tsA || 0) - (tsB || 0);
    });
    
    // Create TradingView chart
    const chartElement = document.getElementById('tradingview-chart');
    const chart = LightweightCharts.createChart(chartElement, {
        width: chartElement.clientWidth,
        height: 600,
        layout: {
            background: { color: '#ffffff' },
            textColor: '#333',
        },
        grid: {
            vertLines: { color: '#e0e0e0' },
            horzLines: { color: '#e0e0e0' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
            secondsVisible: false,
        },
    });
    
    // Add line series for Bid
    const bidSeries = chart.addLineSeries({
        color: '#4BC0C0', // Teal/cyan
        lineWidth: 2,
        title: 'Bid',
    });
    
    // Add line series for Ask
    const askSeries = chart.addLineSeries({
        color: '#FF6384', // Red/pink
        lineWidth: 2,
        title: 'Ask',
    });
    
    // Add line series for Last
    const lastSeries = chart.addLineSeries({
        color: '#36A2EB', // Blue
        lineWidth: 2,
        title: 'Last',
    });
    
    // Prepare data for TradingView (format: { time, value })
    const bidData = sortedData
        .map(item => {
            const time = parseTimestampToUnix(item.timestamp);
            if (!time) return null;
            return {
                time: time,
                value: parseFloat(item.bid || 0),
            };
        })
        .filter(item => item !== null && item.time !== null && item.value > 0);
    
    const askData = sortedData
        .map(item => {
            const time = parseTimestampToUnix(item.timestamp);
            if (!time) return null;
            return {
                time: time,
                value: parseFloat(item.ask || 0),
            };
        })
        .filter(item => item !== null && item.time !== null && item.value > 0);
    
    const lastData = sortedData
        .map(item => {
            const time = parseTimestampToUnix(item.timestamp);
            if (!time) return null;
            return {
                time: time,
                value: parseFloat(item.last || 0),
            };
        })
        .filter(item => item !== null && item.time !== null && item.value > 0);
    
    // Set data to series
    bidSeries.setData(bidData);
    askSeries.setData(askData);
    lastSeries.setData(lastData);
    
    // Handle window resize
    window.addEventListener('resize', () => {
        chart.applyOptions({ width: chartElement.clientWidth });
    });
    
    // Store reference for cleanup
    currentChart = chart;
}

/**
 * Update candle info panel with OHLC values and position near cursor
 */
function updateCandleInfo(candleData, point) {
    const panel = document.getElementById('candle-info-panel');
    if (!panel) return;
    
    // Update time
    const timeEl = document.getElementById('candle-time');
    if (timeEl) {
        timeEl.textContent = candleData.timestamp || '-';
    }
    
    // Format prices with appropriate decimal places (5 decimals for precision)
    const formatPrice = (price) => {
        if (price === null || price === undefined || isNaN(price)) return '-';
        return price.toFixed(5);
    };
    
    // Update OHLC values
    const openEl = document.getElementById('candle-open');
    if (openEl) openEl.textContent = formatPrice(candleData.open);
    
    const highEl = document.getElementById('candle-high');
    if (highEl) highEl.textContent = formatPrice(candleData.high);
    
    const lowEl = document.getElementById('candle-low');
    if (lowEl) lowEl.textContent = formatPrice(candleData.low);
    
    const closeEl = document.getElementById('candle-close');
    if (closeEl) closeEl.textContent = formatPrice(candleData.close);
    
    // Position tooltip near cursor
    if (point) {
        const chartElement = document.getElementById('tradingview-chart');
        const chartContainer = document.getElementById('chart-container');
        if (chartElement && chartContainer) {
            const chartRect = chartElement.getBoundingClientRect();
            const containerRect = chartContainer.getBoundingClientRect();
            
            // point.x and point.y are relative to the chart canvas
            // Calculate position relative to chart container (which has position: relative)
            const offsetX = 15; // Offset from cursor
            const offsetY = 15;
            
            // Get the offset of chart element within container (accounting for padding)
            const chartOffsetX = chartRect.left - containerRect.left;
            const chartOffsetY = chartRect.top - containerRect.top;
            
            // Calculate position relative to container
            let left = chartOffsetX + point.x + offsetX;
            let top = chartOffsetY + point.y + offsetY;
            
            // Keep tooltip within container bounds
            const tooltipWidth = 220; // Approximate tooltip width
            const tooltipHeight = 180; // Approximate tooltip height
            
            if (left + tooltipWidth > containerRect.width) {
                left = chartOffsetX + point.x - tooltipWidth - offsetX; // Show on left side of cursor
            }
            
            if (top + tooltipHeight > containerRect.height) {
                top = chartOffsetY + point.y - tooltipHeight - offsetY; // Show above cursor
            }
            
            // Ensure tooltip doesn't go outside container area
            left = Math.max(10, Math.min(left, containerRect.width - tooltipWidth - 10));
            top = Math.max(10, Math.min(top, containerRect.height - tooltipHeight - 10));
            
            panel.style.left = left + 'px';
            panel.style.top = top + 'px';
        }
    }
    
    // Show panel
    panel.style.display = 'block';
    panel.classList.add('show');
}

/**
 * Hide candle info panel
 */
function hideCandleInfo() {
    const panel = document.getElementById('candle-info-panel');
    if (panel) {
        panel.style.display = 'none';
        panel.classList.remove('show');
    }
}

/**
 * Find nearest timestamp in array (for edge case handling)
 */
function findNearestTimestamp(targetTime, timeArray) {
    if (!timeArray || timeArray.length === 0) return null;
    
    let nearest = timeArray[0];
    let minDiff = Math.abs(targetTime - nearest);
    
    for (let i = 1; i < timeArray.length; i++) {
        const diff = Math.abs(targetTime - timeArray[i]);
        if (diff < minDiff) {
            minDiff = diff;
            nearest = timeArray[i];
        }
    }
    
    // Only return if within reasonable range (e.g., within 60 seconds)
    return minDiff <= 60 ? nearest : null;
}

/**
 * Render data table for non-chart collections
 */
function renderTable(data) {
    const container = document.getElementById('table-container');
    if (!container) {
        console.error('table-container element not found');
        return;
    }
    
    container.style.display = 'block';
    
    const thead = document.getElementById('table-head');
    const tbody = document.getElementById('table-body');
    
    if (!thead || !tbody) {
        console.error('table-head or table-body element not found');
        return;
    }
    
    // Clear existing content
    thead.innerHTML = '';
    tbody.innerHTML = '';
    
    if (data.length === 0) {
        return;
    }
    
    // Get all unique keys from data
    const keys = new Set();
    data.forEach(item => {
        Object.keys(item).forEach(key => keys.add(key));
    });
    
    const sortedKeys = Array.from(keys).sort();
    
    // Create header
    const headerRow = document.createElement('tr');
    sortedKeys.forEach(key => {
        const th = document.createElement('th');
        th.textContent = key;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    
    // Create rows (limit to 1000 rows for performance)
    const displayData = data.slice(0, 1000);
    displayData.forEach(item => {
        const row = document.createElement('tr');
        sortedKeys.forEach(key => {
            const td = document.createElement('td');
            const value = item[key];
            if (value === null || value === undefined) {
                td.textContent = '';
            } else if (typeof value === 'object') {
                td.textContent = JSON.stringify(value);
            } else {
                td.textContent = String(value);
            }
            row.appendChild(td);
        });
        tbody.appendChild(row);
    });
    
    if (data.length > 1000) {
        const infoRow = document.createElement('tr');
        const infoCell = document.createElement('td');
        infoCell.colSpan = sortedKeys.length;
        infoCell.textContent = `Showing first 1000 of ${data.length} records`;
        infoCell.style.textAlign = 'center';
        infoCell.style.fontStyle = 'italic';
        infoCell.style.color = '#7f8c8d';
        infoRow.appendChild(infoCell);
        tbody.appendChild(infoRow);
    }
}

