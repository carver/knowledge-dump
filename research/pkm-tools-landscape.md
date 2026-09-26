# PKM tools landscape (2026-09-25)

Goal: one private, local, agent-friendly hub over Evernote/Keep exports, bookmarks, repo TODOs, host notes, and structured records (contacts).

Activity data: GitHub API (`repos/{r}` pushed_at, `releases?per_page=1`), pulled 2026-09-25. "Last rel" = newest GitHub release. Star counts omitted. Unverified claims are marked (unverified).

## TL;DR

- Markdown-folder tools are the safe core. Obsidian, SilverBullet, Foam, zk, nb and Basic Memory all read the same folder, so the choice is reversible. Obsidian is proprietary but free for any use ([license][obs-lic]).
- SilverBullet (MIT, release 2026-09-22) is the best OSS fit for a single hub. Plain markdown, self-hosted PWA with offline mode, and Lua queries over frontmatter give you "records as pages" ([site][sb]). Its MCP servers are community-built ([Ahmad-A0][sb-mcp1], [plug][sb-mcp2]).
- Obsidian is the strongest editor. Bases (a core plugin) gives table/card views over frontmatter ([help][obs-bases]), there's an official CLI since 1.12, though it drives the running app and isn't headless ([help][obs-cli]), and the official Importer handles both Evernote and Google Keep ([importer][obs-imp]).
- For contacts, structured data wants a real DB. Grist (Apache-2.0, SQLite files, [README][grist]) or plain SQLite + Datasette (with the official `datasette-mcp` plugin, [repo][ds-mcp]) are the most agent-friendly. NocoDB changed to the "Sustainable Use License" in 2026 ([LICENSE][noco-lic]), so it's no longer OSS.
- Monica is in limbo. v5 never left beta (last beta 2025-04, [releases][monica-rel]), 4.x last shipped 2024-05, and a from-scratch "Monica v3" is promised "before the end of 2026" ([v3 page][monica-v3]). The hosted instance will be wiped end of Dec 2026 ([PR #7978][monica-pr]). Don't adopt it now. vCard files (Radicale/khard) or a SQLite/Grist table plus a wiki page per person is safer.
- Logseq split in April 2026. The markdown-file version is now "Logseq OG", maintenance-only ([post][lsq-split], [repo][lsq-og]). The new DB version is 2.0.1 "Beta" (2026-07, [release][lsq-rel]). Avoid either for now.
- Bookmarks: Karakeep (AGPL, official MCP + CLI + agent skills, mobile apps, [README][karakeep], [MCP docs][karakeep-mcp]) is the most agent-ready. linkding (MIT, SQLite, REST) is the minimal option ([README][linkding]).
- Dead or stale: Reor (archived), Kuzu (archived 2025-10), Chandler (archived), Dendron (maintenance only), Memex (last release 2020), Dataview (last release 2025-04), dogsheep evernote/takeout importers (2021/2023). Details in the tables.

## 1. PKM / linked notes

| Tool | What | License | Storage | Local/self-host | Sync | Mobile capture | API/CLI/MCP | Last rel / status | Structured |
|---|---|---|---|---|---|---|---|---|---|
| Obsidian | Markdown vault editor | Proprietary, free for all use [obs-lic] | Plain .md | Local app | Paid Sync, or any file sync (git/Syncthing) | Yes, native apps | Official CLI (needs running app) [obs-cli]; community MCP via Local REST API [mcp-obs] | 1.13.8, 2026-08-21 [obs-rel] | Frontmatter + Bases [obs-bases] |
| SilverBullet | Self-hosted markdown wiki, programmable | MIT [gh-sb] | Plain .md folder [sb] | Self-host web/PWA | Server is the source of truth; offline PWA [sb] | PWA only | HTTP; community MCPs [sb-mcp1][sb-mcp2] | 2.11.1, 2026-09-22 | Frontmatter/tags + Lua queries [sb] |
| Logseq (DB) | Outliner, graph DB | AGPL-3.0 | DB (SQLite-backed, unverified); "Markdown mirror" planned [lsq-split] | Local | E2EE Logseq sync [lsq-split] | Apps | MCP server + headless CLI in progress [lsq-split] | 2.0.1 beta, 2026-07-13 [lsq-rel] | Typed properties/classes (unverified detail) |
| Logseq OG | Old file-based outliner | AGPL-3.0 | Plain .md | Local | File sync | Apps | Plugin API | Maintenance only [lsq-split]; repo push 2026-05-28 [lsq-og] | Block properties |
| Trilium (TriliumNext) | Hierarchical notes, all-in-one | AGPL-3.0 [trilium] | SQLite [trilium-etapi] | Desktop + self-host server | Own sync server [trilium] | Mobile web frontend [trilium] | ETAPI REST; built-in optional MCP server, auth required since v0.105 [trilium-mcp][trilium-105] | v0.106.0, 2026-09-25 | Labels, relations, promoted attributes [trilium-etapi] |
| Joplin | Evernote-like notebooks | AGPL-3.0-or-later (some subdirs differ) [joplin-lic] | SQLite local, Markdown notes | Local; optional Joplin Server | Nextcloud/WebDAV/Dropbox/OneDrive/Joplin Cloud, E2EE [joplin] | Yes, native apps | Data API, terminal CLI; community MCPs [joplin-mcp] | v3.7.18, 2026-09-11 | Tags only |
| Foam | VS Code wiki-links extension | MIT [foam-lic] | Plain .md | Local | git | No | VS Code | vscode@0.44.6, 2026-09-01 | Frontmatter |
| Dendron | VS Code hierarchical notes | Apache-2.0 | .md | Local | git | No | | Maintenance only [dendron]; push 2025-11 | Schemas |
| Zettlr | Markdown editor, academic | GPL-3.0 | .md | Local | File sync | No | | v4.8.0, 2026-09-18 | Frontmatter |
| AFFiNE | Docs + whiteboard + DB blocks | MIT client, separate server license [affine-lic] | CRDT/local DB (unverified) | Local + self-host server | Own server | Apps | | stable v0.27.4, 2026-08-18; canary daily | DB blocks |
| Anytype | Object-based local-first notes | "Any Source Available License" (not OSS) [anytype-lic] | Encrypted local objects | Local, P2P / self-host any-sync [anytype] | any-sync, E2EE | Apps | gRPC API; official MCP + CLI (MIT) [anytype-mcp][anytype-cli] | v0.57.1-beta, 2026-09-22 | Types/relations (strong) |
| SiYuan | Block-based notes | AGPL-3.0 | JSON files + SQLite index (unverified) | Local/docker | Paid or S3/WebDAV (unverified) | Apps | HTTP API | v3.8.5, 2026-09-22 | Attribute views (DB) |
| Memos (added) | Keep-like timeline, quick capture | MIT [memos] | SQLite default (unverified) | Self-host | Server | Web/PWA + web clipper [memos] | REST API (unverified); MCP not found | v0.31.0, 2026-09-19 | Tags |
| Basic Memory (added) | Markdown KB built for LLM via MCP | AGPL-3.0 [basic-mem] | Plain .md + local index | Local | Files | No | Native MCP [basic-mem] | v0.23.2, 2026-08-25 | Observations/relations in md |

Not covered, since they're server wikis rather than personal tools: Outline (BSL, not OSS [outline-lic]), Wiki.js (AGPL, v2.5.315 2026-09-21), Docmost (AGPL, v0.96.0).

## 2. Structured + wiki hybrids

| Tool | What | License | Storage | API / MCP | Last rel | Notes |
|---|---|---|---|---|---|---|
| Grist (grist-core) | Spreadsheet-DB, Python formulas | Apache-2.0 [grist] | One SQLite file per doc [grist] | REST; built-in MCP (`GRIST_MCP_ENABLED`) is **full edition**, which is free for individuals; community MCPs for core [grist] | v1.7.19, 2026-09-06 | Two-way refs, markdown cells. Best DB fit for contacts |
| NocoDB | Airtable-like UI over SQL DB | Sustainable Use License since 2026 (source-available) [noco-lic] | Postgres/SQLite/MySQL | REST; built-in MCP [noco-mcp] | 2026.09.0, 2026-09-10 | License change is a red flag |
| Baserow | Airtable-like | MIT core + premium dir [baserow-lic] | Postgres [baserow] | REST (OpenAPI); built-in MCP [baserow-mcp] | 2.3.4, 2026-09-15 | Heavier (Django + Postgres) |
| AppFlowy | Notion-like | AGPL-3.0 | Local + AppFlowy Cloud | | 0.14.5, 2026-09-22 | Weak CLI/agent story (unverified) |
| Obsidian Bases | Table views over frontmatter | Proprietary core plugin | .md frontmatter + `.base` file [obs-bases] | via Obsidian CLI | ships with Obsidian | Replaces most Dataview use |
| Dataview | Obsidian query plugin | MIT | .md | | 0.5.70, 2025-04-07; push 2025-11 | Stalled; prefer Bases |
| SilverBullet queries | Lua-integrated queries over pages | MIT | .md | | see above | "Records as pages" pattern [sb] |
| Datasette + sqlite-utils | Publish/explore SQLite; CLI to load JSON/CSV | Apache-2.0 | SQLite | JSON API; `datasette-mcp` adds `/-/mcp` [ds-mcp] | datasette 1.0a41, 2026-09-24; sqlite-utils 4.2.1 | Most agent-friendly structured store |

Tana and Capacities are closed SaaS. Anytype is the closest local-first "object/type" equivalent but isn't OSS. I found no mature OSS Tana clone.

## 3. Personal CRM and contacts

| Tool | License | Storage | Status | API/MCP | Notes |
|---|---|---|---|---|---|
| Monica 4.x | AGPL-3.0 | MySQL/SQLite (Laravel) | Last rel v4.1.2, 2024-05-04 [monica-rel] | REST API | Stable but frozen |
| Monica v5 ("Chandler") | AGPL-3.0 | same | Chandler repo archived; merged into `main`, README says "beta" [monica-readme]; last v5.0.0-beta.5, 2025-04-21 | | Never went GA |
| Monica "v3" (rebuild) | "will remain open source" | ? | Promised before end 2026, migration path planned [monica-v3]; hosted instance deletion end Dec 2026 [monica-pr] | "Everything in UI via API" [monica-v3] | Vapor until shipped |
| Twenty | AGPL-3.0 + some enterprise files [twenty-lic] | Postgres | v2.41.0, 2026-09-17 | GraphQL/REST; community MCPs [twenty-mcp] | Sales CRM, overkill for friends |
| Radicale | GPL-3.0 | vCard/iCal files on disk [radicale] | v3.8.1, 2026-09-24 | CardDAV | Phones sync contacts natively |
| khard (+ vdirsyncer) | GPL-3.0 | Local vCard dir [khard] | v0.21.0 tag; commit 2026-09-07 | CLI | Warns vCard interop is messy on write [khard] |

Take: contacts need two things, phone sync (CardDAV) and rich "how I know them" data. vCard covers the first badly on the second. The practical pattern is a SQLite/Grist `people` table (or frontmatter pages) with a `wiki_page` column, plus an optional one-way export to vCard/Radicale for the phone.

## 4. Bookmarks / read-later

| Tool | License | Storage | Mobile | API/CLI/MCP | Last rel |
|---|---|---|---|---|---|
| Karakeep (ex-Hoarder) | AGPL-3.0 | SQLite via Drizzle (unverified, README names Drizzle only) | iOS/Android apps [karakeep] | REST, CLI, official MCP `@karakeep/mcp`, agent skills [karakeep-mcp] | v0.33.2, 2026-08-11 |
| Linkwarden | AGPL-3.0 | Postgres (unverified) | Native iOS/Android [linkwarden] | REST; Floccus browser sync [linkwarden] | v2.16.3, 2026-09-09 |
| linkding | MIT | SQLite (unverified) | Community apps [linkding] | REST [linkding] | v1.47.0, 2026-09-13 |
| Wallabag | MIT | DB | Apps | REST | 2.6.14, 2025-10-07 (slow) |
| Shaarli | zlib | "database-free" flat file [shaarli] | Web | REST | v0.16.7, 2026-09-19 |
| ArchiveBox | MIT | HTML/PDF/WARC/JSON + SQLite index [archivebox] | No | CLI, Python, SQLite [archivebox] | v0.9.51, 2026-09-23 |

Karakeep and Linkwarden both sync browser bookmarks via Floccus [karakeep][linkwarden], which covers the "bookmarks spread across browsers" problem.

## 5. Search / indexing over existing files

| Tool | License | Status | Notes |
|---|---|---|---|
| ripgrep + fzf | MIT/Unlicense | Active | What agents already use. Zero setup. Good enough for plain-text dirs |
| Recoll | GPL | 1.44.x in 2026 [recoll] | Xapian full-text index incl. PDFs/office. Hosted on framagit, not GitHub |
| Khoj | AGPL-3.0 | Last rel 2.0.0-beta.28, 2026-03; commits to 2026-08 | Self-host AI search/chat over md/org/pdf [khoj]. Slowing |
| Reor | AGPL-3.0 | **Archived** (last rel 2025-04) | Drop |
| Memex (WorldBrain) | ? | Last GH release 2020; push 2025-12 | Drop |
| Datasette + Dogsheep | Apache-2.0 | datasette active; dogsheep-beta 0.11 (2026-04); `evernote-to-sqlite` 2021, `google-takeout-to-sqlite` 2023 | Search across many SQLite DBs [dogsheep-beta]. Importers stale but small |
| Paperless-ngx | GPL-3.0 | v3.2.1, 2026-09-20 | Scanned docs/PDF OCR archive; community MCPs (unverified) |

## 6. Plain-text tools

| Tool | License | Last rel | Fit |
|---|---|---|---|
| org-mode / org-roam | GPL-3.0 | org-roam v2.3.1, 2025-06; push 2026-04 | Only if you live in Emacs. org-roam keeps SQLite index |
| Denote | GPL-3.0 | no GH releases; push 2026-09-25 | Emacs, filename-as-metadata, no DB |
| todo.txt-cli | GPL-3.0 | v2.14.0, 2026-09-01 | Format for per-repo TODOs, easy to grep/aggregate |
| zk | GPL-3.0 | v0.15.6, 2026-07-26 | CLI over md, wikilinks, SQLite index, LSP [zk]. Good agent tool |
| nb | AGPL-3.0 | 7.25.5, 2026-08-12 | CLI notes + bookmarks, git-backed sync [nb] |
| Zim | GPL-2.0 | push 2026-09-01 | Desktop wiki, plain text |

## 7. Graph / SQLite stores (brief)

- **SQLite + Datasette**: default choice. `datasette-mcp` 0.2 (2026-09-01) [ds-mcp].
- **TerminusDB**: Apache-2.0, v12.0.7 2026-08-10. Git-like versioned graph. Heavy for personal use.
- **Kuzu**: MIT, **archived 2025-10-10** (v0.11.3). Drop.
- Graph-in-markdown (wikilinks + frontmatter relations, indexed by zk/Basic Memory/SilverBullet) covers the "knowledge graph" need without a graph DB.

## 8. Importers

| Source | Tool | Output | Status |
|---|---|---|---|
| Evernote .enex | Obsidian Importer [obs-imp] | md + attachments | 3.1.8, 2026-09-24 |
| | evernote2md (Go CLI) [evernote2md] | md, optional frontmatter | v0.23.0, 2026-08-23 |
| | YARLE | md, templates | v6.16.1, 2026-03-05 |
| | Joplin native import [joplin] | Joplin DB | active |
| | Trilium native import [trilium] | Trilium DB | active |
| | dogsheep evernote-to-sqlite | SQLite | 0.3.2, 2021 (stale) |
| Google Keep Takeout | Obsidian Importer [obs-imp] | md | active |
| | jimmy (CLI, `--format google_keep`) [jimmy] | md + frontmatter, many formats incl. Evernote | active |
| | keep-to-markdown variants, google-keep-extractor [keep-search] | md | small scripts, mixed maintenance |

Suggested path: run the Obsidian Importer or `jimmy` once to get markdown, then commit it to git. That output is readable by every tool above.

## 9. MCP / agent integration summary

| Tool | Official MCP | Other agent access |
|---|---|---|
| Obsidian | No | Official CLI (needs app) [obs-cli]; community MCP [mcp-obs]; or just files |
| SilverBullet | No | Community MCPs [sb-mcp1][sb-mcp2]; files |
| Trilium | Yes, built-in, optional [trilium-mcp] | ETAPI |
| Logseq DB | Yes, announced [lsq-split] | CLI in progress |
| Anytype | Yes [anytype-mcp] | CLI [anytype-cli] |
| Joplin | Community [joplin-mcp] | Data API, CLI |
| Karakeep | Yes [karakeep-mcp] | CLI, skills |
| Grist | Built-in (full edition) [grist] | REST |
| NocoDB / Baserow | Built-in [noco-mcp][baserow-mcp] | REST |
| Datasette | Yes, plugin [ds-mcp] | JSON API, sqlite3 |
| Basic Memory | Is an MCP server [basic-mem] | files |
| Twenty | Community [twenty-mcp] | GraphQL/REST |

For Claude Code specifically, plain files + `rg` + `sqlite3` need no MCP at all. MCP matters mostly for server-backed apps (Karakeep, Trilium, Grist).

## Architecture patterns

**A. Markdown vault + git + SQLite sidecar.** One git repo: `notes/` (md, wikilinks, frontmatter), `data/*.db` (people, etc.), `index.md` hub. Edit with Obsidian and/or SilverBullet; query SQLite with Datasette + `datasette-mcp`.
- Pro: every piece is plain text or SQLite, agents need nothing special, zero lock-in, git history.
- Con: two sources of truth for people (row + page), so you need a convention or a script to keep them linked. Mobile capture depends on the editor.

**B. SilverBullet (or Obsidian) as hub, frontmatter-as-records.** Each contact is a page with frontmatter (`email`, `birthday`, `met_via`), and queries/Bases render tables.
- Pro: one store, record and wiki page are the same file, simplest mental model.
- Con: no schema enforcement, weak for many-to-many/relational queries. Fine at hundreds of contacts, awkward at thousands. SilverBullet mobile is a PWA only.

**C. Trilium all-in-one.** Notes, attributes-as-fields, relations, built-in MCP, native Evernote import.
- Pro: one app, real structured attributes, active (release today), official MCP.
- Con: SQLite blob, not greppable files. Agents must use ETAPI/MCP. Harder to mix with repo TODO files.

**D. Federated: specialized apps + hub index.** Karakeep (bookmarks), Memos or Joplin (Keep replacement), Grist (contacts), and a markdown `index.md` wiki linking to them, with each app exposing MCP.
- Pro: best UX per domain, good mobile capture, most apps already have MCP.
- Con: several docker services to run, back up and upgrade. Cross-cutting search needs an extra layer. Most of these apps are server-first, which strains "local-only".

**E. Dogsheep-style warehouse.** Leave data where it is; nightly scripts ingest Keep/Evernote/bookmarks/repo TODOs/contacts into SQLite with `sqlite-utils`, search via Datasette (+ dogsheep-beta), and expose it via `datasette-mcp`.
- Pro: covers the "pointer to where it lives" need, read-optimized for agents, no migration needed.
- Con: read-only view. You still need an editing home for new notes. Importers for Evernote/Takeout are stale and you'd maintain them yourself.

My take: A as the core (with B's per-person pages), E-style ingest scripts for the "pointer only" sources (browser bookmarks, host text files, repo TODO.txt), and exactly one server app, Karakeep, if bookmark capture from phone matters. Defer the CRM decision until Monica v3 actually ships.

## Open questions

1. Mobile capture: must it work offline on the phone, or is a self-hosted PWA reachable over Tailscale/LAN fine? This decides Obsidian vs SilverBullet vs Memos.
2. OSS required? Obsidian (proprietary, files are open) and Anytype (source-available) hinge on this.
3. Hosting: is a small always-on server acceptable, or must it all run inside this sandbox/host only? This rules D in or out.
4. Contacts: do you need phone contact sync (CardDAV), or only a reference store for you and agents?
5. Evernote/Keep: full migration into the new home, or archive plus searchable index (pattern E)?
6. Repo TODO files: leave them in place and index them, or centralize them?
7. Scale: roughly how many notes and contacts? Matters for B vs A.
8. Where the knowledge-dump repo sits relative to editing: is this repo itself the vault?

## Decisions (2026-09-25)

Answers to the open questions above, plus what they imply.

| # | Decision | Implication |
|---|---|---|
| 1 | Phone capture must work offline. Degraded offline is fine. Phone is Android. | Markor (plain-file editor) + Syncthing to the host. Captures land in an inbox folder, triaged later. |
| 2 | OSS only. | Obsidian, Anytype, NocoDB out. Evernote import via `jimmy` or `evernote2md`, not the Obsidian Importer. |
| 3 | Services run on the Ubuntu host. The sandbox (agents) can be offline anytime; only AI features stop. Phone keeps working with the host offline. Remote access over Tailscale. | Host runs SilverBullet, Radicale, Syncthing, maybe Karakeep. Agents reach files through the `claudedev/` mount and services at `host.docker.internal`. |
| 4 | Phone contact sync wanted. | Radicale is the master copy for contacts, synced to Android with DAVx5. |
| 5 | Evernote: full migration. Keep: archive, searchable. | Evernote becomes markdown in the data repo. Keep Takeout stays raw, indexed into SQLite. New quick notes go to the Markor inbox, not Keep. |
| 6 | Repo TODO files stay where they are. | Indexer scans the repos. No moving. |
| 7 | Thousands of contacts, mostly thin. A handful get full pages. | vCard holds the thin data (NOTE for meetup notes). Markdown pages only for people with more to say. |
| 8 | Data and code in separate git repos. Data can sit in a subfolder, no submodules. | `knowledge-dump/data/` has its own `.git` and is listed in the code repo's `.gitignore`. |
| - | Try Karakeep for bookmarks. | One more service on the host. |

### Contact linking (verified)

Radicale stores each contact as a `.vcf` file and keeps custom properties. I tested this on Radicale 3.x: I PUT a vCard with `URL`, `NOTE`, `X-KD-WIKI` and `X-KD-HOW-MET`, and GET returned all of them unchanged, only reordered. DAVx5 keeps properties it doesn't understand when a contact is edited on the phone ([DAVx5 manual][davx5-tech]).

Link scheme:
- The vCard `URL` points to the person's SilverBullet page. Android's contact app shows it as a tappable link.
- An `X-` property holds the page path for agents.
- The page frontmatter holds the vCard `UID`.
- SQLite is a rebuildable index over both, never the source of truth.

Radicale writes `.Radicale.cache/` next to the `.vcf` files. Gitignore it if the collection lives in the data repo.

### Syncthing on stock Android (checked 2026-09-25)

- The official app is dead. The maintainer retired it on 2024-10-20, citing Play publishing friction and no maintenance ([announcement][st-retire]). The repo is archived and its last release was 1.28.1, 2024-12-03.
- Syncthing-Fork is the maintained replacement. Repo `researchxxl/syncthing-android` (the old Catfriend1 URL redirects there), MPL-2.0, last push 2026-09-24, release v2.1.5.0 2026-09-08 ([repo][st-fork]). minSdk 23 (Android 6), targetSdk 37.
- Where to get it:
  - F-Droid: `com.github.catfriend1.syncthingfork` 2.1.5.0 ([F-Droid][st-fdroid]). The README also points to GitHub releases and Obtainium.
  - Play Store: a "Syncthing-Fork" listing exists under the old package id `com.github.catfriend1.syncthingandroid`, developer "nel0x", updated Aug 14, 2026. The README doesn't link it, so I couldn't confirm it's the same maintainers' build.
- Stock Android runs it; the catch is Google's developer verification. It starts enforcing 2026-09-30 in Brazil, Indonesia, Singapore and Thailand, and globally in 2027. Apps from unverified developers then need the "advanced flow", which includes a one-time 24-hour wait ([Android Authority][adv-flow]). F-Droid signs most apps with its own key and objects to the scheme ([9to5Google][adv-flow2]). F-Droid installs should keep working in the US through 2026, but 2027 is uncertain.

Building it yourself works around verification. Google's FAQ says "Apps installed using ADB won't require verification" ([FAQ][dv-faq]). A free "limited distribution" account also covers up to 20 devices with no ID check.

Costs of self-building:
- You own the updates. Syncthing ships security fixes, so something has to rebuild and reinstall.
- An APK with your own signing key can't update over an F-Droid or Play install. Uninstall first; the sync config can be exported and imported.

Phone test log (2026-09-26, Syncthing-Fork 2.1.5 + Markor, test folder `claudedev/kd-sync-test/`):
- Pairing: scan the QR code from Devices → Add Device → QR icon. The phone camera alone won't open the app.
- Accepting a shared folder: tap the notification. Tapping ✓ on the form can fail silently and stay greyed out. Reopening from the notification fixed it.
- A (round trip): passed on wifi.
- B (offline capture, 2 new files + 1 edit): passed once the phone reconnected.
- The default run conditions sync on unmetered wifi only. Turn on "Run on mobile data".
- The sandbox sees Syncthing writes late. The host got the files around 13:56:50, but the sandbox mount listed nothing new until about 14:01. Syncthing writes a temp file and renames it, so the file gets a new inode. That is the stale cache problem `refresh-mount` describes. Agents reading synced files must drop caches first (`sudo sh -c 'echo 2 > /proc/sys/vm/drop_caches'`) or read through a host service instead.
- Dropping caches doesn't fix directory listings. After the conflict test, `ls` in the sandbox still didn't show the new conflict file, and the directory mtime stayed at 13:56:50. `cat` by exact name read it fine, and the host's Syncthing REST API (`/rest/db/browse`) listed it. Agents can't trust `ls` or `rg` over synced folders from inside the sandbox. They should list files through a host API.
- C (conflict): passed, nothing lost. Both sides edited `from-sandbox.md` while the phone was in airplane mode. Syncthing kept the newer phone edit as `from-sandbox.md` and saved the older sandbox edit as `from-sandbox.sync-conflict-20260926-140932-L2PYUWV.md`. The inbox design should expect these files and have triage pick them up.
- After airplane mode, the host held a dead connection for about 5.5 minutes (14:03:43 to 14:09:20, "read timeout"). It rejected the phone's reconnects with "already connected to this device" until then, so sync resumes up to about 5 minutes after going back online.
- Before the timeout, the phone connected over Tailscale (`fd7a:115c:...`) and over a direct connection from its cellular IP to the host's LAN IP (`192.168.7.37:22000`). The direct one means Syncthing's port is reachable from the internet, probably through UPnP on the router. To stay Tailscale-only, turn off NAT traversal, relays and global discovery, and listen on the Tailscale address only.

Fallbacks if sideloading gets painful:
- SilverBullet installed as a web app in Chrome. Installed web apps get persistent storage in Chrome, so eviction is less likely than on iOS (unverified for SilverBullet specifically).
- The Play build of Syncthing-Fork, once its origin is confirmed.

[davx5-tech]: https://manual.davx5.com/technical_information.html
[dv-faq]: https://developer.android.com/developer-verification/guides/faq
[st-retire]: https://forum.syncthing.net/t/discontinuing-syncthing-android/23002
[st-fork]: https://github.com/researchxxl/syncthing-android
[st-fdroid]: https://f-droid.org/packages/com.github.catfriend1.syncthingfork
[adv-flow]: https://www.androidauthority.com/google-android-advanced-flow-sideloading-rollout-begins-3700073/
[adv-flow2]: https://9to5google.com/2026/08/18/google-gradually-rolling-out-androids-advanced-sideloading-ahead-of-developer-verification/

## Sources

Activity/license data from `gh api repos/<owner>/<repo>` and `/releases`, fetched 2026-09-25, for every repo named above (https://github.com/<owner>/<repo>).

[obs-lic]: https://obsidian.md/license
[obs-rel]: https://github.com/obsidianmd/obsidian-releases/releases
[obs-cli]: https://obsidian.md/help/cli
[obs-bases]: https://obsidian.md/help/bases/views
[obs-imp]: https://github.com/obsidianmd/obsidian-importer
[mcp-obs]: https://github.com/MarkusPfundstein/mcp-obsidian
[sb]: https://silverbullet.md/
[gh-sb]: https://github.com/silverbulletmd/silverbullet
[sb-mcp1]: https://github.com/Ahmad-A0/silverbullet-mcp
[sb-mcp2]: https://ai.silverbullet.md/MCP%20Server/
[lsq-split]: https://logseq.io/p/e3YDyX5AYr
[lsq-rel]: https://github.com/logseq/logseq/releases/tag/2.0.1
[lsq-og]: https://github.com/logseq/og
[trilium]: https://github.com/TriliumNext/Trilium
[trilium-etapi]: https://docs.triliumnotes.org/user-guide/advanced-usage/etapi
[trilium-mcp]: https://github.com/TriliumNext/Trilium/blob/main/docs/User%20Guide/User%20Guide/AI/MCP.md
[trilium-105]: https://github.com/TriliumNext/Trilium/releases/tag/v0.105.0
[joplin]: https://joplinapp.org/help/
[joplin-lic]: https://github.com/laurent22/joplin/blob/dev/LICENSE
[joplin-mcp]: https://github.com/alondmnt/joplin-mcp
[foam-lic]: https://github.com/foambubble/foam/blob/main/LICENSE
[dendron]: https://github.com/dendronhq/dendron/discussions/3890
[affine-lic]: https://github.com/toeverything/AFFiNE/blob/canary/LICENSE
[anytype]: https://github.com/anyproto/anytype-ts
[anytype-lic]: https://github.com/anyproto/anytype-ts/blob/develop/LICENSE.md
[anytype-mcp]: https://github.com/anyproto/anytype-mcp
[anytype-cli]: https://github.com/anyproto/anytype-cli
[memos]: https://github.com/usememos/memos
[basic-mem]: https://github.com/basicmachines-co/basic-memory
[outline-lic]: https://github.com/outline/outline/blob/main/LICENSE
[grist]: https://github.com/gristlabs/grist-core
[noco-lic]: https://github.com/nocodb/nocodb/blob/develop/LICENSE.md
[noco-mcp]: https://nocodb.com/docs/apis-and-mcp/mcp
[baserow]: https://github.com/baserow/baserow
[baserow-lic]: https://github.com/baserow/baserow/blob/develop/LICENSE
[baserow-mcp]: https://baserow.io/user-docs/mcp-server
[ds-mcp]: https://github.com/datasette/datasette-mcp
[monica-rel]: https://github.com/monicahq/monica/releases
[monica-readme]: https://github.com/monicahq/monica
[monica-v3]: https://www.monicahq.com/en/v3/
[monica-pr]: https://github.com/monicahq/monica/pull/7978
[twenty-lic]: https://github.com/twentyhq/twenty/blob/main/LICENSE
[twenty-mcp]: https://github.com/mhenry3164/twenty-crm-mcp-server
[radicale]: https://radicale.org/v3.html
[khard]: https://github.com/lucc/khard
[karakeep]: https://github.com/karakeep-app/karakeep
[karakeep-mcp]: https://docs.karakeep.app/integrations/mcp/
[linkwarden]: https://github.com/linkwarden/linkwarden
[linkding]: https://github.com/sissbruecker/linkding
[shaarli]: https://github.com/shaarli/Shaarli
[archivebox]: https://github.com/ArchiveBox/ArchiveBox
[recoll]: https://www.recoll.org/pages/download.html
[khoj]: https://github.com/khoj-ai/khoj
[dogsheep-beta]: https://github.com/dogsheep/dogsheep-beta
[zk]: https://github.com/zk-org/zk
[nb]: https://github.com/xwmx/nb
[evernote2md]: https://github.com/wormi4ok/evernote2md
[jimmy]: https://github.com/marph91/jimmy
[keep-search]: https://github.com/tpwo/google-keep-extractor
