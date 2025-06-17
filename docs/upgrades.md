# Upgrade Notes

## Pydantic v2 migration
- Validators updated to use `@field_validator`.

## Datetime handling
- All uses of `datetime.utcnow()` replaced with `datetime.now(timezone.utc)`.
- Database models now store timezone-aware timestamps with `timezone=True`.

## FastAPI lifespan
- Startup and shutdown logic migrated to FastAPI's `lifespan` context.
- Background workers start and stop within the lifespan handler.

## Testing adjustments
- Tests patched to use new lifespan behavior and timezone-aware datetimes.
