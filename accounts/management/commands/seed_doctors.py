from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from accounts.models import Doctor

User = get_user_model()

DOCTORS = [
    {
        'name': 'David Maxwell',
        'medical_id': '1001',
        'medical_number': '1001',
        'specialty': 'Internal Medicine',
        'description': 'Treats seasonal and infectious diseases',
        'accepted_insurance': 'bimeh_salamat,bimeh_tamin_ejtemaei,bimeh_iran',
    },
    {
        'name': 'Olivia Stone',
        'medical_id': '1002',
        'medical_number': '1002',
        'specialty': 'Neurology',
        'description': 'Manages headaches and migraines',
        'accepted_insurance': 'bimeh_salamat,bimeh_niroo_mosallah,bimeh_asia',
    },
    {
        'name': 'Ethan Blake',
        'medical_id': '1003',
        'medical_number': '1003',
        'specialty': 'Orthopedics',
        'description': 'Treats back pain and joint disorders',
        'accepted_insurance': 'bimeh_salamat,bimeh_roostaei_ashayer,bimeh_dana',
    },
    {
        'name': 'Mia Harrison',
        'medical_id': '1004',
        'medical_number': '1004',
        'specialty': 'Cardiology',
        'description': 'Controls high blood pressure and heart conditions',
        'accepted_insurance': 'bimeh_salamat,bimeh_khadamat_darmani,bimeh_parsian',
    },
    {
        'name': 'Lucas Bennett',
        'medical_id': '1005',
        'medical_number': '1005',
        'specialty': 'Endocrinology',
        'description': 'Manages diabetes and blood sugar regulation',
        'accepted_insurance': 'bimeh_salamat,bimeh_komite_emdad,bimeh_novin',
    },
    {
        'name': 'Amelia Clarke',
        'medical_id': '1006',
        'medical_number': '1006',
        'specialty': 'Psychiatry',
        'description': 'Treats anxiety and depression',
        'accepted_insurance': 'bimeh_salamat,bimeh_saman,bimeh_razi',
    },
    {
        'name': 'Nathan Reid',
        'medical_id': '1007',
        'medical_number': '1007',
        'specialty': 'Dermatology',
        'description': 'Diagnoses skin rashes and allergies',
        'accepted_insurance': 'bimeh_tamin_ejtemaei,bimeh_niroo_mosallah,bimeh_iran',
    },
    {
        'name': 'Sophia Grant',
        'medical_id': '1008',
        'medical_number': '1008',
        'specialty': 'Gastroenterology',
        'description': 'Treats stomach and digestive issues',
        'accepted_insurance': 'bimeh_roostaei_ashayer,bimeh_khadamat_darmani,bimeh_asia',
    },
    {
        'name': 'Daniel Hayes',
        'medical_id': '1009',
        'medical_number': '1009',
        'specialty': 'Pulmonology',
        'description': 'Controls asthma and respiratory problems',
        'accepted_insurance': 'bimeh_komite_emdad,bimeh_dana,bimeh_parsian',
    },
    {
        'name': 'Emma Foster',
        'medical_id': '1010',
        'medical_number': '1010',
        'specialty': 'Family Medicine',
        'description': 'Provides general check-ups and preventive care',
        'accepted_insurance': 'bimeh_salamat,bimeh_tamin_ejtemaei,bimeh_niroo_mosallah,bimeh_iran,bimeh_asia',
    },
]


class Command(BaseCommand):
    help = 'Seed the 10 clinic doctors if they do not already exist.'

    def handle(self, *args, **options):
        created = 0
        for doc in DOCTORS:
            username = doc['name'].lower().replace(' ', '')
            if Doctor.objects.filter(medical_id=doc['medical_id']).exists():
                continue

            user = User.objects.create_user(
                username=username,
                password=doc['medical_id'],
                role='doctor',
            )
            doctor = Doctor(
                user=user,
                medical_number=doc['medical_number'],
                medical_id=doc['medical_id'],
                specialty=doc['specialty'],
                description=doc['description'],
                accepted_insurance=doc['accepted_insurance'],
            )
            doctor.name = doc['name']
            doctor.save()
            created += 1

        if created:
            self.stdout.write(self.style.SUCCESS(f'{created} doctor(s) seeded.'))
        else:
            self.stdout.write('All doctors already exist.')
