# AI Sales Trainer PoC

Python microservice for AI-powered sales training capabilities:

**Core Features:**
- **RAG** - Knowledge base for sales training materials
- **Voice** - Real-time audio conversations (OpenAI or ElevenLabs)
- **Evaluation** - Score conversations against methodologies (SPIN, MEDDIC, etc.)

**Conversational Practice:**
- **Chat** - Text-based practice with AI customer personas
- **Scenarios** - Sales scenario management

**AI Assistants:**
- **Questions** - SPIN question creator and reviewer
- **Qualification** - MEDDPICC opportunity analysis
- **Value Proposition** - Golden Circle value prop review
- **Navigation** - Next best action recommendations

## Quick Start

```bash
cd ai-poc
cp .env.example .env
# Edit .env with your API keys
docker compose up -d
```

API available at http://localhost:8000 | Swagger docs at http://localhost:8000/docs

## Standalone Usage

### 1. RAG Knowledge Base

**Ingest documents:**
```bash
# Upload a PDF
curl -X POST http://localhost:8000/rag/ingest \
  -F "file=@./sales_training.pdf"

# Upload a Word doc
curl -X POST http://localhost:8000/rag/ingest \
  -F "file=@./methodology_guide.docx"

# Upload plain text
curl -X POST http://localhost:8000/rag/ingest \
  -F "file=@./quick_tips.txt"
```

**Query the knowledge base:**
```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How should I handle price objections?"}'
```

**Manage documents:**
```bash
# List all documents
curl http://localhost:8000/rag/documents

# Check status
curl http://localhost:8000/rag/status

# Delete a document
curl -X DELETE http://localhost:8000/rag/documents/old_guide.pdf
```

### 2. Conversation Evaluation

**Evaluate a sales conversation:**
```bash
curl -X POST http://localhost:8000/evaluate/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Sales: What challenges are you facing with your current solution?\nProspect: It is too slow and crashes often.\nSales: How does that impact your team productivity?\nProspect: We lose about 2 hours per week.",
    "methodology": "SPIN",
    "persona": "IT Manager"
  }'
```

**Available methodologies:**
```bash
curl http://localhost:8000/evaluate/methodologies
```

Returns: SPIN, MEDDIC, Challenger, Sandler with their scoring categories.

### 3. Voice - Real-time Conversation

Real-time audio-to-audio conversation. This endpoint acts as an auth proxy - it returns credentials for the client to connect directly to the voice provider (OpenAI or ElevenLabs).

**Get conversation credentials:**
```bash
# For OpenAI (default) - no agent_id needed
curl -X POST http://localhost:8000/voice/conversation/start \
  -H "Content-Type: application/json" \
  -d '{}'

# For ElevenLabs - requires agent_id
curl -X POST http://localhost:8000/voice/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "your_elevenlabs_agent_id"}'
```

Response varies by provider:

**OpenAI response:**
```json
{
  "url": "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
  "token": "ephemeral_token_here",
  "provider": "openai"
}
```

**ElevenLabs response:**
```json
{
  "url": "wss://api.elevenlabs.io/v1/convai/conversation?agent_id=...",
  "token": null,
  "provider": "elevenlabs"
}
```

**Connect from client:**
The client connects directly to the provider using the returned credentials:

```javascript
// OpenAI - token sent as auth header
const ws = new WebSocket(url, {
  headers: { Authorization: `Bearer ${token}` }
});

// ElevenLabs - signed URL, no auth header needed
const ws = new WebSocket(url);
```

The `VOICE_PROVIDER` environment variable controls which provider is used ("openai" or "elevenlabs").

### 4. Practice Conversations (Chat)

**Start a practice session:**
```bash
# List available scenarios
curl http://localhost:8000/scenarios

# Get specific scenario
curl http://localhost:8000/scenarios/enterprise_saas_cfo

# Start conversation with a scenario
curl -X POST http://localhost:8000/chat/start \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "enterprise_saas_cfo"}'
```

