-- RBAC: roles, permissions, assignments, and user overrides

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(128) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);

CREATE TABLE IF NOT EXISTS user_permission_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    effect VARCHAR(8) NOT NULL CHECK (effect IN ('grant', 'deny')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_user_permission_overrides_user_id ON user_permission_overrides(user_id);

-- Seed roles
INSERT INTO roles (name, description) VALUES
    ('admin', 'Full system access'),
    ('recruiter', 'Create and manage own sessions and integrations'),
    ('interviewer', 'Process and review interview sessions'),
    ('viewer', 'Read-only access to sessions')
ON CONFLICT (name) DO NOTHING;

-- Seed permissions
INSERT INTO permissions (key, description) VALUES
    ('sessions:read', 'List and view own sessions'),
    ('sessions:write', 'Update own sessions'),
    ('sessions:delete', 'Delete own sessions'),
    ('sessions:create', 'Create new sessions'),
    ('sessions:read_all', 'View any user sessions'),
    ('sessions:write_all', 'Modify any user sessions'),
    ('sessions:process', 'Run AI processing on sessions'),
    ('ingest:upload', 'Upload transcript files'),
    ('output:edit', 'Edit session AI output'),
    ('chat:use', 'Use session chat'),
    ('interview:read', 'View interview scorecards'),
    ('interview:process', 'Run interview panel merge'),
    ('integrations:microsoft', 'Connect Microsoft account'),
    ('integrations:teams', 'Import Teams transcripts'),
    ('integrations:onedrive', 'Browse and import OneDrive files'),
    ('rbac:manage', 'Assign roles and permission overrides')
ON CONFLICT (key) DO NOTHING;

-- Link roles to permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.key IN (
    'sessions:read', 'sessions:write', 'sessions:delete', 'sessions:create',
    'sessions:process', 'ingest:upload', 'output:edit', 'chat:use',
    'interview:read', 'interview:process',
    'integrations:microsoft', 'integrations:teams', 'integrations:onedrive'
)
WHERE r.name = 'recruiter'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.key IN (
    'sessions:read', 'sessions:process', 'output:edit', 'chat:use',
    'interview:read', 'interview:process'
)
WHERE r.name = 'interviewer'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.key IN ('sessions:read', 'interview:read')
WHERE r.name = 'viewer'
ON CONFLICT DO NOTHING;
