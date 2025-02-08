var map = L.map('map').setView([20.5937, 78.9629], 5);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

var drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

var drawControl = new L.Control.Draw({
    draw: {
        polygon: false,
        polyline: false,
        circle: false,
        marker: false,
        circlemarker: false,
        rectangle: true
    },
    edit: {
        featureGroup: drawnItems
    }
});
map.addControl(drawControl);

map.on(L.Draw.Event.CREATED, function (event) {
    var layer = event.layer;
    drawnItems.clearLayers();
    drawnItems.addLayer(layer);

    var bounds = layer.getBounds();
    var coordinates = [
        bounds.getSouthWest().lng, bounds.getSouthWest().lat, 
        bounds.getNorthEast().lng, bounds.getNorthEast().lat
    ];

    console.log("Selected Coordinates:", coordinates);

    fetch('/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bounds: coordinates })
    })
    .then(response => response.json())
    .then(data => {
        console.log("API Response:", data);

        if (data.error) {
            console.error("Server Error:", data.error);
            alert("Error: " + data.error);
            return;
        }

        // Display Land Cover Image
        document.getElementById('landcover_img').src = `http://127.0.0.1:8000/${data.landcover}`;

        // Plot Population Data
        const popData = data.population_data;
        const builtData = data.built_area_data;

        if (popData && popData.date && popData.pop) {
            Plotly.newPlot('pop-graph', [{
                x: popData.date,
                y: popData.pop,
                type: 'line',
                line: { color: '#3B82F6' }
            }], {
                margin: { t: 0 },
                xaxis: { title: 'Date' },
                yaxis: { title: 'Population' }
            });

            // Population Change Graph
            Plotly.newPlot('pop-change-graph', [{
                x: popData.date,
                y: popData.change,
                type: 'bar',
                marker: { color: '#10B981' }
            }], {
                margin: { t: 0 },
                xaxis: { title: 'Date' },
                yaxis: { title: 'Change (%)' }
            });
        } else {
            console.warn("No valid population data received.");
        }

        // Plot Built Area Data
        if (builtData && builtData.date && builtData.area) {
            Plotly.newPlot('built-area-graph', [{
                x: builtData.date,
                y: builtData.area,
                type: 'line',
                line: { color: '#EF4444' }
            }], {
                margin: { t: 0 },
                xaxis: { title: 'Date' },
                yaxis: { title: 'Built-up Area' }
            });

            // Built Area Change Graph
            Plotly.newPlot('built-change-graph', [{
                x: builtData.date,
                y: builtData.change,
                type: 'bar',
                marker: { color: '#F59E0B' }
            }], {
                margin: { t: 0 },
                xaxis: { title: 'Date' },
                yaxis: { title: 'Change (%)' }
            });
        } else {
            console.warn("No valid built area data received.");
        }

    })
    .catch(error => {
        console.error("Fetch Error:", error);
        alert("Failed to communicate with the server. Check the console for details.");
    });
});

