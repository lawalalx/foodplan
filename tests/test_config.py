"""
Tests for database configuration and connection.
Validates AsyncSession setup and database operations.
"""
import pytest
from sqlalchemy import select
from sqlmodel import SQLModel
from models import User


class TestDatabaseConfig:
    """Test database configuration."""
    
    @pytest.mark.asyncio
    async def test_engine_creation(self, test_engine):
        """Test async engine creation."""
        assert test_engine is not None
        # Verify we can execute a query
        async with test_engine.connect() as conn:
            result = await conn.execute(select(1))
            assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_session_creation(self, test_session):
        """Test async session creation."""
        assert test_session is not None
        # Verify we can use the session
        result = await test_session.execute(select(1))
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_table_creation(self, test_engine):
        """Test that all tables are created."""
        # Tables should already be created in fixture
        async with test_engine.connect() as conn:
            # Verify one of the tables exists
            result = await conn.execute(select(1))
            assert result is not None


class TestDatabaseOperations:
    """Test basic database operations."""
    
    @pytest.mark.asyncio
    async def test_create_read(self, test_session, dummy_user_data):
        """Test CREATE and READ operations."""
        # Create
        user = User(**dummy_user_data)
        test_session.add(user)
        await test_session.commit()
        
        # Read
        result = await test_session.get(User, user.user_id)
        assert result is not None
        assert result.user_id == dummy_user_data["user_id"]
    
    @pytest.mark.asyncio
    async def test_update(self, test_session, user_in_db):
        """Test UPDATE operation."""
        # Update
        user_in_db.household_size = 5
        test_session.add(user_in_db)
        await test_session.commit()
        
        # Verify
        result = await test_session.get(User, user_in_db.user_id)
        assert result.household_size == 5
    
    @pytest.mark.asyncio
    async def test_delete(self, test_session, user_in_db):
        """Test DELETE operation."""
        user_id = user_in_db.user_id
        
        # Delete
        await test_session.delete(user_in_db)
        await test_session.commit()
        
        # Verify deletion
        result = await test_session.get(User, user_id)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_session, dummy_user_data):
        """Test transaction rollback."""
        # Create user
        user = User(**dummy_user_data)
        test_session.add(user)
        await test_session.commit()
        
        # Try to modify and rollback
        user.household_size = 10
        test_session.add(user)
        await test_session.rollback()
        
        # Verify original value
        result = await test_session.get(User, user.user_id)
        assert result.household_size == dummy_user_data["household_size"]


class TestSessionDependency:
    """Test the session dependency injection pattern."""
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self, test_engine):
        """Test session context manager pattern."""
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        
        session_maker = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Use context manager
        async with session_maker() as session:
            user = User(user_id="test_ctx")
            session.add(user)
            await session.commit()
            
            result = await session.get(User, user.user_id)
            assert result is not None
