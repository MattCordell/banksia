"""Identity generator: names, addresses, and birth dates for synthetic patients."""

import random
from datetime import date, timedelta
from typing import Optional

from common.types import PatientContext

GIVEN_NAMES = [
    "Ambitious", "Outgoing", "Compassionate", "Independent", "Adventurous",
    "Humble", "Charismatic", "Loyal", "Curious", "Analytical", "Assertive",
    "Sociable", "Patient", "Creative", "Happy", "Sad", "Angry", "Excited",
    "Calm", "Anxious", "Confident", "Insecure", "Empathetic", "Sympathetic",
    "Enthusiastic", "Nervous", "Content", "Frustrated", "Energetic", "Vibrant",
    "Healthy", "Fit", "Robust", "Resilient", "Nourished", "Well-balanced",
    "Rested", "Hydrated", "Strong", "Agile", "Vital", "Thriving",
]

FAMILY_NAMES = [
    "Kangaroo", "Koala", "Platypus", "Wombat", "Wallaby", "Tasmanian Devil",
    "Echidna", "Possum", "Quokka", "Sugar Glider", "Kookaburra", "Emu",
    "Cassowary", "Cockatoo", "Dingo", "Frilled-Neck Lizard", "Tasmanian Tiger",
    "Numbat", "Bilby", "Quoll", "Bandicoot", "Pademelon", "Redback Spider",
    "Blue-ringed Octopus", "Funnel-Web", "Box Jellyfish", "Cane Toad",
    "Green Tree Frog", "Crocodile", "Galah", "Blue-tongued Lizard", "Goanna",
    "Lorikeet", "Magpie", "Brushtail Possum", "Potoroo", "Brush Turkey",
    "Flying Fox", "Gouldian Finch", "Taipan", "Bettong", "Humpback Whale",
]

STREET_PLANTS = [
    "Eucalyptus", "Acacia", "Banksia", "Callistemon", "Melaleuca", "Corymbia",
    "Leptospermum", "Grevillea", "Xanthorrhoea", "Acmena", "Cycad",
    "Brachychiton", "Allocasuarina", "Hakea", "Boronia", "Correa", "Waratah",
    "Wattle", "Quandong",
]

STREET_SUFFIXES = [
    "St", "Ave", "Rd", "Ln", "Blvd", "Cres", "Ct", "Cl", "Pl", "Dr",
    "Way", "Sq", "Tce", "Pde", "Hwy", "Esp", "Cove", "Rise",
]

CITIES = [
    "Springfield", "Victoria", "Richmond", "Kensington", "Newcastle",
    "Mount Pleasant", "Windsor", "Fairfield", "Franklin", "Devonport",
    "Preston", "Glenelg", "Brighton", "Hawthorn", "Brunswick", "Geelong",
    "Richmond", "Kensington", "Newcastle", "Windsor", "Fairfield",
]

AUSTRALIAN_STATES = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]


def generate_street_number() -> int:
    """Generate a street number between 1 and 999, skewed toward lower values."""
    # Exponential distribution skewed toward small numbers, clamped to 1-999
    number = int(random.expovariate(1 / 60)) + 1
    return min(number, 999)


def generate_address(state: Optional[str] = None) -> dict:
    """Generate a random Australian-style address.

    Args:
        state: Australian state abbreviation. If None, a random state is chosen.

    Returns:
        dict with keys: street_address, city, state
    """
    street_number = generate_street_number()
    street_name = random.choice(STREET_PLANTS)
    street_suffix = random.choice(STREET_SUFFIXES)

    return {
        "street_address": f"{street_number} {street_name} {street_suffix}",
        "city": random.choice(CITIES),
        "state": state or random.choice(AUSTRALIAN_STATES),
    }


def generate_name() -> dict:
    """Generate a random patient name.

    Returns:
        dict with keys: given_name, family_name
    """
    return {
        "given_name": random.choice(GIVEN_NAMES),
        "family_name": random.choice(FAMILY_NAMES),
    }


def generate_birth_date(age: int, episode_date: Optional[date] = None) -> date:
    """Calculate a random birth date that makes the person the given age.

    The birth date is chosen so the person is exactly `age` years old on
    some day within the year window ending at `episode_date`.

    Args:
        age: Target age in years.
        episode_date: Reference date. Defaults to today.

    Returns:
        A date object.
    """
    ref = episode_date or date.today()

    # Latest possible birthday: they turned `age` today
    latest_birthday = ref.replace(year=ref.year - age)
    # Earliest possible birthday: one day before they would be age+1
    earliest_birthday = ref.replace(year=ref.year - age - 1) + timedelta(days=1)

    delta_days = (latest_birthday - earliest_birthday).days
    random_offset = random.randint(0, max(delta_days, 0))
    return earliest_birthday + timedelta(days=random_offset)


def assign_identity(ctx: PatientContext, episode_date: Optional[date] = None) -> None:
    """Populate identity fields on a PatientContext in place.

    Args:
        ctx: The patient context to populate.
        episode_date: Reference date for birth date calculation. Defaults to today.
    """
    name = generate_name()
    ctx.given_name = name["given_name"]
    ctx.family_name = name["family_name"]

    address = generate_address(state=ctx.state)
    ctx.street_address = address["street_address"]
    ctx.city = address["city"]
    # If ctx.state was None, adopt the randomly chosen one
    if ctx.state is None:
        ctx.state = address["state"]

    ctx.birth_date = generate_birth_date(ctx.age, episode_date=episode_date)
