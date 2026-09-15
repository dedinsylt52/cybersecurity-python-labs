import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

users = {
    "forensic_lead": {
        "role": "forensic_analyst",
        "clearance": 4,
        "department": "Forensics",
        "active": True,
    },
    "compliance_off": {
        "role": "compliance_officer",
        "clearance": 3,
        "department": "Compliance",
        "active": True,
    },
    "trainee_sec": {
        "role": "trainee",
        "clearance": 1,
        "department": "Training",
        "active": True,
    },
    "vendor_tech": {
        "role": "vendor_support",
        "clearance": 2,
        "department": "Vendor",
        "active": True,
    },
    "archived_usr": {
        "role": "archived",
        "clearance": 1,
        "department": "Archive",
        "active": False,
    },
}
resources = [
    ("forensic_images", 4),
    ("compliance_reports", 3),
    ("training_videos", 1),
    ("vendor_tools", 2),
    ("evidence_locker", 4),
    ("certification_docs", 1),
    ("audit_findings", 3),
    ("chain_of_custody", 4),
    ("support_tickets", 2),
    ("learning_modules", 1),
]
security_levels = ("Basic", "Standard", "Protected", "Maximum")
blocked_users = {"archived_usr", "terminated_vendor", "security_breach"}


def print_resources():
    print("Список ресурсів системи:")
    for name, level in resources:
        level_name = security_levels[level - 1]
        print(f"  {name:<25} -> {level_name}")
    print()


def check_access(username, resource_name, resource_level):
    if username not in users:
        return "DENY", "User not found"

    if username in blocked_users:
        return "DENY", "User is blocked"

    user = users[username]

    if not user["active"]:
        return "DENY", "Account inactive"

    if user["clearance"] >= resource_level:
        return "ALLOW", ""

    return "DENY", "Insufficient clearance"


def main():
    print(f"Студент: {STUDENT_NAME}, Група: {GROUP_NAME}, Варіант: {VARIANT_NUMBER}")
    print()

    print_resources()

    print("Перевірка доступу:")
    for username in users:
        for resource_name, resource_level in resources:
            result, reason = check_access(username, resource_name, resource_level)
            if result == "ALLOW":
                print(f"user={username} resource={resource_name} -> ALLOW")
            else:
                print(f"user={username} resource={resource_name} -> DENY ({reason})")


if __name__ == "__main__":
    main()
