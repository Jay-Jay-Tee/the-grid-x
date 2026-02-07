grid-x-hybrid/
│
├── coordinator/                    # Central server (ONE instance)
│   ├── __init__.py
│   ├── main.py                     # FastAPI server (entry point)
│   ├── database.py                 # SQLite database operations
│   ├── scheduler.py                # Job assignment logic
│   ├── workers.py                  # Worker registry management
│   ├── credit_manager.py           # Credit/balance system
│   ├── websocket.py                # Real-time WebSocket updates
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile                  # Container for coordinator
│
├── worker/                         # Worker agent (MULTIPLE instances)
│   ├── __init__.py
│   ├── main.py                     # Worker agent (polls coordinator)
│   ├── resource_monitor.py         # CPU/GPU/memory monitoring
│   ├── docker_manager.py           # Docker container management
│   ├── task_executor.py            # Execute tasks in containers
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile                  # Container for worker
│
├── sdk/                            # Client SDK (for end users)
│   ├── src/
│   │   ├── index.ts                # Main export
│   │   ├── client.ts               # GridXClient class
│   │   ├── types.ts                # TypeScript interfaces
│   │   └── websocket.ts            # WebSocket client
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md                   # SDK usage docs
│
├── ui/                             # Web dashboard (React)
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── App.tsx                 # Main app component
│   │   ├── components/
│   │   │   ├── Dashboard.tsx       # Worker + Job overview
│   │   │   ├── Marketplace.tsx     # Submit jobs
│   │   │   ├── Credits.tsx         # Credit balance view
│   │   │   ├── WorkerCard.tsx      # Worker display card
│   │   │   └── JobCard.tsx         # Job display card
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts     # WebSocket hook
│   │   │   └── useGridX.ts         # SDK integration hook
│   │   ├── services/
│   │   │   └── api.ts              # API wrapper (uses SDK)
│   │   ├── styles/
│   │   │   └── App.css
│   │   └── index.tsx               # React entry point
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile                  # Container for UI
│
├── common/                         # Shared utilities (optional)
│   ├── __init__.py
│   ├── schemas.py                  # Shared data models (Pydantic)
│   ├── utils.py                    # Helper functions
│   └── constants.py                # Shared constants
│
├── config/                         # Configuration files
│   ├── coordinator.env.example     # Coordinator env variables
│   ├── worker.env.example          # Worker env variables
│   └── docker-security.yml         # Docker security policies
│
├── scripts/                        # Utility scripts
│   ├── setup.sh                    # Initial setup script
│   ├── start-dev.sh                # Start development environment
│   └── test-integration.sh         # Integration tests
│
├── tests/                          # Test suite
│   ├── coordinator/
│   │   ├── test_scheduler.py
│   │   ├── test_credits.py
│   │   └── test_api.py
│   ├── worker/
│   │   ├── test_monitor.py
│   │   ├── test_docker.py
│   │   └── test_executor.py
│   └── integration/
│       └── test_end_to_end.py
│
├── docs/                           # Documentation
│   ├── architecture.md             # System architecture
│   ├── api-reference.md            # API documentation
│   ├── deployment.md               # Deployment guide
│   └── security.md                 # Security practices
│
├── docker-compose.yml              # Multi-container orchestration
├── docker-compose.dev.yml          # Development override
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── README.md                       # Project overview
├── LICENSE                         # License file
└── QUICKSTART.md                   # Quick start guide