# Gates: Bibi always-on operation and 2027-02 relocation

Scope: Keep Bibi available while the current PC is off using another powered computing device (owned computer, robot computer, or optional cloud host), without consuming its scarce C-drive space, and preserve a verified migration path to the home computer in February 2027. The ultimate target is an onboard Physical AI brain; external hosting and paid model APIs are optional design dependencies, not prerequisites.

- [x] G1: Deployment preflight records disk capacity, authenticated database counts, versions, and Redis reachability without modifying the database or disclosing credentials.
  CHECK: .\.venv\Scripts\python.exe -B scripts/deployment/preflight.py --output claudedocs/deployment/preflight_2026-09-11.json
  EXPECT: PREFLIGHT_RECORDED
  EVIDENCE: 2026-09-11; PowerShell; cwd=E:/A2A/our-a2a-project; exit=0; EXPECT matched; stdout bytes=89 SHA256=6a9baf89cb9e9deca682647af20e8a623de45fa104fa81e07af4ac44c63a0029; report SHA256=7799eb768f147f2547d1cdad6085060c3e1ad3901712202ff25dc22862173197; malformed URL/missing configuration/credential-redaction negative controls passed; artifact secret scan passed. Direct command execution, not a gate-check approval record.

- [x] G2: The deployment proposal separates code, secrets, persistent data, backups, and build storage; documents the C-drive constraint and February 2027 move; and identifies the actual autonomous activity paths.
  EVIDENCE: 2026-09-11 manual inspection of ALWAYS_ON_2026-09-11.md against current code; /sleep page mounts MemoryConsolidationCard -> useIdleSleep at 30 minutes; API lifespan has no timer; curiosity explore_batch changes status without a learning operation; replay changes graph weights; Neo4j store-format compatibility remains explicitly unverified. Linter has 9 advisory warnings for manual deployment gates and numeric names/dates; these gates cannot be treated as automated evidence until a target exists.

- [ ] G3: A suitable powered computing device, access method, and unattended activity scope are available; costs are approved only if the chosen route requires spending.
  EVIDENCE: pending; user clarified an onboard Physical AI target on 2026-09-11. An owned device and robot computer are valid alternatives to cloud hosting. Earlier mandatory cloud/API budget framing is withdrawn. No paid host has been provisioned.

- [ ] G4: The selected device runs Bibi's approved runtime and unattended activities with private access, persistent storage, restart recovery, and an explicit inventory of remaining external API dependencies.
  EVIDENCE: pending; device and activity scope are not yet selected. Current chat uses Gemini and embeddings use OpenAI; no offline replacement has been implemented or claimed. No container build or image download has been run on this PC.

- [ ] G5: A restored copy of Bibi's data matches the source's labels, relationships, properties, and application identifiers; a backup restore is demonstrated before cutover.
  EVIDENCE: pending; no source shutdown, export/import, database write, or cutover has been performed.

- [ ] G6: An independent observer verifies access and an approved activity record while the current PC is off, and the February 2027 transfer procedure has a verified backup artifact.
  EVIDENCE: pending; local connectivity checks do not establish this outcome.
