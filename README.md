# Advanced Data Analysis & Visualisation Engine

This Streamlit app leverages OpenAI's GPT-4 and Code Interpreter to provide advanced data analysis and visualization capabilities for CSV files.

## Features

- Upload multiple CSV files
- Automated analysis using GPT-4 and Code Interpreter
- Interactive chat interface for asking questions about your data
- Dynamic visualization generation
- Moderation checks for user inputs

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/nakranivaibhav/csv_analyzer.git
   cd csv_analyzer
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key:
   - Create a `.streamlit/secrets.toml` file in the project root
   - Add your API key: `OPENAI_API_KEY = "your-api-key-here"`

> **Important**: Never commit your `secrets.toml` file to version control.

## Running the App

To start the Streamlit app, run:

```
streamlit run chat_app.py
```

The app will open in your default web browser.

## Usage

1. Upload one or more CSV files using the file uploader.
2. Once uploaded, use the chat interface to ask questions about your data.
3. The app will analyze your data, generate visualizations, and provide insights based on your queries.

> **Tip**: For best results, ask specific questions about your data or request particular types

## Files

- `chat_app.py`: Main Streamlit application
- `create_assistant.py`: Script to create and configure the OpenAI assistant
- `requirements.txt`: List of Python dependencies

## Notes

- The app uses GPT-4o LLM.
- Uploaded files and generated images are temporarily stored and processed within the app.
- The conversation does not persist between sessions.