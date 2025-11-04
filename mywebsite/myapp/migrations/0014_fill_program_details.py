from __future__ import annotations

from django.db import migrations


ITINERARY = """Registration at welcome camp.
Gear up and go through pre-ride safety briefing and program orientation given by the instructor.
Practice and training on a nice and easy track next to the camp supervised by staff and guide.
Enjoy rides on dirt and muddy areas. Go through moderate bumpy trails, work your way through a dense mangrove forest to find the hidden beach.
Also seeing the insect eating plant, rubber plantations and palm garden.
Back to camp for refreshments, fresh fruits and cold beverages. Then transferred back to hotel or location."""


SCHEDULE = """09.00 am – 11.00 am / 12.00 am – 02.00 pm / 03.00 pm – 05.00 pm
There is free schedule transfer available from Kata, Karon, Patong, Kalim, Kamala, Surin and Bangtao beaches please check availability via Phone/WhatsApp +66-8-9874-0055 or email : booking@atvphuket.com
Cost of transfer is applied for those who stay at Nai Harn, Rawai,Chalong, Cape Panwa, Siray, Phuket Town, Phuket Town Suburb, Laem Hin, Layan, Nai Thon, Nai Yang, Mai Khao and Ao Po areas. THB 1400 for 1-4 paxs and THB 1,800 for 5-10 paxs"""


INCLUDES = """Protective gears (helmet, gloves, shoes), raincoat, changing room, lockers, drinking water, fruits in season and accidental insurance for participants."""


EXCLUDES = """Round-Trip transfer, 3% bank surcharge & ATV damaged
What to bring; spare cloths, towels, sun lotion, sun glasses, camera and cash."""


PRICING_NOTES = """Rider for this program must be older than 8 years old.
Passenger for this program must be older than 4 years old.
Children younger than 4 years old will be free of charge.
Cost of transfer at THB 500 per pax will be charged for escort who is none rider/none passenger."""


PLEASE_NOTE = """The riders must be in good physical and mental condition to ride safely. Therefore, no influence of alcohol and drugs, pregnancy as well as physical problems are not allowed.
Children under 16, riding ATVs must be supervised by parents/guardian and tour guide/instructor or tour operator.
In case of rider with passenger, acceptance will be under tour operator’s consideration and guests shall accept to sign a waiver form and use protective gears such as helmet, glove etc.
During the tour, strictly follow the tour guide/instructor. The tour operator has the authority to stop any risky riding or unpleasant mannerism with no refund.
Cost of transfer at THB 500 per pax will be charged for escorter who is none rider/none passenger.
Additional cost of THB 2,500 is charged on top of tour price for those who request private round-trip transfer.
Additional cost of THB 4,000 is charged on top of tour price for those who request a private ATV tour.
All ATV tour programs are designed for rainy-sunny days. If you mind for wetness or rain, please reconsider before making reservation.
Due to the limitation of the number of participants in each tour slots, we agree to accept your reservation when paid in full amount with 2 days in advance basis.
Cancellation is required 48 hours in advance basis.
Postponement (only one time allowed) is required 3 hours prior to pick-up time.
Accidental insurance covers only riders and passengers and automatically uncovered for all risky riding.
There is no insurance for ATVs, participants are required to pay for all the damages of the use of ATVs due to the rider's carelessness and recklessness or violation of the rules and regulations.
We reserve the right to stop any risky rides and irrespective manners to the locals & ATV instructors without any refund."""


def forward(apps, schema_editor):
    Program = apps.get_model("myapp", "Program")
    Program.objects.update(
        itinerary=ITINERARY,
        schedule_details=SCHEDULE,
        tour_includes=INCLUDES,
        tour_excludes=EXCLUDES,
        tour_notes=PLEASE_NOTE,
        pricing_notes=PRICING_NOTES,
    )


def backward(apps, schema_editor):
    Program = apps.get_model("myapp", "Program")
    Program.objects.update(
        itinerary="",
        schedule_details="",
        tour_includes="",
        tour_excludes="",
        tour_notes="",
        pricing_notes="",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0013_program_itinerary_program_pricing_notes_and_more"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
