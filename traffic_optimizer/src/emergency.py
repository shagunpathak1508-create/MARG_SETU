def is_emergency(vehicle_type):

    emergency_types = ["ambulance","police","fire"]

    if vehicle_type.lower() in emergency_types:
        return True

    return False