// Global application state
let appData = {
    logbooks: [],
    boats: {},
    persons: {},
    destinations: {},
    years: [],
    distanceRange: [0, 50],
};

let charts = {
    boat: null,
    rower: null,
    time: null
};

let tables = {
    logbook: null,
    boat: null,
    rower: null
};

// Column indices in tables.logbook
const YEAR_COLUMN = 0;
const DATE_COLUMN = 1;
const BOAT_COLUMN = 2;
const CREW_COLUMN = 3;
const DIST_COLUMN = 4;
const DEST_COLUMN = 5;

// Entry point
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await loadData();
        initializeUI();
        setupEventListeners();
        applyLogbookFilters();
    } catch (error) {
        console.error('Failed to initialize application:', error);
        alert('Failed to load data. Please check the console for details.');
    }
});

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
            parseDate(entry.date),
            formatBoat(entry.boat),
            formatCrew(entry.crew),
            entry.dist || 0,
            formatDestination(entry.dest)
        ]);

        // Extract unique years and sort them
        appData.years = [...new Set(logbooks.map(entry => entry.year))]
            .filter(year => year >= 2011) /* Hack until we clean the data */
            .sort((a, b) => b - a);

        // Calculate distance range
        const distances = logbooks.map(entry => entry.dist || 0).filter(d => d > 0);
        if (distances.length > 0) {
            appData.distanceRange = [0, Math.max(...distances)];
        }

    } catch (error) {
        console.error('Error loading data:', error);
        throw error;
    }
}

function initializeUI() {
    initializeTabs();
    initializeSliders();
    initializeTable();
    document.querySelectorAll('.search-input').forEach(input => {
        input.placeholder = 'Search for boats, crew, and destinations';
    });
}

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

function initializeSliders() {
    const minYear = Math.min(...appData.years);
    const maxYear = Math.max(...appData.years);

    const statsSliders = [
        { id: 'logbook-year-slider', minSpan: 'logbook-year-min', maxSpan: 'logbook-year-max', change: applyLogbookFilters },
        { id: 'logbook-dist-slider', minSpan: 'logbook-dist-min', maxSpan: 'logbook-dist-max', change: applyLogbookFilters,
            start: [0, 100], range: { 'min': 0, '20%': 5, '40%': 10, '60%': 20, '80%': 50, 'max': 100 } },
        { id: 'boat-year-slider', minSpan: 'boat-year-min', maxSpan: 'boat-year-max', change: updateStatistics },
        { id: 'rower-year-slider', minSpan: 'rower-year-min', maxSpan: 'rower-year-max', change: updateStatistics },
        { id: 'time-year-slider', minSpan: 'time-year-min', maxSpan: 'time-year-max', change: updateStatistics }
    ];
    statsSliders.forEach(config => {
        const slider = document.getElementById(config.id);
        const minSpan = document.getElementById(config.minSpan);
        const maxSpan = document.getElementById(config.maxSpan);

        const start = config.start || [maxYear, maxYear+1];
        const range = config.range || { 'min': minYear, 'max': maxYear+1 };
        noUiSlider.create(slider, {
            start: start,
            connect: true,
            range: range,
            step: 1,
            tooltips: false,
            format: {
                to: value => Math.round(value),
                from: value => Number(value)
            }
        });

        slider.noUiSlider.on('update', (values) => {
            minSpan.textContent = values[0];
            maxSpan.textContent = values[1];
        });

        slider.noUiSlider.on('change', config.change);
    });
}

function setupEventListeners() {
    document.getElementById('logbook-search-input').addEventListener('input', applyLogbookFilters);
    document.getElementById('time-search-input').addEventListener('input', updateKmOverTime);
    document.getElementById('logbook-reset-btn').addEventListener('click', resetLogbookFilters);
    document.getElementById('time-reset-btn').addEventListener('click', resetTimeFilters);

    const helpModal = document.getElementById('search-help-modal');
    document.querySelectorAll('.search-help-link').forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            helpModal.style.display = 'block';
        });
    });
    helpModal.addEventListener('click', () => {
        helpModal.style.display = 'none';
    });
    helpModal.querySelector('.close-btn').addEventListener('click', () => {
        helpModal.style.display = 'none';
    });
}

