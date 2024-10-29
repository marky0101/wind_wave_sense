var map = L.map('map').setView([8.926317, 124.158692], 7);
var currentMarker = null;
let hourlyChart;
let directionChart;
let periodChart;

// OpenStreetMap tile layer
var streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    zoom: 16,
    minZoom: 7,
    maxZoom: 10,
}).addTo(map);

// OpenTopoMap tile layer
var topoLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    zoom: 7,
    minZoom: 7,
    maxZoom: 10,
    attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap'
});

// Layer control to switch between street map and topographic map
var baseMaps = {
    "Street Map": streetLayer,
    "Topographic Map": topoLayer
};
L.control.layers(baseMaps).addTo(map);

// Define custom icon for marker
var customIcon = L.icon({
    iconUrl: '../static/assets/marker.png', // Replace with your custom marker image path
    iconSize: [38, 45], // Size of the icon
    iconAnchor: [22, 45], // Point of the icon which will correspond to marker's location
    popupAnchor: [-3, -45] // Point from which the popup should open relative to the iconAnchor
});

// Initialize empty charts
function initCharts() {
    const hourlyCtx = document.getElementById('hourlyWindWaveChart').getContext('2d');
    hourlyChart = new Chart(hourlyCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Hourly Wind Wave Height',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                fill: false,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true }
            }
        }
    });

    const directionCtx = document.getElementById('windWaveDirectionChart').getContext('2d');
    directionChart = new Chart(directionCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Hourly Wind Wave Direction',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                fill: false,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true }
            }
        }
    });

    const periodCtx = document.getElementById('windWavePeriodChart').getContext('2d');
    periodChart = new Chart(periodCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Hourly Wind Wave Period',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                fill: false,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true }
            }
        }
    });
}

// Function to create or update a chart
function createOrUpdateChart(chart, ctx, labels, data, label) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.update();
}

// Function to handle click on the map
function handleMapClick(e) {
    var lat = e.latlng.lat.toFixed(6);
    var lng = e.latlng.lng.toFixed(6);

    fetchWindWaveData(lat, lng);
}

// Fetch wind wave data from server
function fetchWindWaveData(lat, lng) {
    fetch('/get-stored-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lng })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateWindWaveData(data.current);

            // Update latitude and longitude in the container
            document.getElementById('latitude').innerText = lat;
            document.getElementById('longitude').innerText = lng;

            // Remove previous marker if it exists
            if (currentMarker) map.removeLayer(currentMarker);

            // Add new marker with custom icon
            currentMarker = L.marker([lat, lng], { icon: customIcon }).addTo(map)
                .bindPopup(`Latitude: ${lat}<br>Longitude: ${lng}`)
                .openPopup();

            // Plot hourly wind wave data
            createOrUpdateChart(
                hourlyChart,
                hourlyChart.ctx,
                data.hourly.time,
                data.hourly.wind_wave_height,
                'Hourly Wind Wave Height'
            );

            // Check if direction data exists
            const directionData = data.hourly.wind_wave_direction || Array(data.hourly.time.length).fill(null);
            createOrUpdateChart(
                directionChart,
                directionChart.ctx,
                data.hourly.time,
                directionData,
                'Hourly Wind Wave Direction'
            );

            // Check if period data exists
            const periodData = data.hourly.wind_wave_period || Array(data.hourly.time.length).fill(null);
            createOrUpdateChart(
                periodChart,
                periodChart.ctx,
                data.hourly.time,
                periodData,
                'Hourly Wind Wave Period'
            );

            // Analyze safety
            analyzeSafety(data.current.wind_wave_height, data.current.wind_wave_direction, data.current.wind_wave_period);

        } else {
            alert('No data found for this location.');
        }
    })
    .catch(error => console.error('Error:', error));
}

// Update wind wave data in the table
function updateWindWaveData(data) {
    document.getElementById('windHeight').innerText = data.wind_wave_height || 'N/A';
    document.getElementById('windDirection').innerText = data.wind_wave_direction || 'N/A';
    document.getElementById('windPeriod').innerText = data.wind_wave_period || 'N/A';
}

// Analyze safety based on the wind wave data
function analyzeSafety(windHeight, windDirection, windPeriod) {
    let analysis = '';
    let isSafe = true;

    // Define safety thresholds
    const heightThreshold = 2; // meters
    const periodThreshold = 5; // seconds

    // Analyze wind direction
    if (windDirection) {
        const direction = getWindDirection(windDirection);
        analysis += `The wind is coming from the <strong>${direction}</strong> direction.<br>`;
    } else {
        analysis += `Wind direction data is not available.<br>`;
    }

    // Analyze wind wave height
    if (windHeight > heightThreshold) {
        analysis += `Warning: The wind wave height is <strong>${windHeight} meters</strong>, which is considered dangerous for sailing.<br>`;
        isSafe = false;
    } else {
        analysis += `The wind wave height of <strong>${windHeight} meters</strong> is safe for sailing.<br>`;
    }

    // Analyze wind wave period
    if (windPeriod < periodThreshold) {
        analysis += `<strong>Caution:</strong> The wind wave period is <strong>${windPeriod} seconds</strong>, indicating turbulent conditions.<br>`;
        isSafe = false;
    } else {
        analysis += `The wind wave period of <strong>${windPeriod} seconds</strong> is safe for sailing.<br>`;
    }

    // Final safety summary
    if (isSafe) {
        analysis += `<strong>Overall Result:</strong> Conditions are safe for sailing.<br>`;
    } else {
        analysis += `<strong>Overall Result:</strong> Conditions are not safe for sailing.<br>`;
    }

    // Update the NLP analysis output with bold formatting
    document.getElementById('nlpOutput').innerHTML = analysis; // Use innerHTML to render HTML content

}

// Function to convert wind direction in degrees to compass direction
function getWindDirection(degrees) {
    const directions = [
        { name: 'North', min: 337.5, max: 360 },
        { name: 'North', min: 0, max: 22.5 },
        { name: 'East', min: 22.5, max: 67.5 },
        { name: 'South', min: 67.5, max: 112.5 },
        { name: 'West', min: 112.5, max: 157.5 },
        { name: 'South', min: 157.5, max: 202.5 },
        { name: 'West', min: 202.5, max: 247.5 },
        { name: 'North', min: 247.5, max: 292.5 },
        { name: 'East', min: 292.5, max: 337.5 },
    ];

    for (const dir of directions) {
        if (degrees >= dir.min && degrees < dir.max) {
            return dir.name;
        }
    }
    return 'Unknown Direction';
}

// Add event listener to the map for clicks
map.on('click', handleMapClick);

// Initialize charts
initCharts();
