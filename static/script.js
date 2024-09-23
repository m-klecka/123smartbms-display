async function fetchBmsStatus() {
    try {
        let response = await fetch('/status');
        let data = await response.json();

        // Update the content for each section with the received data
        document.getElementById('pack_voltage').textContent = data.pack_voltage;
        document.getElementById('charge_current').textContent = data.charge_current;
        document.getElementById('discharge_current').textContent = data.discharge_current;
        document.getElementById('pack_current').textContent = data.pack_current;
        document.getElementById('soc').textContent = data.soc;
        document.getElementById('lowest_cell_voltage').textContent = data.lowest_cell_voltage;
        document.getElementById('lowest_cell_voltage_num').textContent = data.lowest_cell_voltage_num;
        document.getElementById('highest_cell_voltage').textContent = data.highest_cell_voltage;
        document.getElementById('highest_cell_voltage_num').textContent = data.highest_cell_voltage_num;
        document.getElementById('lowest_cell_temperature').textContent = data.lowest_cell_temperature;
        document.getElementById('lowest_cell_temperature_num').textContent = data.lowest_cell_temperature_num;
        document.getElementById('highest_cell_temperature').textContent = data.highest_cell_temperature;
        document.getElementById('highest_cell_temperature_num').textContent = data.highest_cell_temperature_num;
        document.getElementById('cell_count').textContent = data.cell_count;
        document.getElementById('cell_communication_error').textContent = data.cell_communication_error ? 'Yes' : 'No';
        document.getElementById('allowed_to_discharge').textContent = data.allowed_to_discharge ? 'Yes' : 'No';
        document.getElementById('allowed_to_charge').textContent = data.allowed_to_charge ? 'Yes' : 'No';
        document.getElementById('timestamp').textContent = data.timestamp;
    } catch (error) {
        console.error('Error fetching BMS status:', error);
    }
}

function showPage(page) {
    // Hide all pages
    const pages = document.querySelectorAll('.content-page');
    pages.forEach(p => p.style.display = 'none');
    
    // Show the selected page
    document.getElementById('page-' + page).style.display = 'flex';
}

async function checkConnectionStatus() {
    try {
        let response = await fetch('/connection_status');
        let data = await response.json();

        let statusText = document.getElementById('status-text');
        if (data.connected) {
            statusText.textContent = "Připoeno";
            statusText.style.color = "green";
        } else {
            statusText.textContent = "Odpojeno";
            statusText.style.color = "red";
        }
    } catch (error) {
        console.error('Error fetching connection status:', error);
        let statusText = document.getElementById('status-text');
        statusText.textContent = "Neznamý";
        statusText.style.color = "orange";
    }
}

document.addEventListener("DOMContentLoaded", function() {
    fetchBmsStatus();
    checkConnectionStatus();
    setInterval(fetchBmsStatus, 5000); // Fetch status every 5 seconds
    setInterval(checkConnectionStatus, 5000); // Check connection status every 5 seconds
    showPage('home'); // Show the default page
});