////////////////////////////////////////////////////////////////////////////
// Helpers
////////////////////////////////////////////////////////////////////////////

function extractTerms(inputId) {
    const input = document.getElementById(inputId).value.toLowerCase().trim();
    return input.length === 0 ? [] : input.match(/"[^"]*"|'[^']*'|[^\s]+/g).map(term => {
        // Remove surrounding quotes if present
        if ((term.startsWith('"') && term.endsWith('"')) || (term.startsWith("'") && term.endsWith("'"))) {
            return term.slice(1, -1);
        }
        return term;
    });
}

function parseDate(date) {
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

////////////////////////////////////////////////////////////////////////////
// Logbook
////////////////////////////////////////////////////////////////////////////

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
            label: 'Distance (km)',
            type: 'number',
            width: '80px',
        },
        {
            key: 'dest',
            label: 'Destination',
            type: 'string',
        }
    ];

    tables.logbook = new SortableTable({
        container: '#logbook-table',
        data: appData.logbooks,
        columns: columns,
        rowsPerPage: 50,
        showPagination: true,
        allowSorting: true,
        sort: { column: 'date', ascending: false },
        emptyMessage: 'No logbook entries found'
    });
}

let filterTimer = null;
const FILTER_TIMEOUT_MS = 100;

function applyLogbookFilters() {
    if (filterTimer) {
        clearTimeout(filterTimer);
    }
    filterTimer = setTimeout(() => {
        const yearSlider = document.getElementById('logbook-year-slider');
        const yearRange = yearSlider.noUiSlider.get().map(Number);
        const distanceSlider = document.getElementById('logbook-dist-slider');
        const distanceRange = distanceSlider.noUiSlider.get().map(Number);
        const terms = extractTerms('logbook-search-input');

        tables.logbook.filter(entry => {
            // Year filter
            const year = entry[YEAR_COLUMN];
            if (year < yearRange[0] || year >= yearRange[1]) {
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
                const dest = entry[DEST_COLUMN].toLowerCase();
                if (!terms.every(term => boatName.includes(term) || crewNames.includes(term) || dest.includes(term))) {
                    return false;
                }
            }
            return true;
        })
    }, FILTER_TIMEOUT_MS);
}

// Reset all filters to default state
function resetLogbookFilters() {
    document.getElementById('logbook-search-input').value = '';
    const yearSlider = document.getElementById('logbook-year-slider');
    yearSlider.noUiSlider.set([Math.min(...appData.years), Math.max(...appData.years) + 1]);
    const distanceSlider = document.getElementById('logbook-dist-slider');
    distanceSlider.noUiSlider.set([0, 100]);
    applyLogbookFilters();
}

////////////////////////////////////////////////////////////////////////////
// Statistics
////////////////////////////////////////////////////////////////////////////

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

function createBarChart(canvasId, title, xtitle, ytitle, labels, data, existingChart) {
    if (existingChart) {
        existingChart.destroy();
    }

    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
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
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: title !== null,
                    text: title
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: xtitle !== null,
                        text: xtitle
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: ytitle !== null,
                        text: ytitle
                    }
                }
            }
        }
    });
}

////////////////////////////////////////////////////////////////////////////
// Statistics: distance by entity
////////////////////////////////////////////////////////////////////////////

