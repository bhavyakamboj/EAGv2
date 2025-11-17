function fetchCarVariants(brand, model, fuelType, transmission, state) {
    const query = `Get variants for ${brand}, ${model}, ${fuelType}, ${transmission} in ${state}`;
    
    return fetch('http://localhost:5000/v1/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .catch(error => {
        console.error('Error fetching car variants:', error);
        throw error;
    });
}