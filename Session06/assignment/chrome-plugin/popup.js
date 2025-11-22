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
    // Dark mode toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    const body = document.body;

    // Load saved preference
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode === 'true') {
        body.classList.add('dark-mode');
    }

    // Toggle handler
    darkModeToggle.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        // Persist preference
        localStorage.setItem('darkMode', body.classList.contains('dark-mode'));
    });



    const brandSelect = document.getElementById('brand');
    const modelSelect = document.getElementById('model');
    const fuelSelect = document.getElementById('fuelType');
    const transmissionSelect = document.getElementById('transmission');
    const stateSelect = document.getElementById('state');
    const fetchButton = document.getElementById('fetchVariants');
    const openWindowButton = document.getElementById('openWindow');
    const resultDiv = document.getElementById('result');
	const jsonInput = document.getElementById('jsonInput');
	const formatBtn = document.getElementById('formatBtn');
	const clearBtn = document.getElementById('clearBtn');
	const finalBox = document.getElementById('finalBox');
	const restPre = document.getElementById('restPre');
	const restDetails = document.getElementById('restDetails');
	const errorEl = document.getElementById('error');

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
        if (!brand || !model) {
            resultDiv.textContent = 'Please select Brand and Model.';
            return;
        }

        // Build query string as requested. Brand/model/fuel/transmission are lowercased like the example; state kept as selected value.
        // const query = `Find the variant of cars with brand as ${brand.toLowerCase()}, model as ${model.toLowerCase()}, fuel type as ${fuel.toLowerCase()}, transmission as ${transmission.toLowerCase()} with state as ${state}`;

        // Build a dynamic query: include a clause only if the value is not empty.
        const queryParts = [];

        // Base phrase
        queryParts.push('Find the on road price of cars with ');

        if (brand) queryParts.push(`brand as ${brand.toLowerCase()},`);
        if (model) queryParts.push(`model as ${model.toLowerCase()},`);
        if (fuel) queryParts.push(`fuel type as ${fuel.toLowerCase()},`);
        if (transmission) queryParts.push(`transmission as ${transmission.toLowerCase()},`);
        if (state) queryParts.push(`and state as ${state}`);

        const query = queryParts.join(', ');

        const queryDisplay = document.getElementById('queryDisplay');
        queryDisplay.textContent = `Query: ${query}`;


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

            // *** NEW: Populate the textarea with the response ***
            jsonInput.value = JSON.stringify(data, null, 2);
            // Optionally reformat the content (uncomment the next line if you want the formatted view immediately)
            formatAndDisplay(jsonInput.value);
            // show pretty JSON in resultDiv for quick feedback
            // resultDiv.textContent = JSON.stringify(data, null, 2);
        } catch (err) {
            resultDiv.textContent = `Network error: ${err.message}`;
        } finally {
            fetchButton.disabled = false;
        }
    });

    // Open a persistent popup window (won't auto-close on outside clicks)
    if (openWindowButton) {
        openWindowButton.addEventListener('click', () => {
            // Ask background to open a new window running popup.html
            if (chrome && chrome.runtime && chrome.runtime.sendMessage) {
                chrome.runtime.sendMessage({ action: 'openPersistentWindow' }, (resp) => {
                    if (chrome.runtime.lastError) {
                        console.error('Error sending openPersistentWindow message:', chrome.runtime.lastError);
                        return;
                    }
                    if (resp && resp.success) {
                        console.log('Opened persistent window, id:', resp.windowId);
                    } else {
                        console.error('Failed to open persistent window:', resp && resp.error);
                    }
                });
            } else {
                // Fallback: open a normal window/tab
                window.open('popup.html', '_blank', 'width=420,height=640');
            }
        });
    }

	function showError(msg) {
		errorEl.textContent = msg;
		errorEl.style.display = msg ? 'block' : 'none';
	}

	function formatAndDisplay(raw) {
		showError('');
		finalBox.style.display = 'none';
		restPre.textContent = '';
		restDetails.removeAttribute('open');

		if (!raw || !raw.trim()) {
			showError('Paste JSON into the input first.');
			return;
		}

		try {
			const obj = JSON.parse(raw);
			// Extract final_response (if present)
			let finalVal = undefined;
			if (Object.prototype.hasOwnProperty.call(obj, 'final_response')) {
				finalVal = obj['final_response'];
			}

			// Prepare remaining object (shallow copy without final_response)
			const remaining = Array.isArray(obj) ? obj.slice() : { ...obj };
			if (finalVal !== undefined && !Array.isArray(remaining)) {
				delete remaining['final_response'];
			}

			// Show final_response highlighted
			if (finalVal !== undefined) {
				finalBox.style.display = 'block';
				finalBox.textContent = typeof finalVal === 'string' ? finalVal : JSON.stringify(finalVal, null, 2);
			} else {
				finalBox.style.display = 'none';
			}

			// Show remaining pretty-printed inside collapsed details
			const remainingText = JSON.stringify(remaining, null, 2);
			restPre.textContent = remainingText;
			// keep details collapsed by default; user can open
		} catch (e) {
			showError('Invalid JSON: ' + e.message);
		}
	}

	formatBtn.addEventListener('click', () => {
		formatAndDisplay(jsonInput.value);
	});

	clearBtn.addEventListener('click', () => {
		jsonInput.value = '';
		finalBox.style.display = 'none';
		restPre.textContent = '';
		showError('');
	});

	// Optional: if extension sends JSON via message, handle it
	chrome.runtime?.onMessage?.addListener((msg) => {
		if (msg?.json) {
			jsonInput.value = typeof msg.json === 'string' ? msg.json : JSON.stringify(msg.json, null, 2);
			formatAndDisplay(jsonInput.value);
		}
	});
});