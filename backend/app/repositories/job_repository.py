from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, desc
from app.models.database.job import Job, JobType, JobStatus

class AsyncJobRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ==========================================
    # 1. CREATE (Triggered by User)
    # ==========================================

    async def create_job(self, user_id: int, job_type: JobType, source_path: str, original_name: str ):
        """Creates a new job in the PENDING state."""
        new_job = Job(
            user_id=user_id,
            type=job_type,
            source_path=source_path,
            original_name=original_name,
            status=JobStatus.PENDING,
            is_seen=False
        )
        self.db.add(new_job)
        await self.db.commit()
        await self.db.refresh(new_job)
        return new_job

    # ==========================================
    # 2. READ / FETCH METHODS
    # ==========================================

    async def get_by_id(self, job_id: int):
        """Fetches a single job by its ID."""
        stmt = select(Job).where(Job.id == job_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_user_jobs(self, user_id: int, skip: int = 0, limit: int = 50):
        """Fetches all jobs for a specific user, ordered by newest first."""
        stmt = (
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(desc(Job.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_pending_jobs_for_worker(self, job_type: JobType = None, limit: int = 10):
        """Fetches PENDING jobs for a background worker to process."""
        stmt = select(Job).where(Job.status == JobStatus.PENDING)
        if job_type:
            stmt = stmt.where(Job.type == job_type)
            
        stmt = stmt.order_by(Job.created_at).limit(limit) # Oldest first
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_unseen_notifications(self, user_id: int):
        """Fetches completed or failed jobs that the user hasn't looked at yet."""
        stmt = select(Job).where(
            Job.user_id == user_id,
            Job.is_seen == False,
            Job.status != JobStatus.PENDING
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ==========================================
    # 3. UPDATE / WORKER METHODS
    # ==========================================

    async def complete_job(self, job_id: int, target_path: str):
        """Called by your worker when a job successfully finishes."""
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.COMPLETED, target_path=target_path)
            .execution_options(synchronize_session="fetch")
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return await self.get_by_id(job_id)
    
    async def update_job_status(self, job_id: int, status: JobStatus):
        """Updates the status of a job."""
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(status=status)
            .execution_options(synchronize_session="fetch")
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return await self.get_by_id(job_id)


    async def fail_job(self, job_id: int):
        """Called by your worker if something crashes during processing."""
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.FAILED)
            .execution_options(synchronize_session="fetch")
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return await self.get_by_id(job_id)

    async def mark_as_seen(self, job_id: int):
        """Updates a job when a user acknowledges the notification."""
        stmt = update(Job).where(Job.id == job_id).values(is_seen=True)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    # ==========================================
    # 4. DELETE
    # ==========================================

    async def delete_job(self, job_id: int):
        """Deletes a job record from the database."""
        stmt = delete(Job).where(Job.id == job_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
    



    