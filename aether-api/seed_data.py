#!/usr/bin/env python3
"""Seed test data for development"""
import uuid
from datetime import datetime
from app.core.database import SessionLocal
from app.models import Organization, Project
from app.models.organization import PlanType
from app.models.project import EnvironmentType


def seed_test_data():
    """Create test organization and project for development."""
    db = SessionLocal()

    try:
        # Create test organization
        org_id = uuid.uuid4()
        test_org = Organization(
            id=org_id,
            name="Test Organization",
            plan=PlanType.PRO,
            api_key="ae_test_key_development_12345",
            created_at=datetime.utcnow()
        )
        db.add(test_org)
        db.commit()
        db.refresh(test_org)

        print("=" * 60)
        print("✅ Created Test Organization")
        print("=" * 60)
        print(f"Organization ID: {test_org.id}")
        print(f"Name: {test_org.name}")
        print(f"Plan: {test_org.plan.value}")
        print(f"API Key: {test_org.api_key}")
        print()

        # Create test project
        project_id = uuid.uuid4()
        test_project = Project(
            id=project_id,
            org_id=test_org.id,
            name="Test RAG System",
            description="Development testing project",
            environment=EnvironmentType.DEVELOPMENT,
            created_at=datetime.utcnow()
        )
        db.add(test_project)
        db.commit()
        db.refresh(test_project)

        print("=" * 60)
        print("✅ Created Test Project")
        print("=" * 60)
        print(f"Project ID: {test_project.id}")
        print(f"Name: {test_project.name}")
        print(f"Description: {test_project.description}")
        print(f"Environment: {test_project.environment.value}")
        print(f"Organization ID: {test_project.org_id}")
        print()

        print("=" * 60)
        print("🎯 Quick Reference")
        print("=" * 60)
        print(f"Use this Project ID for testing:")
        print(f"  {test_project.id}")
        print()
        print(f"Use this API Key for authentication:")
        print(f"  {test_org.api_key}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🚀 Seeding test data...\n")
    seed_test_data()
    print("\n✅ Seed data complete!\n")
