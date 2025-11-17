// options.js

document.addEventListener('DOMContentLoaded', function () {
    const brandSelect = document.getElementById('brand');
    const modelSelect = document.getElementById('model');
    const fuelTypeSelect = document.getElementById('fuelType');
    const transmissionSelect = document.getElementById('transmission');
    const stateSelect = document.getElementById('state');
    const fetchButton = document.getElementById('fetchVariants');

    // Populate dropdowns with options
    const brands = ['TATA'];
    const models = ['HARRIER'];
    const fuelTypes = ['DIESEL', 'ELECTRIC'];
    const transmissions = ['AUTOMATIC', 'MANUAL'];
    const states = ['DELHI', 'TAMILNADU', 'GUJARAT', 'KERALA', 'MAHARASHTRA'];

    brands.forEach(brand => {
        const option = document.createElement('option');
        option.value = brand;
        option.textContent = brand;
        brandSelect.appendChild(option);
    });

    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
    });

    fuelTypes.forEach(fuelType => {
        const option = document.createElement('option');
        option.value = fuelType;
        option.textContent = fuelType;
        fuelTypeSelect.appendChild(option);
    });

    transmissions.forEach(transmission => {
        const option = document.createElement('option');
        option.value = transmission;
        option.textContent = transmission;
        transmissionSelect.appendChild(option);
    });

    states.forEach(state => {
        const option = document.createElement('option');
        option.value = state;
        option.textContent = state;
        stateSelect.appendChild(option);
    });

    fetchButton.addEventListener('click', function () {
        const selectedBrand = brandSelect.value;
        const selectedModel = modelSelect.value;
        const selectedFuelType = fuelTypeSelect.value;
        const selectedTransmission = transmissionSelect.value;
        const selectedState = stateSelect.value;

        const query = `Find the on-road price of cars with brand as ${selectedBrand}, model as ${selectedModel}, fuel type as ${selectedFuelType}, transmission as ${selectedTransmission} with state as ${selectedState}`;
        console.log(query)
        // Call the API to fetch variants
        fetchVariants(query, selectedState);
    });

    function fetchVariants(query, state) {
        // Implement the API call to fetch car variants based on the query
        // POST to http://127.0.0.1:5000/v1/chat with JSON body { "query": "<query>" }
        console.log(`Fetching variants with query: ${query} for state: ${state}`);

        const resultDiv = document.getElementById('result');
        if (resultDiv) resultDiv.textContent = 'Loading...';

        fetch('http://127.0.0.1:5000/v1/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        })
        .then(async (resp) => {
            if (!resp.ok) {
                const txt = await resp.text();
                throw new Error(`HTTP ${resp.status}: ${txt}`);
            }
            return resp.json();
        })
        .then((data) => {
            // pretty-print JSON into result div
            if (resultDiv) resultDiv.textContent = JSON.stringify(data, null, 2);
            console.log('Variants response:', data);
        })
        .catch((err) => {
            console.error('Error fetching variants:', err);
            if (resultDiv) resultDiv.textContent = `Error: ${err.message}`;
        });
    }
});