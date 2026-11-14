# EconLens – Conversational AI for Economic Data Analysis

## Overview

EconLens is a conversational AI application that allows users to analyze U.S. GDP and Core CPI inflation data using natural-language questions.

The application retrieves economic data from FRED, processes it, and generates interactive visualizations and AI-powered explanations.

## Technologies Used

- **Python** – Backend and data processing
- **Streamlit** – Web interface
- **Google Gemini** – Conversational AI
- **Pandas** – Economic data analysis
- **Plotly** – Interactive visualizations
- **FRED** – Economic data source

## Installation

**1. Clone the repository**

```bash
git clone <repository-url>
cd <repository-folder>
```

**2. Install dependencies**

```bash
python -m pip install -r requirements.txt
```

**3. Configure the API key**

Create a `.env` file in the project directory (or copy `.env.example`) and add:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Get an API key from [Google AI Studio](https://aistudio.google.com/apikey).

**4. Run the application**

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## Features

- Retrieve historical and latest GDP and Core CPI data
- Calculate GDP growth and inflation rates
- Analyze economic trends over time
- Compare GDP growth with Core CPI inflation
- Generate interactive economic visualizations
- Answer natural-language economic questions using Gemini

## Data Sources

- [FRED – Gross Domestic Product (GDP)](https://fred.stlouisfed.org/series/GDP)
- [FRED – Core Consumer Price Index (CPILFESL)](https://fred.stlouisfed.org/series/CPILFESL)

## Notes

- An internet connection is required to retrieve FRED data.
- Gemini requires a valid API key.
- The application supports rule-based question handling when Gemini is unavailable.
