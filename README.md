# ScholarProof 🎓🔍

**Evidence before trust.**

ScholarProof is an AI-powered verification platform that helps students verify scholarships, university admission requirements, deadlines, funding claims, and suspicious offers using reliable official sources.

🌐 Live demo: https://scholar-proof.vercel.app
## Screenshots

### Homepage
![ScholarProof Homepage](screenshots/Screenshot%20From%202026-09-14%2009-13-49.png)

### Screenshot Verification
![ScholarProof Screenshot Verification](screenshots/Screenshot%20From%202026-09-14%2009-12-42.png)

### Claim Analysis
![ScholarProof Claim Analysis](screenshots/Screenshot%20From%202026-09-14%2009-12-59.png)

### Security Analysis & Next Steps
![ScholarProof Security Analysis](screenshots/Screenshot%20From%202026-09-14%2009-13-16.png)

### Verification History
![ScholarProof History](screenshots/Screenshot%20From%202026-09-14%2009-13-36.png)

## Problem

Students often find scholarship and admission information through:

- Telegram
- Instagram
- WhatsApp
- unofficial websites
- forwarded screenshots

This information can be outdated, misleading, or unsafe.

## Solution

ScholarProof accepts:

- Text
- URLs
- Screenshots

It checks important claims and gives one of four results:

- ✅ Verified
- ⚠️ Partially Verified
- ❌ Contradicted
- ❓ Insufficient Evidence

It also checks for security risks such as:

- unofficial application channels
- suspicious payment requests
- impersonation
- misleading scholarship claims
- fake deadlines
- Telegram / WhatsApp application scams

## Features

- AI-assisted verification
- Official-source research
- Scholarship checking
- Admission requirement checking
- Deadline verification
- Security analysis
- Screenshot input
- URL verification
- Uzbek / English / Russian interface
- Dark / Light mode
- Verification history
- Responsive design

## Tech Stack

### Frontend
- React
- Vite
- JavaScript
- CSS
- Vercel

### Backend
- Python
- FastAPI
- OpenAI API
- Render

## Architecture

```text
User Input
   ↓
Claim Extraction
   ↓
Web Research
   ↓
Official Source Verification
   ↓
Security Analysis
   ↓
Structured Report