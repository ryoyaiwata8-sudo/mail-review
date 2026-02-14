# Weekly Report Automation System

## Overview
Automates the generation of weekly reports by analyzing phone and email interactions using Google Gemini (or OpenAI) APIs.

## Features
- **Data Ingestion**: Parses email logs (Excel) and phone logs (MP3 filenames/audio).
- **Audio Transcription**: Automatically transcribes `.mp3` files using Gemini 2.5 Flash or OpenAI Whisper.
- **Evaluation**: specific, evidence-based grading of agent interactions.
- **Reporting**: Generates a Markdown report (`weekly_report.md`).

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    -   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        # Windows: copy .env.example .env
        ```
    -   Edit `.env` and add your API Keys (`GEMINI_API_KEY` or `OPENAI_API_KEY`).
    -   (Optional) Set `GEMINI_MODEL_NAME` (default: `gemini-2.5-flash`).

## Usage

1.  **Prepare Data**:
    -   Place Audio files (`.mp3`) in `data/`.
    -   Place Email logs (`.xlsx`) in `data/`.

2.  **Run the Script**:
    ```bash
    python main.py
    ```

3.  **Check Output**:
    -   The report will be generated as `weekly_report.md`.
