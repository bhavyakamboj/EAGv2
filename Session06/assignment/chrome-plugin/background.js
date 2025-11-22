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

    // Allow popup to request a persistent window that doesn't auto-close
    if (request.action === "openPersistentWindow") {
        const url = chrome.runtime.getURL('popup.html');
        // Create a new popup window — this window will remain open until closed by the user
        chrome.windows.create({ url, type: 'popup', width: 420, height: 640 }, (win) => {
            if (chrome.runtime.lastError) {
                console.error('Error creating window:', chrome.runtime.lastError);
                sendResponse({ success: false, error: chrome.runtime.lastError.message });
                return;
            }
            sendResponse({ success: true, windowId: win.id });
        });

        return true; // will respond asynchronously
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