// popup.js

const models = {
    "TATA": {
        "HARRIER": {
            "DIESEL": ["AUTOMATIC", "MANUAL"],
            "ELECTRIC": ["AUTOMATIC"]
        }
    },
    "MAHINDRA": {
        "BE6": {
            "ELECTRIC": ["AUTOMATIC"]
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const brandSelect = document.getElementById('brand');
    const modelSelect = document.getElementById('model');
    const fuelSelect = document.getElementById('fuelType');
    const transmissionSelect = document.getElementById('transmission');
    const stateSelect = document.getElementById('state');
    const fetchButton = document.getElementById('fetchVariants');
    const resultDiv = document.getElementById('result');

    function clearOptions(select) {
        while (select.options.length > 0) select.remove(0);
    }

    function populateSelect(selectElement, options, placeholder = null) {
        clearOptions(selectElement);
        if (placeholder !== null) {
            const ph = document.createElement('option');
            ph.value = '';
            ph.textContent = placeholder;
            selectElement.appendChild(ph);
        }
        options.forEach(option => {
            const opt = document.createElement('option');
            opt.value = option;
            opt.textContent = option;
            selectElement.appendChild(opt);
        });
    }

    // populate brands
    const brands = Object.keys(models);
    populateSelect(brandSelect, brands, 'Select Brand');

    // populate states (static)
    const states = ['DELHI', 'TAMILNADU', 'MAHARASHTRA', 'GUJARAT', 'KERALA', 'ODISHA', 'PUNJAB', 'WESTBENGAL', 'MEGHALAYA', 'BIHAR', 'TELANGANA'];
    populateSelect(stateSelect, states, 'Select State');

    // initialize dependent selects
    populateSelect(modelSelect, [], 'Select Model');
    modelSelect.disabled = true;
    populateSelect(fuelSelect, [], 'Select Fuel Type');
    fuelSelect.disabled = true;
    populateSelect(transmissionSelect, [], 'Select Transmission');
    transmissionSelect.disabled = true;

    brandSelect.addEventListener('change', () => {
        const brand = brandSelect.value;
        // reset downstream
        populateSelect(fuelSelect, [], 'Select Fuel Type');
        fuelSelect.disabled = true;
        populateSelect(transmissionSelect, [], 'Select Transmission');
        transmissionSelect.disabled = true;
        resultDiv.textContent = '';

        if (!brand) {
            populateSelect(modelSelect, [], 'Select Model');
            modelSelect.disabled = true;
            return;
        }

        const modelNames = Object.keys(models[brand] || {});
        populateSelect(modelSelect, modelNames, 'Select Model');
        modelSelect.disabled = false;
    });

    modelSelect.addEventListener('change', () => {
        const brand = brandSelect.value;
        const model = modelSelect.value;

        populateSelect(fuelSelect, [], 'Select Fuel Type');
        fuelSelect.disabled = true;
        populateSelect(transmissionSelect, [], 'Select Transmission');
        transmissionSelect.disabled = true;
        resultDiv.textContent = '';

        if (!brand || !model) return;

        const fuelTypes = Object.keys(models[brand][model] || {});
        populateSelect(fuelSelect, fuelTypes, 'Select Fuel Type');
        fuelSelect.disabled = fuelTypes.length === 0;
    });

    fuelSelect.addEventListener('change', () => {
        const brand = brandSelect.value;
        const model = modelSelect.value;
        const fuel = fuelSelect.value;

        populateSelect(transmissionSelect, [], 'Select Transmission');
        transmissionSelect.disabled = true;
        resultDiv.textContent = '';

        if (!brand || !model || !fuel) return;

        const transmissions = (models[brand][model] && models[brand][model][fuel]) || [];
        populateSelect(transmissionSelect, transmissions, 'Select Transmission');
        transmissionSelect.disabled = transmissions.length === 0;
    });

    fetchButton.addEventListener('click', async () => {
        // gather values
        const brand = brandSelect.value;
        const model = modelSelect.value;
        const fuel = fuelSelect.value;
        const transmission = transmissionSelect.value;
        const state = stateSelect.value || '';

        // validation
        if (!brand || !model || !fuel || !transmission) {
            resultDiv.textContent = 'Please select Brand, Model, Fuel Type and Transmission.';
            return;
        }

        // Build query string as requested. Brand/model/fuel/transmission are lowercased like the example; state kept as selected value.
        const query = `Find the variant of cars with brand as ${brand.toLowerCase()}, model as ${model.toLowerCase()}, fuel type as ${fuel.toLowerCase()}, transmission as ${transmission.toLowerCase()} with state as ${state}`;

        resultDiv.textContent = 'Loading...';
        fetchButton.disabled = true;

        try {
            const resp = await fetch('http://127.0.0.1:5000/v1/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });

            if (!resp.ok) {
                const txt = await resp.text();
                resultDiv.textContent = `Error ${resp.status}: ${txt}`;
                return;
            }

            const data = await resp.json();
            // show pretty JSON
            resultDiv.textContent = JSON.stringify(data, null, 2);
        } catch (err) {
            resultDiv.textContent = `Network error: ${err.message}`;
        } finally {
            fetchButton.disabled = false;
        }
    });
});