// Global application state
let appData = {
    logbooks: [],
    boats: {},
    persons: {},
    destinations: {},
    filteredLogbooks: [],
    currentPage: 1,
    itemsPerPage: 25,
    sortColumn: 'date',
    sortDirection: 'desc',
    years: [],
    distanceRange: [0, 50]
};

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await loadData();
        initializeUI();
        setupEventListeners();
        applyFilters();
    } catch (error) {
        console.error('Failed to initialize application:', error);
        alert('Failed to load data. Please check the console for details.');
    }
});

// Load JSON data files
async function loadData() {
    try {
        const [logbooksResponse, boatsResponse, personsResponse, destinationsResponse] = await Promise.all([
            fetch('data/logbooks.json'),
            fetch('data/boats.json'),
            fetch('data/persons.json'),
            fetch('data/destinations.json')
        ]);

        appData.logbooks = await logbooksResponse.json();
        const boats = await boatsResponse.json();
        const persons = await personsResponse.json();
        const destinations = await destinationsResponse.json();

        // Convert arrays to lookup objects
        appData.boats = boats.reduce((acc, boat) => {
            acc[boat.id] = boat;
            return acc;
        }, {});

        appData.persons = persons.reduce((acc, person) => {
            acc[person.id] = person;
            return acc;
        }, {});

        appData.destinations = destinations.reduce((acc, dest) => {
            acc[dest.id] = dest;
            return acc;
        }, {});

        // Extract unique years and sort them
        appData.years = [...new Set(appData.logbooks.map(entry => entry.year))].sort((a, b) => b - a);
        
        // Calculate distance range
        const distances = appData.logbooks.map(entry => entry.dist || 0).filter(d => d > 0);
        if (distances.length > 0) {
            appData.distanceRange = [0, Math.max(...distances)];
        }

    } catch (error) {
        console.error('Error loading data:', error);
        throw error;
    }
}

// Initialize UI components
function initializeUI() {
    initializeTabs();
    populateYearSelects();
    initializeDistanceSlider();
    initializeTable();
    initializeStatistics();
}

// Tab functionality
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            
            // Update button states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update content states
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${targetTab}-tab`).classList.add('active');
            
            if (targetTab === 'statistics') {
                updateStatistics();
            }
        });
    });

    // Statistics sub-tabs
    const statsTabButtons = document.querySelectorAll('.stats-tab-button');
    const statsTabContents = document.querySelectorAll('.stats-tab-content');
    
    statsTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.statsTab;
            
            // Update button states
            statsTabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update content states
            statsTabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${targetTab}-tab`).classList.add('active');
            
            updateStatistics();
        });
    });
}

// Populate year select elements
function populateYearSelects() {
    const yearSelects = [
        'year-select',
        'boat-stats-year-select', 
        'rower-stats-year-select',
        'time-stats-year-select'
    ];
    
    yearSelects.forEach(selectId => {
        const select = document.getElementById(selectId);
        select.innerHTML = '';
        
        appData.years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            // Select most recent year by default
            if (year === appData.years[0]) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    });
}

// Initialize distance slider
function initializeDistanceSlider() {
    const slider = document.getElementById('distance-slider');
    const minSpan = document.getElementById('distance-min');
    const maxSpan = document.getElementById('distance-max');
    
    // Create logarithmic range: good resolution up to 20km, then coarser to 100km
    noUiSlider.create(slider, {
        start: [0, 100],
        connect: true,
        range: {
            'min': 0,
            '20%': 5,
            '40%': 10,
            '60%': 20,
            '80%': 50,
            'max': 100
        },
        step: 1,
        tooltips: false, // Remove handle tooltips
        format: {
            to: value => Math.round(value),
            from: value => Number(value)
        }
    });
    
    slider.noUiSlider.on('update', (values) => {
        minSpan.textContent = values[0];
        maxSpan.textContent = values[1];
    });
    
    slider.noUiSlider.on('change', applyFilters);
}

// Setup event listeners
function setupEventListeners() {
    // Search input
    document.getElementById('search-input').addEventListener('input', applyFilters);
    
    // Year select
    document.getElementById('year-select').addEventListener('change', applyFilters);
    
    // Statistics year selects
    document.getElementById('boat-stats-year-select').addEventListener('change', updateStatistics);
    document.getElementById('rower-stats-year-select').addEventListener('change', updateStatistics);
    document.getElementById('time-stats-year-select').addEventListener('change', updateStatistics);
    document.getElementById('time-stats-type').addEventListener('change', updateStatistics);
    
    setupTableEventHandlers();
}

