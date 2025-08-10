# Comprehensive API Scraper

This document outlines a Python-based application engineered for the extraction of story data and associated media from a specified API. The architecture is designed for robust operation, incorporating features that enable the process to be interrupted and resumed without any loss of progress, thereby ensuring operational continuity.

### Key Features

* **Resumable Operations**: The application is capable of resuming operations from the last known checkpoint, which guarantees efficiency and data integrity during prolonged or interrupted execution.

* **Efficient Media Handling**: All associated media for each story is systematically downloaded, with an integrated mechanism designed to prevent redundant file transfers.

* **Persistent Authentication**: An authenticated session is maintained and cached, eliminating the need for repeated user authentication for a predefined period.

* **Structured Codebase**: The codebase is segmented into modular, focused components, a design choice that significantly enhances comprehensibility and facilitates long-term maintenance.

### Prerequisites

This application requires the following dependencies to be installed within the Python environment:

* **Python 3.6 or newer**

* **UV**

* **External Libraries**: `requests`, `beautifulsoup4`, `python-dotenv`

### Installation

1.  To acquire the source code, clone the repository using the following command:

    ```sh
    git clone [repository-url]
    cd [repository-name]
    ```

2.  Install the project dependencies from the `uv.lock` file:

    ```sh
    uv sync
    ```

### Configuration

Application configuration is managed via environment variables. A best practice is to copy the provided `example.env` file and rename it to `.env`, then update all the variables with correct value.


### Usage

To operate the application, you must first activate the virtual environment created by `uv`.

1.  Activate the virtual environment:

    ```sh
    # On macOS or Linux
    source .venv/bin/activate
    # On Windows
    .venv\Scripts\activate
    ```

2.  Execute the application from the root directory:

    ```sh
    python main.py
    ```

Upon execution, the script will handle the authentication process and commence the download of files to the destination directory specified by the `DOWNLOAD_PATH` variable.
