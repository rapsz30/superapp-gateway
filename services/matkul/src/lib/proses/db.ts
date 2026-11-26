import { Pool, type PoolClient } from "pg";
import { randomUUID } from "crypto";

// Satu pool per proses (aman untuk hot reload Next.js dev).
const g = globalThis as unknown as { __pgPool?: Pool; __pgReady?: Promise<void> };

function pool(): Pool {
  if (!g.__pgPool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) throw new Error("DATABASE_URL belum diset");
    g.__pgPool = new Pool({ connectionString });
  }
  return g.__pgPool;
}

const SCHEMA = `
CREATE TABLE IF NOT EXISTS matkul_file (
  id          TEXT PRIMARY KEY,
  nama_file   TEXT,
  data        BYTEA NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS matkul_khs (
  ref        TEXT PRIMARY KEY,
  file_id    TEXT,
  data       JSONB NOT NULL,
  keyakinan  REAL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Konteks panduan prodi disimpan saat ekstraksi, supaya rekomendasi dan semua revisi untuk KHS yang sama
-- memakai versi panduan yang sama walau kaprodi mengaktifkan versi baru di tengah proses.
ALTER TABLE matkul_khs ADD COLUMN IF NOT EXISTS pengajuan_id TEXT;
ALTER TABLE matkul_khs ADD COLUMN IF NOT EXISTS panduan_versi INT;
ALTER TABLE matkul_khs ADD COLUMN IF NOT EXISTS panduan_teks TEXT;
ALTER TABLE matkul_khs ADD COLUMN IF NOT EXISTS maks_sks INT;
-- Hasil bacaan KHS per isi berkas, dipakai bersama oleh pratinjau dan proses pengajuan (disimpan sementara).
CREATE TABLE IF NOT EXISTS matkul_bacaan (
  sidik      TEXT PRIMARY KEY,
  data       JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Rencana pratinjau yang dilihat mahasiswa; dipakai proses pengajuan untuk berkas yang sama (disimpan sementara).
CREATE TABLE IF NOT EXISTS matkul_pratinjau (
  sidik           TEXT NOT NULL,
  pemilik         TEXT NOT NULL,
  panduan_id      TEXT NOT NULL,
  semester_target INT NOT NULL,
  data            JSONB NOT NULL,
  perubahan       JSONB NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (sidik, pemilik, panduan_id, semester_target)
);
ALTER TABLE matkul_khs ADD COLUMN IF NOT EXISTS pemilik TEXT;
ALTER TABLE matkul_khs ADD COLUMN IF NOT EXISTS panduan_id TEXT;
CREATE TABLE IF NOT EXISTS matkul_rencana (
  ref             TEXT PRIMARY KEY,
  khs_ref         TEXT NOT NULL REFERENCES matkul_khs(ref),
  semester_target INT,
  data            JSONB NOT NULL,
  parent_ref      TEXT,
  revisi_ke       INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
`;

async function ready() {
  if (!g.__pgReady) {
    g.__pgReady = pool()
      .query(SCHEMA)
      .then(() => undefined)
      .catch((e) => {
        g.__pgReady = undefined;
        throw e;
      });
  }
  return g.__pgReady;
}

export function newId(prefix: string) {
  return `${prefix}_${randomUUID().replace(/-/g, "").slice(0, 8)}`;
}

export async function query<T = any>(text: string, params: unknown[] = []): Promise<T[]> {
  await ready();
  const res = await pool().query(text, params as any[]);
  return res.rows as T[];
}

export async function queryTx<T>(
  client: PoolClient,
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  const res = await client.query(text, params as any[]);
  return res.rows as T[];
}

export async function withTransaction<T>(fn: (client: PoolClient) => Promise<T>): Promise<T> {
  await ready();
  const client = await pool().connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (e) {
    await client.query("ROLLBACK");
    throw e;
  } finally {
    client.release();
  }
}
