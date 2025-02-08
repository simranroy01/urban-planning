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
        document.getElementById('landcover_img').src = data.landcover;
        document.getElementById('pop_graph').src = data.pop_graph;
        document.getElementById('built_graph').src = data.built_graph;
    })
    .catch(error => {
        console.error("Fetch Error:", error);
    });
});


