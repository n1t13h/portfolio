# Backend review refactor — plan

Responds to the four review comments on PR #2. Fetched with `~/.claude/bin/pr-comments 2 -R n1t13h/portfolio`.

| # | Comment | Change |
|---|---|---|
| 1 | `services/collections.py`: no service–repository pattern; services make DB calls directly, so they are hard to unit test | Add a **repository layer** (abstract interface + SQLAlchemy implementation per aggregate). Services depend only on the interfaces. |
| 2 | `api/admin/collection_schemas.py`: keep schemas in a `schemas/` folder | Move **every** Pydantic model (requests and responses, admin and public, plus those inlined in routers) into one `app/schemas/` package, one module per entity. |
| 3 | `core/db.py`: follow the SQLAlchemy **Unit of Work** article | Add `AbstractUnitOfWork` / `SqlAlchemyUnitOfWork` (`app/uow.py`): a context manager that opens a session, exposes the repositories, commits explicitly, and **rolls back on exit unless committed**. Services take a UoW and never touch a `Session`. `core/db.py` keeps only engine/session-factory/`Base`. |
| 4 | `tests/`: flat; no entity or unit/integration separation | Reorganise as `tests/unit/<entity>/` and `tests/integration/<entity>/` (entities: photos, collections, auth, public, contact, sync, seed, backup, images, storage, unsplash, core). Shared fakes move to `tests/fakes/`. |

The article itself could not be fetched (Medium returns 403 to automated requests), so the UoW follows its canonical form (Cosmic Python, ch. 6): abstract base with `__enter__`/`__exit__`, `commit()`, `rollback()`, repositories attached to the UoW, and a SQLAlchemy implementation built on a session factory.

## Target architecture

```
app/
  models/          ORM entities (unchanged)
  schemas/         Pydantic request/response models, one module per entity   <- comment 2
  repositories/    abstract repositories + SQLAlchemy implementations        <- comment 1
  uow.py           AbstractUnitOfWork + SqlAlchemyUnitOfWork                 <- comment 3
  services/        use cases: take a UoW factory (+ storage etc.), return schemas, no Session
  api/             thin routers: parse request -> call service -> return schema
  integrations/    R2, Unsplash, Telegram (unchanged)
  core/            config, db (engine/factory/Base only), clock, security, limits, errors
```

Rules:
- A service method is one transaction: `with self._uow() as uow: ...; uow.commit()`. Services receive a **factory** (`Callable[[], AbstractUnitOfWork]`) because some (sync, seed, contact) run several transactions in sequence; request-scoped services just use one.
- Entities never leave a service. Services return Pydantic schemas built inside the transaction, so nothing depends on a live session (no lazy loading after close).
- Repositories hold queries only; business rules stay in services.
- Unit tests use `FakeUnitOfWork` with in-memory repositories (subclasses of the abstract ones, so a missing method fails loudly). Contract tests run the same behaviour checks against the fake **and** the SQL repository so the fake cannot drift.

## Tasks (each leaves the whole suite green)

1. **Test layout** — pure move: `tests/unit/...` and `tests/integration/...` by entity; split `fakes.py` into a `fakes/` package; fix imports. No behaviour change.
2. **Schemas package** — move all Pydantic models into `app/schemas/`; routers import from there. No behaviour change.
3. **UoW + repositories (infrastructure)** — abstract and SQL repositories for photos, collections (+chapters), catalog (public read side), admin/login failures, audit, sync state, contact; `AbstractUnitOfWork`, `SqlAlchemyUnitOfWork`, `FakeUnitOfWork`; repository contract tests (fake and SQLite).
4. **Photos service** on the UoW (+ unit tests with the fake UoW).
5. **Collections service** on the UoW (+ unit tests).
6. **Public catalog service** on the UoW (+ unit tests, including the draft-visibility rules).
7. **Auth + audit services** on the UoW (+ unit tests: lockout, TOTP replay, recovery codes, session revocation).
8. **Contact, sync, seed services** on the UoW (+ unit tests). Seed now creates photos with their final status in one transaction (closes a deferred item from the first review).
9. **Wiring and cleanup** — API dependencies build the UoW factory; delete `get_session`, old service helpers and dead modules; CLI uses the UoW.
10. **Docs and verification** — README architecture section; full gates (pytest, ruff, mypy `--strict`); rebuild the docker stack and run `scripts/smoke_local.py`.

## Out of scope
Behaviour changes. The HTTP API, database schema and migrations stay exactly as they are; the existing 224 tests (moved, not rewritten) are the proof.
