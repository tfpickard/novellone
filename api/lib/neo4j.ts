/**
 * Neo4j Database Connection
 *
 * Provides a singleton driver instance and session management for all API functions.
 * Designed for serverless environments where connections should be reused across invocations.
 */

import neo4j, { Driver, Session, ManagedTransaction, Result } from 'neo4j-driver';

// ───────────────────────────────────────────────────────────────────────────
// Environment Configuration
// ───────────────────────────────────────────────────────────────────────────

const NEO4J_URI = process.env.NEO4J_URI;
const NEO4J_USER = process.env.NEO4J_USER || 'neo4j';
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD;

if (!NEO4J_URI || !NEO4J_PASSWORD) {
  throw new Error(
    'Neo4j connection details missing. Set NEO4J_URI and NEO4J_PASSWORD environment variables.'
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Singleton Driver
// ───────────────────────────────────────────────────────────────────────────

let driver: Driver | null = null;

/**
 * Get or create the Neo4j driver instance.
 * Reuses the same driver across serverless function invocations for efficiency.
 */
export function getDriver(): Driver {
  if (!driver) {
    driver = neo4j.driver(
      NEO4J_URI!,
      neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD!),
      {
        maxConnectionPoolSize: 50,
        connectionAcquisitionTimeout: 60000, // 60 seconds
        maxTransactionRetryTime: 30000, // 30 seconds
      }
    );

    // Verify connectivity
    driver.verifyConnectivity()
      .then(() => console.log('✓ Neo4j driver connected'))
      .catch((err) => {
        console.error('✗ Neo4j connection failed:', err);
        driver = null;
      });
  }

  return driver;
}

/**
 * Close the driver connection.
 * Call this when shutting down the application (not needed in serverless functions).
 */
export async function closeDriver(): Promise<void> {
  if (driver) {
    await driver.close();
    driver = null;
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Session Management
// ───────────────────────────────────────────────────────────────────────────

/**
 * Execute a read query with automatic session management.
 *
 * @param query - Cypher query string
 * @param params - Query parameters
 * @returns Query result
 */
export async function executeRead<T = unknown>(
  query: string,
  params: Record<string, unknown> = {}
): Promise<Result<T>> {
  const driver = getDriver();
  const session = driver.session({ database: 'neo4j', defaultAccessMode: neo4j.session.READ });

  try {
    return await session.run<T>(query, params);
  } finally {
    await session.close();
  }
}

/**
 * Execute a write query with automatic session management.
 *
 * @param query - Cypher query string
 * @param params - Query parameters
 * @returns Query result
 */
export async function executeWrite<T = unknown>(
  query: string,
  params: Record<string, unknown> = {}
): Promise<Result<T>> {
  const driver = getDriver();
  const session = driver.session({ database: 'neo4j', defaultAccessMode: neo4j.session.WRITE });

  try {
    return await session.run<T>(query, params);
  } finally {
    await session.close();
  }
}

/**
 * Execute a transaction with automatic retry logic.
 * Use this for complex multi-statement writes that should be atomic.
 *
 * @param work - Transaction work function
 * @returns Transaction result
 */
export async function executeWriteTransaction<T>(
  work: (tx: ManagedTransaction) => Promise<T>
): Promise<T> {
  const driver = getDriver();
  const session = driver.session({ database: 'neo4j', defaultAccessMode: neo4j.session.WRITE });

  try {
    return await session.executeWrite(work);
  } finally {
    await session.close();
  }
}

/**
 * Execute a read transaction.
 * Use this for complex multi-statement reads that need consistency.
 *
 * @param work - Transaction work function
 * @returns Transaction result
 */
export async function executeReadTransaction<T>(
  work: (tx: ManagedTransaction) => Promise<T>
): Promise<T> {
  const driver = getDriver();
  const session = driver.session({ database: 'neo4j', defaultAccessMode: neo4j.session.READ });

  try {
    return await session.executeRead(work);
  } finally {
    await session.close();
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Health Check
// ───────────────────────────────────────────────────────────────────────────

/**
 * Verify database connectivity and return server info.
 * Useful for health check endpoints.
 */
export async function healthCheck(): Promise<{
  connected: boolean;
  serverInfo?: {
    version: string;
    address: string;
  };
  error?: string;
}> {
  try {
    const driver = getDriver();
    const serverInfo = await driver.getServerInfo();

    return {
      connected: true,
      serverInfo: {
        version: serverInfo.protocolVersion.toString(),
        address: serverInfo.address,
      },
    };
  } catch (error) {
    return {
      connected: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Utility Functions
// ───────────────────────────────────────────────────────────────────────────

/**
 * Convert Neo4j Integer to JavaScript number.
 * Neo4j returns large integers as Integer objects, not native numbers.
 */
export function toNumber(value: unknown): number {
  if (neo4j.isInt(value)) {
    return value.toNumber();
  }
  return typeof value === 'number' ? value : 0;
}

/**
 * Convert Neo4j DateTime to JavaScript Date.
 */
export function toDate(value: unknown): Date | null {
  if (neo4j.isDateTime(value) || neo4j.isDate(value)) {
    return new Date(value.toString());
  }
  if (typeof value === 'string') {
    return new Date(value);
  }
  if (typeof value === 'number') {
    return new Date(value);
  }
  return null;
}

/**
 * Extract properties from a Neo4j node, converting special types.
 */
export function extractNodeProperties<T = Record<string, unknown>>(
  node: unknown
): T {
  if (!node || typeof node !== 'object') {
    return {} as T;
  }

  const props = (node as any).properties || node;
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(props)) {
    if (neo4j.isInt(value)) {
      result[key] = value.toNumber();
    } else if (neo4j.isDateTime(value) || neo4j.isDate(value)) {
      result[key] = new Date(value.toString());
    } else {
      result[key] = value;
    }
  }

  return result as T;
}

/**
 * Check if Tom canonical node exists, create if not.
 * Call this during initialization or health checks.
 */
export async function ensureTomExists(): Promise<void> {
  const query = `
    MERGE (tom:Tom {id: 'tom-canonical'})
    ON CREATE SET
      tom.name = 'Tom',
      tom.description = 'The tinkering engineer who anchors every premise',
      tom.role = 'canonical-character',
      tom.totalAppearances = 0,
      tom.createdAt = timestamp()
    RETURN tom
  `;

  await executeWrite(query);
}

// ───────────────────────────────────────────────────────────────────────────
// Exports
// ───────────────────────────────────────────────────────────────────────────

export { neo4j };
export type { Driver, Session, ManagedTransaction, Result };
