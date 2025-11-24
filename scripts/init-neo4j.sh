#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════
# Initialize Neo4j Database
# ═══════════════════════════════════════════════════════════════════════════

set -e

echo "🚀 Initializing Neo4j database..."

# Check if environment variables are set
if [ -z "$NEO4J_URI" ] || [ -z "$NEO4J_USER" ] || [ -z "$NEO4J_PASSWORD" ]; then
  echo "❌ Error: NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set"
  echo ""
  echo "Usage:"
  echo "  export NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io"
  echo "  export NEO4J_USER=neo4j"
  echo "  export NEO4J_PASSWORD=your-password"
  echo "  ./scripts/init-neo4j.sh"
  exit 1
fi

echo "📡 Connecting to: $NEO4J_URI"
echo "👤 User: $NEO4J_USER"

# Run initialization Cypher script
cat neo4j/init.cypher | cypher-shell \
  -a "$NEO4J_URI" \
  -u "$NEO4J_USER" \
  -p "$NEO4J_PASSWORD" \
  --format plain

echo ""
echo "✅ Neo4j database initialized successfully!"
echo ""
echo "Next steps:"
echo "  1. Deploy to Vercel: vercel --prod"
echo "  2. Test health endpoint: curl https://your-project.vercel.app/api/health"
echo "  3. Spawn a story: curl -X POST https://your-project.vercel.app/api/admin/spawn"