**Practice the conversation:**
```bash
# Send your message (use conversation_id from start response)
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "your-conversation-id",
    "content": "Hi Sarah, thanks for meeting with me today."
  }'

# List all conversations
curl http://localhost:8000/chat

# Get conversation history
curl http://localhost:8000/chat/{conversation_id}

# End and evaluate
curl -X POST http://localhost:8000/chat/{conversation_id}/end
```

### 5. SPIN Question Review

**Review a discovery question:**
```bash
curl -X POST http://localhost:8000/questions/review \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do you currently track customer interactions?",
    "question_type": "situation",
    "context": "Selling CRM to mid-market retail company"
  }'
```

**List question types:**
```bash
curl http://localhost:8000/questions/types
```

Returns SPIN type validation, score, open/closed analysis, strengths, improvements, and an improved version.

### 6. MEDDPICC Qualification

**Analyze opportunity qualification:**
```bash
curl -X POST http://localhost:8000/qualification/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": "Expecting 30% reduction in reporting time",
    "economic_buyer": "CFO - Sarah Johnson",
    "decision_criteria": "Integration with existing ERP, ease of use",
    "decision_process": "IT review -> Pilot -> Executive approval",
    "paper_process": "Standard procurement, 2-week legal review",
    "implicate_pain": "Manual reporting takes 2 days/week, delaying decisions",
    "champion": "IT Director - Mike Chen, frustrated with current system",
    "competition": "Evaluating Competitor X and building in-house",
    "context": "Mid-market manufacturing company, $50M revenue"
  }'
```

**Get framework reference:**
```bash
curl http://localhost:8000/qualification/framework
```

Returns per-dimension analysis (strong/weak/missing), gap analysis with suggested questions, priority actions, and risk factors.

### 7. Value Proposition Review

**Review your value prop using Golden Circle:**
```bash
curl -X POST http://localhost:8000/value-prop/review \
  -H "Content-Type: application/json" \
  -d '{
    "value_prop": "We help sales teams close more deals faster with AI-powered coaching that identifies skill gaps and provides personalized training recommendations.",
    "target_customer": "Mid-market B2B SaaS companies",
    "industry": "Software/Technology"
  }'
```

**Get framework reference:**
```bash
curl http://localhost:8000/value-prop/golden-circle
curl http://localhost:8000/value-prop/tips
```

Returns Golden Circle analysis (Why/How/What), customer-centricity score, clarity analysis, and an improved version.

### 8. Navigation Advisor

**Get next best action for a deal:**
```bash
curl -X POST http://localhost:8000/navigation/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "current_stage": "discovery",
    "recent_activity": "Had discovery call, customer has manual reporting pain",
    "challenges": "Hard to get meeting with CFO",
    "meddpicc_context": "Champion identified, Economic Buyer unknown"
  }'
```

Returns recommended action, preparation items, questions to ask, red flags, and alternatives.

**Get stage playbook:**
```bash
curl http://localhost:8000/navigation/stages
curl http://localhost:8000/navigation/playbook/discovery
```

### 9. Health & Status

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
curl http://localhost:8000/rag/status
```

## Architecture

```
┌─────────────────┐         HTTP          ┌─────────────────┐
│  NestJS App     │ ───────────────────►  │  Python PoC     │
│  (Auth, UI)     │                       │  (AI Logic)     │
└─────────────────┘                       └────────┬────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────┐
                    ▼                              ▼                  ▼
               ┌─────────┐                  ┌───────────┐      ┌────────────┐
               │ Qdrant  │                  │  OpenAI/  │      │ OpenAI/    │
               │         │                  │  Gemini   │      │ ElevenLabs │
               └─────────┘                  └───────────┘      └────────────┘
                                               (LLM)              (Voice)
