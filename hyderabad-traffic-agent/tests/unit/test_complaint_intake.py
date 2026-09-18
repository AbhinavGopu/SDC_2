import unittest

from src.complaints.intake_api import ComplaintIntakeService, ComplaintSubmission


class ComplaintIntakeServiceTest(unittest.TestCase):
    def test_submit_creates_record_with_received_status(self):
        service = ComplaintIntakeService()

        submission = ComplaintSubmission(
            citizen_name="Asha Rao",
            contact_email="asha@example.com",
            locality="Ameerpet",
            category="traffic",
            description="Severe bottleneck near the metro exit during evening rush.",
            severity="high",
        )

        record = service.submit(submission)

        self.assertEqual(record.status, "received")
        self.assertEqual(record.category, "traffic")
        self.assertEqual(record.locality, "Ameerpet")
        self.assertEqual(service.list_recent(1)[0].id, record.id)


if __name__ == "__main__":
    unittest.main()
