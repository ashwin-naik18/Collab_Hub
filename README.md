# CollabHub

A Flask-based collaboration platform where users can share project ideas, connect with collaborators, and apply to work on innovative projects.

## Features

* User Registration and Login
* Email OTP Verification
* Post Project Ideas
* View Project Details
* Apply to Collaborate on Projects
* Manage Applications
* MySQL Database Integration
* Responsive User Interface

## Tech Stack

* Python
* Flask
* MySQL
* HTML
* CSS
* Jinja2 Templates

## Project Structure

```
CollabHub/
│
├── app.py
├── config.py
├── db.py
├── database.sql
│
├── static/
│   └── favicon.png
│
├── templates/
│   ├── base.html
│   ├── edit_idea.html
│   ├── idea_detail.html
│   ├── index.html
│   ├── login.html
│   ├── my_applications.html
│   ├── post_idea.html
│   ├── register.html
│   └── verify_otp.html
```

## Installation

1. Clone the repository

```bash
git clone <repository-url>
```

2. Move into the project directory

```bash
cd CollabHub
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment variables

Create a `.env` file and add your MySQL and email credentials.

5. Import the database

```bash
mysql -u root -p < database.sql
```

6. Run the application

```bash
python app.py
```

## Future Improvements

* Real-time collaboration features
* Team chat functionality
* Project recommendation system
* User profiles and portfolios
* AI-powered collaborator matching

