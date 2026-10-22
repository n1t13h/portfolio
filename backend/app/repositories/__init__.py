"""Repositories: the only code that queries the database.

Each module holds an abstract interface (what services may ask for) and its SQLAlchemy
implementation. Services depend on the interfaces, via the unit of work in `app.uow`.
"""
