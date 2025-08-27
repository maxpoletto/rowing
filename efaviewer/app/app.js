// Global application state
let appData = {
    logbooks: [],
    boats: {},
    persons: {},
    destinations: {},
    years: [],
    distanceRange: [0, 50],
    logbookTable: null
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

function formatDate(date) {
    // Parse european-style dates, DD.MM.YYYY
    let d;
    if (typeof date === 'string' && /^\d{2}\.\d{2}\.\d{4}$/.test(date)) {
        const [day, month, year] = date.split('.').map(Number);
        d = new Date(year, month - 1, day);
    } else {
        d = new Date(date);
    }
    return d;
}

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

// Load JSON data files
async function loadData() {
    try {
        const [logbooksResponse, boatsResponse, personsResponse, destinationsResponse] = await Promise.all([
            fetch('data/logbooks.json'),
            fetch('data/boats.json'),
            fetch('data/persons.json'),
            fetch('data/destinations.json')
        ]);

        const logbooks = await logbooksResponse.json();
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

        appData.logbooks = logbooks.map(entry => [
            entry.year,
            formatDate(entry.date),
            formatBoat(entry.boat),
            formatCrew(entry.crew),
            entry.dist || 0,
            formatDestination(entry.dest)
        ]);

        // Extract unique years and sort them
        appData.years = [...new Set(logbooks.map(entry => entry.year))].sort((a, b) => b - a);

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
}

const YEAR_COLUMN = 0;
const DATE_COLUMN = 1;
const BOAT_COLUMN = 2;
const CREW_COLUMN = 3;
const DIST_COLUMN = 4;
const DEST_COLUMN = 5;

function initializeTable() {
    const columns = [
        {
            key: 'year',
            hidden: true,
            type: 'string',
        },
        {
            key: 'date',
            label: 'Date',
            type: 'date',
            width: '100px',
            formatter: (value) => value.toLocaleDateString()
        },
        {
            key: 'boat',
            label: 'Boat',
            type: 'string',
        },
        {
            key: 'crew',
            label: 'Crew',
            type: 'string',
        },
        {
            key: 'dist',
            label: 'Distance',
            type: 'number',
            width: '80px',
        },
        {
            key: 'dest',
            label: 'Destination',
            type: 'string',
        }
    ];

    appData.logbookTable = new SortableTable({
        container: '.logbook-table',
        data: appData.logbooks,
        columns: columns,
        rowsPerPage: 50,
        showPagination: true,
        allowSorting: true,
        emptyMessage: 'No logbook entries found'
    });
}

let filterTimer = null;
const FILTER_TIMEOUT_MS = 50;

function applyFilters() {
    if (filterTimer) {
        clearTimeout(filterTimer);
    }
    filterTimer = setTimeout(() => {
        const selectedYears = Array.from(document.getElementById('year-select').selectedOptions)
            .map(option => parseInt(option.value));
        const terms = document.getElementById('search-input').value.toLowerCase().trim().split(' ');
        const slider = document.getElementById('distance-slider');
        const distanceRange = slider.noUiSlider.get().map(Number);

        appData.logbookTable.filter(entry => {
            // Year filter
            if (selectedYears.length > 0 && !selectedYears.includes(entry[YEAR_COLUMN])) {
                return false;
            }

            // Distance filter
            const dist = entry[DIST_COLUMN] || 0;
            if (dist < distanceRange[0] || dist > distanceRange[1]) {
                return false;
            }

            // Search filter
            if (terms.length > 0) {
                const boat = entry[BOAT_COLUMN];
                const boatName = boat ? boat.toLowerCase() : '';
                const crewNames = entry[CREW_COLUMN].toLowerCase();
                if (!terms.every(term => boatName.includes(term) || crewNames.includes(term))) {
                    return false;
                }
            }
            return true;
        })
    }, FILTER_TIMEOUT_MS);
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