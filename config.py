TARGET_COMPANIES = {
    "greenhouse": [
        {"name": "Airbnb",    "token": "airbnb"},
        {"name": "Anthropic", "token": "anthropic"},
    ],
    "ashby": [
        {"name": "Notion", "token": "notion"},
        {"name": "Ramp",   "token": "ramp"},
    ],
}

PREFERRED_STACK = [
    'Python', 'TypeScript', 'JavaScript', 'React', 'Node',
    'FastAPI', 'ML', 'LLM', 'cloud', 'AWS', 'distributed',
]

BIG_TECH_COMPANIES = {
    'Google', 'Meta', 'Apple', 'Amazon', 'Microsoft', 'Netflix',
    'Stripe', 'Airbnb', 'Uber', 'Lyft', 'Salesforce', 'Adobe',
    'Oracle', 'Intel', 'Nvidia', 'Qualcomm', 'LinkedIn', 'Twitter',
    'X', 'Snap', 'Coinbase', 'Robinhood', 'Palantir', 'Databricks',
    'OpenAI', 'Anthropic', 'Figma', 'Notion', 'Canva', 'Atlassian',
    'Shopify', 'Spotify', 'Block', 'Square', 'PayPal', 'Twilio',
    'Cloudflare', 'Datadog', 'MongoDB', 'Snowflake',
}

BLACKLIST = [
    {'company': 'Infosys',      'reason': 'staffing',     'date_added': '2026-05-10'},
    {'company': 'TechStaffing', 'reason': 'scam-pattern', 'date_added': '2026-05-10'},
]

DEDUP_WINDOW_DAYS = 14
HISTORY_RETENTION_DAYS = 14
JD_FETCH_TIMEOUT_SECONDS = 10
DATE_FILTER_HOURS = 48
