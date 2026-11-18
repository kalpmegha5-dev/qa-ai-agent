# 🤖 QA AI Agent – Intelligent Test Assistant

An AI-powered Quality Engineering assistant designed to help QA professionals analyse software requirements, identify potential gaps and risks, and generate structured test scenarios and test cases.

**Project Status:** 🚧 Working Prototype | Actively Evolving

## 🎯 Project Overview

The QA AI Agent explores how Generative AI can support requirement analysis and test design across software development projects.

Designed with a Senior QA Lead mindset, the application focuses on improving requirement understanding, identifying potential testing risks, and strengthening QA coverage — particularly for retail, e-commerce and omnichannel applications.

## ✨ Current Capabilities

### 1. AI-Powered Requirement Analysis
- Analyse user stories and business requirements.
- Identify potential requirement gaps, ambiguities and conflicts.
- Highlight external system dependencies.
- Assess potential business and QA risks.
- Identify assumptions and requirement readiness.

### 2. Intelligent QA Scenario Generation
Derive testing scenarios across four coverage categories:
- Positive scenarios
- Negative scenarios
- Boundary scenarios
- Edge cases

### 3. Consolidated BA / PO Clarification
- Generate business clarification questions.
- Present questions together instead of asking them individually.
- Accept consolidated BA / PO responses.
- Reassess clarifications and display resolved items and remaining gaps.
- Maintain clarification-round history during the application session.

### 4. AI Test Case Generation
Generate structured test cases from user stories, including:
- Test case ID and category
- Scenario and preconditions
- Execution steps
- Expected results
- Priority
- Assumptions and requirement gaps

## 🛒 Example Use Case

**Scenario:** A customer wants to place an online order using a credit card or gift card.

The assistant can explore testing considerations such as:
- Successful credit card payment and order creation.
- Gift card payment and insufficient balance.
- Split payment scenarios.
- Payment gateway failures and timeouts.
- Duplicate payment requests.
- Payment success with order creation failure.
- Payment and order status inconsistencies.

These are AI-generated testing considerations and should be validated against confirmed business rules.

## 🏗️ Application Architecture

QA Engineer  
↓  
Streamlit User Interface  
↓  
Python QA Logic  
↓  
Ollama Local LLM  
↓  
Structured Requirement Analysis / QA Scenarios / Test Cases

## 🧰 Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11 | Core application development |
| Streamlit | Interactive user interface |
| Ollama | Local LLM execution |
| Qwen 2.5 3B | AI-powered requirement analysis and test generation |
| Requests | Communication with Ollama API |
| Pandas | Structured data presentation |
| Git & GitHub | Version control and portfolio |

## 🚀 Run Locally

### Prerequisites
- Python 3.11
- Git
- Ollama installed on your machine

### 1. Clone the repository

```bash
git clone https://github.com/kalpmegha5-dev/qa-ai-agent.git
cd qa-ai-agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Download the AI model

```bash
ollama pull qwen2.5:3b
```

Ensure Ollama is running locally.

### 5. Launch the application

```bash
python -m streamlit run app.py
```

The application will open in your browser.

## 🔒 Privacy Considerations

This prototype uses Ollama to run the configured language model locally.

Requirement content is sent to the local Ollama service rather than a paid cloud AI API. Avoid entering confidential, personally identifiable or production-sensitive information unless your environment is approved for that data.

## ⚠️ Current Limitations

- AI output quality depends on the selected model and the clarity of the input requirements.
- Local model inference can take time depending on available hardware.
- Generated findings and test cases require review by a QA professional.
- The application is a prototype and is not yet validated for production use.

## 🛣️ Future Enhancements

- Improve AI reasoning and requirement traceability.
- Add downloadable test case reports.
- Introduce defect analysis and API test generation.
- Add automated validation and regression coverage.
- Explore additional AI models and evaluation techniques.
- Expand support for enterprise and omnichannel testing workflows.

## 👩‍💻 About This Project

This is a hands-on AI in Quality Engineering initiative built to explore practical applications of Generative AI in software testing.

The project combines 13+ years of QA domain experience with Python, local LLMs and AI-assisted workflows.

**Built with a Quality Engineering mindset.**