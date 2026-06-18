"""Centralized server endpoint constants — single source of truth.

All Beep.AI.Server paths live here. Client and support modules
import from this module instead of hardcoding paths.
"""

V1_CHAT_COMPLETIONS = "/v1/chat/completions"
V1_MODELS = "/v1/models"
V1_MESSAGES = "/v1/messages"
V1_RESPONSES = "/v1/responses"
V1_EMBEDDINGS = "/v1/embeddings"
V1_HEALTH = "/v1/health"

V1_API_TOKENS_CHECK = "/v1/api/tokens/check"

V1_API_AGENTS_BUNDLES_IMPORT = "/v1/api/agents/bundles/import"

V1_AGENT_CODING_EXECUTE = "/v1/api/agent-framework/agents/beep.agent.coding/execute"
V1_AGENT_CODING_SESSIONS = "/v1/api/agent-framework/agents/beep.agent.coding/sessions"
V1_AGENT_CODING_SKILLS = "/v1/api/agent-framework/agents/beep.agent.coding/skills"

V1_RAG_QUERY = "/v1/rag/query"
V1_RAG_COLLECTIONS = "/v1/rag/collections"
V1_RAG_COLLECTION_QUERY = "/v1/rag/collections/{collection_id}/query"

# Deprecated — sunset 2026-12-31; use V1_RAG_* for new code.
V1_API_RAG_QUERY = "/v1/api/rag/query"
V1_API_RAG_COLLECTIONS = "/v1/api/rag/collections"
V1_API_RAG_COLLECTION_QUERY = "/v1/api/rag/collections/{collection_id}/query"

V1_COMPACTION = "/v1/api/agent-framework/agents/beep.agent.coding/compact"

V1_MCP = "/v1/mcp"
MCP_REGISTRY = "/mcp/registry"

V1_TOOLING = "/v1/tooling"

V1_SERVICES = "/v1/services"
V1_VERSION = "/v1/version"

CAPABILITY_DISCOVERY_TIMEOUT = 5.0