// Table functionality
function initializeTable() {
    setupTableSorting();
}

function setupTableSorting() {
    const headers = document.querySelectorAll('#logbook-table th[data-sort]');
    
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const sortBy = header.dataset.sort;
            
            // Toggle sort direction if same column, otherwise default to asc
            if (appData.sortColumn === sortBy) {
                appData.sortDirection = appData.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                appData.sortColumn = sortBy;
                appData.sortDirection = 'asc';
            }
            
            updateSortIndicators();
            applyFilters();
        });
    });
}

function updateSortIndicators() {
    const headers = document.querySelectorAll('#logbook-table th[data-sort]');
    
    headers.forEach(header => {
        const indicator = header.querySelector('.sort-indicator');
        indicator.className = 'sort-indicator';
        
        if (header.dataset.sort === appData.sortColumn) {
            indicator.classList.add(appData.sortDirection);
        }
    });
}

// Pagination functionality (based on the provided function)
function setupTableEventHandlers() {
    document.getElementById('first-page').addEventListener('click', () => {
        appData.currentPage = 1;
        renderTable();
    });
    
    document.getElementById('prev-page').addEventListener('click', () => {
        if (appData.currentPage > 1) {
            appData.currentPage--;
            renderTable();
        }
    });
    
    document.getElementById('next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(appData.filteredLogbooks.length / appData.itemsPerPage);
        if (appData.currentPage < totalPages) {
            appData.currentPage++;
            renderTable();
        }
    });
    
    document.getElementById('last-page').addEventListener('click', () => {
        const totalPages = Math.ceil(appData.filteredLogbooks.length / appData.itemsPerPage);
        appData.currentPage = totalPages;
        renderTable();
    });
}

function renderPageNumbers() {
    const totalPages = Math.ceil(appData.filteredLogbooks.length / appData.itemsPerPage);
    const pageNumbersContainer = document.getElementById('page-numbers');
    pageNumbersContainer.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    const maxVisiblePages = 5;
    let startPage = Math.max(1, appData.currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    // Adjust start if we're near the end
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageButton = document.createElement('button');
        pageButton.className = `page-number ${i === appData.currentPage ? 'active' : ''}`;
        pageButton.textContent = i;
        pageButton.addEventListener('click', () => {
            appData.currentPage = i;
            renderTable();
        });
        pageNumbersContainer.appendChild(pageButton);
    }
}

