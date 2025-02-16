async function checkRisk(latitude, longitude) {
    try {
        const response = await fetch("http://127.0.0.1:5000/check", { // Use your backend URL
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ latitude, longitude })
        });

        const data = await response.json();
        document.getElementById("result").innerText = `Risk Level: ${data.riskLevel}`;

        if (data.safeZones && data.safeZones.length > 0) {
            alert("🚨 High Earthquake Risk! Proceed to the nearest safe zone.");
            safeZoneMarkers.forEach(marker => map.removeLayer(marker));
            safeZoneMarkers = [];

            data.safeZones.forEach(zone => {
                const marker = L.marker([zone.latitude, zone.longitude]).addTo(map)
                    .bindPopup(`🛑 Safe Zone: ${zone.name}`).openPopup();
                safeZoneMarkers.push(marker);
            });
        }
    } catch (error) {
        console.error("Error checking risk:", error);
        document.getElementById("result").innerText = "Error connecting to the server.";
    }
}
