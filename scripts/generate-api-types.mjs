import fs from 'node:fs/promises';
import path from 'node:path';
import openapiTS, { astToString } from 'openapi-typescript';
const base=process.env.API_BASE_URL || 'http://127.0.0.1:18100';
const schema=await fetch(`${base}/openapi.json`).then(async r=>{if(!r.ok)throw new Error(`OpenAPI ${r.status}`);return r.json();});
const target=path.resolve(import.meta.dirname,'../packages/api-types/schema.d.ts');
await fs.writeFile(target, '// Generated from Python OpenAPI. Run pnpm types:api.\n'+astToString(await openapiTS(schema)));
console.log('API contract types generated.');