// Filtering and sorting
function applyFilters() {
    const selectedYears = Array.from(document.getElementById('year-select').selectedOptions)
        .map(option => parseInt(option.value));
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const slider = document.getElementById('distance-slider');
    const distanceRange = slider.noUiSlider.get().map(Number);
    
    appData.filteredLogbooks = appData.logbooks.filter(entry => {
        // Year filter
        if (selectedYears.length > 0 && !selectedYears.includes(entry.year)) {
            return false;
        }
        
        // Distance filter
        const dist = entry.dist || 0;
        if (dist < distanceRange[0] || dist > distanceRange[1]) {
            return false;
        }
        
        // Search filter
        if (searchTerm) {
            const boat = appData.boats[entry.boat];
            const boatName = boat ? boat.name.toLowerCase() : '';
            
            const crewNames = entry.crew.map(personId => {
                const person = appData.persons[personId];
                if (!person) return '';
                return `${person.fn || ''} ${person.ln || ''}`.toLowerCase();
            }).join(' ');
            
            if (!boatName.includes(searchTerm) && !crewNames.includes(searchTerm)) {
                return false;
            }
        }
        
        return true;
    });
    
    // Sort the filtered data
    appData.filteredLogbooks.sort((a, b) => {
        let aVal, bVal;
        
        switch (appData.sortColumn) {
            case 'date':
                aVal = new Date(a.date.split('.').reverse().join('-'));
                bVal = new Date(b.date.split('.').reverse().join('-'));
                break;
            case 'boat':
                aVal = appData.boats[a.boat]?.name || '';
                bVal = appData.boats[b.boat]?.name || '';
                break;
            case 'crew':
                aVal = formatCrew(a.crew);
                bVal = formatCrew(b.crew);
                break;
            case 'dist':
                aVal = a.dist || 0;
                bVal = b.dist || 0;
                break;
            case 'dest':
                aVal = appData.destinations[a.dest]?.name || '';
                bVal = appData.destinations[b.dest]?.name || '';
                break;
            default:
                return 0;
        }
        
        if (aVal < bVal) return appData.sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return appData.sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
    
    appData.currentPage = 1;
    renderTable();
}

// Table rendering
function renderTable() {
    const tbody = document.querySelector('#logbook-table tbody');
    const startIndex = (appData.currentPage - 1) * appData.itemsPerPage;
    const endIndex = startIndex + appData.itemsPerPage;
    const pageData = appData.filteredLogbooks.slice(startIndex, endIndex);
    
    tbody.innerHTML = pageData.map(entry => `
        <tr>
            <td>${entry.date}</td>
            <td>${formatBoat(entry.boat)}</td>
            <td>${formatCrew(entry.crew)}</td>
            <td>${entry.dist || 0} km</td>
            <td>${formatDestination(entry.dest)}</td>
        </tr>
    `).join('');
    
    updatePaginationInfo();
    renderPageNumbers();
    updatePaginationButtons();
}

function updatePaginationInfo() {
    const totalEntries = appData.filteredLogbooks.length;
    const startIndex = (appData.currentPage - 1) * appData.itemsPerPage + 1;
    const endIndex = Math.min(appData.currentPage * appData.itemsPerPage, totalEntries);
    
    document.getElementById('showing-start').textContent = totalEntries === 0 ? 0 : startIndex;
    document.getElementById('showing-end').textContent = endIndex;
    document.getElementById('total-entries').textContent = totalEntries;
}

function updatePaginationButtons() {
    const totalPages = Math.ceil(appData.filteredLogbooks.length / appData.itemsPerPage);
    
    document.getElementById('first-page').disabled = appData.currentPage === 1;
    document.getElementById('prev-page').disabled = appData.currentPage === 1;
    document.getElementById('next-page').disabled = appData.currentPage === totalPages || totalPages === 0;
    document.getElementById('last-page').disabled = appData.currentPage === totalPages || totalPages === 0;
}

// Formatting functions
function formatBoat(boatId) {
    const boat = appData.boats[boatId];
    if (!boat) return 'Unknown';
    return boat.suffix ? `${boat.name} (${boat.suffix})` : boat.name;
}

function formatCrew(crewIds) {
    return crewIds.map(personId => {
        const person = appData.persons[personId];
        if (!person) return 'Unknown';
        return `${person.fn || ''} ${person.ln || ''}`.trim();
    }).join(', ');
}

function formatDestination(destId) {
    const dest = appData.destinations[destId];
    return dest ? dest.name : 'Unknown';
}

// Statistics functionality
let statsCharts = {
    boat: null,
    rower: null,
    time: null
};

function initializeStatistics() {
    // Initialize Chart.js default settings
    Chart.defaults.font.family = 'inherit';
    Chart.defaults.font.size = 12;
    Chart.defaults.plugins.legend.position = 'top';
}

function updateStatistics() {
    const activeStatsTab = document.querySelector('.stats-tab-button.active').dataset.statsTab;
    
    switch (activeStatsTab) {
        case 'km-by-boat':
            updateKmByBoat();
            break;
        case 'km-by-rower':
            updateKmByRower();
            break;
        case 'km-over-time':
            updateKmOverTime();
            break;
    }
}

function updateKmByBoat() {
    const selectedYears = Array.from(document.getElementById('boat-stats-year-select').selectedOptions)
        .map(option => parseInt(option.value));
    
    const boatKm = {};
    
    appData.logbooks.forEach(entry => {
        if (selectedYears.length === 0 || selectedYears.includes(entry.year)) {
            const boat = appData.boats[entry.boat];
            if (boat && entry.dist) {
                const boatName = formatBoat(entry.boat);
                boatKm[boatName] = (boatKm[boatName] || 0) + entry.dist;
            }
        }
    });
    
    // Sort by distance and take top 20
    const sortedData = Object.entries(boatKm)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20);
    
    const labels = sortedData.map(([name]) => name);
    const data = sortedData.map(([, km]) => km);
    
    if (statsCharts.boat) {
        statsCharts.boat.destroy();
    }
    
    const ctx = document.getElementById('boat-chart').getContext('2d');
    statsCharts.boat = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total km',
                data: data,
                backgroundColor: '#2c5aa0',
                borderColor: '#1a3d6b',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Total Kilometers by Boat'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Distance (km)'
                    }
                }
            }
        }
    });
}

