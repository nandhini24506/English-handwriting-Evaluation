# English Handwriting Evaluation

## Website, Backend and Database Integration

This branch contains my contribution to the EHE 2.0 project, focusing on the website interface, Flask backend, authentication, database integration, and supporting application features.

## Project Overview

EHE 2.0 is a web-based application designed to help users evaluate English handwriting and review feedback through a website interface.

My contribution focuses on connecting the website pages with backend functionality and database operations.

## My Contribution

### 1. Website Frontend
- Developed and integrated HTML templates for the application.
- Created pages for login, registration, dashboard, history, uploads, and results.
- Added pages for practice, student progress, and teacher functionality.
- Integrated shared layouts and styling for a consistent user experience.

### 2. Flask Backend
- Integrated application routes and page navigation using Flask.
- Worked on user authentication and access control.
- Connected website forms and pages with backend operations.
- Integrated student progress, teacher features, and report generation where implemented.

### 3. Database Integration
- Worked on MySQL connectivity and database operations.
- Updated the database schema in `schema.sql`.
- Integrated database functionality with the Flask application.
- Supported the storage and retrieval of application data.

### 4. Application Integration
- Worked on connecting frontend pages, backend routes, and database functionality.
- Updated project dependencies and documentation.
- Supported testing of application routes and backend features.

## Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Database:** MySQL
- **Testing:** Pytest
- **Version Control:** Git and GitHub

## Project Structure

```text
EHE/
├── app.py
├── auth.py
├── database.py
├── create_admin.py
├── progress.py
├── teacher.py
├── reports.py
├── schema.sql
├── requirements.txt
├── templates/
├── static/
└── tests/
```

*Note: The actual repository branch must contain the files in the structure shown above for this tree to be accurate.*

## Setup and Execution

1. Install Python and MySQL.
2. Clone the project repository.
3. Create and activate a Python virtual environment.
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Configure the required environment variables using `.env.example` as a reference.
6. Create and configure the MySQL database using the provided schema.
7. Start the Flask application using the project's configured entry point.

Refer to the application's configuration and database setup instructions before running it.

**Website Frontend, Flask Backend, and Database Integration**. This includes connecting the user interface with backend routes, authentication, database operations, and supporting application functionality.

AI evaluation, handwriting image processing, and OCR are shared project areas and are not claimed here as my individual contribution.

## Repository

[English Handwriting Evaluation — GitHub](https://github.com/nandhini24506/English-handwriting-Evaluation)

## Academic Project

EHE 2.0 — English Handwriting Evaluation
