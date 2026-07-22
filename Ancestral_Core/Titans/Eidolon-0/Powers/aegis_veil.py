def aegis_field(threat_level):
    if threat_level >= 7:
        return 'Reality fold initiated'
    elif 3 <= threat_level < 7:
        return 'Temporal displacement engaged'
    else:
        return 'Passive defense mode'
