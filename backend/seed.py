import os
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.project import Project
from app.models.activity import Activity

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eventpath")

def seed_db():
    print(f"Connecting to database: {DATABASE_URL}")
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if sample project already exists
        existing = db.query(Project).filter(Project.name == "Dream Wedding Planning").first()
        if existing:
            print("Sample project 'Dream Wedding Planning' already exists. Skipping seeding.")
            return

        print("Seeding sample event planning project...")
        # 1. Create the project
        project = Project(
            name="Dream Wedding Planning",
            description="Complete scheduling pipeline for a premium wedding event including venue, catering, decor, and RSVPs.",
            target_completion_date=date(2027, 6, 15),
            mode="PERT"  # Seed in PERT mode to demo both CPM and PERT math!
        )
        db.add(project)
        db.flush()  # Generate project.id

        # 2. Create the activities with durations and PERT estimates
        # Format: (name, duration, opt, likely, pess)
        activities_data = [
            ("Venue Booking & Selection", 10.0, 8.0, 10.0, 12.0),
            ("Catering & Menu Selection", 5.0, 4.0, 5.0, 8.0),
            ("Invitation Design & Layout", 4.0, 3.0, 4.0, 5.0),
            ("Send Invitations to Guests", 3.0, 2.0, 3.0, 4.0),
            ("Decor & Floral Concept Design", 6.0, 5.0, 6.0, 8.0),
            ("Bridal Attire & Fittings", 15.0, 10.0, 15.0, 20.0),
            ("RSVP Collection & Follow-ups", 21.0, 14.0, 21.0, 28.0),
            ("Table Layout & Seating Chart", 2.0, 1.0, 2.0, 4.0),
            ("Rehearsal Dinner & Setup", 1.0, 1.0, 1.0, 1.0),
            ("Wedding Day Coordination", 1.0, 1.0, 1.0, 1.0)
        ]

        activities_dict = {}
        for name, duration, opt, likely, pess in activities_data:
            act = Activity(
                project_id=project.id,
                name=name,
                duration=duration,
                optimistic_time=opt,
                most_likely_time=likely,
                pessimistic_time=pess
            )
            db.add(act)
            activities_dict[name] = act
            
        db.flush()  # Generate IDs for activities

        # 3. Setup dependencies
        # Venue booking is predecessor to Catering, Invitations (venue name needed), and Decor
        activities_dict["Catering & Menu Selection"].predecessors.append(activities_dict["Venue Booking & Selection"])
        activities_dict["Send Invitations to Guests"].predecessors.append(activities_dict["Venue Booking & Selection"])
        activities_dict["Decor & Floral Concept Design"].predecessors.append(activities_dict["Venue Booking & Selection"])
        
        # Send Invitations requires Invitation Design to be completed
        activities_dict["Send Invitations to Guests"].predecessors.append(activities_dict["Invitation Design & Layout"])
        
        # RSVP Collection follows Invitation Sending
        activities_dict["RSVP Collection & Follow-ups"].predecessors.append(activities_dict["Send Invitations to Guests"])
        
        # Seating Chart depends on both RSVPs and Catering being finalized
        activities_dict["Table Layout & Seating Chart"].predecessors.append(activities_dict["RSVP Collection & Follow-ups"])
        activities_dict["Table Layout & Seating Chart"].predecessors.append(activities_dict["Catering & Menu Selection"])
        
        # Rehearsal Dinner follows Bridal Attire, Seating Chart, and Decor Concept
        activities_dict["Rehearsal Dinner & Setup"].predecessors.append(activities_dict["Bridal Attire & Fittings"])
        activities_dict["Rehearsal Dinner & Setup"].predecessors.append(activities_dict["Table Layout & Seating Chart"])
        activities_dict["Rehearsal Dinner & Setup"].predecessors.append(activities_dict["Decor & Floral Concept Design"])
        
        # Wedding Day Coordination follows the Rehearsal Dinner
        activities_dict["Wedding Day Coordination"].predecessors.append(activities_dict["Rehearsal Dinner & Setup"])

        db.commit()
        print("Successfully seeded database with 'Dream Wedding Planning' project!")
        print(f"Project ID: {project.id}")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