```

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_BACKEND` | `local` or `s3` | local |
| `LOCAL_DATA_PATH` | Local storage path | ./data |
| `S3_BUCKET_NAME` | S3 bucket for documents | - |
| `QDRANT_HOST` | Qdrant host | localhost |
| `QDRANT_PORT` | Qdrant port | 6333 |
| `LLM_PROVIDER` | `openai` or `gemini` | openai |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GOOGLE_API_KEY` | Google AI API key | - |
| `VOICE_PROVIDER` | `openai` or `elevenlabs` | openai |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | - |
| `USE_FULL_CONTEXT` | RAG mode: `true` loads all docs, `false` uses vector search | false |

## Project Structure

```
ai-poc/
├── app/
│   ├── api/                    # HTTP endpoints
│   │   ├── rag.py              # Document ingestion & querying
│   │   ├── voice.py            # Voice conversation auth proxy
│   │   ├── evaluate.py         # Conversation scoring
│   │   ├── chat.py             # Practice conversations
│   │   ├── scenarios.py        # Scenario management
│   │   ├── questions.py        # SPIN question review
│   │   ├── qualification.py    # MEDDPICC analysis
│   │   ├── value_prop.py       # Value proposition review
│   │   └── navigation.py       # Next best action advisor
│   ├── services/               # Business logic
│   │   ├── llm.py              # OpenAI/Gemini abstraction
│   │   ├── vector_store.py     # Qdrant integration
│   │   ├── document_processor.py
│   │   ├── voice_service.py    # Voice provider abstraction
│   │   ├── openai_voice_service.py
│   │   ├── elevenlabs_service.py
│   │   ├── conversation.py     # Conversation state management
│   │   ├── evaluation.py       # Evaluation logic
│   │   └── scenarios.py        # Scenario data
│   ├── storage/                # File storage (local/S3)
│   ├── utils/                  # Shared utilities
│   │   ├── llm_helpers.py
│   │   └── json_parser.py
│   ├── config.py
│   ├── constants.py
│   ├── logging_config.py
│   └── main.py
├── tests/                      # Test suite
├── prompts/                    # LLM prompt templates
├── docs/                       # Documentation
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## API Summary

| Prefix | Purpose |
|--------|---------|
| `/health` | Health and readiness checks |
| `/rag` | RAG document Q&A |
| `/voice` | Voice conversation auth proxy (OpenAI/ElevenLabs) |
| `/chat` | Text-based practice conversations |
| `/scenarios` | Practice scenario management |
| `/questions` | SPIN question review |
| `/qualification` | MEDDPICC analysis |
| `/value-prop` | Value proposition review |
| `/navigation` | Next best action advisor |
| `/evaluate` | Conversation evaluation |

### Complete Endpoint Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness check with dependency status |
| POST | `/rag/ingest` | Ingest document (PDF, DOCX, TXT) |
| POST | `/rag/query` | Query knowledge base |
| GET | `/rag/documents` | List all documents |
| DELETE | `/rag/documents/{filename}` | Delete a document |
| GET | `/rag/status` | Get RAG system status |
| POST | `/voice/conversation/start` | Get voice conversation credentials |
| POST | `/evaluate/conversation` | Evaluate a sales conversation |
| GET | `/evaluate/methodologies` | List evaluation methodologies |
| POST | `/chat/start` | Start a practice conversation |
| POST | `/chat/message` | Send message in conversation |
| GET | `/chat` | List all conversations |
| GET | `/chat/{conversation_id}` | Get conversation by ID |
| POST | `/chat/{conversation_id}/end` | End conversation and get evaluation |
| GET | `/scenarios` | List available scenarios |
| GET | `/scenarios/{scenario_id}` | Get specific scenario |
| POST | `/questions/review` | Review a SPIN question |
| GET | `/questions/types` | List SPIN question types |
| POST | `/qualification/analyze` | Analyze opportunity (MEDDPICC) |
| GET | `/qualification/framework` | Get MEDDPICC framework info |
| POST | `/value-prop/review` | Review value proposition |
| GET | `/value-prop/golden-circle` | Get Golden Circle framework info |
| GET | `/value-prop/tips` | Get value prop writing tips |
| POST | `/navigation/recommend` | Get next best action recommendation |
| GET | `/navigation/stages` | List sales stages |
| GET | `/navigation/playbook/{stage}` | Get playbook for specific stage |

## Development

```bash
# Install dependencies
uv sync

# Start Qdrant only
docker compose up qdrant -d

# Run app locally
uv run uvicorn app.main:app --reload

# Lint & format
uv run ruff check .
uv run ruff format .

# Run tests
uv run pytest
```
