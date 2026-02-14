-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    stark_invoice_id TEXT UNIQUE,
    amount REAL NOT NULL,
    customer_name TEXT NOT NULL,
    customer_tax_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    fee REAL,
    net_amount REAL,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    error_message TEXT
);

-- Transfers
CREATE TABLE IF NOT EXISTS transfers (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    stark_transfer_id TEXT UNIQUE,
    external_id TEXT UNIQUE,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    completed_at TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    error_message TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- Events Log (auditoria)
CREATE TABLE IF NOT EXISTS events_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    metadata TEXT,
    timestamp TEXT NOT NULL,
    processed INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_stark_id ON invoices(stark_invoice_id);
CREATE INDEX IF NOT EXISTS idx_transfers_invoice ON transfers(invoice_id);
CREATE INDEX IF NOT EXISTS idx_transfers_external_id ON transfers(external_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events_log(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events_log(timestamp);
