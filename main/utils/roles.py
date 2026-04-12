# main/utils/roles.py

def has_role(user, role):
    return user.is_authenticated and user.groups.filter(name=role).exists()