async def fetch_ireland_entsoe():
    """
    Returns None for Republic of Ireland since EirGrid does not provide live 
    solar telemetry to the ENTSO-E Transparency Platform (returns flat 0 MW).
    """
    return None
