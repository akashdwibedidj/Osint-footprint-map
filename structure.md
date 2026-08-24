OSINT_FOOTPRINT_MAPPING
└── backend
    └── app
        ├── __pycache__
        ├── core
        ├── db
        ├── models
        │   ├── __pycache__
        │   ├── finding.py
        │   ├── scan.py
        │   └── target.py
        ├── routers
        ├── services
        │   ├── __pycache__
        │   ├── neo4j_query.py
        │   ├── risk_scoring.py
        │   └── storage.py
        └── tools
            ├── __pycache__
            ├── exif_extractor
            │   ├── __pycache__
            │   ├── __init__.py
            │   ├── router.py
            │   └── service.py
            ├── gitleak_scanner
            │   ├── __pycache__
            │   ├── __init__.py
            │   ├── router.py
            │   └── service.py
            ├── haveibeenpwned(not working! missing api)
                └── __init__.py
                ├── router.py
            │   └── service.py
            ├── instaloader
            │   ├── __pycache__
            │   ├── __init__.py
            │   ├── router.py
            │   └── service.py
            ├── maigret
                    __init__.py
            │   ├── router.py
            │   └── service.py
            └── sherlock
                └── __init__.py
                ├── router.py
            │   └── service.py



backend
├── app/            (above)
├── reports
├── test_repo
├── venv
├── .env
├── init_db.py
├── main.py
├── config.py
├── requirements.txt
├── report.json
├── result.json
└── frontend/       (separate, not expanded)



frontend
├── node_modules
├── public
├── src
│   ├── api
│   │   └── client.ts
│   ├── assets
│   ├── components
│   │   ├── layout
│   │   │   ├── Header.tsx
│   │   │   ├── Shell.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── tools
│   │   │   ├── exif_extractor/ExifExtractorView.tsx
│   │   │   ├── gitleak_scanner/GitleakScannerView.tsx
│   │   │   ├── haveibeenpwned/HaveIBeenPwnedView.tsx
│   │   │   ├── instaloader/InstaloaderView.tsx
│   │   │   ├── maigret/MaigretView.tsx
│   │   │   └── sherlock/SherlockView.tsx
│   │   ├── FindingsTable.tsx
│   │   ├── GraphView.tsx
│   │   ├── History.tsx
│   │   ├── ScanForm.tsx
│   │   └── ScanFormUpload.tsx
│   ├── config
│   │   └── tools.ts
│   ├── pages
│   │   └── Dashboard.tsx
│   ├── types
│   │   └── index.ts
│   ├── App.css
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
├── .env
├── .gitignore
├── .oxlintrc.json
├── docker-compose.yml
├── index.html
├── package.json / package-lock.json
├── postcss.config.js
├── README.md
├── structure.md
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
└── vite.config.ts