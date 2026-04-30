"""Rent stabilization status classifier."""
import pandas as pd


def classify_rent_stab(units, year_built, exempt):
    """Returns one of: 'Likely Rent Stabilized', 'Possibly Rent Stabilized',
    'Likely Market Rate', 'Unknown'."""

    if pd.isna(units) or pd.isna(year_built) or units == 0:
        return 'Unknown'

    units = int(units)
    year_built = int(year_built)
    has_abatement = pd.notna(exempt) and float(exempt) > 0

    # Pre-1974 with 6+ units — default rent-stabilized under NY State law (ETPA 1974)
    if year_built < 1974 and year_built > 0 and units >= 6:
        return 'Likely Rent Stabilized'

    # Has tax abatement (421-a, J-51, etc.) — usually rent-stabilized for abatement period
    if has_abatement and units >= 6:
        return 'Possibly Rent Stabilized'

    # Newer building or fewer than 6 units — likely market rate
    if year_built >= 1974 and not has_abatement:
        return 'Likely Market Rate'

    if units < 6:
        return 'Likely Market Rate'

    return 'Unknown'


def explain_rent_stab(status, units, year_built, exempt):
    """Returns a renter-facing explanation string."""

    if status == 'Likely Rent Stabilized':
        return (
            f"Built in {int(year_built)} with {int(units)} residential units. This building is legally subject to NY State's Emergency Tenant Protection Act of 1974. "
            "IMPORTANT: Individual units may have been deregulated through vacancy decontrol (pre-2019), substantial rehabilitation, or high-rent decertification. "
            "If you're paying market-rate rent here, request your unit's rent history from NY DHCR (file form REC-1) — illegal deregulation is common and tenants may be entitled to rent refunds and damages."
        )

    if status == 'Possibly Rent Stabilized':
        return (
            f"This building has {int(units)} residential units and active tax abatements "
            "(such as 421-a or J-51). Buildings receiving these benefits are typically "
            "rent-stabilized for the duration of the abatement. Confirm with the landlord "
            "and check NY DHCR records."
        )

    if status == 'Likely Market Rate':
        return (
            f"Built in {int(year_built) if year_built > 0 else 'unknown'}, "
            f"{int(units) if not pd.isna(units) else 'unknown'} units. "
            "Likely a market-rate building. Rent increases are not legally capped and lease "
            "renewal is at the landlord's discretion."
        )

    return "Insufficient data to determine rent stabilization status. Check NY DHCR directly."