function updateKmByRower() {
    const selectedYears = Array.from(document.getElementById('rower-stats-year-select').selectedOptions)
        .map(option => parseInt(option.value));
    
    const rowerKm = {};
    
    appData.logbooks.forEach(entry => {
        if (selectedYears.length === 0 || selectedYears.includes(entry.year)) {
            entry.crew.forEach(personId => {
                const person = appData.persons[personId];
                if (person && entry.dist) {
                    const rowerName = `${person.fn || ''} ${person.ln || ''}`.trim();
                    rowerKm[rowerName] = (rowerKm[rowerName] || 0) + entry.dist;
                }
            });
        }
    });
    
    // Sort by distance and take top 20
    const sortedData = Object.entries(rowerKm)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20);
    
    const labels = sortedData.map(([name]) => name);
    const data = sortedData.map(([, km]) => km);
    
    if (statsCharts.rower) {
        statsCharts.rower.destroy();
    }
    
    const ctx = document.getElementById('rower-chart').getContext('2d');
    statsCharts.rower = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total km',
                data: data,
                backgroundColor: '#2c5aa0',
                borderColor: '#1a3d6b',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Total Kilometers by Rower'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Distance (km)'
                    }
                }
            }
        }
    });
}

function updateKmOverTime() {
    const selectedYears = Array.from(document.getElementById('time-stats-year-select').selectedOptions)
        .map(option => parseInt(option.value));
    const viewType = document.getElementById('time-stats-type').value;
    
    const timeData = {};
    
    appData.logbooks.forEach(entry => {
        if (selectedYears.length === 0 || selectedYears.includes(entry.year)) {
            const [day, month, year] = entry.date.split('.');
            const monthKey = `${year}-${month.padStart(2, '0')}`;
            
            if (!timeData[monthKey]) {
                timeData[monthKey] = {};
            }
            
            if (viewType === 'boat') {
                const boatName = formatBoat(entry.boat);
                timeData[monthKey][boatName] = (timeData[monthKey][boatName] || 0) + (entry.dist || 0);
            } else {
                entry.crew.forEach(personId => {
                    const person = appData.persons[personId];
                    if (person) {
                        const rowerName = `${person.fn || ''} ${person.ln || ''}`.trim();
                        timeData[monthKey][rowerName] = (timeData[monthKey][rowerName] || 0) + (entry.dist || 0);
                    }
                });
            }
        }
    });
    
    // Get all unique entities and months
    const allEntities = new Set();
    const sortedMonths = Object.keys(timeData).sort();
    
    Object.values(timeData).forEach(monthData => {
        Object.keys(monthData).forEach(entity => allEntities.add(entity));
    });
    
    // Get top 10 entities by total distance
    const entityTotals = {};
    Array.from(allEntities).forEach(entity => {
        entityTotals[entity] = Object.values(timeData)
            .reduce((total, monthData) => total + (monthData[entity] || 0), 0);
    });
    
    const topEntities = Object.entries(entityTotals)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(([entity]) => entity);
    
    // Create datasets for each entity
    const datasets = topEntities.map((entity, index) => {
        const colors = [
            '#2c5aa0', '#e74c3c', '#27ae60', '#f39c12', '#9b59b6',
            '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#d35400'
        ];
        
        return {
            label: entity,
            data: sortedMonths.map(month => timeData[month][entity] || 0),
            backgroundColor: colors[index % colors.length],
            borderColor: colors[index % colors.length],
            borderWidth: 1
        };
    });
    
    if (statsCharts.time) {
        statsCharts.time.destroy();
    }
    
    const ctx = document.getElementById('time-chart').getContext('2d');
    statsCharts.time = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedMonths.map(month => {
                const [year, monthNum] = month.split('-');
                const date = new Date(year, monthNum - 1);
                return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
            }),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Kilometers Over Time by ${viewType === 'boat' ? 'Boat' : 'Rower'}`
                }
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Month'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Distance (km)'
                    }
                }
            }
        }
    });
}