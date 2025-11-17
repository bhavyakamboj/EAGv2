// background.js
chrome.runtime.onInstalled.addListener(() => {
    console.log("Chrome extension installed.");
});

// Listen for messages from popup.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "fetchVariants") {
        fetchVariants(request.data)
            .then(response => sendResponse({ success: true, data: response }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // Indicates that the response will be sent asynchronously
    }
});

// Function to fetch car variants from the Flask backend
async function fetchVariants(data) {
    const response = await fetch("http://localhost:5000/v1/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ query: data })
    });

    if (!response.ok) {
        throw new Error("Network response was not ok");
    }

    return response.json();
}