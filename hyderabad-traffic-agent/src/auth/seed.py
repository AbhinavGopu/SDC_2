from src.auth.db import engine, SessionLocal
from src.auth.models import Base, Ward, Citizen, Planner
from src.auth.security import hash_password


def seed_data():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        existing_wards = {ward.name for ward in session.query(Ward).all()}
        demo_wards = [
            {"id": 1, "name": "Ameerpet", "ghmc_code": "HYD-W1", "description": "Core IT and residential ward.", "locality": "Ameerpet"},
            {"id": 2, "name": "Gachibowli", "ghmc_code": "HYD-W2", "description": "Large tech corridor with frequent peak-hour congestion.", "locality": "Gachibowli"},
            {"id": 3, "name": "Kukatpally", "ghmc_code": "HYD-W3", "description": "Busy suburban ward with mixed traffic.", "locality": "Kukatpally"},
            {"id": 4, "name": "Secunderabad", "ghmc_code": "HYD-W4", "description": "Key transit hub and civic center.", "locality": "Secunderabad"},
            {"id": 5, "name": "Madhapur", "ghmc_code": "HYD-W5", "description": "Major IT/ITES hub, high office-goer traffic.", "locality": "Madhapur"},
            {"id": 6, "name": "Banjara Hills", "ghmc_code": "HYD-W6", "description": "Upscale commercial and residential area with steep terrain.", "locality": "Banjara Hills"},
            {"id": 7, "name": "Jubilee Hills", "ghmc_code": "HYD-W7", "description": "Premium residential and commercial zone with high vehicle density.", "locality": "Jubilee Hills"},
            {"id": 8, "name": "Begumpet", "ghmc_code": "HYD-W8", "description": "Commercial and residential hub, old airport area.", "locality": "Begumpet"},
            {"id": 9, "name": "Uppal", "ghmc_code": "HYD-W9", "description": "Key eastern gateway hub with metro terminal.", "locality": "Uppal"},
            {"id": 10, "name": "Dilsukhnagar", "ghmc_code": "HYD-W10", "description": "Densely populated educational and commercial hub.", "locality": "Dilsukhnagar"},
        ]
        for ward_data in demo_wards:
            if ward_data["name"] not in existing_wards:
                session.add(Ward(**ward_data))

        if not session.query(Citizen).filter(Citizen.email == 'citizen1@hyderabad.local').one_or_none():
            session.add_all([
                Citizen(email=f'citizen{i}@hyderabad.local', password_hash=hash_password('citizen123'), full_name=f'Ward {i} Citizen', ward_id=i)
                for i in range(1, 11)
            ])

        if not session.query(Planner).filter(Planner.email == 'planner1@hyderabad.local').one_or_none():
            session.add_all([
                Planner(email=f'planner{i}@hyderabad.local', password_hash=hash_password('planner123'), full_name=f'Ward {i} Planner', ward_id=i)
                for i in range(1, 11)
            ])

        session.commit()
    finally:
        session.close()


if __name__ == '__main__':
    seed_data()