function updateDistanceByEntity(yearRange, entityExtractor, canvasId, tableContainer, existingChart, existingTable) {
    const entityKm = {};

    appData.logbooks.forEach(entry => {
        const year = entry[YEAR_COLUMN];
        if (year >= yearRange[0] && year < yearRange[1]) {
            const entities = entityExtractor(entry);
            entities.forEach(entityName => {
                entityKm[entityName] = (entityKm[entityName] || 0) + entry[DIST_COLUMN];
            });
        }
    });

    // Sort by distance
    const sortedData = Object.entries(entityKm)
        .sort((a, b) => b[1] - a[1]);

    // Chart shows top 20
    const chartLabels = sortedData.slice(0, 20).map(([name]) => name);
    const chartData = sortedData.slice(0, 20).map(([, km]) => km);
    const chart = createBarChart(canvasId, null, null, 'Distance (km)', chartLabels, chartData, existingChart);

    let table = existingTable;
    if (!table) {
        table = new SortableTable({
            container: tableContainer,
            data: sortedData,
            columns: [
                {
                    key: 'name',
                    label: 'Name',
                    type: 'string',
                },
                {
                    key: 'km',
                    label: 'Kilometers',
                    type: 'number',
                    width: '80px'
                }
            ],
            rowsPerPage: 25,
            showPagination: true,
            allowSorting: true,
            sort: { column: 'km', ascending: false },
            emptyMessage: 'No data found'
        });
    } else {
        table.setData(sortedData);
    }
    return { chart, table };
}

function updateKmByBoat() {
    const yearSlider = document.getElementById('boat-year-slider');
    const yearRange = yearSlider.noUiSlider.get().map(Number);

    const boatExtractor = (entry) => [entry[BOAT_COLUMN]];

    const { chart, table } = updateDistanceByEntity(
        yearRange,
        boatExtractor,
        'boat-chart',
        '#boat-table',
        charts.boat,
        tables.boat
    );

    charts.boat = chart;
    tables.boat = table;
}

function updateKmByRower() {
    const yearSlider = document.getElementById('rower-year-slider');
    const yearRange = yearSlider.noUiSlider.get().map(Number);

    const rowerExtractor = (entry) => entry[CREW_COLUMN].split(',').map(name => name.trim());

    const { chart, table } = updateDistanceByEntity(
        yearRange,
        rowerExtractor,
        'rower-chart',
        '#rower-table',
        charts.rower,
        tables.rower
    );

    charts.rower = chart;
    tables.rower = table;
}

////////////////////////////////////////////////////////////////////////////
// Statistics: Monthly kilometers
////////////////////////////////////////////////////////////////////////////

function updateKmOverTime() {
    const yearSlider = document.getElementById('time-year-slider');
    const yearRange = yearSlider.noUiSlider.get().map(Number);
    const terms = extractTerms('time-search-input');

    const monthlyTotals = {};

    appData.logbooks.forEach(entry => {
        const year = entry[YEAR_COLUMN];
        if (year < yearRange[0] || year >= yearRange[1]) {
            return;
        }

        // Search filter
        if (terms.length > 0) {
            const boatName = entry[BOAT_COLUMN].toLowerCase();
            const crewNames = entry[CREW_COLUMN].toLowerCase();
            const destName = entry[DEST_COLUMN].toLowerCase();
            if (!terms.every(term => boatName.includes(term) || crewNames.includes(term) || destName.includes(term))) {
                return;
            }
        }

        const d = entry[DATE_COLUMN];
        const monthKey = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}`;
        monthlyTotals[monthKey] = (monthlyTotals[monthKey] || 0) + (entry[DIST_COLUMN] || 0);
    });

    // Create sorted list of months in range
    const allMonths = [];
    for (let year = yearRange[0]; year < yearRange[1]; year++) {
        for (let month = 1; month <= 12; month++) {
            const monthKey = `${year}-${month.toString().padStart(2, '0')}`;
            allMonths.push(monthKey);
        }
    }
    const data = allMonths.map(month => monthlyTotals[month] || 0);
    const labels = allMonths.map(month => {
        const [year, monthNum] = month.split('-');
        const date = new Date(year, monthNum - 1);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
    });

    const scope = terms.length > 0 ? `("${terms.join('" AND "')}")` : 'the whole club';
    const title = `Monthly kilometers from 1.1.${yearRange[0]} to 1.1.${yearRange[1]} for ${scope}`;

    charts.time = createBarChart('time-chart', title, 'Month', 'Distance (km)', labels, data, charts.time);
}

function resetTimeFilters() {
    const yearSlider = document.getElementById('time-year-slider');
    yearSlider.noUiSlider.set([Math.min(...appData.years), Math.max(...appData.years) + 1]);
    document.getElementById('time-search-input').value = '';
    updateKmOverTime();
}
