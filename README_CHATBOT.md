# AI Appointment Booking Chatbot

A comprehensive appointment booking system with an AI-powered chatbot that can understand natural language and handle appointment operations.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Chat UI │    │   Chatbot API   │    │ Calendar Service│
│  (Tailwind CSS) │◄──►│  (LLM + FastAPI)│◄──►│   (FastAPI)     │
│                 │    │                 │    │                 │
│ - Chat Interface│    │ - Intent Analysis│    │ - Appointments │
│ - Responsive    │    │ - API Orchestration│  │ - Doctors      │
│ - Real-time     │    │ - Conversation Mgmt│  │ - Google Cal   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │
                    ┌─────────────────┐
                    │   Doctor Data   │
                    │   (JSON Store)  │
                    └─────────────────┘
```

## Services

### 1. Calendar Service (Port 8000)
- **Purpose**: Core appointment booking functionality
- **Features**: Book, reschedule, cancel appointments with Google Calendar sync
- **Tech**: FastAPI, PostgreSQL, Google Calendar API

### 2. Chatbot Service (Port 8001)
- **Purpose**: AI-powered natural language interface
- **Features**: Intent classification, entity extraction, conversation management
- **Tech**: FastAPI, LangChain, OpenAI GPT

### 3. React Frontend (Port 3000)
- **Purpose**: User-friendly chat interface
- **Features**: Real-time chat, responsive design, suggested actions
- **Tech**: React, TypeScript, Tailwind CSS

## Prerequisites

- Docker and Docker Compose
- OpenAI API key (for chatbot functionality)
- Google Calendar service account credentials

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository>
cd calendar-booking-chatbot
```

### 2. Environment Configuration

```bash
# Copy and configure chatbot environment
cp chatbot-service/env.example chatbot-service/.env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Start All Services

```bash
docker-compose up --build
```

### 4. Initialize Database

```bash
# Populate sample data
docker-compose exec calendar-service python populate_sample_data.py

# Export doctor data for chatbot
docker-compose exec calendar-service python export_doctor_data.py
```

### 5. Access the Application

- **Chatbot UI**: http://localhost:3000
- **Calendar API**: http://localhost:8000/docs
- **Chatbot API**: http://localhost:8001/docs

## Manual Development Setup

### Calendar Service Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
createdb appointment_db
python create_database.py
python run_migrations.py

# Populate sample data
python populate_sample_data.py

# Run service
python run.py
```

### Chatbot Service Setup

```bash
cd chatbot-service

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp env.example .env
# Edit .env with your OpenAI API key

# Run service
python run_chatbot.py
```

### Frontend Setup

```bash
cd chatbot-frontend

# Install dependencies
npm install

# Start development server
npm start
```

## API Endpoints

### Calendar Service

- `GET /api/v1/doctors/export` - Export doctor data for chatbot
- `POST /api/v1/appointments/` - Book appointment
- `PUT /api/v1/appointments/{id}/reschedule` - Reschedule appointment
- `DELETE /api/v1/appointments/{id}` - Cancel appointment
- `GET /api/v1/appointments/availability/search` - Search availability

### Chatbot Service

- `POST /api/v1/chat/` - Send message to chatbot
- `GET /api/v1/chat/conversation/{id}` - Get conversation history
- `WEBSOCKET /api/v1/chat/ws/{conversation_id}` - Real-time chat

## Chatbot Capabilities

The AI chatbot can understand and handle:

### Intent Classification
- **Book Appointment**: Schedule new appointments
- **Reschedule Appointment**: Change existing appointment times
- **Cancel Appointment**: Cancel bookings
- **Doctor Information**: Provide doctor details and specialties
- **Check Availability**: Find available time slots
- **My Appointments**: Show user's existing bookings

### Entity Extraction
- Dates and times
- Doctor names and specializations
- Patient information
- Medical symptoms and conditions

### Conversation Features
- Context awareness
- Multi-turn conversations
- Suggested actions
- Confirmation workflows
- Error handling

## Sample Interactions

```
User: I want to book an appointment with a cardiologist
Bot: I'd be happy to help you book an appointment! I need a bit more information: your name, your phone number, the type of doctor you need. Could you please provide these details?

User: My name is John Doe, phone is 123-456-7890
Bot: Perfect! I have all the information needed to book your appointment. Here's what I have: doctor_type: cardiologist, patient_name: John Doe, patient_phone: 123-456-7890. Would you like me to proceed with booking this appointment?

User: Yes, please book it for tomorrow at 2 PM
Bot: Great! I've booked your appointment with Dr. Sarah Smith (Cardiology) for tomorrow at 2:00 PM. Your appointment ID is abc-123-def. You'll receive a confirmation email shortly.
```

## Development

### Adding New Intent Types

1. Update `IntentType` enum in `chatbot-service/app/models/chat.py`
2. Add handling logic in `ChatService._generate_response_based_on_intent()`
3. Update LLM prompts if needed

### Customizing Responses

Modify the prompts in `LLMService` class to change how the chatbot responds to different intents.

### Adding New Entities

1. Update `EntityType` enum
2. Add extraction logic in LLM prompts
3. Handle new entities in response generation

## Testing

### Unit Tests

```bash
# Calendar service tests
cd calendar-service
pytest

# Chatbot service tests
cd chatbot-service
pytest
```

### Integration Tests

```bash
# Test end-to-end booking flow
python test_integration.py
```

### Manual Testing

1. Start all services with Docker Compose
2. Access chatbot UI at http://localhost:3000
3. Test various conversation flows
4. Verify appointments appear in calendar service

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Set**
   - Ensure `OPENAI_API_KEY` is set in `chatbot-service/.env`
   - Chatbot will fallback to basic responses without LLM

2. **Database Connection Issues**
   - Check PostgreSQL is running: `docker-compose ps`
   - Verify connection string in environment variables

3. **Google Calendar Not Syncing**
   - Verify service account credentials are mounted
   - Check Google Calendar permissions

4. **WebSocket Connection Issues**
   - Ensure chatbot service is healthy
   - Check browser console for connection errors

### Logs

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs chatbot-service
docker-compose logs calendar-service

# Follow logs in real-time
docker-compose logs -f
```

## Deployment

For production deployment:

1. Set up proper SSL certificates
2. Configure environment variables securely
3. Set up monitoring and logging
4. Configure load balancing
5. Set up database backups
6. Implement proper authentication

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure Docker builds work correctly

## License

[Add your license information here]