# Chrome Car Variant Selector Extension

This Chrome extension allows users to select car specifications such as brand, model, fuel type, transmission, and state from dropdown menus. Based on the selections, it generates a query to fetch car variants and their prices from a Flask backend.

## Project Structure

- **manifest.json**: Contains metadata about the Chrome extension, including its name, version, permissions, and the files it uses.
- **popup.html**: Defines the HTML structure for the popup that appears when the extension icon is clicked. It includes dropdowns for selecting brand, model, fuel type, transmission, and state.
- **popup.css**: Contains styles for the `popup.html`, ensuring the dropdowns and other elements are visually appealing and user-friendly.
- **popup.js**: Contains the JavaScript logic for the popup. It handles user interactions, populates the dropdowns with data from the backend, and constructs the query based on user selections.
- **background.js**: Runs in the background and manages events for the extension. It can handle API requests and responses.
- **content.js**: Interacts with web pages if needed, allowing the extension to modify content or extract information from the current page.
- **utils/api.js**: Contains utility functions for making API calls to the Flask backend. It constructs the request to fetch car variants based on user input.
- **options.html**: Provides an options page for the extension, allowing users to configure settings if necessary.
- **options.js**: Contains the JavaScript logic for the options page, handling user input and saving settings.

## Installation

1. Download or clone the repository.
2. Open Chrome and navigate to `chrome://extensions/`.
3. Enable "Developer mode" in the top right corner.
4. Click on "Load unpacked" and select the `chrome-plugin` directory.
5. The extension should now be installed and visible in your Chrome toolbar.

## Usage

1. Click on the extension icon in the Chrome toolbar.
2. A popup will appear with dropdown menus for selecting the car specifications.
3. After making your selections, the extension will generate a query to fetch the car variants and display the results.

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes. 

## License

This project is licensed under the MIT License.