# Async Background Jobs
- **Scheduler Tool**: Utilize `APScheduler (AsyncIOScheduler)` for background non-blocking execution inside the Uvicorn loop.
- **Job States**: Database states (`JobStatus`) mark progress across `WAITING`, `PROCESSING`, `COMPLETE`, or `FAILED`.
- **Error Propagation**: Log errors globally `logging.getLogger(__name__)` and handle state updates locally so background exceptions don't leak.
